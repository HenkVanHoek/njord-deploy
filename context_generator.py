"""
NjordDeploy Context Generator

Aggregates codebase, generates manifests, checks RTX 3060 VRAM limits,
validates YAML password quoting, and enforces architectural UI mapping.

License:
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import re
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent
OUT_FILE = "llm_context.txt"
MANIFEST_FILE = "included_files.txt"
OUTPUT_PATH = PROJECT_ROOT / OUT_FILE
MANIFEST_PATH = PROJECT_ROOT / MANIFEST_FILE

# RTX 3060 Safety Limits (12GB VRAM)
SAFE_TOKENS = 32768
HARD_TOKENS = 90000

# UI Mapping: Logic controllers linked to templates
UI_MAP = {
    "configurator_app": "src/web/static/js/app.js",
    "editor_app": "src/web/static/js/editor_app.js",
}

# Comprehensive exclusions to maintain VRAM health
IGNORE_DIRS = {
    ".venv",
    "venv",
    "env",
    ".env",
    ".git",
    "__pycache__",
    "node_modules",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".pytest_cache",
    "playwright-report",
    "test-results",
    "vendor",
    "lib",
    "fonts",
    "tests",
    "component_templates",
    ".github",
}
EXTENSIONS = {".py", ".html", ".js", ".css", ".yml", ".mf"}


def validate_yaml(content, file_name):
    """Checks for unquoted secrets in YAML files."""
    pattern = r"(password|secret|key):\s*([^\s\"'].*)"
    matches = re.findall(pattern, content, re.IGNORECASE)
    if matches:
        print(f"SECURITY ALERT: Unquoted secret in {file_name}")
        for k, v in matches:
            print(f"  -> {k}: {v} (Must use double quotes)")


def get_valid_files():
    """Scans project, pruning bloat and self-references."""
    found = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            # Skip self and minified bloat
            if file in [OUT_FILE, MANIFEST_FILE] or ".min." in file:
                continue
            if any(file.endswith(ext) for ext in EXTENSIONS):
                found.append(os.path.relpath(os.path.join(root, file), PROJECT_ROOT))
    return found


def run_generator():
    """Assembles context with architectural awareness and VRAM guards."""
    base_files = get_valid_files()

    # Architectural Mapping Logic
    extra = {
        ctrl
        for key, ctrl in UI_MAP.items()
        if any(key in f for f in base_files) and (PROJECT_ROOT / ctrl).exists()
    }

    all_f = sorted(list(set(base_files) | extra))
    file_stats = {}

    header = (
        "MASTER INSTRUCTIONS FOR PISELFHOSTING EXPERT\n"
        "===========================================\n"
        "1. YAML passwords must use double quotes.\n"
        "2. Python line length must not exceed 88 characters.\n"
        "3. UI structure is managed in app.js or editor_app.js.\n"
        "4. Use 4-space indentation for all code blocks.\n\n"
    )

    full_content = header
    for path in all_f:
        full_content += f"\n--- FILE: {path} ---\n"
        try:
            with open(PROJECT_ROOT / path, "r", encoding="utf-8") as f:
                data = f.read()
                file_stats[path] = len(data)
                if path.endswith(".yml"):
                    validate_yaml(data, path)
                full_content += data
        except Exception as e:
            full_content += f"Read Error: {e}\n"

    # VRAM Metrics
    tokens = len(full_content) // 4
    print(f"\n--- VRAM Analysis: {tokens} tokens ---")

    # Bloat Analysis
    top_5 = sorted(file_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    print("Largest Files:")
    for i, (p, s) in enumerate(top_5, 1):
        print(f" {i}. {p} ({s // 1024} KB)")

    # Write Context
    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        out.write(full_content)

    # Write Manifest
    with open(MANIFEST_PATH, "w", encoding="utf-8") as man:
        status = "SAFE" if tokens < SAFE_TOKENS else "WATCH"
        if tokens > HARD_TOKENS:
            status = "CRITICAL"
        man.write(f"Tokens: {tokens} | VRAM Status: {status}\n" + "=" * 30 + "\n")
        man.writelines(f"{f}\n" for f in all_f)

    print(f"\nSuccessfully generated {OUT_FILE} and {MANIFEST_FILE}")


if __name__ == "__main__":
    run_generator()
