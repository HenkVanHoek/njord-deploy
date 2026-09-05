# scripts/proxmox_package_test_runner.py
import argparse
import base64
import json
import logging
import os
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests  # type: ignore
from dotenv import load_dotenv

# Ensure we can import from the 'src' root directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.component_manager import ComponentManager  # noqa: E402
from managers.deployment_manager import DeploymentManager  # noqa: E402
from managers.setup_manager import SetupManager  # noqa: E402
from managers.ssh_manager import SSHManager  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402 # type: ignore
from utils.screenshot_utils import capture_service_screenshot  # noqa: E402
from utils.security_utils import mask_passwords  # noqa: E402
from utils.template_header import update_template_header_content  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("proxmox_package_test_runner")

# Components that cannot be tested automatically due to hardware, registry,
# or pre-existing state requirements
SKIPPED_COMPONENTS = [
    "web-notepad",
    "zigbee2mqtt",
    "lora-service",
    "njorddeploy-service-maintenance",
    "gluetun",
]

# Test-specific environment variable overrides for ports that conflict with
# host OS services (e.g., local DNS resolvers)
TEST_PORT_OVERRIDES = {
    # Port 53 conflicts with systemd-resolved on host Linux/LXC
    "ADGUARDHOME_DNS_PORT_TCP": "5353",
    "ADGUARDHOME_DNS_PORT_UDP": "5353",
    "PIHOLE_DNS_PORT": "5353",
}


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


