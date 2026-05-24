from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.philosophy.helpers import (
    compute_stoic_consistency,
    detect_dichotomy_gaps,
    filter_archetype_episodes,
    format_philosophy_slice,
    format_shadow_context,
    parse_dream_metadata,
)


def test_compute_stoic_consistency():
    result = compute_stoic_consistency({"morning": 5, "evening": 4}, days=7)
    assert result["score"] == 64
    assert result["morning"] == 5
    assert result["evening"] == 4


def test_compute_stoic_consistency_caps_at_100():
    result = compute_stoic_consistency({"morning": 7, "evening": 7}, days=7)
    assert result["score"] == 100


def test_detect_dichotomy_gaps_empty_audit():
    ritual = MagicMock()
    ritual.logged_at = datetime(2026, 5, 20, tzinfo=timezone.utc)
    ritual.dichotomy_audit = ""
    gaps = detect_dichotomy_gaps([ritual])
    assert len(gaps) == 1
    assert "boş" in gaps[0]


def test_detect_dichotomy_gaps_control_phrase():
    ritual = MagicMock()
    ritual.logged_at = datetime(2026, 5, 20, tzinfo=timezone.utc)
    ritual.dichotomy_audit = "Kontrol edemedim, bıraktım"
    gaps = detect_dichotomy_gaps([ritual])
    assert "kontrol dışı" in gaps[0]


def test_parse_dream_metadata_valid_json():
    raw = '{"mood": "kaygılı", "symbols": ["su", "koridor"]}'
    result = parse_dream_metadata(raw)
    assert result["mood"] == "kaygılı"
    assert result["symbols"] == ["su", "koridor"]


def test_parse_dream_metadata_invalid_json():
    result = parse_dream_metadata("not json")
    assert result["mood"] is None
    assert result["symbols"] is None


def test_format_philosophy_slice_truncates():
    dream = MagicMock(content="a" * 100, mood="huzursuz")
    shadow = MagicMock(content="b" * 100)
    thought = MagicMock(automatic_thought="c" * 100, situation=None)
    text = format_philosophy_slice([dream], [shadow], [thought], max_chars=200)
    assert len(text) <= 200
    assert "Rüya" in text


def test_filter_archetype_episodes_skips_job_types():
    weekly = MagicMock(content="Haftalık", metadata={"type": "weekly_reflection"})
    monthly = MagicMock(content="Aylık", metadata={"type": "monthly_archetype"})
    normal = MagicMock(content="Gerçek episod", metadata={"type": "session"})
    result = filter_archetype_episodes([weekly, monthly, normal])
    assert result == ["Gerçek episod"]


def test_format_shadow_context_includes_checkins():
    checkin = MagicMock(date=date(2026, 5, 20), mood=6, stress=7)
    text = format_shadow_context([checkin], [], [])
    assert "ruh_hali=6" in text
    assert "stres=7" in text


@pytest.mark.asyncio
async def test_deep_analyzer_rate_limit_blocks():
    from app.ai.analysis.deep_analyzer import DeepAnalyzer

    session = AsyncMock()
    analyzer = DeepAnalyzer(session)
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=3)
    redis.expire = AsyncMock()

    with patch("app.ai.analysis.deep_analyzer.get_redis", AsyncMock(return_value=redis)):
        result = await analyzer.analyze(1, lens="all", days=7)

    assert "limit" in result.lower()


@pytest.mark.asyncio
async def test_deep_analyzer_stoic_metrics_in_context():
    from app.ai.analysis.deep_analyzer import DeepAnalyzer

    session = AsyncMock()
    analyzer = DeepAnalyzer(session)
    analyzer.context.build = AsyncMock(return_value=MagicMock(
        profile_summary="profil", checkin_snapshot="checkins"
    ))
    analyzer.dreams.get_recent = AsyncMock(return_value=[])
    analyzer.shadows.get_recent = AsyncMock(return_value=[])
    analyzer.thoughts.get_recent = AsyncMock(return_value=[])
    analyzer.stoic.get_recent = AsyncMock(return_value=[])
    analyzer.emotions.get_recent = AsyncMock(return_value=[])
    analyzer.check_ins.get_recent = AsyncMock(return_value=[])
    analyzer.stoic.count_recent_by_type = AsyncMock(return_value={"morning": 3, "evening": 2})

    context = await analyzer._gather_context(1, 7, lens="stoic")
    assert "Stoic tutarlılık skoru" in context
    assert "3 sabah" in context
