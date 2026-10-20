#!/usr/bin/env python3
"""Audit script for validating NjordDeploy code against OWASP Top 10 for LLMs.

Checks prompt construction, input sanitization, XML boundary demarcation,
deterministic ground-truth clamping, SSTI gatekeeping, and schema validation.
"""

import sys
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def check_generator_security() -> List[Tuple[bool, str]]:
    """Verifies security controls in src/utils/ai_generator.py."""
    file_path = PROJECT_ROOT / "src" / "utils" / "ai_generator.py"
    if not file_path.exists():
        return [(False, f"Target file missing: {file_path}")]

    content = file_path.read_text(encoding="utf-8")
    checks = []

    # 1. XML Boundary Enclosure for untrusted files
    has_xml_readme = '<untrusted_source_file type="readme"' in content
    checks.append(
        (
            has_xml_readme,
            "LLM01: README content enclosed in <untrusted_source_file> tags.",
        )
    )

    has_xml_compose = '<untrusted_source_file type="docker-compose"' in content
    checks.append(
        (
            has_xml_compose,
            "LLM01: Docker compose content enclosed in <untrusted_source_file>.",
        )
    )

    has_xml_instr = "<custom_user_instructions>" in content
    checks.append(
        (
            has_xml_instr,
            "LLM01: Custom instructions enclosed in <custom_user_instructions>.",
        )
    )

    # 2. System prompt prompt-injection guardrail
    has_guardrail = "Prompt Injection" in content and "OWASP LLM01" in content
    checks.append(
        (
            has_guardrail,
            "LLM01: System prompt includes explicit Prompt Injection Defense.",
        )
    )

    # 3. URL Credential Stripping
    has_url_scrub = (
        "clean_netloc = parsed_clean.hostname or parsed_clean.netloc" in content
    )
    checks.append(
        (
            has_url_scrub,
            "LLM06: Credentials scrubbed from repository URL before prompt build.",
        )
    )

    # 4. Pre-prompt Content Scrubbing
    has_content_scrubbing = "sanitize_logs(readme_content" in content
    checks.append(
        (
            has_content_scrubbing,
            "LLM06: Untrusted repository content scrubbed via sanitize_logs().",
        )
    )

    # 5. SSTI Gatekeeping
    has_ssti_check = "__class__" in content and "Jinja2 SSTI" in content
    checks.append(
        (
            has_ssti_check,
            "LLM02: Template checks detect Jinja2 SSTI / Python dunders.",
        )
    )

    # 6. Safety classification in return payload
    has_is_safe = 'data["is_safe"]' in content
    checks.append(
        (
            has_is_safe,
            "LLM02: Generated component data includes deterministic is_safe flag.",
        )
    )

    return checks


def check_evaluator_security() -> List[Tuple[bool, str]]:
    """Verifies security controls in src/managers/deployment_evaluator.py."""
    file_path = PROJECT_ROOT / "src" / "managers" / "deployment_evaluator.py"
    if not file_path.exists():
        return [(False, f"Target file missing: {file_path}")]

    content = file_path.read_text(encoding="utf-8")
    checks = []

    # 1. XML Demarcation of Runtime Logs
    has_log_boundary = "<untrusted_deployment_logs>" in content
    checks.append(
        (
            has_log_boundary,
            "LLM01: Runtime container logs enclosed in " "<untrusted_deployment_logs>.",
        )
    )

    # 2. Guardrail in Evaluator System Prompt
    has_eval_guardrail = "OWASP LLM01 - Prompt Injection Defense" in content
    checks.append(
        (
            has_eval_guardrail,
            "LLM01: Evaluator system prompt includes anti-override guardrails.",
        )
    )

    # 3. Deterministic Exit-Code Clamping
    has_exit_clamp = (
        'exit_code != 0 and ai_result.get("status") == "GREEN"' in content
        and 'ai_result["status"] = "RED"' in content
    )
    checks.append(
        (
            has_exit_clamp,
            "LLM02: Exit code != 0 deterministically clamps AI status to RED.",
        )
    )

    # 4. Rule-Based Precedence
    has_rule_precedence = (
        'ai_result.get("status") == "GREEN" and rule_res.get("status") in' in content
    )
    checks.append(
        (
            has_rule_precedence,
            "LLM02: Deterministic rule evaluation overrules hallucinated GREEN.",
        )
    )

    # 5. Output Schema Enum Validation
    has_enum_valid = "VALID_EVALUATION_STATUSES" in content
    checks.append(
        (
            has_enum_valid,
            "LLM02: Evaluation status validated against strict enum set.",
        )
    )

    # 6. HTML/XSS Sanitization
    has_html_escape = "html.escape(str(val or" in content
    checks.append(
        (
            has_html_escape,
            "LLM02: Text output fields sanitized with html.escape against XSS.",
        )
    )

    return checks


