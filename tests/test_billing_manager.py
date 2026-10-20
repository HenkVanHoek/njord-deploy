# tests/test_billing_manager.py

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from managers.billing_manager import (
    PLAN_FREE,
    PLAN_PRO,
    BillingManager,
    configure_stripe_ca_bundle,
)
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


def test_mock_checkout_and_portal_sessions(test_setup, monkeypatch):
    db, _, user = test_setup
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_PRO_PRICE_ID", raising=False)
    monkeypatch.delenv("STRIPE_PRICE_MONTHLY", raising=False)
    monkeypatch.delenv("STRIPE_PRICE_YEARLY", raising=False)

    unconfigured_billing = BillingManager(db=db)
    assert unconfigured_billing.is_configured() is False

    mock_url, err = unconfigured_billing.create_checkout_session(
        user["id"],
        success_url="https://deploy.njorddeploy.com/billing/success",
        cancel_url="https://deploy.njorddeploy.com/billing/cancel",
        interval="yearly",
    )
    assert err is None
    assert mock_url is not None
    assert "mock_checkout=true" in mock_url

    portal_url, err = unconfigured_billing.create_customer_portal_session(
        user["id"],
        return_url="https://deploy.njorddeploy.com/settings",
    )
    assert err is None
    assert portal_url is not None
    assert "mock_portal=true" in portal_url


def test_configure_stripe_ca_bundle(tmp_path, monkeypatch):
    fake_cert = tmp_path / "cert.pem"
    fake_cert.write_text("dummy", encoding="utf-8")

    with patch("managers.billing_manager.stripe") as mock_stripe:
        with patch("os.path.exists", side_effect=lambda p: p == str(fake_cert)):
            configure_stripe_ca_bundle()
            # If cert exists, it sets ca_bundle_path
            assert mock_stripe.ca_bundle_path is not None

        # Test frozen bundle branch
        bundle_crt = tmp_path / "stripe" / "data" / "ca-certificates.crt"
        bundle_crt.parent.mkdir(parents=True, exist_ok=True)
        bundle_crt.write_text("cert", encoding="utf-8")

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        with patch("os.path.exists", side_effect=lambda p: p == str(bundle_crt)):
            configure_stripe_ca_bundle()
            assert mock_stripe.ca_bundle_path == str(bundle_crt)


def test_real_stripe_checkout_session_flow(test_setup, monkeypatch):
    db, _, user = test_setup
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_12345")
    monkeypatch.setenv("STRIPE_PRICE_MONTHLY", "price_month_1")
    monkeypatch.setenv("STRIPE_PRICE_YEARLY", "price_year_2")
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", "pk_test_12345")

    billing = BillingManager(db=db)
    assert billing.is_configured() is True
    assert billing.publishable_key == "pk_test_12345"

    mock_customer = MagicMock()
    mock_customer.id = "cus_created_123"
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/c/pay/cs_test"

    with patch(
        "managers.billing_manager.stripe.Customer.create", return_value=mock_customer
    ):
        with patch(
            "managers.billing_manager.stripe.checkout.Session.create",
            return_value=mock_session,
        ):
            # 1. Monthly checkout (creates customer)
            url, err = billing.create_checkout_session(
                user["id"],
                success_url="https://deploy.njorddeploy.com/billing/success",
                cancel_url="https://deploy.njorddeploy.com/billing/cancel",
                interval="monthly",
            )
            assert err is None
            assert url == "https://checkout.stripe.com/c/pay/cs_test"

            # Check that customer was saved in db
            u = db.get_user_by_id(user["id"])
            assert u["stripe_customer_id"] == "cus_created_123"

            # 2. Yearly checkout (reuses existing customer)
            url_y, err_y = billing.create_checkout_session(
                user["id"],
                success_url="https://deploy.njorddeploy.com/billing/success?step=2",
                cancel_url="https://deploy.njorddeploy.com/billing/cancel",
                interval="yearly",
            )
            assert err_y is None
            assert url_y == "https://checkout.stripe.com/c/pay/cs_test"

            # 3. Fallback when user not in DB creates local_admin
            url_guest, err_guest = billing.create_checkout_session(
                99999,
                success_url="https://deploy.njorddeploy.com/billing/success",
                cancel_url="https://deploy.njorddeploy.com/billing/cancel",
            )
            assert err_guest is None
            assert url_guest is not None

    # Missing price ID test
    billing_noprice = BillingManager(db=db)
    with patch.object(billing_noprice, "is_configured", return_value=True):
        monkeypatch.delenv("STRIPE_PRICE_MONTHLY", raising=False)
        monkeypatch.delenv("STRIPE_PRICE_YEARLY", raising=False)
        monkeypatch.delenv("STRIPE_PRO_PRICE_ID", raising=False)
        url_noprice, err_noprice = billing_noprice.create_checkout_session(
            user["id"],
            success_url="https://deploy.njorddeploy.com/billing/success",
            cancel_url="https://deploy.njorddeploy.com/billing/cancel",
        )
        assert url_noprice is None
        assert "No active Stripe Price ID" in err_noprice

    monkeypatch.setenv("STRIPE_PRICE_MONTHLY", "price_month_1")
    # Error handling when Session.create raises exception
    with patch(
        "managers.billing_manager.stripe.checkout.Session.create",
        side_effect=Exception("Stripe API down"),
    ):
        url_err, err_msg = billing.create_checkout_session(
            user["id"],
            success_url="https://deploy.njorddeploy.com/billing/success",
            cancel_url="https://deploy.njorddeploy.com/billing/cancel",
        )
        assert url_err is None
        assert "Stripe API down" in err_msg


