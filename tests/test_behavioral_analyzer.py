from app.ai.behavioral.analyzer import _avg


def test_avg_filters_none():
    assert _avg([1, None, 3]) == 2.0


def test_avg_empty_returns_none():
    assert _avg([None, None]) is None
