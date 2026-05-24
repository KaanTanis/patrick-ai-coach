from app.ai.food.formatter import format_food_response, parse_food_response, strip_json_markdown
from app.schemas.models import FoodAnalysisResult


def test_strip_json_markdown():
    raw = '```json\n{"estimated_calories": 500}\n```'
    assert strip_json_markdown(raw).startswith("{")


def test_parse_food_response_valid():
    raw = """```json
{
  "estimated_calories": 520,
  "protein_g": 42,
  "carbs_g": 28,
  "fat_g": 22,
  "portion_description": "Izgara tavuk salata",
  "confidence": "medium",
  "healthier_swap": "Sos miktarını azalt",
  "conversational_response": "Güzel bir seçim."
}
```"""
    result = parse_food_response(raw)
    assert result is not None
    assert result.estimated_calories == 520
    assert result.portion_description == "Izgara tavuk salata"


def test_format_food_response_turkish():
    result = FoodAnalysisResult(
        estimated_calories=520,
        protein_g=42,
        carbs_g=28,
        fat_g=22,
        portion_description="Izgara tavuk salata",
        confidence="medium",
        healthier_swap="Sos azalt",
        conversational_response="Öğle için makul.",
    )
    text = format_food_response(
        result,
        local_time="2026-05-24 14:30",
        time_of_day="öğle",
        meal_count=2,
        total_calories=980,
        should_nudge_enough=False,
    )
    assert "Izgara tavuk salata" in text
    assert "520 kcal" in text
    assert "3. öğünün" in text
    assert "980" in text
    assert "{" not in text


def test_format_food_nudge_when_enough():
    result = FoodAnalysisResult(
        estimated_calories=600,
        protein_g=30,
        carbs_g=50,
        fat_g=20,
        portion_description="Köfte pilav",
        confidence="high",
        healthier_swap="",
        conversational_response="",
    )
    text = format_food_response(
        result,
        local_time="2026-05-24 22:00",
        time_of_day="gece",
        meal_count=4,
        total_calories=2100,
        should_nudge_enough=True,
    )
    assert "dolu bir gün" in text