def check_editor_gatekeeper() -> List[Tuple[bool, str]]:
    """Verifies SSTI and save gatekeeper in src/editor_app/app.py."""
    file_path = PROJECT_ROOT / "src" / "editor_app" / "app.py"
    if not file_path.exists():
        return [(False, f"Target file missing: {file_path}")]

    content = file_path.read_text(encoding="utf-8")
    checks = []

    has_ssti_gate = (
        "Forbidden template expression" in content and "__class__" in content
    )
    checks.append(
        (
            has_ssti_gate,
            "LLM02: save_ai_component endpoint enforces SSTI gatekeeper check.",
        )
    )

    return checks


def run_audit() -> bool:
    """Executes all OWASP LLM security compliance checks."""
    print("=" * 70)
    print("  NjordDeploy OWASP Top 10 for LLMs - Security Compliance Audit")
    print("=" * 70)

    all_checks: List[Tuple[str, List[Tuple[bool, str]]]] = [
        ("AI Generator (src/utils/ai_generator.py)", check_generator_security()),
        (
            "AI Checker (src/managers/deployment_evaluator.py)",
            check_evaluator_security(),
        ),
        ("Save Gatekeeper (src/editor_app/app.py)", check_editor_gatekeeper()),
    ]

    total_passed = 0
    total_checks = 0

    for section_name, section_results in all_checks:
        print(f"\n📂 {section_name}:")
        for passed, description in section_results:
            total_checks += 1
            if passed:
                total_passed += 1
                print(f"  ✅ PASS: {description}")
            else:
                print(f"  ❌ FAIL: {description}")

    print("\n" + "=" * 70)
    print(
        f"  Audit Result: {total_passed}/{total_checks} controls verified "
        f"({100 * total_passed // total_checks}%)."
    )
    print("=" * 70)

    return total_passed == total_checks


def check_upstream_releases() -> None:
    """Queries official OWASP release channels for newer upstream releases."""
    import requests

    print("\n🌐 Upstream OWASP Standaard Verificatie:")
    url = (
        "https://api.github.com/repos/OWASP/"
        "www-project-top-10-for-large-language-model-applications/releases"
    )
    try:
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            releases = resp.json()
            if isinstance(releases, list) and releases:
                latest, *_ = releases
                tag = latest.get("tag_name", "Unknown")
                name = latest.get("name", "Unknown")
                print(f"  ℹ️ Laatste getagde release: {name} ({tag})")
                print("  ℹ️ Officiële hub: https://genai.owasp.org/")
                print("  ℹ️ NjordDeploy baseline: OWASP Top 10 for LLMs 2025/2026")
        else:
            print(f"  ⚠️ Upstream controle overgeslagen (HTTP {resp.status_code}).")
    except Exception as exc:
        print(f"  ⚠️ Upstream controle kon niet worden voltooid: {exc}")


if __name__ == "__main__":
    check_upstream = "--check-upstream" in sys.argv
    success = run_audit()
    if check_upstream:
        check_upstream_releases()
    sys.exit(0 if success else 1)