def verify_package_health(
    vm_ip: str,
    vm_user: str,
    vm_pass: str,
    package_components: List[Dict[str, Any]],
    comp_mgr: ComponentManager,
    engine: str = "docker",
    max_retries: int = 40,
    mode: str = "vm",
) -> Dict[str, Any]:
    """Runs SSH-based checks and optional HTTP requests to verify health.

    Checks all package components.
    """
    results: Dict[str, Any] = {
        "success": True,
        "components": {},
        "details": "",
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
        results["success"] = False
        results["details"] = f"SSH verification failed: {conn_msg}"
        return results

    try:
        # Check container status
        log_lines: List[str] = []

        def append_log(msg: str):
            log_lines.append(msg)

        # Determine container CLI binary (podman or docker)
        if engine.lower() in ("docker", "podman"):
            cont_cli = engine.lower()
        else:
            cli_detect_cmd = (
                "if command -v podman >/dev/null 2>&1; then echo 'podman'; "
                "else echo 'docker'; fi"
            )
            _, cli_out = ssh_mgr.execute_command(
                cli_detect_cmd,
                lambda x: None,
                check_exit_code=False,
            )
            cont_cli = (cli_out or "").strip() or "docker"

        sudo_pfx = "" if vm_user == "root" else f"echo '{vm_pass}' | sudo -S "
        user_pfx = (
            "XDG_RUNTIME_DIR=/run/user/$(id -u) "
            if cont_cli == "podman" and vm_user != "root"
            else ""
        )

        def _get_running_containers() -> List[str]:
            containers: List[str] = []
            # Check user namespace
            cmd_cont_ps = (
                f"{user_pfx}{cont_cli} ps -a --filter "
                "label=com.docker.compose.project=njorddeploy "
                "--format '{{.Names}} ({{.Status}})'"
            )
            cmd_exit, ps_out = ssh_mgr.execute_command(
                cmd_cont_ps,
                lambda x: None,
                check_exit_code=False,
            )

            if cmd_exit != 0 or not ps_out or not ps_out.strip():
                # Fallback without label filter if not tagged by compose
                fallback_ps = (
                    f"{user_pfx}{cont_cli} ps -a "
                    "--format '{{{{.Names}}}} ({{{{.Status}}}})'"
                )
                fallback_exit, fallback_out = ssh_mgr.execute_command(
                    fallback_ps,
                    lambda x: None,
                    check_exit_code=False,
                )
                if fallback_exit == 0 and fallback_out:
                    ps_out = fallback_out
                    cmd_exit = 0

            if cmd_exit == 0 and ps_out:
                containers.extend(
                    [line.strip() for line in ps_out.splitlines() if line.strip()]
                )

            # Check root namespace if non-root user (e.g. rootful Podman/Docker in VM)
            if vm_user != "root":
                root_ps = (
                    f"{sudo_pfx}{cont_cli} ps -a --filter "
                    "label=com.docker.compose.project=njorddeploy "
                    "--format '{{.Names}} ({{.Status}})'"
                )
                root_exit, root_out = ssh_mgr.execute_command(
                    root_ps,
                    lambda x: None,
                    check_exit_code=False,
                )
                if root_exit != 0 or not root_out or not root_out.strip():
                    fallback_root = (
                        f"{sudo_pfx}{cont_cli} ps -a "
                        "--format '{{{{.Names}}}} ({{{{.Status}}}})'"
                    )
                    _, fb_root_out = ssh_mgr.execute_command(
                        fallback_root,
                        lambda x: None,
                        check_exit_code=False,
                    )
                    if fb_root_out:
                        root_out = fb_root_out
                        root_exit = 0
                if root_exit == 0 and root_out:
                    containers.extend(
                        [line.strip() for line in root_out.splitlines() if line.strip()]
                    )

            return list(dict.fromkeys(containers))

        running_containers = _get_running_containers()
        overall_success = True
        component_status = {}

        for comp in package_components:
            comp_id = comp.get("id", "unknown")
            if hasattr(comp_mgr.reader, "get_docker_service_name"):
                svc_name = comp_mgr.reader.get_docker_service_name(comp_id)
            else:
                svc_name = comp_id

            # Find matching container running (exact/prefix matches prioritized)
            is_running = False
            matched_container = None
            candidates: List[tuple[str, str]] = []
            for container in running_containers:
                parts = container.split()
                if not parts:
                    continue
                cname, *rest = parts
                status_part = container[len(cname) :]
                if (
                    cname == svc_name
                    or cname == f"njorddeploy-{svc_name}"
                    or cname == comp_id
                    or cname == f"njorddeploy-{comp_id}"
                    or cname.endswith(f"-{svc_name}")
                ):
                    candidates.insert(0, (cname, status_part))
                elif svc_name in cname or comp_id in cname:
                    candidates.append((cname, status_part))

            if candidates:
                for cname, status_part in candidates:
                    if "Up" in status_part:
                        is_running = True
                        matched_container = cname
                        break
                if not matched_container:
                    cname, status_part = candidates[0]
                    matched_container = cname
                    is_running = "Up" in status_part

            # If not running immediately, retry up to 4 times for background sidecars
            if not is_running:
                for _ in range(4):
                    time.sleep(3)
                    running_containers = _get_running_containers()
                    candidates = []
                    for container in running_containers:
                        parts = container.split()
                        if not parts:
                            continue
                        cname, *rest = parts
                        status_part = container[len(cname) :]
                        if (
                            cname == svc_name
                            or cname == f"njorddeploy-{svc_name}"
                            or cname == comp_id
                            or cname == f"njorddeploy-{comp_id}"
                            or cname.endswith(f"-{svc_name}")
                        ):
                            candidates.insert(0, (cname, status_part))
                        elif svc_name in cname or comp_id in cname:
                            candidates.append((cname, status_part))

                    if candidates:
                        for cname, status_part in candidates:
                            if "Up" in status_part:
                                is_running = True
                                matched_container = cname
                                break
                    if is_running:
                        break

            comp_error_message = ""
            comp_http_ok: str | bool | None = None
            comp_logs_error = False
            comp_detected_version = None
            comp_record_screenshot: Optional[str] = None
            comp_record_url: Optional[str] = None

            if not is_running:
                comp_error_message = (
                    f"No running container found matching service '{svc_name}'."
                )
                if matched_container:
                    err_logs: List[str] = []
                    ssh_mgr.execute_command(
                        f"{sudo_pfx}{cont_cli} logs {matched_container} --tail 100",
                        lambda x: err_logs.append(x),
                        check_exit_code=False,
                    )
                    if err_logs:
                        comp_error_message += (
                            "\nLast 100 container logs:\n" + "\n".join(err_logs)
                        )
                overall_success = False
            else:
                # Check container logs for tracebacks or fatal errors
                comp_logs: List[str] = []
                ssh_mgr.execute_command(
                    f"{sudo_pfx}{cont_cli} logs {matched_container} --tail 100",
                    lambda x: comp_logs.append(x),
                    check_exit_code=False,
                )
                logs_content = "\n".join(comp_logs).lower()
                if "traceback" in logs_content or "fatal" in logs_content:
                    comp_logs_error = True

                # Inspect container config to get the actual version
                cmd_inspect = (
                    f"{sudo_pfx}{cont_cli} inspect {matched_container} "
                    "--format '{{{{json .Config}}}}'"
                )
                inspect_exit, inspect_out = ssh_mgr.execute_command(
                    cmd_inspect,
                    lambda x: None,
                    check_exit_code=False,
                )
                if inspect_exit == 0 and inspect_out is not None:
                    try:
                        config_data = json.loads(inspect_out.strip())
                        labels = config_data.get("Labels") or {}
                        env_list = config_data.get("Env") or []

                        # Check common version sources
                        ver: str | None = labels.get("org.opencontainers.image.version")
                        if not ver:
                            ver = labels.get("version")
                        if not ver:
                            for env in env_list:
                                if "=" in env:
                                    k, v = env.split("=", 1)
                                    if k.upper() in [
                                        "VERSION",
                                        "CADDY_VERSION",
                                        "RADARR_VERSION",
                                        "SONARR_VERSION",
                                        "HA_VERSION",
                                        "APP_VERSION",
                                    ]:
                                        ver = v
                                        break
                        if ver is not None:
                            comp_detected_version = ver.strip()
                    except Exception as inspect_ex:
                        logger.warning(
                            "Failed to parse docker inspect for "
                            f"{comp_id}: {inspect_ex}"
                        )

                # Check UI access if applicable
                if comp.get("has_ui", False):
                    ui_var = comp.get("ui_port_variable")
                    port = None
                    variables_list = comp_mgr.reader.get_component_variables(comp_id)
                    if ui_var:
                        for var in variables_list:
                            var_name = var.get("id") or var.get("name")
                            if var_name == ui_var:
                                port = var.get("default")
                                break
                    # Fallback to standard ports
                    if not port:
                        port = comp.get("traefik_internal_port")
                    if not port:
                        for var in variables_list:
                            if var.get("type") == "port":
                                port = var.get("default")
                                break

                    if port:
                        import urllib3

                        urllib3.disable_warnings(
                            urllib3.exceptions.InsecureRequestWarning
                        )
                        protocol = comp.get("protocol", "http")
                        url = f"{protocol}://{vm_ip}:{port}"
                        logger.info(
                            f"Probing HTTP UI for {comp_id} at {url} "
                            f"(retrying up to {max_retries} times)..."
                        )
                        probe_success = False
                        for attempt in range(1, max_retries + 1):
                            try:
                                res = requests.get(
                                    url, timeout=5, verify=False
                                )  # nosec B501
                                if res.status_code in [200, 301, 302, 401, 403]:
                                    comp_http_ok = True
                                    probe_success = True
                                    break
                                else:
                                    comp_http_ok = False
                                    if attempt < max_retries:
                                        time.sleep(5)
                            except Exception as ex:
                                comp_http_ok = False
                                if attempt == max_retries:
                                    comp_error_message += (
                                        f" HTTP Probe failed after {max_retries} "
                                        f"attempts: {ex}"
                                    )
                                else:
                                    time.sleep(5)

                        if not probe_success and comp_id in [
                            "adguard-home",
                            "adguardhome",
                        ]:
                            fallback_url = f"http://{vm_ip}:3000"
                            # noinspection PyBroadException
                            try:
                                res = requests.get(
                                    fallback_url, timeout=5, verify=False
                                )  # nosec B501
                                if res.status_code in [200, 301, 302, 401, 403]:
                                    comp_http_ok = True
                                    probe_success = True
                            except Exception:  # nosec B110
                                pass

                        if probe_success:
                            active_shot_url = (
                                fallback_url
                                if (
                                    comp_id in ["adguard-home", "adguardhome"]
                                    and res.status_code not in [200, 301, 302, 401, 403]
                                )
                                else url
                            )
                            comp_record_url = active_shot_url
                            try:
                                shot_dir = (
                                    project_root
                                    / "docs"
                                    / "images"
                                    / "test_screenshots"
                                )
                                shot_dir.mkdir(parents=True, exist_ok=True)
                                ts_clean = time.strftime("%Y%m%d_%H%M%S")
                                m_clean = mode.lower()
                                e_clean = engine.lower()
                                shot_fn = (
                                    f"pkg_{comp_id}_{m_clean}_{e_clean}_{ts_clean}.png"
                                )
                                shot_dest = shot_dir / shot_fn
                                logger.info(
                                    f"📸 Capturing Web UI screenshot for "
                                    f"{comp_id} at {active_shot_url}..."
                                )
                                captured_path = capture_service_screenshot(
                                    url=active_shot_url,
                                    output_path=shot_dest,
                                )
                                if captured_path and shot_dest.exists():
                                    comp_record_screenshot = (
                                        f"images/test_screenshots/{shot_fn}"
                                    )
                                    logger.info(
                                        f"📸 Screenshot saved: "
                                        f"{comp_record_screenshot}"
                                    )
                            except Exception as shot_ex:
                                logger.warning(
                                    f"Screenshot failed for {comp_id}: {shot_ex}"
                                )
                        else:
                            overall_success = False

            comp_record = {
                "running": is_running,
                "http_ok": comp_http_ok,
                "logs_error": comp_logs_error,
                "error_message": comp_error_message,
                "detected_version": comp_detected_version,
                "screenshot_path": comp_record_screenshot,
                "http_url": comp_record_url,
            }
            component_status[comp_id] = comp_record

        results["success"] = overall_success
        results["components"] = component_status
        results["details"] = (
            f"Successfully checked {len(package_components)} components."
        )

    finally:
        ssh_mgr.close()

    return results


def update_template_status(
    templates_path: Path,
    component_id: str,
    tested_version: str,
    mode: str,
    engine: str = "docker",
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
        logger.info(
            f"Updated template status headers for {component_id} "
            f"(mode: {mode}, engine: {engine}, version: {tested_version})"
        )
    except Exception as e:
        logger.error(f"Failed to update template status for {component_id}: {e}")


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


def resolve_dedicated_vm_template(
    proxmox_client: ProxmoxClient, node: str, engine: str, template_id: int
) -> Tuple[int, bool]:
    """Returns (effective_template_id, is_dedicated).

    Auto-selects dedicated VM template (911 for Docker, 913 for Podman).
    """
    target_id = 911 if engine.lower() == "docker" else 913
    if template_id == target_id:
        return target_id, True

    if template_id in (902, 911, 912, 913, 914):
        # noinspection PyBroadException
        try:
            qemu_vms = proxmox_client.get(f"nodes/{node}/qemu").get("data", [])
            for vm in qemu_vms:
                if vm.get("vmid") == target_id:
                    logger.info(
                        f"🚀 Auto-selected dedicated {engine.upper()} VM "
                        f"template ID {target_id} on '{node}'."
                    )
                    return target_id, True
        except Exception as e:
            logger.debug(f"Failed to check dedicated VM template: {e}")
    return template_id, False


def resolve_dedicated_lxc_template(
    proxmox_client: ProxmoxClient, node: str, engine: str
) -> Optional[int]:
    """Returns dedicated LXC template ID (912 for Docker, 914 for Podman)
    if it exists on the node.
    """
    target_id = 912 if engine.lower() == "docker" else 914
    # noinspection PyBroadException
    try:
        lxc_containers = proxmox_client.get(f"nodes/{node}/lxc").get("data", [])
        for ct in lxc_containers:
            if ct.get("vmid") == target_id:
                logger.info(
                    f"🚀 Auto-selected dedicated {engine.upper()} LXC "
                    f"template ID {target_id} on '{node}'."
                )
                return target_id
    except Exception as e:
        logger.debug(f"Failed to check dedicated LXC template: {e}")
    return None


def start_lxc(client: ProxmoxClient, node: str, vmid: int) -> dict:
    return client.post(f"nodes/{node}/lxc/{vmid}/status/start")


def stop_lxc(client: ProxmoxClient, node: str, vmid: int) -> dict:
    return client.post(f"nodes/{node}/lxc/{vmid}/status/stop")


def destroy_lxc(client: ProxmoxClient, node: str, vmid: int) -> dict:
    return client.delete(f"nodes/{node}/lxc/{vmid}", params={"purge": 1, "force": 1})


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


def _save_incremental_package_result(test_record: Dict[str, Any]) -> None:
    """Appends or updates a single package test result directly in
    tests/proxmox_package_results.json and updates PROXMOX_PACKAGE_TESTS.md.
    """
    try:
        tests_dir = project_root / "tests"
        tests_dir.mkdir(exist_ok=True)
        docs_dir = project_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        json_path = tests_dir / "proxmox_package_results.json"

        history: List[Dict[str, Any]] = []
        if json_path.exists():
            # noinspection PyBroadException
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        history = loaded
            except Exception as read_ex:
                logger.warning(f"Could not load existing test results: {read_ex}")

        clean_record = dict(test_record)
        for key in ("error_message", "details", "running_details"):
            if key in clean_record and isinstance(clean_record[key], str):
                clean_record[key] = mask_passwords(clean_record[key])

        updated = False
        for idx, rec in enumerate(history):
            if (
                rec.get("package_id") == clean_record.get("package_id")
                and (rec.get("mode") or "lxc") == (clean_record.get("mode") or "lxc")
                and (rec.get("engine") or "docker")
                == (clean_record.get("engine") or "docker")
            ):
                history[idx] = clean_record
                updated = True
                break

        if not updated:
            history.append(clean_record)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
            f.write("\n")

        # Write instance-specific markdown report
        inst_rep_fn = clean_record.get("report_file")
        if inst_rep_fn and inst_rep_fn != "PROXMOX_PACKAGE_TESTS.md":
            inst_path = docs_dir / inst_rep_fn
            inst_failed = 0 if clean_record.get("status") == "success" else 1
            write_markdown_report(inst_path, [clean_record], inst_failed)
            logger.info(f"Saved instance markdown report to: {inst_path}")

        latest_report_path = docs_dir / "PROXMOX_PACKAGE_TESTS.md"
        hist_failed = sum(1 for r in history if r.get("status") != "success")
        write_markdown_report(latest_report_path, history, hist_failed)
    except Exception as save_err:
        logger.warning(f"Failed to incrementally save package test result: {save_err}")


# Context object tracking active test VM/LXC for graceful teardown on interrupt
active_cleanup_target: Dict[str, Any] = {
    "client": None,
    "node": None,
    "vmid": None,
    "shared_lxc_vmid": None,
    "is_lxc": False,
}


def register_signal_handlers(client: ProxmoxClient, node: str) -> None:
    """Registers SIGINT and SIGTERM handlers to tear down test VMs on interrupt."""
    active_cleanup_target["client"] = client
    active_cleanup_target["node"] = node

    def _handle_signal(sig: int, _frame: Any) -> None:
        logger.warning(
            f"Received shutdown signal ({sig}). "
            "Performing immediate emergency teardown of active test instances..."
        )
        cli = active_cleanup_target.get("client")
        nod = active_cleanup_target.get("node")
        vmid = active_cleanup_target.get("vmid") or active_cleanup_target.get(
            "shared_lxc_vmid"
        )
        is_lxc = active_cleanup_target.get("is_lxc", False) or bool(
            active_cleanup_target.get("shared_lxc_vmid")
        )
        if isinstance(cli, ProxmoxClient) and isinstance(nod, str) and vmid:
            # noinspection PyBroadException
            try:
                logger.info(
                    f"Emergency cleanup: stopping & destroying "
                    f"{'LXC' if is_lxc else 'VM'} {vmid}..."
                )
                if is_lxc:
                    # noinspection PyBroadException
                    try:
                        stop_lxc(cli, nod, vmid)
                        time.sleep(1)
                    except Exception:  # nosec B110
                        pass
                    destroy_lxc(cli, nod, vmid)
                else:
                    # noinspection PyBroadException
                    try:
                        cli.stop_vm(nod, vmid)
                        time.sleep(1)
                    except Exception:  # nosec B110
                        pass
                    cli.destroy_vm(nod, vmid)
                logger.info(f"Emergency cleanup for {vmid} complete.")
            except Exception as e:
                logger.error(f"Error during emergency cleanup of {vmid}: {e}")

        if isinstance(cli, ProxmoxClient) and isinstance(nod, str):
            # noinspection PyBroadException
            try:
                cleanup_stale_test_instances(cli, nod)
            except Exception:  # nosec B110
                pass
        os._exit(130)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


def check_concurrent_runners() -> None:
    """Checks if another test runner is already running locally and warns."""
    # noinspection PyBroadException
    try:
        import psutil

        current_pid = os.getpid()
        active_runners = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            # noinspection PyBroadException
            try:
                p_info = proc.info
                p_pid = p_info["pid"]
                if p_pid == current_pid:
                    continue
                cmdline = " ".join(p_info.get("cmdline") or [])
                if (
                    "proxmox_package_test_runner.py" in cmdline
                    or "proxmox_test_runner.py" in cmdline
                ):
                    active_runners.append((p_pid, cmdline))
            except Exception:  # nosec B110
                pass

        if active_runners:
            for apid, acmd in active_runners:
                logger.warning(
                    f"⚠️ Concurrent runner detected (PID {apid}: {acmd}). "
                    "Running multiple sessions simultaneously may overload Proxmox."
                )
    except Exception as ps_err:
        logger.debug(f"psutil check skipped: {ps_err}")


def check_host_memory_headroom(
    client: ProxmoxClient, node: str, min_free_mb: int = 4096
) -> bool:
    """Verifies that the Proxmox host has at least `min_free_mb` MB free RAM available.

    Returns True if memory headroom is safe, False if dangerously low.
    """
    # noinspection PyBroadException
    try:
        status_res = client.get(f"nodes/{node}/status")
        data = status_res.get("data", {})
        mem = data.get("memory", {})
        free_bytes = mem.get("free", 0)
        total_bytes = mem.get("total", 0)
        used_bytes = mem.get("used", 0)
        available_bytes = total_bytes - used_bytes
        free_mb = available_bytes // (1024 * 1024)
        logger.info(
            f"Proxmox host '{node}' memory check: {free_mb} MB available "
            f"(free: {free_bytes // (1024*1024)} MB, "
            f"used: {used_bytes // (1024*1024)} MB "
            f"/ {total_bytes // (1024*1024)} MB)"
        )
        if free_mb < min_free_mb:
            logger.error(
                f"❌ DANGER: Proxmox host '{node}' has only {free_mb} MB available RAM "
                f"(safety threshold: {min_free_mb} MB). "
                "Aborting test launch to prevent OOM crash of host and operational VMs!"
            )
            return False
        return True
    except Exception as ex:
        logger.warning(f"Could not check host memory status: {ex}")
        return True


def cleanup_stale_test_instances(client: ProxmoxClient, node: str) -> None:
    """Finds and destroys any leftover test VMs or LXC containers from previous runs."""
    stale_prefixes = ("pish-test-", "pish-diag-", "njord-test-")
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
                # noinspection PyBroadException
                try:
                    client.stop_vm(node, vmid)
                    time.sleep(2)
                except Exception:  # nosec B110
                    pass
                # noinspection PyBroadException
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
        test_ips = ("10.99.0.199", "192.168.178.199")
        for lxc in lxcs:
            lxc_name = lxc.get("name", "")
            vmid = lxc.get("vmid")
            if not vmid or lxc.get("template"):
                continue

            is_stale = any(lxc_name.startswith(pfx) for pfx in stale_prefixes)
            if not is_stale and lxc_name.startswith("CT"):
                # Check if this CT has one of the dedicated test IPs
                # noinspection PyBroadException
                try:
                    cfg = client.get(f"nodes/{node}/lxc/{vmid}/config").get("data", {})
                    net0 = cfg.get("net0", "")
                    if any(f"ip={tip}" in net0 for tip in test_ips):
                        is_stale = True
                except Exception:  # nosec B110
                    pass

            if is_stale:
                logger.warning(
                    f"Found stale test LXC '{lxc_name}' (VMID: {vmid}). Cleaning up..."
                )
                # noinspection PyBroadException
                try:
                    stop_lxc(client, node, vmid)
                    time.sleep(2)
                except Exception:  # nosec B110
                    pass
                # noinspection PyBroadException
                try:
                    destroy_lxc(client, node, vmid)
                    logger.info(f"Stale test LXC {vmid} destroyed.")
                except Exception as ex:
                    logger.warning(f"Could not destroy stale test LXC {vmid}: {ex}")
    except Exception as ex:
        logger.warning(f"Error checking for stale test LXCs: {ex}")


def calculate_package_resources(
    package_id: str,
    package_components: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculates dynamically required RAM, CPU cores, disk and retry budget."""
    base_ram = 2048
    base_cores = 4
    extra_disk_gb = 10
    retry_budget = 40

    heavyweight_components: Dict[str, Dict[str, int]] = {
        "open-webui": {"ram": 4096, "cores": 4, "disk": 15, "retries": 65},
        "ollama": {"ram": 4096, "cores": 4, "disk": 15, "retries": 50},
        "litellm": {"ram": 2048, "cores": 2, "disk": 10, "retries": 45},
        "paperless-ngx": {"ram": 4096, "cores": 4, "disk": 15, "retries": 75},
        "stirling-pdf": {"ram": 3072, "cores": 4, "disk": 10, "retries": 60},
        "immich": {"ram": 4096, "cores": 4, "disk": 20, "retries": 65},
        "jellyfin": {"ram": 3072, "cores": 4, "disk": 15, "retries": 45},
        "nextcloud": {"ram": 3072, "cores": 4, "disk": 10, "retries": 45},
        "gitlab": {"ram": 4096, "cores": 4, "disk": 25, "retries": 65},
    }

    max_ram = base_ram
    max_cores = base_cores
    disk_increment = extra_disk_gb
    max_retries = retry_budget

    for comp in package_components:
        cid = comp.get("id", "")
        if cid in heavyweight_components:
            spec = heavyweight_components[cid]
            max_ram = max(max_ram, spec["ram"])
            max_cores = max(max_cores, spec["cores"])
            disk_increment = max(disk_increment, spec["disk"])
            max_retries = max(max_retries, spec["retries"])

    # If stack has 5+ components, allocate extra resources safely capped
    if len(package_components) >= 5:
        max_ram = max(max_ram, 3072)
        disk_increment = max(disk_increment, 15)
        max_retries = max(max_retries, 50)

    # Hard cap at 4096 MB to safeguard host memory & development workstation VM
    max_ram = min(max_ram, 4096)

    return {
        "ram": max_ram,
        "cores": max_cores,
        "extra_disk_gb": disk_increment,
        "max_retries": max_retries,
    }


def run_package_environment_tests(
    proxmox_client: ProxmoxClient,
    node: str,
    mode: str,
    engine: str,
    template_id: int,
    vm_user: str,
    vm_pass: str,
    target_packages: Dict[str, Any],
    comp_mgr: ComponentManager,
    setup_output_dir: Path,
    ssh_public_key: str,
    report_filename: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Runs tests for all target packages in a specific (mode, engine) environment."""
    is_lxc = mode.lower() == "lxc"
    all_components = comp_mgr.get_all_components()
    comp_map = {c.get("id"): c for c in all_components if c.get("id")}

    env_results: List[Dict[str, Any]] = []

    test_ip = os.getenv("PROXMOX_TEST_IP")
    bridge = os.getenv("PROXMOX_BRIDGE")
    if not bridge:
        bridge = "vmbr1" if (test_ip and "10.99." in test_ip) else "vmbr0"
    elif test_ip and "10.99." in test_ip and bridge == "vmbr0":
        bridge = "vmbr1"

    default_gw = "10.99.0.1" if (test_ip and "10.99." in test_ip) else "192.168.178.1"
    raw_gw = os.getenv("PROXMOX_GATEWAY")
    if not raw_gw or (test_ip and "10.99." in test_ip and "10.99." not in raw_gw):
        test_gw = default_gw
    else:
        test_gw = raw_gw
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

    # --- LXC shared container setup (provisioned once, reused for all packages) ---
    shared_lxc_vmid: int | None = None
    shared_lxc_ip: str | None = None

    if is_lxc:
        logger.info(
            f"LXC mode ({engine.upper()}): provisioning a shared container "
            "for all packages."
        )
        try:
            if not check_host_memory_headroom(proxmox_client, node, min_free_mb=3584):
                raise RuntimeError(
                    "Proxmox host memory is critically low (< 3.5 GB free). "
                    "Aborting LXC test setup to protect host and VMs."
                )
            shared_lxc_vmid = proxmox_client.get_next_vmid()
            active_cleanup_target["vmid"] = shared_lxc_vmid
            active_cleanup_target["shared_lxc_vmid"] = shared_lxc_vmid
            active_cleanup_target["is_lxc"] = True
            dedicated_lxc_id = resolve_dedicated_lxc_template(
                proxmox_client, node, engine
            )
            if dedicated_lxc_id:
                logger.info(
                    f"Cloning dedicated LXC template {dedicated_lxc_id} to "
                    f"shared container {shared_lxc_vmid} on node '{node}'..."
                )
                clone_res = proxmox_client.clone_lxc(
                    node=node,
                    vmid=dedicated_lxc_id,
                    newid=shared_lxc_vmid,
                    hostname=f"pish-test-pkg-{engine.lower()}",
                    full=True,
                )
                upid = clone_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(proxmox_client, node, upid)

                proxmox_client.configure_lxc(
                    node=node,
                    vmid=shared_lxc_vmid,
                    config_data={
                        "cores": 4,
                        "memory": 4096,
                        "swap": 512,
                        "net0": lxc_net,
                    },
                )
                if shared_lxc_vmid is None:
                    raise RuntimeError("Failed to allocate shared LXC VMID.")
                start_lxc(proxmox_client, node, shared_lxc_vmid)
            else:
                logger.info(
                    f"Creating shared LXC container {shared_lxc_vmid} "
                    f"on node '{node}'..."
                )
                ostemplate = find_suitable_lxc_template(proxmox_client, node)
                logger.info(f"Using template: {ostemplate}")

                create_data = {
                    "vmid": shared_lxc_vmid,
                    "ostemplate": ostemplate,
                    "hostname": f"pish-test-pkg-{engine.lower()}",
                    "cores": 4,
                    "memory": 4096,
                    "swap": 512,
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
                time.sleep(3)
            else:
                shared_lxc_ip = wait_for_lxc_ip(proxmox_client, node, shared_lxc_vmid)
            if shared_lxc_ip is None:
                raise RuntimeError("shared_lxc_ip is None in LXC mode")
            logger.info(f"LXC container {shared_lxc_vmid} online at {shared_lxc_ip}.")
            time.sleep(5)

            # Install engine manually on shared container only if created from scratch
            if not dedicated_lxc_id:
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
                        f"SSH attempt {attempt + 1}/6 failed: {conn_msg}. "
                        "Retrying in 5 seconds..."
                    )
                    time.sleep(5)
                if not connected:
                    raise RuntimeError(
                        f"Failed to SSH into shared LXC container: {conn_msg}"
                    )

                if engine == "docker":
                    for cmd in [
                        "apt-get update",
                        "apt-get install -y curl ca-certificates gnupg",
                        "curl -fsSL https://get.docker.com -o get-docker.sh",
                        "sh get-docker.sh",
                        "systemctl enable --now docker",
                    ]:
                        lxc_ssh.execute_command(cmd, lambda msg: None)
                else:
                    for cmd in [
                        "apt-get update",
                        "apt-get install -y podman podman-compose",
                    ]:
                        lxc_ssh.execute_command(cmd, lambda msg: None)

                lxc_ssh.close()
                logger.info(f"{engine.upper()} installed on shared LXC container.")

        except Exception as setup_err:
            logger.error(f"Failed to provision shared LXC container: {setup_err}")
            if shared_lxc_vmid:
                # noinspection PyBroadException
                try:
                    stop_lxc(proxmox_client, node, shared_lxc_vmid)
                    destroy_lxc(proxmox_client, node, shared_lxc_vmid)
                except Exception:  # nosec B110
                    pass
            return []

    try:
        clean_cli = "podman" if engine == "podman" else "docker"
        ssh_user = "root" if is_lxc else vm_user

        for pkg_id, pkg in target_packages.items():
            logger.info("========================================")
            logger.info(
                f"Testing package: {pkg_id} ({pkg.get('name')}) "
                f"[{mode.upper()} / {engine.upper()}]"
            )
            logger.info("========================================")

            # Find all components belonging to this package, excluding skipped ones
            explicit_cids = pkg.get("components")
            if isinstance(explicit_cids, list) and explicit_cids:
                package_components = [
                    comp_map[cid]
                    for cid in explicit_cids
                    if cid in comp_map and cid not in SKIPPED_COMPONENTS
                ]
            else:
                package_components = [
                    c
                    for c in all_components
                    if c.get("package_id") == pkg_id
                    and c.get("id") not in SKIPPED_COMPONENTS
                ]
            if not package_components:
                logger.warning(f"No components found for package {pkg_id}. Skipping.")
                continue

            pkg_res = calculate_package_resources(pkg_id, package_components)
            logger.info(
                f"Sizing profile for stack '{pkg_id}': "
                f"{pkg_res['ram']}MB RAM, {pkg_res['cores']} Cores, "
                f"+{pkg_res['extra_disk_gb']}GB Disk, "
                f"{pkg_res['max_retries']} Retries"
            )

            ts_inst = time.strftime("%Y%m%d_%H%M%S")
            inst_report_filename = (
                f"PROXMOX_PACKAGE_TESTS_{pkg_id}_{mode.lower()}_"
                f"{engine.lower()}_{ts_inst}.md"
            )

            test_record: Dict[str, Any] = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "package_id": pkg_id,
                "package_name": pkg.get("name"),
                "status": "failed",
                "mode": mode.lower(),
                "engine": engine.lower(),
                "vmid": shared_lxc_vmid if is_lxc else None,
                "ip": shared_lxc_ip if is_lxc else None,
                "deployment": "failed",
                "components": {},
                "report_file": inst_report_filename,
                "error_message": "",
            }

            new_vmid: int | None = None
            vm_ip: str | None = shared_lxc_ip if is_lxc else None
            is_dedicated_vm = False

            try:
                if is_lxc:
                    # Clean engine state between packages
                    logger.info(
                        f"Cleaning {engine.upper()} environment before testing "
                        f"package {pkg_id}..."
                    )
                    cleanup_ssh = SSHManager(
                        hostname=vm_ip,
                        username=ssh_user,
                        password=vm_pass,
                        allow_auto_add=True,
                        load_system_keys=False,
                    )
                    cleanup_connected = False
                    for attempt in range(6):
                        cleanup_connected, _ = cleanup_ssh.connect()
                        if cleanup_connected:
                            break
                        time.sleep(3)
                    if not cleanup_connected:
                        raise RuntimeError(
                            f"Cannot connect to shared LXC container {vm_ip} "
                            "for cleanup."
                        )

                    cleanup_script = (
                        f"running_c=$({clean_cli} ps -q 2>/dev/null); "
                        f'if [ -n "$running_c" ]; then {clean_cli} stop $running_c '
                        "2>/dev/null || true; fi; "
                        f"all_c=$({clean_cli} ps -aq 2>/dev/null); "
                        f'if [ -n "$all_c" ]; then {clean_cli} rm -f $all_c '
                        "2>/dev/null || true; fi; "
                        f"{clean_cli} system prune -af --volumes 2>/dev/null || true; "
                        f"{clean_cli} network inspect njorddeploy_net "
                        ">/dev/null 2>&1 || "
                        f"{clean_cli} network create njorddeploy_net "
                        "2>/dev/null || true; "
                        "mkdir -p /tmp/.ansible && "
                        "chmod 1777 /tmp/.ansible 2>/dev/null || true; "
                        "mkdir -p /etc/docker 2>/dev/null || true; "
                        'printf \'{\\n  "dns": ["1.1.1.1", "8.8.8.8"],\\n'
                        '  "registry-mirrors": ["http://10.99.0.2:5000"],\\n'
                        '  "insecure-registries": ["10.99.0.2:5000"]\\n}\\n\' '
                        "> /etc/docker/daemon.json 2>/dev/null || true; "
                        "mkdir -p /etc/containers/registries.conf.d "
                        "2>/dev/null || true; "
                        'printf \'[[registry]]\\nprefix = "docker.io"\\n'
                        'location = "docker.io"\\n\\n'
                        '[[registry.mirror]]\\nlocation = "10.99.0.2:5000"\\n'
                        "insecure = true\\n' "
                        "> /etc/containers/registries.conf.d/mirror.conf "
                        "2>/dev/null || true; "
                        "rm -rf /opt/njorddeploy/* 2>/dev/null || true"
                    )
                    b64_clean = base64.b64encode(cleanup_script.encode("utf-8")).decode(
                        "ascii"
                    )
                    cleanup_ssh.execute_command(
                        f"bash -c 'echo {b64_clean} | base64 -d | bash'",
                        lambda msg: None,
                        check_exit_code=False,
                    )
                    cleanup_ssh.close()
                    logger.info(f"{engine.upper()} environment clean.")

                else:
                    if not check_host_memory_headroom(
                        proxmox_client, node, min_free_mb=3584
                    ):
                        raise RuntimeError(
                            f"Proxmox host memory is critically low (< 3.5 GB free). "
                            f"Aborting test of stack '{pkg_id}' to protect host."
                        )
                    # VM Mode: Clone a fresh VM from template
                    new_vmid = proxmox_client.get_next_vmid()
                    active_cleanup_target["vmid"] = new_vmid
                    active_cleanup_target["is_lxc"] = False
                    test_record["vmid"] = new_vmid
                    eff_vm_template, is_dedicated_vm = resolve_dedicated_vm_template(
                        proxmox_client, node, engine, template_id
                    )
                    logger.info(
                        f"Cloning VM template {eff_vm_template} to new VMID "
                        f"{new_vmid} (package: {pkg_id}, engine: {engine.upper()})..."
                    )
                    try:
                        clone_res = proxmox_client.clone_vm(
                            node=node,
                            vmid=eff_vm_template,
                            newid=new_vmid,
                            name=f"pish-test-{pkg_id}",
                            full=False,
                        )
                        upid = clone_res.get("data")
                        if isinstance(upid, str):
                            wait_for_proxmox_task(proxmox_client, node, upid)
                    except Exception as clone_err:
                        if "Linked clone feature is not supported" in str(clone_err):
                            logger.warning(
                                "Linked clone not supported, falling back to full."
                            )
                            clone_res = proxmox_client.clone_vm(
                                node=node,
                                vmid=eff_vm_template,
                                newid=new_vmid,
                                name=f"pish-test-{pkg_id}",
                                full=True,
                            )
                            upid = clone_res.get("data")
                            if isinstance(upid, str):
                                wait_for_proxmox_task(proxmox_client, node, upid)
                        else:
                            raise

                    import urllib.parse

                    conf_res = proxmox_client.configure_vm(
                        node=node,
                        vmid=new_vmid,
                        config_data={
                            "memory": pkg_res["ram"],
                            "cores": pkg_res["cores"],
                            "ciuser": vm_user,
                            "cipassword": vm_pass,
                            "sshkeys": urllib.parse.quote(ssh_public_key),
                            "ipconfig0": vm_ipconfig,
                            "nameserver": os.getenv(
                                "PROXMOX_NAMESERVER", "1.1.1.1 8.8.8.8"
                            ),
                            "agent": "enabled=1",
                            "net0": vm_net,
                        },
                    )
                    upid = conf_res.get("data")
                    if isinstance(upid, str):
                        wait_for_proxmox_task(proxmox_client, node, upid)

                    # noinspection PyBroadException
                    try:
                        proxmox_client.resize_vm_disk(
                            node=node,
                            vmid=new_vmid,
                            disk="scsi0",
                            size=f"+{pkg_res['extra_disk_gb']}G",
                        )
                        logger.info(
                            f"Expanded disk on VM {new_vmid} "
                            f"(+{pkg_res['extra_disk_gb']}G) for stack '{pkg_id}'."
                        )
                    except Exception as resize_err:
                        logger.warning(f"Could not resize VM disk: {resize_err}")

                    proxmox_client.start_vm(node=node, vmid=new_vmid)
                    if new_vmid is None:
                        raise RuntimeError("new_vmid is None")

                    # Wait for guest agent to report IP and verify VM has booted
                    discovered_ip = wait_for_ip(
                        proxmox_client, node, new_vmid, timeout_seconds=120
                    )
                    if clean_ip:
                        vm_ip = clean_ip
                        logger.info(
                            f"Using configured static IP for VM: {vm_ip} "
                            f"(guest agent reported: {discovered_ip})"
                        )
                    else:
                        vm_ip = discovered_ip

                    if not vm_ip:
                        raise TimeoutError(
                            "Unable to retrieve IP address for cloned VM."
                        )
                    test_record["vmid"] = new_vmid
                    test_record["ip"] = vm_ip
                    logger.info(f"VM {new_vmid} online at {vm_ip}.")
                    time.sleep(3)

                    logger.info(
                        f"Waiting for SSH daemon to become ready on VM {vm_ip}..."
                    )
                    vm_ssh = SSHManager(
                        hostname=vm_ip,
                        username=vm_user,
                        password=vm_pass,
                        allow_auto_add=True,
                        load_system_keys=False,
                    )
                    connected = False
                    conn_msg = ""
                    for attempt in range(15):
                        connected, conn_msg = vm_ssh.connect()
                        if connected:
                            break
                        time.sleep(5)
                    if not connected:
                        raise TimeoutError(
                            f"Could not connect via SSH to VM {vm_ip}: {conn_msg}"
                        )

                    # Prepare VM environment: DNS, Registry Mirror, apt locks, disk
                    sudo_pfx = (
                        "" if vm_user == "root" else f"echo '{vm_pass}' | sudo -S "
                    )
                    vm_init_script = (
                        "#!/usr/bin/env bash\n"
                        "set -e\n"
                        "if command -v cloud-init >/dev/null 2>&1; then "
                        "cloud-init status --wait || true; fi\n"
                        "systemctl stop systemd-resolved 2>/dev/null || true\n"
                        "systemctl disable systemd-resolved 2>/dev/null || true\n"
                        "chattr -i /etc/resolv.conf 2>/dev/null || true\n"
                        "rm -f /etc/resolv.conf\n"
                        "printf 'nameserver 1.1.1.1\\nnameserver 8.8.8.8\\n' "
                        "> /etc/resolv.conf\n"
                        "chattr +i /etc/resolv.conf 2>/dev/null || true\n"
                        "mkdir -p /etc/docker 2>/dev/null || true\n"
                        'printf \'{\\n  "dns": ["1.1.1.1", "8.8.8.8"],\\n'
                        '  "registry-mirrors": ["http://10.99.0.2:5000"],\\n'
                        '  "insecure-registries": ["10.99.0.2:5000"]\\n}\\n\' '
                        "> /etc/docker/daemon.json 2>/dev/null || true\n"
                        "mkdir -p /etc/containers/registries.conf.d "
                        "2>/dev/null || true\n"
                        'printf \'[[registry]]\\nprefix = "docker.io"\\n'
                        'location = "docker.io"\\n\\n'
                        '[[registry.mirror]]\\nlocation = "10.99.0.2:5000"\\n'
                        "insecure = true\\n' "
                        "> /etc/containers/registries.conf.d/mirror.conf "
                        "2>/dev/null || true\n"
                        "systemctl restart docker 2>/dev/null || true\n"
                        "mkdir -p /tmp/.ansible && chmod 1777 /tmp/.ansible\n"
                        "systemctl stop apt-daily.service apt-daily-upgrade.service "
                        "apt-daily.timer apt-daily-upgrade.timer "
                        "unattended-upgrades.service 2>/dev/null || true\n"
                        "systemctl disable --now apt-daily.timer "
                        "apt-daily-upgrade.timer "
                        "unattended-upgrades.service 2>/dev/null || true\n"
                        "systemctl kill --kill-who=all apt-daily.service "
                        "apt-daily-upgrade.service unattended-upgrades.service "
                        "2>/dev/null || true\n"
                        "while fuser /var/lib/dpkg/lock-frontend "
                        "/var/lib/dpkg/lock /var/lib/apt/lists/lock "
                        "/var/cache/apt/archives/lock >/dev/null 2>&1; do "
                        "sleep 2; done\n"
                        "growpart /dev/sda 1 2>/dev/null || true\n"
                        "resize2fs /dev/sda1 2>/dev/null || true\n"
                    )
                    b64_init = base64.b64encode(vm_init_script.encode("utf-8")).decode(
                        "ascii"
                    )
                    logger.info(
                        "Initializing VM environment (DNS, registry mirror, "
                        "apt locks, disk)..."
                    )
                    vm_ssh.execute_command(
                        f"{sudo_pfx}bash -c 'echo {b64_init} | base64 -d | bash'",
                        lambda msg: None,
                        check_exit_code=False,
                    )

                    vm_ssh.close()

                # Build configuration package locally
                logger.info(
                    f"Generating deployment configurations for package {pkg_id}..."
                )
                folder_vmid = shared_lxc_vmid if is_lxc else new_vmid
                pkg_output_dir = (
                    setup_output_dir / str(folder_vmid) / pkg_id
                ).resolve()
                setup_mgr = SetupManager(
                    component_manager=comp_mgr.reader, output_dir=pkg_output_dir
                )
                setup_mgr.initialize_environment()

                all_selected_ids = [
                    c.get("id") for c in package_components if c.get("id")
                ]
                for comp in package_components:
                    dependencies = comp.get("depends_on", [])
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

                user_vars["PISelfhosting_HOST_IP"] = vm_ip
                user_vars["CONTAINER_ENGINE"] = engine.lower()
                user_vars["TARGET_MODE"] = mode.lower()
                user_vars["container_engine"] = engine.lower()
                user_vars["target_mode"] = mode.lower()
                user_vars["DATA_ROOT"] = "/opt/njorddeploy/data"

                success, errors = setup_mgr.prepare_deployment_package(
                    selected_components=all_selected_ids,
                    user_variables=user_vars,
                    managed_devices=[{"ip": vm_ip}],
                )
                if not success:
                    raise RuntimeError(
                        f"Failed to prepare deployment package: {errors}"
                    )

                if engine.lower() == "podman":
                    user_vars["PODMAN_ROOTFUL"] = True

                comp_mgr.generate_deployment_artifacts(
                    selected_components_data=all_selected_data,
                    global_vars=user_vars,
                    output_path=pkg_output_dir,
                )

                # Deploy via Ansible
                logger.info(
                    f"Executing Ansible deployment of package {pkg_id} to {vm_ip}..."
                )
                deploy_mgr = DeploymentManager(component_manager=comp_mgr)
                run_vmid = shared_lxc_vmid if is_lxc else new_vmid
                task_id = f"test-pkg-{pkg_id}-{run_vmid}"
                tasks_dict = {task_id: {"logs": [], "status": "pending"}}

                is_rootful = is_lxc or (
                    engine.lower() == "podman"
                    and any(bool(c.get("requires_root")) for c in all_selected_data)
                )
                skip_prov = bool(is_lxc or is_dedicated_vm)
                deploy_mgr.start_deployment(
                    task_id=task_id,
                    tasks=tasks_dict,
                    output_path=str(pkg_output_dir),
                    devices=[
                        {
                            "ip": vm_ip,
                            "username": ssh_user,
                            "password": vm_pass,
                            "container_engine": engine.lower(),
                            "podman_rootful": is_rootful,
                            "skip_engine_provisioning": skip_prov,
                        }
                    ],
                    selected_components_data=all_selected_data,
                    global_vars=user_vars,
                )

                task_outcome: Dict[str, Any] = tasks_dict.get(task_id, {})
                if task_outcome.get("status") == "completed":
                    test_record["deployment"] = "success"
                    logger.info("Ansible package deployment completed successfully.")
                else:
                    test_record["deployment"] = "failed"
                    errors_list: List[Dict[str, Any]] = task_outcome.get("errors", [])
                    first_error: Dict[str, Any] = next(iter(errors_list), {})
                    err_details = first_error.get(
                        "details", "Ansible package execution error"
                    )
                    raise RuntimeError(f"Package deployment failed: {err_details}")

                # Health verification
                logger.info(
                    "Running health verification probes for all package components..."
                )
                if not isinstance(vm_ip, str):
                    raise RuntimeError("vm_ip is None")
                health_results = verify_package_health(
                    vm_ip=vm_ip,
                    vm_user=ssh_user,
                    vm_pass=vm_pass,
                    package_components=package_components,
                    comp_mgr=comp_mgr,
                    engine=engine,
                    max_retries=pkg_res["max_retries"],
                    mode=mode,
                )

                test_record["components"] = health_results["components"]
                if health_results["success"]:
                    test_record["status"] = "success"
                    logger.info(
                        f"✅ Package {pkg_id} verified successfully! "
                        f"[{mode.upper()} / {engine.upper()}]"
                    )

                    for comp in package_components:
                        cid = comp.get("id")
                        cstatus = health_results["components"].get(cid, {})
                        ver = cstatus.get("detected_version") or comp.get(
                            "default_version", "latest"
                        )
                        update_template_status(
                            templates_path=project_root / "component_templates",
                            component_id=cid,
                            tested_version=ver,
                            mode=mode,
                            engine=engine,
                        )
                else:
                    test_record["status"] = "failed"
                    test_record["error_message"] = health_results["details"]
                    logger.error(
                        f"❌ Package verification failed for {pkg_id} "
                        f"[{mode.upper()} / {engine.upper()}]: "
                        f"{health_results['details']}"
                    )

            except Exception as ex:
                logger.error(
                    f"❌ Error during test of package {pkg_id} "
                    f"[{mode.upper()} / {engine.upper()}]: {ex}"
                )
                test_record["status"] = "failed"
                test_record["error_message"] = str(ex)
            finally:
                active_cleanup_target["vmid"] = None
                if not is_lxc and new_vmid:
                    logger.info(f"Stopping and destroying VM {new_vmid}...")
                    # noinspection PyBroadException
                    try:
                        stop_res = proxmox_client.stop_vm(node, new_vmid)
                        upid = stop_res.get("data")
                        if isinstance(upid, str):
                            wait_for_proxmox_task(proxmox_client, node, upid)
                    except Exception as stop_err:
                        logger.warning(
                            f"Note: Could not stop VM {new_vmid} "
                            f"(may already be stopped): {stop_err}"
                        )
                    # noinspection PyBroadException
                    try:
                        destroy_res = proxmox_client.destroy_vm(node, new_vmid)
                        upid = destroy_res.get("data")
                        if isinstance(upid, str):
                            wait_for_proxmox_task(proxmox_client, node, upid)
                        logger.info(f"VM {new_vmid} destroyed.")
                    except Exception as teardown_err:
                        logger.error(f"Failed to destroy VM {new_vmid}: {teardown_err}")

                # Cleanup local output folder
                folder_vmid = shared_lxc_vmid if is_lxc else new_vmid
                if folder_vmid:
                    pkg_output_dir = setup_output_dir / str(folder_vmid) / pkg_id
                    if pkg_output_dir.exists():
                        shutil.rmtree(pkg_output_dir)

            env_results.append(test_record)
            _save_incremental_package_result(test_record)

    finally:
        active_cleanup_target["vmid"] = None
        active_cleanup_target["shared_lxc_vmid"] = None
        if is_lxc and shared_lxc_vmid:
            logger.info(f"Destroying shared LXC container {shared_lxc_vmid}...")
            # noinspection PyBroadException
            try:
                status_info = proxmox_client.get(
                    f"nodes/{node}/lxc/{shared_lxc_vmid}/status/current"
                )
                ct_status = status_info.get("data", {}).get("status")
                if ct_status == "running":
                    logger.info(f"Stopping LXC container {shared_lxc_vmid}...")
                    stop_res = stop_lxc(proxmox_client, node, shared_lxc_vmid)
                    upid = stop_res.get("data")
                    if isinstance(upid, str):
                        wait_for_proxmox_task(proxmox_client, node, upid)
            except Exception as stop_err:
                logger.warning(
                    f"Note: Could not stop LXC container {shared_lxc_vmid} "
                    f"(may already be stopped): {stop_err}"
                )

            # noinspection PyBroadException
            try:
                destroy_res = destroy_lxc(proxmox_client, node, shared_lxc_vmid)
                upid = destroy_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(proxmox_client, node, upid)
                logger.info(
                    f"Shared LXC container {shared_lxc_vmid} destroyed successfully."
                )
            except Exception as teardown_err:
                logger.warning(
                    "Failed to destroy shared LXC container "
                    f"{shared_lxc_vmid}: {teardown_err}"
                )

    return env_results


def run_proxmox_package_tests(cli_args) -> int:
    """Orchestrates package testing across requested environments."""
    load_dotenv(project_root / ".env", override=True)
    proxmox_client = setup_proxmox_client()

    node = cli_args.node or os.getenv("PROXMOX_NODE") or "pve"
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

    # 1. Check for concurrent runners to prevent overloading Proxmox
    check_concurrent_runners()

    # 2. Register interrupt signal handlers for graceful VM teardown
    register_signal_handlers(proxmox_client, node)

    # 3. Purge any orphaned test VMs/LXCs from previous runs or crashes
    cleanup_stale_test_instances(proxmox_client, node)

    # 4. Enforce physical host memory headroom safety threshold
    if not check_host_memory_headroom(proxmox_client, node, min_free_mb=3584):
        logger.error(
            "Proxmox host memory is critically low (< 3.5 GB free). "
            "Aborting test run to protect host and operational VMs."
        )
        return 1

    metadata_path = project_root / "config" / "components_metadata.json"
    templates_path = project_root / "component_templates"

    comp_mgr = ComponentManager(
        metadata_file_path=str(metadata_path), templates_path=str(templates_path)
    )
    setup_output_dir = project_root / "tmp_proxmox_package_test"

    all_packages = comp_mgr.get_all_packages()

    target_packages = {}
    if cli_args.packages:
        selected_ids = [p.strip() for p in cli_args.packages.split(",")]
        for pkg_id, pkg_data in all_packages.items():
            if pkg_id in selected_ids:
                target_packages[pkg_id] = pkg_data
    else:
        target_packages = all_packages.copy()

    if cli_args.exclude:
        excluded_ids = [p.strip() for p in cli_args.exclude.split(",")]
        for pkg_id in excluded_ids:
            target_packages.pop(pkg_id, None)

    if not target_packages:
        logger.info("No packages matching criteria to test.")
        return 0

    dummy_mgr = SSHManager(
        hostname="localhost", username="test", password="key"
    )  # nosec B106
    # noinspection PyProtectedMember
    ssh_key_obj = dummy_mgr._get_or_create_key()
    ssh_public_key = f"{ssh_key_obj.get_name()} {ssh_key_obj.get_base64()}"

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
        logger.info(f"STARTING PACKAGE MATRIX TEST RUN: {len(matrix)} ENVIRONMENTS")
        for idx, (m, e) in enumerate(matrix, 1):
            logger.info(
                f"  [{idx}/{len(matrix)}] Target: {m.upper()} | Engine: {e.upper()}"
            )
        logger.info(f"Total test executions: {len(matrix) * len(target_packages)}")
    else:
        m, e = matrix[0]
        logger.info(
            f"EXECUTING PACKAGE TEST RUN(S): Mode={m.upper()} | Engine={e.upper()}"
        )
        logger.info(f"Total packages to test: {len(target_packages)}")
    logger.info("==================================================")

    # Determine report filename
    timestamp_fn = time.strftime("%Y%m%d_%H%M%S")
    if cli_args.packages:
        pkg_list = [p.strip() for p in cli_args.packages.split(",") if p.strip()]
        if len(pkg_list) > 3:
            pkg_str = f"{pkg_list[0]}_to_{pkg_list[-1]}_{len(pkg_list)}runs"
        else:
            pkg_str = "_".join(pkg_list)
        report_filename = f"PROXMOX_PACKAGE_TESTS_{pkg_str}_{timestamp_fn}.md"
    else:
        report_filename = f"PROXMOX_PACKAGE_TESTS_all_{timestamp_fn}.md"

    logger.info(f"Report filename: {report_filename}")

    results_summary: List[Dict[str, Any]] = []

    for mode_item, engine_item in matrix:
        logger.info(
            f"Target Environment: {mode_item.upper()} | Engine: {engine_item.upper()}"
        )
        env_results = run_package_environment_tests(
            proxmox_client=proxmox_client,
            node=node,
            mode=mode_item,
            engine=engine_item,
            template_id=template_id,
            vm_user=vm_user,
            vm_pass=vm_pass,
            target_packages=target_packages,
            comp_mgr=comp_mgr,
            setup_output_dir=setup_output_dir,
            ssh_public_key=ssh_public_key,
            report_filename=report_filename,
        )
        results_summary.extend(env_results)

    failed_count = sum(1 for r in results_summary if r.get("status") != "success")

    # Ensure output dirs exist
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)

    report_path = docs_dir / report_filename
    write_markdown_report(report_path, results_summary, failed_count)
    logger.info(f"Saved human-readable markdown report to: {report_path}")

    # Send Signal Notification
    overall_status = "✅ ALL SUCCESSFUL" if failed_count == 0 else "❌ FAILED"
    passed_count = len(results_summary) - failed_count

    signal_msg = (
        f"🚢 NjordDeploy Proxmox Package Test Report\n"
        f"Status: {overall_status}\n"
        f"Total packages tested: {len(results_summary)}\n"
        f"Passed: {passed_count}\n"
        f"Failed: {failed_count}"
    )
    if failed_count > 0:
        failed_list = [
            f"{r['package_id']} ({r.get('mode')})"
            for r in results_summary
            if r["status"] != "success"
        ]
        signal_msg += f"\nFailed: {', '.join(failed_list)}"

    send_signal_message(signal_msg)

    return failed_count


def write_markdown_report(
    report_path: Path,
    results: List[Dict[str, Any]],
    failed_count: int,
):
    """Writes a clean, formatted Markdown report of the package test outcomes."""
    total_count = len(results)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    title = "Proxmox Automated Package Testing Report"

    md_lines = [
        f"# {title}",
        "",
        f"**Run Timestamp:** {timestamp}",
        (
            f"**Total Packages Tested:** {total_count} | "
            f"**Passed:** {total_count - failed_count} | "
            f"**Failed:** {failed_count}"
        ),
        "",
        "## Packages Summary Table",
        "",
        (
            "| Package ID | Package Name | Target | Engine | "
            "VM ID | IP Address | Deployment | Status |"
        ),
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for record in results:
        mode_val = (record.get("mode") or "lxc").upper()
        engine_val = (record.get("engine") or "docker").upper()
        status_emoji = "✅ PASS" if record["status"] == "success" else "❌ FAIL"
        md_lines.append(
            f"| `{record['package_id']}` | {record['package_name']} | "
            f"{mode_val} | {engine_val} | "
            f"{record['vmid']} | {record['ip'] or 'N/A'} | "
            f"{record['deployment']} | **{status_emoji}** |"
        )

    md_lines.append("")
    md_lines.append("## Detailed Components Verification Status")
    md_lines.append("")

    for record in results:
        mode_val = (record.get("mode") or "lxc").upper()
        engine_val = (record.get("engine") or "docker").upper()
        md_lines.append(
            f"### Package: `{record['package_id']}` ({record['package_name']})"
        )
        md_lines.append(f"- **Target:** {mode_val} | **Engine:** {engine_val}")
        md_lines.append(f"- **VMID:** {record['vmid']}")
        md_lines.append(f"- **IP:** {record['ip'] or 'N/A'}")
        md_lines.append(f"- **Deployment:** {record['deployment']}")
        md_lines.append(
            f"- **Overall Status:** "
            f"{'✅ PASS' if record['status'] == 'success' else '❌ FAIL'}"
        )

        components_data = record.get("components", {})
        if components_data:
            md_lines.append("")
            md_lines.append("#### Component Health Status:")
            md_lines.append("")
            md_lines.append(
                "| Component ID | Container Running | HTTP UI Port | "
                "Log Error (Traceback/Fatal) | Version | Status |"
            )
            md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

            for comp_id, comp_record in components_data.items():
                running = "Running" if comp_record.get("running") else "Stopped"
                http_val = (
                    "N/A"
                    if comp_record.get("http_ok") is None
                    else ("OK" if comp_record.get("http_ok") else "FAIL")
                )
                log_err = "Yes ❌" if comp_record.get("logs_error") else "None"
                ver = comp_record.get("detected_version") or "unknown"
                comp_status = (
                    "✅ OK"
                    if comp_record.get("running")
                    and (
                        comp_record.get("http_ok") is None or comp_record.get("http_ok")
                    )
                    else "❌ FAILED"
                )

                md_lines.append(
                    f"| `{comp_id}` | {running} | {http_val} | "
                    f"{log_err} | {ver} | {comp_status} |"
                )

            pkg_shots = [
                (cid, crec)
                for cid, crec in components_data.items()
                if crec.get("screenshot_path")
            ]
            if pkg_shots:
                md_lines.append("")
                md_lines.append("#### Web UI Screenshots:")
                md_lines.append("")
                for cid, crec in pkg_shots:
                    surl = crec.get("http_url") or "N/A"
                    md_lines.append(f"##### Component: `{cid}`")
                    md_lines.append(f"- **Endpoint:** [{surl}]({surl})")
                    md_lines.append("")
                    md_lines.append(f"![{cid} Web UI]({crec['screenshot_path']})")
                    md_lines.append("")

        if record.get("error_message"):
            md_lines.append("")
            md_lines.append("**Error / Failures Message:**")
            md_lines.append("```")
            md_lines.append(record["error_message"])
            md_lines.append("```")

        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines).rstrip() + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Run automated integration tests for " "NjordDeploy packages on Proxmox VE."
        )
    )
    parser.add_argument(
        "--packages",
        type=str,
        help="Comma-separated list of package IDs to test. Defaults to all.",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Comma-separated list of package IDs to exclude from test run.",
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
        help="Testing mode: 'vm', 'lxc', or 'both' (default: lxc)",
    )
    parser.add_argument(
        "--engine",
        type=str,
        choices=["docker", "podman", "both", "all"],
        default="docker",
        help="Container engine: 'docker', 'podman', or 'both' (default: docker)",
    )
    args = parser.parse_args()

    exit_code = run_proxmox_package_tests(args)
    sys.exit(0 if exit_code == 0 else 1)
