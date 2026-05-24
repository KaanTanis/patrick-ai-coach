"""Select OpenAI chat model based on message complexity and intent."""

SIMPLE_MAX_LEN = 80


def pick_chat_model(message: str, intent: str = "free_chat") -> str:
    if intent in {"relapse", "checkin", "deep"}:
        return "gpt-4o"
    text = message.strip()
    if len(text) <= SIMPLE_MAX_LEN and "?" not in text and "—" not in text:
        return "gpt-4o-mini"
    return "gpt-4o"
