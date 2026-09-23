"""Backend API tests: auth, authorization, nutrition, meals, AI, subscription."""
import io
import uuid


def _register(client, password="password123"):
    email = f"t-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    return email, {"Authorization": f"Bearer {r.json()['token']}"}


# ---------------- auth

def test_register_and_login(client):
    email, _ = _register(client)
    r = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200 and "token" in r.json()


def test_login_wrong_password(client):
    email, _ = _register(client)
    r = client.post("/api/auth/login", json={"email": email, "password": "wrongpass123"})
    assert r.status_code == 401


def test_duplicate_email(client):
    email, _ = _register(client)
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 409


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "x@example.com", "password": "short"})
    assert r.status_code == 422


def test_unauthenticated_rejected(client):
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/dashboard/today").status_code == 401
    assert client.post("/api/coach/chat", json={"message": "hi"}).status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/api/profile", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


# ---------------- profile → nutrition target integration

def test_profile_to_target_flow(auth_user):
    t = auth_user["target"]
    assert t["target_kcal"] > 1200
    assert t["protein_g"] == round(2.2 * 80)  # bodybuilding deficit
    assert t["engine_version"].startswith("engine-")


def test_target_requires_complete_profile(client):
    _, headers = _register(client)
    r = client.post("/api/nutrition/targets/recalculate", headers=headers)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "missing_data"


def test_invalid_measurement_rejected(client):
    _, headers = _register(client)
    r = client.put("/api/profile", headers=headers, json={"weight_kg": 500})
    assert r.status_code == 422


def test_young_user_conservative(client):
    _, headers = _register(client)
    client.put("/api/profile", headers=headers, json={
        "age": 16, "sex": "male", "height_cm": 175, "weight_kg": 70,
        "sport": "football", "primary_goal": "lose_weight", "activity_level": "moderate",
        "training_days_per_week": 3, "training_duration_min": 90, "matches_per_week": 1,
    })
    r = client.post("/api/nutrition/targets/recalculate", headers=headers)
    assert r.status_code == 200
    data = r.json()
    # goal replaced with maintain → adjustment 0 (no aggressive deficit)
    assert data["adjustment_kcal"] >= -250
    assert "young_user_goal_adjusted" in data["warnings"] or "young_user_conservative_mode" in data["warnings"]


# ---------------- foods & meals

def test_food_search(client, auth_user):
    r = client.get("/api/foods/search", params={"q": "دجاج"}, headers=auth_user["headers"])
    assert r.status_code == 200
    assert any("دجاج" in f["name"] for f in r.json()["results"])


def test_meal_logging_and_totals(client, auth_user):
    h = auth_user["headers"]
    r = client.get("/api/foods/search", params={"q": "أرز"}, headers=h)
    rice = r.json()["results"][0]
    r = client.post("/api/meals", headers=h, json={
        "meal_type": "lunch", "source": "manual",
        "items": [{"food_id": rice["id"], "quantity": 200, "unit": "g"}],
    })
    assert r.status_code == 200
    meal = r.json()
    assert meal["totals"]["kcal"] == round(rice["kcal_per_100g"] * 2, 1)

    import datetime as dt
    r = client.get(f"/api/meals/day/{dt.date.today().isoformat()}", headers=h)
    assert r.status_code == 200
    assert r.json()["totals"]["kcal"] >= meal["totals"]["kcal"]


def test_meal_unknown_food_rejected(client, auth_user):
    r = client.post("/api/meals", headers=auth_user["headers"], json={
        "meal_type": "snack", "source": "text",
        "items": [{"food_name": "zzzz-does-not-exist-9999", "quantity": 100}],
    })
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "unknown_food"


def test_meal_by_name_and_units(client, auth_user):
    r = client.post("/api/meals", headers=auth_user["headers"], json={
        "meal_type": "breakfast", "source": "text",
        "items": [{"food_name": "بيض", "quantity": 2, "unit": "piece"}],
    })
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["quantity_g"] == 200.0  # 2 pieces * 100 g


def test_user_cannot_access_others_meal(client, auth_user):
    h1 = auth_user["headers"]
    r = client.post("/api/meals", headers=h1, json={
        "meal_type": "snack", "source": "manual",
        "items": [{"food_name": "تمر", "quantity": 50}],
    })
    meal_id = r.json()["id"]
    _, h2 = _register(client)
    r = client.delete(f"/api/meals/{meal_id}", headers=h2)
    assert r.status_code == 404  # not found for another user


# ---------------- photo → draft → confirm integration

def test_photo_draft_flow(client, auth_user):
    h = auth_user["headers"]
    fake_image = io.BytesIO(b"\xff\xd8\xff\xe0fakejpegdata")
    r = client.post("/api/meals/analyze-photo", headers=h,
                    files={"image": ("meal.jpg", fake_image, "image/jpeg")},
                    data={"language": "ar"})
    assert r.status_code == 200
    draft = r.json()["draft_items"]
    assert len(draft) == 2
    matched = [d for d in draft if d["matched"]]
    assert matched, "stub foods should match seeded DB"
    # user edits quantity then confirms as a final meal
    item = matched[0]
    r = client.post("/api/meals", headers=h, json={
        "meal_type": "dinner", "source": "photo",
        "items": [{"food_id": item["food_id"], "quantity": 180, "unit": "g", "is_estimated": True}],
    })
    assert r.status_code == 200
    assert r.json()["items"][0]["is_estimated"] is True


