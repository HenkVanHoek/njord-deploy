# scripts/proxmox_gui.py
"""
Interactive Web Application for configuring and running NjordDeploy component
integration tests on Proxmox VE (supporting Docker & Podman).
"""

import json
import logging
import os
import queue
import signal
import subprocess  # nosec B404
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, make_response, render_template, request


def get_project_root() -> Path:
    """Returns base project root, supporting PyInstaller frozen bundles."""
    if getattr(sys, "frozen", False):
        base_path_str: Optional[str] = getattr(sys, "_MEIPASS", None)
        if base_path_str:
            return Path(base_path_str)
    return Path(__file__).resolve().parent.parent


# Ensure we can import from project root and src directory
project_root = get_project_root()
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from managers.component_manager import ComponentManager  # noqa: E402
from scripts.proxmox_test_runner import get_template_status  # noqa: E402
from utils.ai_failure_diagnoser import (  # noqa: E402
    AIFailureDiagnoser,
    apply_suggested_template,
)
from utils.container_engine import get_configured_engine  # noqa: E402
from utils.failed_components import load_untestable_components  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
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
                # noinspection PyBroadException
                try:
                    self.log_queue.get_nowait()
                except queue.Empty:
                    break

        runner_script = project_root / "scripts" / "proxmox_test_runner.py"
        python_bin = "python3" if getattr(sys, "frozen", False) else sys.executable
        cmd = [
            python_bin,
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
            # noinspection PyBroadException
            try:
                env = os.environ.copy()
                # noinspection SpellCheckingInspection
                env["PYTHONUNBUFFERED"] = "1"
                env["CONTAINER_ENGINE"] = engine

                running_proc = subprocess.Popen(  # nosec B603
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                    cwd=str(project_root),
                    start_new_session=True,
                )
                self.process = running_proc

                self.log_queue.put(
                    {
                        "type": "status",
                        "status": "running",
                        "engine": engine,
                        "mode": mode,
                    }
                )

                if running_proc.stdout is not None:
                    for line in iter(running_proc.stdout.readline, ""):
                        if not line:
                            break
                        if "\r" in line:
                            parts = [p.strip() for p in line.split("\r") if p.strip()]
                            clean_line = next(reversed(parts), "")
                        else:
                            clean_line = line.rstrip("\r\n")

                        if clean_line:
                            self.log_queue.put({"type": "log", "content": clean_line})
                            self._inspect_log_line(clean_line, _engine=engine)

                running_proc.wait()
            except Exception as exc:
                logger.error(f"Error running test process: {exc}")
                self.log_queue.put({"type": "log", "content": f"ERROR: {exc}"})
            finally:
                exit_code = 0
                if self.process is not None:
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

    def _inspect_log_line(self, line: str, _engine: str = ""):
        """Analyzes stdout lines to emit structured events to the UI."""
        now_ts = time.strftime("%Y-%m-%d %H:%M:%S")

        # Detect component start: "Testing component: <id> (Engine: <e>, Mode: <m>)"
        if "Testing component:" in line:
            _, comp_part = line.split("Testing component:", 1)
            comp_words = comp_part.strip().split()
            comp_id = next(iter(comp_words), "unknown").strip("() ")
            self.current_component = comp_id

            current_engine = self.current_engine
            current_mode = self.current_mode
            if "Engine:" in line:
                # noinspection PyBroadException
                try:
                    _, eng_part = line.split("Engine:", 1)
                    eng_token, *_ = eng_part.split(",")
                    current_engine = eng_token.strip("() ").upper()
                except Exception:  # nosec B110
                    pass
            if "Mode:" in line:
                # noinspection PyBroadException
                try:
                    _, mode_part = line.split("Mode:", 1)
                    mode_token, *_ = mode_part.split(",")
                    current_mode = mode_token.strip("() ").upper()
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
            _, comp_part = line.split("Component", 1)
            comp_words = comp_part.strip().split()
            comp_id = next(iter(comp_words), "unknown")
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
            err_msg = line.strip()
            if ":" in line:
                _, err_msg = line.split(":", 1)
                err_msg = err_msg.strip()
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
                        "error_message": err_msg,
                    },
                }
            )

        # Detect skipped: "⏭️ Skipping <comp_id>: ..."
        elif "⏭️ Skipping" in line:
            _, skip_part = line.split("Skipping", 1)
            skip_words = skip_part.strip().split()
            comp_id = next(iter(skip_words), "unknown").strip(":")
            self.log_queue.put(
                {
                    "type": "record",
                    "record": {
                        "timestamp": now_ts,
                        "component_id": comp_id,
                        "mode": self.current_mode,
                        "engine": self.current_engine,
                        "status": "skipped",
                        "deployment": "skipped",
                        "running": False,
                        "error_message": line.strip(),
                    },
                }
            )

    def stop_test(self) -> bool:
        """Terminates active test runner subprocess and all child processes."""
        with self.lock:
            proc = self.process
            if not self.is_running or proc is None:
                return False
            # noinspection PyBroadException
            try:
                pgid: Optional[int] = None
                if proc.pid is not None:
                    # noinspection PyBroadException
                    try:
                        found_pgid: int = os.getpgid(proc.pid)
                        if found_pgid > 1 and found_pgid != os.getpgrp():
                            pgid = found_pgid
                            os.killpg(found_pgid, signal.SIGTERM)
                        else:
                            proc.terminate()
                    except Exception:
                        proc.terminate()

                def _force_kill(p: subprocess.Popen, kill_pgid: Optional[int]):
                    time.sleep(1.5)
                    if isinstance(kill_pgid, int) and kill_pgid > 1:
                        target_pgid: int = kill_pgid
                        # noinspection PyBroadException
                        try:
                            if target_pgid != os.getpgrp():
                                os.killpg(target_pgid, signal.SIGKILL)
                        except Exception:  # nosec B110
                            pass
                    # noinspection PyBroadException
                    try:
                        if p.poll() is None:
                            p.kill()
                    except Exception:  # nosec B110
                        pass

                threading.Thread(
                    target=_force_kill, args=(proc, pgid), daemon=True
                ).start()

                self.log_queue.put(
                    {
                        "type": "log",
                        "content": (
                            "⚠️ Test session aborted by user. "
                            "Terminating all test processes..."
                        ),
                    }
                )
                return True
            except Exception as exc:
                logger.error(f"Failed to terminate process group: {exc}")
                return False


