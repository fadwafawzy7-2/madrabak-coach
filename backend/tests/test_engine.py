"""Nutrition Engine unit tests — pure, no DB/network."""
import json
from pathlib import Path

import pytest

from app.engine.nutrition_engine import (
    DayType, EngineError, EngineInput, Goal, Sex, Sport,
    calc_bmr, calc_tdee, calculate_targets, cm_to_inch, effective_training_days,
    estimate_body_fat_us_navy, inch_to_cm, kg_to_lb, lb_to_kg,
)

RULES = json.loads((Path(__file__).parent.parent / "config" / "nutrition_rules_v1.json").read_text())


def make_input(**kw):
    defaults = dict(
        age=30, sex=Sex.MALE, height_cm=178, weight_kg=80,
        sport=Sport.BODYBUILDING, goal=Goal.MAINTAIN, activity_level="light",
        training_days_per_week=4, training_duration_min=60, training_intensity="moderate",
    )
    defaults.update(kw)
    return EngineInput(**defaults)


# ---------------- BMR (Mifflin-St Jeor)

def test_bmr_male():
    # 10*80 + 6.25*178 - 5*30 + 5 = 800 + 1112.5 - 150 + 5 = 1767.5
    assert calc_bmr(Sex.MALE, 80, 178, 30) == pytest.approx(1767.5)


def test_bmr_female():
    # 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
    assert calc_bmr(Sex.FEMALE, 60, 165, 25) == pytest.approx(1345.25)


# ---------------- TDEE / activity model

def test_tdee_no_training_equals_bmr_times_factor():
    inp = make_input(training_days_per_week=0, training_duration_min=0)
    assert calc_tdee(inp, RULES) == pytest.approx(1767.5 * 1.375)


def test_tdee_adds_training_average():
    inp = make_input(training_days_per_week=4, training_duration_min=60, training_intensity="moderate")
    expected = 1767.5 * 1.375 + (6.0 * 60 * 4) / 7
    assert calc_tdee(inp, RULES) == pytest.approx(expected)


def test_invalid_activity_level():
    inp = make_input(activity_level="extreme")
    with pytest.raises(EngineError) as e:
        calc_tdee(inp, RULES)
    assert e.value.code == "invalid_activity_level"


# ---------------- football match logic

def test_match_replaces_training_day():
    eff, matches = effective_training_days(4, 2, matches_replace=True)
    assert eff == 2 and matches == 2


def test_match_does_not_replace():
    eff, matches = effective_training_days(4, 2, matches_replace=False)
    assert eff == 4 and matches == 2


def test_effective_days_never_negative():
    eff, matches = effective_training_days(1, 3, matches_replace=True)
    assert eff == 0 and matches == 3


def test_week_capped_at_seven():
    eff, matches = effective_training_days(7, 3, matches_replace=False)
    assert eff + matches <= 7 + 3  # matches counted separately, training capped
    assert eff == 4  # 7 - 3


def test_football_tdee_counts_match_kcal():
    inp = make_input(sport=Sport.FOOTBALL, training_days_per_week=3, matches_per_week=1,
                     matches_replace_training_day=True, training_duration_min=90,
                     training_intensity="high")
    base = 1767.5 * 1.375
    weekly = 8.0 * 90 * 2 + 700 * 1  # 2 effective training days + 1 match
    assert calc_tdee(inp, RULES) == pytest.approx(base + weekly / 7)


def test_non_football_ignores_matches():
    inp = make_input(sport=Sport.RUNNING, matches_per_week=2)
    inp2 = make_input(sport=Sport.RUNNING, matches_per_week=0)
    assert calc_tdee(inp, RULES) == pytest.approx(calc_tdee(inp2, RULES))


# ---------------- targets & macros

def test_maintain_target_equals_tdee():
    r = calculate_targets(make_input(goal=Goal.MAINTAIN), RULES)
    assert r.adjustment_kcal == 0
    assert r.target_kcal == r.tdee_kcal


def test_lose_weight_deficit():
    r = calculate_targets(make_input(goal=Goal.LOSE_WEIGHT), RULES)
    assert r.adjustment_kcal == -500
    assert r.target_kcal == r.tdee_kcal - 500


