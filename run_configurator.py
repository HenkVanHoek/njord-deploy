# run_configurator.py

"""
Production entrypoint for running the NjordDeploy Configurator application.

Launches the Flask configurator application using the Waitress WSGI server
on port 5001 (or CONFIGURATOR_PORT environment variable).
"""

import logging
import os

from waitress import serve

from src.configurator_app.app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NjordDeployConfigurator")

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("CONFIGURATOR_PORT", 5001))
    host = os.environ.get("CONFIGURATOR_HOST", "0.0.0.0")  # nosec B104

    logger.info(
        f"Starting NjordDeploy Configurator via Waitress WSGI server "
        f"on http://{host}:{port}"
    )
    serve(app, host=host, port=port, threads=6)
