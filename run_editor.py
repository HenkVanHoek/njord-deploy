# run_editor.py

"""
Production entrypoint for running the NjordDeploy Editor application.

Launches the Flask editor application using the Waitress WSGI server
on port 5000 (or EDITOR_PORT environment variable).
"""

import logging
import os

from waitress import serve

from src.editor_app.app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NjordDeployEditor")

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("EDITOR_PORT", 5000))
    host = os.environ.get("EDITOR_HOST", "0.0.0.0")  # nosec B104

    logger.info(
        f"Starting NjordDeploy Editor via Waitress WSGI server "
        f"on http://{host}:{port}"
    )
    serve(app, host=host, port=port, threads=6)
