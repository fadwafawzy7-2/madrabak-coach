"""Application settings. All secrets come from environment variables — never hard-coded."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg://coach:coach_dev_password@localhost:5432/coach_dev"

    # Auth
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 30

    # AI providers (empty => providers run in stub mode)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_vision_model: str = "gemini-2.0-flash"

    # Supabase (optional alternative auth/storage backend)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Google Play
    google_play_package_name: str = "com.madrabak.coach"
    google_play_service_account_json: str = ""  # path to service-account file

    # Subscription
    trial_days: int = 14
    subscription_price_usd: float = 4.99

    # Config files
    nutrition_rules_path: str = str(BASE_DIR / "config" / "nutrition_rules_v1.json")
    safety_rules_path: str = str(BASE_DIR / "config" / "safety_rules_v1.json")

    # Environment
    env: str = "dev"

    model_config = {"env_file": str(BASE_DIR / ".env"), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
