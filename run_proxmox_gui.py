# run_proxmox_gui.py
"""
Entrypoint for launching the NjordDeploy Proxmox Test Suite Web UI.

Launches the Flask testing GUI on port 5050 (or PROXMOX_GUI_PORT environment
variable) using Waitress and opens the default browser automatically.
"""

import logging
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

# Ensure local workspace src is at the head of sys.path
_src_dir = str(Path(__file__).resolve().parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from waitress import serve  # noqa: E402

from scripts.proxmox_gui import create_app  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("NjordDeployProxmoxGUI")


def is_port_in_use(host: str, port: int) -> bool:
    """Checks if the specified host and TCP port are already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        check_host = "127.0.0.1" if host == "0.0.0.0" else host  # nosec B104
        return s.connect_ex((check_host, port)) == 0


def open_browser(url: str):
    """Opens the default system browser to the specified URL."""
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PROXMOX_GUI_PORT", 5050))
    host = os.environ.get("PROXMOX_GUI_HOST", "0.0.0.0")  # nosec B104

    url_host = "localhost" if host == "0.0.0.0" else host  # nosec B104
    url = f"http://{url_host}:{port}"

    if is_port_in_use(host, port):
        logger.info(
            f"NjordDeploy Proxmox Test GUI is already running on {url}. "
            "Opening existing instance in browser..."
        )
        if not os.environ.get("NO_BROWSER"):
            open_browser(url)
        sys.exit(0)

    app = create_app()

    logger.info(f"Starting NjordDeploy Proxmox Test GUI via Waitress WSGI on {url}")

    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, open_browser, args=[url]).start()

    try:
        serve(app, host=host, port=port, threads=16)
    except OSError as err:
        if "already in use" in str(err).lower() or getattr(err, "errno", None) in (
            98,
            10048,
        ):
            logger.info(
                f"Port {port} is already in use. "
                "Opening existing instance in browser..."
            )
            if not os.environ.get("NO_BROWSER"):
                open_browser(url)
            sys.exit(0)
        raise