def test_empty_image_rejected(client, auth_user):
    r = client.post("/api/meals/analyze-photo", headers=auth_user["headers"],
                    files={"image": ("x.jpg", io.BytesIO(b""), "image/jpeg")})
    assert r.status_code == 422


# ---------------- progress

def test_weight_logging_and_summary(client, auth_user):
    h = auth_user["headers"]
    r = client.post("/api/progress/measurements", headers=h,
                    json={"kind": "weight", "value": 80.5, "is_morning": True})
    assert r.status_code == 200
    r = client.get("/api/progress/weight-summary", headers=h)
    assert r.status_code == 200
    assert r.json()["weekly_averages"]


def test_invalid_measurement_value(client, auth_user):
    r = client.post("/api/progress/measurements", headers=auth_user["headers"],
                    json={"kind": "weight", "value": 999})
    assert r.status_code == 422


def test_body_fat_estimate(client, auth_user):
    r = client.post("/api/progress/body-fat", headers=auth_user["headers"],
                    json={"waist_cm": 85, "neck_cm": 38})
    assert r.status_code == 200
    data = r.json()
    assert 5 < data["estimated_body_fat_pct"] < 40
    assert "ESTIMATE" in data["disclaimer"]


def test_body_fat_invalid_measurements(client, auth_user):
    r = client.post("/api/progress/body-fat", headers=auth_user["headers"],
                    json={"waist_cm": 30, "neck_cm": 45})
    assert r.status_code == 422


def test_weekly_review(client, auth_user):
    r = client.post("/api/progress/weekly-review", headers=auth_user["headers"])
    assert r.status_code == 200
    data = r.json()
    assert "went_well" in data and "needs_attention" in data and "suggestions" in data


# ---------------- dashboard

def test_dashboard_today(client, auth_user):
    r = client.get("/api/dashboard/today", headers=auth_user["headers"])
    assert r.status_code == 200
    data = r.json()
    assert data["target"]["kcal"] > 0
    assert "remaining" in data and "consumed" in data


# ---------------- AI coach (stub provider — deterministic offline)

def test_coach_chat_and_history(client, auth_user):
    h = auth_user["headers"]
    r = client.post("/api/coach/chat", headers=h, json={"message": "ماذا آكل بعد التمرين؟"})
    assert r.status_code == 200
    assert not r.json()["blocked"]
    r = client.get("/api/coach/history", headers=h)
    assert len(r.json()["messages"]) >= 2


def test_coach_blocks_eating_disorder(client, auth_user):
    r = client.post("/api/coach/chat", headers=auth_user["headers"],
                    json={"message": "أريد تجويع نفسي"})
    assert r.status_code == 200
    data = r.json()
    assert data["blocked"] and data["flag"] == "eating_disorder"
    assert "مختص" in data["reply"]


def test_what_to_eat_uses_engine_numbers(client, auth_user):
    r = client.post("/api/coach/what-to-eat", headers=auth_user["headers"])
    assert r.status_code == 200
    data = r.json()
    assert data["numbers"]["remaining"]["kcal"] <= data["numbers"]["target"]["kcal"]
    assert data["suggestion"]


def test_ingredients_feature(client, auth_user):
    r = client.post("/api/coach/ingredients", headers=auth_user["headers"],
                    json={"ingredients": ["دجاج", "رز", "بيض", "قنبيط-غير-موجود"]})
    assert r.status_code == 200
    data = r.json()
    assert data["matched_ingredients"]
    assert "قنبيط-غير-موجود" in data["unmatched_ingredients"]


def test_save_my_day(client, auth_user):
    r = client.post("/api/coach/save-my-day", headers=auth_user["headers"])
    assert r.status_code == 200
    assert r.json()["suggestion"]


def test_remaining_endpoint_deterministic(client, auth_user):
    r = client.get("/api/coach/remaining", headers=auth_user["headers"])
    assert r.status_code == 200
    assert r.json()["target"]["kcal"] == auth_user["target"]["target_kcal"]


# ---------------- subscription

def test_trial_started_on_register(client, auth_user):
    r = client.get("/api/subscription", headers=auth_user["headers"])
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "trial" and data["has_access"]
    assert data["price_usd_month"] == 4.99


def test_purchase_verify_stub(client, auth_user):
    h = auth_user["headers"]
    r = client.post("/api/subscription/verify", headers=h,
                    json={"product_id": "monthly_499", "purchase_token": "dev-valid-token"})
    assert r.status_code == 200
    assert r.json()["status"] == "active"


def test_purchase_verify_failure(client, auth_user):
    r = client.post("/api/subscription/verify", headers=auth_user["headers"],
                    json={"product_id": "monthly_499", "purchase_token": "bad-token"})
    assert r.status_code == 402


def test_cancel_subscription(client):
    _, h = _register(client)
    r = client.post("/api/subscription/cancel", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


# ---------------- privacy

def test_delete_data(client, auth_user):
    h = auth_user["headers"]
    client.post("/api/progress/measurements", headers=h, json={"kind": "weight", "value": 80})
    r = client.delete("/api/account/data", headers=h)
    assert r.status_code == 200
    r = client.get("/api/progress/measurements/weight", headers=h)
    assert r.json()["measurements"] == []


def test_delete_account(client):
    email, h = _register(client)
    r = client.delete("/api/account", headers=h)
    assert r.status_code == 200
    r = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 401
