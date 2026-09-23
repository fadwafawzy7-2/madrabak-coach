"""Safety / Guardrails layer.

Validates user data, nutrition targets, AI input and AI output.
Config-driven via safety_rules (versioned). Never diagnoses; when a sensitive
topic is detected we respond with a scripted safe message in the user's
language and log a safety flag — the AI is not called at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SAFE_RESPONSES = {
    "eating_disorder": {
        "ar": "أنا هنا لمساعدتك بطريقة صحية وآمنة. التجويع أو السلوكيات التعويضية القاسية تضر جسمك ولا تساعد على تقدم حقيقي. "
              "إذا كنت تعاني من أفكار صعبة حول الأكل، أنصحك بشدة بالتحدث مع مختص مؤهل. "
              "يمكنني مساعدتك في بناء خطة معتدلة ومستدامة بدلاً من ذلك.",
        "en": "I'm here to help you in a healthy, safe way. Starvation or harsh compensatory behaviors harm your body and don't create real progress. "
              "If you're struggling with difficult thoughts about eating, I strongly encourage you to talk to a qualified professional. "
              "I can help you build a moderate, sustainable plan instead.",
        "he": "אני כאן כדי לעזור לך בדרך בריאה ובטוחה. הרעבה או התנהגויות מפצות קיצוניות פוגעות בגוף ולא יוצרות התקדמות אמיתית. "
              "אם קשה לך עם מחשבות סביב אכילה, מומלץ מאוד לפנות לאיש מקצוע מוסמך. "
              "אני יכול לעזור לך לבנות תוכנית מתונה וברת-קיימא במקום זאת.",
    },
    "medical": {
        "ar": "هذا سؤال طبي يتجاوز دوري كمدرب تغذية ولياقة. لا أستطيع التشخيص أو وصف الأدوية. "
              "يرجى استشارة طبيب أو مختص مؤهل. يسعدني مساعدتك في التغذية والتدريب ضمن حدود آمنة.",
        "en": "This is a medical question beyond my role as a nutrition and fitness coach. I can't diagnose or prescribe medication. "
              "Please consult a doctor or qualified professional. I'm happy to help with nutrition and training within safe limits.",
        "he": "זו שאלה רפואית שחורגת מתפקידי כמאמן תזונה וכושר. אינני יכול לאבחן או לרשום תרופות. "
              "אנא פנה לרופא או לאיש מקצוע מוסמך. אשמח לעזור בתזונה ואימונים בגבולות בטוחים.",
    },
    "output_blocked": {
        "ar": "عذراً، لا يمكنني تقديم هذه النصيحة لأنها قد تكون غير آمنة. جرب سؤالاً آخر وسأساعدك بطريقة صحية.",
        "en": "Sorry, I can't give that advice because it may be unsafe. Try another question and I'll help you in a healthy way.",
        "he": "מצטער, אינני יכול לתת עצה זו כי היא עלולה להיות לא בטוחה. נסה שאלה אחרת ואעזור בדרך בריאה.",
    },
}


@dataclass
class SafetyCheck:
    allowed: bool
    flag_type: str | None = None
    severity: str = "info"
    scripted_response: str | None = None
    warnings: list[str] = field(default_factory=list)


def _lang(language: str) -> str:
    return language if language in ("ar", "en", "he") else "en"


def check_user_message(message: str, language: str, rules: dict) -> SafetyCheck:
    """Pre-check before any AI call."""
    lowered = message.lower()
    for flag, patterns in rules["blocked_intent_patterns"].items():
        if flag == "comment":
            continue
        for p in patterns:
            if p.lower() in lowered:
                return SafetyCheck(
                    allowed=False,
                    flag_type=flag,
                    severity="high" if flag == "eating_disorder" else "medium",
                    scripted_response=SAFE_RESPONSES.get(flag, SAFE_RESPONSES["medical"])[_lang(language)],
                )
    return SafetyCheck(allowed=True)


def check_ai_output(text: str, language: str, rules: dict) -> SafetyCheck:
    """Post-check on AI output before it reaches the user."""
    lowered = text.lower()
    for p in rules["ai_output_blocked_patterns"]:
        if p.lower() in lowered:
            return SafetyCheck(
                allowed=False,
                flag_type="dangerous_ai_output",
                severity="high",
                scripted_response=SAFE_RESPONSES["output_blocked"][_lang(language)],
            )
    return SafetyCheck(allowed=True)


def validate_profile_measurements(data: dict, rules: dict) -> list[str]:
    """Returns a list of error codes for out-of-bounds measurements."""
    errors = []
    bounds = rules["measurement_bounds"]
    mapping = {
        "age": "age", "height_cm": "height_cm", "weight_kg": "weight_kg",
        "waist_cm": "waist_cm", "neck_cm": "neck_cm", "hip_cm": "hip_cm", "arm_cm": "arm_cm",
    }
    for key, bkey in mapping.items():
        val = data.get(key)
        if val is None:
            continue
        b = bounds[bkey]
        if not (b["min"] <= val <= b["max"]):
            errors.append(f"invalid_{bkey}")
    return errors


def adjust_goal_for_young_user(age: int, goal: str, rules: dict) -> tuple[str, list[str]]:
    """Conservative behavior for users under the young-user threshold."""
    warnings: list[str] = []
    if age < rules["min_age"]:
        return goal, ["under_min_age"]
    if age < rules["young_user_age_threshold"]:
        policy = rules["young_user_policy"]
        if goal in policy["block_goals"]:
            warnings.append("young_user_goal_adjusted")
            return policy["replace_blocked_goal_with"], warnings
        warnings.append("young_user_conservative_mode")
    return goal, warnings


def clamp_deficit_for_young_user(age: int, adjustment_kcal: int, rules: dict) -> tuple[int, list[str]]:
    if age < rules["young_user_age_threshold"]:
        max_deficit = rules["young_user_policy"]["max_deficit_kcal"]
        if adjustment_kcal < -max_deficit:
            return -max_deficit, ["young_user_deficit_clamped"]
    return adjustment_kcal, []
