import json
import re

from app.config import get_settings
from app.schemas.models import FoodAnalysisResult

settings = get_settings()

CONFIDENCE_TR = {"low": "düşük", "medium": "orta", "high": "yüksek"}


def strip_json_markdown(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_food_response(raw: str) -> FoodAnalysisResult | None:
    cleaned = strip_json_markdown(raw)
    try:
        data = json.loads(cleaned)
        return FoodAnalysisResult.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def format_food_response(
    result: FoodAnalysisResult,
    *,
    local_time: str,
    time_of_day: str,
    meal_count: int,
    total_calories: int,
    should_nudge_enough: bool,
) -> str:
    confidence = CONFIDENCE_TR.get(result.confidence.lower(), result.confidence)
    header = f"🍽 {result.portion_description}"
    macros = (
        f"~{result.estimated_calories} kcal · "
        f"P {result.protein_g:.0g} · K {result.carbs_g:.0g} · Y {result.fat_g:.0g}"
    )
    meta = f"güven: {confidence}"

    time_line = f"🕐 Saat {local_time.split(' ')[-1] if ' ' in local_time else local_time} — {time_of_day}."
    if meal_count > 0:
        time_line += f" Bugün {meal_count + 1}. öğünün"
        if total_calories > 0:
            projected = total_calories + result.estimated_calories
            time_line += f" (kayıtlı ~{total_calories} kcal, bu öğünle ~{projected} kcal)."
        time_line += "."
    else:
        time_line += " Bugünkü ilk öğünün."

    parts = [header, macros, meta, "", time_line]

    if result.conversational_response.strip():
        parts.extend(["", result.conversational_response.strip()])
    elif result.healthier_swap.strip():
        parts.extend(["", f"💡 {result.healthier_swap.strip()}"])

    if should_nudge_enough:
        parts.extend([
            "",
            "Bugün oldukça dolu bir gün — bu öğünü paylaşmak sorun değil; "
            "akşam hafif kalmak veya atlamak da iyi bir seçenek.",
        ])

    return "\n".join(parts)
