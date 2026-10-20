# tests/configurator_app/test_configurator_saas_auth_billing.py

"""Comprehensive coverage for Configurator App SaaS, Auth, Agent, and Billing routes.

Covers:
- Server mode before_request enforcement (setup required, auth required, API keys)
- First-run setup wizard, login, logout, password changes
- Multi-tenancy user registration
- Server registration and Agent install script generation
- Node agent telemetry and heartbeat verification
- Stripe billing checkout, customer portal, and webhooks
- Health checks, index page, and Swagger UI
"""

import unittest
from unittest.mock import patch

from configurator_app.app import create_app


class ConfiguratorSaaSAuthBillingTestCase(unittest.TestCase):
    """Test suite for SaaS, multi-tenancy, authentication, and billing."""

    def setUp(self):
        """Initializes Flask test client with mocked manager instances."""
        self.patcher_manager = patch("configurator_app.app.ComponentManager")
        self.patcher_setup = patch("configurator_app.app.SetupManager")
        self.patcher_scanner = patch("configurator_app.app.NodeScanner")
        self.patcher_deploy = patch("configurator_app.app.DeploymentManager")

        self.mock_manager_class = self.patcher_manager.start()
        self.mock_setup_class = self.patcher_setup.start()
        self.mock_scanner_class = self.patcher_scanner.start()
        self.mock_deploy_class = self.patcher_deploy.start()

        self.mock_manager = self.mock_manager_class.return_value
        self.mock_setup = self.mock_setup_class.return_value
        self.mock_scanner = self.mock_scanner_class.return_value
        self.mock_deploy = self.mock_deploy_class.return_value

        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-saas-secret"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.patcher_manager.stop()
        self.patcher_setup.stop()
        self.patcher_scanner.stop()
        self.patcher_deploy.stop()

    def test_server_mode_before_request_enforcement(self):
        """Verifies server mode before_request redirects, API errors, and bypasses."""
        env_server = {"NJORD_SERVER_MODE": "1"}

        # 1. Admin not configured
        with (
            patch.dict("os.environ", env_server),
            patch("configurator_app.app.is_auth_enabled", return_value=True),
            patch("configurator_app.app.is_admin_configured", return_value=False),
        ):
            # API non-public request -> 401 setup required
            res_api = self.client.get(
                "/api/servers", headers={"Accept": "application/json"}
            )
            self.assertEqual(res_api.status_code, 401)
            self.assertTrue(res_api.get_json().get("setup_required"))

            # Web non-public request -> redirect to /setup
            res_web = self.client.get("/settings")
            self.assertEqual(res_web.status_code, 302)
            self.assertIn("/setup", res_web.headers["Location"])

        # 2. Admin configured, unauthenticated
        with (
            patch.dict("os.environ", env_server),
            patch("configurator_app.app.is_auth_enabled", return_value=True),
            patch("configurator_app.app.is_admin_configured", return_value=True),
        ):
            # API request -> 401 unauthorized
            res_unauth_api = self.client.get(
                "/api/servers", headers={"Accept": "application/json"}
            )
            self.assertEqual(res_unauth_api.status_code, 401)

            # Web request -> redirect to /login
            res_unauth_web = self.client.get("/settings")
            self.assertEqual(res_unauth_web.status_code, 302)
            self.assertIn("/login", res_unauth_web.headers["Location"])

            # Valid API key in header -> allowed through
            with (
                patch("configurator_app.app.verify_api_key", return_value=True),
                patch(
                    "configurator_app.app.extract_api_key_from_request",
                    return_value="valid_key",
                ),
                patch(
                    "managers.database_manager.DatabaseManager.list_servers_for_user",
                    return_value=[],
                ),
            ):
                res_key = self.client.get(
                    "/api/servers",
                    headers={"X-Njord-API-Key": "valid_key"},
                )
                self.assertEqual(res_key.status_code, 200)

            # Active session with user plan sync
            with self.client.session_transaction() as sess:
                sess["logged_in"] = True
                sess["user"] = "admin"
                sess["role"] = "admin"

            with patch(
                "managers.database_manager.DatabaseManager.get_user_by_username",
                return_value={"username": "admin", "plan": "pro"},
            ):
                res_sess = self.client.get("/health")
                self.assertEqual(res_sess.status_code, 200)

    def test_setup_and_login_and_logout_flow(self):
        """Verifies /setup, /login, and /logout handling."""
        # 1. /setup GET when admin configured
        with patch("configurator_app.app.is_admin_configured", return_value=True):
            res_setup_get = self.client.get("/setup")
            self.assertEqual(res_setup_get.status_code, 302)

        # 2. /setup GET when admin NOT configured
        with patch("configurator_app.app.is_admin_configured", return_value=False):
            res_setup_fresh = self.client.get("/setup")
            self.assertEqual(res_setup_fresh.status_code, 200)

        # 3. /setup POST when already configured (returns 403)
        with patch("configurator_app.app.is_admin_configured", return_value=True):
            res_setup_post_dup = self.client.post(
                "/api/setup",
                json={"username": "admin", "password": "Password123!"},
            )
            self.assertEqual(res_setup_post_dup.status_code, 403)

        # 4. /setup POST missing password
        with patch("configurator_app.app.is_admin_configured", return_value=False):
            res_bad_setup = self.client.post("/api/setup", json={"username": "admin"})
            self.assertEqual(res_bad_setup.status_code, 400)

            # Valid setup
            with (
                patch(
                    "configurator_app.app.validate_password_strength",
                    return_value=(True, None),
                ),
                patch(
                    "configurator_app.app.validate_username",
                    return_value=(True, None),
                ),
                patch(
                    "configurator_app.app.save_auth_config",
                    return_value={"api_key": "test_api_key"},
                ),
                patch(
                    "managers.database_manager.DatabaseManager.create_user",
                    return_value={"id": 1, "username": "admin"},
                ),
            ):
                res_setup_ok = self.client.post(
                    "/api/setup",
                    json={"username": "admin", "password": "Password123!"},
                )
                self.assertEqual(res_setup_ok.status_code, 200)

        with self.client.session_transaction() as sess:
            sess.clear()

        # 5. /login GET and POST
        res_login_page = self.client.get("/login")
        self.assertEqual(res_login_page.status_code, 200)

        with patch("configurator_app.app.verify_credentials", return_value=False):
            res_login_bad = self.client.post(
                "/login",
                json={"username": "admin", "password": "wrongpassword"},
            )
            self.assertEqual(res_login_bad.status_code, 401)

        with (
            patch("configurator_app.app.verify_credentials", return_value=True),
            patch(
                "managers.database_manager.DatabaseManager.get_user_by_username",
                return_value={
                    "id": 1,
                    "username": "admin",
                    "role": "admin",
                    "plan": "pro",
                },
            ),
        ):
            res_login_ok = self.client.post(
                "/login",
                json={"username": "admin", "password": "correctpassword"},
            )
            self.assertEqual(res_login_ok.status_code, 200)

        # 6. /logout
        res_logout = self.client.get("/logout")
        self.assertEqual(res_logout.status_code, 302)

    def test_change_password_route(self):
        """Verifies /api/auth/change-password credential validation and errors."""
        with patch("configurator_app.app.is_admin_configured", return_value=True):
            # 1. Unauthorized when auth is enabled and not logged in
            with patch("configurator_app.app.is_auth_enabled", return_value=True):
                res_unauth = self.client.post("/api/auth/change-password", json={})
                self.assertEqual(res_unauth.status_code, 401)

            with self.client.session_transaction() as sess:
                sess["logged_in"] = True
                sess["user"] = "admin"

            # 2. Config missing
            with (
                patch("configurator_app.app.is_auth_enabled", return_value=True),
                patch("configurator_app.app.load_auth_config", return_value=None),
            ):
                res_no_cfg = self.client.post("/api/auth/change-password", json={})
                self.assertEqual(res_no_cfg.status_code, 400)

            # 3. Wrong current password
            with (
                patch("configurator_app.app.is_auth_enabled", return_value=True),
                patch(
                    "configurator_app.app.load_auth_config",
                    return_value={"username": "admin"},
                ),
                patch("configurator_app.app.verify_credentials", return_value=False),
            ):
                res_wrong_pw = self.client.post(
                    "/api/auth/change-password",
                    json={"current_password": "wrong"},
                )
                self.assertEqual(res_wrong_pw.status_code, 400)

            # 4. Weak new password
            with (
                patch("configurator_app.app.is_auth_enabled", return_value=True),
                patch(
                    "configurator_app.app.load_auth_config",
                    return_value={"username": "admin"},
                ),
                patch("configurator_app.app.verify_credentials", return_value=True),
                patch(
                    "configurator_app.app.validate_password_strength",
                    return_value=(False, "Password too short"),
                ),
            ):
                res_weak = self.client.post(
                    "/api/auth/change-password",
                    json={
                        "current_password": "correct",
                        "new_password": "short",
                    },
                )
                self.assertEqual(res_weak.status_code, 400)

            # 5. Success
            with (
                patch("configurator_app.app.is_auth_enabled", return_value=True),
                patch(
                    "configurator_app.app.load_auth_config",
                    return_value={"username": "admin"},
                ),
                patch("configurator_app.app.verify_credentials", return_value=True),
                patch(
                    "configurator_app.app.validate_password_strength",
                    return_value=(True, None),
                ),
                patch("configurator_app.app.save_auth_config", return_value=True),
            ):
                res_pw_ok = self.client.post(
                    "/api/auth/change-password",
                    json={
                        "current_password": "correct",
                        "new_password": "NewStrongPassword2026!",
                        "confirm_password": "NewStrongPassword2026!",
                    },
                )
                self.assertEqual(res_pw_ok.status_code, 200)

    def test_register_and_servers_and_agent(self):
        """Verifies multi-tenancy registration, servers list, and agent installer."""
        # 1. /register GET
        res_reg_page = self.client.get("/register")
        self.assertEqual(res_reg_page.status_code, 200)

        # 2. /register POST validation error
        with patch(
            "configurator_app.app.validate_username",
            return_value=(False, "Invalid username"),
        ):
            res_bad_user = self.client.post("/api/register", json={"username": "bad"})
            self.assertEqual(res_bad_user.status_code, 400)

        # 3. /register POST duplicate user
        with (
            patch(
                "configurator_app.app.validate_username",
                return_value=(True, None),
            ),
            patch(
                "configurator_app.app.validate_password_strength",
                return_value=(True, None),
            ),
            patch(
                "managers.database_manager.DatabaseManager.get_user_by_username",
                return_value={"id": 1},
            ),
        ):
            res_dup_reg = self.client.post(
                "/api/register",
                json={"username": "existing", "password": "Password123!"},
            )
            self.assertEqual(res_dup_reg.status_code, 409)

        # 4. /register POST success
        with (
            patch(
                "configurator_app.app.validate_username",
                return_value=(True, None),
            ),
            patch(
                "configurator_app.app.validate_password_strength",
                return_value=(True, None),
            ),
            patch(
                "managers.database_manager.DatabaseManager.get_user_by_username",
                return_value=None,
            ),
            patch(
                "managers.database_manager.DatabaseManager.get_user_by_email",
                return_value=None,
            ),
            patch(
                "managers.database_manager.DatabaseManager.create_user",
                return_value={"id": 42, "username": "newuser"},
            ),
        ):
            res_reg_ok = self.client.post(
                "/api/register",
                json={"username": "newuser", "password": "Password123!"},
            )
            self.assertEqual(res_reg_ok.status_code, 201)

        # 5. /api/servers
        with patch(
            "managers.database_manager.DatabaseManager.list_servers_for_user",
            return_value=[{"id": 1, "name": "Node 1"}],
        ):
            res_servers = self.client.get("/api/servers")
            self.assertEqual(res_servers.status_code, 200)

        # 6. /api/servers/add quota check
        with (
            patch(
                "managers.billing_manager.BillingManager.can_user_add_server",
                return_value=(False, "Plan limit reached"),
            ),
        ):
            res_quota = self.client.post("/api/servers/add", json={})
            self.assertEqual(res_quota.status_code, 403)

        with (
            patch(
                "managers.billing_manager.BillingManager.can_user_add_server",
                return_value=(True, None),
            ),
            patch(
                "managers.agent_manager.AgentManager.register_node",
                return_value={"id": 10, "agent_token": "token123"},
            ),
            patch(
                "managers.agent_manager.AgentManager.generate_install_command",
                return_value="curl https://...",
            ),
        ):
            res_add_ok = self.client.post(
                "/api/servers/add", json={"name": "New Server"}
            )
            self.assertEqual(res_add_ok.status_code, 201)

        # 7. /install-agent script download
        with patch(
            "managers.agent_manager.AgentManager.generate_install_script",
            return_value="#!/bin/bash\necho ok",
        ):
            res_script = self.client.get("/install-agent?token=token123")
            self.assertEqual(res_script.status_code, 200)
            self.assertIn("text/x-shellscript", res_script.headers["Content-Type"])

        # 8. /api/agent/heartbeat missing token
        res_hb_no_token = self.client.post("/api/agent/heartbeat", json={})
        self.assertEqual(res_hb_no_token.status_code, 401)

        with patch(
            "managers.agent_manager.AgentManager.process_heartbeat",
            return_value=(True, "OK"),
        ):
            res_hb_ok = self.client.post(
                "/api/agent/heartbeat",
                headers={"X-Njord-Agent-Token": "token123"},
                json={"cpu": 10},
            )
            self.assertEqual(res_hb_ok.status_code, 200)

    def test_billing_checkout_portal_and_webhooks(self):
        """Verifies billing status, checkout, customer portal, and webhooks."""
        with (
            patch(
                "managers.billing_manager.BillingManager.get_user_plan_info",
                return_value={"plan": "free", "max_servers": 1},
            ),
        ):
            # 1. /api/billing/status
            res_status = self.client.get("/api/billing/status")
            self.assertEqual(res_status.status_code, 200)

        # 2. /api/billing/checkout error and success
        with (
            patch(
                "managers.billing_manager.BillingManager.create_checkout_session",
                return_value=(None, "Invalid price"),
            ),
        ):
            res_chk_err = self.client.post("/api/billing/checkout", json={})
            self.assertEqual(res_chk_err.status_code, 400)

        with (
            patch(
                "managers.billing_manager.BillingManager.create_checkout_session",
                return_value=("https://checkout.stripe.com/pay", None),
            ),
        ):
            res_chk_ok = self.client.post("/api/billing/checkout", json={})
            self.assertEqual(res_chk_ok.status_code, 200)
            self.assertIn("checkout_url", res_chk_ok.get_json())

        portal_target = (
            "managers.billing_manager.BillingManager." "create_customer_portal_session"
        )
        # 3. /api/billing/portal error and success
        with patch(
            portal_target,
            return_value=(None, "Customer not found"),
        ):
            res_portal_err = self.client.post("/api/billing/portal", json={})
            self.assertEqual(res_portal_err.status_code, 400)

        with patch(
            portal_target,
            return_value=("https://billing.stripe.com/session", None),
        ):
            res_portal_ok = self.client.post("/api/billing/portal", json={})
            self.assertEqual(res_portal_ok.status_code, 200)

        # 4. /api/billing/webhook
        with (
            patch(
                "managers.billing_manager.BillingManager.handle_webhook_event",
                return_value=(False, "Invalid signature"),
            ),
        ):
            res_wh_err = self.client.post("/api/billing/webhook", data=b"{}")
            self.assertEqual(res_wh_err.status_code, 400)

        with (
            patch(
                "managers.billing_manager.BillingManager.handle_webhook_event",
                return_value=(True, "Processed"),
            ),
        ):
            res_wh_ok = self.client.post("/api/billing/webhook", data=b"{}")
            self.assertEqual(res_wh_ok.status_code, 200)

        # 5. Chatwoot webhook
        with patch(
            "managers.chatwoot_bot_manager.ChatwootBotManager.handle_webhook_event",
            return_value=(True, "Handled"),
        ):
            res_cw = self.client.post("/api/chatwoot/webhook", data=b"{}")
            self.assertEqual(res_cw.status_code, 200)

    def test_health_and_index_and_docs(self):
        """Verifies health check, root index page, and Swagger UI."""
        # 1. Health check standalone
        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.get_json()["status"], "ok")

        # 2. Root index page
        res_index = self.client.get("/")
        self.assertEqual(res_index.status_code, 200)

        # 3. Swagger docs
        res_docs = self.client.get("/api/docs")
        self.assertEqual(res_docs.status_code, 200)
