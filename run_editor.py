# run_editor.py

"""
Production entrypoint for running the NjordDeploy Editor application.

Launches the Flask editor application using the Waitress WSGI server
on port 5000 (or EDITOR_PORT environment variable).
"""

import logging
import os
import threading
import webbrowser

from waitress import serve

from src.editor_app.app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NjordDeployEditor")


def open_browser(url: str):
    """Opens the default system browser to the specified URL."""
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("EDITOR_PORT", 5000))
    host = os.environ.get("EDITOR_HOST", "0.0.0.0")  # nosec B104

    url_host = "localhost" if host == "0.0.0.0" else host  # nosec B104
    url = f"http://{url_host}:{port}"

    logger.info(f"Starting NjordDeploy Editor via Waitress WSGI server " f"on {url}")

    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, open_browser, args=[url]).start()

    serve(app, host=host, port=port, threads=6)
