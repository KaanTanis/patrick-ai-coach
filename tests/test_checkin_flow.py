from app.bot.handlers.checkin import SKIP_TEXTS


def test_skip_texts_includes_turkish():
    assert "atla" in SKIP_TEXTS
    assert "/atla" in SKIP_TEXTS
    assert "/skip" in SKIP_TEXTS


def test_checkin_handler_has_adaptive_state():
    from app.bot.handlers import checkin

    assert hasattr(checkin, "_start_checkin")
    assert hasattr(checkin, "PARTIAL_ACK")


def test_food_handler_fsm_guard():
    import inspect

    from app.bot.handlers import food

    source = inspect.getsource(food.handle_food_photo)
    assert "StateFilter(None)" in source
    assert "food_photo_during_fsm" in inspect.getsource(food)
