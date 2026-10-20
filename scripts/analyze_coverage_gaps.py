#!/usr/bin/env python3
"""Coverage Gap Analyzer & Per-Module Quality Gate for NjordDeploy.

Enforces a strict per-module line coverage threshold (default: >= 95.0%) across
every individual source module in src/. Parses pytest-cov JSON reports,
classifies uncovered lines into semantic actionable categories, prints a
detailed scorecard, and exits with 1 if any module fails the mandate.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess  # nosec B404
import sys
from typing import Any

DEFAULT_EXCLUDES = (
    "tests/*",
    "test_*",
    "*_test.py",
    "conftest.py",
    "scripts/*",
    "ansible/*",
    "component_templates/*",
    "docs/*",
    "linux/*",
    "windows/*",
    ".venv/*",
    "venv/*",
    "build/*",
    "dist/*",
    "*.egg-info/*",
    "setup.py",
)

SEMANTIC_CATEGORIES = (
    "UNAUTHENTICATED_GUARD",
    "RBAC_AUTHORIZATION",
    "DEFENSIVE_FALLBACK",
    "ORM_TRANSACTION_ROLLBACK",
    "EDGE_INPUT_VALIDATION",
    "EXTERNAL_SERVICE_FAILURE",
)


def run_pytest_coverage_json(
    output_json: str, cov_packages: list[str] | None = None
) -> bool:
    """Runs pytest with coverage and exports a JSON report."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
    ]
    if cov_packages:
        for pkg in cov_packages:
            cmd.append(f"--cov={pkg}")
    else:
        cmd.append("--cov=src")

    cmd.extend(
        [
            f"--cov-report=json:{output_json}",
            "--cov-report=term-missing",
            "-q",
        ]
    )
    proc = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603
    return proc.returncode == 0


def classify_line_content(line_text: str) -> str:
    """Classifies an uncovered line into one of 6 semantic gap categories."""
    stripped = line_text.strip()
    lowered = stripped.lower()

    # 1. ORM / Exception / Rollback
    if (
        stripped.startswith("except ")
        or stripped.startswith("except:")
        or "rollback" in lowered
        or "abort(500" in stripped
        or "500" in stripped
    ):
        return "ORM_TRANSACTION_ROLLBACK"

    # 2. RBAC / Authorization
    if (
        "role" in lowered
        or "permission" in lowered
        or "unauthorized" in lowered
        or "forbidden" in lowered
        or "tenant" in lowered
        or "cross-tenant" in lowered
        or "abort(403" in stripped
        or "403" in stripped
    ):
        return "RBAC_AUTHORIZATION"

    # 3. Unauthenticated Guard
    if (
        "login_required" in lowered
        or "is_auth_enabled" in lowered
        or "is_admin_configured" in lowered
        or "logged_in" in lowered
        or "session.get(" in lowered
        or 'redirect(url_for("login' in lowered
        or 'redirect(url_for("setup' in lowered
        or "verify_api_key" in lowered
        or "auth_token" in lowered
        or "abort(401" in stripped
        or "401" in stripped
    ):
        return "UNAUTHENTICATED_GUARD"

    # 4. External Service Failure
    if (
        "timeout" in lowered
        or "requests." in lowered
        or "timeoutexpired" in lowered
        or "connectionrefused" in lowered
        or "filenotfounderror" in lowered
        or "webhook" in lowered
        or "stripe" in lowered
        or "chatwoot" in lowered
        or "nmap" in lowered
        or "ssh" in lowered
        or "502" in stripped
        or "504" in stripped
    ):
        return "EXTERNAL_SERVICE_FAILURE"

    # 5. Edge Input Validation
    if (
        "validate_" in lowered
        or "isinstance(" in lowered
        or "if not " in lowered
        or "abort(400" in stripped
        or "400" in stripped
        or "bad request" in lowered
        or "valueerror" in lowered
        or "keyerror" in lowered
    ):
        return "EDGE_INPUT_VALIDATION"

    # 6. Defensive Fallback
    return "DEFENSIVE_FALLBACK"


def should_include_file(
    rel_path: str,
    includes: list[str] | None,
    excludes: list[str],
) -> bool:
    """Determines whether a file belongs to the audited source tree."""
    normalized = rel_path.replace("\\", "/")

    # Exclude non-src files by default unless explicitly included
    if not normalized.startswith("src/"):
        return False

    # Check explicit excludes
    for pattern in excludes:
        clean_pat = pattern.strip()
        if fnmatch.fnmatch(normalized, clean_pat) or fnmatch.fnmatch(
            os.path.basename(normalized), clean_pat
        ):
            return False

    # If includes specified, file must match at least one
    if includes:
        matched = False
        for inc in includes:
            clean_inc = inc.strip().rstrip("/")
            if normalized == clean_inc or normalized.startswith(f"{clean_inc}/"):
                matched = True
                break
        if not matched:
            return False

    return normalized.endswith(".py")


