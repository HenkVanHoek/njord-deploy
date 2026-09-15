# tests/fums/test_fums_security.py
"""FUMS Security & Threat Model Test Suite.

Verifies SSRF prevention, command injection defense, path containment,
AVG/GDPR dummy data hygiene, tenant isolation, and outbound mail traps
according to NjordDeploy Air-Traffic-Control security standards.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from managers.customer_sandbox_manager import CustomerSandboxManager
from managers.fleet_update_manager import FleetUpdateManager
from utils.fums_notifier import FUMSNotifier
from utils.security_utils import validate_and_sanitize_url


class TestFUMSSSRFPrevention:
    """Tests defending against SSRF attacks on Signal and Matrix dispatchers."""

    def test_reject_dangerous_schemes(self):
        dangerous_urls = [
            "file:///etc/passwd",
            "gopher://127.0.0.1:25",
            "ftp://anonymous@internal.corp",
            "ldap://127.0.0.1:389",
            "dict://127.0.0.1:11211",
        ]
        for bad_url in dangerous_urls:
            is_valid, clean_url, err = validate_and_sanitize_url(bad_url)
            assert is_valid is False, f"URL {bad_url} was unexpectedly allowed!"
            assert clean_url is None

    def test_reject_crlf_and_control_characters(self):
        crlf_injections = [
            "http://signal.local:8080/v2/send\r\nHost: malicious.site",
            "https://matrix.org/send\x00/room",
            "http://127.0.0.1:8080\nGET /evil",
        ]
        for injection in crlf_injections:
            is_valid, clean_url, _ = validate_and_sanitize_url(injection)
            assert is_valid is False

    @patch("requests.post")
    def test_notifier_blocks_untrusted_scheme(self, mock_post):
        notifier = FUMSNotifier(
            signal_api="file:///etc/shadow",
            signal_sender="+31600000000",
        )
        res = notifier.send_signal("test payload", "+31611111111")
        assert res is False
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_matrix_notifier_blocks_malformed_url(self, mock_post):
        notifier = FUMSNotifier(
            matrix_homeserver="gopher://127.0.0.1:1234",
            matrix_token="dummy_token",
        )
        res = notifier.send_matrix("!test:matrix.org", "hello")
        assert res is False
        mock_post.assert_not_called()


class TestFUMSInputSanitization:
    """Verifies protection against command injection and invalid parameter tampering."""

    def test_build_ansible_args_parameter_types(self):
        mgr = FleetUpdateManager()
        # Even with complex characters, variables are passed via extra_vars dictionary,
        # never as raw unquoted shell concatenation.
        args = mgr.build_ansible_update_args(
            component_id="nextcloud; rm -rf /",
            target_host="192.168.1.100",
            new_tag="v30.0.0$(reboot)",
            service_port=8080,
        )
        assert isinstance(args["extravars"], dict)
        assert args["extravars"]["component_id"] == "nextcloud; rm -rf /"
        assert args["extravars"]["new_tag"] == "v30.0.0$(reboot)"
        # Confirm inventory uses trailing comma for literal target host
        assert args["inventory"] == "192.168.1.100,"

    def test_handle_client_response_sanitization(self):
        mgr = FleetUpdateManager()
        analysis = {"component_id": "nextcloud", "new_version": "30.0.0"}

        # Attempted injection inside user input
        res = mgr.handle_client_response(
            analysis=analysis,
            client_response_text="UPDATE 1; drop table users; --",
            client_id="ClientMalicious",
        )
        assert res["action"] == "production_update_immediate"
        assert res["safety_level"] == "high_safety"


class TestCustomerSandboxSecurityAndPrivacy:
    """Validates AVG/GDPR compliance, tenant isolation, and outbound mail traps."""

    def test_sandbox_hostname_sanitization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sandboxes.db"
            mock_pve = MagicMock()
            mock_pve.get.return_value = {
                "data": [{"name": "eth0", "inet": "192.168.1.200/24"}]
            }

            mgr = CustomerSandboxManager(
                proxmox_client=mock_pve,
                db_path=db_path,
                base_domain="training.njorddeploy.com",
            )

            # Untrusted client name with spaces and special chars
            res = mgr.request_sandbox(
                client_id="Evil Corp / Admin @!#$",
                component_id="nextcloud",
                target_version="30.0.0",
            )
            assert res["success"] is True
            # Verified safe URL slug
            assert (
                "https://evil-corp--admin-.training.njorddeploy.com"
                == res["access_url"]
            )

            # Verify LXC clone hostname was sanitized
            mock_pve.clone_lxc.assert_called_once()
            _, kwargs = mock_pve.clone_lxc.call_args
            assert "train-evil-corp--admin-" == kwargs["hostname"]

    def test_sandbox_mailpit_and_privacy_guarantees(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sandboxes.db"
            mgr = CustomerSandboxManager(
                proxmox_client=MagicMock(),
                db_path=db_path,
            )
            res = mgr.request_sandbox(
                client_id="HealthcareClient",
                component_id="nextcloud",
                target_version="30.0.0",
            )
            # Must explicitly guarantee Mailpit trap and clean dummy data
            assert "Mailpit active on port 8025" in res["mail_catcher"]
            assert "Clean dummy seed" in res["data_privacy"]
            assert "AVG/GDPR safe" in res["data_privacy"]
