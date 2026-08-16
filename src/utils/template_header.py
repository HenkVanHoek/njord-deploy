# src/utils/template_header.py
"""Utility to manage and cumulatively update docker-compose template headers."""

import re
import time
from typing import Dict, Optional


def merge_platform_notes(
    existing_notes: str,
    mode: str,
    engine: str,
    version: str,
    test_date: Optional[str] = None,
) -> str:
    """Merges a new test result into existing platform_notes cumulatively.

    Format produced:
    Tested on Proxmox LXC: docker (v1.0, 2026-08-14), podman (v1.0, 2026-08-14);
    Proxmox VM: docker (v1.0, 2026-08-14).
    """
    if not test_date:
        test_date = time.strftime("%Y-%m-%d")

    clean_mode = "VM" if mode.upper() == "VM" else "LXC"
    clean_engine = engine.lower().strip()
    clean_version = (
        version.strip()
        if version and version.lower() not in ("none", "unknown")
        else "latest"
    )

    # Dictionary: {platform: {engine: {"version": ..., "date": ...}}}
    platforms: Dict[str, Dict[str, Dict[str, str]]] = {}

    # Parse existing notes
    if existing_notes and existing_notes.strip() not in (
        "None",
        "none",
        '""',
        "''",
    ):
        raw = existing_notes.strip().strip('"').strip("'")
        if raw.startswith("Tested on ") or raw.startswith("Tested successfully on "):
            raw = (
                raw.replace("Tested on ", "")
                .replace("Tested successfully on ", "")
                .rstrip(".")
            )

        # Split by platform delimiter ';'
        sections = [s.strip() for s in raw.split(";") if s.strip()]
        for sec in sections:
            plat_name = None
            if "Proxmox LXC" in sec:
                plat_name = "Proxmox LXC"
            elif "Proxmox VM" in sec:
                plat_name = "Proxmox VM"

            if plat_name:
                if plat_name not in platforms:
                    platforms[plat_name] = {}

                # Check if structured: "docker (v1.0, 2026-08-14)"
                # Pattern: (docker|podman)(?:\s*\(([^,]+),\s*([^)]+)\))?
                matches = re.findall(
                    r"(docker|podman)(?:\s*\(([^,]+),\s*([^)]+)\))?",
                    sec,
                    re.IGNORECASE,
                )
                for eng, ver, dt in matches:
                    eng_lower = eng.lower()
                    ver_val = ver.strip() if ver else "latest"
                    dt_val = dt.strip() if dt else test_date
                    platforms[plat_name][eng_lower] = {
                        "version": ver_val,
                        "date": dt_val,
                    }

    # Add or update current test run
    cur_plat = f"Proxmox {clean_mode}"
    if cur_plat not in platforms:
        platforms[cur_plat] = {}

    platforms[cur_plat][clean_engine] = {
        "version": clean_version,
        "date": test_date,
    }

    # Format result string
    ordered_plats = [p for p in ["Proxmox LXC", "Proxmox VM"] if p in platforms]
    for p in sorted(platforms.keys()):
        if p not in ordered_plats:
            ordered_plats.append(p)

    plat_strs = []
    for plat in ordered_plats:
        eng_dict = platforms[plat]
        ordered_engs = [e for e in ["docker", "podman"] if e in eng_dict]
        for e in sorted(eng_dict.keys()):
            if e not in ordered_engs:
                ordered_engs.append(e)

        eng_parts = []
        for eng in ordered_engs:
            info = eng_dict[eng]
            eng_parts.append(f"{eng} ({info['version']}, {info['date']})")

        plat_strs.append(f"{plat}: {', '.join(eng_parts)}")

    if not plat_strs:
        return (
            f"Tested on Proxmox {clean_mode}: "
            f"{clean_engine} ({clean_version}, {test_date})."
        )

    return f"Tested on {'; '.join(plat_strs)}."


def update_template_header_content(
    content: str,
    mode: str,
    engine: str,
    tested_version: str,
    test_date: Optional[str] = None,
) -> str:
    """Updates the header comments in a docker-compose template string."""
    if not test_date:
        test_date = time.strftime("%Y-%m-%d")

    clean_version = (
        tested_version.strip()
        if tested_version and tested_version.lower() not in ("none", "unknown")
        else "latest"
    )

    lines = content.splitlines()
    updated_lines = []
    in_header = True
    status_found = False
    version_found = False
    notes_found = False
    existing_notes = ""
    existing_version = "latest"

    # First pass: find existing values
    for line in lines:
        if line.startswith("#"):
            stripped = line[1:].strip()
            if stripped.startswith("last_tested_version:"):
                val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                if val and val.lower() not in ("none", "unknown"):
                    existing_version = val
            elif stripped.startswith("platform_notes:"):
                existing_notes = stripped.split(":", 1)[1].strip().strip('"').strip("'")
        else:
            break

    # Determine best version to record
    version_to_record = clean_version
    if version_to_record.lower() in ("latest", "none", "unknown"):
        if existing_version.lower() not in ("latest", "none", "unknown"):
            version_to_record = existing_version

    # Compute new merged notes
    merged_notes = merge_platform_notes(
        existing_notes=existing_notes,
        mode=mode,
        engine=engine,
        version=version_to_record,
        test_date=test_date,
    )

    # Second pass: replace header lines
    for line in lines:
        if in_header and line.startswith("#"):
            stripped = line[1:].strip()
            if stripped.startswith("status:"):
                updated_lines.append('# status: "tested"')
                status_found = True
            elif stripped.startswith("last_tested_version:"):
                updated_lines.append(f'# last_tested_version: "{version_to_record}"')
                version_found = True
            elif stripped.startswith("platform_notes:"):
                updated_lines.append(f'# platform_notes: "{merged_notes}"')
                notes_found = True
            else:
                updated_lines.append(line)
        else:
            in_header = False
            updated_lines.append(line)

    if not status_found or not version_found or not notes_found:
        # Prepend missing headers
        header_lines = [
            '# status: "tested"',
            f'# last_tested_version: "{version_to_record}"',
            f'# platform_notes: "{merged_notes}"',
            '# breaking_changes: "None"',
        ]
        return "\n".join(header_lines) + "\n" + content

    return "\n".join(updated_lines) + "\n"
