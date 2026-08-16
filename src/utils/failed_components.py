# src/utils/failed_components.py
"""
Utility functions for reading, querying, and updating untestable and skipped
components defined in docs/FAILED_COMPONENTS.md.
"""

import re
from pathlib import Path
from typing import Dict, Optional

# Default repository root path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_failed_components_path(custom_path: Optional[Path] = None) -> Path:
    """Returns the absolute path to docs/FAILED_COMPONENTS.md."""
    if custom_path:
        return custom_path
    return _PROJECT_ROOT / "docs" / "FAILED_COMPONENTS.md"


def load_untestable_components(
    doc_path: Optional[Path] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Parses FAILED_COMPONENTS.md and returns a dictionary of active
    untestable / skipped components and their metadata.

    Components marked with 'Status: Fixed' are ignored.
    """
    path = get_failed_components_path(doc_path)
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    in_skipped_section = False
    components: Dict[str, Dict[str, str]] = {}
    current_id: Optional[str] = None
    current_data: Dict[str, str] = {}

    for line in lines:
        stripped = line.strip()

        # Check section header
        if stripped.startswith("## "):
            if "Skipped" in stripped or "Untestable" in stripped:
                in_skipped_section = True
            else:
                if current_id and in_skipped_section:
                    # Check if marked as Fixed
                    if "fixed" not in current_data.get("status", "").lower():
                        components[current_id] = current_data
                    current_id = None
                    current_data = {}
                in_skipped_section = False
            continue

        if not in_skipped_section:
            continue

        # Detect component heading: e.g. ### `component-id` or ### `comp` (Desc)
        if stripped.startswith("### "):
            if current_id:
                if "fixed" not in current_data.get("status", "").lower():
                    components[current_id] = current_data
                current_id = None
                current_data = {}

            # Extract component ID inside backticks
            match = re.search(r"`([^`]+)`", stripped)
            if match:
                first_group, *rest = match.groups()
                current_id = first_group.strip()
                current_data = {
                    "raw_heading": stripped,
                    "date": "",
                    "reason": "",
                    "action": "",
                    "status": "",
                }
            continue

        if current_id:
            if "**Date**:" in stripped:
                current_data["date"] = stripped.split("**Date**:", 1)[1].strip()
            elif "**Reason**:" in stripped:
                current_data["reason"] = stripped.split("**Reason**:", 1)[1].strip()
            elif "**Action**:" in stripped:
                current_data["action"] = stripped.split("**Action**:", 1)[1].strip()
            elif "**Status**:" in stripped:
                current_data["status"] = stripped.split("**Status**:", 1)[1].strip()

    if current_id and in_skipped_section:
        if "fixed" not in current_data.get("status", "").lower():
            components[current_id] = current_data

    return components


def is_component_untestable(component_id: str, doc_path: Optional[Path] = None) -> bool:
    """Checks whether a given component ID is in the untestable components list."""
    untestable_map = load_untestable_components(doc_path)
    return component_id in untestable_map


def remove_untestable_component(
    component_id: str, doc_path: Optional[Path] = None
) -> bool:
    """
    Removes a component from the 'Skipped / Untestable Components' section
    in FAILED_COMPONENTS.md when it passes verification tests.

    Returns True if the component was found and removed, False otherwise.
    """
    path = get_failed_components_path(doc_path)
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    new_lines = []
    in_skipped_section = False
    skipping_current_comp = False
    found = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## "):
            in_skipped_section = "Skipped" in stripped or "Untestable" in stripped
            skipping_current_comp = False
            new_lines.append(line)
            continue

        if in_skipped_section and stripped.startswith("### "):
            match = re.search(r"`([^`]+)`", stripped)
            if match:
                first_group, *rest = match.groups()
                matched_id = first_group.strip()
                if matched_id == component_id:
                    skipping_current_comp = True
                    found = True
                    continue
                else:
                    skipping_current_comp = False

        if in_skipped_section and skipping_current_comp:
            # Skip lines belonging to this component until the next ### or ## heading
            continue

        new_lines.append(line)

    if found:
        # Clean up possible excessive blank lines
        cleaned_content = "\n".join(new_lines).rstrip() + "\n"
        path.write_text(cleaned_content, encoding="utf-8")
        return True

    return False


def add_or_update_untestable_component(
    component_id: str,
    reason: str,
    action: str = "Skipped for further developer inspection.",
    date_str: str = "",
    doc_path: Optional[Path] = None,
) -> None:
    """
    Adds or updates a component entry under 'Skipped / Untestable Components'
    in FAILED_COMPONENTS.md.
    """
    import time

    if not date_str:
        date_str = time.strftime("%Y-%m-%d")

    path = get_failed_components_path(doc_path)
    if not path.exists():
        initial_doc = (
            "# Failed and Difficult-to-Fix Components\n\n"
            "This document tracks components that failed verification or could "
            "not be tested/fixed within 3 attempts, along with the reasons and "
            "current status.\n\n"
            "## Skipped / Untestable Components\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(initial_doc, encoding="utf-8")

    # Remove any existing entry first to avoid duplicates
    remove_untestable_component(component_id, doc_path=path)

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    comp_block = [
        f"### `{component_id}`",
        f"*   **Date**: {date_str}",
        f"*   **Reason**: {reason}",
        f"*   **Action**: {action}",
        "",
    ]

    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if line.strip().startswith("## ") and (
            "Skipped" in line or "Untestable" in line
        ):
            new_lines.append("")
            new_lines.extend(comp_block)
            inserted = True

    if not inserted:
        new_lines.append("")
        new_lines.append("## Skipped / Untestable Components")
        new_lines.append("")
        new_lines.extend(comp_block)

    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
