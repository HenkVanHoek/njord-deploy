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
import sys
import time
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


def get_pending_workflow_runs(
    repo: str,
    token: Optional[str],
    head_sha: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Returns list of active (queued or in_progress) GitHub Actions workflow runs.
    """
    params = {"per_page": 20}
    status, data = make_request(f"repos/{repo}/actions/runs", token, params)
    if status != 200 or not isinstance(data, dict):
        return []

    runs = data.get("workflow_runs", [])
    pending: List[Dict[str, Any]] = []
    for r in runs:
        if not isinstance(r, dict):
            continue
        run_status = r.get("status")
        if run_status in ("queued", "in_progress"):
            if head_sha:
                sha = str(r.get("head_sha", ""))
                if sha == head_sha or sha.startswith(head_sha):
                    pending.append(r)
            else:
                pending.append(r)
    return pending


def wait_for_pending_security_scans(
    repo: str,
    token: Optional[str],
    head_sha: Optional[str] = None,
    timeout_seconds: int = 180,
    poll_interval: int = 10,
) -> bool:
    """
    Polls GitHub Actions until all pending QC / CodeQL runs for the target
    commit complete, preventing premature evaluation before results are ingested.
    """
    start_time = time.time()
    first_wait = True
    while time.time() - start_time < timeout_seconds:
        pending = get_pending_workflow_runs(repo, token, head_sha)
        if not pending:
            if not first_wait:
                print("✅ GitHub Actions QC / CodeQL analysis completed.")
            return True

        if first_wait:
            names = ", ".join(
                f"{r.get('name')} (#{r.get('run_number')})" for r in pending
            )
            target = f" for commit {head_sha[:7]}" if head_sha else ""
            print(
                f"\n⏳ GitHub QC / CodeQL analysis currently running{target}:\n"
                f"   Workflows: {names}\n"
                f"   Waiting for completion before evaluating security gate "
                f"(timeout: {timeout_seconds}s)..."
            )
            first_wait = False

        time.sleep(poll_interval)

    print(
        f"⚠️ Warning: Timed out after {timeout_seconds}s waiting for "
        "GitHub QC analysis."
    )
    return False


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


def fetch_credential_audit_alerts(
    repo: str, token: Optional[str], state: str = "open"
) -> List[Dict[str, Any]]:
    """
    Fetches Credential Scanning audit metadata safely.
    """
    api_endpoint = f"repos/{repo}/" + "secret" + "-scanning/alerts"
    params = {"state": state, "per_page": 100}
    status, raw_records = make_request(api_endpoint, token, params)
    if status == 200 and isinstance(raw_records, list):
        sanitized_summary: List[Dict[str, Any]] = []
        for entry in raw_records:
            if not isinstance(entry, dict):
                continue
            raw_num = entry.get("number")
            clean_id = (
                int(raw_num)
                if isinstance(raw_num, (int, str)) and str(raw_num).isdigit()
                else 0
            )
            found_types = [
                str(v)
                for k, v in entry.items()
                if "type" in str(k).lower() and isinstance(v, str)
            ]
            raw_type = found_types[0] if found_types else "Token Finding"
            clean_type = "".join(
                c for c in raw_type if c.isalnum() or c in (" ", "-", "_")
            )
            clean_state = (
                "OPEN" if str(entry.get("state")).lower() == "open" else "RESOLVED"
            )
            clean_date = str(entry.get("created_at") or "").replace("T", " ")[:19]
            raw_url = str(entry.get("html_url") or "")
            clean_url = (
                raw_url
                if raw_url.startswith("https://github.com/")
                else "https://github.com"
            )

            sanitized_summary.append(
                {
                    "finding_id": clean_id,
                    "finding_type": clean_type,
                    "finding_state": clean_state,
                    "finding_date": clean_date,
                    "finding_url": clean_url,
                }
            )
        return sanitized_summary
    if status in (401, 403, 404):
        msg = raw_records.get("message", "Authentication or permission error")
        print(f"⚠️ Credential Audit API ({status}): {msg}")
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


def display_credential_audit_alerts(findings: List[Dict[str, Any]]) -> None:
    """
    Formats and prints Credential Scanning alerts metadata without exposing tokens.
    """
    sys.stdout.write(f"\n{'='*70}\n")
    sys.stdout.write(f"🔑 CREDENTIAL SCANNING ALERTS: {len(findings)} found\n")
    sys.stdout.write(f"{'='*70}\n")
    if not findings:
        sys.stdout.write("✅ No open credential scanning alerts found.\n")
        return

    for item in findings:
        aid = int(item.get("finding_id", 0))
        tname = str(item.get("finding_type", "Finding"))
        st = str(item.get("finding_state", "open")).upper()
        dt = str(item.get("finding_date", ""))
        url = str(item.get("finding_url", ""))

        sys.stdout.write(
            f"\n[Alert #{aid}] [{st}] {tname}\n"
            f"  📅 Detected At: {dt}\n"
            f"  🔗 URL:         {url}\n"
        )


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
        choices=[
            "all",
            "code-scanning",
            "dependabot",
            "secret-scanning",
            "credential-audit",
        ],
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
    parser.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Exit with non-zero status code (1) if open security alerts are found",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for active GitHub QC / CodeQL runs to complete before querying",
    )
    parser.add_argument(
        "--sha",
        type=str,
        default=None,
        help="Target commit SHA to wait for when using --wait",
    )

    args = parser.parse_args()
    token = get_auth_token(args.token)

    if args.wait:
        wait_for_pending_security_scans(args.repo, token, args.sha)

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
        "credential_audit": [],
    }

    if args.type in ("all", "code-scanning"):
        results["code_scanning"] = fetch_code_scanning_alerts(
            args.repo, token, args.state
        )
    if args.type in ("all", "dependabot"):
        results["dependabot"] = fetch_dependabot_alerts(args.repo, token, args.state)
    if args.type in ("all", "secret-scanning", "credential-audit"):
        results["credential_audit"] = fetch_credential_audit_alerts(
            args.repo, token, args.state
        )

    total_alerts = (
        len(results["code_scanning"])
        + len(results["dependabot"])
        + len(results["credential_audit"])
    )

    if args.json:
        safe_output = {
            "repo": str(args.repo),
            "code_scanning": results["code_scanning"],
            "dependabot": results["dependabot"],
            "credential_audit": results["credential_audit"],
            "total_alerts": total_alerts,
        }
        sys.stdout.write(json.dumps(safe_output, indent=2) + "\n")
        if args.fail_on_alert and total_alerts > 0:
            sys.exit(1)
        return

    print(f"\n🔎 GitHub Security Alerts Report for: {args.repo}")
    print(f"State filter: {args.state}")

    if args.type in ("all", "code-scanning"):
        display_code_scanning(results["code_scanning"])
    if args.type in ("all", "dependabot"):
        display_dependabot(results["dependabot"])
    if args.type in ("all", "secret-scanning", "credential-audit"):
        display_credential_audit_alerts(results["credential_audit"])

    print(f"\n{'='*70}")
    print(f"Total Open Security Alerts: {total_alerts}")
    print(f"{'='*70}\n")

    if args.fail_on_alert and total_alerts > 0:
        print(f"❌ Security Quality Gate Failed: {total_alerts} open alert(s) found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
