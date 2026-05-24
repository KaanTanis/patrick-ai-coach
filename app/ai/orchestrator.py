import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context.bundle import ContextBuilder
from app.ai.memory.extractor import MemoryExtractor
from app.ai.memory.profile_updater import ProfileUpdater
from app.ai.behavioral.relapse import RelapseRecovery, detect_relapse_intent
from app.ai.openai_client import get_openai_client
from app.ai.prompt_composer import PromptComposer
from app.repositories import ConversationRepository, UserRepository
from app.schemas.models import OrchestratorResponse
from app.services.chat_session import get_or_create_session_id, touch_session

logger = structlog.get_logger()


class AIOrchestrator:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.conversations = ConversationRepository(session)
        self.context = ContextBuilder(session)
        self.prompts = PromptComposer(session)
        self.relapse = RelapseRecovery(session)

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

        if intent == "relapse" or detect_relapse_intent(message):
            response_text = await self.relapse.handle(user.id, message)
            await self.conversations.add_message(user.id, session_id, "user", message)
            await self.conversations.add_message(user.id, session_id, "assistant", response_text)
            await touch_session(telegram_id, session_id)
            await self._queue_memory_extraction(user.id, message, response_text)
            await self._queue_profile_update(user.id)
            return OrchestratorResponse(text=response_text, session_id=session_id, intent="relapse")

        bundle = await self.context.build(
            user.id, query=message, intent=intent, session_id=session_id
        )
        messages = await self.prompts.compose_from_bundle(bundle, user_message=message)

        client = get_openai_client()
        response_text = await client.chat(messages, model="gpt-4o")

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
            from arq import create_pool
            from arq.connections import RedisSettings

            from app.config import get_settings

            redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
            pool = await create_pool(redis_settings)
            await pool.enqueue_job(
                "extract_memories_task",
                user_id,
                user_message,
                assistant_response,
            )
            await pool.close()
        except Exception as exc:
            logger.warning("orchestrator.queue_failed", error=str(exc))
            extractor = MemoryExtractor(self.session)
            await extractor.extract_and_store(user_id, user_message, assistant_response)

    async def _queue_profile_update(self, user_id: int) -> None:
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            from app.config import get_settings

            redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
            pool = await create_pool(redis_settings)
            await pool.enqueue_job("update_user_profile_task", user_id)
            await pool.close()
        except Exception as exc:
            logger.warning("orchestrator.profile_queue_failed", error=str(exc))
            updater = ProfileUpdater(self.session)
            await updater.update(user_id)