def test_macros_sum_to_target():
    r = calculate_targets(make_input(goal=Goal.LOSE_FAT), RULES)
    total = r.protein_g * 4 + r.carbs_g * 4 + r.fat_g * 9
    assert abs(total - r.target_kcal) < 30  # rounding tolerance


def test_protein_by_sport_and_direction():
    r = calculate_targets(make_input(goal=Goal.LOSE_FAT, sport=Sport.BODYBUILDING), RULES)
    assert r.protein_g == round(2.2 * 80)
    r2 = calculate_targets(make_input(goal=Goal.MAINTAIN, sport=Sport.NON_ATHLETE), RULES)
    assert r2.protein_g == round(1.2 * 80)


def test_fat_minimum_respected():
    r = calculate_targets(make_input(goal=Goal.LOSE_WEIGHT), RULES)
    assert r.fat_g >= round(0.6 * 80)


def test_min_calories_floor_female():
    inp = make_input(sex=Sex.FEMALE, weight_kg=48, height_cm=152, age=45,
                     activity_level="sedentary", training_days_per_week=0,
                     training_duration_min=0, goal=Goal.LOSE_WEIGHT, sport=Sport.NON_ATHLETE)
    r = calculate_targets(inp, RULES)
    assert r.target_kcal >= 1200
    assert "min_calories_floor_applied" in r.warnings


def test_constraint_conflict_raised():
    # tiny person, huge protein requirement relative to calories
    rules = json.loads(json.dumps(RULES))
    rules["protein_g_per_kg"]["bodybuilding"]["deficit"] = 6.0
    rules["min_calories"]["male"] = 800
    inp = make_input(weight_kg=60, height_cm=160, age=50, activity_level="sedentary",
                     training_days_per_week=0, training_duration_min=0, goal=Goal.LOSE_WEIGHT)
    with pytest.raises(EngineError) as e:
        calculate_targets(inp, rules)
    assert e.value.code == "constraint_conflict"


def test_results_are_versioned():
    r = calculate_targets(make_input(), RULES)
    assert r.engine_version.startswith("engine-")
    assert r.nutrition_rules_version == RULES["version"]


# ---------------- validation / missing data

@pytest.mark.parametrize("kw,code", [
    (dict(age=0), "invalid_age"),
    (dict(age=150), "invalid_age"),
    (dict(height_cm=30), "invalid_height"),
    (dict(weight_kg=10), "invalid_weight"),
    (dict(training_days_per_week=9), "invalid_training_days"),
    (dict(matches_per_week=-1), "invalid_matches"),
    (dict(training_duration_min=999), "invalid_training_duration"),
])
def test_input_validation(kw, code):
    with pytest.raises(EngineError) as e:
        calculate_targets(make_input(**kw), RULES)
    assert e.value.code == code


# ---------------- body fat (US Navy)

def test_body_fat_male_reasonable():
    pct = estimate_body_fat_us_navy(Sex.MALE, 178, 85, 38)
    assert 10 < pct < 30


def test_body_fat_female_requires_hip():
    with pytest.raises(EngineError) as e:
        estimate_body_fat_us_navy(Sex.FEMALE, 165, 70, 32)
    assert e.value.code == "missing_hip"


def test_body_fat_female_reasonable():
    pct = estimate_body_fat_us_navy(Sex.FEMALE, 165, 70, 32, hip_cm=95)
    assert 15 < pct < 40


def test_body_fat_invalid_waist_leq_neck_no_nan():
    with pytest.raises(EngineError) as e:
        estimate_body_fat_us_navy(Sex.MALE, 178, 40, 45)
    assert e.value.code in ("invalid_measurements", "invalid_waist")


def test_body_fat_out_of_range_measurement():
    with pytest.raises(EngineError):
        estimate_body_fat_us_navy(Sex.MALE, 178, 300, 38)


# ---------------- unit conversions

def test_unit_round_trips():
    assert lb_to_kg(kg_to_lb(80)) == pytest.approx(80)
    assert inch_to_cm(cm_to_inch(178)) == pytest.approx(178)
    assert kg_to_lb(100) == pytest.approx(220.46, abs=0.01)
    assert inch_to_cm(70) == pytest.approx(177.8, abs=0.01)
