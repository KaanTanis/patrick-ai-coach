from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select

from app.ai.behavioral.insights import InsightGenerator
from app.ai.memory.extractor import MemoryExtractor
from app.ai.memory.summarizer import SessionSummarizer
from app.config import get_settings
from app.db import async_session_factory
from app.jobs.scheduler import build_cron_jobs
from app.models import User
from app.repositories import ConversationRepository, MemoryRepository, UserRepository

logger = structlog.get_logger()
settings = get_settings()


async def extract_memories_task(ctx: dict, user_id: int, user_message: str, assistant_response: str) -> None:
    async with async_session_factory() as session:
        extractor = MemoryExtractor(session)
        stored = await extractor.extract_and_store(user_id, user_message, assistant_response)
        await session.commit()
        logger.info("job.extract_memories", user_id=user_id, stored=stored)


async def summarize_stale_sessions(ctx: dict) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    async with async_session_factory() as session:
        conversations = ConversationRepository(session)
        summarizer = SessionSummarizer(session)
        session_ids = await conversations.get_stale_sessions(cutoff)
        for session_id in session_ids:
            await summarizer.summarize_session(session_id)
        await session.commit()
        logger.info("job.summarize_sessions", count=len(session_ids))


async def analyze_behavioral_patterns(ctx: dict) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(User))
        users = list(result.scalars().all())
        generator = InsightGenerator(session)
        for user in users:
            created = await generator.generate(user.id)
            logger.info("job.analyze_patterns", user_id=user.id, insights=created)
        await session.commit()


async def update_user_profile_task(ctx: dict, user_id: int) -> None:
    from app.ai.memory.profile_updater import ProfileUpdater

    async with async_session_factory() as session:
        updater = ProfileUpdater(session)
        await updater.update(user_id)
        await session.commit()
        logger.info("job.profile_updated", user_id=user_id)


async def adaptive_outreach_task(ctx: dict) -> None:
    from app.ai.proactive.coach import ProactiveCoach

    async with async_session_factory() as session:
        result = await session.execute(select(User))
        users = list(result.scalars().all())
        coach = ProactiveCoach(session)
        sent = 0
        for user in users:
            try:
                if await coach.process_user(user):
                    sent += 1
            except Exception as exc:
                logger.warning("job.outreach_failed", user_id=user.id, error=str(exc))
        await session.commit()
        logger.info("job.adaptive_outreach", sent=sent, total=len(users))


async def decay_memory_importance(ctx: dict) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(User))
        users = list(result.scalars().all())
        repo = MemoryRepository(session)
        for user in users:
            await repo.decay_importance(user.id)
        await session.commit()


async def generate_weekly_reflection(ctx: dict) -> None:
    from aiogram import Bot

    from app.ai.openai_client import get_openai_client
    from app.repositories import CheckInRepository, InsightRepository

    bot = Bot(token=settings.telegram_bot_token)
    async with async_session_factory() as session:
        result = await session.execute(select(User))
        users = list(result.scalars().all())
        for user in users:
            checkins = CheckInRepository(session)
            insights = InsightRepository(session)
            recent = await checkins.get_recent(user.id, days=7)
            active_insights = await insights.get_active(user.id, limit=3)

            if not recent:
                continue

            summary_data = [
                f"date={c.date}, mood={c.mood}, energy={c.energy}, stress={c.stress}"
                for c in recent
            ]
            insight_data = [f"{i.title}: {i.body}" for i in active_insights]

            prompt = f"""Kişisel koçluk kullanıcısı için sıcak bir haftalık yansıma yaz.
Check-in'ler: {summary_data}
İçgörüler: {insight_data}
200 kelimenin altında tut. Tutarlılığı kutla, bir kalıp not et, gelecek hafta için bir odak öner.
Türkçe yaz."""

            reflection = await get_openai_client().chat(
                [{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                max_tokens=300,
            )

            try:
                await bot.send_message(user.telegram_id, f"Haftalık yansıma\n\n{reflection}")
            except Exception as exc:
                logger.warning("job.reflection_failed", user_id=user.id, error=str(exc))

            from app.ai.openai_client import get_openai_client
            from app.models import MemorySource, MemoryType
            from app.repositories import MemoryRepository

            mem_repo = MemoryRepository(session)
            embedding = await get_openai_client().embed(reflection)
            await mem_repo.create(
                user_id=user.id,
                memory_type=MemoryType.EPISODE,
                content=reflection,
                importance=0.8,
                source=MemorySource.ANALYSIS,
                metadata={"type": "weekly_reflection"},
                embedding=embedding,
            )
        await session.commit()
    await bot.session.close()


async def cleanup_old_conversations(ctx: dict) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    async with async_session_factory() as session:
        conversations = ConversationRepository(session)
        deleted = await conversations.delete_older_than(cutoff)
        await session.commit()
        logger.info("job.cleanup_conversations", deleted=deleted)


async def consolidate_memories_task(ctx: dict) -> None:
    from sqlalchemy import delete

    from app.ai.memory.profile_updater import ProfileUpdater
    from app.ai.memory.ranker import cosine_similarity
    from app.models import Memory

    async with async_session_factory() as session:
        result = await session.execute(select(User))
        users = list(result.scalars().all())
        repo = MemoryRepository(session)
        updater = ProfileUpdater(session)
        merged_total = 0

        for user in users:
            memories = await repo.get_with_embeddings(user.id)
            to_delete: set[int] = set()

            for i, m1 in enumerate(memories):
                if m1.id in to_delete or m1.embedding is None:
                    continue
                emb1 = m1.embedding.embedding
                for m2 in memories[i + 1 :]:
                    if m2.id in to_delete or m2.embedding is None:
                        continue
                    if m1.memory_type != m2.memory_type:
                        continue
                    sim = cosine_similarity(emb1, m2.embedding.embedding)
                    if sim >= 0.92:
                        if m1.importance >= m2.importance:
                            to_delete.add(m2.id)
                        else:
                            to_delete.add(m1.id)
                            break

            for memory_id in to_delete:
                await session.execute(delete(Memory).where(Memory.id == memory_id))
            merged_total += len(to_delete)

            try:
                await updater.update(user.id)
            except Exception as exc:
                logger.warning("job.consolidate_profile_failed", user_id=user.id, error=str(exc))

        await session.commit()
        logger.info("job.consolidate_memories", merged=merged_total, users=len(users))


class WorkerSettings:
    redis_settings = __import__("arq.connections", fromlist=["RedisSettings"]).RedisSettings.from_dsn(
        settings.redis_url
    )
    functions = [
        extract_memories_task,
        summarize_stale_sessions,
        analyze_behavioral_patterns,
        adaptive_outreach_task,
        update_user_profile_task,
        decay_memory_importance,
        generate_weekly_reflection,
        cleanup_old_conversations,
        consolidate_memories_task,
    ]
    cron_jobs = build_cron_jobs(
        {
            "summarize_stale_sessions": summarize_stale_sessions,
            "analyze_behavioral_patterns": analyze_behavioral_patterns,
            "adaptive_outreach_task": adaptive_outreach_task,
            "decay_memory_importance": decay_memory_importance,
            "generate_weekly_reflection": generate_weekly_reflection,
            "cleanup_old_conversations": cleanup_old_conversations,
            "consolidate_memories_task": consolidate_memories_task,
        }
    )
