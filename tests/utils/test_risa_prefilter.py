# tests/utils/test_risa_prefilter.py
"""Unit tests for RISA Token Filtering Engine."""

from utils.risa_prefilter import (
    classify_update_risk,
    extract_signal_lines,
    filter_changelog_for_risa,
    is_target_inspection_file,
)


def test_is_target_inspection_file():
    assert is_target_inspection_file("docker-compose.yml") is True
    assert is_target_inspection_file("/opt/app/compose.yaml") is True
    assert is_target_inspection_file("Dockerfile") is True
    assert is_target_inspection_file(".env.example") is True
    assert is_target_inspection_file("docs/MIGRATION.md") is True
    # Application sources should be ignored to prevent token explosions
    assert is_target_inspection_file("src/main.py") is False
    assert is_target_inspection_file("frontend/bundle.js") is False
    assert is_target_inspection_file("server.go") is False


def test_extract_signal_lines():
    sample_text = (
        "## Release Notes v2.0.0\n"
        "This release brings general speedups.\n"
        "Small bugfixes in CSS.\n"
        "BREAKING CHANGE: The DATABASE_URL format has changed.\n"
        "Please update your env variables.\n"
        "Added cool new button in navigation.\n"
    )
    signals = extract_signal_lines(sample_text, max_context_lines=1)
    joined = "\n".join(signals)
    assert "BREAKING CHANGE" in joined
    assert "Small bugfixes in CSS" in joined  # 1 line context
    assert "DATABASE_URL" in joined


def test_classify_update_risk_red_major():
    res = classify_update_risk("v1.5.2", "v2.0.0", signal_lines=[])
    assert res["risk_level"] == "RED"
    assert res["is_major"] is True
    assert res["requires_gatekeeper"] is True


def test_classify_update_risk_red_db_migration():
    res = classify_update_risk(
        "v1.5.2", "v1.5.3", signal_lines=[], has_db_migration=True
    )
    assert res["risk_level"] == "RED"
    assert res["requires_gatekeeper"] is True


def test_classify_update_risk_orange_env():
    signals = ["ENV_VAR: Added OIDC_ISSUER_URL for SSO."]
    res = classify_update_risk("v1.5.2", "v1.5.3", signal_lines=signals)
    assert res["risk_level"] == "ORANGE"
    assert res["requires_gatekeeper"] is False


def test_classify_update_risk_green():
    signals = []
    res = classify_update_risk("v1.5.2", "v1.5.3", signal_lines=signals)
    assert res["risk_level"] == "GREEN"
    assert res["requires_gatekeeper"] is False


def test_filter_changelog_for_risa():
    raw = (
        "Fixes:\n"
        "- Fixed alignment on mobile\n"
        "- Fixed typo in README\n"
        "- MIGRATION: Table users now has column status NOT NULL\n"
        "- Performance tweak in cache\n"
    )
    filtered = filter_changelog_for_risa(raw, max_tokens_approx=50)
    assert "MIGRATION" in filtered
    assert "Fixed typo in README" in filtered or "Table users" in filtered
