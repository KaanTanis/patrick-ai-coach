from statistics import mean
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import CheckInRepository, MealRepository, MemoryRepository
from app.repositories.philosophy import DreamRepository, EmotionRepository, StoicRitualRepository


def _avg(values: list[float | int | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    return mean(nums) if nums else None


class BehavioralAnalyzer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.check_ins = CheckInRepository(session)
        self.meals = MealRepository(session)
        self.dreams = DreamRepository(session)
        self.emotions = EmotionRepository(session)
        self.stoic = StoicRitualRepository(session)
        self.memories = MemoryRepository(session)

    async def detect_patterns(self, user_id: int) -> list[dict[str, Any]]:
        checkins = await self.check_ins.get_recent(user_id, days=30)
        if len(checkins) < 5:
            return []

        flags: list[dict[str, Any]] = []

        high_stress = [c for c in checkins if c.stress and c.stress >= 7]
        low_stress = [c for c in checkins if c.stress and c.stress < 7]

        if high_stress and low_stress:
            high_mood = _avg([c.mood for c in high_stress if c.mood])
            low_mood = _avg([c.mood for c in low_stress if c.mood])
            if (
                high_mood
                and low_mood
                and high_mood < low_mood * 0.8
            ):
                flags.append(
                    {
                        "flag": "stress_mood_correlation",
                        "evidence": {
                            "high_stress_avg_mood": round(high_mood, 1),
                            "low_stress_avg_mood": round(low_mood, 1),
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
                poor_dates = {c.date for c in poor_sleep}
                missed_after_poor = sum(
                    1 for d in poor_dates
                    if not any(c.date == d for c in checkins)
                )
                if missed_after_poor >= 2:
                    flags.append(
                        {
                            "flag": "sleep_motivation_checkin_chain",
                            "evidence": {"poor_sleep_days_without_checkin": missed_after_poor},
                        }
                    )

        workout_days = sum(1 for c in checkins if c.workout_done)
        if len(checkins) >= 14 and workout_days < 3:
            flags.append(
                {
                    "flag": "workout_inconsistency",
                    "evidence": {"workout_days_last_30": workout_days},
                }
            )

        setback_count = await self.memories.count_recent_setbacks(user_id, days=30)
        if setback_count >= 2:
            flags.append(
                {
                    "flag": "recurring_setback",
                    "evidence": {"setback_count": setback_count},
                }
            )

        reminders = await self.memories.get_reminders(user_id, limit=3)
        if reminders and len(checkins) >= 7:
            recent_notes = " ".join((c.notes or "") for c in checkins[:7]).lower()
            mentioned = any(r.content[:20].lower() in recent_notes for r in reminders)
            if not mentioned:
                flags.append(
                    {
                        "flag": "reminder_followup",
                        "evidence": {"active_reminders": len(reminders)},
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

        weekday_mood = _avg([c.mood for c in checkins if c.mood and c.date.weekday() < 5])
        weekend_mood = _avg([c.mood for c in checkins if c.mood and c.date.weekday() >= 5])
        if weekday_mood and weekend_mood and abs(weekday_mood - weekend_mood) >= 2:
            flags.append(
                {
                    "flag": "weekend_vs_weekday_mood",
                    "evidence": {
                        "weekday_avg_mood": round(weekday_mood, 1),
                        "weekend_avg_mood": round(weekend_mood, 1),
                    },
                }
            )

        meal_dates = {m.logged_at.date() for m in meals}
        post_meal_low_energy = 0
        for c in checkins:
            if c.date in meal_dates and c.energy and c.energy <= 4:
                post_meal_low_energy += 1
        if post_meal_low_energy >= 3:
            flags.append(
                {
                    "flag": "post_meal_energy_crash",
                    "evidence": {"low_energy_meal_days": post_meal_low_energy},
                }
            )

        dream_list = await self.dreams.get_recent(user_id, days=30, limit=10)
        if dream_list and high_stress:
            stress_dates = {c.date for c in high_stress}
            dream_stress_days = sum(
                1 for d in dream_list if d.logged_at.date() in stress_dates
            )
            if dream_stress_days >= 2:
                flags.append(
                    {
                        "flag": "dream_stress_correlation",
                        "evidence": {
                            "dreams_on_stress_days": dream_stress_days,
                            "total_dreams": len(dream_list),
                        },
                    }
                )

        ritual_counts = await self.stoic.count_recent_by_type(user_id, days=7)
        morning = ritual_counts.get("morning", 0)
        evening = ritual_counts.get("evening", 0)
        if morning + evening >= 3:
            flags.append(
                {
                    "flag": "stoic_ritual_consistency",
                    "evidence": {"morning": morning, "evening": evening, "days": 7},
                }
            )
        elif morning + evening == 0 and len(checkins) >= 7:
            flags.append(
                {
                    "flag": "stoic_ritual_gap",
                    "evidence": {"rituals_last_7_days": 0},
                }
            )

        emotion_entries = await self.emotions.get_recent(user_id, days=14, limit=20)
        if emotion_entries and high_stress:
            high_stress_emotions = [
                e for e in emotion_entries
                if any(c.stress and c.stress >= 7 and c.date == e.logged_at.date() for c in checkins)
            ]
            if len(high_stress_emotions) >= 3:
                flags.append(
                    {
                        "flag": "emotion_stress_correlation",
                        "evidence": {"stress_day_emotions": len(high_stress_emotions)},
                    }
                )

        if high_stress and meals:
            high_stress_dates = {c.date for c in high_stress}
            stress_meals = [m for m in meals if m.logged_at.date() in high_stress_dates]
            low_energy_stress = sum(
                1 for c in checkins
                if c.date in high_stress_dates and c.energy and c.energy <= 4
            )
            if len(stress_meals) >= 2 and low_energy_stress >= 2:
                flags.append(
                    {
                        "flag": "stress_food_energy_chain",
                        "evidence": {
                            "stress_day_meals": len(stress_meals),
                            "low_energy_stress_days": low_energy_stress,
                        },
                    }
                )

        recent_setback = await self.memories.get_recent_relapse(user_id, days=7)
        if recent_setback:
            since = recent_setback.created_at.date()
            dream_list_recent = await self.dreams.get_recent(user_id, days=7, limit=10)
            shadow_spike = sum(1 for d in dream_list_recent if d.logged_at.date() >= since)
            if shadow_spike >= 2:
                flags.append(
                    {
                        "flag": "setback_reflection_spike",
                        "evidence": {"reflection_entries_after_setback": shadow_spike},
                    }
                )

        return flags