def create_app() -> Flask:
    """Creates and configures the Flask application."""
    load_dotenv(project_root / ".env")

    templates_dir = project_root / "scripts" / "templates"
    if not templates_dir.exists():
        templates_dir = project_root / "templates"
    static_dir = project_root / "scripts" / "static"
    if not static_dir.exists():
        static_dir = project_root / "static"

    app = Flask(
        __name__,
        template_folder=str(templates_dir),
        static_folder=str(static_dir),
    )

    runner_mgr = TestRunnerManager()

    @app.route("/")
    def index() -> Response:
        resp = make_response(
            render_template("proxmox_gui.html", cache_bust=int(time.time()))
        )
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.route("/api/config", methods=["GET"])
    def get_config() -> Response:
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
    def get_components() -> Response:
        """Returns all components with template status and metadata."""
        metadata_path = project_root / "config" / "components_metadata.json"
        templates_path = project_root / "component_templates"
        untestable_doc = project_root / "docs" / "FAILED_COMPONENTS.md"
        untestable_map = load_untestable_components(untestable_doc)

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
            is_untestable = cid in untestable_map
            untestable_reason = untestable_map.get(cid, {}).get("reason", "")
            enriched.append(
                {
                    "id": cid,
                    "name": comp.get("name") or cid,
                    "category": comp.get("category"),
                    "description": comp.get("description", ""),
                    "has_ui": bool(comp.get("has_ui", False)),
                    "status": status,
                    "version": comp.get("component_version", "latest"),
                    "is_untestable": is_untestable,
                    "untestable_reason": untestable_reason,
                }
            )

        # Sort alphabetically by name
        enriched.sort(key=lambda x: x["name"].lower())
        return jsonify(enriched)

    @app.route("/api/run", methods=["POST"])
    def run_tests() -> Union[Response, Tuple[Response, int]]:
        """Starts a test run with selected options."""
        raw_data = request.get_json()
        data = raw_data if isinstance(raw_data, dict) else {}
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
    def stop_tests() -> Response:
        """Stops active test run."""
        stopped = runner_mgr.stop_test()
        return jsonify({"success": stopped})

    @app.route("/api/status", methods=["GET"])
    def get_status() -> Response:
        """Returns current runner status."""
        return jsonify(
            {
                "is_running": runner_mgr.is_running,
                "current_component": runner_mgr.current_component,
            }
        )

    @app.route("/api/stream", methods=["GET"])
    def stream_logs() -> Response:
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
    def get_report() -> Response:
        """Reads latest Markdown report."""
        report_path = project_root / "docs" / "PROXMOX_TESTS.md"
        if report_path.exists():
            content = report_path.read_text(encoding="utf-8")
            return jsonify({"report": content})
        return jsonify({"report": ""})

    @app.route("/api/results", methods=["GET"])
    def get_results() -> Response:
        """Returns cumulative test results history."""
        results_file = project_root / "tests" / "proxmox_results.json"
        if results_file.exists():
            # noinspection PyBroadException
            try:
                with open(results_file, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                    if isinstance(history_data, list):
                        return jsonify(history_data)
            except Exception as exc:
                logger.warning(f"Failed to read results file: {exc}")
        return jsonify([])

    @app.route("/api/results/clear", methods=["POST"])
    def clear_results() -> Union[Response, Tuple[Response, int]]:
        """Clears test results history."""
        results_file = project_root / "tests" / "proxmox_results.json"
        # noinspection PyBroadException
        try:
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump([], f)
                f.write("\n")
            runner_mgr.results_history = []
            return jsonify({"success": True})
        except Exception as exc:
            logger.error(f"Failed to clear results file: {exc}")
            return (
                jsonify({"success": False, "error": "Failed to clear results file."}),
                500,
            )

    @app.route("/api/ai/status", methods=["GET"])
    def ai_status() -> Response:
        """Checks if AI failure diagnoser is configured and ready."""
        diagnoser = AIFailureDiagnoser()
        return jsonify(
            {
                "configured": diagnoser.is_configured(),
                "provider": diagnoser.provider,
                "model": diagnoser.engine.model,
            }
        )

    @app.route("/api/ai/diagnose", methods=["POST"])
    def ai_diagnose() -> Union[Response, Tuple[Response, int]]:
        """Diagnoses a single component failure or batch of failures with Gemini."""
        raw_payload = request.get_json()
        payload = raw_payload if isinstance(raw_payload, dict) else {}
        diagnoser = AIFailureDiagnoser()

        if not diagnoser.is_configured():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            f"AI provider '{diagnoser.provider}' is not configured. "
                            "Please set GEMINI_API_KEY in your .env file."
                        ),
                    }
                ),
                400,
            )

        is_batch = payload.get("batch", False)

        # noinspection PyBroadException
        try:
            if is_batch:
                records = payload.get("records")
                if not records:
                    results_file = project_root / "tests" / "proxmox_results.json"
                    if results_file.exists():
                        all_res = json.loads(results_file.read_text(encoding="utf-8"))
                        if isinstance(all_res, list):
                            records = [
                                r for r in all_res if r.get("status") == "failed"
                            ]
                        else:
                            records = []
                    else:
                        records = []

                if not records:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "No failed test records found to analyze.",
                            }
                        ),
                        400,
                    )

                diagnosis = diagnoser.diagnose_batch_failures(failed_records=records)
                return jsonify(
                    {
                        "success": True,
                        "batch": True,
                        "diagnosis": diagnosis,
                    }
                )

            else:
                raw_record = payload.get("record")
                record = raw_record if isinstance(raw_record, dict) else {}
                raw_comp_id = payload.get("component_id") or record.get("component_id")
                if not isinstance(raw_comp_id, str) or not raw_comp_id.strip():
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "component_id is required",
                            }
                        ),
                        400,
                    )
                from werkzeug.utils import secure_filename

                comp_id = secure_filename(raw_comp_id.strip())
                tmpl_dir = (project_root / "component_templates" / comp_id).resolve()
                templates_root = (project_root / "component_templates").resolve()
                if not tmpl_dir.is_relative_to(templates_root):
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Invalid component ID path.",
                            }
                        ),
                        400,
                    )

                tmpl_file = tmpl_dir / "docker-compose.template.yml"
                tmpl_content = (
                    tmpl_file.read_text(encoding="utf-8") if tmpl_file.exists() else ""
                )
                logs_snippet = payload.get("logs", "")

                results_file = project_root / "tests" / "proxmox_results.json"
                history_records = []
                if results_file.exists():
                    # noinspection PyBroadException
                    try:
                        raw_hist = json.loads(results_file.read_text(encoding="utf-8"))
                        if isinstance(raw_hist, list):
                            history_records = raw_hist
                    except Exception:  # nosec B110
                        pass

                diagnosis = diagnoser.diagnose_single_failure(
                    test_record=record
                    or {
                        "component_id": comp_id,
                        "error_message": payload.get("error_message", ""),
                    },
                    template_content=tmpl_content,
                    container_logs=logs_snippet,
                    history_records=history_records,
                )
                return jsonify(
                    {
                        "success": True,
                        "batch": False,
                        "diagnosis": diagnosis,
                    }
                )

        except Exception as exc:
            logger.error(f"AI diagnosis error: {exc}", exc_info=True)
            return (
                jsonify({"success": False, "error": "AI diagnosis failed."}),
                500,
            )

    @app.route("/api/ai/apply-patch", methods=["POST"])
    def ai_apply_patch() -> Union[Response, Tuple[Response, int]]:
        """Applies a suggested AI template patch to the component template."""
        raw_payload = request.get_json()
        payload = raw_payload if isinstance(raw_payload, dict) else {}
        comp_id = payload.get("component_id")
        template_content = payload.get("template_content")

        if not isinstance(comp_id, str) or not isinstance(template_content, str):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "component_id and template_content are required.",
                    }
                ),
                400,
            )

        success = apply_suggested_template(
            component_id=comp_id,
            new_template_content=template_content,
            project_root=project_root,
        )
        return jsonify({"success": success})

    @app.route("/api/ai/apply-matrix-constraint", methods=["POST"])
    def ai_apply_matrix_constraint() -> Union[Response, Tuple[Response, int]]:
        """Applies a suggested matrix constraint (modes, engines, notes) to metadata."""
        raw_payload = request.get_json()
        payload = raw_payload if isinstance(raw_payload, dict) else {}
        comp_id = payload.get("component_id")
        modes = payload.get("modes")
        engines = payload.get("engines")
        notes = payload.get("notes")

        if not isinstance(comp_id, str) or not comp_id.strip():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "component_id is required.",
                    }
                ),
                400,
            )

        try:
            component_manager = ComponentManager(
                templates_path=str(project_root / "component_templates"),
                metadata_file_path=str(
                    project_root / "config" / "components_metadata.json"
                ),
            )
            success = component_manager.update_component_matrix_constraint(
                component_id=comp_id.strip(),
                modes=modes if isinstance(modes, list) else None,
                engines=engines if isinstance(engines, list) else None,
                notes=str(notes) if notes is not None else None,
            )
            return jsonify({"success": success, "component_id": comp_id})
        except Exception as exc:
            logger.error(f"Failed to apply matrix constraint: {exc}", exc_info=True)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to apply matrix constraint.",
                    }
                ),
                500,
            )

    return app


if __name__ == "__main__":
    app_instance = create_app()
    port = int(os.environ.get("PROXMOX_GUI_PORT", "5050"))
    host = str(os.environ.get("PROXMOX_GUI_HOST", "0.0.0.0"))  # nosec B104

    print(f"Starting NjordDeploy Proxmox Test GUI on http://localhost:{port}")
    app_instance.run(host=host, port=port, debug=False)
