"""Safety layer tests — pure config-driven checks."""
import json
from pathlib import Path

from app.safety.guardrails import (
    adjust_goal_for_young_user, check_ai_output, check_user_message,
    clamp_deficit_for_young_user, validate_profile_measurements,
)

RULES = json.loads((Path(__file__).parent.parent / "config" / "safety_rules_v1.json").read_text())


def test_eating_disorder_blocked_arabic():
    r = check_user_message("أريد تجويع نفسي لأخسر وزن بسرعة", "ar", RULES)
    assert not r.allowed
    assert r.flag_type == "eating_disorder"
    assert "مختص" in r.scripted_response


def test_eating_disorder_blocked_english():
    r = check_user_message("I want to starve myself", "en", RULES)
    assert not r.allowed and r.flag_type == "eating_disorder"


def test_medical_blocked():
    r = check_user_message("What medication should I take for my thyroid?", "en", RULES)
    assert not r.allowed and r.flag_type == "medical"


def test_normal_message_allowed():
    r = check_user_message("ماذا آكل بعد التمرين؟", "ar", RULES)
    assert r.allowed


def test_ai_output_blocked():
    r = check_ai_output("You should just skip all meals tomorrow.", "en", RULES)
    assert not r.allowed
    assert r.scripted_response


def test_ai_output_allowed():
    r = check_ai_output("Have a balanced dinner with chicken and rice.", "en", RULES)
    assert r.allowed


def test_measurement_bounds():
    errs = validate_profile_measurements({"weight_kg": 500, "height_cm": 170}, RULES)
    assert errs == ["invalid_weight_kg"]
    assert validate_profile_measurements({"weight_kg": 80}, RULES) == []


def test_young_user_goal_replaced():
    goal, warnings = adjust_goal_for_young_user(16, "lose_weight", RULES)
    assert goal == "maintain"
    assert "young_user_goal_adjusted" in warnings


def test_adult_goal_untouched():
    goal, warnings = adjust_goal_for_young_user(25, "lose_weight", RULES)
    assert goal == "lose_weight" and warnings == []


def test_under_min_age():
    _, warnings = adjust_goal_for_young_user(11, "maintain", RULES)
    assert "under_min_age" in warnings


def test_young_user_deficit_clamped():
    adj, w = clamp_deficit_for_young_user(16, -500, RULES)
    assert adj == -250 and w == ["young_user_deficit_clamped"]
    adj2, w2 = clamp_deficit_for_young_user(30, -500, RULES)
    assert adj2 == -500 and w2 == []
