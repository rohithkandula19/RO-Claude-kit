from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from csk_api.db import reset_db_for_tests
    reset_db_for_tests(db_url)
    from csk_api.main import make_app
    return TestClient(make_app())


def _signup(client: TestClient) -> str:
    return client.post("/signup", json={"email": "founder@example.com"}).json()["api_token"]


# ---------- /billing/checkout ----------

def test_checkout_requires_auth(client: TestClient) -> None:
    r = client.post("/billing/checkout?plan=pro")
    assert r.status_code == 401


def test_checkout_unknown_plan(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    h = {"Authorization": f"Bearer {_signup(client)}"}
    r = client.post("/billing/checkout?plan=unobtanium", headers=h)
    assert r.status_code == 400
    assert "unknown plan" in r.json()["detail"].lower()


def test_checkout_without_stripe_config_errors_clearly(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    h = {"Authorization": f"Bearer {_signup(client)}"}
    r = client.post("/billing/checkout?plan=pro", headers=h)
    assert r.status_code == 400
    assert "stripe" in r.json()["detail"].lower()


def test_checkout_creates_session(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro_xxx")

    h = {"Authorization": f"Bearer {_signup(client)}"}

    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.json.return_value = {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/cs_test_1"}
    fake_resp.raise_for_status = MagicMock()
    fake_resp.status_code = 200

    with patch.object(httpx.Client, "post", return_value=fake_resp) as mock_post:
        r = client.post("/billing/checkout?plan=pro", headers=h)

    assert r.status_code == 200, r.text
    assert r.json()["url"].startswith("https://checkout.stripe.com/")
    assert mock_post.called  # Stripe's API was hit


# ---------- /webhooks/stripe ----------

def _signed_payload(payload: bytes, secret: str) -> str:
    """Build a valid Stripe-Signature header for a test payload."""
    ts = int(time.time())
    signed = f"{ts}.{payload.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_webhook_rejects_invalid_signature(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    body = b'{"type":"checkout.session.completed"}'
    r = client.post(
        "/webhooks/stripe",
        content=body,
        headers={"Stripe-Signature": "t=0,v1=bogus", "Content-Type": "application/json"},
    )
    assert r.status_code == 400
    assert "signature" in r.json()["detail"].lower()


def test_webhook_upgrades_plan_on_checkout_completed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "whsec_test"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    # First — sign up a user so we have a real user_id to reference
    token = _signup(client)
    me = client.get("/connections", headers={"Authorization": f"Bearer {token}"})  # forces auth path
    assert me.status_code == 200
    # Derive the user_id from the DB (small test seam — we just inserted one user)
    from csk_api.db import _SessionLocal, _get_engine, User
    _get_engine()
    s = _SessionLocal()
    user = s.query(User).first()
    user_id = user.id
    s.close()

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": str(user_id),
                "amount_total": 1900,  # $19 — Pro
            }
        },
    }
    body = json.dumps(event).encode("utf-8")
    headers = {
        "Stripe-Signature": _signed_payload(body, secret),
        "Content-Type": "application/json",
    }
    r = client.post("/webhooks/stripe", content=body, headers=headers)
    assert r.status_code == 200, r.text
    assert "pro" in r.json()["message"].lower()


def test_webhook_downgrades_on_subscription_deleted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "whsec_test"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    token = _signup(client)
    client.get("/connections", headers={"Authorization": f"Bearer {token}"})

    from csk_api.db import _SessionLocal, _get_engine, User, Plan
    _get_engine()
    s = _SessionLocal()
    user = s.query(User).first()
    user.plan = Plan.PRO
    s.commit()
    user_id = user.id
    s.close()

    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"metadata": {"user_id": str(user_id)}}},
    }
    body = json.dumps(event).encode("utf-8")
    headers = {"Stripe-Signature": _signed_payload(body, secret), "Content-Type": "application/json"}
    r = client.post("/webhooks/stripe", content=body, headers=headers)
    assert r.status_code == 200
    assert "free" in r.json()["message"].lower()


# ---------- /billing/portal ----------

def test_portal_requires_auth(client: TestClient) -> None:
    r = client.post("/billing/portal")
    assert r.status_code == 401


def test_portal_errors_without_checkout_history(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stripe needs a customer_id; without one (no prior Checkout), 400."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    h = {"Authorization": f"Bearer {_signup(client)}"}
    r = client.post("/billing/portal", headers=h)
    assert r.status_code == 400
    assert "stripe customer" in r.json()["detail"].lower()


def test_portal_returns_url_when_customer_exists(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    h = {"Authorization": f"Bearer {_signup(client)}"}

    # Seed a Stripe customer ID on the user directly (would normally come
    # from the checkout.session.completed webhook).
    from csk_api.db import User, _SessionLocal, _get_engine
    _get_engine()
    s = _SessionLocal()
    user = s.query(User).first()
    user.stripe_customer_id = "cus_stripe_test_abc"
    s.commit()
    s.close()

    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"url": "https://billing.stripe.com/p/session/test_abc"}
    fake_resp.raise_for_status = MagicMock()

    with patch.object(httpx.Client, "post", return_value=fake_resp) as mock_post:
        r = client.post("/billing/portal", headers=h)

    assert r.status_code == 200, r.text
    assert r.json()["url"].startswith("https://billing.stripe.com/")
    assert mock_post.called


def test_webhook_stashes_stripe_customer_id_on_checkout(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies the customer ID lands on User.stripe_customer_id."""
    secret = "whsec_test"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    token = _signup(client)
    client.get("/connections", headers={"Authorization": f"Bearer {token}"})

    from csk_api.db import User, _SessionLocal, _get_engine
    _get_engine()
    s = _SessionLocal()
    user = s.query(User).first()
    user_id = user.id
    s.close()

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": str(user_id),
                "customer": "cus_from_webhook_xyz",
                "amount_total": 1900,
            }
        },
    }
    body = json.dumps(event).encode("utf-8")
    headers = {"Stripe-Signature": _signed_payload(body, secret), "Content-Type": "application/json"}
    client.post("/webhooks/stripe", content=body, headers=headers)

    # Confirm the field was persisted
    s = _SessionLocal()
    user = s.query(User).first()
    assert user.stripe_customer_id == "cus_from_webhook_xyz"
    s.close()


def test_webhook_ignores_unhandled_event_types(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "whsec_test"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    body = json.dumps({"type": "invoice.paid", "data": {"object": {}}}).encode("utf-8")
    headers = {"Stripe-Signature": _signed_payload(body, secret), "Content-Type": "application/json"}
    r = client.post("/webhooks/stripe", content=body, headers=headers)
    assert r.status_code == 200
    assert "ignored" in r.json()["message"].lower()
