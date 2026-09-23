"""Feature services: «ماذا آكل الآن؟», «عندي هذه المكونات», «إنقاذ اليوم».

The Nutrition Engine / meal totals produce the actual numbers; the AI only turns
them into friendly suggestions. Ingredient nutrition comes from the Food Database.
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException

from ..db import jdump
from ..providers.ai_chat import AiChatProvider, get_chat_provider
from ..safety import guardrails
from .coach import SYSTEM_PROMPT, _check_daily_limit, log_ai_usage
from .foods import match_food_by_name
from .meals import day_totals, list_meals_for_day
from .nutrition import get_current_target, get_profile
from .rules import get_safety_rules


def compute_remaining(user_id: str, today: dt.date | None = None) -> dict:
    """Deterministic remaining-macros calculation (no AI)."""
    target = get_current_target(user_id)
    if not target:
        raise HTTPException(status_code=422, detail={"code": "no_nutrition_target"})
    meals = list_meals_for_day(user_id, today or dt.date.today())
    totals = day_totals(meals)
    return {
        "target": {"kcal": target["target_kcal"], "protein_g": target["protein_g"],
                   "carbs_g": target["carbs_g"], "fat_g": target["fat_g"]},
        "consumed": totals,
        "remaining": {
            "kcal": round(target["target_kcal"] - totals["kcal"], 1),
            "protein_g": round(target["protein_g"] - totals["protein_g"], 1),
            "carbs_g": round(target["carbs_g"] - totals["carbs_g"], 1),
            "fat_g": round(target["fat_g"] - totals["fat_g"], 1),
        },
        "meals_eaten": [m["meal_type"] for m in meals],
    }


async def _ai_suggest(user_id: str, endpoint: str, instruction: str,
                      extra_ctx: dict, provider: AiChatProvider | None = None) -> dict:
    safety_rules = get_safety_rules()
    limits = safety_rules["ai_limits"]
    _check_daily_limit(user_id, endpoint, limits["coach_messages_per_day"])

    profile = get_profile(user_id)
    language = profile.get("language", "ar")
    numbers = compute_remaining(user_id)
    ctx = {
        "numbers": numbers,
        "sport": profile.get("sport"), "goal": profile.get("primary_goal"),
        "budget_tier": profile.get("budget_tier"),
        "food_preferences": profile.get("food_preferences") or [],
        "time_of_day": dt.datetime.now().strftime("%H:%M"),
        **extra_ctx,
    }
    system = (
        SYSTEM_PROMPT.get(language, SYSTEM_PROMPT["en"])
        + "\nPrefer filling, sustainable, affordable meals with protein and fiber."
        + "\n\nCONTEXT (source of truth — use these exact numbers):\n" + jdump(ctx)
    )
    provider = provider or get_chat_provider()
    try:
        result = await provider.chat(system, [{"role": "user", "content": instruction}],
                                     max_tokens=limits["max_output_tokens"])
    except Exception:
        raise HTTPException(status_code=503, detail={"code": "ai_unavailable"})
    log_ai_usage(user_id, result.provider, result.model, endpoint,
                 result.input_tokens, result.output_tokens, result.estimated_cost_usd)
    post = guardrails.check_ai_output(result.text, language, safety_rules)
    reply = result.text if post.allowed else post.scripted_response
    return {"numbers": numbers, "suggestion": reply}


async def what_should_i_eat(user_id: str, provider: AiChatProvider | None = None) -> dict:
    return await _ai_suggest(
        user_id, "what_to_eat",
        "Based on my remaining calories and macros in the context, suggest 2-3 realistic meal "
        "options for right now. Respect my budget, preferences, sport and the time of day.",
        {}, provider,
    )


async def ingredients_to_meals(user_id: str, ingredients: list[str],
                               provider: AiChatProvider | None = None) -> dict:
    if not ingredients or len(ingredients) > 30:
        raise HTTPException(status_code=422, detail={"code": "invalid_ingredients"})
    # match against food DB so the AI has verified per-100g values to reference
    matched, unmatched = [], []
    for ing in ingredients:
        food = match_food_by_name(ing)
        if food:
            matched.append({
                "name": food["name"], "kcal_per_100g": food["kcal_per_100g"],
                "protein_per_100g": food["protein_per_100g"], "carbs_per_100g": food["carbs_per_100g"],
                "fat_per_100g": food["fat_per_100g"], "confidence": food["confidence_level"],
            })
        else:
            unmatched.append(ing)
    result = await _ai_suggest(
        user_id, "ingredients_meals",
        "I have these ingredients (with verified per-100g values in the context). Propose 2-3 meals I can "
        "make from them that fit my remaining macros. Use ONLY the database values for any numbers; "
        "for unmatched ingredients, do not invent nutrition values — mention they need to be logged manually.",
        {"available_ingredients": matched, "unmatched_ingredients": unmatched}, provider,
    )
    result["matched_ingredients"] = matched
    result["unmatched_ingredients"] = unmatched
    return result


async def save_my_day(user_id: str, provider: AiChatProvider | None = None) -> dict:
    return await _ai_suggest(
        user_id, "save_my_day",
        "I ate a large meal today. Without any shaming, and WITHOUT recommending starvation, skipping meals "
        "as punishment or dangerous compensation, look at my remaining numbers and suggest a realistic, "
        "kind way to finish the day (e.g. lighter protein-focused dinner, a walk, hydration). "
        "One bigger day does not ruin progress.",
        {}, provider,
    )
