#!/usr/bin/env python3
# run_service.py

"""
Production 24/7 Persistent Self-Hosted Service Entrypoint for NjordDeploy.

Runs the NjordDeploy application suite (Flask Web UI, Configurator, Editor,
and Headless REST API) as a persistent daemon/service.
"""

import logging
import os
import signal
import socket
import sys
from pathlib import Path

# Ensure local workspace src is at the head of sys.path
_src_dir = str(Path(__file__).resolve().parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from configurator_app.app import create_app  # noqa: E402
from managers.ssh_manager import SSHManager  # noqa: E402
from utils.resource_utils import (  # noqa: E402
    get_app_data_dir,
    get_project_version,
    get_ssh_key_path,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("NjordDeployService")


def handle_shutdown_signal(signum, frame):
    """Graceful shutdown signal handler."""
    sig_name = signal.Signals(signum).name
    logger.info(
        f"Received termination signal ({sig_name}). Shutting down gracefully..."
    )
    sys.exit(0)


def is_port_in_use(host: str, port: int) -> bool:
    """Checks if the specified host and TCP port are already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        check_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host  # nosec B104
        return s.connect_ex((check_host, port)) == 0


def initialize_service_environment() -> tuple[Path, str]:
    """Ensures persistent storage directory and SSH key pair exist."""
    data_dir = get_app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    ssh_key_file = get_ssh_key_path()
    ssh_key_file.parent.mkdir(parents=True, exist_ok=True)

    # Initialize / verify SSH key
    ssh_mgr = SSHManager(
        hostname="localhost", username="local", password=""
    )  # nosec B106
    public_key_str = ssh_mgr.get_public_key_string()

    # Save public key file for easy access by operators / scripts
    pub_key_file = ssh_key_file.with_suffix(".pub")
    try:
        pub_key_file.write_text(public_key_str.strip() + "\n", encoding="utf-8")
        pub_key_file.chmod(0o644)
    except Exception as ex:
        logger.debug(f"Could not write .pub file: {ex}")

    return data_dir, public_key_str


def main():
    """Main service entrypoint."""
    os.environ.setdefault("NJORD_SERVER_MODE", "true")

    # Register signal handlers for graceful shutdown (SIGTERM & SIGINT)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    # CLI action delegation if flags are passed
    cli_flags = {
        "--deploy",
        "--inspect",
        "--backup",
        "--restore",
        "--list-backups",
        "--scan-stacks",
        "--example-config",
        "--cli",
    }
    if any(arg in cli_flags for arg in sys.argv[1:]):
        from cli.runner import main as cli_main

        filtered_args = [a for a in sys.argv[1:] if a != "--cli"]
        sys.exit(cli_main(filtered_args))

    host = os.environ.get("NJORD_HOST") or os.environ.get(
        "CONFIGURATOR_HOST", "0.0.0.0"  # nosec B104
    )
    port = int(
        os.environ.get("NJORD_PORT") or os.environ.get("CONFIGURATOR_PORT", 5001)
    )
    threads = int(os.environ.get("NJORD_THREADS", 8))
    wsgi_server = os.environ.get("WSGI_SERVER", "waitress").lower()

    version = get_project_version()
    data_dir, pub_key = initialize_service_environment()

    bind_all = "0.0.0.0"  # nosec B104
    url_display = f"http://{'127.0.0.1' if host == bind_all else host}:{port}"
    pub_key_snippet = pub_key[:40]

    logger.info("=" * 65)
    logger.info(f"  NjordDeploy 24/7 Persistent Daemon (v{version})")
    logger.info("=" * 65)
    logger.info("  Mode:           Self-Hosted 24/7 Service Daemon")
    logger.info(f"  Listening on:   {host}:{port} ({url_display})")
    logger.info(f"  Data Directory: {data_dir}")
    logger.info(f"  SSH Key Path:   {get_ssh_key_path()}")
    logger.info(
        f"  SSH Public Key: {pub_key_snippet}... "
        f"(saved to {get_ssh_key_path().with_suffix('.pub')})"
    )
    logger.info(f"  Healthcheck:    {url_display}/api/health")
    logger.info(f"  OpenAPI / UI:   {url_display}/api/docs")
    logger.info(f"  WSGI Server:    {wsgi_server.capitalize()}")
    logger.info("=" * 65)

    if is_port_in_use(host, port):
        logger.warning(
            f"Port {port} is already in use by another process. "
            f"Attempting to bind anyway or check running instance..."
        )

    app = create_app()

    if wsgi_server == "gunicorn" and os.name != "nt":
        try:
            from gunicorn.app.base import BaseApplication  # type: ignore

            class StandaloneGunicornApplication(BaseApplication):
                def __init__(self, flask_application, options=None):
                    self.options = options or {}
                    self.application = flask_application
                    super().__init__()

                def load_config(self):
                    config = {
                        key: value
                        for key, value in self.options.items()
                        if key in self.cfg.settings and value is not None
                    }
                    for key, value in config.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            gunicorn_options = {
                "bind": f"{host}:{port}",
                "workers": int(os.environ.get("GUNICORN_WORKERS", 2)),
                "threads": threads,
                "timeout": 120,
                "accesslog": "-",
                "errorlog": "-",
            }
            logger.info("Starting Gunicorn WSGI server...")
            StandaloneGunicornApplication(app, gunicorn_options).run()
            return
        except ImportError:
            logger.info("Gunicorn not installed; falling back to Waitress WSGI server.")

    # Default production WSGI server: Waitress
    from waitress import serve

    try:
        serve(app, host=host, port=port, threads=threads)
    except OSError as err:
        logger.critical(f"Fatal error starting WSGI server on {host}:{port} - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
