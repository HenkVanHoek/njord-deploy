# run_editor.py

"""
Production entrypoint for running the NjordDeploy Editor application.

Launches the Flask editor application using the Waitress WSGI server
on port 5000 (or EDITOR_PORT environment variable).
"""

import logging
import os
import socket
import sys
import threading
import webbrowser

from waitress import serve

from src.editor_app.app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NjordDeployEditor")


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
    port = int(os.environ.get("EDITOR_PORT", 5000))
    host = os.environ.get("EDITOR_HOST", "0.0.0.0")  # nosec B104

    url_host = "localhost" if host == "0.0.0.0" else host  # nosec B104
    url = f"http://{url_host}:{port}"

    if is_port_in_use(host, port):
        logger.info(
            f"NjordDeploy Editor is already running on {url}. "
            f"Opening existing instance in browser..."
        )
        if not os.environ.get("NO_BROWSER"):
            open_browser(url)
        sys.exit(0)

    app = create_app()

    logger.info(f"Starting NjordDeploy Editor via Waitress WSGI server on {url}")

    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, open_browser, args=[url]).start()

    try:
        serve(app, host=host, port=port, threads=6)
    except OSError as err:
        if "already in use" in str(err).lower() or getattr(err, "errno", None) in (
            98,
            10048,
        ):
            logger.info(
                f"Port {port} is already in use. "
                f"Opening existing instance in browser..."
            )
            if not os.environ.get("NO_BROWSER"):
                open_browser(url)
            sys.exit(0)
        raise
