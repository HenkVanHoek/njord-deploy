# scripts/proxmox_gui.py
"""
Interactive Web Application for configuring and running NjordDeploy component
integration tests on Proxmox VE (supporting Docker & Podman).
"""

import json
import logging
import os
import queue
import subprocess  # nosec B404
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, make_response, render_template, request

# Ensure we can import from the 'src' root directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.component_manager import ComponentManager  # noqa: E402
from scripts.proxmox_test_runner import get_template_status  # noqa: E402
from utils.container_engine import get_configured_engine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("proxmox_gui")


class TestRunnerManager:
    """Manages the background test runner subprocess and log streaming."""

    __test__ = False

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.log_queue: queue.Queue = queue.Queue()
        self.is_running: bool = False
        self.current_component: Optional[str] = None
        self.current_engine: str = "DOCKER"
        self.current_mode: str = "LXC"
        self.current_run_failures: int = 0
        self.current_run_passed: int = 0
        self.results_history: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def start_test(
        self,
        components: List[str],
        engine: str = "docker",
        mode: str = "lxc",
        node: str = "pve",
        template_id: str = "902",
    ) -> bool:
        """Launches proxmox_test_runner.py in a managed background process."""
        with self.lock:
            if self.is_running:
                logger.warning("Test runner is already executing.")
                return False

            self.is_running = True
            self.results_history = []
            self.current_run_failures = 0
            self.current_run_passed = 0
            self.current_engine = engine.upper()
            self.current_mode = mode.upper()
            # Clear log queue
            while not self.log_queue.empty():
                try:
                    self.log_queue.get_nowait()
                except queue.Empty:
                    break

        runner_script = project_root / "scripts" / "proxmox_test_runner.py"
        cmd = [
            sys.executable,
            "-u",  # Unbuffered output
            str(runner_script),
            "--mode",
            mode,
            "--engine",
            engine,
            "--node",
            node,
        ]

        if mode == "vm" and template_id:
            cmd.extend(["--template-id", template_id])

        if components:
            cmd.extend(["--components", ",".join(components)])

        logger.info(f"Launching test process: {' '.join(cmd)}")

        def run_worker():
            try:
                # noinspection PyBroadException
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                env["CONTAINER_ENGINE"] = engine

                self.process = subprocess.Popen(  # nosec B603
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                    cwd=str(project_root),
                )

                self.log_queue.put(
                    {
                        "type": "status",
                        "status": "running",
                        "engine": engine,
                        "mode": mode,
                    }
                )

                if self.process.stdout:
                    for line in iter(self.process.stdout.readline, ""):
                        if not line:
                            break
                        if "\r" in line:
                            parts = [p.strip() for p in line.split("\r") if p.strip()]
                            clean_line = parts[-1] if parts else ""
                        else:
                            clean_line = line.rstrip("\r\n")

                        if clean_line:
                            self.log_queue.put({"type": "log", "content": clean_line})
                            self._inspect_log_line(clean_line, engine)

                self.process.wait()
            except Exception as exc:
                logger.error(f"Error running test process: {exc}")
                self.log_queue.put({"type": "log", "content": f"ERROR: {exc}"})
            finally:
                exit_code = 0
                if self.process:
                    exit_code = self.process.returncode or 0

                with self.lock:
                    self.is_running = False
                    self.process = None

                failed_count = self.current_run_failures
                if exit_code != 0 and failed_count == 0:
                    failed_count = 1
                passed_count = self.current_run_passed

                self.log_queue.put(
                    {
                        "type": "status",
                        "status": "completed",
                        "failed_count": failed_count,
                        "passed_count": passed_count,
                    }
                )

        worker_thread = threading.Thread(target=run_worker, daemon=True)
        worker_thread.start()
        return True

    def _inspect_log_line(self, line: str, engine: str):
        """Analyzes stdout lines to emit structured events to the UI."""
        now_ts = time.strftime("%Y-%m-%d %H:%M:%S")

        # Detect component start: "Testing component: <id> (Engine: <e>, Mode: <m>)"
        if "Testing component:" in line:
            parts = line.split("Testing component:", 1)
            comp_part = parts[1].strip()
            comp_id = comp_part.split()[0].strip("() ")
            self.current_component = comp_id

            current_engine = self.current_engine
            current_mode = self.current_mode
            if "Engine:" in line:
                try:
                    current_engine = (
                        line.split("Engine:")[1]
                        .split(",")[0]
                        .split(")")[0]
                        .strip()
                        .upper()
                    )
                except Exception:  # nosec B110
                    pass
            if "Mode:" in line:
                try:
                    current_mode = (
                        line.split("Mode:")[1]
                        .split(",")[0]
                        .split(")")[0]
                        .strip()
                        .upper()
                    )
                except Exception:  # nosec B110
                    pass

            self.current_engine = current_engine
            self.current_mode = current_mode

            self.log_queue.put(
                {
                    "type": "record",
                    "record": {
                        "timestamp": now_ts,
                        "component_id": comp_id,
                        "mode": current_mode,
                        "engine": current_engine,
                        "status": "running",
                        "deployment": "In Progress",
                        "running": True,
                    },
                }
            )

        # Detect component success: "✅ Component adguard-home verified successfully!"
        elif "verified successfully!" in line and "Component" in line:
            self.current_run_passed += 1
            parts = line.split("Component", 1)
            comp_id = parts[1].split()[0] if len(parts) > 1 else "unknown"
            self.log_queue.put(
                {
                    "type": "record",
                    "record": {
                        "timestamp": now_ts,
                        "component_id": comp_id,
                        "mode": self.current_mode,
                        "engine": self.current_engine,
                        "status": "success",
                        "deployment": "success",
                        "running": True,
                    },
                }
            )

        # Detect failure: "❌ Component verification failed" / "❌ Error during test of"
        elif (
            "❌ Component verification failed" in line
            or "❌ Error during test of" in line
        ):
            self.current_run_failures += 1
            comp_id = self.current_component or "unknown"
            self.log_queue.put(
                {
                    "type": "record",
                    "record": {
                        "timestamp": now_ts,
                        "component_id": comp_id,
                        "mode": self.current_mode,
                        "engine": self.current_engine,
                        "status": "failed",
                        "deployment": "failed",
                        "running": False,
                    },
                }
            )

    def stop_test(self) -> bool:
        """Terminates active test runner subprocess."""
        with self.lock:
            if not self.is_running or not self.process:
                return False
            try:
                self.process.terminate()
                self.log_queue.put(
                    {
                        "type": "log",
                        "content": "⚠️ Test execution terminated by user.",
                    }
                )
                return True
            except Exception as exc:
                logger.error(f"Failed to terminate process: {exc}")
                return False


