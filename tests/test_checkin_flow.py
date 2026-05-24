from app.bot.handlers.checkin import SKIP_TEXTS


def test_skip_texts_includes_turkish():
    assert "atla" in SKIP_TEXTS
    assert "/atla" in SKIP_TEXTS
    assert "/skip" in SKIP_TEXTS


def test_chat_handler_has_state_filter():
    import inspect

    from app.bot.handlers import chat

    source = inspect.getsource(chat.free_chat)
    assert "StateFilter(None)" in source


def test_food_handler_fsm_guard():
    import inspect

    from app.bot.handlers import food

    source = inspect.getsource(food.handle_food_photo)
    assert "StateFilter(None)" in source
    assert "food_photo_during_fsm" in inspect.getsource(food)
