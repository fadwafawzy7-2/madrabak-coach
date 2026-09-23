"""Food database service. Source of truth for food nutrition values.

Values are stored per 100g. AI is never allowed to invent nutrition values:
if a food is not matched here, the item is flagged `unmatched` and the client
must ask the user to pick/enter a food.
"""
from __future__ import annotations

from sqlalchemy import text

from ..db import db_conn


def search_foods(query: str, language: str | None = None, limit: int = 20) -> list[dict]:
    q = f"%{query.strip().lower()}%"
    sql = (
        "SELECT id, name, alternative_names, language, kcal_per_100g, protein_per_100g, "
        "carbs_per_100g, fat_per_100g, fiber_per_100g, source, confidence_level "
        "FROM foods WHERE (lower(name) LIKE :q OR lower(alternative_names::text) LIKE :q) "
    )
    params: dict = {"q": q, "lim": limit}
    if language:
        sql += "ORDER BY (language = :lang) DESC, length(name) ASC "
        params["lang"] = language
    else:
        sql += "ORDER BY length(name) ASC "
    sql += "LIMIT :lim"
    with db_conn() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [_food_dict(r) for r in rows]


def get_food(food_id: str) -> dict | None:
    with db_conn() as conn:
        row = conn.execute(text("SELECT * FROM foods WHERE id = :i"), {"i": food_id}).mappings().fetchone()
    return _food_dict(row) if row else None


def match_food_by_name(name: str, language: str | None = None) -> dict | None:
    """Best-effort database match for a detected/typed food name."""
    results = search_foods(name, language, limit=1)
    if results:
        return results[0]
    # try individual words (longest first) for compound names
    words = sorted(name.split(), key=len, reverse=True)
    for w in words:
        if len(w) < 3:
            continue
        results = search_foods(w, language, limit=1)
        if results:
            return results[0]
    return None


def compute_item_nutrition(food: dict, quantity_g: float) -> dict:
    factor = quantity_g / 100.0
    return {
        "kcal": round(float(food["kcal_per_100g"]) * factor, 1),
        "protein_g": round(float(food["protein_per_100g"]) * factor, 1),
        "carbs_g": round(float(food["carbs_per_100g"]) * factor, 1),
        "fat_g": round(float(food["fat_per_100g"]) * factor, 1),
        "fiber_g": round(float(food["fiber_per_100g"]) * factor, 1),
    }


def _food_dict(r) -> dict:
    d = dict(r)
    d["id"] = str(d["id"])
    for k in ("kcal_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g", "fiber_per_100g"):
        d[k] = float(d[k])
    return d
