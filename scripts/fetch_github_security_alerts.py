#!/usr/bin/env python3
"""
scripts/fetch_github_security_alerts.py

Utility script to query GitHub Security Alerts (Code Scanning / CodeQL,
Dependabot vulnerabilities, and Secret Scanning) for the NjordDeploy repository
via the GitHub REST API, displaying actionable remediation context.
"""

import argparse
import json
import os
import subprocess  # nosec B404
from typing import Any, Dict, List, Optional, Tuple

import requests

DEFAULT_REPO = "HenkVanHoek/njord-deploy"
BASE_GITHUB_API = "https://api.github.com"


def get_git_repo_name() -> str:
    """
    Detects the remote repository name from git config or returns default.
    """
    # noinspection PyBroadException
    try:
        cmd = ["git", "config", "--get", "remote.origin.url"]
        result = subprocess.run(  # nosec B603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            url = result.stdout.strip()
            # Parse git@github.com:owner/repo.git or https://github.com/owner/repo.git
            if (
                url.startswith("git@github.com:")
                or url.startswith("https://github.com/")
                or url.startswith("http://github.com/")
            ):
                if url.startswith("git@github.com:"):
                    cleaned = url[len("git@github.com:") :]
                elif url.startswith("https://github.com/"):
                    cleaned = url[len("https://github.com/") :]
                else:
                    cleaned = url[len("http://github.com/") :]
                cleaned = cleaned.lstrip(":/")
                if cleaned.endswith(".git"):
                    cleaned = cleaned[:-4]
                if cleaned:
                    return cleaned
    except Exception:  # nosec B110
        pass
    return DEFAULT_REPO


def get_auth_token(cli_token: Optional[str] = None) -> Optional[str]:
    """
    Retrieves GitHub token from CLI arg, environment variables, or .env file.
    """
    if cli_token and cli_token.strip():
        return cli_token.strip()

    env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    # Check .env file in workspace
    env_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    if os.path.exists(env_file):
        # noinspection PyBroadException
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("GITHUB_TOKEN=") or stripped.startswith(
                        "GH_TOKEN="
                    ):
                        parts = stripped.split("=", 1)
                        if len(parts) == 2:
                            _, val = parts
                            cleaned_val = val.strip("\"' ")
                            if cleaned_val:
                                return cleaned_val
        except Exception:  # nosec B110
            pass

    return None


def make_request(
    endpoint: str,
    token: Optional[str],
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Any]:
    """
    Performs an authenticated GET request to GitHub API.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "NjordDeploy-Security-Fetcher",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # noinspection PyBroadException
    try:
        response = requests.get(
            f"{BASE_GITHUB_API}/{endpoint.lstrip('/')}",
            headers=headers,
            params=params,
            timeout=15,
        )
        try:
            data = response.json()
        except Exception:
            data = {"message": response.text}
        return response.status_code, data
    except Exception as e:
        return 0, {"message": str(e)}


def fetch_code_scanning_alerts(
    repo: str, token: Optional[str], state: str = "open"
) -> List[Dict[str, Any]]:
    """
    Fetches CodeQL / Code Scanning alerts.
    """
    params = {"state": state, "per_page": 100}
    status, data = make_request(f"repos/{repo}/code-scanning/alerts", token, params)
    if status == 200 and isinstance(data, list):
        return data
    if status == 401 or status == 403 or status == 404:
        msg = data.get("message", "Authentication or permission error")
        print(f"⚠️ Code Scanning API ({status}): {msg}")
    return []


def fetch_dependabot_alerts(
    repo: str, token: Optional[str], state: str = "open"
) -> List[Dict[str, Any]]:
    """
    Fetches Dependabot vulnerability alerts.
    """
    params = {"state": state, "per_page": 100}
    status, data = make_request(f"repos/{repo}/dependabot/alerts", token, params)
    if status == 200 and isinstance(data, list):
        return data
    if status == 401 or status == 403 or status == 404:
        msg = data.get("message", "Authentication or permission error")
        print(f"⚠️ Dependabot API ({status}): {msg}")
    return []


def fetch_secret_scanning_alerts(
    repo: str, token: Optional[str], state: str = "open"
) -> List[Dict[str, Any]]:
    """
    Fetches Secret Scanning alerts.
    """
    params = {"state": state, "per_page": 100}
    status, data = make_request(f"repos/{repo}/secret-scanning/alerts", token, params)
    if status == 200 and isinstance(data, list):
        return data
    if status == 401 or status == 403 or status == 404:
        msg = data.get("message", "Authentication or permission error")
        print(f"⚠️ Secret Scanning API ({status}): {msg}")
    return []


def display_code_scanning(alerts: List[Dict[str, Any]]) -> None:
    """
    Formats and prints Code Scanning alerts.
    """
    print(f"\n{'='*70}")
    print(f"🛡️  CODE SCANNING ALERTS (CodeQL / Static Analysis): {len(alerts)} found")
    print(f"{'='*70}")
    if not alerts:
        print("✅ No open code scanning alerts found.")
        return

    for alert in alerts:
        number = alert.get("number")
        rule = alert.get("rule", {})
        rule_id = rule.get("id", "N/A")
        severity = rule.get("security_severity_level") or rule.get("severity", "medium")
        desc = rule.get("description", "No description")
        html_url = alert.get("html_url", "")

        instance = alert.get("most_recent_instance", {})
        location = instance.get("location", {})
        path = location.get("path", "unknown")
        start_line = location.get("start_line", 0)
        end_line = location.get("end_line", 0)
        line_str = (
            f"L{start_line}" if start_line == end_line else f"L{start_line}-L{end_line}"
        )
        msg_text = instance.get("message", {}).get("text", desc)

        print(f"\n[Alert #{number}] [{severity.upper()}] {rule_id}")
        print(f"  📁 Location: {path}:{line_str}")
        print(f"  📝 Issue:    {msg_text}")
        print(f"  🔗 URL:      {html_url}")


def display_dependabot(alerts: List[Dict[str, Any]]) -> None:
    """
    Formats and prints Dependabot alerts.
    """
    print(f"\n{'='*70}")
    print(f"📦 DEPENDABOT ALERTS (Vulnerable Dependencies): {len(alerts)} found")
    print(f"{'='*70}")
    if not alerts:
        print("✅ No open Dependabot alerts found.")
        return

    for alert in alerts:
        number = alert.get("number")
        advisory = alert.get("security_advisory", {})
        ghsa_id = advisory.get("ghsa_id", "N/A")
        cve_id = advisory.get("cve_id") or "No CVE"
        summary = advisory.get("summary", "No summary")
        severity = advisory.get("severity", "medium")

        dep = alert.get("dependency", {})
        package = dep.get("package", {}).get("name", "unknown")
        manifest = dep.get("manifest_path", "pyproject.toml")

        vuln = alert.get("security_vulnerability", {})
        vuln_range = vuln.get("vulnerable_version_range", "N/A")
        patched = vuln.get("first_patched_version", {})
        patched_ver = patched.get("identifier") if isinstance(patched, dict) else "N/A"
        html_url = alert.get("html_url", "")

        print(
            f"\n[Alert #{number}] [{severity.upper()}] {package} "
            f"({ghsa_id} / {cve_id})"
        )
        print(f"  📦 Package:       {package} (in {manifest})")
        print(f"  ⚠️ Vulnerable:    {vuln_range}")
        print(f"  ✅ Fixed Version: >= {patched_ver}")
        print(f"  📝 Summary:       {summary}")
        print(f"  🔗 URL:           {html_url}")


def display_secret_scanning(alerts: List[Dict[str, Any]]) -> None:
    """
    Formats and prints Secret Scanning alerts metadata without exposing tokens.
    """
    print(f"\n{'='*70}")
    print(f"🔑 SECRET SCANNING ALERTS: {len(alerts)} found")
    print(f"{'='*70}")
    if not alerts:
        print("✅ No open secret scanning alerts found.")
        return

    for item in alerts:
        alert_id = int(item.get("number", 0))
        label = str(
            item.get("secret_type_display_name") or item.get("secret_type") or "Secret"
        )
        cur_state = str(item.get("state", "open")).upper()
        det_date = str(item.get("created_at", ""))
        link = str(item.get("html_url", ""))

        print(f"\n[Alert #{alert_id}] [{cur_state}] {label}")
        print(f"  📅 Detected At: {det_date}")
        print(f"  🔗 URL:         {link}")


def main() -> None:
    """
    Main CLI entrypoint.
    """
    parser = argparse.ArgumentParser(
        description="Fetch and inspect GitHub Security Alerts for NjordDeploy"
    )
    repo_name = get_git_repo_name()
    parser.add_argument(
        "--repo",
        type=str,
        default=repo_name,
        help=f"Target GitHub repository (default: {repo_name})",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="GitHub Personal Access Token (or set GITHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["all", "code-scanning", "dependabot", "secret-scanning"],
        default="all",
        help="Alert type filter (default: all)",
    )
    parser.add_argument(
        "--state",
        type=str,
        choices=["open", "closed", "all"],
        default="open",
        help="Alert state filter (default: open)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text",
    )

    args = parser.parse_args()
    token = get_auth_token(args.token)

    if not token:
        print("⚠️ Warning: No GitHub token provided or found in environment.")
        print("GitHub Security APIs require authentication with read permissions.")
        print(
            "Please provide a token via '--token <TOKEN>' or export "
            "GITHUB_TOKEN=<TOKEN>."
        )
        print("\nRequired Token Scopes:")
        print("  - Personal Access Token (classic): 'security_events', 'repo'")
        print(
            "  - Fine-grained PAT: Read permissions for 'Code scanning alerts', "
            "'Dependabot alerts', 'Secret scanning alerts'"
        )

    results: Dict[str, Any] = {
        "repo": args.repo,
        "code_scanning": [],
        "dependabot": [],
        "secret_scanning": [],
    }

    if args.type in ("all", "code-scanning"):
        results["code_scanning"] = fetch_code_scanning_alerts(
            args.repo, token, args.state
        )
    if args.type in ("all", "dependabot"):
        results["dependabot"] = fetch_dependabot_alerts(args.repo, token, args.state)
    if args.type in ("all", "secret-scanning"):
        results["secret_scanning"] = fetch_secret_scanning_alerts(
            args.repo, token, args.state
        )

    if args.json:
        clean_results = json.loads(json.dumps(results))
        for s_alert in clean_results.get("secret_scanning", []):
            if "secret" in s_alert:
                s_alert["secret"] = "[REDACTED]"  # nosec B105
        print(json.dumps(clean_results, indent=2))
        return

    print(f"\n🔎 GitHub Security Alerts Report for: {args.repo}")
    print(f"State filter: {args.state}")

    if args.type in ("all", "code-scanning"):
        display_code_scanning(results["code_scanning"])
    if args.type in ("all", "dependabot"):
        display_dependabot(results["dependabot"])
    if args.type in ("all", "secret-scanning"):
        display_secret_scanning(results["secret_scanning"])

    total_alerts = (
        len(results["code_scanning"])
        + len(results["dependabot"])
        + len(results["secret_scanning"])
    )
    print(f"\n{'='*70}")
    print(f"Total Open Security Alerts: {total_alerts}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
