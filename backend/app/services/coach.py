"""AI Coach: CoachContextBuilder + safety pipeline + usage limits + cost logging.

Pipeline: user message → safety pre-check → context builder → AiChatProvider
→ safety post-check → response → usage logging.

The AI NEVER mutates targets/macros/profile — it only talks. All numbers in
the context come from the Nutrition Engine and the Food Database.
"""
from __future__ import annotations

import datetime as dt
import logging

from fastapi import HTTPException
from sqlalchemy import text

from ..db import db_conn, jdump, new_id
from ..providers.ai_chat import AiChatProvider, get_chat_provider
from ..safety import guardrails
from .meals import day_totals, list_meals_for_day
from .nutrition import get_current_target, get_profile
from .rules import get_safety_rules

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = {
    "ar": (
        "أنت «مدربك الخاص» — مدرب تغذية ولياقة ودود وعملي. "
        "تحدث بالعربية. استخدم الأرقام الموجودة في السياق فقط (محسوبة من محرك التغذية وقاعدة الأطعمة) — "
        "لا تخترع سعرات أو قيماً غذائية ولا تغير أهداف المستخدم الرقمية. "
        "لا تشخص أمراضاً ولا تصف أدوية ولا تشجع أبداً على التجويع أو خسارة الوزن الخطيرة السريعة. "
        "إذا أكل المستخدم كثيراً فلا تلمه؛ ساعده على إنهاء اليوم بشكل معقول. "
        "عند الأسئلة الطبية انصح بمراجعة مختص مؤهل. كن مختصراً ومشجعاً."
    ),
    "en": (
        "You are 'Your Personal Coach' — a friendly, practical nutrition and fitness coach. "
        "Reply in English. Use ONLY the numbers given in the context (computed by the nutrition engine and food database) — "
        "never invent calories or nutrition values and never change the user's numeric targets. "
        "Never diagnose, prescribe medication, or encourage starvation or dangerous rapid weight loss. "
        "If the user overate, don't shame them; help them finish the day reasonably. "
        "For medical questions, advise seeing a qualified professional. Be concise and encouraging."
    ),
    "he": (
        "אתה 'המאמן האישי שלך' — מאמן תזונה וכושר ידידותי ומעשי. "
        "ענה בעברית. השתמש רק במספרים שבהקשר (מחושבים על ידי מנוע התזונה ומאגר המזון) — "
        "לעולם אל תמציא קלוריות או ערכים תזונתיים ואל תשנה יעדים מספריים. "
        "לעולם אל תאבחן, אל תרשום תרופות ואל תעודד הרעבה או ירידה מסוכנת במשקל. "
        "אם המשתמש אכל יותר מדי — בלי האשמות; עזור לו לסיים את היום בצורה סבירה. "
        "בשאלות רפואיות הפנה לאיש מקצוע מוסמך. היה תמציתי ומעודד."
    ),
}


def _check_daily_limit(user_id: str, endpoint: str, limit: int) -> None:
    with db_conn() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM ai_usage_events WHERE user_id = :u AND endpoint = :e "
                 "AND created_at >= date_trunc('day', now())"),
            {"u": user_id, "e": endpoint},
        ).scalar_one()
    if count >= limit:
        raise HTTPException(status_code=429, detail={"code": "daily_ai_limit_reached", "endpoint": endpoint})


def log_ai_usage(user_id: str | None, provider: str, model: str, endpoint: str,
                 input_tokens: int, output_tokens: int, cost: float) -> None:
    with db_conn() as conn:
        conn.execute(
            text("INSERT INTO ai_usage_events (id, user_id, provider, model, endpoint, input_tokens, "
                 "output_tokens, estimated_cost_usd) VALUES (:i, :u, :p, :m, :e, :it, :ot, :c)"),
            {"i": new_id(), "u": user_id, "p": provider, "m": model, "e": endpoint,
             "it": input_tokens, "ot": output_tokens, "c": cost},
        )


def log_safety_flag(user_id: str, flag_type: str, context: str, severity: str) -> None:
    with db_conn() as conn:
        conn.execute(
            text("INSERT INTO safety_flags (id, user_id, flag_type, context, severity) "
                 "VALUES (:i, :u, :f, :c, :s)"),
            {"i": new_id(), "u": user_id, "f": flag_type, "c": context[:500], "s": severity},
        )


