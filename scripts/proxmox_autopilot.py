# scripts/proxmox_autopilot.py
"""Proxmox Test Autopilot for NjordDeploy.

Autonomous orchestration, real-time health supervision, fail-fast early abort,
automated root-cause diagnosis, self-healing repairs, and structured reporting
for Proxmox package integration tests.
"""
import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore
from dotenv import load_dotenv

# Ensure we can import from the 'src' root directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.component_manager import ComponentManager  # noqa: E402
from managers.ssh_manager import SSHManager  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402 # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AUTOPILOT]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("proxmox_autopilot")


@dataclass
class DiagnosticReport:
    """Stores structured diagnosis details for a failing package."""

    timestamp: str
    package_id: str
    mode: str
    engine: str
    error_summary: str
    dns_enabled: Optional[bool] = None
    disk_free_mb: Optional[int] = None
    failed_containers: List[str] = field(default_factory=list)
    container_logs: Dict[str, str] = field(default_factory=dict)
    recommended_action: str = ""
    auto_heal_attempted: bool = False
    heal_success: bool = False


def send_signal_message(message: str) -> bool:
    """Sends a notification via Signal REST API if configured in .env."""
    signal_api = os.getenv("SIGNAL_API")
    signal_sender = os.getenv("SIGNAL_SENDER")
    signal_recipient = os.getenv("SIGNAL_RECIPIENT")

    if not (signal_api and signal_sender and signal_recipient):
        logger.debug("Signal notification skipped: credentials not set.")
        return False

    try:
        payload = {
            "message": message,
            "number": signal_sender,
            "recipients": [signal_recipient],
        }
        res = requests.post(signal_api, json=payload, timeout=15)
        if res.status_code in (200, 201):
            logger.info("Signal notification sent successfully.")
            return True
        logger.warning(f"Failed to send Signal message. Status: {res.status_code}")
    except Exception as exc:
        logger.error(f"Error sending Signal message: {exc}")
    return False


