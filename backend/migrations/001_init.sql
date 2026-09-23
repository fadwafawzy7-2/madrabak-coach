-- مدربك الخاص — initial schema
-- Migration 001

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,                -- NULL when using external auth provider (Supabase)
    auth_provider TEXT NOT NULL DEFAULT 'local',
    external_auth_id TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT,
    age INT,
    sex TEXT CHECK (sex IN ('male','female')),
    height_cm NUMERIC(5,1),
    weight_kg NUMERIC(5,1),
    sport TEXT CHECK (sport IN ('bodybuilding','strength','calisthenics','running','football','non_athlete')),
    primary_goal TEXT,
    secondary_goal TEXT,
    activity_level TEXT CHECK (activity_level IN ('sedentary','light','moderate','high')),
    training_days_per_week INT DEFAULT 0,
    training_duration_min INT DEFAULT 0,
    training_intensity TEXT CHECK (training_intensity IN ('low','moderate','high')) DEFAULT 'moderate',
    usual_training_time TEXT,
    matches_per_week INT DEFAULT 0,
    matches_replace_training_day BOOLEAN NOT NULL DEFAULT TRUE,
    budget_tier TEXT CHECK (budget_tier IN ('low','medium','high')) DEFAULT 'medium',
    food_preferences JSONB NOT NULL DEFAULT '[]'::jsonb,
    language TEXT NOT NULL DEFAULT 'ar',
    units_system TEXT NOT NULL DEFAULT 'metric',
    height_unit TEXT NOT NULL DEFAULT 'cm',
    weight_unit TEXT NOT NULL DEFAULT 'kg',
    timezone TEXT NOT NULL DEFAULT 'Asia/Jerusalem',
    notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS body_measurements (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind TEXT NOT NULL CHECK (kind IN ('weight','waist','neck','arm','hip','height')),
    value_normalized NUMERIC(6,2) NOT NULL,   -- kg for weight, cm for lengths
    is_morning BOOLEAN NOT NULL DEFAULT FALSE,
    note TEXT
);
CREATE INDEX IF NOT EXISTS ix_meas_user_kind_time ON body_measurements(user_id, kind, measured_at DESC);

CREATE TABLE IF NOT EXISTS body_fat_estimates (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    estimated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    method TEXT NOT NULL DEFAULT 'us_navy',
    body_fat_pct NUMERIC(4,1) NOT NULL,
    inputs JSONB NOT NULL,
    engine_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS foods (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    alternative_names JSONB NOT NULL DEFAULT '[]'::jsonb,
    language TEXT NOT NULL DEFAULT 'ar',
    kcal_per_100g NUMERIC(6,1) NOT NULL,
    protein_per_100g NUMERIC(5,1) NOT NULL,
    carbs_per_100g NUMERIC(5,1) NOT NULL,
    fat_per_100g NUMERIC(5,1) NOT NULL,
    fiber_per_100g NUMERIC(5,1) NOT NULL DEFAULT 0,
    source TEXT NOT NULL,
    confidence_level TEXT NOT NULL CHECK (confidence_level IN ('verified','estimated')),
    is_dev_seed BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_foods_name ON foods(lower(name));

CREATE TABLE IF NOT EXISTS meals (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    meal_type TEXT NOT NULL CHECK (meal_type IN ('breakfast','lunch','dinner','snack')),
    eaten_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source TEXT NOT NULL CHECK (source IN ('text','photo','manual')),
    status TEXT NOT NULL DEFAULT 'final' CHECK (status IN ('draft','final')),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_meals_user_time ON meals(user_id, eaten_at DESC);

CREATE TABLE IF NOT EXISTS meal_items (
    id UUID PRIMARY KEY,
    meal_id UUID NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    food_id UUID REFERENCES foods(id),
    food_name TEXT NOT NULL,
    quantity_g NUMERIC(7,1) NOT NULL,
    unit_entered TEXT NOT NULL DEFAULT 'g',
    quantity_entered NUMERIC(7,1) NOT NULL,
    is_estimated BOOLEAN NOT NULL DEFAULT FALSE,
    kcal NUMERIC(7,1) NOT NULL,
    protein_g NUMERIC(6,1) NOT NULL,
    carbs_g NUMERIC(6,1) NOT NULL,
    fat_g NUMERIC(6,1) NOT NULL,
    fiber_g NUMERIC(6,1) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nutrition_targets (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    bmr_kcal INT NOT NULL,
    tdee_kcal INT NOT NULL,
    target_kcal INT NOT NULL,
    protein_g INT NOT NULL,
    carbs_g INT NOT NULL,
    fat_g INT NOT NULL,
    adjustment_kcal INT NOT NULL,          -- negative = deficit, positive = surplus
    day_type TEXT NOT NULL DEFAULT 'training',
    engine_version TEXT NOT NULL,
    nutrition_rules_version TEXT NOT NULL,
    safety_rules_version TEXT NOT NULL,
    inputs JSONB NOT NULL,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_targets_user ON nutrition_targets(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS weekly_reviews (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    data JSONB NOT NULL,
    UNIQUE (user_id, week_start)
);

CREATE TABLE IF NOT EXISTS coach_context_snapshots (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    snapshot JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS coach_messages (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    safety_flag TEXT
);
CREATE INDEX IF NOT EXISTS ix_coach_msgs ON coach_messages(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS subscriptions (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('trial','active','expired','cancelled','billing_issue')),
    trial_started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    trial_ends_at TIMESTAMPTZ NOT NULL,
    play_purchase_token TEXT,
    play_product_id TEXT,
    current_period_end TIMESTAMPTZ,
    last_verified_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_usage_events (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    estimated_cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_ai_usage ON ai_usage_events(user_id, endpoint, created_at DESC);

CREATE TABLE IF NOT EXISTS safety_flags (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    flag_type TEXT NOT NULL,
    context TEXT,
    severity TEXT NOT NULL DEFAULT 'info'
);

CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_name TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_analytics ON analytics_events(event_name, created_at DESC);

CREATE TABLE IF NOT EXISTS nutrition_rules_config (
    version TEXT PRIMARY KEY,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    rules JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS safety_rules_config (
    version TEXT PRIMARY KEY,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    rules JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO schema_migrations(version) VALUES ('001_init') ON CONFLICT DO NOTHING;
