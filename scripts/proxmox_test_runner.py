# scripts/proxmox_test_runner.py
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
logger = logging.getLogger("proxmox_test_runner")


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

        is_running = False
        if cmd_exit == 0 and output:
            is_running = any("Up" in line for line in output.splitlines())
            results["running"] = is_running
            if is_running:
                results["details"] = f"Running containers:\n{output}"
            else:
                results["details"] = f"Containers found but none are running:\n{output}"
        else:
            results["details"] = f"No running containers found (exit code: {cmd_exit})."

        # Check docker logs for tracebacks or fatal errors
        # Find matching container name
        container_list = [line.split()[0] for line in output.splitlines() if line]
        matched_container = next(iter(container_list), None)

        if matched_container:
            ssh_mgr.execute_command(
                f"docker logs {matched_container} --tail 100",
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

            # Inspect container config to get the actual version
            cmd_inspect = (
                f"docker inspect {matched_container} --format '{{{{json .Config}}}}'"
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

                    # 1. Check org.opencontainers.image.version label
                    ver: str | None = labels.get("org.opencontainers.image.version")
                    # 2. Check other common labels
                    if not ver:
                        ver = labels.get("version")
                    # 3. Check env variables
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
                        results["detected_version"] = ver.strip()
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
                max_retries = 15
                for attempt in range(1, max_retries + 1):
                    try:
                        res = requests.get(url, timeout=5, verify=False)  # nosec B501
                        if res.status_code in [200, 301, 302, 401, 403]:
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
                                time.sleep(5)
                    except Exception as ex:
                        results["http_ok"] = False
                        if attempt == max_retries:
                            results["details"] += (
                                f"\nHTTP Probe failed after {max_retries} "
                                f"attempts: {ex} ({url})"
                            )
                        else:
                            time.sleep(5)

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


def run_proxmox_tests(cli_args) -> int:
    """Orchestrates cloning, deploying, verifying, and tearing down VMs."""
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
    setup_output_dir = project_root / "tmp_proxmox_test"

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
                target_components.append(comp)
    else:
        target_components = all_components

    # Filter out excluded components
    if cli_args.exclude:
        excluded_ids = [c.strip() for c in cli_args.exclude.split(",")]
        target_components = [
            c for c in target_components if c.get("id") not in excluded_ids
        ]

    if not target_components:
        logger.info("No components matching criteria to test.")
        return 0

    logger.info(f"Starting test run for {len(target_components)} components...")
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

    # --- LXC shared container setup (provisioned once, reused for all components) ---
    shared_lxc_vmid: int | None = None
    shared_lxc_ip: str | None = None

    if is_lxc:
        logger.info("LXC mode: provisioning a shared container for all components.")
        try:
            shared_lxc_vmid = proxmox_client.get_next_vmid()
            logger.info(
                f"Creating shared LXC container {shared_lxc_vmid} "
                f"on node '{node}'..."
            )
            ostemplate = find_suitable_lxc_template(proxmox_client, node)
            logger.info(f"Using template: {ostemplate}")

            net_config = "name=eth0,bridge=vmbr0,firewall=1,ip=dhcp"
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
            # Cleanup if partially created
            if shared_lxc_vmid:
                # noinspection PyBroadException
                try:
                    stop_lxc(proxmox_client, node, shared_lxc_vmid)
                    destroy_lxc(proxmox_client, node, shared_lxc_vmid)
                except Exception:  # nosec B110
                    pass
            return 1

    try:
        for comp in target_components:
            comp_id = comp.get("id", "unknown")
            logger.info("----------------------------------------")
            logger.info(f"Testing component: {comp_id}")
            logger.info("----------------------------------------")

            test_record = {
                "component_id": comp_id,
                "status": "failed",
                "vmid": shared_lxc_vmid if is_lxc else None,
                "ip": shared_lxc_ip if is_lxc else None,
                "deployment": "failed",
                "running": False,
                "http_ok": None,
                "error_logs": False,
                "error_message": "",
            }

            new_vmid: int | None = None
            vm_ip: str | None = shared_lxc_ip if is_lxc else None

            try:
                if is_lxc:
                    # Clean Docker state between components so each test
                    # starts from a fresh environment without leftover
                    # containers, volumes, images, or networks.
                    logger.info(
                        f"Cleaning Docker environment before testing {comp_id}..."
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
                        # Step 1: stop all running containers gracefully
                        "docker ps -q | xargs -r docker stop 2>/dev/null || true",
                        # Step 2: force-remove all containers (running or stopped)
                        "docker ps -aq | xargs -r docker rm -f 2>/dev/null || true",
                        # Step 3: prune all unused images, volumes and networks
                        "docker system prune -af --volumes",
                        # Step 4: recreate the shared bridge network
                        (
                            "docker network inspect njorddeploy_net >/dev/null 2>&1 "
                            "|| docker network create njorddeploy_net"
                        ),
                    ]:
                        cleanup_ssh.execute_command(cmd, lambda msg: None)
                    cleanup_ssh.close()
                    logger.info("Docker environment clean.")

                else:
                    # VM mode: clone a fresh VM per component (unchanged)
                    vmid_val = proxmox_client.get_next_vmid()
                    if vmid_val is None:
                        raise RuntimeError("Failed to allocate new VMID from Proxmox.")
                    new_vmid = vmid_val
                    if new_vmid is None:
                        raise RuntimeError("new_vmid unexpectedly None")
                    test_record["vmid"] = new_vmid
                    logger.info(
                        f"Cloning master template VMID {template_id} "
                        f"to {new_vmid}..."
                    )
                    try:
                        clone_res = proxmox_client.clone_vm(
                            node=node,
                            vmid=template_id,
                            newid=new_vmid,
                            name=f"pish-test-{comp_id}",
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
                                name=f"pish-test-{comp_id}",
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
                            "net0": "virtio,bridge=vmbr0,firewall=1",
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
                logger.info(f"Generating deployment configurations for {comp_id}...")
                # Use the VMID as a unique folder name; for LXC that is the
                # shared container's VMID, which is stable across all iterations.
                folder_vmid = shared_lxc_vmid if is_lxc else new_vmid
                comp_output_dir = setup_output_dir / str(folder_vmid) / comp_id
                setup_mgr = SetupManager(
                    component_manager=comp_mgr.reader, output_dir=comp_output_dir
                )
                setup_mgr.initialize_environment()

                all_components = comp_mgr.get_all_components()
                comp_map = {c.get("id"): c for c in all_components if c.get("id")}
                dependencies = comp.get("depends_on", [])
                all_selected_ids = [comp_id]
                for dep_id in dependencies:
                    if dep_id in comp_map and dep_id not in all_selected_ids:
                        all_selected_ids.append(dep_id)

                all_selected_data = [
                    comp_map[cid] for cid in all_selected_ids if cid in comp_map
                ]

                target_variables = comp_mgr.reader.get_component_variables(comp_id)
                user_vars = {}
                for cid in all_selected_ids:
                    variables_list = comp_mgr.reader.get_component_variables(cid)
                    for var in variables_list:
                        var_name = var.get("id") or var.get("name")
                        if var_name:
                            user_vars[var_name] = var.get("default")

                user_vars["PISelfhosting_HOST_IP"] = vm_ip

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
                    output_path=comp_output_dir,
                )

                # 6. Deploy via DeploymentManager (Ansible)
                logger.info(f"Executing Ansible deployment to {vm_ip}...")
                deploy_mgr = DeploymentManager(component_manager=comp_mgr)
                run_vmid = shared_lxc_vmid if is_lxc else new_vmid
                task_id = f"test-{comp_id}-{run_vmid}"
                tasks_dict = {task_id: {"logs": [], "status": "pending"}}

                deploy_mgr.start_deployment(
                    task_id=task_id,
                    tasks=tasks_dict,
                    output_path=str(comp_output_dir),
                    devices=[
                        {
                            "ip": vm_ip,
                            "username": "root" if is_lxc else vm_user,
                            "password": vm_pass,
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

                # 7. Run Health Verification Probe
                logger.info("Running service health verification probe...")
                if vm_ip is None:
                    raise RuntimeError("vm_ip unexpectedly None")
                health = verify_service_health(
                    vm_ip=vm_ip,
                    vm_user="root" if is_lxc else vm_user,
                    vm_pass=vm_pass,
                    _component_id=comp_id,
                    component_details=comp,
                    variables_list=target_variables,
                )

                test_record["running"] = health["running"]
                test_record["http_ok"] = health["http_ok"]
                test_record["error_logs"] = health["logs_error"]

                if health["running"] and (
                    health["http_ok"] is None or health["http_ok"] is True
                ):
                    test_record["status"] = "success"
                    logger.info(f"✅ Component {comp_id} verified successfully!")
                    tested_ver = health.get("detected_version") or comp.get(
                        "component_version", "latest"
                    )
                    if is_lxc:
                        notes = "Tested successfully on Proxmox LXC."
                    else:
                        notes = (
                            "Tested successfully on Proxmox VM "
                            f"(template {template_id})."
                        )
                    update_template_status(templates_path, comp_id, tested_ver, notes)
                else:
                    test_record["status"] = "failed"
                    test_record["error_message"] = health["details"]
                    logger.error(
                        "❌ Component verification failed: " f"{health['details']}"
                    )
                    failed_count += 1

            except Exception as ex:
                logger.error(f"❌ Error during test of {comp_id}: {ex}")
                test_record["status"] = "failed"
                test_record["error_message"] = str(ex)
                failed_count += 1
            finally:
                # In VM mode: destroy the per-component clone after each test.
                # In LXC mode: the shared container is destroyed after the loop.
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

                # Cleanup local output folder for this component
                folder_vmid = shared_lxc_vmid if is_lxc else new_vmid
                if folder_vmid:
                    comp_output_dir = setup_output_dir / str(folder_vmid) / comp_id
                    if comp_output_dir.exists():
                        import shutil

                        shutil.rmtree(comp_output_dir)

            results_summary.append(test_record)

    finally:
        # Destroy the shared LXC container after all components have been tested
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

    # Ensure output dirs exist
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)
    tests_dir = project_root / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Save JSON results
    json_path = tests_dir / "proxmox_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=4)
    logger.info(f"Saved raw test results to: {json_path}")

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
    elif cli_args.untested_ui:
        title_suffix = "untested_ui"
        report_filename = f"PROXMOX_TESTS_untested_ui_{timestamp_fn}.md"
    else:
        title_suffix = "all"
        report_filename = f"PROXMOX_TESTS_all_{timestamp_fn}.md"

    report_path = docs_dir / report_filename
    write_markdown_report(report_path, results_summary, failed_count, title_suffix)
    logger.info(f"Saved human-readable markdown report to: {report_path}")

    # Send Signal Notification
    overall_status = "✅ ALL SUCCESSFUL" if failed_count == 0 else "❌ FAILED"
    passed_count = len(results_summary) - failed_count

    signal_msg = (
        f"🚢 NjordDeploy Proxmox Test Report\n"
        f"Status: {overall_status}\n"
        f"Total tested: {len(results_summary)}\n"
        f"Passed: {passed_count}\n"
        f"Failed: {failed_count}"
    )
    if failed_count > 0:
        failed_list = [
            r["component_id"] for r in results_summary if r["status"] != "success"
        ]
        signal_msg += f"\nFailed: {', '.join(failed_list)}"

    send_signal_message(signal_msg)

    # Maintain copy at PROXMOX_TESTS.md for easy quick viewing
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
):
    """Writes a clean, formatted Markdown report of the test outcomes."""
    total_count = len(results)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    title = "Proxmox Automated Component Testing Report"
    if title_suffix:
        title += f" - {title_suffix}"

    md_lines = [
        f"# {title}",
        "",
        f"**Run Timestamp:** {timestamp}",
        (
            f"**Total Tested:** {total_count} | "
            f"**Passed:** {total_count - failed_count} | "
            f"**Failed:** {failed_count}"
        ),
        "",
        "## Results Table",
        "",
        (
            "| Component ID | VM ID | IP Address | "
            "Deployment | Containers | HTTP | Status |"
        ),
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for record in results:
        status_emoji = "✅ PASS" if record["status"] == "success" else "❌ FAIL"
        http_val = (
            "N/A"
            if record["http_ok"] is None
            else ("OK" if record["http_ok"] else "FAIL")
        )
        md_lines.append(
            f"| `{record['component_id']}` | {record['vmid']} | "
            f"{record['ip'] or 'N/A'} | {record['deployment']} | "
            f"{'Running' if record['running'] else 'Stopped'} | "
            f"{http_val} | **{status_emoji}** |"
        )

    md_lines.append("")
    md_lines.append("## Details & Failures")
    md_lines.append("")

    has_failures = False
    for record in results:
        if record["status"] != "success":
            has_failures = True
            md_lines.append(f"### Component: `{record['component_id']}`")
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
            "All components completed execution and " "verification successfully!"
        )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")


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
        choices=["vm", "lxc"],
        default="vm",
        help="Testing mode: 'vm' or 'lxc' (default: vm)",
    )
    parser.add_argument(
        "--untested-ui",
        action="store_true",
        help=(
            "Automatically test all components that have a UI "
            "and are not yet marked as 'tested'."
        ),
    )
    args = parser.parse_args()

    exit_code = run_proxmox_tests(args)
    sys.exit(0 if exit_code == 0 else 1)