def analyze_coverage_json(
    json_path: str,
    min_coverage: float = 95.0,
    includes: list[str] | None = None,
    excludes: list[str] | None = None,
) -> int:
    """Parses coverage JSON, prints scorecard, and enforces per-module >= 95%."""
    if not os.path.exists(json_path):
        print(f"❌ Coverage JSON bestand niet gevonden: {json_path}")
        print("Tip: Voer eerst pytest uit met --cov-report=json:<pad>")
        return 1

    active_excludes = list(DEFAULT_EXCLUDES)
    if excludes:
        active_excludes.extend(excludes)

    with open(json_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    totals = data.get("totals", {})
    num_statements = totals.get("num_statements", 0)
    missing_statements = totals.get("missing_lines", 0)
    percent_covered = (
        round((num_statements - missing_statements) / num_statements * 100, 2)
        if num_statements > 0
        else 100.0
    )

    print("==================================================")
    print(f"   ⛳ NjordDeploy Per-Module Quality Gate (≥ {min_coverage:.1f}%) ")
    print("==================================================")
    print(f"Totale lijn-dekking: {percent_covered:.2f}% (Norm: ≥ {min_coverage}%)")
    print(f"Statements: {num_statements} | Gemist: {missing_statements}\n")

    files_data = data.get("files", {})
    gap_summary: dict[str, list[dict[str, Any]]] = {}
    module_scores: list[dict[str, Any]] = []
    failed_modules: list[dict[str, Any]] = []

    for file_path, file_info in sorted(files_data.items()):
        rel_path = file_path
        if os.path.isabs(rel_path):
            rel_path = os.path.relpath(rel_path, os.getcwd())

        if not should_include_file(rel_path, includes, active_excludes):
            continue

        summary = file_info.get("summary", {})
        n_stmts = summary.get("num_statements", 0)
        n_miss = summary.get("missing_lines", 0)
        cov_pct = round((n_stmts - n_miss) / n_stmts * 100, 2) if n_stmts > 0 else 100.0

        # Skip empty __init__.py files
        if n_stmts == 0:
            continue

        mod_entry = {
            "path": rel_path,
            "percent": cov_pct,
            "statements": n_stmts,
            "missing": n_miss,
            "passed": cov_pct >= min_coverage,
        }
        module_scores.append(mod_entry)
        if cov_pct < min_coverage:
            failed_modules.append(mod_entry)

        missing_lines = file_info.get("missing_lines", [])
        if missing_lines:
            file_lines = []
            if os.path.exists(rel_path):
                with open(rel_path, "r", encoding="utf-8") as sf:
                    file_lines = sf.readlines()

            file_gaps = []
            for line_num in missing_lines:
                content = ""
                if 1 <= line_num <= len(file_lines):
                    content = file_lines[line_num - 1].strip()
                category = classify_line_content(content)
                file_gaps.append(
                    {
                        "line": line_num,
                        "content": content,
                        "category": category,
                    }
                )
            gap_summary[rel_path] = file_gaps

    print("📊 Per-Module Scorecard:")
    print("-" * 75)
    print(f"{'Module':<45} {'Stmts':>6} {'Miss':>5} {'Cover':>8} {'Status':>8}")
    print("-" * 75)
    for mod in module_scores:
        status_tag = "✅ PASS" if mod["passed"] else "❌ FAIL"
        print(
            f"{mod['path']:<45} {mod['statements']:>6} {mod['missing']:>5} "
            f"{mod['percent']:>7.2f}% {status_tag:>8}"
        )
    print("-" * 75)
    print("")

    if failed_modules:
        print("⚠️  SEMANTISCHE GAP-ANALYSE VOOR GEFAALDE MODULES:")
        print("=" * 75)
        for fm in failed_modules:
            f_path = fm["path"]
            gaps = gap_summary.get(f_path, [])
            pct_str = f"{fm['percent']:.2f}%"
            print(
                f"\n📁 {f_path} (Dekking: {pct_str}, " f"{len(gaps)} gemiste regels):"
            )

            # Categorize gaps
            cat_counts: dict[str, int] = {}
            for g in gaps:
                cat = g["category"]
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
                print(f"   • {cat:<26}: {count} regel(s)")

            print("   --- Detailweergave ---")
            for g in gaps:
                print(f"   L{g['line']:<4} [{g['category']:<26}] {g['content']}")

        print("\n" + "=" * 75)
        print(
            "❌ GEFAALDE MODULES (voldoen niet aan de per-module "
            f"≥ {min_coverage:.1f}% norm):"
        )
        for fm in failed_modules:
            print(
                f"   - {fm['path']}: {fm['percent']:.2f}% "
                f"(vereist: ≥ {min_coverage}%, gemist: {fm['missing']} regels)"
            )
        print(
            "\n🚫 Kwaliteitspoort geblokkeerd: Geen enkele module mag zich "
            "verschuilen achter een globaal gemiddelde."
        )
        return 1

    print(
        f"✨ GEWELDIG! Alle {len(module_scores)} modules voldoen individueel "
        f"aan de Air Traffic Control norm (≥ {min_coverage}%)!"
    )
    return 0


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Coverage Gap Analyzer & Per-Module Quality Gate (>= 95%)"
    )
    parser.add_argument(
        "--json-file",
        default="/tmp/njord_coverage.json",  # nosec B108
        help="Pad naar coverage JSON bestand (standaard: /tmp/njord_coverage.json)",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=95.0,
        help="Minimaal vereist percentage per module (standaard: 95.0)",
    )
    parser.add_argument(
        "--include",
        help="Komma-gescheiden lijst van modules om mee te nemen",
    )
    parser.add_argument(
        "--exclude",
        help="Extra komma-gescheiden patterns om uit te sluiten",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Voer eerst pytest uit om automatisch coverage JSON te genereren",
    )
    args = parser.parse_args()

    include_list = (
        [p.strip() for p in args.include.split(",")] if args.include else None
    )
    exclude_list = (
        [p.strip() for p in args.exclude.split(",")] if args.exclude else None
    )

    if args.run:
        print("🏃 Uitvoeren van pytest coverage suite...")
        run_pytest_coverage_json(args.json_file, include_list)

    exit_code = analyze_coverage_json(
        args.json_file,
        args.min_coverage,
        include_list,
        exclude_list,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
