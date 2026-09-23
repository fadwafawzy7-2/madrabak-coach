"""Test fixtures: dedicated test database with migrations + seed, API client."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATABASE_URL"] = "postgresql+psycopg://coach:coach_dev_password@localhost:5432/coach_test"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app import db as app_db
from app.db import run_migrations

TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DB_URL, future=True)
    # reset schema
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    run_migrations(engine, Path(__file__).parent.parent / "migrations")
    from seeds.dev_foods_seed import seed_foods
    seed_foods(engine)
    app_db.set_engine(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(test_engine):
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def auth_user(client):
    """Registered user with completed profile + computed target."""
    import uuid
    email = f"test-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.put("/api/profile", headers=headers, json={
        "age": 30, "sex": "male", "height_cm": 178, "weight_kg": 80,
        "sport": "bodybuilding", "primary_goal": "lose_fat", "activity_level": "light",
        "training_days_per_week": 4, "training_duration_min": 60,
        "training_intensity": "moderate", "language": "ar", "onboarding_completed": True,
    })
    assert r.status_code == 200, r.text
    r = client.post("/api/nutrition/targets/recalculate", headers=headers)
    assert r.status_code == 200, r.text
    return {"headers": headers, "email": email, "user_id": r.json().get("user_id"), "target": r.json()}
