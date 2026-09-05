# scripts/proxmox_gui.py
"""
Interactive Web Application for configuring and running NjordDeploy component
integration tests on Proxmox VE (supporting Docker & Podman).
"""

import base64
import json
import logging
import os
import queue
import re
import signal
import subprocess  # nosec B404
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
)


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
from utils.security_utils import mask_passwords  # noqa: E402

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
        self.is_aborted: bool = False
        self.current_component: Optional[str] = None
        self.target_type: str = "components"
        self.current_engine: str = "DOCKER"
        self.current_mode: str = "LXC"
        self.current_ip: Optional[str] = None
        self.current_vmid: Optional[Union[str, int]] = None
        self.current_run_failures: int = 0
        self.current_run_passed: int = 0
        self.current_http_ok: Optional[bool] = None
        self.current_http_url: Optional[str] = None
        self.current_report_file: Optional[str] = None
        self.last_failed_key: Optional[str] = None
        self.results_history: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def start_test(
        self,
        target_type: str = "components",
        components: Optional[List[str]] = None,
        packages: Optional[List[str]] = None,
        engine: str = "docker",
        mode: str = "lxc",
        node: str = "pve",
        template_id: str = "902",
        skip_passed: bool = False,
    ) -> bool:
        """Launches test runner subprocess (components or packages) in background."""
        with self.lock:
            if self.is_running:
                logger.warning("Test runner is already executing.")
                return False

            self.is_running = True
            self.is_aborted = False
            self.results_history = []
            self.current_run_failures = 0
            self.current_run_passed = 0
            self.current_ip = None
            self.current_vmid = None
            self.current_http_ok = None
            self.current_http_url = None
            self.current_report_file = None
            self.last_failed_key = None
            self.current_engine = (
                "DOCKER" if engine in ("both", "all") else engine.upper()
            )
            self.current_mode = "LXC" if mode in ("both", "all") else mode.upper()
            self.target_type = target_type
            # Clear log queue
            while not self.log_queue.empty():
                # noinspection PyBroadException
                try:
                    self.log_queue.get_nowait()
                except queue.Empty:
                    break

        python_bin = "python3" if getattr(sys, "frozen", False) else sys.executable

        if target_type == "templates":
            runner_script = project_root / "scripts" / "maintain_proxmox_templates.py"
            target_choice = "all"
            if components and components[0] in (
                "all",
                "docker-vm",
                "docker-lxc",
                "podman-vm",
                "podman-lxc",
            ):
                target_choice = components[0]
            elif mode in ("vm", "lxc") and engine in ("docker", "podman"):
                target_choice = f"{engine}-{mode}"

            cmd = [
                python_bin,
                "-u",  # Unbuffered output
                str(runner_script),
                "--target",
                target_choice,
                "--node",
                node,
            ]
        # Determine effective template ID: for matrix runs across modes or engines,
        # ensure dynamic resolution across 911/912/913/914 by passing 902.
        eff_template = template_id
        if mode in ("both", "all") or engine in ("both", "all"):
            if not eff_template or eff_template in ("902", "911", "912", "913", "914"):
                eff_template = "902"

        if target_type == "packages":
            runner_script = project_root / "scripts" / "proxmox_package_test_runner.py"
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
            if eff_template:
                cmd.extend(["--template-id", eff_template])
            if packages:
                cmd.extend(["--packages", ",".join(packages)])
            if skip_passed:
                cmd.append("--skip-passed")
        else:
            runner_script = project_root / "scripts" / "proxmox_test_runner.py"
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
            if eff_template:
                cmd.extend(["--template-id", eff_template])
            if components:
                cmd.extend(["--components", ",".join(components)])
            if skip_passed:
                cmd.append("--skip-passed")

        logger.info(f"Launching test process ({target_type}): {' '.join(cmd)}")

        def run_worker():
            # noinspection PyBroadException
            try:
                load_dotenv(project_root / ".env", override=True)
                env = os.environ.copy()
                # noinspection SpellCheckingInspection
                env["PYTHONUNBUFFERED"] = "1"
                env["CONTAINER_ENGINE"] = engine
                test_ip = os.getenv("PROXMOX_TEST_IP", "10.99.0.199")
                bridge = os.getenv("PROXMOX_BRIDGE")
                if not bridge:
                    bridge = "vmbr1" if "10.99." in test_ip else "vmbr0"
                elif "10.99." in test_ip and bridge == "vmbr0":
                    bridge = "vmbr1"

                default_gw = "10.99.0.1" if "10.99." in test_ip else "192.168.178.1"
                test_gw = os.getenv("PROXMOX_GATEWAY")
                if not test_gw or ("10.99." in test_ip and "10.99." not in test_gw):
                    test_gw = default_gw

                env["PROXMOX_BRIDGE"] = bridge
                env["PROXMOX_TEST_IP"] = test_ip
                env["PROXMOX_GATEWAY"] = test_gw
                if os.getenv("PROXMOX_VLAN_TAG"):
                    env["PROXMOX_VLAN_TAG"] = os.getenv("PROXMOX_VLAN_TAG")

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
                            safe_line = mask_passwords(clean_line)
                            self.log_queue.put({"type": "log", "content": safe_line})
                            self._inspect_log_line(safe_line, _engine=engine)

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
                    self.is_aborted = False
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
        if self.is_aborted:
            return

        now_ts = time.strftime("%Y-%m-%d %H:%M:%S")

        # Extract IP and VMID from environment setup lines
        if "online at" in line:
            clean_str = line.rstrip(".")
            tokens = clean_str.split()
            for idx, tok in enumerate(tokens):
                if tok == "VM" and idx + 1 < len(tokens):
                    self.current_vmid = tokens[idx + 1]
                elif (
                    tok == "LXC" and idx + 1 < len(tokens) and tokens[idx + 1].isdigit()
                ):
                    self.current_vmid = tokens[idx + 1]
                elif tok == "at" and idx + 1 < len(tokens):
                    self.current_ip = tokens[idx + 1]

        # Extract environment mode & engine if logged
        if "Target Environment:" in line:
            # noinspection PyBroadException
            try:
                _, env_part = line.split("Target Environment:", 1)
                m_part, e_part = env_part.split("|", 1)
                self.current_mode = m_part.strip().upper()
                if "Engine:" in e_part:
                    _, eng_val = e_part.split("Engine:", 1)
                    self.current_engine = eng_val.strip().upper()
            except Exception:  # nosec B110
                pass

        # Extract HTTP UI URL
        if "Probing HTTP UI endpoint:" in line:
            # noinspection PyBroadException
            try:
                _, url_part = line.split("Probing HTTP UI endpoint:", 1)
                self.current_http_url = next(iter(url_part.strip().split()), None)
            except Exception:  # nosec B110
                pass
        elif "Probing HTTP UI for" in line and "at " in line:
            # noinspection PyBroadException
            try:
                _, url_part = line.split("at ", 1)
                self.current_http_url = next(iter(url_part.strip().split()), None)
            except Exception:  # nosec B110
                pass

        # Detect HTTP Probe status
        if (
            "HTTP Probe SUCCESS" in line
            or "HTTP Probe: 200" in line
            or "HTTP Probe: 301" in line
            or "HTTP Probe: 302" in line
            or "HTTP Probe: 401" in line
            or "HTTP Probe: 403" in line
            or "HTTP Probe: 404" in line
        ):
            self.current_http_ok = True
        elif "HTTP Probe FAILED" in line or "HTTP Probe failed after" in line:
            self.current_http_ok = False
        elif "HTTP Probe SKIPPED" in line:
            self.current_http_ok = None

        # Extract report filename
        if "Report filename:" in line:
            # noinspection PyBroadException
            try:
                _, rep_part = line.split("Report filename:", 1)
                self.current_report_file = rep_part.strip()
            except Exception:  # nosec B110
                pass
        elif (
            "Saved human-readable markdown report to:" in line
            or "Saved instance markdown report to:" in line
        ):
            # noinspection PyBroadException
            try:
                split_key = (
                    "Saved human-readable markdown report to:"
                    if "Saved human-readable markdown report to:" in line
                    else "Saved instance markdown report to:"
                )
                _, path_part = line.split(split_key, 1)
                self.current_report_file = Path(path_part.strip()).name
            except Exception:  # nosec B110
                pass

        # Detect package start: "Testing package: <id> (<name>)"
        if "Testing package:" in line:
            _, pkg_part = line.split("Testing package:", 1)
            pkg_words = pkg_part.strip().split()
            pkg_id = next(iter(pkg_words), "unknown").strip("() ")
            self.current_component = pkg_id
            self.current_http_ok = None
            self.current_http_url = None
            self.last_failed_key = None

            current_engine = self.current_engine
            current_mode = self.current_mode
            if "[" in line and "]" in line:
                # noinspection PyBroadException
                try:
                    # Use rsplit to target trailing '[MODE / ENGINE]'
                    bracket_content = line.rsplit("[", 1)[1].split("]", 1)[0]
                    if "/" in bracket_content:
                        m_tok, e_tok = bracket_content.split("/", 1)
                        current_mode = m_tok.strip().upper()
                        current_engine = e_tok.strip().upper()
                except Exception:  # nosec B110
                    pass
            self.current_engine = current_engine
            self.current_mode = current_mode

            self.log_queue.put(
                {
                    "type": "record",
                    "record": {
                        "timestamp": now_ts,
                        "component_id": pkg_id,
                        "mode": current_mode,
                        "engine": current_engine,
                        "vmid": self.current_vmid,
                        "ip": self.current_ip,
                        "status": "running",
                        "deployment": "In Progress",
                        "running": True,
                        "http_ok": None,
                        "http_url": None,
                        "report_file": self.current_report_file,
                        "is_package": True,
                    },
                }
            )

        # Detect component start: "Testing component: <id> (Engine: <e>, Mode: <m>)"
        elif "Testing component:" in line:
            _, comp_part = line.split("Testing component:", 1)
            comp_words = comp_part.strip().split()
            comp_id = next(iter(comp_words), "unknown").strip("() ")
            self.current_component = comp_id
            self.current_http_ok = None
            self.current_http_url = None
            self.last_failed_key = None

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
                        "vmid": self.current_vmid,
                        "ip": self.current_ip,
                        "status": "running",
                        "deployment": "In Progress",
                        "running": True,
                        "http_ok": None,
                        "http_url": None,
                        "report_file": self.current_report_file,
                        "is_package": False,
                    },
                }
            )

        # Detect package success: "✅ Package agile-ops verified successfully!"
        elif "verified successfully!" in line and "Package" in line:
            self.current_run_passed += 1
            _, pkg_part = line.split("Package", 1)
            pkg_words = pkg_part.strip().split()
            pkg_id = next(iter(pkg_words), "unknown")
            mode_val = self.current_mode
            engine_val = self.current_engine
            if "[" in line and "]" in line:
                # noinspection PyBroadException
                try:
                    bracket_content = line.rsplit("[", 1)[1].split("]", 1)[0]
                    if "/" in bracket_content:
                        m_tok, e_tok = bracket_content.split("/", 1)
                        mode_val = m_tok.strip().upper()
                        engine_val = e_tok.strip().upper()
                except Exception:  # nosec B110
                    pass
            self.current_mode = mode_val
            self.current_engine = engine_val
            self.log_queue.put(
                {
                    "type": "record",
                    "record": {
                        "timestamp": now_ts,
                        "component_id": pkg_id,
                        "mode": mode_val,
                        "engine": engine_val,
                        "vmid": self.current_vmid,
                        "ip": self.current_ip,
                        "status": "success",
                        "deployment": "success",
                        "running": True,
                        "http_ok": True,
                        "http_url": self.current_http_url,
                        "report_file": self.current_report_file,
                        "is_package": True,
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
                        "vmid": self.current_vmid,
                        "ip": self.current_ip,
                        "status": "success",
                        "deployment": "success",
                        "running": True,
                        "http_ok": self.current_http_ok,
                        "http_url": self.current_http_url,
                        "report_file": self.current_report_file,
                        "is_package": False,
                    },
                }
            )

        # Detect failure: "❌ Component verification failed" / "❌ Error during test of"
        elif (
            "❌ Component verification failed" in line
            or "❌ Package verification failed" in line
            or "❌ Error during test of" in line
        ):
            comp_id = self.current_component or "unknown"
            is_pkg = "Package" in line or self.target_type == "packages"
            mode_val = self.current_mode
            engine_val = self.current_engine
            if "[" in line and "]" in line:
                # noinspection PyBroadException
                try:
                    bracket_content = line.rsplit("[", 1)[1].split("]", 1)[0]
                    if "/" in bracket_content:
                        m_tok, e_tok = bracket_content.split("/", 1)
                        mode_val = m_tok.strip().upper()
                        engine_val = e_tok.strip().upper()
                except Exception:  # nosec B110
                    pass
            self.current_mode = mode_val
            self.current_engine = engine_val

            fail_key = f"{comp_id}_{mode_val}_{engine_val}"
            if self.last_failed_key != fail_key:
                self.last_failed_key = fail_key
                self.current_run_failures += 1
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
                            "mode": mode_val,
                            "engine": engine_val,
                            "vmid": self.current_vmid,
                            "ip": self.current_ip,
                            "status": "failed",
                            "deployment": "failed",
                            "running": False,
                            "http_ok": self.current_http_ok,
                            "http_url": self.current_http_url,
                            "report_file": self.current_report_file,
                            "error_message": err_msg,
                            "is_package": is_pkg,
                        },
                    }
                )

        # Detect failure category tag: "🏷️ Failure Category: [<category>]"
        elif "🏷️ Failure Category:" in line or "🏷️ [" in line:
            cat = "Onbekend"
            if "[" in line and "]" in line:
                cat = line.split("[", 1)[1].split("]", 1)[0].strip()
            self.log_queue.put(
                {
                    "type": "log",
                    "content": f"🏷️ [Diagnose Categorie] {cat}",
                }
            )

        # Detect milestones in Ansible execution
        elif "TASK [Pull latest service images" in line:
            self.log_queue.put(
                {"type": "log", "content": "📥 [Fase] Container images ophalen..."}
            )
        elif "TASK [Ensure container volume" in line:
            self.log_queue.put(
                {
                    "type": "log",
                    "content": "📁 [Fase] Volume directory structuur voorbereiden...",
                }
            )
        elif "TASK [Deploy services with Compose]" in line:
            self.log_queue.put(
                {
                    "type": "log",
                    "content": "🚀 [Fase] Containers starten via Compose...",
                }
            )
        elif "Running service health verification probe..." in line:
            self.log_queue.put(
                {
                    "type": "log",
                    "content": "🌐 [Fase] Service healthcheck & HTTP Web UI testen...",
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
                        "vmid": self.current_vmid,
                        "ip": self.current_ip,
                        "status": "skipped",
                        "deployment": "skipped",
                        "running": False,
                        "http_ok": None,
                        "http_url": None,
                        "error_message": line.strip(),
                        "is_package": False,
                    },
                }
            )

    def stop_test(self) -> bool:
        """Terminates active test runner subprocess and all child processes."""
        with self.lock:
            proc = self.process
            if not self.is_running or proc is None:
                return False
            self.is_aborted = True
            # noinspection PyBroadException
            try:
                pgid: Optional[int] = None
                if proc.pid is not None:
                    # noinspection PyBroadException
                    try:
                        found_pgid: int = os.getpgid(proc.pid)
                        if found_pgid > 1 and found_pgid != os.getpgrp():
                            pgid = found_pgid
                            # Send SIGINT first to trigger immediate test runner abort
                            os.killpg(found_pgid, signal.SIGINT)
                            time.sleep(0.15)
                            os.killpg(found_pgid, signal.SIGTERM)
                        else:
                            proc.terminate()
                    except Exception:
                        proc.terminate()

                def _force_kill(p: subprocess.Popen, kill_pgid: Optional[int]):
                    time.sleep(2.0)
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

                    # noinspection PyBroadException
                    try:
                        from scripts.proxmox_package_test_runner import (
                            cleanup_stale_test_instances,
                            setup_proxmox_client,
                        )

                        pve_cli = setup_proxmox_client()
                        node_name = os.getenv("PROXMOX_NODE") or "pve"
                        cleanup_stale_test_instances(pve_cli, node_name)
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
                            "Terminating all active test processes immediately..."
                        ),
                    }
                )
                return True
            except Exception as exc:
                logger.error(f"Failed to terminate process group: {exc}")
                return False


