"""Nutrition service: bridges profile data → Nutrition Engine → persisted targets.

Historical targets are never mutated; a new row is created and marked current.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import text

from ..db import db_conn, jdump, new_id
from ..engine.nutrition_engine import (
    DayType, EngineError, EngineInput, EngineResult, Goal, Sex, Sport, calculate_targets,
)
from ..safety.guardrails import adjust_goal_for_young_user, clamp_deficit_for_young_user
from .rules import get_nutrition_rules, get_safety_rules

REQUIRED_FIELDS = ("age", "sex", "height_cm", "weight_kg", "sport", "primary_goal", "activity_level")


def get_profile(user_id: str) -> dict:
    with db_conn() as conn:
        row = conn.execute(
            text("SELECT * FROM profiles WHERE user_id = :u"), {"u": user_id}
        ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return dict(row)


def compute_and_store_target(user_id: str, day_type: str = "training") -> dict:
    profile = get_profile(user_id)
    missing = [f for f in REQUIRED_FIELDS if profile.get(f) is None]
    if missing:
        raise HTTPException(status_code=422, detail={"code": "missing_data", "fields": missing})

    safety_rules = get_safety_rules()
    nutrition_rules = get_nutrition_rules()

    age = int(profile["age"])
    goal, safety_warnings = adjust_goal_for_young_user(age, profile["primary_goal"], safety_rules)
    if "under_min_age" in safety_warnings:
        raise HTTPException(status_code=422, detail={"code": "under_min_age"})

    try:
        inp = EngineInput(
            age=age,
            sex=Sex(profile["sex"]),
            height_cm=float(profile["height_cm"]),
            weight_kg=float(profile["weight_kg"]),
            sport=Sport(profile["sport"]),
            goal=Goal(goal),
            activity_level=profile["activity_level"],
            training_days_per_week=profile.get("training_days_per_week") or 0,
            training_duration_min=profile.get("training_duration_min") or 0,
            training_intensity=profile.get("training_intensity") or "moderate",
            matches_per_week=profile.get("matches_per_week") or 0,
            matches_replace_training_day=bool(profile.get("matches_replace_training_day", True)),
            day_type=DayType(day_type),
        )
        result = calculate_targets(inp, nutrition_rules)
    except EngineError as e:
        raise HTTPException(status_code=422, detail={"code": e.code, "message": e.message})
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "invalid_enum", "message": str(e)})

    # young-user deficit clamp (safety layer decides, engine stays pure)
    adj, clamp_warnings = clamp_deficit_for_young_user(age, result.adjustment_kcal, safety_rules)
    if clamp_warnings:
        delta = adj - result.adjustment_kcal
        result = EngineResult(
            bmr_kcal=result.bmr_kcal, tdee_kcal=result.tdee_kcal,
            target_kcal=result.target_kcal + delta,
            protein_g=result.protein_g, fat_g=result.fat_g,
            carbs_g=round(result.carbs_g + delta / 4.0),
            adjustment_kcal=adj, day_type=result.day_type,
            engine_version=result.engine_version,
            nutrition_rules_version=result.nutrition_rules_version,
            warnings=result.warnings + clamp_warnings,
        )

    all_warnings = list(result.warnings) + [w for w in safety_warnings if w != "under_min_age"]

    tid = new_id()
    with db_conn() as conn:
        conn.execute(text("UPDATE nutrition_targets SET is_current = FALSE WHERE user_id = :u"), {"u": user_id})
        conn.execute(
            text(
                "INSERT INTO nutrition_targets (id, user_id, is_current, bmr_kcal, tdee_kcal, target_kcal, "
                "protein_g, carbs_g, fat_g, adjustment_kcal, day_type, engine_version, "
                "nutrition_rules_version, safety_rules_version, inputs, warnings) VALUES "
                "(:id, :u, TRUE, :bmr, :tdee, :t, :p, :c, :f, :adj, :dt, :ev, :nv, :sv, "
                "CAST(:inputs AS jsonb), CAST(:warn AS jsonb))"
            ),
            {
                "id": tid, "u": user_id, "bmr": result.bmr_kcal, "tdee": result.tdee_kcal,
                "t": result.target_kcal, "p": result.protein_g, "c": result.carbs_g,
                "f": result.fat_g, "adj": result.adjustment_kcal, "dt": result.day_type,
                "ev": result.engine_version, "nv": result.nutrition_rules_version,
                "sv": safety_rules["version"],
                "inputs": jdump({
                    "age": age, "sex": profile["sex"], "height_cm": float(profile["height_cm"]),
                    "weight_kg": float(profile["weight_kg"]), "sport": profile["sport"],
                    "goal": goal, "activity_level": profile["activity_level"],
                }),
                "warn": jdump(all_warnings),
            },
        )
    return {
        "id": tid, "bmr_kcal": result.bmr_kcal, "tdee_kcal": result.tdee_kcal,
        "target_kcal": result.target_kcal, "protein_g": result.protein_g,
        "carbs_g": result.carbs_g, "fat_g": result.fat_g,
        "adjustment_kcal": result.adjustment_kcal, "day_type": result.day_type,
        "engine_version": result.engine_version,
        "nutrition_rules_version": result.nutrition_rules_version,
        "warnings": all_warnings,
    }


def get_current_target(user_id: str) -> dict | None:
    with db_conn() as conn:
        row = conn.execute(
            text("SELECT * FROM nutrition_targets WHERE user_id = :u AND is_current LIMIT 1"), {"u": user_id}
        ).mappings().fetchone()
    return dict(row) if row else None
