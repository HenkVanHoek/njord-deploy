# scripts/proxmox_test_runner.py
import argparse
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil  # type: ignore
import requests  # type: ignore
from dotenv import load_dotenv

# Ensure we can import from the 'src' root directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.component_manager import ComponentManager  # noqa: E402
from managers.deployment_manager import DeploymentManager  # noqa: E402
from managers.setup_manager import SetupManager  # noqa: E402
from managers.ssh_manager import SSHManager  # noqa: E402
from utils.container_engine import ContainerEngine  # noqa: E402
from utils.failed_components import (  # noqa: E402
    is_component_untestable,
    load_untestable_components,
    remove_untestable_component,
)
from utils.proxmox_client import ProxmoxClient  # noqa: E402 # type: ignore
from utils.template_header import update_template_header_content  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("proxmox_test_runner")

_abort_requested = False


def _abort_signal_handler(signum: int, frame: Any) -> None:
    global _abort_requested
    _abort_requested = True
    logger.warning(
        "⚠️ Termination signal received! Aborting entire test session immediately..."
    )
    os._exit(130)


signal.signal(signal.SIGINT, _abort_signal_handler)
signal.signal(signal.SIGTERM, _abort_signal_handler)

# Test-specific environment variable overrides for ports that conflict with
# host OS services (e.g., local DNS resolvers)
TEST_PORT_OVERRIDES = {
    # Port 53 conflicts with systemd-resolved on host Linux/LXC
    "ADGUARDHOME_DNS_PORT_TCP": "5353",
    "ADGUARDHOME_DNS_PORT_UDP": "5353",
    "PIHOLE_DNS_PORT": "5353",
}


def _save_incremental_test_result(test_record: Dict[str, Any]) -> None:
    """Appends or updates a single test result directly in
    tests/proxmox_results.json.
    """
    try:
        tests_dir = project_root / "tests"
        tests_dir.mkdir(exist_ok=True)
        json_path = tests_dir / "proxmox_results.json"

        history: List[Dict[str, Any]] = []
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        history = loaded
            except Exception as read_ex:
                logger.warning(f"Could not load existing test results: {read_ex}")

        updated = False
        for idx, rec in enumerate(history):
            if (
                rec.get("component_id") == test_record.get("component_id")
                and rec.get("timestamp") == test_record.get("timestamp")
                and rec.get("mode") == test_record.get("mode")
                and rec.get("engine") == test_record.get("engine")
            ):
                history[idx] = test_record
                updated = True
                break

        if not updated:
            history.append(test_record)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
            f.write("\n")
    except Exception as save_err:
        logger.warning(f"Failed to incrementally save test result: {save_err}")


def setup_proxmox_client() -> ProxmoxClient:
    """Initializes ProxmoxClient from environment variables."""
    host = os.getenv("PROXMOX_HOST") or "https://192.168.178.51:8006"
    user = os.getenv("PROXMOX_USER") or "root@pam"
    token_id = os.getenv("PROXMOX_TOKEN_ID") or ""
    token_secret = os.getenv("PROXMOX_TOKEN_SECRET") or ""

    if not token_id or not token_secret:
        logger.error("PROXMOX_TOKEN_ID or PROXMOX_TOKEN_SECRET not configured.")
        print(
            "ERROR: Proxmox API Token credentials must be set in your .env file.\n"
            "Required keys:\n"
            "  PROXMOX_HOST=https://192.168.178.51:8006\n"
            "  PROXMOX_USER=root@pam\n"
            "  PROXMOX_TOKEN_ID=<token-id>\n"
            "  PROXMOX_TOKEN_SECRET=<token-secret>\n"
        )
        sys.exit(1)

    return ProxmoxClient(
        host=host,
        user=user,
        token_id=token_id,
        token_secret=token_secret,
        verify_ssl=False,
    )


def wait_for_ip(
    client: ProxmoxClient, node: str, vmid: int, timeout_seconds: int = 120
) -> str | None:
    """Polls the guest agent until it retrieves a valid IP address."""
    logger.info(f"Waiting for VM {vmid} to boot and retrieve dynamic IP...")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        ip = client.get_vm_ip(node, vmid)
        if ip:
            logger.info(f"VM {vmid} is online with IP: {ip}")
            return ip
        time.sleep(5)
    logger.error(f"Timed out waiting for VM {vmid} IP address.")
    return None


