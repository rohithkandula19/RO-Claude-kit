from __future__ import annotations

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
    return TestClient(make_app(), follow_redirects=False)


def _signup(client: TestClient, email: str = "alice@example.com") -> str:
    return client.post("/signup", json={"email": email}).json()["api_token"]


# ---------- /oauth/{provider}/start ----------

def test_oauth_start_without_config_errors(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without env vars set, /start should 400 with a clear message."""
    monkeypatch.delenv("STRIPE_CLIENT_ID", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_REDIRECT_URI", raising=False)

    h = {"Authorization": f"Bearer {_signup(client)}"}
    r = client.get("/oauth/stripe/start", headers=h)
    assert r.status_code == 400
    assert "not configured" in r.json()["detail"].lower()


def test_oauth_start_unknown_provider(client: TestClient) -> None:
    h = {"Authorization": f"Bearer {_signup(client)}"}
    r = client.get("/oauth/notreal/start", headers=h)
    assert r.status_code == 400
    assert "unknown provider" in r.json()["detail"].lower()


def test_oauth_start_requires_auth(client: TestClient) -> None:
    r = client.get("/oauth/stripe/start")
    assert r.status_code == 401


def test_oauth_start_redirects_when_configured(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_CLIENT_ID", "ca_test_123")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("STRIPE_REDIRECT_URI", "https://csk.local/oauth/stripe/callback")

    h = {"Authorization": f"Bearer {_signup(client)}"}
    r = client.get("/oauth/stripe/start", headers=h)
    assert r.status_code == 302
    location = r.headers["location"]
    assert "connect.stripe.com/oauth/authorize" in location
    assert "client_id=ca_test_123" in location
    assert "state=" in location
    assert "scope=read_only" in location


# ---------- /oauth/{provider}/callback ----------

def test_oauth_callback_exchanges_code_and_stores_connection(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: configure provider, start flow to get a state, simulate Stripe
    POST-ing back with code + state, assert the connection is stored."""
    monkeypatch.setenv("STRIPE_CLIENT_ID", "ca_test_123")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("STRIPE_REDIRECT_URI", "https://csk.local/oauth/stripe/callback")

    h = {"Authorization": f"Bearer {_signup(client, 'bob@example.com')}"}

    # Kick off the flow to get a state token
    start = client.get("/oauth/stripe/start", headers=h)
    assert start.status_code == 302
    state = start.headers["location"].split("state=")[1].split("&")[0]

    # Mock Stripe's token exchange
    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.json.return_value = {"access_token": "sk_acct_received_oauth_token"}
    fake_resp.raise_for_status = MagicMock()
    fake_resp.status_code = 200

    with patch.object(httpx.Client, "post", return_value=fake_resp):
        r = client.get(f"/oauth/stripe/callback?code=abc&state={state}")

    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "service": "stripe"}

    # Connection should now appear in the user's list
    conns = client.get("/connections", headers=h).json()
    assert any(c["service"] == "stripe" for c in conns)


def test_oauth_callback_rejects_bad_state(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_CLIENT_ID", "ca_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("STRIPE_REDIRECT_URI", "https://x/cb")

    r = client.get("/oauth/stripe/callback?code=abc&state=never_issued")
    assert r.status_code == 400
    assert "state" in r.json()["detail"].lower()


def test_oauth_callback_state_cant_be_reused(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each state token is one-shot — reusing it should be rejected."""
    monkeypatch.setenv("STRIPE_CLIENT_ID", "ca_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("STRIPE_REDIRECT_URI", "https://x/cb")

    h = {"Authorization": f"Bearer {_signup(client)}"}
    start = client.get("/oauth/stripe/start", headers=h)
    state = start.headers["location"].split("state=")[1].split("&")[0]

    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.json.return_value = {"access_token": "first_token"}
    fake_resp.raise_for_status = MagicMock()
    with patch.object(httpx.Client, "post", return_value=fake_resp):
        client.get(f"/oauth/stripe/callback?code=abc&state={state}")

    # Replay attempt — should fail
    r = client.get(f"/oauth/stripe/callback?code=abc&state={state}")
    assert r.status_code == 400
