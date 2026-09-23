# مدربك الخاص — Your Personal Coach

A personal nutrition & fitness coach: Android app (Kotlin / Jetpack Compose / Material 3)
+ FastAPI backend + PostgreSQL. The AI is the conversational interface — **never** the
numerical source of truth.

## Four sources of truth

| Source | Owns |
|---|---|
| **Nutrition Engine** (`backend/app/engine/nutrition_engine.py`) | BMR (Mifflin-St Jeor), TDEE, calorie target, protein/carbs/fat, deficit/surplus. Pure & deterministic — no AI, no network. Versioned (`engine_version`, `nutrition_rules_version`, `safety_rules_version`); historical targets are never mutated. |
| **Food Database** (`foods` table, per-100g) | Food calories, protein, carbs, fat, fiber. AI can never invent values — unmatched foods are returned as `unmatched` and the user must pick. |
| **User Data** (`profiles`, `body_measurements`) | Age, sex, height, weight, sport, goals, activity, preferences. Normalized internally to kg/cm. |
| **AI** (Groq chat / Gemini vision, behind adapters) | Conversation, explanation, suggestions. Receives compact context built by `CoachContextBuilder`; every reply passes safety pre/post checks; AI can never mutate targets/macros/profile. |

## Repository layout

```
madrabak-coach/
├── backend/
│   ├── app/
│   │   ├── engine/nutrition_engine.py   # deterministic engine + US Navy body fat + unit conversion
│   │   ├── providers/                   # AiChatProvider (Groq/stub), VisionProvider (Gemini/stub)
│   │   ├── safety/guardrails.py         # safety layer (config-driven, versioned)
│   │   ├── services/                    # auth, nutrition, foods, meals, coach, suggestions,
│   │   │                                # progress, subscriptions, rules loader
│   │   ├── routers/api.py               # all endpoints (JWT-protected)
│   │   ├── main.py                      # FastAPI app + rate limiting + safe error handling
│   │   └── settings.py                  # env-var configuration (no secrets in code)
│   ├── config/                          # nutrition_rules_v1.json, safety_rules_v1.json
│   ├── migrations/001_init.sql          # full schema (17 tables)
│   ├── seeds/dev_foods_seed.py          # DEV-ONLY food data (marked is_dev_seed)
│   ├── tests/                           # 78 tests: engine, safety, API, integration
│   ├── run_migrations.py
│   ├── requirements.txt
│   └── .env.example
├── android/                             # Kotlin + Compose + Material 3, single module
│   └── app/src/main/java/com/madrabak/coach/
│       ├── data/api/                    # Retrofit models + service (no secrets)
│       ├── data/repo/                   # session store, API provider, error mapping
│       ├── ui/screens/                  # Auth, Onboarding, Home(يومك), Food, Progress, Coach, Account
│       ├── ui/theme/                    # Material 3 light/dark
│       └── util/                        # MacroMath, validators, notifications, BillingManager
└── docs/DECISIONS.md                    # ambiguity resolutions & provisional values
```

## Run the backend

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env                       # fill values as needed
# PostgreSQL: create db + user matching DATABASE_URL, then:
python run_migrations.py --seed            # migrations + dev food seed
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# API docs: http://localhost:8000/docs
```

Tests:

```bash
# needs a coach_test database (see tests/conftest.py)
python -m pytest tests/ -q
```

## Run / build the Android app

```bash
cd android
# local.properties must point at your Android SDK (sdk.dir=...)
./gradlew assembleDebug          # or: gradle assembleDebug
./gradlew testDebugUnitTest
```

The debug build points at `http://10.0.2.2:8000/api/` (emulator → host backend).
Change `API_BASE_URL` in `app/build.gradle.kts` for a real device / production.

## Environment variables (backend/.env)

| Variable | Purpose | Required for |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection | always |
| `JWT_SECRET` | token signing | always (change in prod) |
| `GROQ_API_KEY`, `GROQ_MODEL` | AI coach chat | live AI (stub otherwise) |
| `GEMINI_API_KEY`, `GEMINI_VISION_MODEL` | food photo analysis | live vision (stub otherwise) |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | optional Supabase Postgres/auth/storage | optional |
| `GOOGLE_PLAY_PACKAGE_NAME`, `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | Play purchase verification | production billing |

Without AI keys, providers run in clearly-marked **stub mode**: the whole product flow
works offline and activating real AI is just setting the env var — no code changes.

## Safety highlights

- Config-driven guardrails (`config/safety_rules_v1.json`, overridable via DB table).
- Eating-disorder / medical intents get scripted safe responses in the user's language; the AI is never called.
- AI output is post-checked before reaching the user.
- Users under 18: conservative mode — weight-loss goals replaced with maintenance, deficit capped.
- Minimum-calorie floors; deficit/surplus clamps; `constraint_conflict` instead of silent macro fallbacks.
- Body fat is always labeled an **estimate** (US Navy formula) and never drives calorie decisions.
- AI daily limits + full cost logging in `ai_usage_events` (changeable without app updates).

## Subscription

14-day free trial starts at registration (server-side). $4.99/month via Google Play
Billing; the app sends purchase tokens to `/api/subscription/verify` and the backend
(Google Play Developer API) is the final source of subscription state.