def _resolve_report_path(
    docs_dir: Path,
    report_type: str = "latest",
    target_file: str = "",
    comp_id: str = "",
) -> Optional[Path]:
    """Resolves target markdown report path based on query parameters."""
    if target_file:
        safe_name = Path(target_file).name
        candidate = docs_dir / safe_name
        if candidate.exists() and candidate.is_file():
            return candidate

    if comp_id:
        matching = sorted(
            docs_dir.glob(f"PROXMOX_*_{comp_id}_*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not matching:
            matching = sorted(
                docs_dir.glob(f"PROXMOX_*{comp_id}*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        if matching:
            return next(iter(matching), None)

    package_reports = sorted(
        docs_dir.glob("PROXMOX_PACKAGE_TESTS_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    component_report = docs_dir / "PROXMOX_TESTS.md"
    package_summary = docs_dir / "PROXMOX_PACKAGE_TESTS.md"

    if report_type == "package":
        return next(
            iter(package_reports),
            package_summary if package_summary.exists() else None,
        )
    if report_type == "component":
        if component_report.exists():
            return component_report
        return None

    latest_pkg = next(iter(package_reports), None)
    if latest_pkg and component_report.exists():
        if latest_pkg.stat().st_mtime > component_report.stat().st_mtime:
            return latest_pkg
        return component_report
    if latest_pkg:
        return latest_pkg
    if component_report.exists():
        return component_report
    if package_summary.exists():
        return package_summary
    return None


def render_markdown_to_pdf(markdown_text: str, docs_dir: Path) -> Optional[bytes]:
    """Renders markdown text into an A4 PDF with embedded images using Playwright."""
    # noinspection PyBroadException
    try:
        import mistune  # type: ignore
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as err:
        logger.error(f"Required PDF export package missing: {err}")
        return None

    # noinspection PyBroadException
    try:
        rendered_html = mistune.html(markdown_text)
        html_content = (
            rendered_html if isinstance(rendered_html, str) else str(rendered_html)
        )

        def embed_img(match: re.Match) -> str:
            rel_path = match.group(1)
            img_file = (docs_dir / rel_path).resolve()
            if str(img_file).startswith(str(docs_dir.resolve())) and img_file.exists():
                data = base64.b64encode(img_file.read_bytes()).decode("ascii")
                ext = img_file.suffix.lstrip(".").lower() or "png"
                return f'src="data:image/{ext};base64,{data}"'
            return match.group(0)

        html_content = re.sub(r'src="(images/[^"]+)"', embed_img, html_content)

        full_html = (
            "<!DOCTYPE html>\n<html>\n<head>\n"
            '<meta charset="utf-8">\n'
            "<style>\n"
            "  @page { size: A4; margin: 15mm; }\n"
            "  body {\n"
            "    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', "
            "Roboto, Helvetica, Arial, sans-serif;\n"
            "    color: #1e293b; background: #ffffff; margin: 0; padding: 0;\n"
            "    line-height: 1.5; font-size: 13px;\n"
            "  }\n"
            "  h1 { font-size: 20px; color: #0f172a; border-bottom: 2px solid "
            "#e2e8f0; padding-bottom: 8px; margin-top: 0; "
            "page-break-after: avoid; }\n"
            "  h2 { font-size: 16px; color: #1e293b; border-bottom: 1px solid "
            "#e2e8f0; padding-bottom: 4px; margin-top: 22px; "
            "page-break-after: avoid; }\n"
            "  h3 { font-size: 14px; color: #334155; margin-top: 16px; "
            "page-break-after: avoid; }\n"
            "  h4 { font-size: 13px; color: #475569; margin-top: 14px; "
            "page-break-after: avoid; }\n"
            "  h5 { font-size: 12px; color: #64748b; margin-top: 12px; "
            "page-break-after: avoid; }\n"
            "  table {\n"
            "    width: 100%; border-collapse: collapse; margin: 12px 0 18px 0;\n"
            "    font-size: 11px; page-break-inside: avoid;\n"
            "  }\n"
            "  th, td {\n"
            "    border: 1px solid #cbd5e1; padding: 5px 8px; text-align: left;\n"
            "  }\n"
            "  th {\n"
            "    background-color: #f1f5f9; font-weight: 600; color: #334155;\n"
            "  }\n"
            "  tr:nth-child(even) { background-color: #f8fafc; }\n"
            "  code {\n"
            "    background: #f1f5f9; border: 1px solid #e2e8f0; padding: 1px 4px;\n"
            "    border-radius: 3px; font-family: ui-monospace, SFMono-Regular, "
            "Menlo, monospace; font-size: 11px;\n"
            "  }\n"
            "  pre {\n"
            "    background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px;\n"
            "    border-radius: 4px; font-size: 11px; page-break-inside: avoid;\n"
            "  }\n"
            "  img {\n"
            "    max-width: 100%; max-height: 280px; object-fit: contain;\n"
            "    border-radius: 6px; border: 1px solid #cbd5e1; display: block;\n"
            "    margin: 6px 0 12px 0; page-break-inside: avoid;\n"
            "  }\n"
            "  a { color: #2563eb; text-decoration: none; }\n"
            "  hr { border: none; border-top: 1px solid #e2e8f0; margin: 20px 0; }\n"
            "</style>\n</head>\n<body>\n"
            f"{html_content}\n"
            "</body>\n</html>"
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(full_html, wait_until="load")
            pdf_bytes = page.pdf(
                format="A4",
                margin={
                    "top": "15mm",
                    "bottom": "15mm",
                    "left": "15mm",
                    "right": "15mm",
                },
                print_background=True,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=(
                    '<div style="font-size: 9px; color: #94a3b8; '
                    "font-family: sans-serif; width: 100%; text-align: right; "
                    'padding-right: 15mm;">'
                    'Page <span class="pageNumber"></span> of '
                    '<span class="totalPages"></span> | NjordDeploy Test Report</div>'
                ),
            )
            browser.close()
            return pdf_bytes
    except Exception as err:
        logger.error(f"Failed to generate PDF from markdown: {err}")
        return None


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
        load_dotenv(project_root / ".env", override=True)
        default_engine = get_configured_engine()
        test_ip = os.getenv("PROXMOX_TEST_IP", "10.99.0.199")
        bridge = os.getenv("PROXMOX_BRIDGE")
        if not bridge:
            bridge = "vmbr1" if "10.99." in test_ip else "vmbr0"
        elif "10.99." in test_ip and bridge == "vmbr0":
            bridge = "vmbr1"

        default_gw = "10.99.0.1" if "10.99." in test_ip else "192.168.178.1"
        test_gw = os.getenv("PROXMOX_GATEWAY")
        if not test_gw or ("10.99." in test_ip and "10.99." not in test_gw):
            test_gw = default_gw

        return jsonify(
            {
                "node": os.getenv("PROXMOX_NODE", "pve"),
                "template_id": os.getenv("PROXMOX_TEMPLATE_ID", "902"),
                "templates": {
                    "docker_vm": 911,
                    "docker_lxc": 912,
                    "podman_vm": 913,
                    "podman_lxc": 914,
                },
                "engine": default_engine,
                "mode": "lxc",
                "bridge": bridge,
                "test_ip": test_ip,
                "gateway": test_gw,
                "vlan_tag": os.getenv("PROXMOX_VLAN_TAG", ""),
            }
        )

    @app.route("/api/config/network", methods=["POST"])
    def set_config_network() -> Union[Response, Tuple[Response, int]]:
        """Sets or toggles the active test network profile (isolated vs lan)."""
        from utils.ai_provider_manager import set_env_key_value

        raw_payload = request.get_json()
        payload = raw_payload if isinstance(raw_payload, dict) else {}
        profile = str(payload.get("profile", "isolated")).lower()

        if profile == "lan":
            bridge = "vmbr0"
            test_ip = "192.168.178.199"
            gateway = "192.168.178.1"
        else:
            profile = "isolated"
            bridge = "vmbr1"
            test_ip = "10.99.0.199"
            gateway = "10.99.0.1"

        os.environ["PROXMOX_BRIDGE"] = bridge
        os.environ["PROXMOX_TEST_IP"] = test_ip
        os.environ["PROXMOX_GATEWAY"] = gateway

        env_path = project_root / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            lines = set_env_key_value(lines, "PROXMOX_BRIDGE", bridge)
            lines = set_env_key_value(lines, "PROXMOX_TEST_IP", test_ip)
            lines = set_env_key_value(lines, "PROXMOX_GATEWAY", gateway)
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

        return jsonify(
            {
                "success": True,
                "profile": profile,
                "bridge": bridge,
                "test_ip": test_ip,
                "gateway": gateway,
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

    @app.route("/api/packages", methods=["GET"])
    def get_packages() -> Response:
        """Returns all turnkey packages/stacks with metadata and last test status."""
        metadata_path = project_root / "config" / "components_metadata.json"
        templates_path = project_root / "component_templates"

        comp_mgr = ComponentManager(
            metadata_file_path=str(metadata_path),
            templates_path=str(templates_path),
        )
        packages_dict = comp_mgr.get_all_packages()
        all_components = {c["id"]: c for c in comp_mgr.get_all_components()}

        # Load package test results history
        pkg_results_file = project_root / "tests" / "proxmox_package_results.json"
        pkg_results_map: Dict[str, Any] = {}
        if pkg_results_file.exists():
            # noinspection PyBroadException
            try:
                with open(pkg_results_file, "r", encoding="utf-8") as f:
                    pkg_history = json.load(f)
                    if isinstance(pkg_history, list):
                        for rec in pkg_history:
                            if isinstance(rec, dict) and "package_id" in rec:
                                pkg_results_map[rec["package_id"]] = rec
            except Exception as read_ex:
                logger.warning(f"Could not read package results: {read_ex}")

        enriched = []
        for pkg_id, pkg in packages_dict.items():
            comp_ids = pkg.get("components") or []
            comp_details = []
            for cid in comp_ids:
                c_data = all_components.get(cid, {})
                comp_details.append(
                    {
                        "id": cid,
                        "name": c_data.get("name", cid),
                        "has_ui": bool(c_data.get("has_ui", False)),
                        "category": c_data.get("category", ""),
                    }
                )

            last_run = pkg_results_map.get(pkg_id)
            enriched.append(
                {
                    "id": pkg_id,
                    "name": pkg.get("name") or pkg_id,
                    "badge": pkg.get("badge") or "Curated Stack",
                    "description": pkg.get("description", ""),
                    "icon": pkg.get("icon") or "fa-solid fa-layer-group",
                    "components": comp_ids,
                    "components_detail": comp_details,
                    "app_count": len(comp_ids),
                    "last_run": last_run,
                    "status": (
                        last_run.get("status", "untested") if last_run else "untested"
                    ),
                }
            )

        enriched.sort(key=lambda x: str(x["name"]).lower())
        return jsonify(enriched)

    @app.route("/api/run", methods=["POST"])
    def run_tests() -> Union[Response, Tuple[Response, int]]:
        """Starts a test run with selected options (components or packages)."""
        raw_data = request.get_json()
        data = raw_data if isinstance(raw_data, dict) else {}
        target_type = str(data.get("target_type", "components")).lower()
        if target_type not in ["components", "packages", "stacks", "templates"]:
            target_type = "components"
        if target_type == "stacks":
            target_type = "packages"

        components = data.get("components", [])
        packages = data.get("packages", [])
        engine = data.get("engine", "docker").lower()
        mode = data.get("mode", "lxc").lower()
        node = data.get("node", "pve")
        template_id = data.get("template_id", "902")
        skip_passed = bool(data.get("skip_passed", False))

        if engine not in ["docker", "podman", "both", "all"]:
            engine = "docker"
        if mode not in ["lxc", "vm", "both", "all"]:
            mode = "lxc"

        success = runner_mgr.start_test(
            target_type=target_type,
            components=components if isinstance(components, list) else [],
            packages=packages if isinstance(packages, list) else [],
            engine=engine,
            mode=mode,
            node=node,
            template_id=template_id,
            skip_passed=skip_passed,
        )
        if success:
            return jsonify({"success": True, "target_type": target_type})
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
                "target_type": runner_mgr.target_type,
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
        """Reads specific or latest Markdown report (component or package)."""
        docs_dir = project_root / "docs"
        report_type = request.args.get("type", "latest")
        target_file = request.args.get("file", "").strip()
        comp_id = request.args.get("component", "").strip()

        target_path = _resolve_report_path(
            docs_dir=docs_dir,
            report_type=report_type,
            target_file=target_file,
            comp_id=comp_id,
        )

        if target_path and target_path.exists():
            content = target_path.read_text(encoding="utf-8")
            return jsonify(
                {"report": content, "filename": target_path.name, "success": True}
            )
        return jsonify({"report": "", "filename": "", "success": False})

    @app.route("/api/report/pdf", methods=["GET"])
    def export_report_pdf() -> Union[Response, Tuple[Response, int]]:
        """Renders and exports a markdown report as an A4 PDF."""
        docs_dir = project_root / "docs"
        report_type = request.args.get("type", "latest")
        target_file = request.args.get("file", "").strip()
        comp_id = request.args.get("component", "").strip()

        target_path = _resolve_report_path(
            docs_dir=docs_dir,
            report_type=report_type,
            target_file=target_file,
            comp_id=comp_id,
        )

        if not target_path or not target_path.exists():
            return jsonify({"error": "Report file not found"}), 404

        content = target_path.read_text(encoding="utf-8")
        pdf_bytes = render_markdown_to_pdf(content, docs_dir)
        if not pdf_bytes:
            return jsonify({"error": "Failed to generate PDF"}), 500

        pdf_filename = f"{target_path.stem}.pdf"
        response = Response(pdf_bytes, mimetype="application/pdf")
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{pdf_filename}"'
        )
        return response

    @app.route("/images/<path:filename>", methods=["GET"])
    @app.route("/docs/images/<path:filename>", methods=["GET"])
    def serve_docs_image(filename: str) -> Union[Response, Tuple[Response, int]]:
        """Securely serves image assets and test screenshots from docs/images."""
        images_dir = (project_root / "docs" / "images").resolve()
        requested_path = (images_dir / filename).resolve()
        # Prevent directory traversal attacks
        if not str(requested_path).startswith(str(images_dir)):
            return jsonify({"error": "Access denied"}), 403
        if not requested_path.exists() or not requested_path.is_file():
            return jsonify({"error": "Image not found"}), 404
        return send_from_directory(images_dir, filename)

    @app.route("/api/results", methods=["GET"])
    def get_results() -> Response:
        """Returns cumulative test results history for components and packages."""
        results_file = project_root / "tests" / "proxmox_results.json"
        pkg_results_file = project_root / "tests" / "proxmox_package_results.json"

        combined: List[Dict[str, Any]] = []

        if results_file.exists():
            # noinspection PyBroadException
            try:
                with open(results_file, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                    if isinstance(history_data, list):
                        recent_data = history_data[-200:]
                        for rec in recent_data:
                            if isinstance(rec, dict):
                                rec_copy = rec.copy()
                                rec_copy["is_package"] = False
                                err_msg = rec_copy.get("error_message")
                                if isinstance(err_msg, str):
                                    masked_err = mask_passwords(err_msg)
                                    if len(masked_err) > 200:
                                        rec_copy["error_message"] = (
                                            masked_err[:200] + "... (truncated)"
                                        )
                                    else:
                                        rec_copy["error_message"] = masked_err
                                combined.append(rec_copy)
            except Exception as exc:
                logger.warning(f"Failed to read results file: {exc}")

        if pkg_results_file.exists():
            # noinspection PyBroadException
            try:
                with open(pkg_results_file, "r", encoding="utf-8") as f:
                    pkg_history = json.load(f)
                    if isinstance(pkg_history, list):
                        for prec in pkg_history:
                            if isinstance(prec, dict):
                                comp_statuses = prec.get("components", {})
                                running_count = sum(
                                    1
                                    for c in comp_statuses.values()
                                    if isinstance(c, dict) and c.get("running")
                                )
                                total_comps = len(comp_statuses)

                                combined.append(
                                    {
                                        "timestamp": prec.get("timestamp") or "",
                                        "component_id": prec.get("package_id"),
                                        "package_name": prec.get("package_name"),
                                        "mode": (prec.get("mode") or "LXC").upper(),
                                        "engine": (
                                            prec.get("engine") or "DOCKER"
                                        ).upper(),
                                        "vmid": prec.get("vmid"),
                                        "ip": prec.get("ip"),
                                        "deployment": (
                                            prec.get("deployment") or "success"
                                        ),
                                        "running": (
                                            running_count == total_comps
                                            and total_comps > 0
                                        ),
                                        "running_details": (
                                            f"{running_count}/{total_comps} Apps"
                                        ),
                                        "http_ok": (
                                            True
                                            if prec.get("status") == "success"
                                            else False
                                        ),
                                        "status": prec.get("status", "success"),
                                        "error_message": prec.get("error_message", ""),
                                        "report_file": prec.get("report_file", ""),
                                        "is_package": True,
                                        "components": comp_statuses,
                                    }
                                )
            except Exception as exc:
                logger.warning(f"Failed to read package results file: {exc}")

        return jsonify(combined)

    @app.route("/api/results/clear", methods=["POST"])
    def clear_results() -> Union[Response, Tuple[Response, int]]:
        """Clears test results history for both components and packages."""
        results_file = project_root / "tests" / "proxmox_results.json"
        pkg_results_file = project_root / "tests" / "proxmox_package_results.json"
        # noinspection PyBroadException
        try:
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump([], f)
                f.write("\n")
            if pkg_results_file.exists():
                with open(pkg_results_file, "w", encoding="utf-8") as f:
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
        active_provider = os.getenv("AI_PROVIDER")
        diagnoser = AIFailureDiagnoser(provider=active_provider)
        return jsonify(
            {
                "configured": diagnoser.is_configured(),
                "provider": diagnoser.provider,
                "model": diagnoser.engine.model,
            }
        )

    @app.route("/api/ai/providers", methods=["GET"])
    def get_ai_providers() -> Response:
        """Returns all registered AI providers, configuration state, and
        active choice.
        """
        from utils.ai_provider_manager import load_ai_providers_registry

        registry = load_ai_providers_registry()
        active_provider = os.getenv("AI_PROVIDER")
        if not active_provider:
            if os.getenv("GEMINI_API_KEY"):
                active_provider = "gemini"
            elif os.getenv("HOSTYOURAI_API_KEY"):
                active_provider = "hostyourai"
            elif os.getenv("OPENAI_API_KEY"):
                active_provider = "openai"
            elif os.getenv("ANTHROPIC_API_KEY"):
                active_provider = "anthropic"
            else:
                active_provider = "ollama"

        provider_list = []
        for p_id, p_def in registry.items():
            if not isinstance(p_def, dict):
                continue
            env_var = p_def.get("env_var")
            is_configured = True
            if p_def.get("requires_api_key", True) and env_var:
                is_configured = bool(os.getenv(env_var))

            model_name = (
                p_def.get("configured_model") or p_def.get("default_model") or "default"
            )
            provider_list.append(
                {
                    "id": p_id,
                    "name": p_def.get("name", p_id.capitalize()),
                    "model": model_name,
                    "configured": is_configured,
                    "is_active": (p_id == active_provider),
                }
            )

        return jsonify(
            {
                "success": True,
                "active_provider": active_provider,
                "providers": provider_list,
            }
        )

    @app.route("/api/ai/select-provider", methods=["POST"])
    def select_ai_provider() -> Union[Response, Tuple[Response, int]]:
        """Sets active AI provider and persists it to .env and environment."""
        from utils.ai_provider_manager import (
            load_ai_providers_registry,
            set_env_key_value,
        )

        raw_payload = request.get_json()
        payload = raw_payload if isinstance(raw_payload, dict) else {}
        chosen_provider = payload.get("provider")

        if not isinstance(chosen_provider, str) or not chosen_provider.strip():
            return (
                jsonify({"success": False, "error": "Provider ID is required."}),
                400,
            )

        chosen_provider = chosen_provider.strip().lower()
        registry = load_ai_providers_registry()
        if chosen_provider not in registry:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Unknown provider '{chosen_provider}'.",
                    }
                ),
                400,
            )

        # Update environment variable
        os.environ["AI_PROVIDER"] = chosen_provider

        # Persist to .env file
        env_path = project_root / ".env"
        lines: list[str] = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        new_lines = set_env_key_value(lines, "AI_PROVIDER", chosen_provider)
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return jsonify(
            {
                "success": True,
                "active_provider": chosen_provider,
                "name": registry[chosen_provider].get("name", chosen_provider),
            }
        )

    @app.route("/api/ai/diagnose", methods=["POST"])
    def ai_diagnose() -> Union[Response, Tuple[Response, int]]:
        """Diagnoses a single failure or batch of failures with configured AI."""
        raw_payload = request.get_json()
        payload = raw_payload if isinstance(raw_payload, dict) else {}
        chosen_provider = payload.get("provider") or os.getenv("AI_PROVIDER")
        chosen_model = payload.get("model")
        diagnoser = AIFailureDiagnoser(
            provider=chosen_provider,
            model=chosen_model,
        )

        if not diagnoser.is_configured():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            f"AI provider '{diagnoser.provider}' is not configured. "
                            "Please check your API key in .env or choose another AI."
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

    @app.route("/api/ai/apply-root-mode", methods=["POST"])
    def ai_apply_root_mode() -> Union[Response, Tuple[Response, int]]:
        """Applies a suggested root mode (requires_root, podman_mode) to metadata."""
        raw_payload = request.get_json()
        payload = raw_payload if isinstance(raw_payload, dict) else {}
        comp_id = payload.get("component_id")
        requires_root = payload.get("requires_root", True)
        podman_mode = payload.get("podman_mode", "rootful")

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
            update_data = {
                "requires_root": bool(requires_root),
                "podman_mode": str(podman_mode),
            }
            comp_details = component_manager.get_component_details(comp_id.strip())
            if (
                comp_details
                and comp_details.get("has_ui")
                and not comp_details.get("ui_port_variable")
            ):
                vars_list = comp_details.get("variables", [])
                for v in vars_list:
                    if isinstance(v, dict) and v.get("type") == "port":
                        update_data["ui_port_variable"] = v.get("name") or v.get("id")
                        break
            component_manager.update_component_metadata(
                comp_id.strip(),
                update_data,
            )
            return jsonify({"success": True, "component_id": comp_id})
        except Exception as exc:
            logger.error(f"Failed to apply root mode: {exc}", exc_info=True)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to apply root mode.",
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
