# File: scripts/check_secrets.py
# Part of the NjordDeploy project.

# Copyright (C) 2026 Henk van Hoek
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see https://www.gnu.org/licenses.

import os
import re
import sys

# Common patterns for keys/secrets
GEMINI_KEY_RE = re.compile(r"AIzaSy[A-Za-z0-9_-]{35}")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----")

# Regex to detect assignments to sensitive variable names
# E.g. GEMINI_API_KEY = "xyz" or export PASSWORD="abc"
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?:export\s+)?([a-zA-Z0-9_\-\.]+)\s*=\s*(['\"])(.*?)\2", re.IGNORECASE
)

# SENSITIVE_KEYWORDS to check in variable names
SENSITIVE_KEYWORDS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
}

# Placeholders that are allowed
PLACEHOLDERS = {
    "placeholder",
    "example",
    "changeme",
    "change_me",
    "insert_here",
    "your_",
    "jouw_",
    "default",
    "none",
    "null",
    "true",
    "false",
    "replace_me",
    "<replace",
    "bpt-registration-token",
    "token-here",
    "password-here",
}


def is_placeholder(value):
    val_lower = value.lower().strip()
    if not val_lower:
        return True
    # Allow environment variable references, variable interpolation, or tag brackets
    if (
        val_lower.startswith("$")
        or val_lower.startswith("{")
        or val_lower.endswith("}")
        or (val_lower.startswith("<") and val_lower.endswith(">"))
    ):
        return True
    for p in PLACEHOLDERS:
        if p in val_lower:
            return True
    return False


def check_file(filepath):
    # Skip binary files, git directory, etc.
    if not os.path.isfile(filepath):
        return []

    filename = os.path.basename(filepath)
    filepath_lower = filepath.lower()

    # Check if this is a test file or a documentation/JS file
    is_test_file = "tests/" in filepath_lower or "test_" in filename

    # Only run assignment checks on code and config files, not JS, MD, HTML, CSS, etc.
    run_assignment_check = not is_test_file and any(
        filepath_lower.endswith(ext)
        for ext in [
            ".py",
            ".sh",
            ".env",
            ".envrc",
            ".yaml",
            ".yml",
            ".json",
            ".conf",
            ".ini",
        ]
    )

    # Read file content safely
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return []

    findings = []
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("#") or stripped.startswith("//"):
            # Still scan comments for Gemini/private keys, but not assignments
            if GEMINI_KEY_RE.search(line):
                findings.append((line_num, "Leaked Gemini API Key detected in comment"))
            if not is_test_file and PRIVATE_KEY_RE.search(line):
                findings.append(
                    (line_num, "Leaked Private Key block detected in comment")
                )
            continue

        # 1. Check for Gemini API Keys
        if GEMINI_KEY_RE.search(line):
            findings.append((line_num, "Leaked Gemini API Key detected"))
            continue

        # 2. Check for Private Keys
        if not is_test_file and PRIVATE_KEY_RE.search(line):
            findings.append((line_num, "Leaked Private Key block detected"))
            continue

        # 3. Check for assignments
        if run_assignment_check:
            match = SECRET_ASSIGNMENT_RE.search(line)
            if match:
                var_name, _, var_value = match.groups()
                var_name_lower = var_name.lower()

                # Skip JS DOM/UI assignments
                DOM_PROPERTIES = [
                    ".placeholder",
                    ".classname",
                    ".type",
                    ".value",
                    ".display",
                    ".id",
                    ".style",
                    ".src",
                ]
                if any(prop in var_name_lower for prop in DOM_PROPERTIES):
                    continue

                # Check if any sensitive keyword is in the variable name
                if any(kw in var_name_lower for kw in SENSITIVE_KEYWORDS):
                    if not is_placeholder(var_value):
                        findings.append(
                            (
                                line_num,
                                f"Potential hardcoded secret assigned to "
                                f"'{var_name}': '{var_value[:4]}...'",
                            )
                        )

    return findings


def main():
    files_to_check = sys.argv[1:]
    if not files_to_check:
        sys.exit(0)

    has_errors = False
    for filepath in files_to_check:
        # Avoid checking check_secrets.py or example files
        filename = os.path.basename(filepath)
        if filename == "check_secrets.py" or ".example" in filename:
            continue

        findings = check_file(filepath)
        if findings:
            has_errors = True
            print(f"[SECURITY CHECK FAILED] {filepath}:")
            for line_num, msg in findings:
                print(f"  Line {line_num}: {msg}")
            print()

    if has_errors:
        print(
            "Error: Staging credentials/secrets is forbidden by "
            "security-secrets-guard policy."
        )
        print(
            "Please remove the plaintext secret, use environment variables, "
            "and try again."
        )
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
