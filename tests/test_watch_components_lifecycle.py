# tests/test_watch_components_lifecycle.py
"""Unit tests for NjordDeploy Upstream Lifecycle Watcher and Pre-Release Filtering."""

import json
from unittest.mock import MagicMock, patch

from scripts.watch_components_lifecycle import (
    check_github_is_prerelease,
    is_newer_version,
    is_prerelease_content,
    is_prerelease_or_invalid,
    parse_latest_release,
    reject_candidate,
)

SAMPLE_RADARR_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>tag:github.com,2008:Repository/77323220/v7.0.0.10815</id>
    <updated>2026-10-25T17:57:55Z</updated>
    <link rel="alternate" type="text/html"
          href="https://github.com/Radarr/Radarr/releases/tag/v7.0.0.10815"/>
    <title>7.0.0.10815</title>
    <content type="html">&lt;p&gt;&lt;em&gt;To receive further Pre-Release updates
    for a non-docker installation, please change the branch to
    &lt;strong&gt;develop&lt;/strong&gt;.&lt;/em&gt;&lt;/p&gt;</content>
  </entry>
  <entry>
    <id>tag:github.com,2008:Repository/77323220/v6.4.4.10685</id>
    <updated>2026-09-16T18:13:40Z</updated>
    <link rel="alternate" type="text/html"
          href="https://github.com/Radarr/Radarr/releases/tag/v6.4.4.10685"/>
    <title>6.4.4.10685</title>
    <content type="html">&lt;p&gt;Stable maintenance release.&lt;/p&gt;</content>
  </entry>
</feed>
"""


def test_is_prerelease_content():
    """Verifies that prerelease content notices in release notes are recognized."""
    prerelease_note = (
        "<p><em>To receive further Pre-Release updates for a non-docker "
        "installation, please change the branch to <strong>develop</strong>.</em></p>"
    )
    stable_note = "<p>Standard GA release notes with bugfixes.</p>"

    assert is_prerelease_content(prerelease_note) is True
    assert is_prerelease_content("This is a pre-release test build.") is True
    assert is_prerelease_content(stable_note) is False
    assert is_prerelease_content("") is False


def test_is_prerelease_or_invalid():
    """Verifies tag pattern filtering for pre-releases and invalid strings."""
    assert is_prerelease_or_invalid("v1.2.0-rc1") is True
    assert is_prerelease_or_invalid("v2.0.0-beta2") is True
    assert is_prerelease_or_invalid("v3.0.0-alpha") is True
    assert is_prerelease_or_invalid("nightly") is True
    assert is_prerelease_or_invalid("master") is True
    assert is_prerelease_or_invalid("v1.2.3") is False
    assert is_prerelease_or_invalid("6.4.4.10685") is False


@patch("urllib.request.urlopen")
def test_check_github_is_prerelease_true(mock_urlopen):
    """Verifies that GitHub API release endpoint flags pre-releases."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"prerelease": True}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    result = check_github_is_prerelease("Radarr/Radarr", "7.0.0.10815")
    assert result is True


@patch("urllib.request.urlopen")
def test_check_github_is_prerelease_false(mock_urlopen):
    """Verifies that stable GA releases return False."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"prerelease": False}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    result = check_github_is_prerelease("Radarr/Radarr", "6.4.4.10685")
    assert result is False


def test_check_github_is_prerelease_empty():
    """Verifies graceful handling when no repo or tag is provided."""
    assert check_github_is_prerelease(None, "1.0.0") is None
    assert check_github_is_prerelease("repo", "") is None


def test_parse_latest_release_skips_prerelease_content():
    """Verifies that parse_latest_release skips pre-release entries and picks GA."""
    latest = parse_latest_release(SAMPLE_RADARR_ATOM_XML)
    assert latest is not None
    # 7.0.0.10815 must be skipped due to pre-release notice in content
    assert latest["version"] == "6.4.4.10685"
    assert latest["raw_tag"] == "v6.4.4.10685"


def test_is_newer_version_progression():
    """Verifies version comparisons with semver progression."""
    assert is_newer_version("6.4.4.10685", "7.0.0.10815") is True
    assert is_newer_version("6.4.4.10685", "6.4.4.10685") is False
    assert is_newer_version("6.4.4.10685", "6.3.0.10514") is False
    assert is_newer_version("6.4.4.10685", "7.0.0-rc1") is False


@patch("scripts.watch_components_lifecycle.sync_to_sysopswatch")
def test_reject_candidate(mock_sync, tmp_path):
    """Verifies rejecting candidate cleans staging and populates ignored_versions."""
    catalog_file = tmp_path / "components_metadata.json"
    initial_data = {
        "components": {
            "radarr": {
                "staging": {
                    "candidate_version": "7.0.0.10815",
                    "status": "needs_review",
                    "last_test_error": "rate limited",
                    "ignored_versions": [],
                }
            }
        }
    }
    catalog_file.write_text(json.dumps(initial_data), encoding="utf-8")

    with patch(
        "scripts.watch_components_lifecycle.CATALOG_METADATA_PATH",
        catalog_file,
    ):
        reject_candidate("radarr")

    updated = json.loads(catalog_file.read_text(encoding="utf-8"))
    radarr_staging = updated["components"]["radarr"]["staging"]
    assert radarr_staging["candidate_version"] is None
    assert radarr_staging["status"] == "idle"
    assert radarr_staging["last_test_error"] is None
    assert "7.0.0.10815" in radarr_staging["ignored_versions"]
