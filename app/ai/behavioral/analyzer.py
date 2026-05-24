from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SmokingEventType
from app.repositories import CheckInRepository, MealRepository, SmokingEventRepository, WorkoutRepository


def _avg(values: list[float | int | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    return mean(nums) if nums else None


class BehavioralAnalyzer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.check_ins = CheckInRepository(session)
        self.meals = MealRepository(session)
        self.smoking = SmokingEventRepository(session)
        self.workouts = WorkoutRepository(session)

    async def detect_patterns(self, user_id: int) -> list[dict[str, Any]]:
        checkins = await self.check_ins.get_recent(user_id, days=30)
        if len(checkins) < 5:
            return []

        flags: list[dict[str, Any]] = []

        high_stress = [c for c in checkins if c.stress and c.stress >= 7]
        low_stress = [c for c in checkins if c.stress and c.stress < 7]

        if high_stress and low_stress:
            high_craving = _avg([c.smoking_craving for c in high_stress])
            low_craving = _avg([c.smoking_craving for c in low_stress])
            if high_craving and low_craving and high_craving > low_craving * 1.5:
                flags.append(
                    {
                        "flag": "stress_smoking_correlation",
                        "evidence": {
                            "high_stress_avg_craving": round(high_craving, 1),
                            "low_stress_avg_craving": round(low_craving, 1),
                        },
                    }
                )

        poor_sleep = [c for c in checkins if c.sleep_quality and c.sleep_quality <= 5]
        good_sleep = [c for c in checkins if c.sleep_quality and c.sleep_quality >= 7]

        if poor_sleep and good_sleep:
            poor_motivation = _avg([c.motivation for c in poor_sleep])
            good_motivation = _avg([c.motivation for c in good_sleep])
            if (
                poor_motivation
                and good_motivation
                and poor_motivation < good_motivation * 0.7
            ):
                flags.append(
                    {
                        "flag": "sleep_motivation_link",
                        "evidence": {
                            "poor_sleep_avg_motivation": round(poor_motivation, 1),
                            "good_sleep_avg_motivation": round(good_motivation, 1),
                        },
                    }
                )

        workouts = await self.workouts.get_recent(user_id, days=30)
        completed = [w for w in workouts if w.completed]
        if len(checkins) >= 14 and len(completed) < 3:
            flags.append(
                {
                    "flag": "workout_inconsistency",
                    "evidence": {"workouts_last_30_days": len(completed)},
                }
            )

        smoking_events = await self.smoking.get_recent(user_id, days=30)
        relapses = [e for e in smoking_events if e.event_type == SmokingEventType.RELAPSE]
        if len(relapses) >= 2:
            flags.append(
                {
                    "flag": "recurring_relapse",
                    "evidence": {"relapse_count": len(relapses)},
                }
            )

        meals = await self.meals.get_recent(user_id, limit=30)
        if meals and high_stress:
            high_stress_dates = {c.date for c in high_stress}
            stress_day_meals = [
                m for m in meals if m.logged_at.date() in high_stress_dates
            ]
            if len(stress_day_meals) >= 3:
                avg_cal = _avg([m.estimated_calories for m in stress_day_meals])
                all_cal = _avg([m.estimated_calories for m in meals if m.estimated_calories])
                if avg_cal and all_cal and avg_cal > all_cal * 1.2:
                    flags.append(
                        {
                            "flag": "stress_eating_pattern",
                            "evidence": {
                                "stress_day_avg_calories": round(avg_cal),
                                "overall_avg_calories": round(all_cal),
                            },
                        }
                    )

        return flags
