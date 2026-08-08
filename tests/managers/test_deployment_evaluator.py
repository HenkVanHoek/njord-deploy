# tests/managers/test_deployment_evaluator.py

from unittest.mock import MagicMock, patch

from managers.deployment_evaluator import (
    DeploymentEvaluator,
    evaluate_deployment,
    sanitize_logs,
)


def test_sanitize_logs_masks_sensitive_data():
    raw_logs = (
        "Starting service...\n"
        "POSTGRES_PASSWORD=supersecret123\n"
        "DATABASE_URL=postgres://user:password123@localhost:5432/db\n"
        "Bearer token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\n"
        "All systems normal."
    )
    sanitized = sanitize_logs(raw_logs)

    assert "supersecret123" not in sanitized
    assert "password123" not in sanitized
    assert "***MASKED***" in sanitized
    assert "All systems normal." in sanitized


def test_rule_evaluation_clean_success():
    evaluator = DeploymentEvaluator()
    logs = "Starting container adguard-home...\nService started successfully."
    res = evaluator.evaluate_with_rules(
        component_name="adguard-home",
        log_text=logs,
        exit_code=0,
        container_status={"running": True},
    )

    assert res["status"] == "GREEN"
    assert "successfully" in res["summary"].lower() or "ok" in res["summary"].lower()


def test_rule_evaluation_port_conflict_yellow():
    evaluator = DeploymentEvaluator()
    logs = (
        "Error starting userland proxy: "
        "listen tcp4 0.0.0.0:53: bind: address already in use"
    )
    res = evaluator.evaluate_with_rules(
        component_name="adguard-home",
        log_text=logs,
        exit_code=1,
        container_status={"running": False},
    )

    assert res["status"] == "YELLOW"
    assert "in use" in res["summary"].lower() or "port" in res["summary"].lower()
    assert res["doc_anchor"] == "USER_GUIDE.md#port-conflicts"
    assert res["user_action"] != ""


def test_rule_evaluation_fatal_jinja_red():
    evaluator = DeploymentEvaluator()
    logs = "jinja2.exceptions.UndefinedError: 'volume_path' is undefined"
    res = evaluator.evaluate_with_rules(
        component_name="nextcloud",
        log_text=logs,
        exit_code=1,
        container_status={"running": False},
    )

    assert res["status"] == "RED"
    assert "volume_path" in res["github_keywords"]


@patch("managers.deployment_evaluator.AIGeneratorEngine")
def test_evaluate_deployment_ai_success(mock_engine_cls):
    mock_engine = MagicMock()
    mock_engine.generate.return_value = (
        '{"status": "YELLOW", "summary": "Port 80 conflict", '
        '"user_action": "Change port", "doc_anchor": "USER_GUIDE.md#ports", '
        '"github_keywords": "port conflict"}'
    )
    mock_engine_cls.return_value = mock_engine

    logs = "listen tcp 0.0.0.0:80: bind: address in use"
    res = evaluate_deployment(
        component_name="nginx",
        log_text=logs,
        exit_code=1,
        container_status={"running": False},
        use_ai=True,
    )

    assert res["status"] == "YELLOW"
    assert res["summary"] == "Port 80 conflict"
    assert res["user_action"] == "Change port"


@patch("managers.deployment_evaluator.AIGeneratorEngine")
def test_evaluate_deployment_ai_fallback_on_error(mock_engine_cls):
    mock_engine = MagicMock()
    mock_engine.generate.side_effect = RuntimeError("API key missing or offline")
    mock_engine_cls.return_value = mock_engine

    logs = "Service started clean and ready."
    res = evaluate_deployment(
        component_name="adguard-home",
        log_text=logs,
        exit_code=0,
        container_status={"running": True},
        use_ai=True,
    )

    # Must fallback cleanly to rule-based evaluation without throwing
    assert res["status"] == "GREEN"
    assert "ok" in res["summary"].lower() or "success" in res["summary"].lower()
