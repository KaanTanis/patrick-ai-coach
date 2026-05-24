from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context.bundle import ContextBundle, ContextBuilder
from app.ai.personalities.base import CORE_IDENTITY, RELAPSE_GUARDRAILS
from app.config import get_settings
from app.models import CheckIn, Conversation, Memory, User
from app.repositories import PersonalityRepository

settings = get_settings()
TEMPLATES_DIR = Path(__file__).parent / "personalities" / "templates"


class PromptComposer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.personalities = PersonalityRepository(session)
        self.context_builder = ContextBuilder(session)

    async def _get_personality_prompt(self, personality_key: str) -> str:
        profile = await self.personalities.get(personality_key)
        if profile:
            return profile.system_prompt

        template_path = TEMPLATES_DIR / f"{personality_key}.yaml"
        if template_path.exists():
            data = yaml.safe_load(template_path.read_text())
            return data.get("system_prompt", "")

        companion = TEMPLATES_DIR / "companion.yaml"
        data = yaml.safe_load(companion.read_text())
        return data.get("system_prompt", "")

    def _format_memories(self, memories: list[Memory]) -> str:
        return self.context_builder.format_memories(memories)

    def _format_checkins(self, checkins: list[CheckIn]) -> str:
        return self.context_builder._format_checkins(checkins)

    def _format_history(self, messages: list[Conversation]) -> list[dict[str, str]]:
        return self.context_builder._trim_history_to_budget(messages)

    async def compose_from_bundle(
        self,
        bundle: ContextBundle,
        user_message: str,
        relapse_context: bool = False,
    ) -> list[dict[str, str]]:
        user = bundle.user
        personality_prompt = await self._get_personality_prompt(user.personality_key)
        goals_text = ""
        if user.goals:
            goals_text = f"Kullanıcı hedefleri: {user.goals}"

        schedule_text = str(bundle.schedule) if bundle.schedule else "Bilinmiyor"

        system_parts = [
            CORE_IDENTITY,
            f"Kişilik modu: {user.personality_key}",
            personality_prompt,
            goals_text,
            f"Şu an (kullanıcı saati): {bundle.local_time} — {bundle.time_of_day}",
            f"Kullanıcı saat dilimi: {user.timezone}",
            "--- Kullanıcı profili (güncel) ---",
            bundle.profile_summary,
            "--- Vardiya ve ritim ---",
            schedule_text,
            "--- Episodik geçmiş (tarihli özetler) ---",
            self.context_builder.format_episodes(bundle.episodic_summaries),
            "--- Getirilen hafızalar ---",
            self._format_memories(bundle.memories),
            "--- Son check-in'ler (7 gün) ---",
            bundle.checkin_snapshot,
            "--- Bugünkü öğünler ---",
            bundle.today_meals_text,
        ]

        if relapse_context:
            system_parts.append(RELAPSE_GUARDRAILS)

        system_parts.append(f"Prompt version: {settings.prompt_version}")

        messages: list[dict[str, str]] = [
            {"role": "system", "content": "\n\n".join(part for part in system_parts if part)}
        ]
        messages.extend(bundle.recent_history)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def compose(
        self,
        user: User,
        user_message: str,
        memories: list[Memory],
        checkins: list[CheckIn],
        history: list[Conversation],
        relapse_context: bool = False,
    ) -> list[dict[str, str]]:
        bundle = ContextBundle(
            user=user,
            profile_summary=user.context_summary or "Henüz profil özeti oluşturulmadı.",
            schedule=user.schedule or {},
            local_time="",
            time_of_day="",
            memories=memories,
            episodic_summaries=[],
            checkin_snapshot=self._format_checkins(checkins),
            today_meals_text="",
            recent_history=self._format_history(history),
        )
        return await self.compose_from_bundle(bundle, user_message, relapse_context)

    async def compose_checkin_summary(
        self, checkin_data: dict[str, Any], averages: dict[str, float | None]
    ) -> str:
        prompt = f"""Kullanıcı için sıcak bir günlük check-in yanıtı oluştur.
Bugünkü veriler: {checkin_data}
7 günlük ortalamalar: {averages}
Format: kabul + bir gözlem + bir mikro eylem. 100 kelimenin altında. Utandırma yok.
Yanıtı Türkçe yaz."""

        return await self._mini_chat(prompt)

    async def _mini_chat(self, prompt: str) -> str:
        from app.ai.openai_client import get_openai_client

        return await get_openai_client().chat(
            [{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=200,
        )