def build_coach_context(user_id: str, today: dt.date | None = None) -> dict:
    """Compact context snapshot — profile summary, current target, today's totals,
    recent weight trend. NOT the whole database."""
    today = today or dt.date.today()
    profile = get_profile(user_id)
    target = get_current_target(user_id)
    meals = list_meals_for_day(user_id, today)
    totals = day_totals(meals)

    with db_conn() as conn:
        weights = conn.execute(
            text("SELECT measured_at::date AS d, value_normalized FROM body_measurements "
                 "WHERE user_id = :u AND kind = 'weight' ORDER BY measured_at DESC LIMIT 14"),
            {"u": user_id},
        ).mappings().all()

    weight_series = [{"date": str(w["d"]), "kg": float(w["value_normalized"])} for w in weights]
    trend = None
    if len(weight_series) >= 4:
        half = len(weight_series) // 2
        recent = sum(w["kg"] for w in weight_series[:half]) / half
        older = sum(w["kg"] for w in weight_series[half:]) / (len(weight_series) - half)
        trend = round(recent - older, 2)

    ctx = {
        "profile": {
            "age": profile.get("age"), "sex": profile.get("sex"), "sport": profile.get("sport"),
            "goal": profile.get("primary_goal"), "weight_kg": float(profile["weight_kg"]) if profile.get("weight_kg") else None,
            "height_cm": float(profile["height_cm"]) if profile.get("height_cm") else None,
            "training_days_per_week": profile.get("training_days_per_week"),
            "budget_tier": profile.get("budget_tier"),
            "food_preferences": profile.get("food_preferences") or [],
            "language": profile.get("language", "ar"),
        },
        "target": {
            "kcal": target["target_kcal"], "protein_g": target["protein_g"],
            "carbs_g": target["carbs_g"], "fat_g": target["fat_g"],
        } if target else None,
        "today": {
            "consumed": totals,
            "remaining": {
                "kcal": round(target["target_kcal"] - totals["kcal"], 1),
                "protein_g": round(target["protein_g"] - totals["protein_g"], 1),
                "carbs_g": round(target["carbs_g"] - totals["carbs_g"], 1),
                "fat_g": round(target["fat_g"] - totals["fat_g"], 1),
            } if target else None,
            "meals": [{"type": m["meal_type"], "kcal": m["totals"]["kcal"]} for m in meals],
            "local_time_hint": dt.datetime.now().strftime("%H:%M"),
        },
        "weight_trend_kg": trend,
        "recent_weights": weight_series[:7],
    }

    with db_conn() as conn:
        conn.execute(
            text("INSERT INTO coach_context_snapshots (id, user_id, snapshot) VALUES (:i, :u, CAST(:s AS jsonb))"),
            {"i": new_id(), "u": user_id, "s": jdump(ctx)},
        )
    return ctx


async def coach_chat(user_id: str, message: str, provider: AiChatProvider | None = None) -> dict:
    safety_rules = get_safety_rules()
    profile = get_profile(user_id)
    language = profile.get("language", "ar")
    limits = safety_rules["ai_limits"]

    # safety pre-check
    pre = guardrails.check_user_message(message, language, safety_rules)
    _store_message(user_id, "user", message, blocked=not pre.allowed, flag=pre.flag_type)
    if not pre.allowed:
        log_safety_flag(user_id, pre.flag_type, message, pre.severity)
        _store_message(user_id, "assistant", pre.scripted_response)
        return {"reply": pre.scripted_response, "blocked": True, "flag": pre.flag_type}

    _check_daily_limit(user_id, "coach_chat", limits["coach_messages_per_day"])

    ctx = build_coach_context(user_id)
    history = _recent_history(user_id, limits["max_history_messages"])

    system = SYSTEM_PROMPT.get(language, SYSTEM_PROMPT["en"]) + "\n\nCONTEXT (source of truth):\n" + jdump(ctx)
    provider = provider or get_chat_provider()
    try:
        result = await provider.chat(system, history + [{"role": "user", "content": message}],
                                     max_tokens=limits["max_output_tokens"])
    except Exception:
        logger.exception("coach_chat: AI provider call failed")
        raise HTTPException(status_code=503, detail={"code": "ai_unavailable"})

    log_ai_usage(user_id, result.provider, result.model, "coach_chat",
                 result.input_tokens, result.output_tokens, result.estimated_cost_usd)

    # safety post-check
    post = guardrails.check_ai_output(result.text, language, safety_rules)
    reply = result.text if post.allowed else post.scripted_response
    if not post.allowed:
        log_safety_flag(user_id, post.flag_type, result.text, post.severity)
    _store_message(user_id, "assistant", reply, blocked=not post.allowed, flag=post.flag_type)
    return {"reply": reply, "blocked": not post.allowed, "flag": post.flag_type}


def _recent_history(user_id: str, limit: int) -> list[dict]:
    with db_conn() as conn:
        rows = conn.execute(
            text("SELECT role, content FROM coach_messages WHERE user_id = :u AND NOT blocked "
                 "AND role IN ('user','assistant') ORDER BY created_at DESC LIMIT :l"),
            {"u": user_id, "l": limit},
        ).mappings().all()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _store_message(user_id: str, role: str, content: str, blocked: bool = False, flag: str | None = None) -> None:
    with db_conn() as conn:
        conn.execute(
            text("INSERT INTO coach_messages (id, user_id, role, content, blocked, safety_flag) "
                 "VALUES (:i, :u, :r, :c, :b, :f)"),
            {"i": new_id(), "u": user_id, "r": role, "c": content, "b": blocked, "f": flag},
        )
