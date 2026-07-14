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
            if newest_deb:
                volid = newest_deb.get("volid")
                if volid:
                    return volid

        # Fallback to Ubuntu templates
        ubuntu_templates = [
            t for t in templates if "ubuntu" in t.get("volid", "").lower()
        ]
        if ubuntu_templates:
            ubuntu_templates.sort(key=lambda x: x.get("volid", ""), reverse=True)
            newest_ubu = next(iter(ubuntu_templates), None)
            if newest_ubu:
                volid = newest_ubu.get("volid")
                if volid:
                    return volid

        # Take any template if neither Debian nor Ubuntu is found
        any_temp = next(iter(templates), None)
        if any_temp:
            volid = any_temp.get("volid")
            if volid:
                return volid

        raise ValueError("No templates found in storage list")
    except Exception as e:
        logger.error(f"Failed to find templates: {e}")
        # Return a standard fallback path using the first storage found
        default_storage = next(iter(storages), "local")
        return f"{default_storage}:vztmpl/debian-12-standard_12.2-1_" f"amd64.tar.zst"


def wait_for_lxc_ip(client: ProxmoxClient, node: str, vmid: int) -> str:
    """Polls the Proxmox API until the container receives an IP address."""
    logger.info(f"Waiting for container {vmid} to receive an IP address...")
    for _ in range(30):
        try:
            endpoint = f"nodes/{node}/lxc/{vmid}/interfaces"
            res = client.get(endpoint)
            interfaces = res.get("data", [])
            for iface in interfaces:
                name = iface.get("name")
                inet = iface.get("inet")
                if name == "eth0" and inet:
                    parts = inet.split("/")
                    ip_addr, *rest = parts
                    if ip_addr and not ip_addr.startswith("127."):
                        return ip_addr
        except Exception as e:
            logger.debug(f"Failed to get interfaces: {e}")
        time.sleep(4)
    raise TimeoutError("Container failed to acquire an IP address in time.")


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

    # 1. Retrieve the next available VMID
    logger.info("Retrieving next available VMID...")
    vmid = client.get_next_vmid()
    logger.info(f"Selected VMID: {vmid}")

    # 2. Get SSH Key from SSHManager
    logger.info("Initializing SSH key...")
    dummy_manager = SSHManager(
        hostname="localhost", username="root", password=""
    )  # nosec B106
    ssh_key = dummy_manager._get_or_create_key()
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
    client.post(creation_endpoint, data=data)
    logger.info("Container creation request submitted successfully.")

    # 5. Wait for IP Address
    try:
        ip_address = wait_for_lxc_ip(client, args.node, vmid)
        logger.info(f"Container is online. IP Address: {ip_address}")
    except Exception as e:
        logger.error(f"Failed to retrieve container IP address: {e}")
        sys.exit(1)

    # 6. Install Docker and configure network via SSH
    logger.info("Provisioning container over SSH (Installing Docker)...")
    # Wait for SSH service to start up on the container
    time.sleep(5)

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
