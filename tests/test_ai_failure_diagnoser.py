"""Tests for AIFailureDiagnoser module."""

import json
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
