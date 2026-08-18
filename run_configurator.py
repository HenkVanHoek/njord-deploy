# run_configurator.py

"""
Production entrypoint for running the NjordDeploy Configurator application.

Launches the Flask configurator application using the Waitress WSGI server
on port 5001 (or CONFIGURATOR_PORT environment variable).
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

from configurator_app.app import create_app  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NjordDeployConfigurator")


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
    cli_flags = {
        "--deploy",
        "--inspect",
        "--backup",
        "--restore",
        "--list-backups",
        "--scan-stacks",
        "--example-config",
        "--cli",
        "--help",
        "-h",
    }
    # If any CLI action argument was passed, run the headless CLI runner directly
    if any(arg in cli_flags for arg in sys.argv[1:]):
        from cli.runner import main as cli_main

        filtered_args = [a for a in sys.argv[1:] if a != "--cli"]
        sys.exit(cli_main(filtered_args))

    port = int(os.environ.get("CONFIGURATOR_PORT", 5001))
    host = os.environ.get("CONFIGURATOR_HOST", "0.0.0.0")  # nosec B104

    url_host = "localhost" if host == "0.0.0.0" else host  # nosec B104
    url = f"http://{url_host}:{port}"

    if is_port_in_use(host, port):
        logger.info(
            f"NjordDeploy Configurator is already running on {url}. "
            f"Opening existing instance in browser..."
        )
        if not os.environ.get("NO_BROWSER"):
            open_browser(url)
        sys.exit(0)

    app = create_app()

    logger.info(f"Starting NjordDeploy Configurator via Waitress WSGI server on {url}")

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
