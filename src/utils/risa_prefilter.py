# src/utils/risa_prefilter.py
"""RISA Token Filtering Engine.

Implements token hygiene and targeted file/diff inspection for upstream
changelogs and release notes according to FUMS Spec section 4.1.
Filters and prioritizes signal words (BREAKING, DEPRECATED, DATABASE,
MIGRATION, ENV_VAR, SCHEMA) to avoid LLM context-window overflow.
"""

import re
from typing import Any, Dict, List, Optional

# Keywords that indicate operational risk and breaking changes
SIGNAL_KEYWORDS = [
    "BREAKING",
    "BREAKING CHANGE",
    "DEPRECATED",
    "DEPRECATION",
    "DATABASE",
    "MIGRATION",
    "ENV_VAR",
    "ENVIRONMENT VARIABLE",
    "SCHEMA",
    "REQUIRES MANUAL",
    "ACTION REQUIRED",
    "POSTGRES",
    "MARIADB",
    "MYSQL",
]

# Targeted inspection file patterns - ignore raw application source code
ALLOWED_INSPECTION_FILES = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "dockerfile",
    ".env",
    ".env.example",
    "migration.md",
    "migrations.md",
    "changelog.md",
    "release.md",
    "releases.md",
)


def is_target_inspection_file(filepath: str) -> bool:
    """Checks if a file path qualifies for targeted RISA inspection.

    Excludes raw application source code to prevent token bloat.
    """
    clean = filepath.strip().lower()
    basename = clean.split("/")[-1]
    return basename in ALLOWED_INSPECTION_FILES or basename.endswith(
        (".env.example", "migration.md", "migrations.md")
    )


def extract_signal_lines(
    text: str,
    max_context_lines: int = 2,
) -> List[str]:
    """Extracts lines containing high-priority signals along with context lines.

    Preserves token budget while extracting breaking change notices.
    """
    if not text:
        return []

    lines = text.splitlines()
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in SIGNAL_KEYWORDS) + r")\b",
        re.IGNORECASE,
    )

    matched_indices = set()
    for idx, line in enumerate(lines):
        if pattern.search(line):
            start = max(0, idx - max_context_lines)
            end = min(len(lines), idx + max_context_lines + 1)
            for i in range(start, end):
                matched_indices.add(i)

    sorted_indices = sorted(matched_indices)
    extracted: List[str] = []
    prev_idx: Optional[int] = None

    for idx in sorted_indices:
        if prev_idx is not None and idx > prev_idx + 1:
            extracted.append("---")
        extracted.append(lines[idx])
        prev_idx = idx

    return extracted


def classify_update_risk(
    old_version: str,
    new_version: str,
    signal_lines: List[str],
    has_db_migration: bool = False,
    has_compose_diff: bool = False,
) -> Dict[str, Any]:
    """Classifies risk level into GREEN (Routine), ORANGE (Env/Config),

    or RED (Major/Breaking/DB Migration).
    """
    reasons: List[str] = []

    # Parse versions if semantic
    old_parts = re.findall(r"\d+", old_version)
    new_parts = re.findall(r"\d+", new_version)

    is_major_bump = False
    if old_parts and new_parts:
        old_major = int(old_parts[0])
        new_major = int(new_parts[0])
        if new_major > old_major:
            is_major_bump = True
            reasons.append(
                f"Major version bump detected ({old_version} -> {new_version})."
            )

    if has_db_migration:
        reasons.append("Database migration or schema mutation detected.")

    joined_signals = " ".join(signal_lines).upper()

    has_breaking = "BREAKING" in joined_signals or "ACTION REQUIRED" in joined_signals
    if has_breaking:
        reasons.append("Breaking change keyword present in upstream release notes.")

    has_env_changes = (
        "ENV_VAR" in joined_signals
        or "ENVIRONMENT VARIABLE" in joined_signals
        or "DEPRECATED" in joined_signals
    )

    if is_major_bump or has_db_migration or has_breaking:
        risk_level = "RED"
    elif has_env_changes or has_compose_diff:
        risk_level = "ORANGE"
        if has_env_changes:
            reasons.append("Environment variable or deprecation notices detected.")
        if has_compose_diff:
            reasons.append("Docker Compose specification diff detected.")
    else:
        risk_level = "GREEN"
        reasons.append("Routine patch/minor release without breaking changes.")

    return {
        "risk_level": risk_level,
        "is_major": is_major_bump,
        "has_db_migration": has_db_migration,
        "reasons": reasons,
        "requires_gatekeeper": risk_level == "RED",
    }


def filter_changelog_for_risa(
    raw_changelog: str,
    max_tokens_approx: int = 1500,
) -> str:
    """Filters raw changelog to prioritize high-risk lines within token limit.

    Approximate token count uses 4 characters per token heuristic.
    """
    if not raw_changelog:
        return ""

    signal_lines = extract_signal_lines(raw_changelog)
    filtered_text = "\n".join(signal_lines)

    max_chars = max_tokens_approx * 4
    if len(filtered_text) > max_chars:
        suffix = "\n... [TRUNCATED FOR TOKEN HYGIENE]"
        filtered_text = filtered_text[:max_chars] + suffix

    return filtered_text
