from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.behavioral.analyzer import BehavioralAnalyzer
from app.ai.proactive.coach import OutreachDecision, evaluate_outreach
from app.config import get_settings
from app.models import User
from app.repositories import MemoryRepository

settings = get_settings()


def _user_now(user: User) -> datetime:
    tz = ZoneInfo(user.timezone or settings.user_timezone)
    return datetime.now(tz)


def _parse_deadline(raw: str | None) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


async def evaluate_outreach_smart(
    session: AsyncSession,
    user: User,
    has_checkin_today: bool,
) -> OutreachDecision:
    base = evaluate_outreach(user, has_checkin_today)
    if base.should_send:
        return base

    now = _user_now(user)
    if not (10 <= now.hour <= 22):
        return OutreachDecision(False, reason="quiet_hours")

    analyzer = BehavioralAnalyzer(session)
    flags = await analyzer.detect_patterns(user.id)
    flag_names = {f["flag"] for f in flags}

    if "reminder_followup" in flag_names:
        return OutreachDecision(True, "reminder_followup", "hatirlatma_takip")

    if "stress_mood_correlation" in flag_names and not has_checkin_today:
        return OutreachDecision(True, "stress_mood", "stres_ruh_hali")

    if "stoic_ritual_gap" in flag_names:
        return OutreachDecision(True, "stoic_invite", "stoic_davet")

    memories = MemoryRepository(session)
    goals = await memories.get_goals(user.id)
    today = now.date()
    for goal in goals:
        meta = goal.metadata_ or {}
        deadline = _parse_deadline(meta.get("deadline"))
        if deadline and 0 <= (deadline - today).days <= 7:
            return OutreachDecision(True, "goal_deadline", f"hedef_{goal.id}")

    return OutreachDecision(False, reason="no_smart_trigger")
