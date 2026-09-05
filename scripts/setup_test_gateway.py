# scripts/setup_test_gateway.py
"""Provisions and configures a dedicated registry mirror gateway container on Proxmox.

Runs on node 'pve' on bridge 'vmbr1' (10.99.0.2:5000) with 30GB storage to provide
a local pull-through cache for Docker Hub images during automated test runs.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.ssh_manager import SSHManager  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("setup_test_gateway")

GATEWAY_VMID = 920
GATEWAY_IP = "10.99.0.2"
GATEWAY_NETMASK = "24"
GATEWAY_ROUTER = "10.99.0.1"
GATEWAY_NAME = "njorddeploy-test-gateway"
REGISTRY_PORT = 5000


def wait_for_proxmox_task(
    client: ProxmoxClient, node: str, upid: str, timeout: int = 180
) -> bool:
    """Waits for a Proxmox task (identified by UPID) to finish."""
    start = time.time()
    while time.time() - start < timeout:
        # noinspection PyBroadException
        try:
            status_data = client.get(f"nodes/{node}/tasks/{upid}/status")
            task_info = status_data.get("data", {})
            if task_info.get("status") == "stopped":
                exit_status = task_info.get("exitstatus")
                if exit_status == "OK":
                    return True
                raise RuntimeError(
                    f"Proxmox task {upid} failed with status: {exit_status}"
                )
        except Exception as ex:
            if "failed with status" in str(ex):
                raise
        time.sleep(2)
    raise TimeoutError(f"Proxmox task {upid} timed out after {timeout} seconds.")


def find_suitable_lxc_template(client: ProxmoxClient, node: str) -> str:
    """Locates a Debian LXC template on the Proxmox node."""
    storage_res = client.get(f"nodes/{node}/storage/local/content")
    for item in storage_res.get("data", []):
        volid = item.get("volid", "")
        if "debian-12" in volid and "vztmpl" in volid:
            return volid
    for item in storage_res.get("data", []):
        volid = item.get("volid", "")
        if "debian" in volid and "vztmpl" in volid:
            return volid
    raise FileNotFoundError("Could not find a Debian LXC template in local:vztmpl.")


def ensure_gateway_container(
    client: ProxmoxClient, node: str, bridge: str, vm_pass: str
) -> None:
    """Ensures container 920 exists and is running on vmbr1."""
    lxcs = client.get(f"nodes/{node}/lxc").get("data", [])
    existing: Optional[Dict[str, Any]] = next(
        (item for item in lxcs if item.get("vmid") == GATEWAY_VMID), None
    )

    if existing:
        logger.info(
            f"Gateway container {GATEWAY_VMID} already exists "
            f"(status: {existing.get('status')})."
        )
        if existing.get("status") != "running":
            logger.info(f"Starting gateway container {GATEWAY_VMID}...")
            start_res = client.start_lxc(node, GATEWAY_VMID)
            upid = start_res.get("data")
            if isinstance(upid, str):
                wait_for_proxmox_task(client, node, upid)
            time.sleep(3)
        return

    logger.info(f"Creating new test gateway container {GATEWAY_VMID} on {bridge}...")
    ostemplate = find_suitable_lxc_template(client, node)
    logger.info(f"Using LXC template: {ostemplate}")

    dummy_mgr = SSHManager(
        hostname="localhost", username="test", password="key"
    )  # nosec B106
    ssh_public_key = dummy_mgr.get_public_key_string()

    net_config = (
        f"name=eth0,bridge={bridge},"
        f"ip={GATEWAY_IP}/{GATEWAY_NETMASK},gw={GATEWAY_ROUTER},"
        "firewall=0"
    )

    create_data = {
        "vmid": GATEWAY_VMID,
        "ostemplate": ostemplate,
        "hostname": GATEWAY_NAME,
        "cores": 1,
        "memory": 512,
        "swap": 256,
        "rootfs": "local-lvm:30",
        "net0": net_config,
        "nameserver": "1.1.1.1 8.8.8.8",
        "features": "nesting=1",
        "unprivileged": 1,
        "onboot": 1,
        "password": vm_pass,
        "ssh-public-keys": ssh_public_key,
        "start": 1,
    }

    create_res = client.create_lxc(node, create_data)
    upid = create_res.get("data")
    if isinstance(upid, str):
        wait_for_proxmox_task(client, node, upid)
    logger.info(f"Gateway container {GATEWAY_VMID} created and started.")
    time.sleep(5)


def configure_registry_service(vm_pass: str) -> bool:
    """Installs and configures docker-registry pull-through cache inside
    container 920.
    """
    logger.info(f"Connecting to registry mirror container at {GATEWAY_IP} via SSH...")
    ssh_mgr = SSHManager(
        hostname=GATEWAY_IP,
        username="root",
        password=vm_pass,
        allow_auto_add=True,
        load_system_keys=False,
    )

    connected = False
    conn_msg = ""
    for _ in range(15):
        connected, conn_msg = ssh_mgr.connect()
        if connected:
            break
        time.sleep(3)

    if not connected:
        logger.error(f"Could not connect to {GATEWAY_IP}: {conn_msg}")
        return False

    logger.info("Configuring DNS, disabling dnsmasq, and installing docker-registry...")
    setup_script = (
        "systemctl stop dnsmasq 2>/dev/null || true; "
        "systemctl disable dnsmasq 2>/dev/null || true; "
        "chattr -i /etc/resolv.conf 2>/dev/null || true; "
        "printf 'nameserver 1.1.1.1\\nnameserver 8.8.8.8\\n' > /etc/resolv.conf; "
        "chattr +i /etc/resolv.conf 2>/dev/null || true; "
        "apt-get update -y && "
        "DEBIAN_FRONTEND=noninteractive apt-get install -y docker-registry curl"
    )
    exit_code, out = ssh_mgr.execute_command(
        setup_script, lambda x: None, check_exit_code=False
    )
    if exit_code != 0:
        logger.error(f"Failed to install docker-registry: {out}")
        ssh_mgr.close()
        return False

    logger.info("Writing docker-registry pull-through cache configuration...")
    registry_conf = (
        "version: 0.1\\n"
        "log:\\n"
        "  fields:\\n"
        "    service: registry\\n"
        "storage:\\n"
        "  cache:\\n"
        "    blobdescriptor: inmemory\\n"
        "  filesystem:\\n"
        "    rootdirectory: /var/lib/docker-registry\\n"
        "http:\\n"
        "  addr: :5000\\n"
        "  headers:\\n"
        "    X-Content-Type-Options: [nosniff]\\n"
        "health:\\n"
        "  storagedriver:\\n"
        "    enabled: true\\n"
        "    interval: 10s\\n"
        "    threshold: 3\\n"
        "proxy:\\n"
        "  remoteurl: https://registry-1.docker.io\\n"
    )

    config_cmd = (
        f"printf '{registry_conf}' > /etc/docker/registry/config.yml; "
        "systemctl restart docker-registry && systemctl enable docker-registry"
    )
    exit_code, out = ssh_mgr.execute_command(
        config_cmd, lambda x: None, check_exit_code=False
    )
    ssh_mgr.close()

    if exit_code != 0:
        logger.error(f"Failed to configure and restart docker-registry: {out}")
        return False

    logger.info("✅ docker-registry pull-through mirror service is active and running.")
    return True


def main() -> None:
    """Entry point for registry gateway setup."""
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Set up dedicated Docker registry cache mirror on Proxmox vmbr1"
    )
    parser.add_argument("--node", default=os.getenv("PROXMOX_NODE", "pve"))
    parser.add_argument("--bridge", default=os.getenv("PROXMOX_BRIDGE", "vmbr1"))
    parser.add_argument(
        "--password", default=os.getenv("PROXMOX_VM_PASSWORD", "SaxGitaar31!")
    )
    args = parser.parse_args()

    client = ProxmoxClient(
        host=os.getenv("PROXMOX_HOST", ""),
        user=os.getenv("PROXMOX_USER", "root@pam"),
        token_id=os.getenv("PROXMOX_TOKEN_ID", ""),
        token_secret=os.getenv("PROXMOX_TOKEN_SECRET", ""),
    )

    ensure_gateway_container(
        client=client, node=args.node, bridge=args.bridge, vm_pass=args.password
    )
    success = configure_registry_service(vm_pass=args.password)
    if not success:
        logger.error("Failed to configure test registry gateway.")
        sys.exit(1)

    logger.info("==================================================")
    logger.info("🎉 Proxmox Test Registry Mirror Gateway Complete!")
    logger.info(
        f"   Registry Port: {REGISTRY_PORT} (http://{GATEWAY_IP}:{REGISTRY_PORT})"
    )
    logger.info("   Upstream Hub:  https://registry-1.docker.io")
    logger.info(f"   Default Route: {GATEWAY_ROUTER}")
    logger.info("==================================================")


if __name__ == "__main__":
    main()
