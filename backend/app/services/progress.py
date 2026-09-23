"""Progress: morning weight logging, body-fat estimates, weekly review."""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import text

from ..db import db_conn, jdump, new_id
from ..engine.nutrition_engine import ENGINE_VERSION, EngineError, Sex, estimate_body_fat_us_navy
from ..safety.guardrails import validate_profile_measurements
from .meals import day_totals, list_meals_for_day
from .nutrition import get_current_target, get_profile
from .rules import get_safety_rules

MEASUREMENT_KINDS = ("weight", "waist", "neck", "arm", "hip", "height")


def log_measurement(user_id: str, kind: str, value: float, is_morning: bool = False,
                    note: str | None = None) -> dict:
    if kind not in MEASUREMENT_KINDS:
        raise HTTPException(status_code=422, detail={"code": "invalid_measurement_kind"})
    rules = get_safety_rules()
    key = "weight_kg" if kind == "weight" else f"{kind}_cm"
    errors = validate_profile_measurements({key: value}, rules) if key in (
        "weight_kg", "waist_cm", "neck_cm", "hip_cm", "arm_cm", "height_cm") else []
    if errors:
        raise HTTPException(status_code=422, detail={"code": errors[0]})
    mid = new_id()
    with db_conn() as conn:
        conn.execute(
            text("INSERT INTO body_measurements (id, user_id, kind, value_normalized, is_morning, note) "
                 "VALUES (:i, :u, :k, :v, :m, :n)"),
            {"i": mid, "u": user_id, "k": kind, "v": value, "m": is_morning, "n": note},
        )
        if kind == "weight":
            conn.execute(text("UPDATE profiles SET weight_kg = :v, updated_at = now() WHERE user_id = :u"),
                         {"v": value, "u": user_id})
    return {"id": mid, "kind": kind, "value": value, "is_morning": is_morning}


def get_measurements(user_id: str, kind: str, days: int = 90) -> list[dict]:
    with db_conn() as conn:
        rows = conn.execute(
            text("SELECT id, measured_at, value_normalized, is_morning FROM body_measurements "
                 "WHERE user_id = :u AND kind = :k AND measured_at >= now() - make_interval(days => :d) "
                 "ORDER BY measured_at"),
            {"u": user_id, "k": kind, "d": days},
        ).mappings().all()
    return [{"id": str(r["id"]), "measured_at": r["measured_at"].isoformat(),
             "value": float(r["value_normalized"]), "is_morning": r["is_morning"]} for r in rows]


def weight_summary(user_id: str) -> dict:
    """Weekly averages & trend — never judges progress from one day."""
    points = get_measurements(user_id, "weight", days=56)
    weeks: dict[str, list[float]] = {}
    for p in points:
        d = dt.date.fromisoformat(p["measured_at"][:10])
        week_start = d - dt.timedelta(days=d.weekday())
        weeks.setdefault(str(week_start), []).append(p["value"])
    weekly_avgs = [{"week_start": k, "avg_kg": round(sum(v) / len(v), 2), "count": len(v)}
                   for k, v in sorted(weeks.items())]
    trend = None
    if len(weekly_avgs) >= 2:
        trend = round(weekly_avgs[-1]["avg_kg"] - weekly_avgs[-2]["avg_kg"], 2)
    return {"points": points[-30:], "weekly_averages": weekly_avgs, "week_over_week_kg": trend}


def estimate_body_fat(user_id: str, waist_cm: float, neck_cm: float, hip_cm: float | None) -> dict:
    profile = get_profile(user_id)
    if not profile.get("sex") or not profile.get("height_cm"):
        raise HTTPException(status_code=422, detail={"code": "missing_data", "fields": ["sex", "height_cm"]})
    try:
        pct = estimate_body_fat_us_navy(
            Sex(profile["sex"]), float(profile["height_cm"]), waist_cm, neck_cm, hip_cm
        )
    except EngineError as e:
        raise HTTPException(status_code=422, detail={"code": e.code, "message": e.message})
    bid = new_id()
    inputs = {"waist_cm": waist_cm, "neck_cm": neck_cm, "hip_cm": hip_cm,
              "height_cm": float(profile["height_cm"]), "sex": profile["sex"]}
    with db_conn() as conn:
        conn.execute(
            text("INSERT INTO body_fat_estimates (id, user_id, method, body_fat_pct, inputs, engine_version) "
                 "VALUES (:i, :u, 'us_navy', :p, CAST(:inp AS jsonb), :v)"),
            {"i": bid, "u": user_id, "p": pct, "inp": jdump(inputs), "v": ENGINE_VERSION},
        )
    return {
        "id": bid, "method": "us_navy", "estimated_body_fat_pct": pct,
        "disclaimer": "This is an ESTIMATE based on circumference measurements, not a medical measurement.",
    }


