from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.retriever import MemoryRetriever
from app.ai.openai_client import get_openai_client
from app.ai.philosophy.helpers import format_philosophy_slice
from app.config import get_settings
from app.models import CheckIn, Conversation, Memory, User
from app.repositories import (
    CheckInRepository,
    ConversationRepository,
    MealRepository,
    MemoryRepository,
    UserRepository,
)
from app.repositories.philosophy import DreamRepository, ShadowRepository, ThoughtRepository

settings = get_settings()


@dataclass
class ContextBundle:
    user: User
    profile_summary: str
    schedule: dict[str, Any]
    local_time: str
    time_of_day: str
    memories: list[Memory] = field(default_factory=list)
    episodic_summaries: list[str] = field(default_factory=list)
    checkin_snapshot: str = ""
    today_meals_text: str = ""
    philosophy_snapshot: str = ""
    recent_history: list[dict[str, str]] = field(default_factory=list)
    today_meal_stats: dict[str, Any] = field(default_factory=dict)


class ContextBuilder:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.memories = MemoryRepository(session)
        self.check_ins = CheckInRepository(session)
        self.conversations = ConversationRepository(session)
        self.meals = MealRepository(session)
        self.retriever = MemoryRetriever(session)
        self.dreams = DreamRepository(session)
        self.shadows = ShadowRepository(session)
        self.thoughts = ThoughtRepository(session)

    async def build(
        self,
        user_id: int,
        query: str = "",
        intent: str = "free_chat",
        session_id: str | None = None,
        include_meals: bool = True,
    ) -> ContextBundle:
        user = await self.users.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        meal_stats = await self.meals.get_today_stats(user_id, user.timezone)
        ranked = await self.retriever.retrieve(user_id, query, intent)
        limit = settings.memory_retrieval_limit
        memories = ranked[:limit]

        episodes = await self.memories.get_recent_episodes(
            user_id, days=settings.episodic_days, limit=5
        )
        episodic_summaries = [
            f"{e.created_at.strftime('%d %b')}: {e.content}" for e in episodes
        ]

        checkins = await self.check_ins.get_recent(user_id, days=7)
        checkin_snapshot = self._format_checkins(checkins)

        history_msgs = await self.conversations.get_recent(
            user_id, session_id=session_id, limit=50
        )
        if not history_msgs:
            history_msgs = await self.conversations.get_recent(user_id, limit=50)
        recent_history = self._trim_history_to_budget(history_msgs)

        today_meals_text = ""
        if include_meals:
            today_meals_text = self._format_meals(meal_stats)

        dreams = await self.dreams.get_recent(user_id, days=30, limit=3)
        shadows = await self.shadows.get_recent(user_id, days=30, limit=3)
        thoughts = await self.thoughts.get_recent(user_id, days=30, limit=3)
        philosophy_snapshot = format_philosophy_slice(dreams, shadows, thoughts)

        return ContextBundle(
            user=user,
            profile_summary=user.context_summary or "Henüz profil özeti oluşturulmadı.",
            schedule=user.schedule or {},
            local_time=meal_stats["local_time"],
            time_of_day=meal_stats["time_of_day"],
            memories=memories,
            episodic_summaries=episodic_summaries,
            checkin_snapshot=checkin_snapshot,
            today_meals_text=today_meals_text,
            philosophy_snapshot=philosophy_snapshot,
            recent_history=recent_history,
            today_meal_stats=meal_stats,
        )

    def profile_gaps(self, bundle: ContextBundle) -> list[str]:
        gaps: list[str] = []
        if not bundle.user.context_summary or "Henüz profil" in bundle.profile_summary:
            gaps.append("hedefler ve öncelikler")
        if not bundle.schedule:
            gaps.append("uyku ve çalışma ritmi")
        if "Son check-in kaydı yok" in bundle.checkin_snapshot:
            gaps.append("günlük enerji ve ruh hali")
        if not bundle.philosophy_snapshot or "Henüz felsefi" in bundle.philosophy_snapshot:
            gaps.append("son günlerdeki iç deneyimler")
        return gaps[:3]

    def _format_checkins(self, checkins: list[CheckIn]) -> str:
        if not checkins:
            return "Son check-in kaydı yok."
        lines = []
        for c in checkins[:7]:
            lines.append(
                f"- {c.date}: ruh_hali={c.mood}, uyku={c.sleep_quality}, enerji={c.energy}, "
                f"enerji={c.energy}, stres={c.stress}, motivasyon={c.motivation}"
            )
        return "\n".join(lines)

    def _format_meals(self, stats: dict[str, Any]) -> str:
        if stats["count"] == 0:
            return "Bugün henüz kayıtlı öğün yok."
        lines = [
            f"Bugün {stats['count']} öğün, toplam ~{stats['total_calories']} kcal",
        ]
        for m in stats["meals"]:
            lines.append(f"- {m['time']}: ~{m['calories']} kcal")
        return "\n".join(lines)

    def _trim_history_to_budget(self, messages: list[Conversation]) -> list[dict[str, str]]:
        client = get_openai_client()
        budget = settings.chat_history_token_budget
        result: list[dict[str, str]] = []
        total = 0
        for msg in reversed(messages):
            tokens = client.count_tokens(msg.content)
            if total + tokens > budget:
                break
            result.insert(0, {"role": msg.role, "content": msg.content})
            total += tokens
        return result

    def format_memories(self, memories: list[Memory]) -> str:
        if not memories:
            return "Henüz kayıtlı hafıza yok."
        return "\n".join(f"- [{m.memory_type}] {m.content}" for m in memories)

    def format_episodes(self, episodes: list[str]) -> str:
        if not episodes:
            return "Henüz episodik özet yok."
        return "\n".join(f"- {e}" for e in episodes)
