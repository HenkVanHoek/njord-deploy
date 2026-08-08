# run_configurator.py

"""
Production entrypoint for running the NjordDeploy Configurator application.

Launches the Flask configurator application using the Waitress WSGI server
on port 5001 (or CONFIGURATOR_PORT environment variable).
"""

import logging
import os
import threading
import webbrowser

from waitress import serve

from src.configurator_app.app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NjordDeployConfigurator")


def open_browser(url: str):
    """Opens the default system browser to the specified URL."""
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("CONFIGURATOR_PORT", 5001))
    host = os.environ.get("CONFIGURATOR_HOST", "0.0.0.0")  # nosec B104

    url_host = "localhost" if host == "0.0.0.0" else host  # nosec B104
    url = f"http://{url_host}:{port}"

    logger.info(
        f"Starting NjordDeploy Configurator via Waitress WSGI server " f"on {url}"
    )

    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, open_browser, args=[url]).start()

    serve(app, host=host, port=port, threads=6)
