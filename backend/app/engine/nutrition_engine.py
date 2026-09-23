"""Deterministic Nutrition Engine.

Source of truth for BMR, TDEE, calorie targets and macros.
- Pure functions. No AI. No network. No database.
- All tunable values come from a nutrition-rules config dict (versioned).
- Never silently changes historical targets: callers persist results with versions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

ENGINE_VERSION = "engine-1.0.0"


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


class Sport(str, Enum):
    BODYBUILDING = "bodybuilding"
    STRENGTH = "strength"
    CALISTHENICS = "calisthenics"
    RUNNING = "running"
    FOOTBALL = "football"
    NON_ATHLETE = "non_athlete"


class Goal(str, Enum):
    LOSE_WEIGHT = "lose_weight"
    LOSE_FAT = "lose_fat"
    MAINTAIN = "maintain"
    GAIN_WEIGHT = "gain_weight"
    GAIN_MUSCLE = "gain_muscle"
    RECOMPOSITION = "recomposition"
    INCREASE_STRENGTH = "increase_strength"
    ATHLETIC_PERFORMANCE = "athletic_performance"
    RUNNING_PERFORMANCE = "running_performance"
    CALISTHENICS_PERFORMANCE = "calisthenics_performance"


class DayType(str, Enum):
    TRAINING = "training"
    REST = "rest"
    MATCH = "match"


class EngineError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class EngineInput:
    age: int
    sex: Sex
    height_cm: float
    weight_kg: float
    sport: Sport
    goal: Goal
    activity_level: str            # daily NON-training activity: sedentary/light/moderate/high
    training_days_per_week: int = 0
    training_duration_min: int = 0
    training_intensity: str = "moderate"   # low/moderate/high
    matches_per_week: int = 0              # football only
    matches_replace_training_day: bool = True
    day_type: DayType = DayType.TRAINING


@dataclass(frozen=True)
class EngineResult:
    bmr_kcal: int
    tdee_kcal: int
    target_kcal: int
    protein_g: int
    fat_g: int
    carbs_g: int
    adjustment_kcal: int
    day_type: str
    engine_version: str
    nutrition_rules_version: str
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- validation

def _validate(inp: EngineInput) -> None:
    if inp.age <= 0 or inp.age > 120:
        raise EngineError("invalid_age", "Age out of accepted range")
    if not (50 <= inp.height_cm <= 280):
        raise EngineError("invalid_height", "Height (cm) out of accepted range")
    if not (20 <= inp.weight_kg <= 400):
        raise EngineError("invalid_weight", "Weight (kg) out of accepted range")
    if inp.training_days_per_week < 0 or inp.training_days_per_week > 7:
        raise EngineError("invalid_training_days", "Training days must be 0..7")
    if inp.matches_per_week < 0 or inp.matches_per_week > 7:
        raise EngineError("invalid_matches", "Matches must be 0..7")
    if inp.training_duration_min < 0 or inp.training_duration_min > 360:
        raise EngineError("invalid_training_duration", "Training duration must be 0..360 min")


# ---------------------------------------------------------------- BMR / TDEE

def calc_bmr(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """Mifflin-St Jeor."""
    base = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age
    return base + 5.0 if sex == Sex.MALE else base - 161.0


def effective_training_days(training_days: int, matches: int, matches_replace: bool) -> tuple[int, int]:
    """Returns (effective_training_days, match_days). Never negative.

    If matches_replace_training_day: a match consumes a training day; that
    session is NOT counted separately (no double counting).
    """
    match_days = max(0, matches)
    if matches_replace:
        eff_training = max(0, training_days - match_days)
    else:
        eff_training = max(0, training_days)
    # A week only has 7 days
    if eff_training + match_days > 7:
        eff_training = max(0, 7 - match_days)
    return eff_training, match_days


def calc_tdee(inp: EngineInput, rules: dict) -> float:
    """Daily-average TDEE.

    Model: daily activity factor covers NON-training life activity.
    Training sessions and football matches are added as weekly kcal
    averaged over 7 days — so a training session is never counted both
    inside the activity factor and as a session (no double counting).
    """
    bmr = calc_bmr(inp.sex, inp.weight_kg, inp.height_cm, inp.age)
    factors = rules["activity_factors"]
    if inp.activity_level not in factors:
        raise EngineError("invalid_activity_level", f"Unknown activity level {inp.activity_level}")
    base = bmr * factors[inp.activity_level]

    per_min = rules["training_session_kcal_per_min"]
    intensity = inp.training_intensity if inp.training_intensity in per_min else "moderate"
    session_kcal = per_min[intensity] * inp.training_duration_min

    eff_days, match_days = effective_training_days(
        inp.training_days_per_week,
        inp.matches_per_week if inp.sport == Sport.FOOTBALL else 0,
        inp.matches_replace_training_day,
    )
    weekly_training_kcal = session_kcal * eff_days
    weekly_match_kcal = rules["match_kcal"]["football"] * match_days if inp.sport == Sport.FOOTBALL else 0.0
    return base + (weekly_training_kcal + weekly_match_kcal) / 7.0


# ---------------------------------------------------------------- target & macros

_DEFICIT_GOALS = {Goal.LOSE_WEIGHT, Goal.LOSE_FAT, Goal.RECOMPOSITION, Goal.CALISTHENICS_PERFORMANCE}
_SURPLUS_GOALS = {Goal.GAIN_WEIGHT, Goal.GAIN_MUSCLE, Goal.INCREASE_STRENGTH}


def _goal_direction(adjustment: float) -> str:
    if adjustment < 0:
        return "deficit"
    if adjustment > 0:
        return "surplus"
    return "maintenance"


def calculate_targets(inp: EngineInput, rules: dict) -> EngineResult:
    """Full deterministic calculation. Raises EngineError('constraint_conflict', ...)
    when protein+fat minimums cannot fit in the calorie target — no secret fallbacks."""
    _validate(inp)
    warnings: list[str] = []

    bmr = calc_bmr(inp.sex, inp.weight_kg, inp.height_cm, inp.age)
    tdee = calc_tdee(inp, rules)

    adjustment = float(rules["goal_adjustment_kcal"][inp.goal.value])
    # clamp to configured limits
    deficit_limit = rules["deficit_limit_kcal"]
    surplus_limit = rules["surplus_limit_kcal"]
    if adjustment < -deficit_limit:
        adjustment = -deficit_limit
        warnings.append("deficit_clamped")
    if adjustment > surplus_limit:
        adjustment = surplus_limit
        warnings.append("surplus_clamped")

    target = tdee + adjustment

    min_cal = rules["min_calories"][inp.sex.value]
    if target < min_cal:
        target = float(min_cal)
        adjustment = target - tdee
        warnings.append("min_calories_floor_applied")

    # Day-type adaptation (football / endurance): match day keeps carbs high;
    # rest day removes the training addition. Simple MVP model.
    if inp.day_type == DayType.REST and inp.sport in (Sport.FOOTBALL, Sport.RUNNING):
        pass  # weekly-average model already smooths; kept simple deliberately

    kcal_per_g = rules["kcal_per_g"]
    direction = _goal_direction(adjustment)

    protein_per_kg = rules["protein_g_per_kg"][inp.sport.value][direction]
    protein_g = protein_per_kg * inp.weight_kg
    protein_kcal = protein_g * kcal_per_g["protein"]

    fat_min_g = rules["fat_g_per_kg_min"] * inp.weight_kg
    fat_default_g = (target * rules["fat_pct_of_calories_default"]) / kcal_per_g["fat"]
    fat_g = max(fat_min_g, fat_default_g)
    fat_kcal = fat_g * kcal_per_g["fat"]

    remaining = target - protein_kcal - fat_kcal
    if remaining < 0:
        # try reducing fat to its minimum before failing
        fat_g = fat_min_g
        fat_kcal = fat_g * kcal_per_g["fat"]
        remaining = target - protein_kcal - fat_kcal
        if remaining < 0:
            raise EngineError(
                "constraint_conflict",
                "Protein and minimum fat requirements exceed the calorie target",
            )
        warnings.append("fat_reduced_to_minimum")

    carbs_g = remaining / kcal_per_g["carbs"]

    carb_min_per_kg = rules["carb_g_per_kg_min"].get(inp.sport.value, rules["carb_g_per_kg_min"]["default"])
    if isinstance(carb_min_per_kg, (int, float)) and carbs_g < carb_min_per_kg * inp.weight_kg:
        warnings.append("carbs_below_sport_minimum")

    return EngineResult(
        bmr_kcal=round(bmr),
        tdee_kcal=round(tdee),
        target_kcal=round(target),
        protein_g=round(protein_g),
        fat_g=round(fat_g),
        carbs_g=round(carbs_g),
        adjustment_kcal=round(adjustment),
        day_type=inp.day_type.value,
        engine_version=ENGINE_VERSION,
        nutrition_rules_version=rules["version"],
        warnings=warnings,
    )


# ---------------------------------------------------------------- body fat (US Navy)

def estimate_body_fat_us_navy(
    sex: Sex, height_cm: float, waist_cm: float, neck_cm: float, hip_cm: float | None = None
) -> float:
    """US Navy circumference ESTIMATE of body-fat %. Not a medical measurement.

    Validates inputs before log10 so it can never return NaN.
    """
    if not (100 <= height_cm <= 250):
        raise EngineError("invalid_height", "Height out of range for body-fat estimate")
    if not (40 <= waist_cm <= 200):
        raise EngineError("invalid_waist", "Waist out of range")
    if not (20 <= neck_cm <= 80):
        raise EngineError("invalid_neck", "Neck out of range")

    if sex == Sex.MALE:
        if waist_cm - neck_cm <= 0:
            raise EngineError("invalid_measurements", "Waist must be greater than neck")
        bf = 495.0 / (1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)) - 450.0
    else:
        if hip_cm is None:
            raise EngineError("missing_hip", "Hip measurement is required for females")
        if not (50 <= hip_cm <= 200):
            raise EngineError("invalid_hip", "Hip out of range")
        if waist_cm + hip_cm - neck_cm <= 0:
            raise EngineError("invalid_measurements", "Waist + hip must be greater than neck")
        bf = 495.0 / (1.29579 - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm) + 0.22100 * math.log10(height_cm)) - 450.0

    if not (0 < bf < 75):
        raise EngineError("implausible_result", "Estimated body fat outside plausible range")
    return round(bf, 1)


# ---------------------------------------------------------------- unit conversion

LB_PER_KG = 2.2046226218
IN_PER_CM = 0.3937007874


def lb_to_kg(lb: float) -> float:
    return lb / LB_PER_KG


def kg_to_lb(kg: float) -> float:
    return kg * LB_PER_KG


def inch_to_cm(inch: float) -> float:
    return inch / IN_PER_CM


def cm_to_inch(cm: float) -> float:
    return cm * IN_PER_CM
