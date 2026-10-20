"""Tests for AIFailureDiagnoser module."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from utils.ai_failure_diagnoser import AIFailureDiagnoser, apply_suggested_template


def test_ai_failure_diagnoser_is_configured():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "dummy-key"}):
        diagnoser = AIFailureDiagnoser(provider="gemini")
        assert diagnoser.is_configured() is True


def test_diagnose_single_failure_mocked():
    diagnoser = AIFailureDiagnoser(provider="gemini")

    mock_response = json.dumps(
        {
            "component_id": "traefik",
            "summary": "Traefik port 8080 requires --api.insecure=true.",
            "root_cause_analysis": "Port 8080 was returning 404.",
            "fix_description": "Add --api.insecure=true to command.",
            "category": "Configuration",
            "suggested_template": (
                "services:\n"
                "  traefik:\n"
                "    command:\n"
                "      - '--api.insecure=true'\n"
            ),
            "patch_notes": "None",
        }
    )

    with patch.object(diagnoser.engine, "generate", return_value=mock_response):
        res = diagnoser.diagnose_single_failure(
            test_record={
                "component_id": "traefik",
                "mode": "LXC",
                "engine": "PODMAN",
                "status": "failed",
                "error_message": "HTTP Probe: 404",
            },
            template_content=(
                "services:\n"
                "  traefik:\n"
                "    command:\n"
                "      - '--api.dashboard=true'\n"
            ),
        )

        assert res["component_id"] == "traefik"
        assert "404" in res["root_cause_analysis"]
        assert "diff" in res
        assert "+      - '--api.insecure=true'" in res["diff"]


def test_diagnose_batch_failures_mocked():
    diagnoser = AIFailureDiagnoser(provider="gemini")

    mock_batch_response = json.dumps(
        {
            "total_analyzed": 2,
            "systemic_summary": "Network creation failed across podman tests.",
            "clusters": [
                {
                    "cluster_name": "Missing Podman Network",
                    "category": "Network",
                    "affected_tests": [
                        "nextcloud-db (LXC/PODMAN)",
                        "nextcloud-redis (LXC/PODMAN)",
                    ],
                    "root_cause_explanation": (
                        "Network njorddeploy_net was not pre-created."
                    ),
                    "recommended_action": "Run podman network create.",
                }
            ],
            "individual_quick_fixes": [],
            "overall_recommendations": ["Pre-create networks"],
        }
    )

    with patch.object(diagnoser.engine, "generate", return_value=mock_batch_response):
        res = diagnoser.diagnose_batch_failures(
            failed_records=[
                {
                    "component_id": "nextcloud-db",
                    "mode": "LXC",
                    "engine": "PODMAN",
                    "error_message": "RuntimeError: missing networks",
                },
                {
                    "component_id": "nextcloud-redis",
                    "mode": "LXC",
                    "engine": "PODMAN",
                    "error_message": "RuntimeError: missing networks",
                },
            ]
        )

        assert res["total_analyzed"] == 2
        assert len(res["clusters"]) == 1
        assert res["clusters"][0]["cluster_name"] == "Missing Podman Network"


def test_diagnose_core_platform_code_failure_mocked():
    diagnoser = AIFailureDiagnoser(provider="gemini")

    mock_response = json.dumps(
        {
            "component_id": "homeassistant",
            "target_type": "CORE_PLATFORM_CODE",
            "target_file": "src/managers/deployment_manager.py",
            "summary": ("Deployment manager failed to create host volume directory."),
            "root_cause_analysis": (
                "Ansible playbook execution raised permission denied on "
                "/opt/njorddeploy."
            ),
            "fix_description": (
                "Ensure setup_manager creates /opt/njorddeploy with correct "
                "permissions."
            ),
            "category": "Backend Logic",
            "suggested_template": None,
            "suggested_code_patch": (
                "--- a/src/managers/deployment_manager.py\n"
                "+++ b/src/managers/deployment_manager.py\n"
                "@@ -10,1 +10,1 @@"
            ),
            "action_plan": (
                "Update setup_manager.py and run pytest tests/test_setup_manager.py."
            ),
            "patch_notes": "None",
        }
    )

    with patch.object(diagnoser.engine, "generate", return_value=mock_response):
        res = diagnoser.diagnose_single_failure(
            test_record={
                "component_id": "homeassistant",
                "mode": "LXC",
                "engine": "PODMAN",
                "status": "failed",
                "error_message": (
                    "Traceback (most recent call last): "
                    "PermissionError: /opt/njorddeploy"
                ),
            },
            template_content="services:\n  homeassistant:\n",
        )

        assert res["target_type"] == "CORE_PLATFORM_CODE"
        assert res["target_file"] == "src/managers/deployment_manager.py"
        assert res["diff"] == ""
        assert "setup_manager" in res["action_plan"]


def test_diagnose_matrix_constraint_failure_mocked():
    diagnoser = AIFailureDiagnoser(provider="gemini")

    mock_response = json.dumps(
        {
            "component_id": "gluetun",
            "target_type": "MATRIX_CONSTRAINT",
            "target_file": "config/components_metadata.json",
            "summary": (
                "Gluetun requires /dev/net/tun host device node unavailable "
                "in unprivileged LXC."
            ),
            "root_cause_analysis": "LXC container does not expose /dev/net/tun.",
            "fix_description": "Restrict gluetun supported_matrix to VM only.",
            "category": "Matrix Incompatibility",
            "suggested_template": None,
            "suggested_code_patch": None,
            "suggested_matrix": {
                "modes": ["vm"],
                "engines": ["docker", "podman"],
            },
            "matrix_notes": "Requires kernel /dev/net/tun device",
            "action_plan": "Update supported_matrix in components_metadata.json.",
            "patch_notes": "None",
        }
    )

    with patch.object(diagnoser.engine, "generate", return_value=mock_response):
        res = diagnoser.diagnose_single_failure(
            test_record={
                "component_id": "gluetun",
                "mode": "LXC",
                "engine": "DOCKER",
                "status": "failed",
                "error_message": (
                    "error gathering device information while adding custom "
                    "device '/dev/net/tun': not a device node"
                ),
            },
            template_content="services:\n  gluetun:\n",
            history_records=[
                {
                    "component_id": "gluetun",
                    "mode": "VM",
                    "engine": "DOCKER",
                    "status": "success",
                },
                {
                    "component_id": "gluetun",
                    "mode": "LXC",
                    "engine": "DOCKER",
                    "status": "failed",
                },
            ],
        )

        assert res["target_type"] == "MATRIX_CONSTRAINT"
        assert res["suggested_matrix"]["modes"] == ["vm"]
        assert "dev/net/tun" in res["matrix_notes"]


def test_apply_suggested_template(tmp_path):
    tpl_dir = tmp_path / "component_templates" / "test-service"
    tpl_dir.mkdir(parents=True)
    tpl_file = tpl_dir / "docker-compose.template.yml"
    tpl_file.write_text("old content", encoding="utf-8")

    success = apply_suggested_template(
        "test-service", "new content", project_root=tmp_path
    )
    assert success is True
    assert tpl_file.read_text(encoding="utf-8") == "new content"


def test_domain_failure_hints_sqlite_and_forge():
    hints_sqlite = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg="Error: Meta database configuration missing SQLite file name"
    )
    assert "SQLITE CONFIGURATION ERROR" in hints_sqlite

    hints_forge = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg=(
            "error: can't setup globals: could not setup service manager: "
            "forge not configured"
        )
    )
    assert "FORGE / CI PREREQUISITE REQUIREMENT" in hints_forge


def test_domain_failure_hints_source_build_and_podman_timing():
    hints_build = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg="failed to resolve source metadata for dockerfile: Dockerfile"
    )
    assert "SOURCE BUILD vs PRE-BUILT IMAGE" in hints_build

    hints_podman = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg="HTTP Probe failed after 75 attempts: connection refused",
        container_logs="Starting immich postgres migrations...",
        engine="PODMAN",
    )
    assert "PODMAN HEAVY STACK COLD-START NOTE" in hints_podman


def test_ai_failure_diagnoser_provider_fallbacks_and_hints(tmp_path):
    """Test provider resolution order, is_configured, hints, and template
    patch failures."""
    # 1. Fallback order for AI providers
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
        d_openai = AIFailureDiagnoser()
        assert d_openai.provider == "openai"

    with patch.dict(os.environ, {"HOSTYOURAI_API_KEY": "hy-test"}, clear=True):
        d_hy = AIFailureDiagnoser()
        assert d_hy.provider == "hostyourai"

    with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-test"}, clear=True):
        d_gem = AIFailureDiagnoser()
        assert d_gem.provider == "gemini"

    with patch.dict(os.environ, {}, clear=True):
        d_ollama = AIFailureDiagnoser()
        assert d_ollama.provider == "ollama"
        assert d_ollama.is_configured() is True

    # 2. is_configured with explicit engine api_key and unconfigured
    d_explicit = AIFailureDiagnoser(provider="custom", api_key="secret-key")
    assert d_explicit.is_configured() is True
    d_unconf = AIFailureDiagnoser(provider="custom_unconf", api_key=None)
    assert d_unconf.is_configured() is False

    # 2b. diagnose_batch_failures with empty records
    assert d_explicit.diagnose_batch_failures([])["total_analyzed"] == 0

    # 3. Additional domain failure hints
    hints_net_host = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg="network_mode: host with exit code: 125",
        engine="podman",
    )
    assert "PODMAN NETWORK_MODE HOST CONFLICT" in hints_net_host

    hints_podman_tb = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg="podman-compose Traceback (most recent call last): RuntimeError",
        engine="podman",
    )
    assert "PODMAN ENGINE NOTE" in hints_podman_tb

    hints_traefik_8080 = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg="traefik api.insecure on port 8080: address already in use"
    )
    assert "TRAEFIK PORT 8080 CONFLICT" in hints_traefik_8080

    hints_sock = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg="failed mounting /var/run/docker.sock",
        engine="podman",
    )
    assert "DOCKER SOCKET REQUIREMENT" in hints_sock

    hints_root = AIFailureDiagnoser._get_domain_failure_hints(
        error_msg="usermod: uid operation not permitted",
        engine="podman",
    )
    assert "PERMISSIONS & ROOTFUL PODMAN NOTE" in hints_root

    # 4. apply_suggested_template non-existent and write failure
    assert (
        apply_suggested_template("nonexistent-app", "content", project_root=tmp_path)
        is False
    )

    valid_comp_dir = tmp_path / "component_templates" / "valid-app"
    valid_comp_dir.mkdir(parents=True)
    with patch.object(Path, "write_text", side_effect=IOError("write denied")):
        assert (
            apply_suggested_template("valid-app", "content", project_root=tmp_path)
            is False
        )
