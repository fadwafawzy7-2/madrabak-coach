"""Subscription service. Backend is the FINAL source of subscription state.

Model: 14-day free trial → $4.99/month via Google Play Billing.
Statuses: trial | active | expired | cancelled | billing_issue.

SubscriptionProvider abstraction:
- GooglePlayVerifier: verifies a purchase token against the Google Play
  Developer API (androidpublisher v3). Requires GOOGLE_PLAY_SERVICE_ACCOUNT_JSON;
  without credentials it runs in stub mode (dev only, clearly marked) so the
  full flow is implemented and only needs the credential to activate.
"""
from __future__ import annotations

import abc
import datetime as dt

from fastapi import HTTPException, Depends
from sqlalchemy import text

from ..db import db_conn
from ..settings import get_settings
from .auth import get_current_user_id


class SubscriptionProvider(abc.ABC):
    @abc.abstractmethod
    async def verify_purchase(self, package_name: str, product_id: str, purchase_token: str) -> dict:
        """Returns {'valid': bool, 'expiry': datetime|None, 'auto_renewing': bool,
        'payment_state': 'ok'|'pending'|'failed'}"""


class GooglePlayVerifier(SubscriptionProvider):
    """Real implementation calls:
    GET https://androidpublisher.googleapis.com/androidpublisher/v3/applications/
        {packageName}/purchases/subscriptions/{subscriptionId}/tokens/{token}
    authenticated with a service-account OAuth token.
    """

    def __init__(self, service_account_json_path: str):
        self._sa_path = service_account_json_path

    async def verify_purchase(self, package_name: str, product_id: str, purchase_token: str) -> dict:
        import json

        import httpx

        # Build a service-account JWT and exchange it for an access token.
        import jwt as pyjwt
        sa = json.loads(open(self._sa_path).read())
        now = int(dt.datetime.now(dt.timezone.utc).timestamp())
        assertion = pyjwt.encode(
            {"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/androidpublisher",
             "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600},
            sa["private_key"], algorithm="RS256",
        )
        async with httpx.AsyncClient(timeout=30) as client:
            tok = await client.post("https://oauth2.googleapis.com/token", data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
            tok.raise_for_status()
            access = tok.json()["access_token"]
            resp = await client.get(
                f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
                f"{package_name}/purchases/subscriptions/{product_id}/tokens/{purchase_token}",
                headers={"Authorization": f"Bearer {access}"},
            )
        if resp.status_code != 200:
            return {"valid": False, "expiry": None, "auto_renewing": False, "payment_state": "failed"}
        data = resp.json()
        expiry_ms = int(data.get("expiryTimeMillis", 0))
        expiry = dt.datetime.fromtimestamp(expiry_ms / 1000, tz=dt.timezone.utc) if expiry_ms else None
        payment_state = {0: "pending", 1: "ok", 2: "ok", 3: "failed"}.get(data.get("paymentState"), "failed")
        return {"valid": expiry is not None and expiry > dt.datetime.now(dt.timezone.utc),
                "expiry": expiry, "auto_renewing": bool(data.get("autoRenewing")), "payment_state": payment_state}


class StubPlayVerifier(SubscriptionProvider):
    """DEV ONLY. Accepts tokens starting with 'dev-valid'; anything else fails."""

    async def verify_purchase(self, package_name: str, product_id: str, purchase_token: str) -> dict:
        if purchase_token.startswith("dev-valid"):
            return {"valid": True, "expiry": dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30),
                    "auto_renewing": True, "payment_state": "ok"}
        return {"valid": False, "expiry": None, "auto_renewing": False, "payment_state": "failed"}


def get_subscription_provider() -> SubscriptionProvider:
    s = get_settings()
    if s.google_play_service_account_json:
        return GooglePlayVerifier(s.google_play_service_account_json)
    return StubPlayVerifier()


def get_subscription_status(user_id: str) -> dict:
    with db_conn() as conn:
        row = conn.execute(
            text("SELECT * FROM subscriptions WHERE user_id = :u"), {"u": user_id}
        ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="subscription_not_found")
    status = row["status"]
    now = dt.datetime.now(dt.timezone.utc)
    # trial expiry is evaluated server-side on every read
    if status == "trial" and row["trial_ends_at"] < now:
        status = "expired"
        with db_conn() as conn:
            conn.execute(text("UPDATE subscriptions SET status = 'expired', updated_at = now() WHERE user_id = :u"),
                         {"u": user_id})
    if status == "active" and row["current_period_end"] and row["current_period_end"] < now:
        status = "expired"
        with db_conn() as conn:
            conn.execute(text("UPDATE subscriptions SET status = 'expired', updated_at = now() WHERE user_id = :u"),
                         {"u": user_id})
    return {
        "status": status,
        "trial_ends_at": row["trial_ends_at"].isoformat(),
        "current_period_end": row["current_period_end"].isoformat() if row["current_period_end"] else None,
        "price_usd_month": get_settings().subscription_price_usd,
        "has_access": status in ("trial", "active"),
    }


async def verify_and_apply_purchase(user_id: str, product_id: str, purchase_token: str,
                                    provider: SubscriptionProvider | None = None) -> dict:
    provider = provider or get_subscription_provider()
    s = get_settings()
    result = await provider.verify_purchase(s.google_play_package_name, product_id, purchase_token)
    if result["payment_state"] == "failed" or not result["valid"]:
        new_status = "billing_issue" if result["payment_state"] == "pending" else None
        if new_status:
            with db_conn() as conn:
                conn.execute(text("UPDATE subscriptions SET status = :s, updated_at = now() WHERE user_id = :u"),
                             {"s": new_status, "u": user_id})
        raise HTTPException(status_code=402, detail={"code": "purchase_verification_failed"})
    with db_conn() as conn:
        conn.execute(
            text("UPDATE subscriptions SET status = 'active', play_purchase_token = :t, play_product_id = :p, "
                 "current_period_end = :e, last_verified_at = now(), updated_at = now() WHERE user_id = :u"),
            {"t": purchase_token, "p": product_id, "e": result["expiry"], "u": user_id},
        )
    return get_subscription_status(user_id)


def cancel_subscription(user_id: str) -> dict:
    with db_conn() as conn:
        conn.execute(text("UPDATE subscriptions SET status = 'cancelled', updated_at = now() WHERE user_id = :u"),
                     {"u": user_id})
    return get_subscription_status(user_id)


async def require_active_access(user_id: str = Depends(get_current_user_id)) -> str:
    """Dependency for paid features (AI chat/suggestions/photo analysis): blocks
    access once the trial has ended and no active subscription exists. Read-only
    / deterministic endpoints (dashboard, meal logging, coach/remaining) stay
    free of this check so a lapsed user can still see their own data."""
    status = get_subscription_status(user_id)
    if not status["has_access"]:
        raise HTTPException(status_code=402, detail={"code": "subscription_expired"})
    return user_id