def test_real_stripe_portal_session_flow(test_setup, monkeypatch):
    db, _, user = test_setup
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_12345")
    monkeypatch.setenv("STRIPE_PRICE_MONTHLY", "price_month_1")

    billing = BillingManager(db=db)

    mock_portal = MagicMock()
    mock_portal.url = "https://billing.stripe.com/p/session/portal_123"

    with patch(
        "managers.billing_manager.stripe.billing_portal.Session.create",
        return_value=mock_portal,
    ):
        # User without customer_id: auto creates customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_auto_456"
        with patch(
            "managers.billing_manager.stripe.Customer.create",
            return_value=mock_customer,
        ):
            url, err = billing.create_customer_portal_session(
                user["id"], return_url="https://deploy.njorddeploy.com/settings"
            )
            assert err is None
            assert url == "https://billing.stripe.com/p/session/portal_123"

        # Portal creation fails with exception
        with patch(
            "managers.billing_manager.stripe.billing_portal.Session.create",
            side_effect=Exception("Portal blocked"),
        ):
            url_err, err_msg = billing.create_customer_portal_session(
                user["id"], return_url="https://deploy.njorddeploy.com/settings"
            )
            assert url_err is None
            assert "Portal blocked" in err_msg

    # User with no customer id and user lookup fails
    with patch.object(billing, "is_configured", return_value=True):
        with patch.object(db, "get_user_by_id", return_value=None):
            with patch.object(db, "get_user_by_username", return_value=None):
                u_port, err_port = billing.create_customer_portal_session(
                    999, "https://test"
                )
                assert u_port is None
                assert "No active billing account" in err_port

    # Test webhook when stripe is None
    with patch("managers.billing_manager.stripe", None):
        ok, msg = billing.handle_webhook_event(b"{}", "")
        assert ok is False
        assert "not installed" in msg


