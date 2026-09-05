# tests/test_screenshot_utils.py
"""Unit tests for the Playwright-based service screenshot utility."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.screenshot_utils import capture_service_screenshot

# noinspection PyBroadException
try:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as _p:
        _b = _p.chromium.launch(headless=True)
        _b.close()
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False


def test_capture_service_screenshot_empty_url(tmp_path: Path):
    """Verifies that an empty or whitespace URL immediately returns None."""
    dest = tmp_path / "test.png"
    assert capture_service_screenshot("", dest) is None
    assert capture_service_screenshot("   ", dest) is None
    assert not dest.exists()


def test_capture_service_screenshot_import_error(tmp_path: Path):
    """Verifies graceful handling when playwright is not installed."""
    dest = tmp_path / "test.png"
    with patch.dict(sys.modules, {"playwright.sync_api": None}):
        with patch(
            "builtins.__import__",
            side_effect=ImportError("No module named 'playwright'"),
        ):
            # Should not raise exception
            res = capture_service_screenshot("http://127.0.0.1:8080", dest)
            assert res is None


@pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="Playwright Chromium browser is not installed or available",
)
def test_capture_service_screenshot_navigation_failure(tmp_path: Path):
    """Verifies that network/connection failure returns None without crashing."""
    dest = tmp_path / "test.png"
    # Port 1 is reserved and guaranteed not to connect
    res = capture_service_screenshot("http://127.0.0.1:1", dest, timeout_ms=1000)
    assert res is None
    assert not dest.exists()


@pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="Playwright Chromium browser is not installed or available",
)
def test_capture_service_screenshot_success(tmp_path: Path):
    """Verifies successful capture of a local webpage."""
    dest = tmp_path / "subfolder" / "success.png"
    # Create a minimal local HTML file and load it via file:// URI
    sample_html = tmp_path / "index.html"
    sample_html.write_text("<html><body><h1>NjordDeploy Test</h1></body></html>")
    file_url = f"file://{sample_html.resolve()}"

    res = capture_service_screenshot(file_url, dest, timeout_ms=10000)
    assert res is not None
    assert dest.exists()
    assert dest.stat().st_size > 0
    # PNG signature check: \x89PNG\r\n\x1a\n
    header = dest.read_bytes()[:8]
    assert header == b"\x89PNG\r\n\x1a\n"