def generate_weekly_review(user_id: str, week_start: dt.date | None = None) -> dict:
    """Deterministic weekly review. Target modifications must go through the
    nutrition endpoint (engine + safety) — this only reports and suggests."""
    today = dt.date.today()
    if week_start is None:
        week_start = today - dt.timedelta(days=today.weekday() + 7)  # last full week
    week_end = week_start + dt.timedelta(days=7)

    target = get_current_target(user_id)
    # gather week data
    daily = []
    for i in range(7):
        day = week_start + dt.timedelta(days=i)
        if day > today:
            break
        meals = list_meals_for_day(user_id, day)
        totals = day_totals(meals)
        daily.append({"date": str(day), "kcal": totals["kcal"], "protein_g": totals["protein_g"],
                      "meals_logged": len(meals)})

    with db_conn() as conn:
        weights = conn.execute(
            text("SELECT value_normalized FROM body_measurements WHERE user_id = :u AND kind = 'weight' "
                 "AND measured_at >= :s AND measured_at < :e"),
            {"u": user_id, "s": week_start, "e": week_end},
        ).scalars().all()
        prev_weights = conn.execute(
            text("SELECT value_normalized FROM body_measurements WHERE user_id = :u AND kind = 'weight' "
                 "AND measured_at >= :s AND measured_at < :e"),
            {"u": user_id, "s": week_start - dt.timedelta(days=7), "e": week_start},
        ).scalars().all()

    avg_weight = round(sum(float(w) for w in weights) / len(weights), 2) if weights else None
    prev_avg = round(sum(float(w) for w in prev_weights) / len(prev_weights), 2) if prev_weights else None
    trend = round(avg_weight - prev_avg, 2) if avg_weight is not None and prev_avg is not None else None

    days_logged = sum(1 for d in daily if d["meals_logged"] > 0)
    avg_kcal = round(sum(d["kcal"] for d in daily if d["meals_logged"] > 0) / max(1, days_logged), 0) if days_logged else None
    avg_protein = round(sum(d["protein_g"] for d in daily if d["meals_logged"] > 0) / max(1, days_logged), 0) if days_logged else None

    went_well, needs_attention, suggestions = [], [], []
    if days_logged >= 5:
        went_well.append("logging_consistency")
    elif days_logged >= 1:
        needs_attention.append("logging_consistency")
        suggestions.append("log_more_days")
    else:
        needs_attention.append("no_logging")
        suggestions.append("start_logging")
    if target and avg_protein is not None:
        if avg_protein >= 0.9 * target["protein_g"]:
            went_well.append("protein_intake")
        else:
            needs_attention.append("protein_intake")
            suggestions.append("increase_protein_foods")
    if trend is not None and target:
        adj = target["adjustment_kcal"]
        if adj < 0 and trend > 0.3:
            needs_attention.append("weight_not_decreasing")
            suggestions.append("review_targets_with_engine")
        elif adj > 0 and trend < -0.3:
            needs_attention.append("weight_not_increasing")
            suggestions.append("review_targets_with_engine")
        else:
            went_well.append("weight_trend_on_track")
    if len(weights) < 3:
        suggestions.append("weigh_more_mornings")

    data = {
        "week_start": str(week_start), "avg_weight_kg": avg_weight, "prev_avg_weight_kg": prev_avg,
        "weight_trend_kg": trend, "days_logged": days_logged, "avg_kcal": avg_kcal,
        "avg_protein_g": avg_protein, "daily": daily,
        "went_well": went_well, "needs_attention": needs_attention, "suggestions": suggestions,
    }
    with db_conn() as conn:
        conn.execute(
            text("INSERT INTO weekly_reviews (id, user_id, week_start, data) "
                 "VALUES (:i, :u, :w, CAST(:d AS jsonb)) "
                 "ON CONFLICT (user_id, week_start) DO UPDATE SET data = CAST(:d AS jsonb), generated_at = now()"),
            {"i": new_id(), "u": user_id, "w": week_start, "d": jdump(data)},
        )
    return data
