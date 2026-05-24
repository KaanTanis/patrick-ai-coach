from datetime import date, datetime
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompt_composer import PromptComposer
from app.models import CheckIn
from app.repositories import CheckInRepository


class CheckInService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.check_ins = CheckInRepository(session)
        self.prompts = PromptComposer(session)

    def _today_for_timezone(self, timezone: str) -> date:
        try:
            return datetime.now(ZoneInfo(timezone)).date()
        except Exception:
            return datetime.now(ZoneInfo("Europe/Istanbul")).date()

    async def save_checkin(
        self, user_id: int, data: dict[str, Any], timezone: str = "Europe/Istanbul"
    ) -> CheckIn:
        today = self._today_for_timezone(timezone)
        return await self.check_ins.upsert(user_id, today, data)

    async def generate_insight(self, user_id: int, check_in: CheckIn) -> str:
        recent = await self.check_ins.get_recent(user_id, days=7)
        averages = self._compute_averages(recent)

        checkin_data = {
            "mood": check_in.mood,
            "sleep_quality": check_in.sleep_quality,
            "energy": check_in.energy,
            "workout_done": check_in.workout_done,
            "stress": check_in.stress,
            "weight": float(check_in.weight) if check_in.weight else None,
            "motivation": check_in.motivation,
            "notes": check_in.notes,
        }

        return await self.prompts.compose_checkin_summary(checkin_data, averages)

    async def complete_checkin(
        self, user_id: int, data: dict[str, Any], timezone: str = "Europe/Istanbul"
    ) -> str:
        check_in = await self.save_checkin(user_id, data, timezone=timezone)
        return await self.generate_insight(user_id, check_in)

    def _compute_averages(self, checkins: list) -> dict[str, float | None]:
        fields = [
            "mood",
            "sleep_quality",
            "energy",
            "stress",
            "motivation",
        ]
        result: dict[str, float | None] = {}
        for field in fields:
            values = [getattr(c, field) for c in checkins if getattr(c, field) is not None]
            result[field] = round(mean(values), 1) if values else None
        return result
