"""
tests/test_fetch_github_security_alerts.py

Unit tests for scripts/fetch_github_security_alerts.py.
"""

from unittest.mock import MagicMock, patch

from scripts.fetch_github_security_alerts import (
    DEFAULT_REPO,
    display_code_scanning,
    display_credential_audit_alerts,
    display_dependabot,
    fetch_code_scanning_alerts,
    fetch_credential_audit_alerts,
    fetch_dependabot_alerts,
    get_auth_token,
    get_git_repo_name,
    make_request,
)


def test_get_git_repo_name_default() -> None:
    with patch("subprocess.run", side_effect=Exception("git error")):
        repo = get_git_repo_name()
        assert repo == DEFAULT_REPO


def test_get_git_repo_name_success() -> None:
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "git@github.com:HenkVanHoek/njord-deploy.git\n"
    with patch("subprocess.run", return_value=mock_res):
        repo = get_git_repo_name()
        assert repo == "HenkVanHoek/njord-deploy"


def test_get_auth_token() -> None:
    # CLI token takes precedence
    token = get_auth_token("cli-token-123")
    assert token == "cli-token-123"

    # Environment variable
    with patch.dict("os.environ", {"GITHUB_TOKEN": "env-token-456"}):
        token = get_auth_token(None)
        assert token == "env-token-456"

    # Fallback to None if nothing set and no .env file
    with patch.dict("os.environ", {}, clear=True):
        with patch("os.path.exists", return_value=False):
            token = get_auth_token(None)
            assert token is None


def test_make_request_success() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": 1}]

    with patch("requests.get", return_value=mock_resp):
        status, data = make_request("test/endpoint", "token123")
        assert status == 200
        assert data == [{"id": 1}]


def test_fetch_code_scanning_alerts() -> None:
    sample_alerts = [{"number": 1, "rule": {"id": "py/full-ssrf"}}]
    with patch(
        "scripts.fetch_github_security_alerts.make_request",
        return_value=(200, sample_alerts),
    ):
        alerts = fetch_code_scanning_alerts("owner/repo", "token")
        assert len(alerts) == 1
        first_alert, *rest = alerts
        assert first_alert["number"] == 1


def test_fetch_dependabot_alerts() -> None:
    sample_alerts = [{"number": 2, "dependency": {"package": {"name": "requests"}}}]
    with patch(
        "scripts.fetch_github_security_alerts.make_request",
        return_value=(200, sample_alerts),
    ):
        alerts = fetch_dependabot_alerts("owner/repo", "token")
        assert len(alerts) == 1
        first_alert, *rest = alerts
        assert first_alert["number"] == 2


def test_fetch_credential_audit_alerts() -> None:
    sample_alerts = [{"number": 3, "token_type": "api_key"}]
    with patch(
        "scripts.fetch_github_security_alerts.make_request",
        return_value=(200, sample_alerts),
    ):
        alerts = fetch_credential_audit_alerts("owner/repo", "token")
        assert len(alerts) == 1
        first_alert, *rest = alerts
        assert first_alert["finding_id"] == 3


def test_display_helpers(capsys) -> None:
    code_alerts = [
        {
            "number": 10,
            "rule": {
                "id": "py/full-ssrf",
                "severity": "high",
                "description": "SSRF vulnerability",
            },
            "most_recent_instance": {
                "location": {"path": "src/app.py", "start_line": 50, "end_line": 50},
                "message": {"text": "SSRF in requests.get"},
            },
            "html_url": "https://github.com/alert/10",
        }
    ]
    display_code_scanning(code_alerts)
    captured = capsys.readouterr()
    assert "py/full-ssrf" in captured.out
    assert "src/app.py:L50" in captured.out

    dep_alerts = [
        {
            "number": 20,
            "security_advisory": {
                "ghsa_id": "GHSA-1234",
                "cve_id": "CVE-2024-1234",
                "summary": "Vulnerable pkg",
                "severity": "high",
            },
            "dependency": {
                "package": {"name": "urllib3"},
                "manifest_path": "pyproject.toml",
            },
            "security_vulnerability": {
                "vulnerable_version_range": "< 2.0.0",
                "first_patched_version": {"identifier": "2.0.0"},
            },
            "html_url": "https://github.com/alert/20",
        }
    ]
    display_dependabot(dep_alerts)
    captured = capsys.readouterr()
    assert "urllib3" in captured.out
    assert "GHSA-1234" in captured.out

    credential_findings = [
        {
            "finding_id": 30,
            "finding_type": "Personal Access Token",
            "finding_state": "open",
            "finding_date": "2026-01-01 00:00:00",
            "finding_url": "https://github.com/alert/30",
        }
    ]
    display_credential_audit_alerts(credential_findings)
    captured = capsys.readouterr()
    assert "Personal Access Token" in captured.out
