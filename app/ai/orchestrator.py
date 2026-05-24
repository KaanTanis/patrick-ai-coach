import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.behavioral.relapse import RelapseRecovery, detect_relapse_intent
from app.ai.model_router import pick_chat_model
from app.ai.memory.extractor import MemoryExtractor
from app.ai.memory.profile_updater import ProfileUpdater
from app.ai.context.bundle import ContextBuilder
from app.ai.openai_client import CircuitOpenError, get_openai_client
from app.ai.prompt_composer import PromptComposer
from app.infra.redis import enqueue_job
from app.repositories import ConversationRepository, UserRepository
from app.schemas.models import OrchestratorResponse
from app.services.chat_session import get_or_create_session_id, touch_session
from app.services.lens import clear_lens, get_lens
from app.services.preferences import PreferencesService

logger = structlog.get_logger()


class AIOrchestrator:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.conversations = ConversationRepository(session)
        self.context = ContextBuilder(session)
        self.prompts = PromptComposer(session)
        self.relapse = RelapseRecovery(session)
        self.preferences = PreferencesService(session)

    async def orchestrate(
        self,
        telegram_id: int,
        message: str,
        intent: str = "free_chat",
        session_id: str | None = None,
        user_name: str | None = None,
    ) -> OrchestratorResponse:
        user = await self.users.get_or_create(telegram_id, name=user_name)
        session_id = session_id or await get_or_create_session_id(telegram_id)

        crisis = self.prompts.check_crisis(message)
        if crisis:
            return OrchestratorResponse(text=crisis, session_id=session_id, intent="crisis")

        if intent == "relapse" or detect_relapse_intent(message):
            response_text = await self.relapse.handle(user.id, message, user.personality_key)
            await self.conversations.add_message(user.id, session_id, "user", message)
            await self.conversations.add_message(user.id, session_id, "assistant", response_text)
            await touch_session(telegram_id, session_id)
            await self._queue_memory_extraction(user.id, message, response_text)
            await self._queue_profile_update(user.id)
            return OrchestratorResponse(text=response_text, session_id=session_id, intent="relapse")

        active_lens = await get_lens(telegram_id)
        if active_lens:
            await clear_lens(telegram_id)

        free_mode = await self.preferences.is_free_mode(user.id)
        bundle = await self.context.build(
            user.id, query=message, intent=intent, session_id=session_id
        )
        messages = await self.prompts.compose_from_bundle(
            bundle, user_message=message, active_lens=active_lens, free_mode=free_mode
        )
        model = pick_chat_model(message, intent)
        max_tokens = 1200 if free_mode else 800

        client = get_openai_client()
        try:
            response_text = await client.chat(messages, model=model, max_tokens=max_tokens)
        except CircuitOpenError as exc:
            response_text = str(exc)

        await self.conversations.add_message(user.id, session_id, "user", message)
        await self.conversations.add_message(
            user.id,
            session_id,
            "assistant",
            response_text,
            token_count=client.count_tokens(response_text),
        )
        await touch_session(telegram_id, session_id)
        await self._queue_memory_extraction(user.id, message, response_text)
        await self._queue_profile_update(user.id)

        return OrchestratorResponse(text=response_text, session_id=session_id, intent=intent)

    async def _queue_memory_extraction(
        self, user_id: int, user_message: str, assistant_response: str
    ) -> None:
        try:
            await enqueue_job("extract_memories_task", user_id, user_message, assistant_response)
        except Exception as exc:
            logger.warning("orchestrator.queue_failed", error=str(exc))
            extractor = MemoryExtractor(self.session)
            await extractor.extract_and_store(user_id, user_message, assistant_response)

    async def _queue_profile_update(self, user_id: int) -> None:
        try:
            await enqueue_job("update_user_profile_task", user_id)
        except Exception as exc:
            logger.warning("orchestrator.profile_queue_failed", error=str(exc))
            updater = ProfileUpdater(self.session)
            await updater.update(user_id)
