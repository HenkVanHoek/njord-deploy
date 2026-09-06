#!/usr/bin/env python3
"""
scripts/check_release_status.py

Utility script to check the status of the latest GitHub Actions release pipeline run
and verify the latest GitHub Release assets for NjordDeploy.
"""

import os
import sys
from typing import Any, Dict, Optional

import requests

# Ensure repository root is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scripts.fetch_github_security_alerts import (  # noqa: E402
    fetch_code_scanning_alerts,
    fetch_credential_audit_alerts,
    fetch_dependabot_alerts,
    get_auth_token,
    get_git_repo_name,
)

REPO = get_git_repo_name()
WORKFLOW_URL = f"https://api.github.com/repos/{REPO}/actions/workflows/release.yml/runs"
RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases/latest"


def get_headers(token: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "NjordDeploy-Release-Checker",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def check_actions_status(token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    print(f"🔍 Querying GitHub Actions workflow runs for {REPO}...")
    headers = get_headers(token)
    try:
        res = requests.get(WORKFLOW_URL, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        runs = data.get("workflow_runs", [])
        if not runs:
            print("⚠️ No workflow runs found for release.yml.")
            return None

        first_run = next(iter(runs), None)
        if not first_run or not isinstance(first_run, dict):
            return None

        run_id = first_run.get("id")
        status = first_run.get("status")
        conclusion = first_run.get("conclusion")
        head_branch = first_run.get("head_branch")
        html_url = first_run.get("html_url")
        created_at = first_run.get("created_at")

        print("\n--- GitHub Actions Release Pipeline Run ---")
        print(f"Run ID:      {run_id}")
        print(f"Tag/Ref:     {head_branch}")
        print(f"Created At:  {created_at}")
        print(f"Status:      {status}")
        print(f"Conclusion:  {conclusion if conclusion else 'In Progress...'}")
        print(f"URL:         {html_url}")

        return first_run
    except Exception as e:
        print(f"❌ Failed to fetch GitHub Actions runs: {e}")
        return None


def check_latest_release(token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    print("\n🔍 Querying latest published release on GitHub...")
    headers = get_headers(token)
    try:
        res = requests.get(RELEASES_URL, headers=headers, timeout=10)
        if res.status_code == 404:
            print("⚠️ No published releases found yet.")
            return None
        res.raise_for_status()
        rel = res.json()
        if not isinstance(rel, dict):
            return None

        tag_name = rel.get("tag_name")
        name = rel.get("name")
        published_at = rel.get("published_at")
        assets = rel.get("assets", [])

        print("--- Latest Published GitHub Release ---")
        print(f"Tag Name:     {tag_name}")
        print(f"Title:        {name}")
        print(f"Published At: {published_at}")
        print(f"Assets Count: {len(assets)}")

        for asset in assets:
            if isinstance(asset, dict):
                size_mb = asset.get("size", 0) / (1024 * 1024)
                print(f"  - {asset.get('name')} ({size_mb:.2f} MB)")

        return rel
    except Exception as e:
        print(f"❌ Failed to fetch latest release details: {e}")
        return None


def check_security_status(token: Optional[str] = None) -> int:
    """
    Queries open CodeQL, Dependabot, and Secret Scanning alerts on GitHub.
    Returns the total count of open alerts.
    """
    print("\n🔍 Querying GitHub Security Alerts (CodeQL, Dependabot, Secrets)...")
    try:
        cs_alerts = fetch_code_scanning_alerts(REPO, token, state="open")
        dep_alerts = fetch_dependabot_alerts(REPO, token, state="open")
        sec_alerts = fetch_credential_audit_alerts(REPO, token, state="open")
        total = len(cs_alerts) + len(dep_alerts) + len(sec_alerts)

        print("--- GitHub Security Status ---")
        print(f"Code Scanning (CodeQL): {len(cs_alerts)} open")
        print(f"Dependabot:             {len(dep_alerts)} open")
        print(f"Secret Scanning:        {len(sec_alerts)} open")
        print(f"Total Open Alerts:      {total}")
        return total
    except Exception as exc:
        print(f"⚠️ Could not fetch security alerts: {exc}")
        return 0


def main() -> None:
    token = get_auth_token()
    run = check_actions_status(token)
    check_latest_release(token)
    open_alerts = check_security_status(token)

    if open_alerts > 0:
        print(f"\n❌ CRITICAL: Found {open_alerts} open security alert(s) on GitHub!")
        sys.exit(1)

    if run and run.get("conclusion") == "failure":
        print("\n❌ CRITICAL: The latest release pipeline failed!")
        sys.exit(1)
    elif run and run.get("conclusion") == "success":
        print("\n✅ SUCCESS: The latest release pipeline completed successfully!")
        sys.exit(0)
    elif run and run.get("status") == "in_progress":
        print("\n⏳ IN PROGRESS: The release pipeline is currently building...")
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
