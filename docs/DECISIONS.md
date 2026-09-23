# Architecture & Ambiguity Decisions

All decisions follow the rule: safest + simplest implementation, configurable, documented.

## 1. Activity model (no double counting)
The daily activity factor (`activity_factors` in nutrition rules) covers **non-training**
life activity only. Training sessions are added as `kcal/min × duration × effective days / 7`
and football matches as a flat provisional `match_kcal`. With
`matches_replace_training_day = true` (default) a match consumes a training day, so a
session and a match are never both counted for the same day. Effective training days are
clamped to ≥ 0 and the week is capped at 7 days.

## 2. Provisional configurable values
Where the spec does not establish precise values, we use clearly-marked provisional
numbers in `config/nutrition_rules_v1.json` (protein g/kg per sport & goal-direction,
fat minimum 0.6 g/kg, default fat 25% kcal, training kcal/min, match kcal 700,
deficit limit 750, surplus limit 500, calorie floors 1500/1200). All are configuration —
an active row in `nutrition_rules_config` overrides the bundled file, so ops can tune
without redeploying the app. No medical certainty is claimed anywhere.

## 3. Macro constraint policy
Protein is fixed first (rules), fat defaults to 25% of calories but never below the
per-kg minimum, carbs get the remainder. If protein + minimum fat exceed the calorie
target the engine raises `constraint_conflict` — no hidden 85/15 fallback, no silent
protein reduction. The API surfaces the error; the product layer decides what the user sees.

## 4. Young users (13–17)
`lose_weight`/`lose_fat` goals are replaced with `maintain` and any deficit is clamped
to 250 kcal (configurable). Users under 13 are rejected (`under_min_age`). This is
deliberately conservative rather than "adult rules scaled down".

## 5. Auth
Local email+password (bcrypt) + JWT was implemented because it works fully offline and
is testable. `AuthProvider` remains the seam: Supabase GoTrue can replace it by
verifying Supabase JWTs in `get_current_user_id` — nothing else changes.
Supabase env vars are already wired in settings.

## 6. AI stub mode
When `GROQ_API_KEY` / `GEMINI_API_KEY` are empty the providers run in deterministic
stub mode with the identical interface and pipeline (safety checks, context building,
usage logging, limits). This satisfies "implement the correct interface and clear
configuration path" for missing credentials. Stub responses are explicitly labeled as
development mode and never invent nutrition numbers.

## 7. Photo analysis honesty
The vision provider only detects food names + rough gram estimates. Nutrition values
come exclusively from the Food Database; unmatched detections carry **no** nutrition
values and force user selection. Every photo-derived item is `is_estimated = true` and
the UI requires editing/confirming before a meal is finalized.

## 8. Units
Everything is stored in kg/cm. lb/inch conversion helpers exist at both the engine and
the Android util layer; conversion is an input/output-boundary concern. The MVP UI ships
metric-first (unit preference fields exist in the profile for later UI wiring).

## 9. Flexible day
Kept out of the deterministic engine per spec. The coach can discuss moderation-focused
flexible meals conversationally; a structured flexible-day engine feature is deferred.

## 10. Weekly review
Fully deterministic (averages, trends, adherence heuristics). It only *suggests*
`review_targets_with_engine`; actual target changes must go through
`POST /nutrition/targets/recalculate` (engine + safety).

## 11. Rate limiting
Simple in-memory per-IP buckets (120/min general, 10/min auth). Documented as
single-instance only; swap for Redis in multi-instance production. Disabled in tests
via `ENV=test`.

## 12. Hebrew resources
Android uses the legacy `values-iw` qualifier (required by the platform). Backend and
API use the modern `he` code.

## 13. Notifications
Implemented client-side (AlarmManager, daily morning-weight reminder at 07:00 and
weekly-review notification), deliberately minimal to avoid notification fatigue.

## 14. Analytics
Backend-only events table (`analytics_events`) with minimal properties; no third-party
SDK, no unnecessary personal data.
