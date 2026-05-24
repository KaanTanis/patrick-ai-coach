from datetime import date, datetime
from zoneinfo import ZoneInfo


from app.ai.proactive.coach import evaluate_outreach, _in_sleep_window
from app.models import User


def _make_user(**kwargs) -> User:
    user = User(
        id=1,
        telegram_id=123,
        personality_key="companion",
        timezone="Europe/Istanbul",
    )
    for key, value in kwargs.items():
        setattr(user, key, value)
    return user


def test_evaluate_outreach_disabled(monkeypatch):
    from app.ai.proactive import coach as coach_module

    monkeypatch.setattr(coach_module.settings, "proactive_outreach_enabled", False)
    user = _make_user()
    decision = evaluate_outreach(user, has_checkin_today=False)
    assert decision.should_send is False


def test_evaluate_outreach_daily_limit():
    user = _make_user(
        nudges_today_date=date.today(),
        nudges_today_count=3,
    )
    decision = evaluate_outreach(user, has_checkin_today=False)
    assert decision.should_send is False
    assert decision.reason == "daily_limit"


def test_evaluate_outreach_missing_checkin(monkeypatch):
    from app.ai.proactive import coach as coach_module

    fixed_now = datetime(2026, 5, 24, 14, 0, tzinfo=ZoneInfo("Europe/Istanbul"))
    monkeypatch.setattr(coach_module, "_user_now", lambda _u: fixed_now)

    user = _make_user(nudges_today_count=0, nudges_today_date=None)
    decision = evaluate_outreach(user, has_checkin_today=False)
    assert decision.should_send is True
    assert decision.nudge_type == "report_request"


def test_evaluate_outreach_too_soon_after_last():
    now = datetime.now(ZoneInfo("Europe/Istanbul"))
    user = _make_user(
        last_proactive_at=now - __import__("datetime").timedelta(hours=1),
        nudges_today_count=1,
        nudges_today_date=date.today(),
    )
    decision = evaluate_outreach(user, has_checkin_today=True)
    assert decision.should_send is False
    assert decision.reason == "too_soon"


def test_in_sleep_window_overnight():
    user = _make_user(schedule={"sleep_window": "23:00-07:00"})
    now = datetime(2026, 5, 24, 2, 0, tzinfo=ZoneInfo("Europe/Istanbul"))
    assert _in_sleep_window(user, now) is True


def test_pre_shift_within_two_hours(monkeypatch):
    from app.ai.proactive import coach as coach_module

    fixed_now = datetime(2026, 5, 24, 21, 0, tzinfo=ZoneInfo("Europe/Istanbul"))
    monkeypatch.setattr(coach_module, "_user_now", lambda _u: fixed_now)

    user = _make_user(
        schedule={"next_shift_start": "23:00"},
        nudges_today_count=0,
    )
    decision = evaluate_outreach(user, has_checkin_today=True)
    assert decision.should_send is True
    assert decision.nudge_type == "pre_shift"
