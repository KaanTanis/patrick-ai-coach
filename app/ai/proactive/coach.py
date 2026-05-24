from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User
from app.repositories import CheckInRepository, UserRepository
from app.services.preferences import PreferencesService

settings = get_settings()


@dataclass
class OutreachDecision:
    should_send: bool
    nudge_type: str = ""
    reason: str = ""


def _user_now(user: User) -> datetime:
    tz = ZoneInfo(user.timezone or settings.user_timezone)
    return datetime.now(tz)


def _parse_time_on_date(time_str: str | None, base: datetime) -> datetime | None:
    if not time_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%H:%M", "%H:%M:%S"):
        try:
            if fmt.startswith("%Y"):
                return datetime.strptime(time_str, fmt).replace(tzinfo=base.tzinfo)
            parsed = datetime.strptime(time_str, fmt)
            return base.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
        except ValueError:
            continue
    return None


def _in_sleep_window(user: User, now: datetime) -> bool:
    schedule = user.schedule or {}
    sleep_window = schedule.get("sleep_window")
    if not sleep_window or not isinstance(sleep_window, str):
        return False
    # Format: "23:00-07:00" or descriptive text — simple hour check
    if "-" not in sleep_window:
        return False
    try:
        start_s, end_s = sleep_window.split("-", 1)
        start = datetime.strptime(start_s.strip(), "%H:%M").time()
        end = datetime.strptime(end_s.strip(), "%H:%M").time()
        t = now.time()
        if start <= end:
            return start <= t <= end
        return t >= start or t <= end
    except ValueError:
        return False


def evaluate_outreach(user: User, has_checkin_today: bool) -> OutreachDecision:
    if not settings.proactive_outreach_enabled:
        return OutreachDecision(False, reason="disabled")

    now = _user_now(user)
    today = now.date()

    if user.nudges_today_date == today and (user.nudges_today_count or 0) >= settings.max_daily_nudges:
        return OutreachDecision(False, reason="daily_limit")

    if user.last_proactive_at:
        last = user.last_proactive_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=ZoneInfo("UTC"))
        last_local = last.astimezone(now.tzinfo)
        if now - last_local < timedelta(hours=settings.min_hours_between_nudges):
            return OutreachDecision(False, reason="too_soon")

    if _in_sleep_window(user, now):
        return OutreachDecision(False, reason="sleep_window")

    schedule = user.schedule or {}

    next_start = _parse_time_on_date(schedule.get("next_shift_start"), now)
    if next_start:
        delta = (next_start - now).total_seconds() / 3600
        if 0 < delta <= 2:
            return OutreachDecision(True, "pre_shift", "vardiya_2h")

    next_end = _parse_time_on_date(schedule.get("next_shift_end"), now)
    if next_end:
        delta = (now - next_end).total_seconds() / 3600
        if 0 <= delta <= 1.5:
            return OutreachDecision(True, "post_shift", "vardiya_sonrasi")

    if not has_checkin_today and 10 <= now.hour <= 22:
        return OutreachDecision(True, "report_request", "checkin_eksik")

    if user.last_proactive_at is None and 10 <= now.hour <= 20:
        return OutreachDecision(True, "gentle_ping", "ilk_temas")

    # Fallback: active hours gentle ping if no nudge today
    if (user.nudges_today_date != today or not user.nudges_today_count) and 12 <= now.hour <= 21:
        return OutreachDecision(True, "mini_pulse", "fallback")

    return OutreachDecision(False, reason="no_trigger")


NUDGE_TEMPLATES: dict[str, str] = {
    "report_request": (
        "Merhaba. Bugün henüz rapor vermedin — ruh halin, enerjin ve günün nasıl geçiyor? "
        "Kısa bir check-in yapalım mı?"
    ),
    "pre_shift": (
        "Vardiyan yaklaşıyor. Kısa bir check-in ile zihnini toparlamak ister misin?"
    ),
    "post_shift": (
        "Vardiya bitti sanırım. Nasıl geçti? Kısa bir debrief yapalım mı?"
    ),
    "mini_pulse": (
        "Naber? Enerjin ve stresin şu an kaç/10? Kısaca yazabilirsin."
    ),
    "gentle_ping": (
        "Bir süredir sessizsin. Nasılsın? İstersen sohbet edebilir veya kısa rapor verebilirsin."
    ),
}


class ProactiveCoach:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.check_ins = CheckInRepository(session)
        self.preferences = PreferencesService(session)

    async def evaluate_user(self, user: User) -> OutreachDecision:
        today = _user_now(user).date()
        checkin = await self.check_ins.get_by_date(user.id, today)
        return evaluate_outreach(user, checkin is not None)

    async def compose_message(self, user: User, decision: OutreachDecision) -> str:
        from app.repositories import MemoryRepository

        base = NUDGE_TEMPLATES.get(decision.nudge_type, NUDGE_TEMPLATES["mini_pulse"])
        reminders = await MemoryRepository(self.session).get_reminders(user.id, limit=2)
        reminder_hint = ""
        if reminders:
            reminder_hint = "Hatırlatmalar: " + "; ".join(r.content[:80] for r in reminders)

        if user.context_summary or reminder_hint:
            from app.ai.openai_client import get_openai_client

            prompt = f"""Kişisel koç olarak kısa bir proaktif mesaj yaz (max 80 kelime, Türkçe).
Mesaj türü: {decision.nudge_type}
Şablon fikir: {base}
Kullanıcı profili: {(user.context_summary or '')[:800]}
{reminder_hint}
Vardiya bilgisi: {user.schedule or {}}
Kişilik: {user.personality_key}
Varsa hatırlatmalardan birini doğal şekilde ekle. Samimi ol. Rapor/check-in davet et."""

            try:
                return await get_openai_client().chat(
                    [{"role": "user", "content": prompt}],
                    model="gpt-4o-mini",
                    max_tokens=150,
                )
            except Exception:
                pass

        return base

    async def process_user(self, user: User) -> bool:
        if not await self.preferences.proactive_enabled(user.id):
            return False

        decision = await self.evaluate_user(user)
        if not decision.should_send:
            return False

        message = await self.compose_message(user, decision)
        from aiogram import Bot

        from app.bot.keyboards import checkin_start_keyboard

        bot = Bot(token=settings.telegram_bot_token)
        try:
            reply_markup = (
                checkin_start_keyboard()
                if decision.nudge_type in {"report_request", "pre_shift", "post_shift"}
                else None
            )
            await bot.send_message(user.telegram_id, message, reply_markup=reply_markup)
        finally:
            await bot.session.close()

        today = _user_now(user).date()
        await self.users.record_proactive_nudge(user.id, today)
        return True