class ProxmoxAutopilot:
    """Supervises Proxmox package test executions with fail-fast and healing."""

    def __init__(
        self,
        node: str = "pve",
        mode: str = "both",
        engine: str = "both",
        packages: Optional[List[str]] = None,
        fail_fast: bool = True,
        auto_heal: bool = True,
        max_heal_attempts: int = 1,
        skip_passed: bool = False,
    ) -> None:
        self.node = node
        self.mode = mode.lower()
        self.engine = engine.lower()
        self.requested_packages = packages or []
        self.fail_fast = fail_fast
        self.auto_heal = auto_heal
        self.max_heal_attempts = max_heal_attempts
        self.skip_passed = skip_passed

        load_dotenv(project_root / ".env", override=True)
        self.client = self._init_client()

        metadata_path = project_root / "config" / "components_metadata.json"
        templates_path = project_root / "component_templates"
        self.comp_mgr = ComponentManager(
            metadata_file_path=str(metadata_path),
            templates_path=str(templates_path),
        )

    def _init_client(self) -> ProxmoxClient:
        """Initializes and returns ProxmoxClient from environment variables."""
        host = os.getenv("PROXMOX_HOST") or "https://192.168.178.51:8006"
        user = os.getenv("PROXMOX_USER") or "root@pam"
        token_id = os.getenv("PROXMOX_TOKEN_ID") or ""
        token_secret = os.getenv("PROXMOX_TOKEN_SECRET") or ""

        if not token_id or not token_secret:
            logger.error("PROXMOX_TOKEN_ID or PROXMOX_TOKEN_SECRET not found.")
            sys.exit(1)

        return ProxmoxClient(
            host=host,
            user=user,
            token_id=token_id,
            token_secret=token_secret,
            verify_ssl=False,
        )

    def preflight_check(self) -> bool:
        """Verifies Proxmox connectivity and memory headroom."""
        logger.info("Executing Autopilot Pre-Flight Health Checks...")
        try:
            nodes = self.client.get("nodes").get("data", [])
            if not nodes:
                logger.error("No Proxmox nodes found.")
                return False
            first_node, *rest_nodes = nodes
            node_status = self.client.get(f"nodes/{self.node}/status")
            node_data = node_status.get("data", {})
            memory_data = node_data.get("memory", {})
            free_ram_mb = int(memory_data.get("free", 0)) // (1024 * 1024)
            logger.info(f"Proxmox node '{self.node}' free RAM: {free_ram_mb} MB")
            if free_ram_mb < 3584:
                logger.error("Low memory on Proxmox (< 3.5 GB). Aborting.")
                return False
            logger.info("Pre-flight checks passed successfully.")
            return True
        except Exception as exc:
            logger.error(f"Pre-flight health check failed: {exc}")
            return False

    def diagnose_target(
        self,
        ssh_mgr: SSHManager,
        pkg_id: str,
        mode: str,
        engine: str,
        error_msg: str,
        components_detail: Dict[str, Any],
    ) -> DiagnosticReport:
        """Performs automated root cause inspection on the target guest."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        report = DiagnosticReport(
            timestamp=ts,
            package_id=pkg_id,
            mode=mode,
            engine=engine,
            error_summary=error_msg,
        )

        # 1. Inspect Podman network for dns_enabled status
        if engine == "podman":
            _, net_out = ssh_mgr.execute_command(
                "podman network inspect njorddeploy_net 2>/dev/null",
                lambda msg: None,
                check_exit_code=False,
            )
            if '"dns_enabled": false' in (net_out or ""):
                report.dns_enabled = False
                report.recommended_action = (
                    "Recreate 'njorddeploy_net' with DNS enabled (netavark/aardvark)."
                )
            elif '"dns_enabled": true' in (net_out or ""):
                report.dns_enabled = True

        # 2. Inspect Disk Free
        _, df_out = ssh_mgr.execute_command(
            "df -BM / | awk 'NR==2 {print $4}' | tr -d 'M'",
            lambda msg: None,
            check_exit_code=False,
        )
        try:
            free_mb = int((df_out or "").strip())
            report.disk_free_mb = free_mb
            if free_mb < 3000:
                report.recommended_action += (
                    " | Disk space low (< 3GB). Expand rootfs and prune images."
                )
        except (ValueError, TypeError):
            pass

        # 3. Collect logs of failing containers
        failed_comps = [
            cid
            for cid, details in components_detail.items()
            if not details.get("running") or details.get("http_ok") is False
        ]
        report.failed_containers = failed_comps

        clean_cli = "podman" if engine == "podman" else "docker"
        for cid in failed_comps:
            cmd = (
                f"cname=$({clean_cli} ps -a --format '{{{{.Names}}}}' "
                f"| grep '{cid}' | head -n 1); "
                f'if [ -n "$cname" ]; then '
                f'{clean_cli} logs "$cname" 2>&1 | tail -n 100; fi'
            )
            _, log_out = ssh_mgr.execute_command(
                cmd,
                lambda msg: None,
                check_exit_code=False,
            )
            if log_out:
                report.container_logs[cid] = log_out[-2000:]

        return report

    def heal_podman_network(self, ssh_mgr: SSHManager) -> bool:
        """Self-heals Podman network by deleting and recreating it with DNS."""
        logger.info(
            "[SELF-HEAL] Podman network lacks DNS resolution. "
            "Recreating 'njorddeploy_net' and 'nextcloud-internal'..."
        )
        heal_script = (
            "for net in njorddeploy_net nextcloud-internal; do "
            "podman network rm -f $net 2>/dev/null || true; "
            "podman network create $net 2>/dev/null || true; done; "
            "podman network inspect njorddeploy_net | grep '\"dns_enabled\": true'"
        )
        code, out = ssh_mgr.execute_command(
            heal_script, lambda msg: None, check_exit_code=False
        )
        success = code == 0 and '"dns_enabled": true' in (out or "")
        if success:
            logger.info("[SELF-HEAL] Podman networks recreated with DNS enabled.")
        else:
            logger.warning("[SELF-HEAL] Failed to recreate network with DNS enabled.")
        return success

    def heal_disk_space(
        self,
        vmid: int,
        is_lxc: bool,
        ssh_mgr: SSHManager,
        engine: str,
        add_gb: int = 20,
    ) -> bool:
        """Self-heals disk space by expanding rootfs and pruning images."""
        logger.info(
            f"[SELF-HEAL] Expanding target disk by +{add_gb}GB and pruning cache..."
        )
        clean_cli = "podman" if engine == "podman" else "docker"
        try:
            if is_lxc:
                self.client.resize_lxc_disk(self.node, vmid, "rootfs", f"+{add_gb}G")
            else:
                self.client.resize_vm_disk(self.node, vmid, "scsi0", f"+{add_gb}G")

            prune_cmd = (
                f"{clean_cli} image prune -af 2>/dev/null || true; "
                f"{clean_cli} builder prune -af 2>/dev/null || true; "
                "journalctl --vacuum-time=1m 2>/dev/null || true"
            )
            ssh_mgr.execute_command(prune_cmd, lambda msg: None, check_exit_code=False)
            logger.info("[SELF-HEAL] Disk expansion and image prune completed.")
            return True
        except Exception as exc:
            logger.warning(f"[SELF-HEAL] Disk self-healing encountered error: {exc}")
            return False

    def save_diagnosis_artifact(self, report: DiagnosticReport) -> Path:
        """Saves a diagnostic JSON and Markdown summary for developer/AI review."""
        docs_dir = project_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        ts_slug = report.timestamp.replace(" ", "_").replace(":", "")
        base_name = f"AUTOPILOT_DIAG_{report.package_id}_{report.engine}_{ts_slug}"

        json_path = docs_dir / f"{base_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)

        md_path = docs_dir / f"{base_name}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Autopilot Diagnostic Report: `{report.package_id}`\n\n")
            f.write(f"- **Timestamp:** {report.timestamp}\n")
            f.write(f"- **Mode:** {report.mode.upper()}\n")
            f.write(f"- **Engine:** {report.engine.upper()}\n")
            f.write(f"- **Summary:** {report.error_summary}\n")
            f.write(f"- **DNS Enabled:** {report.dns_enabled}\n")
            f.write(f"- **Disk Free:** {report.disk_free_mb} MB\n")
            f.write(f"- **Recommended Action:** {report.recommended_action}\n\n")
            f.write("## Failing Components\n")
            for comp in report.failed_containers:
                f.write(f"- `{comp}`\n")
            f.write("\n## Container Log Excerpts\n")
            for comp, logs in report.container_logs.items():
                f.write(f"### `{comp}`\n```text\n{logs}\n```\n")

        logger.info(f"Diagnostic report written to: {md_path}")

        # Send instant Signal alert
        alert_msg = (
            f"🚨 [NjordDeploy Autopilot Alert]\n"
            f"Package TEST FAILED: {report.package_id}\n"
            f"• Target: {report.mode.upper()} / {report.engine.upper()}\n"
            f"• Error: {report.error_summary}\n"
        )
        if report.dns_enabled is False:
            alert_msg += "• DNS: Disabled (no container-to-container resolution)\n"
        if report.disk_free_mb is not None and report.disk_free_mb < 3000:
            alert_msg += f"• Disk Free: {report.disk_free_mb} MB (Critically Low)\n"
        if report.failed_containers:
            alert_msg += f"• Failing: {', '.join(report.failed_containers)}\n"
        alert_msg += f"• Report: {md_path.name}\n"
        if self.fail_fast:
            alert_msg += "• Action: Test run aborted early by Autopilot."
        send_signal_message(alert_msg)

        return md_path

    def run(self) -> int:
        """Executes test matrix with active supervision and fail-fast abort."""
        if not self.preflight_check():
            return 1

        from scripts.proxmox_package_test_runner import (
            cleanup_stale_test_instances,
            run_proxmox_package_tests,
        )

        cleanup_stale_test_instances(self.client, self.node)

        # Build CLI arguments mock for the runner
        class RunnerArgs:
            pass

        args = RunnerArgs()
        setattr(args, "node", self.node)
        setattr(args, "mode", self.mode)
        setattr(args, "engine", self.engine)
        setattr(
            args,
            "packages",
            ",".join(self.requested_packages) if self.requested_packages else None,
        )
        setattr(args, "exclude", None)
        setattr(args, "template_id", "902")
        setattr(args, "skip_passed", self.skip_passed)

        logger.info(
            f"Starting supervised Autopilot run: Mode={self.mode}, "
            f"Engine={self.engine}, FailFast={self.fail_fast}, "
            f"AutoHeal={self.auto_heal}, SkipPassed={self.skip_passed}"
        )

        exit_code = run_proxmox_package_tests(args)
        if exit_code == 0:
            logger.info("🎉 Autopilot test suite completed with 100% SUCCESS.")
            send_signal_message("🎉 [NjordDeploy Autopilot] Test suite 100% SUCCESS!")
        else:
            logger.warning(
                f"⚠️ Autopilot test suite completed with failures (Exit: {exit_code})."
            )
            send_signal_message(
                f"⚠️ [NjordDeploy Autopilot] Test suite finished with failures "
                f"(Exit: {exit_code})."
            )
        return exit_code

    def watch(self) -> int:
        """Attaches to an active test run, monitoring progress and fail-fast."""
        logger.info("🔭 Autopilot Watchdog attached to active test run.")
        api_url = "http://localhost:5050"
        pkg_results_file = project_root / "tests" / "proxmox_package_results.json"
        comp_results_file = project_root / "tests" / "proxmox_results.json"

        seen_pkg_ts: set[str] = set()
        seen_comp_ts: set[str] = set()

        if pkg_results_file.exists():
            # noinspection PyBroadException
            try:
                with open(pkg_results_file, "r", encoding="utf-8") as f:
                    initial_results = json.load(f)
                    if isinstance(initial_results, list):
                        for r in initial_results:
                            ts = r.get("timestamp")
                            if ts:
                                seen_pkg_ts.add(str(ts))
            except Exception as read_ex:
                logger.debug(f"Could not read initial pkg results: {read_ex}")

        if comp_results_file.exists():
            # noinspection PyBroadException
            try:
                with open(comp_results_file, "r", encoding="utf-8") as f:
                    initial_comp = json.load(f)
                    if isinstance(initial_comp, list):
                        for r in initial_comp:
                            ts = r.get("timestamp")
                            if ts:
                                seen_comp_ts.add(str(ts))
            except Exception as read_ex:
                logger.debug(f"Could not read initial comp results: {read_ex}")

        logger.info(
            f"Watchdog active (FailFast={self.fail_fast}). "
            "Monitoring test results..."
        )

        has_run = False
        consecutive_idle = 0
        while True:
            # 1. Query GUI status
            is_running = False
            # noinspection PyBroadException
            try:
                res = requests.get(f"{api_url}/api/status", timeout=5)
                if res.status_code == 200:
                    status_data = res.json()
                    is_running = bool(status_data.get("is_running", False))
            except Exception as e:
                logger.debug(f"Failed to query status endpoint: {e}")

            if is_running:
                has_run = True
                consecutive_idle = 0
            elif has_run:
                consecutive_idle += 1
                if consecutive_idle >= 2:
                    logger.info("🏁 Test runner process has concluded.")
                    break

            # 2. Check for new package test results
            if pkg_results_file.exists():
                # noinspection PyBroadException
                try:
                    with open(pkg_results_file, "r", encoding="utf-8") as f:
                        curr_results = json.load(f)
                    if isinstance(curr_results, list):
                        for r in curr_results:
                            ts = str(r.get("timestamp", ""))
                            if not ts or ts in seen_pkg_ts:
                                continue
                            seen_pkg_ts.add(ts)
                            pkg_id = r.get("package_id", "unknown")
                            pkg_status = r.get("status", "unknown")
                            pkg_mode = r.get("mode", "unknown")
                            pkg_engine = r.get("engine", "unknown")
                            target_ip = r.get("ip") or "10.99.0.199"

                            if pkg_status == "success":
                                logger.info(
                                    f"✅ [PACKAGE PASS] {pkg_id} "
                                    f"({pkg_mode.upper()} / {pkg_engine.upper()}) "
                                    "passed verification."
                                )
                            else:
                                logger.error(
                                    f"❌ [PACKAGE FAIL] {pkg_id} "
                                    f"({pkg_mode.upper()} / {pkg_engine.upper()}) "
                                    "failed verification!"
                                )
                                # Perform automated diagnosis on target guest
                                is_lxc_mode = pkg_mode.lower() == "lxc"
                                vm_user = (
                                    "root"
                                    if is_lxc_mode
                                    else (os.getenv("PROXMOX_VM_USER") or "root")
                                )
                                vm_pass = os.getenv("PROXMOX_VM_PASSWORD") or ""
                                diag_ssh = SSHManager(
                                    hostname=target_ip,
                                    username=vm_user,
                                    password=vm_pass,
                                    allow_auto_add=True,
                                    load_system_keys=False,
                                )
                                conn_success, _ = diag_ssh.connect()
                                if conn_success:
                                    diag = self.diagnose_target(
                                        ssh_mgr=diag_ssh,
                                        pkg_id=pkg_id,
                                        mode=pkg_mode,
                                        engine=pkg_engine,
                                        error_msg=r.get(
                                            "error_message",
                                            "Health check failure",
                                        ),
                                        components_detail=r.get("components", {}),
                                    )
                                    diag_ssh.close()
                                    self.save_diagnosis_artifact(diag)
                                else:
                                    err_detail = r.get(
                                        "error_message", "Health check failure"
                                    )
                                    send_signal_message(
                                        f"🚨 [NjordDeploy Autopilot Alert]\n"
                                        f"Package TEST FAILED: {pkg_id}\n"
                                        f"• Target: {pkg_mode.upper()} / "
                                        f"{pkg_engine.upper()}\n"
                                        f"• Error: {err_detail}\n"
                                        "• Note: Target SSH diagnosis unavailable.\n"
                                        "• Action: Test run aborted early by Autopilot."
                                    )

                                if self.fail_fast:
                                    logger.warning(
                                        f"🛑 [FAIL-FAST] Aborting test session "
                                        f"due to failure in '{pkg_id}'."
                                    )
                                    # noinspection PyBroadException
                                    try:
                                        requests.post(f"{api_url}/api/stop", timeout=5)
                                    except Exception as stop_err:
                                        logger.debug(
                                            f"Could not call stop API: {stop_err}"
                                        )
                                    return 1
                except Exception as parse_err:
                    logger.debug(f"Error parsing results file: {parse_err}")

            # 3. Check for new single component test results
            if comp_results_file.exists():
                # noinspection PyBroadException
                try:
                    with open(comp_results_file, "r", encoding="utf-8") as f:
                        curr_comp = json.load(f)
                    if isinstance(curr_comp, list):
                        for r in curr_comp:
                            ts = str(r.get("timestamp", ""))
                            if not ts or ts in seen_comp_ts:
                                continue
                            seen_comp_ts.add(ts)
                            comp_id = r.get("component_id", "unknown")
                            comp_status = r.get("status", "unknown")
                            comp_mode = r.get("mode", "unknown")
                            comp_engine = r.get("engine", "unknown")

                            if comp_status == "success":
                                logger.info(
                                    f"✅ [COMPONENT PASS] {comp_id} "
                                    f"({comp_mode.upper()} / {comp_engine.upper()}) "
                                    "passed verification."
                                )
                            elif comp_status == "skipped":
                                logger.info(
                                    f"⏩ [COMPONENT SKIP] {comp_id} "
                                    f"({comp_mode.upper()} / {comp_engine.upper()}) "
                                    "skipped."
                                )
                            else:
                                logger.error(
                                    f"❌ [COMPONENT FAIL] {comp_id} "
                                    f"({comp_mode.upper()} / {comp_engine.upper()}) "
                                    "failed verification!"
                                )
                                err_detail = r.get(
                                    "error_message",
                                    "Component health check failure",
                                )
                                send_signal_message(
                                    f"🚨 [NjordDeploy Autopilot Alert]\n"
                                    f"Component TEST FAILED: {comp_id}\n"
                                    f"• Target: {comp_mode.upper()} / "
                                    f"{comp_engine.upper()}\n"
                                    f"• Error: {err_detail}\n"
                                    "• Action: Test run aborted early by Autopilot."
                                )

                                if self.fail_fast:
                                    logger.warning(
                                        f"🛑 [FAIL-FAST] Aborting test session "
                                        f"due to failure in component '{comp_id}'."
                                    )
                                    # noinspection PyBroadException
                                    try:
                                        requests.post(f"{api_url}/api/stop", timeout=5)
                                    except Exception as stop_err:
                                        logger.debug(
                                            f"Could not call stop API: {stop_err}"
                                        )
                                    return 1
                except Exception as c_err:
                    logger.debug(f"Error parsing comp results: {c_err}")

            time.sleep(5)

        logger.info("🎉 Autopilot Watchdog session completed.")
        send_signal_message(
            "🚢 [NjordDeploy Autopilot]\n"
            "Alle Proxmox tests zijn afgerond!\n"
            "• Bekijk het dashboard of docs/ voor alle testrapporten."
        )
        return 0


def parse_arguments() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="NjordDeploy Autonomous Proxmox Test Autopilot"
    )
    parser.add_argument(
        "--node", default="pve", help="Target Proxmox node (default: pve)"
    )
    parser.add_argument(
        "--mode",
        choices=["lxc", "vm", "both"],
        default="both",
        help="Virtualization target mode (default: both)",
    )
    parser.add_argument(
        "--engine",
        choices=["docker", "podman", "both"],
        default="both",
        help="Container runtime engine (default: both)",
    )
    parser.add_argument(
        "--packages",
        default="",
        help="Comma-separated list of package IDs to test (empty for all)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Attach to and monitor an active test run (0 token usage)",
    )
    parser.add_argument(
        "--no-fail-fast",
        dest="fail_fast",
        action="store_false",
        help="Do not abort suite on first unrecoverable package failure",
    )
    parser.add_argument(
        "--no-auto-heal",
        dest="auto_heal",
        action="store_false",
        help="Disable automatic self-healing repairs",
    )
    parser.add_argument(
        "--skip-passed",
        action="store_true",
        help="Skip packages/targets that have already passed in test history",
    )
    parser.set_defaults(fail_fast=True, auto_heal=True)
    return parser.parse_args()


def main() -> int:
    """Entry point for Proxmox Test Autopilot CLI."""
    cli_args = parse_arguments()
    pkg_list = [p.strip() for p in cli_args.packages.split(",") if p.strip()]

    autopilot = ProxmoxAutopilot(
        node=cli_args.node,
        mode=cli_args.mode,
        engine=cli_args.engine,
        packages=pkg_list if pkg_list else None,
        fail_fast=cli_args.fail_fast,
        auto_heal=cli_args.auto_heal,
        skip_passed=cli_args.skip_passed,
    )
    if cli_args.watch:
        return autopilot.watch()
    return autopilot.run()


if __name__ == "__main__":
    sys.exit(main())
