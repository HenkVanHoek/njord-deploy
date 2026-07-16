"""Automated UI tests for the deployed Uptime Kuma component."""

import json
import re
import socket
from pathlib import Path

import pytest

try:
    from playwright.sync_api import Page, expect

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = any  # type: ignore
    expect = None

pytestmark = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE, reason="Playwright is not installed"
)


def is_port_open(ip: str, port: int) -> bool:
    """Helper to check if a specific port is open on the target IP."""
    try:
        with socket.create_connection((ip, port), timeout=2):
            return True
    except OSError:
        return False


def get_deployed_component_ip(component_id: str) -> str:
    """Retrieves the deployed component's dynamic IP from test results."""
    results_path = Path(__file__).resolve().parent.parent / "proxmox_results.json"
    if not results_path.exists():
        raise FileNotFoundError(
            f"Test results not found at {results_path}. "
            "Please run the proxmox test runner first."
        )

    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    for record in results:
        if record.get("component_id") == component_id:
            if record.get("status") == "success" and record.get("ip"):
                return str(record["ip"])

    raise ValueError(
        f"Component {component_id} was not deployed successfully in "
        "the last test run."
    )


def test_uptime_kuma_ui(page: Page) -> None:
    """Verifies that Uptime Kuma's setup/login screen loads correctly."""
    try:
        ip = get_deployed_component_ip("uptime-kuma")
    except Exception as e:
        pytest.skip(f"Skipping UI test: {e}")

    if not is_port_open(ip, 3001):
        pytest.skip(f"Skipping UI test: Port 3001 on {ip} is not reachable.")

    url = f"http://{ip}:3001"

    # Navigate to the Uptime Kuma setup screen
    page.goto(url, timeout=10000)

    # Check for Uptime Kuma in page title
    expect(page).to_have_title(re.compile("Uptime Kuma", re.IGNORECASE))

    # Verify that language selector or primary setup controls are visible
    expect(page.locator("select")).to_be_visible()
