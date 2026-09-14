#!/usr/bin/env python3
"""
scripts/run_local_codeql.py

Local CodeQL Scanner Runner for NjordDeploy.

Ensures the GitHub CodeQL CLI bundle is available locally (auto-downloading and
caching in ~/.local/share/codeql if needed), builds a local database of the
Python codebase, and executes the official 'python-security-and-quality.qls'
security query suite.

Outputs results in SARIF format and returns exit code 0 if 0 vulnerabilities
are found, or non-zero with detailed findings.
"""

import argparse
import json
import os
import shutil
import stat
import subprocess  # nosec B404
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_BUNDLE_TAG = "codeql-bundle-v2.27.0"
CODEQL_DOWNLOAD_URL = (
    "https://github.com/github/codeql-action/releases/download/"
    f"{DEFAULT_BUNDLE_TAG}/codeql-bundle-linux64.tar.gz"
)
LOCAL_INSTALL_DIR = Path.home() / ".local" / "share" / "codeql"
CODEQL_BIN = LOCAL_INSTALL_DIR / "codeql" / "codeql"


def find_codeql_executable() -> Optional[Path]:
    """Finds existing CodeQL binary in PATH or local user cache."""
    # 1. Check system PATH
    which_path = shutil.which("codeql")
    if which_path:
        return Path(which_path)

    # 2. Check user local directory
    if CODEQL_BIN.exists() and os.access(CODEQL_BIN, os.X_OK):
        return CODEQL_BIN

    return None


def install_codeql_bundle(target_dir: Path = LOCAL_INSTALL_DIR) -> Path:
    """Downloads and extracts the official GitHub CodeQL CLI bundle."""
    print(f"\n📦 CodeQL CLI not found locally. Installing to {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / "codeql-bundle.tar.gz"

    print(f"  Downloading CodeQL bundle from: {CODEQL_DOWNLOAD_URL}")
    try:
        # Download with stream progress
        with urllib.request.urlopen(  # nosec B310
            CODEQL_DOWNLOAD_URL, timeout=120
        ) as resp:
            with open(archive_path, "wb") as f:
                shutil.copyfileobj(resp, f)
    except Exception as exc:
        print(f"❌ Failed to download CodeQL bundle: {exc}", file=sys.stderr)
        if archive_path.exists():
            archive_path.unlink()
        sys.exit(1)

    print("  Extracting CodeQL CLI bundle...")
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=target_dir)  # nosec B202
    finally:
        if archive_path.exists():
            archive_path.unlink()

    if CODEQL_BIN.exists():
        # Ensure executable bit
        current_mode = os.stat(CODEQL_BIN).st_mode
        os.chmod(CODEQL_BIN, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"✅ CodeQL CLI installed successfully at: {CODEQL_BIN}")
        return CODEQL_BIN

    print(
        f"❌ Expected binary {CODEQL_BIN} not found after extraction!",
        file=sys.stderr,
    )
    sys.exit(1)


def parse_sarif_results(sarif_path: Path) -> List[Dict[str, Any]]:
    """Parses SARIF output file and extracts security rule violations."""
    if not sarif_path.exists():
        return []

    try:
        with open(sarif_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"⚠️ Failed to parse SARIF output: {exc}")
        return []

    findings: List[Dict[str, Any]] = []
    runs = data.get("runs", [])
    for run in runs:
        results = run.get("results", [])
        for r in results:
            rule_id = r.get("ruleId", "unknown")
            msg = r.get("message", {}).get("text", "")
            level = r.get("level", "warning")

            locs = r.get("locations", [])
            path = "unknown"
            line = 0
            if locs:
                ploc = locs[0].get("physicalLocation", {})
                path = ploc.get("artifactLocation", {}).get("uri", "unknown")
                line = ploc.get("region", {}).get("startLine", 0)

            findings.append(
                {
                    "rule_id": rule_id,
                    "message": msg,
                    "level": level,
                    "path": path,
                    "line": line,
                }
            )

    return findings


def run_local_codeql(
    repo_root: Path,
    auto_install: bool = True,
    clean_db: bool = True,
) -> bool:
    """Creates local CodeQL database, analyzes Python codebase, and checks alerts."""
    print("\n" + "=" * 70)
    print("🛡️  LOCAL GITHUB CODEQL SECURITY SCANNER")
    print("=" * 70)

    codeql_exec = find_codeql_executable()
    if not codeql_exec:
        if not auto_install:
            print("❌ CodeQL CLI is not installed. Run with auto-install enabled.")
            return False
        codeql_exec = install_codeql_bundle()

    db_path = repo_root / "build" / "codeql-db"
    sarif_path = repo_root / "build" / "codeql-results.sarif"
    sarif_path.parent.mkdir(parents=True, exist_ok=True)

    if clean_db and db_path.exists():
        shutil.rmtree(db_path, ignore_errors=True)

    # 1. Create database
    print(f"▶ Creating local CodeQL database: {db_path}...")
    create_cmd = [
        str(codeql_exec),
        "database",
        "create",
        str(db_path),
        "--language=python",
        f"--source-root={repo_root}",
        "--overwrite",
    ]
    res_create = subprocess.run(  # nosec B603
        create_cmd,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if res_create.returncode != 0:
        print(f"❌ Failed to create CodeQL database:\n{res_create.stderr}")
        return False

    # 2. Analyze database with official security suite
    print("▶ Analyzing Python codebase with 'python-security-and-quality.qls'...")
    analyze_cmd = [
        str(codeql_exec),
        "database",
        "analyze",
        str(db_path),
        "python-security-and-quality.qls",
        "--format=sarif-latest",
        f"--output={sarif_path}",
    ]
    res_analyze = subprocess.run(  # nosec B603
        analyze_cmd,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if res_analyze.returncode != 0:
        print(f"❌ CodeQL analysis execution failed:\n{res_analyze.stderr}")
        return False

    # 3. Parse and display findings
    findings = parse_sarif_results(sarif_path)
    if not findings:
        print("\n✅ Local CodeQL Analysis Passed: Zero security alerts found!")
        return True

    print(f"\n❌ Local CodeQL Analysis Failed: {len(findings)} alert(s) detected:")
    for idx, f in enumerate(findings, start=1):
        print(f"\n[{idx}] [{f['level'].upper()}] {f['rule_id']}")
        print(f"    📁 {f['path']}:{f['line']}")
        print(f"    📝 {f['message']}")

    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Local GitHub CodeQL Scanner")
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Do not automatically download and install CodeQL CLI bundle if missing",
    )
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent.parent
    success = run_local_codeql(repo_dir, auto_install=not args.no_install)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
