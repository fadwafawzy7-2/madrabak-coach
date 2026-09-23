"""Meal logging service: text / photo-draft / manual entries."""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import text

from ..db import db_conn, new_id
from . import foods as food_svc

UNIT_TO_GRAMS = {
    # simple provisional unit conversions; per-food serving weights can be added later
    "g": 1.0,
    "kg": 1000.0,
    "cup": 200.0,
    "tbsp": 15.0,
    "tsp": 5.0,
    "piece": 100.0,
    "slice": 30.0,
    "serving": 150.0,
}


def to_grams(quantity: float, unit: str) -> float:
    factor = UNIT_TO_GRAMS.get(unit)
    if factor is None:
        raise HTTPException(status_code=422, detail={"code": "unknown_unit", "unit": unit})
    grams = quantity * factor
    if not (0 < grams <= 10000):
        raise HTTPException(status_code=422, detail={"code": "invalid_quantity"})
    return grams


def create_meal(user_id: str, meal_type: str, source: str, items: list[dict],
                status: str = "final", eaten_at: str | None = None, note: str | None = None) -> dict:
    if meal_type not in ("breakfast", "lunch", "dinner", "snack"):
        raise HTTPException(status_code=422, detail={"code": "invalid_meal_type"})
    if source not in ("text", "photo", "manual"):
        raise HTTPException(status_code=422, detail={"code": "invalid_source"})
    if not items:
        raise HTTPException(status_code=422, detail={"code": "empty_meal"})

    meal_id = new_id()
    resolved_items = []
    for it in items:
        food = None
        if it.get("food_id"):
            food = food_svc.get_food(it["food_id"])
            if not food:
                raise HTTPException(status_code=422, detail={"code": "food_not_found", "food_id": it["food_id"]})
        elif it.get("food_name"):
            food = food_svc.match_food_by_name(it["food_name"])
        if not food:
            raise HTTPException(
                status_code=422,
                detail={"code": "unknown_food", "food_name": it.get("food_name", "")},
            )
        unit = it.get("unit", "g")
        qty_entered = float(it.get("quantity", 0))
        grams = to_grams(qty_entered, unit)
        nutrition = food_svc.compute_item_nutrition(food, grams)
        resolved_items.append({
            "id": new_id(), "food_id": food["id"], "food_name": food["name"],
            "quantity_g": round(grams, 1), "unit_entered": unit, "quantity_entered": qty_entered,
            "is_estimated": bool(it.get("is_estimated", False)), **nutrition,
        })

    with db_conn() as conn:
        conn.execute(
            text("INSERT INTO meals (id, user_id, meal_type, eaten_at, source, status, note) "
                 "VALUES (:i, :u, :mt, COALESCE(CAST(:ea AS timestamptz), now()), :src, :st, :n)"),
            {"i": meal_id, "u": user_id, "mt": meal_type, "ea": eaten_at, "src": source, "st": status, "n": note},
        )
        for ri in resolved_items:
            conn.execute(
                text("INSERT INTO meal_items (id, meal_id, food_id, food_name, quantity_g, unit_entered, "
                     "quantity_entered, is_estimated, kcal, protein_g, carbs_g, fat_g, fiber_g) VALUES "
                     "(:id, :mid, :fid, :fn, :qg, :ue, :qe, :est, :k, :p, :c, :f, :fb)"),
                {"id": ri["id"], "mid": meal_id, "fid": ri["food_id"], "fn": ri["food_name"],
                 "qg": ri["quantity_g"], "ue": ri["unit_entered"], "qe": ri["quantity_entered"],
                 "est": ri["is_estimated"], "k": ri["kcal"], "p": ri["protein_g"],
                 "c": ri["carbs_g"], "f": ri["fat_g"], "fb": ri["fiber_g"]},
            )
    return get_meal(user_id, meal_id)


def get_meal(user_id: str, meal_id: str) -> dict:
    with db_conn() as conn:
        meal = conn.execute(
            text("SELECT * FROM meals WHERE id = :i AND user_id = :u"), {"i": meal_id, "u": user_id}
        ).mappings().fetchone()
        if not meal:
            raise HTTPException(status_code=404, detail="meal_not_found")
        items = conn.execute(
            text("SELECT * FROM meal_items WHERE meal_id = :i"), {"i": meal_id}
        ).mappings().all()
    return _meal_dict(meal, items)


def delete_meal(user_id: str, meal_id: str) -> None:
    with db_conn() as conn:
        res = conn.execute(
            text("DELETE FROM meals WHERE id = :i AND user_id = :u"), {"i": meal_id, "u": user_id}
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="meal_not_found")


def list_meals_for_day(user_id: str, day: dt.date, tz_offset_min: int = 0) -> list[dict]:
    start = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone(dt.timedelta(minutes=tz_offset_min)))
    end = start + dt.timedelta(days=1)
    with db_conn() as conn:
        meals = conn.execute(
            text("SELECT * FROM meals WHERE user_id = :u AND eaten_at >= :s AND eaten_at < :e "
                 "AND status = 'final' ORDER BY eaten_at"),
            {"u": user_id, "s": start, "e": end},
        ).mappings().all()
        out = []
        for m in meals:
            items = conn.execute(
                text("SELECT * FROM meal_items WHERE meal_id = :i"), {"i": str(m["id"])}
            ).mappings().all()
            out.append(_meal_dict(m, items))
    return out


def day_totals(meals: list[dict]) -> dict:
    totals = {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
    for m in meals:
        for k in totals:
            totals[k] += m["totals"][k]
    return {k: round(v, 1) for k, v in totals.items()}


def _meal_dict(meal, items) -> dict:
    items_out = []
    totals = {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
    for it in items:
        d = dict(it)
        d["id"] = str(d["id"])
        d["meal_id"] = str(d["meal_id"])
        d["food_id"] = str(d["food_id"]) if d["food_id"] else None
        for k in ("quantity_g", "quantity_entered", "kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"):
            d[k] = float(d[k])
        for k in totals:
            totals[k] += d[k]
        items_out.append(d)
    return {
        "id": str(meal["id"]), "meal_type": meal["meal_type"],
        "eaten_at": meal["eaten_at"].isoformat(), "source": meal["source"],
        "status": meal["status"], "note": meal["note"],
        "items": items_out, "totals": {k: round(v, 1) for k, v in totals.items()},
    }
