# scripts/create_proxmox_lxc.py
import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Ensure we can import from the 'src' root directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.ssh_manager import SSHManager  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("create_proxmox_lxc")


def find_suitable_template(client: ProxmoxClient, node: str) -> str:
    """Finds a Debian or Ubuntu LXC template in any active storage pool."""
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
            # Prioritize 'local' but include all others
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

    try:
        if not templates:
            raise ValueError("No templates found in any storage list")

        # Prioritize Debian templates
        debian_templates = [
            t for t in templates if "debian" in t.get("volid", "").lower()
        ]
        if debian_templates:
            # Sort by name descending to get the newest version
            debian_templates.sort(key=lambda x: x.get("volid", ""), reverse=True)
            newest_deb = next(iter(debian_templates), None)
            if isinstance(newest_deb, dict):
                volid = newest_deb.get("volid")
                if isinstance(volid, str) and volid:
                    return volid

        # Fallback to Ubuntu templates
        ubuntu_templates = [
            t for t in templates if "ubuntu" in t.get("volid", "").lower()
        ]
        if ubuntu_templates:
            ubuntu_templates.sort(key=lambda x: x.get("volid", ""), reverse=True)
            newest_ubu = next(iter(ubuntu_templates), None)
            if isinstance(newest_ubu, dict):
                volid = newest_ubu.get("volid")
                if isinstance(volid, str) and volid:
                    return volid

        # Take any template if neither Debian nor Ubuntu is found
        any_temp = next(iter(templates), None)
        if isinstance(any_temp, dict):
            volid = any_temp.get("volid")
            if isinstance(volid, str) and volid:
                return volid

        raise ValueError("No templates found in storage list")
    except Exception as e:
        logger.error(f"Failed to find templates: {e}")
        # Return a standard fallback path using the first storage found
        default_storage = next(iter(storages), "local")
        return f"{default_storage}:vztmpl/debian-12-standard_12.2-1_" f"amd64.tar.zst"


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


def wait_for_lxc_ip(
    client: ProxmoxClient, node: str, vmid: int, timeout_seconds: int = 120
) -> str:
    """Polls the Proxmox API until the container receives an IPv4 address."""
    logger.info(f"Waiting for container {vmid} to receive an IPv4 address...")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            endpoint = f"nodes/{node}/lxc/{vmid}/interfaces"
            res = client.get(endpoint)
            interfaces = res.get("data", [])
            logger.debug(f"interfaces response: {interfaces}")
            for iface in interfaces:
                name = iface.get("name")
                # Only read `inet` (IPv4); ignore `inet6` entirely.
                inet = iface.get("inet", "")
                if name == "eth0" and inet:
                    ip_candidate, *_rest = inet.split("/")
                    # Skip loopback and APIPA link-local
                    if (
                        ip_candidate
                        and not ip_candidate.startswith("127.")
                        and not ip_candidate.startswith("169.254.")
                    ):
                        return ip_candidate
        except Exception as e:
            logger.debug(f"Failed to get interfaces: {e}")
        time.sleep(4)
    raise TimeoutError("Container failed to acquire an IPv4 address in time.")


