import json
from typing import Any

from app.models import CheckIn, StoicRitual


def compute_stoic_consistency(ritual_counts: dict[str, int], days: int = 7) -> dict[str, Any]:
    morning = ritual_counts.get("morning", 0)
    evening = ritual_counts.get("evening", 0)
    max_possible = max(days * 2, 1)
    score = min(100, int((morning + evening) / max_possible * 100))
    return {
        "score": score,
        "morning": morning,
        "evening": evening,
        "days": days,
    }


def detect_dichotomy_gaps(evening_rituals: list[StoicRitual]) -> list[str]:
    gaps: list[str] = []
    for ritual in evening_rituals:
        audit = (ritual.dichotomy_audit or "").strip()
        if not audit:
            gaps.append(f"{ritual.logged_at.date()}: dichotomy audit boş")
            continue
        lower = audit.lower()
        if any(phrase in lower for phrase in ("kontrol edemedim", "elimde değildi", "yapamadım")):
            gaps.append(f"{ritual.logged_at.date()}: kontrol dışı alan not edildi")
    return gaps[:5]


def format_checkin_summary(checkins: list[CheckIn], limit: int = 7) -> str:
    if not checkins:
        return "Son check-in kaydı yok."
    lines = []
    for c in checkins[:limit]:
        lines.append(
            f"- {c.date}: ruh_hali={c.mood}, stres={c.stress}"
        )
    return "\n".join(lines)


def format_shadow_context(
    checkins: list[CheckIn],
    recent_setbacks: list,
    recent_shadows: list,
) -> str:
    parts = [f"Son check-in'ler:\n{format_checkin_summary(checkins)}"]
    if recent_setbacks:
        latest = recent_setbacks[0]
        created = getattr(latest, "created_at", None)
        date_str = created.date() if created else "?"
        parts.append(f"Son gerileme: {date_str}, not={latest.content[:100]}")
    if recent_shadows:
        shadow_lines = [f"- {s.content[:100]}" for s in recent_shadows[:2]]
        parts.append("Son gölge notları:\n" + "\n".join(shadow_lines))
    return "\n\n".join(parts)


def parse_dream_metadata(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
        mood = str(data.get("mood", "")).strip() or None
        symbols = data.get("symbols") or []
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(",") if s.strip()]
        symbols = [str(s).strip() for s in symbols if str(s).strip()][:10]
        return {"mood": mood, "symbols": symbols or None}
    except (json.JSONDecodeError, TypeError):
        return {"mood": None, "symbols": None}


def format_philosophy_slice(
    dreams: list,
    shadows: list,
    thoughts: list,
    max_chars: int = 200,
) -> str:
    lines: list[str] = []
    for d in dreams[:3]:
        mood = f" ({d.mood})" if getattr(d, "mood", None) else ""
        lines.append(f"Rüya{mood}: {d.content[:60]}")
    for s in shadows[:3]:
        lines.append(f"Gölge: {s.content[:60]}")
    for t in thoughts[:3]:
        thought = t.automatic_thought or t.situation or ""
        if thought:
            lines.append(f"Düşünce: {thought[:60]}")
    text = "\n".join(lines) if lines else "Henüz felsefi kayıt yok."
    return text[:max_chars]


def filter_archetype_episodes(episodes: list) -> list[str]:
    skip_types = {"weekly_reflection", "monthly_archetype"}
    result: list[str] = []
    for episode in episodes:
        meta = episode.metadata or {}
        if meta.get("type") in skip_types:
            continue
        result.append(episode.content[:150])
    return result[:10]
