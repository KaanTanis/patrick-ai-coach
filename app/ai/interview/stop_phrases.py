STOP_PHRASES = {
    "bu kadar soru yeter",
    "yeter bu kadar",
    "tamam bu kadar",
    "bu kadar yeter",
    "soru yeter",
    "artık yeter",
    "yeterli bu kadar",
}


def is_stop_phrase(text: str) -> bool:
    lower = text.strip().lower()
    return any(phrase in lower for phrase in STOP_PHRASES)
