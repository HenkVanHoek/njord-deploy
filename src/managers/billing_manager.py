# src/managers/billing_manager.py

"""
NjordDeploy Stripe Billing & Subscription Manager
-------------------------------------------------
Handles Stripe Checkout Sessions, Customer Billing Portal, Webhook Events,
and Tier Quota Limits (Free vs Pro).
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple

try:
    import stripe
except ImportError:
    stripe = None  # type: ignore

from managers.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

# Plan Constants
PLAN_FREE = "free"
PLAN_PRO = "pro"

PLAN_QUOTAS = {
    PLAN_FREE: {
        "name": "NjordDeploy Free",
        "price_eur": 0,
        "max_servers": 2,
        "max_deployments_per_day": 10,
        "automated_cloud_backups": False,
        "priority_cve_alerts": False,
    },
    PLAN_PRO: {
        "name": "NjordDeploy Pro",
        "price_eur": 5,
        "max_servers": 9999,
        "max_deployments_per_day": 9999,
        "automated_cloud_backups": True,
        "priority_cve_alerts": True,
    },
}


class BillingManager:
    """
    Manages Stripe billing integrations, customer accounts, and subscription tiers.
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """Initializes the billing manager with database and Stripe credentials."""
        self.db = db or DatabaseManager.get_instance()
        self.api_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
        self.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
        self.monthly_price_id = os.getenv(
            "STRIPE_PRICE_MONTHLY", os.getenv("STRIPE_PRO_PRICE_ID", "")
        ).strip()
        self.yearly_price_id = os.getenv("STRIPE_PRICE_YEARLY", "").strip()
        self.pro_price_id = self.monthly_price_id or self.yearly_price_id

        if stripe and self.api_key:
            stripe.api_key = self.api_key

    def is_configured(self) -> bool:
        """Returns True if Stripe credentials are provided."""
        return bool(
            stripe
            and self.api_key
            and (self.monthly_price_id or self.yearly_price_id or self.pro_price_id)
        )

    def get_user_plan_info(self, user_id: int) -> Dict[str, Any]:
        """Retrieves plan details and current quota usage for a user."""
        user = self.db.get_user_by_id(user_id)
        plan = user.get("plan", PLAN_FREE) if user else PLAN_FREE
        server_count = self.db.count_servers_for_user(user_id)
        quota = PLAN_QUOTAS.get(plan, PLAN_QUOTAS[PLAN_FREE])

        return {
            "plan": plan,
            "plan_name": quota["name"],
            "price_eur": quota["price_eur"],
            "server_count": server_count,
            "max_servers": quota["max_servers"],
            "can_add_server": server_count < quota["max_servers"],
            "automated_cloud_backups": quota["automated_cloud_backups"],
            "priority_cve_alerts": quota["priority_cve_alerts"],
            "stripe_customer_id": user.get("stripe_customer_id") if user else None,
            "stripe_subscription_id": (
                user.get("stripe_subscription_id") if user else None
            ),
            "publishable_key": self.publishable_key if self.publishable_key else None,
            "price_monthly_id": self.monthly_price_id,
            "price_yearly_id": self.yearly_price_id,
        }

    def can_user_add_server(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Validates whether a user can register another server node."""
        plan_info = self.get_user_plan_info(user_id)
        if plan_info["can_add_server"]:
            return True, None

        max_limit = plan_info["max_servers"]
        return False, (
            f"Server limit reached ({plan_info['server_count']}/{max_limit}). "
            "Upgrade to NjordDeploy Pro for unlimited servers."
        )

    def create_checkout_session(
        self,
        user_id: int,
        success_url: str,
        cancel_url: str,
        interval: str = "monthly",
        price_id: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Creates a Stripe Checkout Session for upgrading to NjordDeploy Pro.
        Returns (checkout_url, error_message).
        """
        if not self.is_configured():
            # Mock checkout session for development/testing when Stripe keys are not set
            return f"{success_url}?mock_checkout=true&session_id=cs_mock_12345", None

        user = self.db.get_user_by_id(user_id)
        if not user:
            # Fallback for standalone desktop mode or guest user
            user = self.db.get_user_by_username("local_admin")
            if not user:
                user = self.db.create_user(  # nosec B106
                    username="local_admin",
                    password_hash="",
                    email=os.getenv("DEFAULT_EMAIL", "admin@njorddeploy.com"),
                    role="owner",
                    plan=PLAN_FREE,
                )
            user_id = user["id"]

        # Determine target price ID
        target_price_id = price_id
        if not target_price_id:
            if interval == "yearly" and self.yearly_price_id:
                target_price_id = self.yearly_price_id
            else:
                target_price_id = self.monthly_price_id or self.pro_price_id

        if not target_price_id:
            return None, "No active Stripe Price ID configured for the selected plan."

        try:
            # Look up or create Stripe customer
            customer_id = user.get("stripe_customer_id")
            if not customer_id:
                cust_kwargs: Dict[str, Any] = {
                    "name": user.get("username", "NjordDeploy User"),
                    "metadata": {"user_id": str(user_id)},
                }
                user_email = user.get("email")
                if user_email and "@" in user_email:
                    cust_kwargs["email"] = user_email
                customer = stripe.Customer.create(**cust_kwargs)
                customer_id = customer.id
                self.db.update_user_plan(
                    user_id,
                    plan=user.get("plan", PLAN_FREE),
                    stripe_customer_id=customer_id,
                )

            delim = "&" if "?" in success_url else "?"
            session = stripe.checkout.Session.create(
                customer=customer_id,
                line_items=[
                    {
                        "price": target_price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=f"{success_url}{delim}session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                client_reference_id=str(user_id),
                metadata={
                    "user_id": str(user_id),
                    "plan": PLAN_PRO,
                    "interval": interval,
                },
                allow_promotion_codes=True,
            )
            return session.url, None
        except Exception as e:
            logger.error(f"Stripe Checkout Session creation failed: {e}")
            return None, str(e)

    def create_customer_portal_session(
        self, user_id: int, return_url: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Creates a Stripe Customer Portal Session where the user can manage/cancel
        their subscription and download invoices.
        """
        if not self.is_configured():
            return f"{return_url}?mock_portal=true", None

        user = self.db.get_user_by_id(user_id)
        if not user:
            user = self.db.get_user_by_username("local_admin")

        customer_id = user.get("stripe_customer_id") if user else None
        if not customer_id and user:
            try:
                cust_kwargs: Dict[str, Any] = {
                    "name": user.get("username", "NjordDeploy User"),
                    "metadata": {"user_id": str(user["id"])},
                }
                user_email = user.get("email")
                if user_email and "@" in user_email:
                    cust_kwargs["email"] = user_email
                customer = stripe.Customer.create(**cust_kwargs)
                customer_id = customer.id
                self.db.update_user_plan(
                    user["id"],
                    plan=user.get("plan", PLAN_FREE),
                    stripe_customer_id=customer_id,
                )
            except Exception as e:
                logger.error(f"Failed to auto-create customer for portal: {e}")

        if not customer_id:
            return None, "No active billing account found for this user."

        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return portal_session.url, None
        except Exception as e:
            logger.error(f"Stripe Portal Session creation failed: {e}")
            return None, str(e)

    def handle_webhook_event(
        self, payload: bytes, signature_header: str
    ) -> Tuple[bool, str]:
        """
        Processes inbound Stripe Webhook events with signature verification.
        """
        if not stripe:
            return False, "Stripe library not installed."

        event = None
        try:
            if self.webhook_secret and signature_header:
                event = stripe.Webhook.construct_event(
                    payload, signature_header, self.webhook_secret
                )
            else:
                import json

                event = json.loads(payload.decode("utf-8"))
        except Exception as e:
            logger.error(f"Stripe webhook signature validation failed: {e}")
            return False, f"Invalid webhook signature: {e}"

        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        logger.info(f"Received Stripe Webhook event: {event_type}")

        if event_type in (
            "checkout.session.completed",
            "customer.subscription.created",
        ):
            user_id = data_object.get("client_reference_id") or data_object.get(
                "metadata", {}
            ).get("user_id")
            customer_id = data_object.get("customer")
            subscription_id = data_object.get("subscription") or data_object.get("id")

            if user_id:
                try:
                    u_id = int(user_id)
                    self.db.update_user_plan(
                        u_id,
                        plan=PLAN_PRO,
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=subscription_id,
                    )
                    logger.info(
                        f"User {u_id} upgraded to {PLAN_PRO} via "
                        f"event {event_type} {data_object.get('id')}"
                    )
                except ValueError:
                    logger.warning(f"Invalid user_id in Stripe metadata: {user_id}")
            elif customer_id:
                user = self.db.get_user_by_stripe_customer_id(customer_id)
                if user:
                    self.db.update_user_plan(
                        user["id"],
                        plan=PLAN_PRO,
                        stripe_customer_id=customer_id,
                        stripe_subscription_id=subscription_id,
                    )
                    logger.info(
                        f"User {user['id']} ({customer_id}) upgraded to "
                        f"{PLAN_PRO} via {event_type}"
                    )

        elif event_type in (
            "customer.subscription.deleted",
            "customer.subscription.updated",
        ):
            customer_id = data_object.get("customer")
            status = data_object.get("status")
            subscription_id = data_object.get("id")

            user = self.db.get_user_by_stripe_customer_id(customer_id)
            if user:
                if status in ("active", "trialing"):
                    self.db.update_user_plan(
                        user["id"],
                        plan=PLAN_PRO,
                        stripe_subscription_id=subscription_id,
                    )
                elif status in (
                    "canceled",
                    "unpaid",
                    "incomplete_expired",
                    "past_due",
                ):
                    self.db.update_user_plan(user["id"], plan=PLAN_FREE)
                    logger.info(
                        f"User {user['id']} downgraded to {PLAN_FREE} "
                        f"due to status: {status}"
                    )

        elif event_type == "invoice.payment_failed":
            customer_id = data_object.get("customer")
            logger.warning(
                f"Payment failed for customer {customer_id} on "
                f"invoice {data_object.get('id')}"
            )

        elif event_type == "invoice.payment_succeeded":
            customer_id = data_object.get("customer")
            logger.info(
                f"Payment succeeded for customer {customer_id} on "
                f"invoice {data_object.get('id')}"
            )

        return True, "Webhook processed successfully."
