"""Adaptive interview question composer for /rapor."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_client import get_openai_client
from app.repositories import CheckInRepository, MemoryRepository, UserRepository

STEP_POOL = ["mood", "sleep", "energy", "stress", "motivation", "weight", "workout", "notes"]

DEFAULT_QUESTIONS = {
    "mood": "Bugün ruh halin nasıl? (1-10)",
    "sleep": "Dün gece uyku kaliten nasıldı? (1-10)",
    "energy": "Şu anki enerji seviyen? (1-10)",
    "stress": "Bugün stres seviyen? (1-10)",
    "motivation": "Motivasyon seviyen? (1-10)",
    "weight": "Bugünkü kilon? (kg olarak yaz veya Atla)",
    "workout": "Bugün hareket/antrenman yaptın mı?",
    "notes": "Eklemek istediğin bir not var mı?",
}

RATING_STEPS = {"mood", "sleep", "energy", "stress", "motivation"}
YES_NO_STEPS = {"workout"}
TEXT_STEPS = {"weight", "notes"}


class InterviewComposer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.check_ins = CheckInRepository(session)
        self.memories = MemoryRepository(session)

    async def plan_steps(self, user_id: int) -> list[str]:
        user = await self.users.get_by_id(user_id)
        recent = await self.check_ins.get_recent(user_id, days=7)

        priority: list[str] = []
        if not recent:
            priority = ["mood", "sleep", "energy", "stress", "motivation"]
        else:
            latest = recent[0]
            field_map = {
                "mood": latest.mood,
                "sleep": latest.sleep_quality,
                "energy": latest.energy,
                "stress": latest.stress,
                "motivation": latest.motivation,
                "weight": latest.weight,
            }
            for step, value in field_map.items():
                if value is None:
                    priority.append(step)
            if latest.workout_done is None:
                priority.append("workout")

        if user and not (user.schedule or {}).get("sleep_window"):
            if "sleep" not in priority:
                priority.insert(0, "sleep")

        goals = await self.memories.get_goals(user_id)
        if goals and "motivation" not in priority:
            priority.append("motivation")

        steps: list[str] = []
        for step in priority:
            if step not in steps:
                steps.append(step)
        for step in STEP_POOL:
            if step not in steps:
                steps.append(step)
            if len(steps) >= 5:
                break

        if "notes" not in steps:
            steps.append("notes")
        return steps[:6]

    async def phrase_question(
        self,
        step: str,
        previous_answers: dict[str, Any],
        step_index: int,
        total_steps: int,
    ) -> str:
        context = ", ".join(f"{k}={v}" for k, v in previous_answers.items()) or "henüz yok"
        default = DEFAULT_QUESTIONS.get(step, f"{step}?")

        prompt = f"""Kişisel koçluk raporu için TEK soru yaz (Türkçe).
Adım: {step} ({step_index + 1}/{total_steps})
Önceki yanıtlar: {context}
Kalıbı her seferinde değiştir; kısa ve sıcak ol.
1-10 skala adımlarında (1-10) belirt.
Sadece soruyu yaz, açıklama ekleme."""

        try:
            text = await get_openai_client().chat(
                [{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                max_tokens=80,
            )
            return text.strip() or default
        except Exception:
            return default

    def step_kind(self, step: str) -> str:
        if step in RATING_STEPS:
            return "rating"
        if step in YES_NO_STEPS:
            return "yes_no"
        return "text"
