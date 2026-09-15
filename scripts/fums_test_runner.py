#!/usr/bin/env python3
"""Operational CLI Test Runner for NjordDeploy FUMS.

Executes and verifies all FUMS unit, security, and operational end-to-end
test suites. Can be executed standalone from the terminal or integrated into
automated CI/CD pipelines.

Usage:
    python3 scripts/fums_test_runner.py
    python3 scripts/fums_test_runner.py --suite security
    python3 scripts/fums_test_runner.py --suite e2e
"""

import argparse
import logging
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import List

# Ensure we can import project modules if needed
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [FUMS-RUNNER]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("fums_test_runner")


def run_test_suite(suite_paths: List[str]) -> bool:
    """Executes pytest for the specified test suite paths."""
    cmd = [sys.executable, "-m", "pytest", "-v"] + suite_paths
    logger.info(f"Executing test command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(project_root))  # nosec B603
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NjordDeploy FUMS Operational & Security Test Runner"
    )
    parser.add_argument(
        "--suite",
        choices=["all", "unit", "security", "e2e"],
        default="all",
        help="Select which FUMS test suite to run (default: all)",
    )
    args = parser.parse_args()

    suites = {
        "unit": [
            "tests/utils/test_risa_prefilter.py",
            "tests/utils/test_fums_notifier.py",
            "tests/managers/test_gatekeeper_manager.py",
            "tests/managers/test_customer_sandbox_manager.py",
            "tests/managers/test_fleet_update_manager.py",
        ],
        "security": [
            "tests/fums/test_fums_security.py",
        ],
        "e2e": [
            "tests/fums/test_fums_operational_e2e.py",
        ],
    }

    if args.suite == "all":
        target_paths: List[str] = suites["unit"] + suites["security"] + suites["e2e"]
    else:
        target_paths = suites[args.suite]

    logger.info(
        f"Starting FUMS verification suite [{args.suite.upper()}] "
        f"({len(target_paths)} test files)..."
    )

    success = run_test_suite(target_paths)
    if success:
        logger.info(f"✅ FUMS [{args.suite.upper()}] verification PASSED 100%.")
        return 0

    logger.error(f"❌ FUMS [{args.suite.upper()}] verification FAILED.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
