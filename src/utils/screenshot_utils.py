"""Utility module for capturing Web UI screenshots using Playwright."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("NjordDeploy.Screenshot")


def capture_service_screenshot(
    url: str,
    output_path: Path,
    timeout_ms: int = 15000,
    viewport_width: int = 1280,
    viewport_height: int = 800,
) -> Optional[Path]:
    """Captures a screenshot of a web service UI using headless Chromium.

    Args:
        url: The web URL to navigate to (e.g. http://10.99.0.199:8080/).
        output_path: Destination path for the saved PNG screenshot.
        timeout_ms: Maximum navigation and load wait time in milliseconds.
        viewport_width: Viewport width in pixels.
        viewport_height: Viewport height in pixels.

    Returns:
        Path to the saved screenshot file if successful, None otherwise.
    """
    if not url or not url.strip():
        logger.warning("Empty URL provided for screenshot capture.")
        return None

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        logger.warning(
            "Playwright is not installed or importable. Skipping screenshot capture."
        )
        return None

    try:
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright_instance:
            browser = playwright_instance.chromium.launch(headless=True)
            context = browser.new_context(
                ignore_https_errors=True,
                viewport={"width": viewport_width, "height": viewport_height},
            )
            page = context.new_page()

            logger.info("Navigating to %s for screenshot capture...", url)
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            # Allow brief settle period for client-side rendering / animations
            page.wait_for_timeout(1500)

            page.screenshot(path=str(output_path), full_page=False)
            context.close()
            browser.close()

        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info("Successfully captured screenshot to: %s", output_path)
            return output_path

        logger.warning("Screenshot file was not generated: %s", output_path)
        return None

    except Exception as exc:
        logger.warning(
            "Failed to capture screenshot for %s: %s", url, exc, exc_info=False
        )
        return None
