#!/usr/bin/env python3
"""
Batch test runner for NjordDeploy components on Proxmox LXC.
Dynamically resolves testable components from the metadata file and
excludes skipped ones.
"""

import json
import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
METADATA_FILE = PROJECT_ROOT / "config" / "components_metadata.json"
TEMPLATES_DIR = PROJECT_ROOT / "component_templates"

# Skipped components due to hardware, registry, or pre-existing state requirements
SKIPPED_COMPONENTS = ["web-notepad", "zigbee2mqtt", "lora-service", "notify-push"]


def main():
    if not METADATA_FILE.exists():
        print(f"Error: Metadata file not found at {METADATA_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    components = metadata.get("components", {})

    # Filter valid components that have compose templates and are not skipped
    testable_components = []
    for comp_id in components.keys():
        if comp_id in SKIPPED_COMPONENTS:
            continue

        # Verify template exists
        template_file = TEMPLATES_DIR / comp_id / "docker-compose.template.yml"
        if template_file.exists():
            testable_components.append(comp_id)

    if not testable_components:
        print("No testable components found!")
        sys.exit(0)

    # Sort components alphabetically for predictable execution order
    testable_components.sort()

    components_str = ",".join(testable_components)
    print(f"Found {len(testable_components)} testable components:")
    for comp_id in testable_components:
        print(f" - {comp_id}")
    print()

    # Build test command
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    runner_script = PROJECT_ROOT / "scripts" / "proxmox_test_runner.py"

    cmd = [
        str(venv_python),
        str(runner_script),
        "--components",
        components_str,
        "--mode",
        "lxc",
    ]

    print("Running command:")
    print(" ".join(cmd))
    print()

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Batch testing failed with exit code: {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
