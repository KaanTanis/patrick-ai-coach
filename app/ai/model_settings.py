"""OpenAI model names — configure via .env (OPENAI_CHAT_MODEL, etc.)."""

from app.config import get_settings


def chat_model() -> str:
    """Primary model: coaching, setbacks, deep analysis, long chat."""
    return get_settings().openai_chat_model


def fast_model() -> str:
    """Lightweight model: nudges, extraction, summaries, short chat."""
    return get_settings().openai_fast_model


def vision_model() -> str:
    """Vision-capable model for food photo analysis."""
    return get_settings().openai_vision_model


def embedding_model() -> str:
    """Embedding model for memory retrieval."""
    return get_settings().openai_embedding_model