def verify_service_health(
    vm_ip: str,
    vm_user: str,
    vm_pass: str,
    _component_id: str,
    component_details: Dict[str, Any],
    variables_list: List[Dict[str, Any]],
    engine: str = "docker",
) -> Dict[str, Any]:
    """Runs SSH-based checks and optional HTTP requests to verify health."""
    results: Dict[str, Any] = {
        "running": False,
        "http_ok": None,
        "details": "",
        "logs_error": False,
        "detected_version": None,
    }

    # Initialize SSHManager to run checks
    ssh_mgr = SSHManager(
        hostname=vm_ip,
        username=vm_user,
        password=vm_pass,
        allow_auto_add=True,
        load_system_keys=False,
    )
    connected, conn_msg = ssh_mgr.connect()
    if not connected:
        results["details"] = f"SSH verification failed: {conn_msg}"
        return results

    try:
        # Check container status
        log_lines: List[str] = []

        def append_log(msg: str):
            log_lines.append(msg)

        # Determine container CLI binary (podman or docker) based on engine parameter
        # with fallback detection on target host
        cli_detect_cmd = (
            f"if [ '{engine}' = 'podman' ] && command -v podman >/dev/null 2>&1; "
            "then echo 'podman'; "
            f"elif [ '{engine}' = 'docker' ] && command -v docker >/dev/null 2>&1; "
            "then echo 'docker'; "
            "elif command -v podman >/dev/null 2>&1; then echo 'podman'; "
            "else echo 'docker'; fi"
        )
        _, cli_out = ssh_mgr.execute_command(
            cli_detect_cmd,
            lambda x: None,
            check_exit_code=False,
        )
        cont_cli = (cli_out or "").strip() or engine

        # List containers running on the host (checking user and root namespaces)
        _, user_out = ssh_mgr.execute_command(
            f"{cont_cli} ps -a --format '{{{{.Names}}}} ({{{{.Status}}}})'",
            lambda x: None,
            check_exit_code=False,
        )
        sudo_cmd = (
            f"echo '{vm_pass}' | sudo -S {cont_cli} ps -a "
            f"--format '{{{{.Names}}}} ({{{{.Status}}}})'"
            if vm_user != "root"
            else f"{cont_cli} ps -a --format '{{{{.Names}}}} ({{{{.Status}}}})'"
        )
        _, root_out = ssh_mgr.execute_command(
            sudo_cmd,
            lambda x: None,
            check_exit_code=False,
        )

        def filter_clean_lines(raw: str) -> List[str]:
            return [
                ln.strip()
                for ln in (raw or "").splitlines()
                if ln.strip()
                and not ln.startswith("WARN")
                and not ln.startswith("INFO")
                and not ln.startswith("DEBU")
                and not ln.startswith("level=")
                and not ln.startswith("time=")
                and not ln.startswith("[sudo]")
                and not ln.startswith("Password:")
            ]

        user_valid = filter_clean_lines(user_out)
        root_valid = filter_clean_lines(root_out)

        if any("Up" in line for line in user_valid) or (user_valid and not root_valid):
            output = user_out
            valid_lines = user_valid
            cli_prefix = ""
        else:
            output = root_out
            valid_lines = root_valid
            cli_prefix = f"echo '{vm_pass}' | sudo -S " if vm_user != "root" else ""

        is_running = any("Up" in line for line in valid_lines)
        results["running"] = is_running
        if is_running:
            results["details"] = f"Running containers:\n{output}"
        elif valid_lines:
            results["details"] = f"Containers found but none are running:\n{output}"
        else:
            results["details"] = "No running containers found on target host."

        # Check container logs for tracebacks or fatal errors
        # Find matching container name
        container_list = [line.split()[0] for line in valid_lines if line]
        matched_container = next(iter(container_list), None)

        if matched_container:
            ssh_mgr.execute_command(
                f"{cli_prefix}{cont_cli} logs --tail 100 {matched_container}",
                append_log,
                check_exit_code=False,
            )
            logs_content = "\n".join(log_lines).lower()
            if "traceback" in logs_content or "fatal" in logs_content:
                results["logs_error"] = True

            if not is_running:
                results["details"] += "\nLast 100 container logs:\n" + "\n".join(
                    log_lines
                )

        if not is_running:
            # Run deep diagnostics on target host
            diag_cmds = [
                f"{cont_cli} ps -a",
                "cat /opt/njorddeploy/docker-compose.yml 2>/dev/null",
                f"cd /opt/njorddeploy 2>/dev/null && {cont_cli}-compose logs",
                f"cd /opt/njorddeploy 2>/dev/null && {cont_cli}-compose ps",
            ]
            if matched_container:
                diag_cmds.append(f"{cont_cli} start {matched_container} 2>&1")
                diag_cmds.append(f"{cont_cli} logs --tail 50 {matched_container} 2>&1")
            for dcmd in diag_cmds:
                _, dout = ssh_mgr.execute_command(
                    dcmd, lambda x: None, check_exit_code=False
                )
                if dout and dout.strip():
                    results["details"] += f"\n--- Output of '{dcmd}' ---\n{dout}"
                    logger.warning(f"Remote diagnostic '{dcmd}':\n{dout}")

        # Inspect container config to get the actual version
        if matched_container:
            cmd_inspect = (
                f"{cont_cli} inspect {matched_container} "
                f"'--format' '{{{{json .Config}}}}'"
            )
            inspect_exit, inspect_out = ssh_mgr.execute_command(
                cmd_inspect,
                lambda x: None,
                check_exit_code=False,
            )
            if inspect_exit == 0 and inspect_out is not None:
                try:
                    import json

                    inspect_str = inspect_out.strip()
                    config_data = json.loads(inspect_str)
                    labels = config_data.get("Labels") or {}
                    env_list = config_data.get("Env") or []

                    # 1. Check container labels
                    ver: str | None = (
                        labels.get("org.opencontainers.image.version")
                        or labels.get("version")
                        or labels.get("image.version")
                        or labels.get("org.label-schema.version")
                        or labels.get("build_version")
                    )
                    # 2. Check env variables
                    if not ver:
                        for env in env_list:
                            if "=" in env:
                                k, v = env.split("=", 1)
                                k_upper = k.upper()
                                if k_upper in [
                                    "VERSION",
                                    "CADDY_VERSION",
                                    "RADARR_VERSION",
                                    "SONARR_VERSION",
                                    "HA_VERSION",
                                    "APP_VERSION",
                                    "ADGUARD_VERSION",
                                    "PIHOLE_VERSION",
                                    "IMMICH_VERSION",
                                    "JELLYFIN_VERSION",
                                    "NEXTCLOUD_VERSION",
                                ] or k_upper.endswith("_VERSION"):
                                    if v and v.lower() not in (
                                        "latest",
                                        "none",
                                        "unknown",
                                    ):
                                        ver = v
                                        break

                    if ver is not None and ver.strip():
                        clean_ver = ver.strip()
                        # Clean LinuxServer.io build version string if present
                        if "version:-" in clean_ver:
                            clean_ver = (
                                clean_ver.split("version:-")[1].split()[0].strip()
                            )
                        if clean_ver.lower() not in (
                            "latest",
                            "none",
                            "unknown",
                        ):
                            results["detected_version"] = clean_ver
                except Exception as inspect_ex:
                    logger.warning(
                        f"Failed to parse docker inspect output: {inspect_ex}"
                    )

        # Check UI access if applicable
        if component_details.get("has_ui", False):
            ui_var = component_details.get("ui_port_variable")
            port = None
            if ui_var:
                for var in variables_list:
                    var_name = var.get("id") or var.get("name")
                    if var_name == ui_var:
                        port = var.get("default")
                        break
            # Fallback to standard port if not in vars
            if not port:
                port = component_details.get("traefik_internal_port")
            # If still not found, check if there's any port variable in variables_list
            if not port:
                for var in variables_list:
                    if var.get("type") == "port":
                        port = var.get("default")
                        break

            if port:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                protocol = component_details.get("protocol", "http")
                url = f"{protocol}://{vm_ip}:{port}"
                logger.info(
                    f"Probing HTTP UI endpoint: {url} " "(retrying up to 15 times)..."
                )
                max_retries = 25
                for attempt in range(1, max_retries + 1):
                    try:
                        res = requests.get(url, timeout=5, verify=False)  # nosec B501
                        if res.status_code in [200, 301, 302, 401, 403, 404]:
                            results["http_ok"] = True
                            results[
                                "details"
                            ] += f"\nHTTP Probe: {res.status_code} ({url})"
                            break
                        else:
                            results["http_ok"] = False
                            results[
                                "details"
                            ] += f"\nHTTP Probe: {res.status_code} ({url})"
                            if attempt < max_retries:
                                time.sleep(4)
                    except Exception as ex:
                        results["http_ok"] = False
                        if attempt == max_retries:
                            results["details"] += (
                                f"\nHTTP Probe failed after {max_retries} "
                                f"attempts: {ex} ({url})"
                            )
                        else:
                            time.sleep(4)

                # Fallback for Traefik dashboard
                if not results.get("http_ok") and _component_id == "traefik":
                    try:
                        dash_url = f"{protocol}://{vm_ip}:{port}/dashboard/"
                        dash_res = requests.get(
                            dash_url, timeout=5, verify=False  # nosec B501
                        )
                        if dash_res.status_code in [200, 301, 302]:
                            results["http_ok"] = True
                            results["details"] += (
                                f"\nHTTP Probe (dashboard): "
                                f"{dash_res.status_code} ({dash_url})"
                            )
                    except Exception:  # nosec B110
                        pass

                # Fallback for services like AdGuard Home (initial wizard on port 3000)
                if not results.get("http_ok") and _component_id == "adguard-home":
                    fallback_url = f"http://{vm_ip}:3000"
                    try:
                        res = requests.get(
                            fallback_url, timeout=5, verify=False
                        )  # nosec B501
                        if res.status_code in [200, 301, 302, 401, 403]:
                            results["http_ok"] = True
                            results["details"] += (
                                f"\nHTTP Probe (initial setup port 3000): "
                                f"{res.status_code} ({fallback_url})"
                            )
                    except Exception:  # nosec B110
                        pass

                if not results.get("http_ok"):
                    clog_cmd = (
                        f"cd /opt/njorddeploy 2>/dev/null && "
                        f"{cont_cli} compose logs --tail 40 2>&1 || "
                        f"{cont_cli}-compose logs --tail 40 2>&1"
                    )
                    _, clog_out = ssh_mgr.execute_command(
                        clog_cmd,
                        lambda x: None,
                        check_exit_code=False,
                    )
                    if clog_out and clog_out.strip():
                        results[
                            "details"
                        ] += f"\n--- Service logs on probe failure ---\n{clog_out}"
                        logger.warning(f"Service logs on probe failure:\n{clog_out}")

    finally:
        ssh_mgr.close()

    return results


def update_template_status(
    templates_path: Path,
    component_id: str,
    tested_version: str,
    mode: str,
    engine: str,
    test_date: Optional[str] = None,
) -> None:
    """Updates status, last tested version and platform notes in template."""
    template_file = templates_path / component_id / "docker-compose.template.yml"
    if not template_file.exists():
        logger.warning(f"Template file not found to update status: {template_file}")
        return

    try:
        content = template_file.read_text(encoding="utf-8")
        new_content = update_template_header_content(
            content=content,
            mode=mode,
            engine=engine,
            tested_version=tested_version,
            test_date=test_date,
        )
        template_file.write_text(new_content, encoding="utf-8")

        meta_file = templates_path.parent / "config" / "components_metadata.json"
        if meta_file.exists():
            # noinspection PyBroadException
            try:
                comp_mgr = ComponentManager(
                    templates_path=str(templates_path),
                    metadata_file_path=str(meta_file),
                )
                comp_mgr.mark_component_tested(component_id, test_status="tested")
            except Exception as ex:
                logger.warning(
                    f"Could not update metadata timestamp for {component_id}: {ex}"
                )

        logger.info(
            f"Updated template status headers for {component_id} "
            f"(mode: {mode}, engine: {engine}, version: {tested_version})"
        )
    except Exception as ex:
        logger.error(f"Failed to update template headers for {component_id}: {ex}")


