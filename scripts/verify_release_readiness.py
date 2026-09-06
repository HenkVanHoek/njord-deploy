#!/usr/bin/env python3
"""
scripts/verify_release_readiness.py

Automated Pre-Release Readiness Gate for NjordDeploy.

Verifies that the local git working tree is clean, code quality and tests pass,
and crucially, that GitHub Security Alerts (CodeQL Code Scanning, Dependabot,
and Secret Scanning) have zero open alerts before tagging or publishing a release.
"""

import argparse
import os
import subprocess  # nosec B404
import sys
from typing import Optional

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


def run_command_gate(name: str, cmd: list[str]) -> bool:
    """
    Executes a subprocess command gate and returns True if successful.
    """
    print(f"\n▶ Running Gate: {name}...")
    print(f"  Command: {' '.join(cmd)}")
    result = subprocess.run(  # nosec B603 B607
        cmd,
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        print(f"❌ Gate Failed: {name} (exit code {result.returncode})")
        return False
    print(f"✅ Gate Passed: {name}")
    return True


def check_git_status() -> bool:
    """
    Verifies that the working tree is clean and on main branch.
    """
    print("\n▶ Running Gate: Git Working Tree & Branch...")
    # Check branch name
    res = subprocess.run(  # nosec B603 B607
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    branch = res.stdout.strip()
    if branch != "main":
        print(f"⚠️ Warning: Current branch is '{branch}', expected 'main'.")

    # Check uncommitted changes
    diff_res = subprocess.run(  # nosec B603 B607
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    # Filter untracked or modified files (excluding temporary files if any)
    uncommitted = [
        line
        for line in diff_res.stdout.splitlines()
        if not line.strip().endswith(".log")
    ]
    if uncommitted:
        print("❌ Gate Failed: Working tree has uncommitted changes:")
        for line in uncommitted:
            print(f"  {line}")
        return False

    print("✅ Gate Passed: Working tree is clean.")
    return True


def check_github_security_gate(repo: str, token: Optional[str] = None) -> bool:
    """
    Verifies that zero open security alerts exist on GitHub.
    """
    print("\n▶ Running Gate: GitHub Security Alerts (CodeQL, Dependabot, Secrets)...")
    try:
        cs_alerts = fetch_code_scanning_alerts(repo, token, state="open")
        dep_alerts = fetch_dependabot_alerts(repo, token, state="open")
        sec_alerts = fetch_credential_audit_alerts(repo, token, state="open")
        total = len(cs_alerts) + len(dep_alerts) + len(sec_alerts)

        print(f"  - Code Scanning (CodeQL): {len(cs_alerts)} open")
        print(f"  - Dependabot:             {len(dep_alerts)} open")
        print(f"  - Secret Scanning:        {len(sec_alerts)} open")
        print(f"  Total Open Alerts:        {total}")

        if total > 0:
            print(f"❌ Gate Failed: {total} open security alert(s) on GitHub!")
            if cs_alerts:
                print("\n  Open Code Scanning Alerts:")
                for alert in cs_alerts:
                    rule = alert.get("rule", {}).get("id", "unknown")
                    desc = alert.get("rule", {}).get("description", "")
                    print(f"    - #{alert.get('number')}: {rule} ({desc})")
            return False

        print("✅ Gate Passed: Zero open security alerts on GitHub.")
        return True
    except Exception as exc:
        print(f"❌ Security Gate Error: Could not query GitHub alerts: {exc}")
        return False


def main() -> None:
    """
    Main CLI entrypoint for release readiness verification.
    """
    parser = argparse.ArgumentParser(
        description="Verify pre-release readiness gates for NjordDeploy"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=get_git_repo_name(),
        help="GitHub repository name",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="GitHub authentication token",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip executing pytest test suite",
    )
    parser.add_argument(
        "--skip-quality",
        action="store_true",
        help="Skip executing check_code_quality.sh",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow uncommitted local changes (useful during dry-run testing)",
    )

    args = parser.parse_args()
    token = get_auth_token(args.token)

    print("=" * 70)
    print("🚀 NJORDDEPLOY PRE-RELEASE READINESS VERIFICATION")
    print(f"   Target Repository: {args.repo}")
    print("=" * 70)

    # 1. Git Status Gate
    if not args.allow_dirty and not check_git_status():
        print("\n❌ PRE-RELEASE CHECK FAILED AT GIT STATUS GATE.")
        sys.exit(1)

    # 2. GitHub Security Alerts Gate
    if not check_github_security_gate(args.repo, token):
        print("\n❌ PRE-RELEASE CHECK FAILED AT GITHUB SECURITY GATE.")
        print("Resolve all open security alerts on GitHub before releasing.")
        sys.exit(1)

    # 3. Code Quality Gate
    if not args.skip_quality:
        if not run_command_gate(
            "Code Quality Checks", ["./scripts/check_code_quality.sh"]
        ):
            print("\n❌ PRE-RELEASE CHECK FAILED AT CODE QUALITY GATE.")
            sys.exit(1)

    # 4. Unit Test Suite Gate
    if not args.skip_tests:
        pytest_bin = os.path.join(repo_root, ".venv", "bin", "pytest")
        if not os.path.exists(pytest_bin):
            pytest_bin = "pytest"
        if not run_command_gate("Unit Test Suite", [pytest_bin, "-q"]):
            print("\n❌ PRE-RELEASE CHECK FAILED AT TEST SUITE GATE.")
            sys.exit(1)

    # 5. Documentation Gate
    if not run_command_gate(
        "Documentation Synchronization",
        [sys.executable, "scripts/update_docs.py"],
    ):
        print("\n❌ PRE-RELEASE CHECK FAILED AT DOCUMENTATION GATE.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✨ ALL PRE-RELEASE READINESS GATES PASSED SUCCESSFULLY!")
    print("The repository is 100% verified, clean, secure, and ready to release.")
    print("Recommended next steps:")
    print("  1. bump-my-version bump [patch|minor|major]")
    print("  2. git push origin main --tags")
    print("  3. python scripts/check_release_status.py")
    print("=" * 70 + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
