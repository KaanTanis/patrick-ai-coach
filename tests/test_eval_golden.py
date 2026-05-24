import json
from pathlib import Path

from app.ai.model_router import pick_chat_model
from app.ai.model_settings import chat_model, fast_model
from app.ai.personalities.base import CORE_IDENTITY, RELAPSE_GUARDRAILS

FIXTURES = Path(__file__).parent / "eval" / "golden_prompts.json"

TIER_MODEL = {
    "chat": chat_model,
    "fast": fast_model,
}


def test_golden_prompts_model_routing():
    cases = json.loads(FIXTURES.read_text())
    for case in cases:
        model = pick_chat_model(case["user_message"], case["intent"])
        expected = TIER_MODEL[case["expected_tier"]]()
        assert model == expected, case["id"]


def test_core_identity_has_memory_rules():
    assert "Bellek kullanımı" in CORE_IDENTITY
    assert "Türkçe" in CORE_IDENTITY


def test_relapse_guardrails_present():
    assert "gerileme" in RELAPSE_GUARDRAILS.lower()


def test_golden_system_prompt_keywords():
    cases = json.loads(FIXTURES.read_text())
    combined = CORE_IDENTITY + RELAPSE_GUARDRAILS
    for case in cases:
        for keyword in case.get("system_must_include", []):
            if keyword == "RELAPSE":
                assert "gerileme" in combined.lower()
            elif keyword == "episodik":
                assert "episodik" in combined.lower() or "Geçmişe" in combined
            else:
                assert keyword.lower() in combined.lower(), f"{case['id']}: {keyword}"
