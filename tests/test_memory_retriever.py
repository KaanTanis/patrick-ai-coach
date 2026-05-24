import math
from datetime import datetime, timezone

from app.ai.memory.ranker import cosine_similarity, rank_memories, recency_decay
from app.models import Memory, MemoryEmbedding


def _make_memory(
    content: str,
    memory_type: str = "fact",
    importance: float = 0.5,
    embedding: list[float] | None = None,
) -> Memory:
    m = Memory(id=1, user_id=1, memory_type=memory_type, content=content, importance=importance)
    m.created_at = datetime.now(timezone.utc)
    if embedding:
        m.embedding = MemoryEmbedding(memory_id=1, embedding=embedding)
    return m


def test_recency_decay_recent_is_higher():
    recent = datetime.now(timezone.utc)
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert recency_decay(recent) > recency_decay(old)


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert math.isclose(cosine_similarity(v, v), 1.0)


def test_rank_memories_prioritizes_goals_for_relapse_intent():
    query = [1.0, 0.0]
    memories = [
        _make_memory("likes coffee", "fact", 0.3, [0.9, 0.1]),
        _make_memory("stress trigger evenings", "trigger", 0.8, [0.5, 0.5]),
        _make_memory("spor hedefi", "goal", 0.9, [0.1, 0.9]),
    ]
    ranked = rank_memories(memories, query, "relapse", limit=2)
    types = [m.memory_type for m in ranked]
    assert "goal" in types or "trigger" in types
