"""Select OpenAI chat model based on message complexity and intent."""

from app.ai.model_settings import chat_model, fast_model

SIMPLE_MAX_LEN = 80


def pick_chat_model(message: str, intent: str = "free_chat") -> str:
    if intent in {"setback", "relapse", "checkin", "deep"}:
        return chat_model()
    text = message.strip()
    if len(text) <= SIMPLE_MAX_LEN and "?" not in text and "—" not in text:
        return fast_model()
    return chat_model()
