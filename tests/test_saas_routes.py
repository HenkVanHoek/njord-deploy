# tests/test_saas_routes.py

import json
import tempfile
from pathlib import Path

import pytest

from configurator_app.app import create_app
from managers.database_manager import DatabaseManager


@pytest.fixture
def saas_client():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_saas_app.db"
        DatabaseManager._instance = DatabaseManager(db_file)

        app = create_app(
            test_config={
                "TESTING": True,
                "AUTH_ENABLED": True,
                "SECRET_KEY": "test-secret-key-saas",
            }
        )
        with app.test_client() as client:
            yield client, DatabaseManager._instance


def test_public_saas_routes_accessible(saas_client):
    client, _ = saas_client
    # /register
    resp = client.get("/register")
    assert resp.status_code == 200

    # /install-agent
    resp_script = client.get("/install-agent?token=test_tok_123")
    assert resp_script.status_code == 200
    assert b"#!/usr/bin/env bash" in resp_script.data
    assert b"test_tok_123" in resp_script.data


def test_registration_and_server_management_flow(saas_client):
    client, db = saas_client

    # 1. Register User
    reg_resp = client.post(
        "/api/register",
        json={
            "username": "eval_user",
            "password": "SecurePassword123!",
            "email": "eval@example.com",
        },
    )
    assert reg_resp.status_code == 201
    data = reg_resp.get_json()
    assert data["status"] == "success"
    assert data["plan"] == "free"

    # 2. Add First Server
    s1_resp = client.post(
        "/api/servers/add", json={"name": "Pi 5 Ingress", "ip": "192.168.178.10"}
    )
    assert s1_resp.status_code == 201
    s1_data = s1_resp.get_json()
    token1 = s1_data["server"]["agent_token"]
    assert "curl -sSL" in s1_data["install_command"]

    # 3. Send Heartbeat from Agent
    hb_resp = client.post(
        "/api/agent/heartbeat",
        headers={"X-Njord-Agent-Token": token1},
        json={
            "hostname": "pi5-ingress",
            "os_info": "Raspberry Pi OS Bookworm",
            "memory": "1.2/8.0 GB",
        },
    )
    assert hb_resp.status_code == 200
    assert hb_resp.get_json()["status"] == "acknowledged"

    # 4. Check Server List
    list_resp = client.get("/api/servers")
    assert list_resp.status_code == 200
    servers = list_resp.get_json()["servers"]
    assert len(servers) == 1
    assert servers[0]["status"] == "online"

    # 5. Add Second Server (Allowed on Free)
    s2_resp = client.post(
        "/api/servers/add", json={"name": "VPS Node", "ip": "37.120.176.26"}
    )
    assert s2_resp.status_code == 201

    # 6. Add Third Server (Blocked on Free Tier)
    s3_resp = client.post(
        "/api/servers/add", json={"name": "Extra Node", "ip": "10.0.0.5"}
    )
    assert s3_resp.status_code == 403
    assert s3_resp.get_json()["upgrade_required"] is True


def test_billing_and_webhook_upgrade(saas_client):
    client, db = saas_client

    # Register user
    client.post(
        "/api/register",
        json={
            "username": "premium_user",
            "password": "SecurePassword123!",
            "email": "premium@example.com",
        },
    )

    # Check billing status
    b_resp = client.get("/api/billing/status")
    assert b_resp.status_code == 200
    b_data = b_resp.get_json()["billing"]
    assert b_data["plan"] == "free"

    # Start checkout
    chk_resp = client.post("/api/billing/checkout")
    assert chk_resp.status_code == 200
    assert "checkout_url" in chk_resp.get_json()

    # Simulate Stripe Webhook for upgrade
    user = db.get_user_by_username("premium_user")
    webhook_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "client_reference_id": str(user["id"]),
                "customer": "cus_stripe_premium_123",
                "subscription": "sub_stripe_pro_123",
            }
        },
    }
    wh_resp = client.post(
        "/api/stripe/webhook",
        data=json.dumps(webhook_payload),
        content_type="application/json",
    )
    assert wh_resp.status_code == 200

    # Verify user plan is upgraded to Pro
    updated_b = client.get("/api/billing/status").get_json()["billing"]
    assert updated_b["plan"] == "pro"
    assert updated_b["max_servers"] == 9999
