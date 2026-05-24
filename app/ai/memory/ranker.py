import math
from datetime import datetime, timezone

from app.models import Memory, MemoryType


TYPE_BOOSTS: dict[str, dict[str, float]] = {
    "free_chat": {
        MemoryType.FACT: 0.1,
        MemoryType.TRIGGER: 0.15,
        MemoryType.PATTERN: 0.1,
        MemoryType.GOAL: 0.2,
        MemoryType.RELAPSE: 0.15,
        MemoryType.SCHEDULE: 0.2,
    },
    "relapse": {
        MemoryType.RELAPSE: 0.3,
        MemoryType.TRIGGER: 0.25,
        MemoryType.PATTERN: 0.15,
        MemoryType.GOAL: 0.1,
    },
    "checkin": {
        MemoryType.PATTERN: 0.25,
        MemoryType.FACT: 0.15,
        MemoryType.GOAL: 0.15,
    },
}


def recency_decay(created_at: datetime, half_life_days: float = 30.0) -> float:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - created_at).total_seconds() / 86400
    return math.exp(-0.693 * days / half_life_days)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_memories(
    memories: list[Memory],
    query_embedding: list[float],
    intent: str,
    limit: int = 12,
) -> list[Memory]:
    boosts = TYPE_BOOSTS.get(intent, TYPE_BOOSTS["free_chat"])
    scored: list[tuple[float, Memory]] = []

    for memory in memories:
        if memory.embedding is None:
            semantic = 0.0
        else:
            semantic = cosine_similarity(query_embedding, memory.embedding.embedding)

        recency = recency_decay(memory.created_at)
        importance = memory.importance
        type_boost = boosts.get(memory.memory_type, 0.05)

        score = 0.5 * semantic + 0.2 * recency + 0.2 * importance + 0.1 * type_boost
        scored.append((score, memory))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [memory for _, memory in scored[:limit]]
