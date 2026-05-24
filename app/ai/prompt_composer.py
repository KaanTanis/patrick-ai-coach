from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context.bundle import ContextBundle, ContextBuilder
from app.ai.personalities.base import CORE_IDENTITY, SETBACK_GUARDRAILS
from app.ai.personalities.lenses import CRISIS_KEYWORDS, CRISIS_RESPONSE, FREE_MODE_ADDENDUM
from app.config import get_settings
from app.models import CheckIn, Conversation, Memory, User
from app.repositories import PersonalityRepository
from app.services.lens import lens_prompt

settings = get_settings()
TEMPLATES_DIR = Path(__file__).parent / "personalities" / "templates"


CONTEXTUAL_QUESTION_ADDENDUM = """
Profil boşlukları: {gaps}
Yanıtının sonunda, kullanıcıyı daha iyi tanımak için TEK açık uçlu soru sor.
Soru kalıbını her seferinde değiştir. Zorunlu değilse bile meraklı ve kısa olsun.
Kullanıcı "bu kadar soru yeter" derse soru sorma.
"""


class PromptComposer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.personalities = PersonalityRepository(session)
        self.context_builder = ContextBuilder(session)

    async def _get_personality(self, personality_key: str):
        profile = await self.personalities.get(personality_key)
        if profile:
            return profile
        template_path = TEMPLATES_DIR / f"{personality_key}.yaml"
        if template_path.exists():
            data = yaml.safe_load(template_path.read_text())
            return type("Profile", (), {
                "system_prompt": data.get("system_prompt", ""),
                "tone_rules": {
                    "voice": data.get("voice"),
                    "metaphor_style": data.get("metaphor_style"),
                    "challenge_level": data.get("challenge_level"),
                    "question_ratio": data.get("question_ratio"),
                    "sample_phrases": data.get("sample_phrases", []),
                },
            })()
        companion = yaml.safe_load((TEMPLATES_DIR / "companion.yaml").read_text())
        return type("Profile", (), {
            "system_prompt": companion.get("system_prompt", ""),
            "tone_rules": {},
        })()

    def _format_tone_rules(self, tone_rules: dict[str, Any] | None) -> str:
        if not tone_rules:
            return ""
        parts = []
        if tone_rules.get("voice"):
            parts.append(f"Ses tonu: {tone_rules['voice']}")
        if tone_rules.get("metaphor_style"):
            parts.append(f"Metafor stili: {tone_rules['metaphor_style']}")
        if tone_rules.get("challenge_level"):
            parts.append(f"Meydan okuma: {tone_rules['challenge_level']}")
        if tone_rules.get("question_ratio") is not None:
            parts.append(f"Soru oranı hedefi: {tone_rules['question_ratio']}")
        phrases = tone_rules.get("sample_phrases") or []
        if phrases:
            parts.append("Örnek ifadeler:\n" + "\n".join(f"- {p}" for p in phrases[:4]))
        return "\n".join(parts)

    def check_crisis(self, message: str) -> str | None:
        lower = message.lower()
        for kw in CRISIS_KEYWORDS:
            if kw in lower:
                return CRISIS_RESPONSE
        return None

    async def compose_from_bundle(
        self,
        bundle: ContextBundle,
        user_message: str,
        relapse_context: bool = False,
        active_lens: str | None = None,
        free_mode: bool = False,
        ask_contextual_question: bool = False,
        profile_gaps: list[str] | None = None,
    ) -> list[dict[str, str]]:
        user = bundle.user
        profile = await self._get_personality(user.personality_key)
        personality_prompt = profile.system_prompt
        tone_text = self._format_tone_rules(getattr(profile, "tone_rules", None))

        goals_text = ""
        if user.goals:
            goals_text = f"Kullanıcı hedefleri: {user.goals}"

        schedule_text = str(bundle.schedule) if bundle.schedule else "Bilinmiyor"
        lens_text = lens_prompt(active_lens)

        system_parts = [
            CORE_IDENTITY,
            f"Kişilik modu: {user.personality_key}",
            personality_prompt,
            tone_text,
            lens_text,
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
            "--- Son felsefi kayıtlar (rüya/gölge/düşünce) ---",
            bundle.philosophy_snapshot,
            "--- Bugünkü öğünler ---",
            bundle.today_meals_text,
        ]

        if free_mode:
            system_parts.append(FREE_MODE_ADDENDUM)
        if ask_contextual_question and profile_gaps:
            system_parts.append(
                CONTEXTUAL_QUESTION_ADDENDUM.format(gaps=", ".join(profile_gaps))
            )
        if relapse_context:
            system_parts.append(SETBACK_GUARDRAILS)
        system_parts.append(f"Prompt version: {settings.prompt_version}")

        messages: list[dict[str, str]] = [
            {"role": "system", "content": "\n\n".join(part for part in system_parts if part)}
        ]
        messages.extend(bundle.recent_history)
        messages.append({"role": "user", "content": user_message})
        return messages

    def _format_memories(self, memories: list[Memory]) -> str:
        return self.context_builder.format_memories(memories)

    def _format_checkins(self, checkins: list[CheckIn]) -> str:
        return self.context_builder._format_checkins(checkins)

    def _format_history(self, messages: list[Conversation]) -> list[dict[str, str]]:
        return self.context_builder._trim_history_to_budget(messages)

    async def compose(
        self,
        user: User,
        user_message: str,
        memories: list[Memory],
        checkins: list[CheckIn],
        history: list[Conversation],
        relapse_context: bool = False,
        active_lens: str | None = None,
        free_mode: bool = False,
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
            philosophy_snapshot="",
            recent_history=self._format_history(history),
        )
        return await self.compose_from_bundle(
            bundle, user_message, relapse_context, active_lens, free_mode
        )

    async def compose_checkin_summary(
        self, checkin_data: dict[str, Any], averages: dict[str, float | None]
    ) -> str:
        prompt = f"""Kullanıcı için sıcak bir günlük check-in yanıtı oluştur.
Bugünkü veriler: {checkin_data}
7 günlük ortalamalar: {averages}
Format: kabul + bir gözlem + bir mikro eylem. 100 kelimenin altında.
Yanıtı Türkçe yaz."""
        return await self._mini_chat(prompt)

    async def _mini_chat(self, prompt: str, max_tokens: int = 200) -> str:
        from app.ai.openai_client import get_openai_client

        return await get_openai_client().chat(
            [{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=max_tokens,
        )
