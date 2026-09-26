"""All API routes. Every non-auth route requires a Bearer token.

Errors return machine-readable codes; stack traces are never exposed.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..db import db_conn, jdump, new_id
from ..providers.vision import get_vision_provider
from ..safety.guardrails import validate_profile_measurements
from ..services import coach as coach_svc
from ..services import foods as food_svc
from ..services import meals as meal_svc
from ..services import nutrition as nutrition_svc
from ..services import progress as progress_svc
from ..services import subscriptions as sub_svc
from ..services import suggestions as sugg_svc
from ..services.auth import get_current_user_id, login_or_register_google, login_user, register_user
from ..services.rules import get_safety_rules

router = APIRouter()

# ------------------------------------------------------------------ auth

class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


@router.post("/auth/register")
def register(body: Credentials):
    result = register_user(body.email, body.password)
    _track(result["user_id"], "user_registered", {})
    _track(result["user_id"], "trial_started", {})
    return result


@router.post("/auth/login")
def login(body: Credentials):
    return login_user(body.email, body.password)


class GoogleAuthIn(BaseModel):
    id_token: str


@router.post("/auth/google")
def google_auth(body: GoogleAuthIn):
    result = login_or_register_google(body.id_token)
    if result.pop("is_new_user", False):
        _track(result["user_id"], "user_registered", {"provider": "google"})
        _track(result["user_id"], "trial_started", {})
    return result


# ------------------------------------------------------------------ profile

class ProfileUpdate(BaseModel):
    display_name: str | None = None
    age: int | None = None
    sex: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    sport: str | None = None
    primary_goal: str | None = None
    secondary_goal: str | None = None
    activity_level: str | None = None
    training_days_per_week: int | None = None
    training_duration_min: int | None = None
    training_intensity: str | None = None
    usual_training_time: str | None = None
    matches_per_week: int | None = None
    matches_replace_training_day: bool | None = None
    budget_tier: str | None = None
    food_preferences: list[str] | None = None
    language: str | None = None
    units_system: str | None = None
    height_unit: str | None = None
    weight_unit: str | None = None
    timezone: str | None = None
    notifications_enabled: bool | None = None
    onboarding_completed: bool | None = None


_PROFILE_COLS = set(ProfileUpdate.model_fields.keys())


@router.get("/profile")
def get_profile(user_id: str = Depends(get_current_user_id)):
    p = nutrition_svc.get_profile(user_id)
    for k in ("height_cm", "weight_kg"):
        if p.get(k) is not None:
            p[k] = float(p[k])
    p["user_id"] = str(p["user_id"])
    p["updated_at"] = p["updated_at"].isoformat()
    return p


@router.put("/profile")
def update_profile(body: ProfileUpdate, user_id: str = Depends(get_current_user_id)):
    data = {k: v for k, v in body.model_dump().items() if v is not None and k in _PROFILE_COLS}
    if not data:
        raise HTTPException(status_code=422, detail={"code": "empty_update"})
    errors = validate_profile_measurements(data, get_safety_rules())
    if errors:
        raise HTTPException(status_code=422, detail={"code": "invalid_measurements", "errors": errors})
    sets = ", ".join(f"{k} = :{k}" for k in data)
    params = dict(data)
    if "food_preferences" in params:
        params["food_preferences"] = jdump(params["food_preferences"])
        sets = sets.replace("food_preferences = :food_preferences",
                            "food_preferences = CAST(:food_preferences AS jsonb)")
    params["u"] = user_id
    with db_conn() as conn:
        conn.execute(text(f"UPDATE profiles SET {sets}, updated_at = now() WHERE user_id = :u"), params)
    if data.get("onboarding_completed"):
        _track(user_id, "onboarding_completed", {})
    return get_profile(user_id)


@router.delete("/account")
def delete_account(user_id: str = Depends(get_current_user_id)):
    """Full account + data deletion (privacy requirement)."""
    with db_conn() as conn:
        conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
    return {"deleted": True}


@router.delete("/account/data")
def delete_data(user_id: str = Depends(get_current_user_id)):
    """Delete sensitive data but keep the account."""
    with db_conn() as conn:
        for table in ("meals", "body_measurements", "body_fat_estimates", "coach_messages",
                      "coach_context_snapshots", "weekly_reviews", "analytics_events"):
            conn.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user_id})
    return {"deleted": True}


# ------------------------------------------------------------------ nutrition targets

@router.post("/nutrition/targets/recalculate")
def recalculate_target(day_type: str = "training", user_id: str = Depends(get_current_user_id)):
    return nutrition_svc.compute_and_store_target(user_id, day_type)


@router.get("/nutrition/targets/current")
def current_target(user_id: str = Depends(get_current_user_id)):
    t = nutrition_svc.get_current_target(user_id)
    if not t:
        raise HTTPException(status_code=404, detail="no_target")
    t["id"] = str(t["id"])
    t["user_id"] = str(t["user_id"])
    t["created_at"] = t["created_at"].isoformat()
    return t


# ------------------------------------------------------------------ foods

@router.get("/foods/search")
def foods_search(q: str, language: str | None = None, user_id: str = Depends(get_current_user_id)):
    if len(q.strip()) < 2:
        raise HTTPException(status_code=422, detail={"code": "query_too_short"})
    return {"results": food_svc.search_foods(q, language)}


# ------------------------------------------------------------------ meals

class MealItemIn(BaseModel):
    food_id: str | None = None
    food_name: str | None = None
    quantity: float
    unit: str = "g"
    is_estimated: bool = False


class MealIn(BaseModel):
    meal_type: str
    source: str = "manual"
    items: list[MealItemIn]
    eaten_at: str | None = None
    note: str | None = None


@router.post("/meals")
def create_meal(body: MealIn, user_id: str = Depends(get_current_user_id)):
    meal = meal_svc.create_meal(user_id, body.meal_type, body.source,
                                [i.model_dump() for i in body.items],
                                eaten_at=body.eaten_at, note=body.note)
    _track(user_id, "meal_logged", {"source": body.source, "meal_type": body.meal_type})
    return meal


@router.get("/meals/day/{day}")
def meals_for_day(day: str, user_id: str = Depends(get_current_user_id)):
    try:
        d = dt.date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=422, detail={"code": "invalid_date"})
    meals = meal_svc.list_meals_for_day(user_id, d)
    return {"meals": meals, "totals": meal_svc.day_totals(meals)}


@router.delete("/meals/{meal_id}")
def delete_meal(meal_id: str, user_id: str = Depends(get_current_user_id)):
    meal_svc.delete_meal(user_id, meal_id)
    return {"deleted": True}


# ------------------------------------------------------------------ photo analysis

@router.post("/meals/analyze-photo")
async def analyze_photo(image: UploadFile = File(...), language: str = Form("ar"),
                        user_id: str = Depends(sub_svc.require_active_access)):
    """Photo → Vision AI → DB matching → DRAFT items. The user must edit/confirm
    before the meal is finalized via POST /meals. Quantities are estimates."""
    rules = get_safety_rules()
    coach_svc._check_daily_limit(user_id, "photo_analysis", rules["ai_limits"]["image_analyses_per_day"])
    content = await image.read()
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=422, detail={"code": "invalid_image"})
    mime = image.content_type or "image/jpeg"
    if not mime.startswith("image/"):
        raise HTTPException(status_code=422, detail={"code": "invalid_image"})
    provider = get_vision_provider()
    try:
        result = await provider.detect_foods(content, mime, language)
    except Exception:
        raise HTTPException(status_code=503, detail={"code": "vision_unavailable"})
    coach_svc.log_ai_usage(user_id, result.provider, result.model, "photo_analysis",
                           result.input_tokens, result.output_tokens, result.estimated_cost_usd)
    draft_items = []
    for f in result.foods:
        food = food_svc.match_food_by_name(f.name, language)
        if food:
            nutrition = food_svc.compute_item_nutrition(food, f.estimated_grams)
            draft_items.append({
                "matched": True, "food_id": food["id"], "food_name": food["name"],
                "detected_name": f.name, "estimated_grams": f.estimated_grams,
                "confidence": food["confidence_level"], **nutrition,
            })
        else:
            # No DB match → NO nutrition values invented. User must pick a food.
            draft_items.append({
                "matched": False, "food_id": None, "food_name": None,
                "detected_name": f.name, "estimated_grams": f.estimated_grams,
            })
    _track(user_id, "image_analyzed", {"foods_detected": len(draft_items)})
    return {
        "draft_items": draft_items,
        "note": "estimates_only_user_must_confirm",
    }


# ------------------------------------------------------------------ progress

class MeasurementIn(BaseModel):
    kind: str
    value: float
    is_morning: bool = False
    note: str | None = None


@router.post("/progress/measurements")
def log_measurement(body: MeasurementIn, user_id: str = Depends(get_current_user_id)):
    result = progress_svc.log_measurement(user_id, body.kind, body.value, body.is_morning, body.note)
    _track(user_id, "measurement_logged", {"kind": body.kind})
    return result


@router.get("/progress/measurements/{kind}")
def get_measurements(kind: str, days: int = 90, user_id: str = Depends(get_current_user_id)):
    return {"measurements": progress_svc.get_measurements(user_id, kind, days)}


@router.get("/progress/weight-summary")
def weight_summary(user_id: str = Depends(get_current_user_id)):
    return progress_svc.weight_summary(user_id)


class BodyFatIn(BaseModel):
    waist_cm: float
    neck_cm: float
    hip_cm: float | None = None


@router.post("/progress/body-fat")
def body_fat(body: BodyFatIn, user_id: str = Depends(get_current_user_id)):
    return progress_svc.estimate_body_fat(user_id, body.waist_cm, body.neck_cm, body.hip_cm)


@router.post("/progress/weekly-review")
def weekly_review(user_id: str = Depends(get_current_user_id)):
    data = progress_svc.generate_weekly_review(user_id)
    _track(user_id, "weekly_review_generated", {})
    return data


# ------------------------------------------------------------------ dashboard

@router.get("/dashboard/today")
def dashboard_today(user_id: str = Depends(get_current_user_id)):
    """Home screen «يومك»: target, consumed, remaining, macros, morning weight."""
    target = nutrition_svc.get_current_target(user_id)
    today = dt.date.today()
    meals = meal_svc.list_meals_for_day(user_id, today)
    totals = meal_svc.day_totals(meals)
    with db_conn() as conn:
        w = conn.execute(
            text("SELECT value_normalized FROM body_measurements WHERE user_id = :u AND kind = 'weight' "
                 "AND is_morning AND measured_at >= CURRENT_DATE ORDER BY measured_at DESC LIMIT 1"),
            {"u": user_id},
        ).scalar()
    profile = nutrition_svc.get_profile(user_id)
    return {
        "target": {
            "kcal": target["target_kcal"], "protein_g": target["protein_g"],
            "carbs_g": target["carbs_g"], "fat_g": target["fat_g"],
        } if target else None,
        "consumed": totals,
        "remaining": {
            "kcal": round(target["target_kcal"] - totals["kcal"], 1),
            "protein_g": round(target["protein_g"] - totals["protein_g"], 1),
            "carbs_g": round(target["carbs_g"] - totals["carbs_g"], 1),
            "fat_g": round(target["fat_g"] - totals["fat_g"], 1),
        } if target else None,
        "meals": meals,
        "morning_weight_kg": float(w) if w is not None else None,
        "training_days_per_week": profile.get("training_days_per_week"),
        "sport": profile.get("sport"),
    }


# ------------------------------------------------------------------ coach & AI features

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.post("/coach/chat")
async def chat(body: ChatIn, user_id: str = Depends(sub_svc.require_active_access)):
    result = await coach_svc.coach_chat(user_id, body.message)
    _track(user_id, "coach_used", {"blocked": result["blocked"]})
    return result


@router.get("/coach/history")
def coach_history(limit: int = 30, user_id: str = Depends(get_current_user_id)):
    with db_conn() as conn:
        rows = conn.execute(
            text("SELECT role, content, created_at FROM coach_messages WHERE user_id = :u "
                 "AND role IN ('user','assistant') ORDER BY created_at DESC LIMIT :l"),
            {"u": user_id, "l": min(limit, 100)},
        ).mappings().all()
    return {"messages": [{"role": r["role"], "content": r["content"],
                          "created_at": r["created_at"].isoformat()} for r in reversed(rows)]}


@router.post("/coach/what-to-eat")
async def what_to_eat(user_id: str = Depends(sub_svc.require_active_access)):
    result = await sugg_svc.what_should_i_eat(user_id)
    _track(user_id, "what_to_eat_used", {})
    return result


class IngredientsIn(BaseModel):
    ingredients: list[str] = Field(min_length=1, max_length=30)


@router.post("/coach/ingredients")
async def ingredients(body: IngredientsIn, user_id: str = Depends(sub_svc.require_active_access)):
    result = await sugg_svc.ingredients_to_meals(user_id, body.ingredients)
    _track(user_id, "ingredients_used", {})
    return result


@router.post("/coach/save-my-day")
async def save_my_day(user_id: str = Depends(sub_svc.require_active_access)):
    result = await sugg_svc.save_my_day(user_id)
    _track(user_id, "save_my_day_used", {})
    return result


@router.get("/coach/remaining")
def remaining(user_id: str = Depends(get_current_user_id)):
    """Deterministic remaining macros — no AI call."""
    return sugg_svc.compute_remaining(user_id)


# ------------------------------------------------------------------ subscription

@router.get("/subscription")
def subscription_status(user_id: str = Depends(get_current_user_id)):
    return sub_svc.get_subscription_status(user_id)


class PurchaseIn(BaseModel):
    product_id: str
    purchase_token: str


@router.post("/subscription/verify")
async def verify_purchase(body: PurchaseIn, user_id: str = Depends(get_current_user_id)):
    result = await sub_svc.verify_and_apply_purchase(user_id, body.product_id, body.purchase_token)
    _track(user_id, "subscription_started", {})
    return result


@router.post("/subscription/cancel")
def cancel(user_id: str = Depends(get_current_user_id)):
    result = sub_svc.cancel_subscription(user_id)
    _track(user_id, "subscription_cancelled", {})
    return result


# ------------------------------------------------------------------ analytics

class EventIn(BaseModel):
    event_name: str = Field(min_length=1, max_length=64)
    properties: dict = Field(default_factory=dict)


@router.post("/analytics/events")
def track_event(body: EventIn, user_id: str = Depends(get_current_user_id)):
    _track(user_id, body.event_name, body.properties)
    return {"ok": True}


def _track(user_id: str | None, event_name: str, properties: dict) -> None:
    try:
        with db_conn() as conn:
            conn.execute(
                text("INSERT INTO analytics_events (id, user_id, event_name, properties) "
                     "VALUES (:i, :u, :e, CAST(:p AS jsonb))"),
                {"i": new_id(), "u": user_id, "e": event_name, "p": jdump(properties)},
            )
    except Exception:
        pass  # analytics must never break product flows