def create_app() -> Flask:
    """Creates and configures the Flask application."""
    load_dotenv(project_root / ".env")

    templates_dir = project_root / "scripts" / "templates"
    static_dir = project_root / "scripts" / "static"

    app = Flask(
        __name__,
        template_folder=str(templates_dir),
        static_folder=str(static_dir),
    )

    runner_mgr = TestRunnerManager()

    @app.route("/")
    def index():
        resp = make_response(
            render_template("proxmox_gui.html", cache_bust=int(time.time()))
        )
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.route("/api/config", methods=["GET"])
    def get_config():
        """Returns Proxmox settings from .env."""
        default_engine = get_configured_engine()
        return jsonify(
            {
                "node": os.getenv("PROXMOX_NODE", "pve"),
                "template_id": os.getenv("PROXMOX_TEMPLATE_ID", "902"),
                "engine": default_engine,
                "mode": "lxc",
            }
        )

    @app.route("/api/components", methods=["GET"])
    def get_components():
        """Returns all components with template status and metadata."""
        metadata_path = project_root / "config" / "components_metadata.json"
        templates_path = project_root / "component_templates"

        comp_mgr = ComponentManager(
            metadata_file_path=str(metadata_path),
            templates_path=str(templates_path),
        )
        components = comp_mgr.get_all_components()

        enriched = []
        for comp in components:
            cid = comp.get("id", "")
            if not cid:
                continue

            status = get_template_status(templates_path, cid)
            enriched.append(
                {
                    "id": cid,
                    "name": comp.get("name") or cid,
                    "category": comp.get("category"),
                    "description": comp.get("description", ""),
                    "has_ui": bool(comp.get("has_ui", False)),
                    "status": status,
                    "version": comp.get("component_version", "latest"),
                }
            )

        # Sort alphabetically by name
        enriched.sort(key=lambda x: x["name"].lower())
        return jsonify(enriched)

    @app.route("/api/run", methods=["POST"])
    def run_tests():
        """Starts a test run with selected options."""
        data = request.get_json() or {}
        components = data.get("components", [])
        engine = data.get("engine", "docker").lower()
        mode = data.get("mode", "lxc").lower()
        node = data.get("node", "pve")
        template_id = data.get("template_id", "902")

        if engine not in ["docker", "podman", "both", "all"]:
            engine = "docker"
        if mode not in ["lxc", "vm", "both", "all"]:
            mode = "lxc"

        success = runner_mgr.start_test(
            components=components,
            engine=engine,
            mode=mode,
            node=node,
            template_id=template_id,
        )
        if success:
            return jsonify({"success": True})
        return (
            jsonify(
                {"success": False, "error": "A test run is already currently active."}
            ),
            409,
        )

    @app.route("/api/stop", methods=["POST"])
    def stop_tests():
        """Stops active test run."""
        stopped = runner_mgr.stop_test()
        return jsonify({"success": stopped})

    @app.route("/api/status", methods=["GET"])
    def get_status():
        """Returns current runner status."""
        return jsonify(
            {
                "is_running": runner_mgr.is_running,
                "current_component": runner_mgr.current_component,
            }
        )

    @app.route("/api/stream", methods=["GET"])
    def stream_logs():
        """Server-Sent Events endpoint for real-time log output."""

        def event_stream():
            while True:
                try:
                    item = runner_mgr.log_queue.get(timeout=1.0)
                    yield f"data: {json.dumps(item)}\n\n"
                except queue.Empty:
                    # Heartbeat comment to prevent client timeout
                    yield ": heartbeat\n\n"

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.route("/api/report", methods=["GET"])
    def get_report():
        """Reads latest markdown report."""
        report_path = project_root / "docs" / "PROXMOX_TESTS.md"
        if report_path.exists():
            content = report_path.read_text(encoding="utf-8")
            return jsonify({"report": content})
        return jsonify({"report": ""})

    @app.route("/api/results", methods=["GET"])
    def get_results():
        """Returns cumulative test results history."""
        results_file = project_root / "tests" / "proxmox_results.json"
        if results_file.exists():
            try:
                with open(results_file, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                    if isinstance(history_data, list):
                        return jsonify(history_data)
            except Exception as e:
                logger.warning(f"Failed to read results file: {e}")
        return jsonify([])

    @app.route("/api/results/clear", methods=["POST"])
    def clear_results():
        """Clears test results history."""
        results_file = project_root / "tests" / "proxmox_results.json"
        try:
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump([], f)
                f.write("\n")
            runner_mgr.results_history = []
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Failed to clear results file: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    return app


if __name__ == "__main__":
    app_instance = create_app()
    port = int(os.environ.get("PROXMOX_GUI_PORT", 5050))
    host = os.environ.get("PROXMOX_GUI_HOST", "0.0.0.0")  # nosec B104

    print(f"Starting NjordDeploy Proxmox Test GUI on http://localhost:{port}")
    app_instance.run(host=host, port=port, debug=False)
