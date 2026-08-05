#!/usr/bin/env python3
"""
scripts/check_release_status.py

Utility script to check the status of the latest GitHub Actions release pipeline run
and verify the latest GitHub Release assets for NjordDeploy.
"""

import sys

import requests

REPO = "HenkVanHoek/njord-deploy"
WORKFLOW_URL = f"https://api.github.com/repos/{REPO}/actions/workflows/release.yml/runs"
RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "NjordDeploy-Release-Checker",
}


def check_actions_status():
    print(f"🔍 Querying GitHub Actions workflow runs for {REPO}...")
    try:
        res = requests.get(WORKFLOW_URL, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        runs = data.get("workflow_runs", [])
        if not runs:
            print("⚠️ No workflow runs found for release.yml.")
            return None

        latest_run = runs[0]
        run_id = latest_run.get("id")
        status = latest_run.get("status")
        conclusion = latest_run.get("conclusion")
        head_branch = latest_run.get("head_branch")
        html_url = latest_run.get("html_url")
        created_at = latest_run.get("created_at")

        print("\n--- GitHub Actions Release Pipeline Run ---")
        print(f"Run ID:      {run_id}")
        print(f"Tag/Ref:     {head_branch}")
        print(f"Created At:  {created_at}")
        print(f"Status:      {status}")
        print(f"Conclusion:  {conclusion if conclusion else 'In Progress...'}")
        print(f"URL:         {html_url}")

        return latest_run
    except Exception as e:
        print(f"❌ Failed to fetch GitHub Actions runs: {e}")
        return None


def check_latest_release():
    print("\n🔍 Querying latest published release on GitHub...")
    try:
        res = requests.get(RELEASES_URL, headers=HEADERS, timeout=10)
        if res.status_code == 404:
            print("⚠️ No published releases found yet.")
            return None
        res.raise_for_status()
        rel = res.json()

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
            size_mb = asset.get("size", 0) / (1024 * 1024)
            print(f"  - {asset.get('name')} ({size_mb:.2f} MB)")

        return rel
    except Exception as e:
        print(f"❌ Failed to fetch latest release details: {e}")
        return None


def main():
    run = check_actions_status()
    check_latest_release()

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