def get_template_status(templates_path: Path, component_id: str) -> str:
    """Reads the status of a component from its template header."""
    template_file = templates_path / component_id / "docker-compose.template.yml"
    if not template_file.exists():
        return "untested"
    # noinspection PyBroadException
    try:
        content = template_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("#"):
                stripped = line[1:].strip()
                if stripped.startswith("status:"):
                    parts = stripped.split(":", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    except Exception:  # nosec B110
        pass
    return "untested"


def check_concurrent_test_runners() -> None:
    """Checks if another proxmox_test_runner process is active and warns."""
    current_pid = os.getpid()
    active_runners: List[Tuple[int, str]] = []
    # noinspection PyBroadException
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            if proc.info.get("pid") == current_pid:
                continue
            cmdline = proc.info.get("cmdline") or []
            cmd_str = " ".join(cmdline)
            if "proxmox_test_runner.py" in cmd_str:
                active_runners.append((proc.info["pid"], cmd_str))
    except Exception:  # nosec B110
        pass

    if active_runners:
        for apid, acmd in active_runners:
            logger.warning(
                f"⚠️ Concurrent test runner detected (PID {apid}: {acmd}). "
                "Running multiple test sessions simultaneously may cause "
                "IP/VMID collisions on Proxmox."
            )


def cleanup_stale_test_instances(client: ProxmoxClient, node: str) -> None:
    """Finds and destroys any leftover test VMs or LXC containers from aborted runs."""
    stale_prefixes = ("pish-test-", "njord-test-")
    # Clean up stale QEMU VMs
    # noinspection PyBroadException
    try:
        vms = client.get(f"nodes/{node}/qemu").get("data", [])
        for vm in vms:
            vm_name = vm.get("name", "")
            vmid = vm.get("vmid")
            if any(vm_name.startswith(pfx) for pfx in stale_prefixes) and vmid:
                logger.warning(
                    f"Found stale test VM '{vm_name}' (VMID: {vmid}). Cleaning up..."
                )
                try:
                    client.stop_vm(node, vmid)
                    time.sleep(2)
                except Exception:  # nosec B110
                    pass
                try:
                    client.destroy_vm(node, vmid)
                    logger.info(f"Stale test VM {vmid} destroyed.")
                except Exception as ex:
                    logger.warning(f"Could not destroy stale test VM {vmid}: {ex}")
    except Exception as ex:
        logger.warning(f"Error checking for stale test VMs: {ex}")

    # Clean up stale LXC containers
    # noinspection PyBroadException
    try:
        lxcs = client.get(f"nodes/{node}/lxc").get("data", [])
        for lxc in lxcs:
            lxc_name = lxc.get("name", "")
            vmid = lxc.get("vmid")
            if any(lxc_name.startswith(pfx) for pfx in stale_prefixes) and vmid:
                logger.warning(
                    f"Found stale test LXC '{lxc_name}' (VMID: {vmid}). Cleaning up..."
                )
                try:
                    stop_lxc(client, node, vmid)
                    time.sleep(2)
                except Exception:  # nosec B110
                    pass
                try:
                    destroy_lxc(client, node, vmid)
                    logger.info(f"Stale test LXC {vmid} destroyed.")
                except Exception as ex:
                    logger.warning(f"Could not destroy stale test LXC {vmid}: {ex}")
    except Exception as ex:
        logger.warning(f"Error checking for stale test LXCs: {ex}")


def find_suitable_lxc_template(client: ProxmoxClient, node: str) -> str:
    """Finds a Debian LXC template in active storage pools."""
    storages = ["local"]
    try:
        storage_res = client.get(f"nodes/{node}/storage")
        active_vztmpl_storages = []
        for store in storage_res.get("data", []):
            is_active = store.get("active")
            content_types = store.get("content", "")
            if is_active and "vztmpl" in content_types:
                name = store.get("storage")
                if name:
                    active_vztmpl_storages.append(name)
        if active_vztmpl_storages:
            storages = sorted(active_vztmpl_storages, key=lambda x: x != "local")
    except Exception as e:
        logger.warning(f"Failed to list Proxmox storage pools: {e}")

    templates = []
    for s in storages:
        try:
            endpoint = f"nodes/{node}/storage/{s}/content"
            res = client.get(endpoint, params={"content": "vztmpl"})
            templates.extend(res.get("data", []))
        except Exception as e:
            logger.warning(f"Failed to query templates on storage '{s}': {e}")

    if templates:
        # Prioritize Debian templates
        debian_templates = [
            t for t in templates if "debian" in t.get("volid", "").lower()
        ]
        if debian_templates:
            debian_templates.sort(key=lambda x: x.get("volid", ""), reverse=True)
            newest_deb = next(iter(debian_templates), None)
            if isinstance(newest_deb, dict):
                volid = newest_deb.get("volid")
                if isinstance(volid, str) and volid:
                    return volid

    default_storage = next(iter(storages), "local")
    return f"{default_storage}:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst"


def wait_for_lxc_ip(
    client: ProxmoxClient, node: str, vmid: int, timeout_seconds: int = 120
) -> str:
    """Polls the Proxmox API until the container receives an IP address."""
    logger.info(f"Waiting for container {vmid} to receive an IP address...")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            endpoint = f"nodes/{node}/lxc/{vmid}/interfaces"
            res = client.get(endpoint)
            interfaces = res.get("data", [])
            for iface in interfaces:
                name = iface.get("name")
                inet = iface.get("inet")
                if name == "eth0" and inet:
                    parts = inet.split("/")
                    ip_addr, *_ = parts
                    if ip_addr and not ip_addr.startswith("127."):
                        return ip_addr
        except Exception as e:
            logger.debug(f"Failed to get interfaces: {e}")
        time.sleep(4)
    raise TimeoutError("Container failed to acquire an IP address in time.")


def start_lxc(client: ProxmoxClient, node: str, vmid: int) -> dict:
    return client.post(f"nodes/{node}/lxc/{vmid}/status/start")


def stop_lxc(client: ProxmoxClient, node: str, vmid: int) -> dict:
    return client.post(f"nodes/{node}/lxc/{vmid}/status/stop")


def destroy_lxc(client: ProxmoxClient, node: str, vmid: int) -> dict:
    return client.delete(f"nodes/{node}/lxc/{vmid}", params={"purge": 1})


def wait_for_proxmox_task(
    client: ProxmoxClient, node: str, upid: str, timeout_seconds: int = 180
) -> None:
    """Polls the Proxmox task status until it completes successfully."""
    logger.info(f"Waiting for Proxmox task to complete: {upid}")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            endpoint = f"nodes/{node}/tasks/{upid}/status"
            res = client.get(endpoint)
            data = res.get("data", {})
            status = data.get("status")
            if status == "stopped":
                exit_status = data.get("exitstatus")
                if exit_status == "OK":
                    logger.info("Proxmox task completed successfully.")
                    return
                elif isinstance(exit_status, str) and exit_status.startswith(
                    "WARNINGS"
                ):
                    logger.warning(
                        f"Proxmox task completed with non-fatal warnings: {exit_status}"
                    )
                    return
                else:
                    raise RuntimeError(
                        f"Proxmox task failed with status: {exit_status}"
                    )
        except Exception as e:
            if "failed with status" in str(e):
                raise e
            logger.debug(f"Failed to query task status: {e}")
        time.sleep(2)
    raise TimeoutError("Proxmox task timed out.")


def send_signal_message(message: str) -> None:
    """Sends a Signal message using the configured Signal API in the environment."""
    signal_api = os.getenv("SIGNAL_API")
    signal_sender = os.getenv("SIGNAL_SENDER")
    signal_recipient = os.getenv("SIGNAL_RECIPIENT")

    if not (signal_api and signal_sender and signal_recipient):
        logger.debug(
            "Signal notification skipped: "
            "SIGNAL_API, SIGNAL_SENDER, or SIGNAL_RECIPIENT not set."
        )
        return

    logger.info("Sending Signal notification...")
    try:
        import requests

        payload = {
            "message": message,
            "number": signal_sender,
            "recipients": [signal_recipient],
        }
        res = requests.post(signal_api, json=payload, timeout=15)
        if res.status_code in (200, 201):
            logger.info("Signal notification sent successfully.")
        else:
            logger.error(
                f"Failed to send Signal message. "
                f"Status: {res.status_code}, Response: {res.text}"
            )
    except Exception as e:
        logger.error(f"Error sending Signal message: {e}")


def calculate_resource_requirements(
    target_components: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Calculates dynamically required RAM (MB) and CPU cores from metadata."""
    base_ram = 8192
    base_cores = 4

    heavyweight_components = {
        "gitlab": 8192,
        "immich": 8192,
        "open-webui": 8192,
        "nextcloud": 4096,
        "frigate": 4096,
    }

    max_ram = base_ram
    max_cores = base_cores

    for comp in target_components:
        comp_id = comp.get("id", "")
        profile = comp.get("resource_profile") or {}
        ram_prof = ""
        cpu_prof = ""
        if isinstance(profile, dict):
            ram_prof = str(profile.get("ram", "low")).lower()
            cpu_prof = str(profile.get("cpu", "low")).lower()

        if ram_prof == "high" or comp_id in heavyweight_components:
            required = heavyweight_components.get(comp_id, 8192)
            max_ram = max(max_ram, required)
        elif ram_prof == "medium":
            max_ram = max(max_ram, 4096)

        if cpu_prof == "high":
            max_cores = max(max_cores, 6)

    return {"ram": max_ram, "cores": max_cores}


def run_environment_tests(
    proxmox_client,
    node: str,
    mode: str,
    engine: str,
    template_id: int,
    vm_user: str,
    vm_pass: str,
    target_components: List[Dict[str, Any]],
    comp_mgr: ComponentManager,
    setup_output_dir: Path,
    ssh_public_key: str,
) -> List[Dict[str, Any]]:
    """Runs test cycle on a specific (mode, engine) environment."""
    is_lxc = mode == "lxc"
    env_results: List[Dict[str, Any]] = []

    res_req = calculate_resource_requirements(target_components)
    allocated_ram = res_req["ram"]
    allocated_cores = res_req["cores"]

    logger.info("==================================================")
    logger.info(f"Target Environment: {mode.upper()} | Engine: {engine.upper()}")
    logger.info(
        f"Testing {len(target_components)} components "
        f"(Allocated Resources: {allocated_ram}MB RAM, {allocated_cores} Cores)..."
    )
    logger.info("==================================================")
    test_ip = os.getenv("PROXMOX_TEST_IP")
    test_gw = os.getenv("PROXMOX_GATEWAY", "192.168.178.1")
    bridge = os.getenv("PROXMOX_BRIDGE", "vmbr0")
    vlan_tag = os.getenv("PROXMOX_VLAN_TAG")

    tag_suffix = f",tag={vlan_tag}" if vlan_tag else ""
    if test_ip:
        ip_cidr = test_ip if "/" in test_ip else f"{test_ip}/24"
        clean_ip = test_ip.split("/")[0]
        lxc_net = (
            f"name=eth0,bridge={bridge}{tag_suffix},"
            f"firewall=0,ip={ip_cidr},gw={test_gw}"
        )
        vm_ipconfig = f"ip={ip_cidr},gw={test_gw}"
        vm_net = f"virtio,bridge={bridge}{tag_suffix},firewall=0"
    else:
        clean_ip = None
        lxc_net = f"name=eth0,bridge={bridge}{tag_suffix},firewall=0,ip=dhcp"
        vm_ipconfig = "ip=dhcp"
        vm_net = f"virtio,bridge={bridge}{tag_suffix},firewall=0"

    shared_lxc_vmid: int | None = None
    shared_lxc_ip: str | None = None
    shared_vm_vmid: int | None = None
    shared_vm_ip: str | None = None

    if is_lxc:
        logger.info(
            f"LXC mode: provisioning a shared container for {engine.upper()} tests."
        )
        try:
            shared_lxc_vmid = proxmox_client.get_next_vmid()
            logger.info(
                f"Creating shared LXC container {shared_lxc_vmid} on node '{node}'..."
            )
            ostemplate = find_suitable_lxc_template(proxmox_client, node)
            logger.info(f"Using template: {ostemplate}")

            create_data = {
                "vmid": shared_lxc_vmid,
                "ostemplate": ostemplate,
                "cores": allocated_cores,
                "memory": allocated_ram,
                "swap": 1024,
                "rootfs": "local-lvm:40",
                "net0": lxc_net,
                "features": "nesting=1",
                "unprivileged": 1,
                "password": vm_pass,
                "ssh-public-keys": ssh_public_key,
                "start": 1,
            }
            create_res = proxmox_client.post(f"nodes/{node}/lxc", data=create_data)
            upid = create_res.get("data")
            if isinstance(upid, str):
                wait_for_proxmox_task(proxmox_client, node, upid)

            if shared_lxc_vmid is None:
                raise RuntimeError("shared_lxc_vmid unexpectedly None")
            if clean_ip:
                shared_lxc_ip = clean_ip
                logger.info(f"Using configured static IP for LXC: {shared_lxc_ip}")
            else:
                shared_lxc_ip = wait_for_lxc_ip(proxmox_client, node, shared_lxc_vmid)
            if shared_lxc_ip is None:
                raise RuntimeError("shared_lxc_ip is None in LXC mode")
            logger.info(f"Shared LXC container online at {shared_lxc_ip}.")
            time.sleep(5)

            # Install container engine once on the shared container
            logger.info(f"Installing {engine.upper()} on shared LXC container...")
            lxc_ssh = SSHManager(
                hostname=shared_lxc_ip,
                username="root",
                password=vm_pass,
                allow_auto_add=True,
                load_system_keys=False,
            )
            connected = False
            conn_msg = ""
            for attempt in range(6):
                connected, conn_msg = lxc_ssh.connect()
                if connected:
                    break
                logger.info(
                    f"SSH attempt {attempt + 1}/6 failed: {conn_msg}. Retrying in 5s..."
                )
                time.sleep(5)
            if not connected:
                raise RuntimeError(
                    f"Failed to SSH into shared LXC container: {conn_msg}"
                )

            engine_helper = ContainerEngine(engine)
            provision_cmds = engine_helper.get_provisioning_commands(username="root")
            for cmd in provision_cmds:
                lxc_ssh.execute_command(cmd, lambda msg: None)

            # Ensure /tmp/.ansible directory exists with full permissions
            lxc_ssh.execute_command(
                "mkdir -p /tmp/.ansible && chmod 1777 /tmp/.ansible",
                lambda msg: None,
            )
            # Overwrite /root/.ssh/authorized_keys cleanly with runner key
            lxc_ssh.execute_command(
                f'mkdir -p /root/.ssh && echo "{ssh_public_key}" > '
                "/root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys",
                lambda msg: None,
            )
            if vm_user and vm_user != "root":
                lxc_ssh.execute_command(
                    f"id -u {vm_user} >/dev/null 2>&1 || "
                    f"useradd -m -s /bin/bash {vm_user}; "
                    f"echo '{vm_user}:{vm_pass}' | chpasswd; "
                    f"echo '{vm_user} ALL=(ALL) NOPASSWD:ALL' > "
                    f"/etc/sudoers.d/99-{vm_user}; "
                    f"mkdir -p /home/{vm_user}/.ssh && "
                    f'echo "{ssh_public_key}" > '
                    f"/home/{vm_user}/.ssh/authorized_keys && "
                    f"chown -R {vm_user}:{vm_user} /home/{vm_user}/.ssh && "
                    f"chmod 700 /home/{vm_user}/.ssh && "
                    f"chmod 600 /home/{vm_user}/.ssh/authorized_keys",
                    lambda msg: None,
                )
            lxc_ssh.close()
            logger.info(f"{engine.upper()} installed on shared LXC container.")

        except Exception as setup_err:
            logger.error(f"Failed to provision shared LXC container: {setup_err}")
            if shared_lxc_vmid:
                try:
                    stop_lxc(proxmox_client, node, shared_lxc_vmid)
                    destroy_lxc(proxmox_client, node, shared_lxc_vmid)
                except Exception:  # nosec B110
                    pass
            return env_results
    else:
        # VM mode: Provision a single shared VM for this environment test batch
        logger.info(f"VM mode: provisioning a shared VM for {engine.upper()} tests.")
        try:
            shared_vm_vmid = proxmox_client.get_next_vmid()
            if shared_vm_vmid is None:
                raise RuntimeError("Failed to allocate VMID from Proxmox.")
            logger.info(
                f"Cloning master template VMID {template_id} to shared VM "
                f"{shared_vm_vmid}..."
            )
            try:
                clone_res = proxmox_client.clone_vm(
                    node=node,
                    vmid=template_id,
                    newid=shared_vm_vmid,
                    name=f"pish-test-vm-{engine}",
                    full=False,
                )
                upid = clone_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(proxmox_client, node, upid)
            except Exception as clone_err:
                if "Linked clone feature is not supported" in str(clone_err):
                    logger.warning("Linked clone unsupported, full clone...")
                    clone_res = proxmox_client.clone_vm(
                        node=node,
                        vmid=template_id,
                        newid=shared_vm_vmid,
                        name=f"pish-test-vm-{engine}",
                        full=True,
                    )
                    upid = clone_res.get("data")
                    if isinstance(upid, str):
                        wait_for_proxmox_task(proxmox_client, node, upid)
                else:
                    raise

            import urllib.parse

            proxmox_client.configure_vm(
                node=node,
                vmid=shared_vm_vmid,
                config_data={
                    "ciuser": vm_user,
                    "cipassword": vm_pass,
                    "sshkeys": urllib.parse.quote(ssh_public_key),
                    "ipconfig0": vm_ipconfig,
                    "net0": vm_net,
                    "cores": allocated_cores,
                    "memory": allocated_ram,
                    "balloon": 2048,
                    "agent": "enabled=1",
                },
            )
            proxmox_client.start_vm(node=node, vmid=shared_vm_vmid)
            if clean_ip:
                shared_vm_ip = clean_ip
                logger.info(f"Using configured static IP for VM: {shared_vm_ip}")
                time.sleep(15)
            else:
                shared_vm_ip = wait_for_ip(
                    proxmox_client, node, shared_vm_vmid, timeout_seconds=180
                )
            if not shared_vm_ip:
                raise TimeoutError("Unable to retrieve shared VM IP address.")
            logger.info(f"Shared VM {shared_vm_vmid} online at {shared_vm_ip}.")
            time.sleep(5)

            # Install container engine once on the shared VM
            logger.info(f"Installing {engine.upper()} on shared VM...")
            vm_ssh = SSHManager(
                hostname=shared_vm_ip,
                username=vm_user,
                password=vm_pass,
                allow_auto_add=True,
                load_system_keys=False,
            )
            connected = False
            conn_msg = ""
            for attempt in range(8):
                connected, conn_msg = vm_ssh.connect()
                if connected:
                    break
                logger.info(
                    f"SSH attempt {attempt + 1}/8 failed: {conn_msg}. Retrying in 5s..."
                )
                time.sleep(5)
            if not connected:
                raise RuntimeError(f"Failed to SSH into shared VM: {conn_msg}")

            engine_helper = ContainerEngine(engine)
            provision_cmds = engine_helper.get_provisioning_commands(username=vm_user)
            sudo_pfx = f"echo '{vm_pass}' | sudo -S " if vm_user != "root" else ""
            for cmd in provision_cmds:
                clean_cmd = (
                    cmd.replace("sudo ", sudo_pfx)
                    if "sudo " in cmd
                    else f"{sudo_pfx}{cmd}"
                )
                vm_ssh.execute_command(clean_cmd, lambda msg: None)

            # Ensure /tmp/.ansible directory exists with full permissions
            vm_ssh.execute_command(
                f"{sudo_pfx}mkdir -p /tmp/.ansible && "
                f"{sudo_pfx}chmod 1777 /tmp/.ansible",
                lambda msg: None,
            )
            # Overwrite /root/.ssh/authorized_keys cleanly with runner key
            vm_ssh.execute_command(
                f"{sudo_pfx}mkdir -p /root/.ssh && "
                f'echo "{ssh_public_key}" | '
                f"{sudo_pfx}tee /root/.ssh/authorized_keys >/dev/null && "
                f"{sudo_pfx}chmod 600 /root/.ssh/authorized_keys",
                lambda msg: None,
            )
            if vm_user != "root":
                vm_ssh.execute_command(
                    f"mkdir -p /home/{vm_user}/.ssh && "
                    f'echo "{ssh_public_key}" > '
                    f"/home/{vm_user}/.ssh/authorized_keys && "
                    f"chmod 600 /home/{vm_user}/.ssh/authorized_keys",
                    lambda msg: None,
                )
            vm_ssh.close()
            logger.info(f"{engine.upper()} installed on shared VM.")

        except Exception as setup_err:
            logger.error(f"Failed to provision shared VM: {setup_err}")
            if shared_vm_vmid:
                try:
                    proxmox_client.stop_vm(node, shared_vm_vmid)
                    time.sleep(2)
                    proxmox_client.destroy_vm(node, shared_vm_vmid)
                except Exception:  # nosec B110
                    pass
            return env_results

    active_vmid = shared_lxc_vmid if is_lxc else shared_vm_vmid
    active_ip = shared_lxc_ip if is_lxc else shared_vm_ip
    ssh_user = "root" if is_lxc else vm_user

    try:
        for comp in target_components:
            if _abort_requested:
                logger.warning("⚠️ Abort requested. Halting component test loop.")
                break
            comp_id = comp.get("id", "unknown")
            logger.info("----------------------------------------")
            logger.info(
                f"Testing component: {comp_id} "
                f"(Engine: {engine.upper()}, Mode: {mode.upper()})"
            )
            logger.info("----------------------------------------")

            test_record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "component_id": comp_id,
                "mode": mode.upper(),
                "engine": engine.upper(),
                "status": "failed",
                "vmid": active_vmid,
                "ip": active_ip,
                "deployment": "failed",
                "running": False,
                "http_ok": None,
                "error_logs": False,
                "error_message": "",
            }

            # Check supported_matrix constraints before executing deployment
            if not comp_mgr.is_mode_supported(comp_id, mode):
                logger.info(
                    f"⏭️ Skipping {comp_id}: Mode '{mode.upper()}' is not "
                    "supported by component matrix constraint."
                )
                test_record["status"] = "skipped"
                test_record["deployment"] = "skipped"
                test_record["error_message"] = (
                    f"Skipped: Mode '{mode.upper()}' is not supported by "
                    "matrix constraint."
                )
                env_results.append(test_record)
                _save_incremental_test_result(test_record)
                continue

            if not comp_mgr.is_engine_supported(comp_id, engine):
                logger.info(
                    f"⏭️ Skipping {comp_id}: Engine '{engine.upper()}' is not "
                    "supported by component matrix constraint."
                )
                test_record["status"] = "skipped"
                test_record["deployment"] = "skipped"
                test_record["error_message"] = (
                    f"Skipped: Engine '{engine.upper()}' is not supported by "
                    "matrix constraint."
                )
                env_results.append(test_record)
                _save_incremental_test_result(test_record)
                continue

            try:
                if active_ip is None:
                    raise RuntimeError(f"Target IP is None in {mode.upper()} mode")

                logger.info(
                    f"Cleaning {engine.upper()} environment before testing "
                    f"{comp_id}..."
                )
                cleanup_ssh = SSHManager(
                    hostname=active_ip,
                    username=ssh_user,
                    password=vm_pass,
                    allow_auto_add=True,
                    load_system_keys=False,
                )
                connected = False
                conn_msg = ""
                for attempt in range(1, 16):
                    connected, conn_msg = cleanup_ssh.connect()
                    if connected:
                        break
                    if attempt < 15:
                        logger.info(
                            f"Waiting for SSH on {active_ip}:22 "
                            f"(attempt {attempt}/15)..."
                        )
                        time.sleep(3)
                if not connected:
                    raise RuntimeError(
                        f"Cannot connect to target host for cleanup: {conn_msg}"
                    )

                clean_cli = "podman" if engine == "podman" else "docker"
                cleanup_script = (
                    "if [ -d /opt/njorddeploy ]; then "
                    f"  (cd /opt/njorddeploy && {clean_cli} compose down -v "
                    "--remove-orphans 2>/dev/null || true); "
                    f"  (cd /opt/njorddeploy && {clean_cli}-compose down -v "
                    "--remove-orphans 2>/dev/null || true); "
                    "fi; "
                    f"running_c=$({clean_cli} ps -q 2>/dev/null); "
                    f'if [ -n "$running_c" ]; then {clean_cli} stop $running_c '
                    "2>/dev/null || true; fi; "
                    f"all_c=$({clean_cli} ps -aq 2>/dev/null); "
                    f'if [ -n "$all_c" ]; then {clean_cli} rm -f $all_c '
                    "2>/dev/null || true; fi; "
                    f"{clean_cli} system prune -af --volumes 2>/dev/null || true; "
                    f"{clean_cli} network inspect njorddeploy_net >/dev/null 2>&1 || "
                    f"{clean_cli} network create njorddeploy_net 2>/dev/null || true; "
                    f'if [ "{clean_cli}" = "podman" ] && [ -n "{ssh_user}" ]; then '
                    f'su - {ssh_user} -c "{clean_cli} network create '
                    'njorddeploy_net 2>/dev/null || true"; '
                    "fi; "
                    "mkdir -p /tmp/.ansible && "
                    "chmod 1777 /tmp/.ansible 2>/dev/null || true; "
                    "rm -rf /opt/njorddeploy/* 2>/dev/null || true"
                )
                if is_lxc or ssh_user == "root":
                    clean_cmd = f"sh -c '{cleanup_script}'"
                else:
                    clean_cmd = f"echo '{vm_pass}' | sudo -S sh -c '{cleanup_script}'"

                cleanup_ssh.execute_command(
                    clean_cmd, lambda msg: None, check_exit_code=False
                )
                cleanup_ssh.close()
                logger.info(f"{engine.upper()} environment clean.")

                # Generate deployment package locally
                logger.info(f"Generating deployment configurations for {comp_id}...")
                folder_vmid = active_vmid
                comp_output_dir = setup_output_dir / str(folder_vmid) / comp_id
                setup_mgr = SetupManager(
                    component_manager=comp_mgr.reader, output_dir=comp_output_dir
                )
                setup_mgr.initialize_environment()

                all_components_data = comp_mgr.get_all_components()
                comp_map = {c.get("id"): c for c in all_components_data if c.get("id")}
                dependencies = comp.get("depends_on", [])
                all_selected_ids = [comp_id]
                for dep_id in dependencies:
                    if dep_id in comp_map and dep_id not in all_selected_ids:
                        all_selected_ids.append(dep_id)

                all_selected_data = [
                    comp_map[cid] for cid in all_selected_ids if cid in comp_map
                ]

                user_vars = {}
                for cid in all_selected_ids:
                    variables_list = comp_mgr.reader.get_component_variables(cid)
                    for var in variables_list:
                        var_name = var.get("id") or var.get("name")
                        if var_name:
                            user_vars[var_name] = var.get("default")
                for var_name, override_val in TEST_PORT_OVERRIDES.items():
                    if var_name in user_vars:
                        user_vars[var_name] = override_val
                user_vars["PISelfhosting_HOST_IP"] = active_ip
                user_vars["CONTAINER_ENGINE"] = engine.lower()
                user_vars["TARGET_MODE"] = mode.lower()

                comp_mgr.generate_deployment_artifacts(
                    selected_components_data=all_selected_data,
                    global_vars=user_vars,
                    output_path=comp_output_dir,
                )

                # Deploy via Ansible
                logger.info(
                    f"Executing Ansible deployment to {active_ip} ({engine.upper()})..."
                )
                deploy_mgr = DeploymentManager(component_manager=comp_mgr)
                run_vmid = active_vmid
                task_id = f"test-{comp_id}-{run_vmid}"
                tasks_dict = {task_id: {"logs": [], "status": "pending"}}

                deploy_mgr.start_deployment(
                    task_id=task_id,
                    tasks=tasks_dict,
                    output_path=str(comp_output_dir),
                    devices=[
                        {
                            "ip": active_ip,
                            "username": ssh_user,
                            "password": vm_pass,
                            "container_engine": engine,
                        }
                    ],
                    selected_components_data=[comp],
                    global_vars=user_vars,
                )

                task_outcome: Dict[str, Any] = tasks_dict.get(task_id, {})
                if task_outcome.get("status") == "completed":
                    test_record["deployment"] = "success"
                    logger.info("Ansible deployment completed successfully.")
                else:
                    test_record["deployment"] = "failed"
                    errors_list: List[Dict[str, Any]] = task_outcome.get("errors", [])
                    first_error: Dict[str, Any] = next(iter(errors_list), {})
                    err_details = first_error.get("details", "Ansible execution error")
                    raise RuntimeError(f"Deployment failed: {err_details}")

                # Health verification
                logger.info("Running service health verification probe...")
                target_variables = comp_mgr.reader.get_component_variables(comp_id)
                health = verify_service_health(
                    vm_ip=active_ip,
                    vm_user=ssh_user,
                    vm_pass=vm_pass,
                    _component_id=comp_id,
                    component_details=comp,
                    variables_list=target_variables,
                    engine=engine,
                )

                test_record["running"] = health["running"]
                test_record["http_ok"] = health["http_ok"]
                test_record["error_logs"] = health["logs_error"]

                is_success = health["running"] and (
                    health["http_ok"] is True or health["http_ok"] is None
                )

                if is_success:
                    test_record["status"] = "success"
                    logger.info(f"✅ Component {comp_id} verified successfully!")
                    detected_version = health.get("detected_version")
                    version_to_record = (
                        detected_version
                        if (
                            detected_version
                            and detected_version.lower()
                            not in ("none", "latest", "unknown")
                        )
                        else comp.get("component_version", "latest")
                    )
                    update_template_status(
                        templates_path=project_root / "component_templates",
                        component_id=comp_id,
                        tested_version=version_to_record,
                        mode=mode.upper(),
                        engine=engine.lower(),
                        test_date=time.strftime("%Y-%m-%d"),
                    )
                else:
                    test_record["status"] = "failed"
                    test_record["error_message"] = health["details"]
                    logger.error(
                        f"❌ Component verification failed: {health['details']}"
                    )

            except Exception as ex:
                logger.error(f"❌ Error during test of {comp_id}: {ex}")
                test_record["status"] = "failed"
                test_record["error_message"] = str(ex)
                if _abort_requested:
                    logger.warning(
                        "⚠️ Abort detected during exception. Halting component loop."
                    )
                    break
            finally:
                folder_vmid = active_vmid
                if folder_vmid:
                    comp_output_dir = setup_output_dir / str(folder_vmid) / comp_id
                    if comp_output_dir.exists():
                        import shutil

                        shutil.rmtree(comp_output_dir)

            env_results.append(test_record)
            _save_incremental_test_result(test_record)

    finally:
        if is_lxc and shared_lxc_vmid:
            logger.info(f"Destroying shared LXC container {shared_lxc_vmid}...")
            try:
                stop_res = stop_lxc(proxmox_client, node, shared_lxc_vmid)
                upid = stop_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(proxmox_client, node, upid)
                destroy_res = destroy_lxc(proxmox_client, node, shared_lxc_vmid)
                upid = destroy_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(proxmox_client, node, upid)
                logger.info(f"Shared LXC container {shared_lxc_vmid} destroyed.")
            except Exception as teardown_err:
                logger.error(
                    f"Failed to destroy shared LXC container "
                    f"{shared_lxc_vmid}: {teardown_err}"
                )
        elif not is_lxc and shared_vm_vmid:
            logger.info(f"Destroying shared VM {shared_vm_vmid}...")
            try:
                stop_res = proxmox_client.stop_vm(node, shared_vm_vmid)
                upid = stop_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(proxmox_client, node, upid)
                destroy_res = proxmox_client.destroy_vm(node, shared_vm_vmid)
                upid = destroy_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(proxmox_client, node, upid)
                logger.info(f"Shared VM {shared_vm_vmid} destroyed.")
            except Exception as teardown_err:
                logger.error(
                    f"Failed to destroy shared VM {shared_vm_vmid}: {teardown_err}"
                )

    return env_results


def run_proxmox_tests(cli_args) -> int:
    """Orchestrates matrix environments, deploying, and generating reports."""
    load_dotenv()
    check_concurrent_test_runners()
    proxmox_client = setup_proxmox_client()

    node = cli_args.node or os.getenv("PROXMOX_NODE") or "pve"
    cleanup_stale_test_instances(proxmox_client, node)
    template_env = os.getenv("PROXMOX_TEMPLATE_ID") or "902"
    template_id = int(cli_args.template_id or template_env)
    vm_user = os.getenv("PROXMOX_VM_USER") or ""
    vm_pass = os.getenv("PROXMOX_VM_PASSWORD") or ""

    if not vm_user or not vm_pass:
        logger.error("PROXMOX_VM_USER or PROXMOX_VM_PASSWORD not configured.")
        print(
            "ERROR: PROXMOX_VM_USER and PROXMOX_VM_PASSWORD must be configured "
            "in your .env file."
        )
        sys.exit(1)

    # Load local directories and config
    metadata_path = project_root / "config" / "components_metadata.json"
    templates_path = project_root / "component_templates"

    comp_mgr = ComponentManager(
        metadata_file_path=str(metadata_path), templates_path=str(templates_path)
    )
    setup_output_dir = project_root / "tmp_proxmox_test"

    # Load untestable components list from docs/FAILED_COMPONENTS.md
    untestable_doc = project_root / "docs" / "FAILED_COMPONENTS.md"
    untestable_map = load_untestable_components(untestable_doc)

    # Get target components list
    all_components = comp_mgr.get_all_components()
    target_components = []

    if cli_args.components:
        selected_ids = [c.strip() for c in cli_args.components.split(",")]
        for comp in all_components:
            if comp.get("id") in selected_ids:
                target_components.append(comp)
    elif getattr(cli_args, "untested_ui", False):
        for comp in all_components:
            comp_id = comp.get("id", "")
            if (
                comp.get("has_ui")
                and get_template_status(templates_path, comp_id) != "tested"
            ):
                if (
                    getattr(cli_args, "include_untestable", False)
                    or comp_id not in untestable_map
                ):
                    target_components.append(comp)
    else:
        if getattr(cli_args, "include_untestable", False):
            target_components = all_components
        else:
            target_components = [
                c for c in all_components if c.get("id") not in untestable_map
            ]
            skipped_untestable = [
                c.get("id") for c in all_components if c.get("id") in untestable_map
            ]
            if skipped_untestable:
                logger.info(
                    f"Skipping {len(skipped_untestable)} untestable component(s) "
                    f"from docs/FAILED_COMPONENTS.md: {', '.join(skipped_untestable)}"
                )

    # Filter out excluded components
    if cli_args.exclude:
        excluded_ids = [c.strip() for c in cli_args.exclude.split(",")]
        target_components = [
            c for c in target_components if c.get("id") not in excluded_ids
        ]

    if not target_components:
        logger.info("No components matching criteria to test.")
        return 0

    # Ensure a local SSH key is generated to copy to the VMs/containers
    dummy_mgr = SSHManager(
        hostname="localhost", username="test", password="key"
    )  # nosec B106
    # noinspection PyProtectedMember
    ssh_key_obj = dummy_mgr._get_or_create_key()
    ssh_public_key = f"{ssh_key_obj.get_name()} {ssh_key_obj.get_base64()}"

    # Determine execution matrix
    engine_arg = (
        (getattr(cli_args, "engine", None) or os.getenv("CONTAINER_ENGINE") or "docker")
        .strip()
        .lower()
    )
    engines = ["docker", "podman"] if engine_arg in ("both", "all") else [engine_arg]
    if not engines or any(e not in ["docker", "podman"] for e in engines):
        engines = ["docker"]

    mode_arg = (getattr(cli_args, "mode", "lxc") or "lxc").strip().lower()
    modes = ["lxc", "vm"] if mode_arg in ("both", "all") else [mode_arg]
    if not modes or any(m not in ["lxc", "vm"] for m in modes):
        modes = ["lxc"]

    matrix = [(m, e) for m in modes for e in engines]

    logger.info("==================================================")
    if len(matrix) > 1:
        logger.info(f"STARTING MATRIX TEST RUN: {len(matrix)} ENVIRONMENTS")
        for idx, (m, e) in enumerate(matrix, 1):
            logger.info(
                f"  [{idx}/{len(matrix)}] Target: {m.upper()} | Engine: {e.upper()}"
            )
        logger.info(f"Total test executions: {len(matrix) * len(target_components)}")
    else:
        m, e = matrix[0]
        logger.info(f"EXECUTING TEST RUN(S): Mode={m.upper()} | Engine={e.upper()}")
        logger.info(f"Total components to test: {len(target_components)}")
    logger.info("==================================================")

    results_summary: List[Dict[str, Any]] = []

    for mode_item, engine_item in matrix:
        env_results = run_environment_tests(
            proxmox_client=proxmox_client,
            node=node,
            mode=mode_item,
            engine=engine_item,
            template_id=template_id,
            vm_user=vm_user,
            vm_pass=vm_pass,
            target_components=target_components,
            comp_mgr=comp_mgr,
            setup_output_dir=setup_output_dir,
            ssh_public_key=ssh_public_key,
        )
        results_summary.extend(env_results)

    # Check if any previously untestable/failed components passed verification
    # and automatically remove them from docs/FAILED_COMPONENTS.md
    for record in results_summary:
        if record.get("status") == "success":
            cid = record.get("component_id")
            if cid and is_component_untestable(cid, untestable_doc):
                removed = remove_untestable_component(cid, untestable_doc)
                if removed:
                    logger.info(
                        f"🎉 Component '{cid}' passed verification! "
                        "Automatically removed from docs/FAILED_COMPONENTS.md."
                    )

    failed_count = sum(
        1 for r in results_summary if r.get("status") not in ("success", "skipped")
    )
    skipped_count = sum(1 for r in results_summary if r.get("status") == "skipped")
    passed_count = sum(1 for r in results_summary if r.get("status") == "success")

    # Ensure output dirs exist
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)
    tests_dir = project_root / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Save cumulative JSON results history
    json_path = tests_dir / "proxmox_results.json"
    history: List[Dict[str, Any]] = []
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    history = loaded
        except Exception as read_ex:
            logger.warning(f"Could not load existing test results: {read_ex}")

    # Merge results_summary into history with deduplication based on unique test key
    for res_rec in results_summary:
        updated = False
        for idx, h_rec in enumerate(history):
            if (
                h_rec.get("component_id") == res_rec.get("component_id")
                and h_rec.get("timestamp") == res_rec.get("timestamp")
                and h_rec.get("mode") == res_rec.get("mode")
                and h_rec.get("engine") == res_rec.get("engine")
            ):
                history[idx] = res_rec
                updated = True
                break
        if not updated:
            history.append(res_rec)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)
        f.write("\n")
    logger.info(f"Saved test results history ({len(history)} entries) to: {json_path}")

    # Generate Markdown Report
    timestamp_fn = time.strftime("%Y%m%d_%H%M%S")
    if cli_args.components:
        comp_list = [c.strip() for c in cli_args.components.split(",") if c.strip()]
        if len(comp_list) > 3:
            comp_str = f"{comp_list[0]}_to_{comp_list[-1]}_{len(comp_list)}runs"
        else:
            comp_str = "_".join(comp_list)
        title_suffix = cli_args.components
        report_filename = f"PROXMOX_TESTS_{comp_str}_{timestamp_fn}.md"
    elif getattr(cli_args, "untested_ui", False):
        title_suffix = "untested_ui"
        report_filename = f"PROXMOX_TESTS_untested_ui_{timestamp_fn}.md"
    else:
        title_suffix = "all"
        report_filename = f"PROXMOX_TESTS_all_{timestamp_fn}.md"

    report_path = docs_dir / report_filename
    matrix_label = (
        f"MATRIX ({len(matrix)} envs)"
        if len(matrix) > 1
        else f"{matrix[0][1].upper()} ({matrix[0][0].upper()})"
    )
    write_markdown_report(
        report_path,
        results_summary,
        failed_count,
        title_suffix,
        engine=matrix_label,
    )
    logger.info(f"Saved human-readable markdown report to: {report_path}")

    # Send Signal Notification
    overall_status = "✅ ALL SUCCESSFUL" if failed_count == 0 else "❌ FAILED"

    envs_desc = ", ".join(f"{m.upper()}+{e.upper()}" for m, e in matrix)
    signal_msg = (
        f"🚢 NjordDeploy Proxmox Test Report\n"
        f"Environments: {envs_desc}\n"
        f"Status: {overall_status}\n"
        f"Total tested: {len(results_summary)}\n"
        f"Passed: {passed_count}\n"
        f"Skipped: {skipped_count}\n"
        f"Failed: {failed_count}"
    )
    if failed_count > 0:
        failed_list = [
            f"{r['component_id']} ({r.get('mode', 'LXC')}/{r.get('engine', 'DOCKER')})"
            for r in results_summary
            if r["status"] not in ("success", "skipped")
        ]
        signal_msg += f"\nFailed: {', '.join(failed_list)}"

    send_signal_message(signal_msg)

    # Perform AI batch diagnosis if enabled and failures occurred
    if failed_count > 0 and getattr(args, "ai_diagnose", False):
        try:
            logger.info("✨ Running Gemini AI Systemic Batch Failure Diagnosis...")
            from utils.ai_failure_diagnoser import AIFailureDiagnoser

            diagnoser = AIFailureDiagnoser()
            if diagnoser.is_configured():
                failed_recs = [r for r in results_summary if r["status"] != "success"]
                ai_result = diagnoser.diagnose_batch_failures(failed_recs)
                summary_text = ai_result.get("systemic_summary", "")
                logger.info(f"✨ AI Systemic Summary: {summary_text}")
                ai_md = [
                    "",
                    "## 🤖 Gemini AI Systemic Failure Diagnosis",
                    "",
                    f"**Systemic Summary:** {summary_text}",
                    "",
                ]
                for cl in ai_result.get("clusters", []):
                    cname = cl.get("cluster_name", "Issue")
                    ai_md.append(f"### Pattern: {cname}")
                    aff = ", ".join(cl.get("affected_tests", []))
                    ai_md.append(f"- **Affected:** {aff}")
                    ai_md.append(
                        f"- **Root Cause:** {cl.get('root_cause_explanation', '')}"
                    )
                    ai_md.append(
                        f"- **Recommended Action:** {cl.get('recommended_action', '')}"
                    )
                    ai_md.append("")
                with open(report_path, "a", encoding="utf-8") as f:
                    f.write("\n".join(ai_md) + "\n")
        except Exception as ai_ex:
            logger.warning(f"AI batch failure diagnosis failed: {ai_ex}")

    # Maintain copy at PROXMOX_TESTS.md
    latest_report_path = docs_dir / "PROXMOX_TESTS.md"
    try:
        if latest_report_path.exists():
            latest_report_path.unlink()
        import shutil

        shutil.copy2(report_path, latest_report_path)
    except Exception as sym_err:
        logger.warning(f"Could not copy latest report to PROXMOX_TESTS.md: {sym_err}")

    return failed_count


def write_markdown_report(
    report_path: Path,
    results: List[Dict[str, Any]],
    failed_count: int,
    title_suffix: str = "",
    engine: str = "docker",
):
    """Writes a clean, formatted Markdown report of the test outcomes."""
    total_count = len(results)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    title = "Proxmox Automated Component Testing Report"
    if title_suffix:
        title += f" - {title_suffix}"

    skipped_count = sum(1 for r in results if r.get("status") == "skipped")
    passed_count = sum(1 for r in results if r.get("status") == "success")

    md_lines = [
        f"# {title}",
        "",
        f"**Run Timestamp:** {timestamp}",
        (
            f"**Execution Profile:** `{engine}` | "
            f"**Total Tested:** {total_count} | "
            f"**Passed:** {passed_count} | "
            f"**Skipped:** {skipped_count} | "
            f"**Failed:** {failed_count}"
        ),
        "",
        "## Results Table",
        "",
        (
            "| Date / Time | Component ID | Target | Engine | VM ID | IP Address | "
            "Deployment | Containers | HTTP | Status |"
        ),
        ("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"),
    ]

    for record in results:
        if record["status"] == "success":
            status_emoji = "✅ PASS"
        elif record["status"] == "skipped":
            status_emoji = "⚠️ SKIPPED"
        else:
            status_emoji = "❌ FAIL"
        rec_mode = record.get("mode", "LXC").upper()
        rec_engine = record.get("engine", engine).upper()
        rec_time = record.get("timestamp") or timestamp
        http_val = (
            "N/A"
            if record["http_ok"] is None
            else ("OK" if record["http_ok"] else "FAIL")
        )
        md_lines.append(
            f"| {rec_time} | `{record['component_id']}` | `{rec_mode}` | "
            f"`{rec_engine}` | {record['vmid']} | {record['ip'] or 'N/A'} | "
            f"{record['deployment']} | "
            f"{'Running' if record['running'] else 'Stopped'} | "
            f"{http_val} | **{status_emoji}** |"
        )

    md_lines.append("")
    md_lines.append("## Details & Failures")
    md_lines.append("")

    has_failures = False
    for record in results:
        if record["status"] not in ("success", "skipped"):
            has_failures = True
            rec_mode = record.get("mode", "LXC").upper()
            rec_engine = record.get("engine", engine).upper()
            md_lines.append(
                f"### Component: `{record['component_id']}` ({rec_mode} + {rec_engine})"
            )
            md_lines.append(f"- **Target Mode:** `{rec_mode}`")
            md_lines.append(f"- **Engine:** `{rec_engine}`")
            md_lines.append(f"- **VMID:** {record['vmid']}")
            md_lines.append(f"- **IP:** {record['ip'] or 'N/A'}")
            md_lines.append(f"- **Deployment Outcome:** {record['deployment']}")
            md_lines.append("- **Error / Logs:**")
            md_lines.append("```")
            md_lines.append(record["error_message"] or "Unknown error")
            md_lines.append("```")
            md_lines.append("")

    if not has_failures:
        md_lines.append(
            "All components completed execution and verification successfully!"
        )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines).rstrip() + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Run automated integration tests for "
            "NjordDeploy components on Proxmox VE."
        )
    )
    parser.add_argument(
        "--components",
        type=str,
        help="Comma-separated list of component IDs to test. Defaults to all.",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Comma-separated list of component IDs to exclude from test run.",
    )
    parser.add_argument(
        "--template-id", type=str, help="VMID of the master template to clone."
    )
    parser.add_argument("--node", type=str, help="Proxmox node name.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["vm", "lxc", "both", "all"],
        default="lxc",
        help="Testing mode: 'lxc', 'vm', or 'both'/'all' (default: lxc)",
    )
    parser.add_argument(
        "--engine",
        type=str,
        choices=["docker", "podman", "both", "all"],
        default=os.getenv("CONTAINER_ENGINE", "docker"),
        help=(
            "Container engine: 'docker', 'podman', or 'both'/'all' " "(default: docker)"
        ),
    )
    parser.add_argument(
        "--untested-ui",
        action="store_true",
        help=(
            "Automatically test all components that have a UI "
            "and are not yet marked as 'tested'."
        ),
    )
    parser.add_argument(
        "--include-untestable",
        action="store_true",
        help=(
            "Include untestable/skipped components from docs/FAILED_COMPONENTS.md "
            "in the test run."
        ),
    )
    parser.add_argument(
        "--ai-diagnose",
        action="store_true",
        help=(
            "Use Gemini AI to analyze test failures and provide systemic "
            "architectural recommendations."
        ),
    )
    args = parser.parse_args()

    exit_code = run_proxmox_tests(args)
    sys.exit(0 if exit_code == 0 else 1)