def main():
    load_dotenv(dotenv_path=project_root / ".env")

    parser = argparse.ArgumentParser(
        description="Creates and provisions a Proxmox LXC container for NjordDeploy."
    )
    parser.add_argument("--cores", type=int, default=4, help="Number of CPU cores")
    parser.add_argument("--memory", type=int, default=8192, help="Memory size in MB")
    parser.add_argument(
        "--storage-size", type=str, default="40", help="Disk size in GB"
    )
    parser.add_argument(
        "--storage-name",
        type=str,
        default="local-lvm",
        help="Storage pool name",
    )
    parser.add_argument(
        "--node",
        type=str,
        default=os.getenv("PROXMOX_NODE", "pve"),
        help="Proxmox node name",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="PiSelfhostLXC2026!",
        help="Root password for LXC",
    )

    args = parser.parse_args()

    host = os.getenv("PROXMOX_HOST", "https://192.168.178.51:8006")
    user = os.getenv("PROXMOX_USER", "root@pam")
    token_id = os.getenv("PROXMOX_TOKEN_ID", "")
    token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")

    if not token_id or not token_secret:
        logger.error(
            "PROXMOX_TOKEN_ID or PROXMOX_TOKEN_SECRET is not configured in .env"
        )
        sys.exit(1)

    client = ProxmoxClient(host, user, token_id, token_secret)

    # Pre-flight: guard against DHCP pool exhaustion.
    # If too many stopped CTs exist the DHCP server may run out of leases,
    # causing new containers to receive only IPv6 and no IPv4 address.
    stale_ct_threshold = 10
    existing_lxc = client.get_lxc_list(args.node)
    stopped_cts = [ct for ct in existing_lxc if ct.get("status") == "stopped"]
    if len(stopped_cts) >= stale_ct_threshold:
        stale_vmids = sorted(int(ct.get("vmid", 0)) for ct in stopped_cts)
        logger.error(
            f"Pre-flight check failed: {len(stopped_cts)} stopped LXC "
            f"containers detected on node '{args.node}'. This may exhaust "
            f"the DHCP lease pool. Destroy stale containers first.\n"
            f"Stale VMIDs: {stale_vmids}"
        )
        sys.exit(1)

    # 1. Retrieve the next available VMID
    logger.info("Retrieving next available VMID...")
    vmid = client.get_next_vmid()
    logger.info(f"Selected VMID: {vmid}")

    # 2. Get SSH Key from SSHManager
    logger.info("Initializing SSH key...")
    dummy_manager = SSHManager(
        hostname="localhost", username="root", password=""
    )  # nosec B106
    ssh_key = dummy_manager.get_ssh_key()
    pubkey = f"{ssh_key.get_name()} {ssh_key.get_base64()}"

    # 3. Find suitable template
    logger.info("Locating suitable LXC template...")
    ostemplate = find_suitable_template(client, args.node)
    logger.info(f"Using template: {ostemplate}")

    # 4. Define creation parameters
    net_config = "name=eth0,bridge=vmbr0,firewall=1,ip=dhcp"
    rootfs_config = f"{args.storage_name}:{args.storage_size}"

    # Features: nesting=1 is required to run Docker inside LXC.
    # Note: keyctl=1 is omitted because Proxmox API tokens are
    # not allowed to change non-nesting feature flags.
    features_config = "nesting=1"

    data = {
        "vmid": vmid,
        "ostemplate": ostemplate,
        "cores": args.cores,
        "memory": args.memory,
        "swap": 512,
        "rootfs": rootfs_config,
        "net0": net_config,
        "features": features_config,
        "unprivileged": 1,
        "password": args.password,
        "ssh-public-keys": pubkey,
        "start": 1,
    }

    logger.info(f"Creating LXC container {vmid} on node '{args.node}'...")
    creation_endpoint = f"nodes/{args.node}/lxc"
    result = client.post(creation_endpoint, data=data)
    upid = result.get("data")
    logger.info("Container creation request submitted successfully.")

    # Wait for the Proxmox provisioning task to complete
    # (mirrors the approach in proxmox_test_runner.py)
    if isinstance(upid, str):
        wait_for_proxmox_task(client, args.node, upid)

    try:
        ip_address = wait_for_lxc_ip(client, args.node, vmid)
        logger.info(f"Container is online. IP Address: {ip_address}")
    except Exception as e:
        logger.error(f"Failed to retrieve container IP address: {e}")
        sys.exit(1)

    # Wait for SSH daemon to start
    logger.info("Waiting 10s for SSH daemon to start...")
    time.sleep(10)

    ssh = SSHManager(
        hostname=ip_address,
        username="root",
        password=args.password,
        allow_auto_add=True,
    )

    # Simple log callback for SSH commands
    def ssh_log(msg: str):
        logger.info(f"[SSH] {msg}")

    connected, conn_msg = ssh.connect()
    if not connected:
        logger.error(f"Failed to connect to container via SSH: {conn_msg}")
        sys.exit(1)

    # Execution commands to install Docker and setup external network
    install_commands = [
        "apt-get update",
        "apt-get install -y curl ca-certificates gnupg",
        "curl -fsSL https://get.docker.com -o get-docker.sh",
        "sh get-docker.sh",
        "systemctl enable --now docker",
        "docker network create njorddeploy_net",
    ]

    for cmd in install_commands:
        logger.info(f"Executing: {cmd}")
        exit_code, output = ssh.execute_command(cmd, log_callback=ssh_log)
        if exit_code != 0:
            logger.error(f"Command failed with exit code {exit_code}: {output}")
            sys.exit(1)

    logger.info("=" * 60)
    logger.info("LXC CONTAINER PROVISIONING COMPLETED SUCCESSFULLY!")
    logger.info(f"  Container ID:  {vmid}")
    logger.info(f"  IP Address:    {ip_address}")
    logger.info(f"  Root Password: {args.password}")
    logger.info("  SSH Port:      22")
    logger.info("Docker is installed and 'njorddeploy_net' network is ready.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