def test_webhook_event_handling_extended(test_setup, monkeypatch):
    db, billing, user = test_setup

    # 1. checkout.session.completed with client_reference_id
    payload1 = json.dumps(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "client_reference_id": str(user["id"]),
                    "customer": "cus_test_101",
                    "subscription": "sub_test_101",
                }
            },
        }
    ).encode("utf-8")

    success, _ = billing.handle_webhook_event(payload1, "")
    assert success is True
    u1 = db.get_user_by_id(user["id"])
    assert u1["plan"] == PLAN_PRO
    assert u1["stripe_customer_id"] == "cus_test_101"

    # 2. customer.subscription.created with customer fallback (no client_reference_id)
    payload2 = json.dumps(
        {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test_102",
                    "customer": "cus_test_101",
                }
            },
        }
    ).encode("utf-8")

    success2, _ = billing.handle_webhook_event(payload2, "")
    assert success2 is True

    # 3. Invalid user_id ValueError branch
    payload_bad_id = json.dumps(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_bad",
                    "client_reference_id": "not_an_int",
                    "customer": "cus_test_101",
                }
            },
        }
    ).encode("utf-8")
    success_bad, _ = billing.handle_webhook_event(payload_bad_id, "")
    assert success_bad is True

    # 4. customer.subscription.updated with status trialing
    payload_trial = json.dumps(
        {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_101",
                    "customer": "cus_test_101",
                    "status": "trialing",
                }
            },
        }
    ).encode("utf-8")
    success_trial, _ = billing.handle_webhook_event(payload_trial, "")
    assert success_trial is True
    assert db.get_user_by_id(user["id"])["plan"] == PLAN_PRO

    # 5. customer.subscription.updated with status unpaid / past_due (downgrade)
    payload_downgrade = json.dumps(
        {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_101",
                    "customer": "cus_test_101",
                    "status": "past_due",
                }
            },
        }
    ).encode("utf-8")
    success_down, _ = billing.handle_webhook_event(payload_downgrade, "")
    assert success_down is True
    assert db.get_user_by_id(user["id"])["plan"] == PLAN_FREE

    # 6. invoice payment failed and succeeded
    payload_fail = json.dumps(
        {
            "type": "invoice.payment_failed",
            "data": {"object": {"id": "in_fail_1", "customer": "cus_test_101"}},
        }
    ).encode("utf-8")
    assert billing.handle_webhook_event(payload_fail, "")[0] is True

    payload_succ = json.dumps(
        {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_succ_1", "customer": "cus_test_101"}},
        }
    ).encode("utf-8")
    assert billing.handle_webhook_event(payload_succ, "")[0] is True

    # 7. Signature verification with webhook secret
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    billing_sec = BillingManager(db=db)

    with patch(
        "managers.billing_manager.stripe.Webhook.construct_event"
    ) as mock_construct:
        mock_construct.return_value = {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_1"}},
        }
        ok, msg = billing_sec.handle_webhook_event(b"payload", "t=123,v1=sig")
        assert ok is True

        mock_construct.side_effect = Exception("Signature verification failed")
        bad_ok, bad_msg = billing_sec.handle_webhook_event(b"bad", "bad_sig")
        assert bad_ok is False
        assert "Invalid webhook signature" in bad_msg


def test_checkout_missing_price_id(test_setup, monkeypatch):
    db, _, user = test_setup
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")

    b = BillingManager(db=db)
    monkeypatch.setattr(b, "is_configured", lambda: True)
    monkeypatch.setattr(BillingManager, "monthly_price_id", property(lambda self: ""))
    monkeypatch.setattr(BillingManager, "yearly_price_id", property(lambda self: ""))
    monkeypatch.setattr(BillingManager, "pro_price_id", property(lambda self: ""))

    url, err = b.create_checkout_session(user["id"], "https://s", "https://c")
    assert url is None
    assert "No active Stripe Price ID" in err


def test_checkout_and_portal_errors(test_setup, monkeypatch):
    db, _, user = test_setup
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_PRICE_MONTHLY", "price_test_monthly")

    b = BillingManager(db=db)

    # Checkout session creation exception
    with patch(
        "managers.billing_manager.stripe.checkout.Session.create",
        side_effect=Exception("Stripe API down"),
    ):
        with patch(
            "managers.billing_manager.stripe.Customer.create",
            return_value=MagicMock(id="cus_new_1"),
        ):
            url, err = b.create_checkout_session(user["id"], "https://s", "https://c")
            assert url is None
            assert "Stripe API down" in err

    # Customer portal auto-create customer exception
    user_no_stripe = db.create_user("user_no_stripe", "hash", email="u_no@example.com")
    with patch(
        "managers.billing_manager.stripe.Customer.create",
        side_effect=Exception("Cust fail"),
    ):
        url, err = b.create_customer_portal_session(user_no_stripe["id"], "https://ret")
        assert url is None
        assert "No active billing account" in err

    # Customer portal session creation exception
    db.update_user_plan(user["id"], plan=PLAN_FREE, stripe_customer_id="cus_ok")
    with patch(
        "managers.billing_manager.stripe.billing_portal.Session.create",
        side_effect=Exception("Portal down"),
    ):
        url, err = b.create_customer_portal_session(user["id"], "https://ret")
        assert url is None
        assert "Portal down" in err


def test_billing_manager_stripe_import_and_ca_bundle():
    """Verify stripe import error fallback and CA bundle edge cases."""
    import importlib

    import managers.billing_manager as bm

    # 1. Stripe ImportError (lines 18-19) and stripe=None in ca bundle (line 55)
    with patch.dict(sys.modules, {"stripe": None}):
        reloaded = importlib.reload(bm)
        assert reloaded.stripe is None
        reloaded.configure_stripe_ca_bundle()
    importlib.reload(bm)

    # 2. Certifi probe exception (lines 62-63)
    with patch.dict(sys.modules, {"certifi": None}):
        bm.configure_stripe_ca_bundle()
