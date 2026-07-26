# scripts/proxmox_package_test_runner.py
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

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
]


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

        # List containers running in the compose project
        cmd_docker_ps = (
            "docker ps -a --filter "
            "label=com.docker.compose.project=njorddeploy "
            "--format '{{.Names}} ({{.Status}})'"
        )
        cmd_exit, output = ssh_mgr.execute_command(
            cmd_docker_ps,
            lambda x: None,
            check_exit_code=False,
        )

        running_containers = []
        if cmd_exit == 0 and output:
            running_containers = [
                line.strip() for line in output.splitlines() if line.strip()
            ]

        overall_success = True
        component_status = {}

        for comp in package_components:
            comp_id = comp.get("id", "unknown")
            if hasattr(comp_mgr.reader, "get_docker_service_name"):
                svc_name = comp_mgr.reader.get_docker_service_name(comp_id)
            else:
                svc_name = comp_id

            # Find matching container running
            is_running = False
            matched_container = None
            for container in running_containers:
                if svc_name in container:
                    is_running = "Up" in container
                    container_name, *_ = container.split()
                    matched_container = container_name
                    break

            comp_error_message = ""
            comp_http_ok: str | bool | None = None
            comp_logs_error = False
            comp_detected_version = None

            if not is_running:
                comp_error_message = (
                    f"No running container found matching service '{svc_name}'."
                )
                if matched_container:
                    err_logs: List[str] = []
                    ssh_mgr.execute_command(
                        f"docker logs {matched_container} --tail 100",
                        lambda x: err_logs.append(x),
                        check_exit_code=False,
                    )
                    if err_logs:
                        comp_error_message += (
                            "\nLast 100 container logs:\n" + "\n".join(err_logs)
                        )
                overall_success = False
            else:
                # Check docker logs for tracebacks or fatal errors
                comp_logs: List[str] = []
                ssh_mgr.execute_command(
                    f"docker logs {matched_container} --tail 100",
                    lambda x: comp_logs.append(x),
                    check_exit_code=False,
                )
                logs_content = "\n".join(comp_logs).lower()
                if "traceback" in logs_content or "fatal" in logs_content:
                    comp_logs_error = True

                # Inspect container config to get the actual version
                cmd_inspect = (
                    f"docker inspect {matched_container} "
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
                            "(retrying up to 15 times)..."
                        )
                        max_retries = 15
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
                        if not probe_success:
                            overall_success = False

            comp_record = {
                "running": is_running,
                "http_ok": comp_http_ok,
                "logs_error": comp_logs_error,
                "error_message": comp_error_message,
                "detected_version": comp_detected_version,
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
    platform_notes: str,
) -> None:
    """Updates status, last tested version and platform notes in template."""
    template_file = templates_path / component_id / "docker-compose.template.yml"
    if not template_file.exists():
        logger.warning(f"Template file not found to update status: {template_file}")
        return

    try:
        content = template_file.read_text(encoding="utf-8")
        lines = content.splitlines()

        updated_lines = []
        in_header = True
        status_replaced = False
        version_replaced = False
        notes_replaced = False

        for line in lines:
            if in_header and line.startswith("#"):
                stripped = line[1:].strip()
                if stripped.startswith("status:"):
                    updated_lines.append('# status: "tested"')
                    status_replaced = True
                elif stripped.startswith("last_tested_version:"):
                    updated_lines.append(f'# last_tested_version: "{tested_version}"')
                    version_replaced = True
                elif stripped.startswith("platform_notes:"):
                    updated_lines.append(f'# platform_notes: "{platform_notes}"')
                    notes_replaced = True
                else:
                    updated_lines.append(line)
            else:
                in_header = False
                updated_lines.append(line)

        if not status_replaced or not version_replaced or not notes_replaced:
            logger.warning(
                f"Could not find standard headers in {template_file}, "
                "skipping header update."
            )
            return

        new_content = "\n".join(updated_lines) + "\n"
        template_file.write_text(new_content, encoding="utf-8")
        logger.info(
            f"Updated template status headers for {component_id} to "
            f"'tested' (version: {tested_version}, notes: {platform_notes})"
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


def run_proxmox_package_tests(cli_args) -> int:
    """Orchestrates package testing.

    Clones, deploys, verifies, and tears down VMs for package testing.
    """
    load_dotenv()
    proxmox_client = setup_proxmox_client()

    node = cli_args.node or os.getenv("PROXMOX_NODE") or "pve"
    template_env = os.getenv("PROXMOX_TEMPLATE_ID") or "900"
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
    setup_output_dir = project_root / "tmp_proxmox_package_test"

    # Get target packages list
    all_packages = comp_mgr.get_all_packages()
    all_components = comp_mgr.get_all_components()

    target_packages = {}
    if cli_args.packages:
        selected_ids = [p.strip() for p in cli_args.packages.split(",")]
        for pkg_id, pkg_data in all_packages.items():
            if pkg_id in selected_ids:
                target_packages[pkg_id] = pkg_data
    else:
        target_packages = all_packages.copy()

    # Filter out excluded packages
    if cli_args.exclude:
        excluded_ids = [p.strip() for p in cli_args.exclude.split(",")]
        for pkg_id in excluded_ids:
            target_packages.pop(pkg_id, None)

    if not target_packages:
        logger.info("No packages matching criteria to test.")
        return 0

    logger.info(f"Starting test run for {len(target_packages)} packages...")
    results_summary = []
    failed_count = 0

    # Ensure a local SSH key is generated to copy to the VMs
    dummy_mgr = SSHManager(
        hostname="localhost", username="test", password="key"
    )  # nosec B106
    # noinspection PyProtectedMember
    ssh_key_obj = dummy_mgr._get_or_create_key()
    ssh_public_key = f"{ssh_key_obj.get_name()} {ssh_key_obj.get_base64()}"

    is_lxc = getattr(cli_args, "mode", "vm") == "lxc"

    # --- LXC shared container setup (provisioned once, reused for all packages) ---
    shared_lxc_vmid: int | None = None
    shared_lxc_ip: str | None = None

    if is_lxc:
        logger.info("LXC mode: provisioning a shared container for all packages.")
        try:
            shared_lxc_vmid = proxmox_client.get_next_vmid()
            logger.info(
                f"Creating shared LXC container {shared_lxc_vmid} "
                f"on node '{node}'..."
            )
            ostemplate = find_suitable_lxc_template(proxmox_client, node)
            logger.info(f"Using template: {ostemplate}")

            net_config = "name=eth0,bridge=vmbr0,firewall=0,ip=dhcp"
            create_data = {
                "vmid": shared_lxc_vmid,
                "ostemplate": ostemplate,
                "cores": 4,
                "memory": 8192,
                "swap": 512,
                "rootfs": "local-lvm:40",
                "net0": net_config,
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
            shared_lxc_ip = wait_for_lxc_ip(proxmox_client, node, shared_lxc_vmid)
            if shared_lxc_ip is None:
                raise RuntimeError("shared_lxc_ip is None in LXC mode")
            logger.info(f"Shared LXC container online at {shared_lxc_ip}.")
            time.sleep(10)

            # Install Docker once on the shared container
            logger.info("Installing Docker on shared LXC container...")
            if shared_lxc_ip is None:
                raise RuntimeError("shared_lxc_ip unexpectedly None")
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

            for cmd in [
                "apt-get update",
                "apt-get install -y curl ca-certificates gnupg",
                "curl -fsSL https://get.docker.com -o get-docker.sh",
                "sh get-docker.sh",
                "systemctl enable --now docker",
            ]:
                lxc_ssh.execute_command(cmd, lambda msg: None)
            lxc_ssh.close()
            logger.info("Docker installed on shared LXC container.")

        except Exception as setup_err:
            logger.error(f"Failed to provision shared LXC container: {setup_err}")
            if shared_lxc_vmid:
                # noinspection PyBroadException
                try:
                    stop_lxc(proxmox_client, node, shared_lxc_vmid)
                    destroy_lxc(proxmox_client, node, shared_lxc_vmid)
                except Exception:  # nosec B110
                    pass
            return 1

    try:
        for pkg_id, pkg in target_packages.items():
            logger.info("========================================")
            logger.info(f"Testing package: {pkg_id} ({pkg.get('name')})")
            logger.info("========================================")

            # Find all components belonging to this package, excluding skipped ones
            package_components = [
                c
                for c in all_components
                if c.get("package_id") == pkg_id
                and c.get("id") not in SKIPPED_COMPONENTS
            ]
            if not package_components:
                logger.warning(f"No components found for package {pkg_id}. Skipping.")
                continue

            test_record = {
                "package_id": pkg_id,
                "package_name": pkg.get("name"),
                "status": "failed",
                "vmid": shared_lxc_vmid if is_lxc else None,
                "ip": shared_lxc_ip if is_lxc else None,
                "deployment": "failed",
                "components": {},
                "error_message": "",
            }

            new_vmid: int | None = None
            vm_ip: str | None = shared_lxc_ip if is_lxc else None

            try:
                if is_lxc:
                    # Clean Docker state between packages
                    logger.info(
                        "Cleaning Docker environment before testing "
                        f"package {pkg_id}..."
                    )
                    if shared_lxc_ip is None:
                        raise RuntimeError("shared_lxc_ip is None in LXC mode")
                    cleanup_ssh = SSHManager(
                        hostname=shared_lxc_ip,
                        username="root",
                        password=vm_pass,
                        allow_auto_add=True,
                        load_system_keys=False,
                    )
                    connected, conn_msg = cleanup_ssh.connect()
                    if not connected:
                        raise RuntimeError(
                            f"Cannot connect to shared LXC for cleanup: {conn_msg}"
                        )
                    for cmd in [
                        "docker ps -q | xargs -r docker stop 2>/dev/null || true",
                        "docker ps -aq | xargs -r docker rm -f 2>/dev/null || true",
                        "docker system prune -af --volumes",
                        (
                            "docker network inspect njorddeploy_net >/dev/null 2>&1 "
                            "|| docker network create njorddeploy_net"
                        ),
                    ]:
                        cleanup_ssh.execute_command(cmd, lambda msg: None)
                    cleanup_ssh.close()
                    logger.info("Docker environment clean.")

                else:
                    # VM mode: clone a fresh VM per package
                    vmid_val = proxmox_client.get_next_vmid()
                    if vmid_val is None:
                        raise RuntimeError("Failed to allocate new VMID from Proxmox.")
                    new_vmid = vmid_val
                    if new_vmid is None:
                        raise RuntimeError("new_vmid unexpectedly None")
                    test_record["vmid"] = new_vmid
                    logger.info(
                        f"Cloning master template VMID {template_id} to {new_vmid}..."
                    )
                    try:
                        clone_res = proxmox_client.clone_vm(
                            node=node,
                            vmid=template_id,
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
                                "Linked clone not supported, "
                                "falling back to full clone..."
                            )
                            clone_res = proxmox_client.clone_vm(
                                node=node,
                                vmid=template_id,
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

                    logger.info(f"Configuring Cloud-Init for VMID {new_vmid}...")
                    proxmox_client.configure_vm(
                        node=node,
                        vmid=new_vmid,
                        config_data={
                            "ciuser": vm_user,
                            "cipassword": vm_pass,
                            "sshkeys": urllib.parse.quote(ssh_public_key),
                            "ipconfig0": "ip=dhcp",
                            "agent": "enabled=1",
                            "ide2": "local-lvm:cloudinit",
                            "net0": "virtio,bridge=vmbr0,firewall=0",
                        },
                    )
                    logger.info(f"Starting VMID {new_vmid}...")
                    proxmox_client.start_vm(node=node, vmid=new_vmid)

                    vm_ip = wait_for_ip(proxmox_client, node, new_vmid)
                    if not vm_ip:
                        raise TimeoutError(
                            "Unable to retrieve IP address for cloned VM."
                        )
                    test_record["vmid"] = new_vmid
                    test_record["ip"] = vm_ip
                    time.sleep(10)

                # 5. Build configuration package locally
                logger.info(
                    f"Generating deployment configurations for package {pkg_id}..."
                )
                folder_vmid = shared_lxc_vmid if is_lxc else new_vmid
                pkg_output_dir = setup_output_dir / str(folder_vmid) / pkg_id
                setup_mgr = SetupManager(
                    component_manager=comp_mgr.reader, output_dir=pkg_output_dir
                )
                setup_mgr.initialize_environment()

                # Get all component IDs in package and their dependencies
                comp_map = {c.get("id"): c for c in all_components if c.get("id")}
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

                # Build variables dictionary
                user_vars = {}
                for cid in all_selected_ids:
                    variables_list = comp_mgr.reader.get_component_variables(cid)
                    for var in variables_list:
                        var_name = var.get("id") or var.get("name")
                        if var_name:
                            user_vars[var_name] = var.get("default")

                user_vars["PISelfhosting_HOST_IP"] = vm_ip

                # Prepare deployment files (.env and compose templates)
                success, errors = setup_mgr.prepare_deployment_package(
                    selected_components=all_selected_ids,
                    user_variables=user_vars,
                    managed_devices=[{"ip": vm_ip}],
                )
                if not success:
                    errors_summary = ", ".join([err.get("summary") for err in errors])
                    raise RuntimeError(
                        f"Configuration packaging failed: {errors_summary}"
                    )

                comp_mgr.generate_deployment_artifacts(
                    selected_components_data=all_selected_data,
                    global_vars=user_vars,
                    output_path=pkg_output_dir,
                )

                # 6. Deploy via DeploymentManager (Ansible)
                logger.info(
                    f"Executing Ansible deployment of package {pkg_id} to {vm_ip}..."
                )
                deploy_mgr = DeploymentManager(component_manager=comp_mgr)
                run_vmid = shared_lxc_vmid if is_lxc else new_vmid
                task_id = f"test-{pkg_id}-{run_vmid}"
                tasks_dict = {task_id: {"logs": [], "status": "pending"}}

                deploy_mgr.start_deployment(
                    task_id=task_id,
                    tasks=tasks_dict,
                    output_path=str(pkg_output_dir),
                    devices=[
                        {
                            "ip": vm_ip,
                            "username": "root" if is_lxc else vm_user,
                            "password": vm_pass,
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
                    err_details = first_error.get("details", "Ansible execution error")
                    raise RuntimeError(f"Deployment failed: {err_details}")

                # 7. Run Health Verification Probe for each package component
                logger.info(
                    "Running health verification probes for all package components..."
                )
                if vm_ip is None:
                    raise RuntimeError("vm_ip unexpectedly None")
                health_results = verify_package_health(
                    vm_ip=vm_ip,
                    vm_user="root" if is_lxc else vm_user,
                    vm_pass=vm_pass,
                    package_components=package_components,
                    comp_mgr=comp_mgr,
                )

                test_record["components"] = health_results["components"]

                if health_results["success"]:
                    test_record["status"] = "success"
                    logger.info(f"✅ Package {pkg_id} verified successfully!")

                    # Update header status of all components in this package
                    for comp in package_components:
                        comp_id = comp.get("id")
                        if not isinstance(comp_id, str) or not comp_id:
                            continue
                        comp_health = health_results["components"].get(comp_id, {})
                        tested_ver_val = (
                            comp_health.get("detected_version")
                            or comp.get("component_version")
                            or "latest"
                        )
                        tested_ver = str(tested_ver_val)
                        if is_lxc:
                            notes = (
                                "Tested successfully as part of package "
                                f"'{pkg_id}' on Proxmox LXC."
                            )
                        else:
                            notes = (
                                f"Tested successfully as part of package "
                                f"'{pkg_id}' on Proxmox VM "
                                f"(template {template_id})."
                            )
                        update_template_status(
                            templates_path, comp_id, tested_ver, notes
                        )
                else:
                    test_record["status"] = "failed"
                    test_record["error_message"] = health_results["details"]
                    logger.error(
                        f"❌ Package verification failed: {health_results['details']}"
                    )
                    failed_count += 1

            except Exception as ex:
                logger.error(f"❌ Error during test of package {pkg_id}: {ex}")
                test_record["status"] = "failed"
                test_record["error_message"] = str(ex)
                failed_count += 1
            finally:
                if not is_lxc and new_vmid:
                    logger.info(f"Stopping and destroying VM {new_vmid}...")
                    try:
                        stop_res = proxmox_client.stop_vm(node, new_vmid)
                        upid = stop_res.get("data")
                        if isinstance(upid, str):
                            wait_for_proxmox_task(proxmox_client, node, upid)
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
                        import shutil

                        shutil.rmtree(pkg_output_dir)

            results_summary.append(test_record)

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
                    "Failed to destroy shared LXC container "
                    f"{shared_lxc_vmid}: {teardown_err}"
                )

    # Ensure output dirs exist
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)
    tests_dir = project_root / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Save JSON results
    json_path = tests_dir / "proxmox_package_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=4)
    logger.info(f"Saved raw test results to: {json_path}")

    # Generate Markdown Report
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
            r["package_id"] for r in results_summary if r["status"] != "success"
        ]
        signal_msg += f"\nFailed: {', '.join(failed_list)}"

    send_signal_message(signal_msg)

    # Maintain copy at PROXMOX_PACKAGE_TESTS.md for easy quick viewing
    latest_report_path = docs_dir / "PROXMOX_PACKAGE_TESTS.md"
    try:
        if latest_report_path.exists():
            latest_report_path.unlink()
        import shutil

        shutil.copy2(report_path, latest_report_path)
    except Exception as sym_err:
        logger.warning(
            f"Could not copy latest report to PROXMOX_PACKAGE_TESTS.md: {sym_err}"
        )

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
        "| Package ID | Package Name | VM ID | IP Address | Deployment | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for record in results:
        status_emoji = "✅ PASS" if record["status"] == "success" else "❌ FAIL"
        md_lines.append(
            f"| `{record['package_id']}` | {record['package_name']} | "
            f"{record['vmid']} | {record['ip'] or 'N/A'} | "
            f"{record['deployment']} | **{status_emoji}** |"
        )

    md_lines.append("")
    md_lines.append("## Detailed Components Verification Status")
    md_lines.append("")

    for record in results:
        md_lines.append(
            f"### Package: `{record['package_id']}` ({record['package_name']})"
        )
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
        f.write("\n".join(md_lines) + "\n")


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
        choices=["vm", "lxc"],
        default="vm",
        help="Testing mode: 'vm' or 'lxc' (default: vm)",
    )
    args = parser.parse_args()

    exit_code = run_proxmox_package_tests(args)
    sys.exit(0 if exit_code == 0 else 1)
