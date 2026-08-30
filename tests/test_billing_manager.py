# tests/test_billing_manager.py

import tempfile
from pathlib import Path

import pytest

from managers.billing_manager import PLAN_FREE, PLAN_PRO, BillingManager
from managers.database_manager import DatabaseManager


@pytest.fixture
def test_setup():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test_billing.db")
        billing = BillingManager(db=db)
        user = db.create_user("charlie", "mockhash", email="charlie@example.com")
        yield db, billing, user


def test_free_tier_limits(test_setup):
    db, billing, user = test_setup
    info = billing.get_user_plan_info(user["id"])
    assert info["plan"] == PLAN_FREE
    assert info["max_servers"] == 2
    assert info["server_count"] == 0
    assert info["can_add_server"] is True

    # Add 2 servers (allowed)
    db.add_server(user["id"], "Server 1", agent_token="tok_1")
    db.add_server(user["id"], "Server 2", agent_token="tok_2")

    can_add, err = billing.can_user_add_server(user["id"])
    assert can_add is False
    assert "limit reached" in err.lower()


def test_upgrade_and_pro_tier_limits(test_setup):
    db, billing, user = test_setup
    # Upgrade to Pro
    db.update_user_plan(user["id"], plan=PLAN_PRO, stripe_customer_id="cus_pro_123")

    info = billing.get_user_plan_info(user["id"])
    assert info["plan"] == PLAN_PRO
    assert info["max_servers"] == 9999
    assert info["automated_cloud_backups"] is True

    # Add 3 servers (allowed on Pro)
    db.add_server(user["id"], "Server 1", agent_token="tok_1")
    db.add_server(user["id"], "Server 2", agent_token="tok_2")
    db.add_server(user["id"], "Server 3", agent_token="tok_3")

    can_add, err = billing.can_user_add_server(user["id"])
    assert can_add is True
    assert err is None


def test_checkout_and_portal_sessions(test_setup):
    db, billing, user = test_setup
    checkout_url, err = billing.create_checkout_session(
        user["id"],
        success_url="https://deploy.njorddeploy.com/billing/success",
        cancel_url="https://deploy.njorddeploy.com/billing/cancel",
        interval="yearly",
    )
    assert err is None
    assert checkout_url is not None and checkout_url.startswith("https://")

    portal_url, err = billing.create_customer_portal_session(
        user["id"],
        return_url="https://deploy.njorddeploy.com/settings",
    )
    assert err is None
    assert portal_url is not None and portal_url.startswith("https://")


def test_webhook_event_handling(test_setup):
    import json

    db, billing, user = test_setup

    # Test checkout.session.completed webhook
    payload = json.dumps(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "client_reference_id": str(user["id"]),
                    "customer": "cus_test_999",
                    "subscription": "sub_test_888",
                }
            },
        }
    ).encode("utf-8")

    success, msg = billing.handle_webhook_event(payload, "")
    assert success is True

    # User should now be upgraded to Pro
    user_updated = db.get_user_by_id(user["id"])
    assert user_updated["plan"] == PLAN_PRO
    assert user_updated["stripe_customer_id"] == "cus_test_999"

    # Test customer.subscription.deleted webhook (cancellation)
    payload_cancel = json.dumps(
        {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test_888",
                    "customer": "cus_test_999",
                    "status": "canceled",
                }
            },
        }
    ).encode("utf-8")

    success, msg = billing.handle_webhook_event(payload_cancel, "")
    assert success is True

    user_canceled = db.get_user_by_id(user["id"])
    assert user_canceled["plan"] == PLAN_FREE
