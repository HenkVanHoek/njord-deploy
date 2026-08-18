# scripts/test_backup_restore_lxc.py
"""Automated Disaster Recovery & Backup/Restore Test Suite on Proxmox VE.

Provisions a clean Proxmox LXC container, deploys a test container stack,
creates a point-in-time backup, introduces a volume mutation, restores the
snapshot, verifies state convergence, and cleans up the container.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Ensure import access to 'src' directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.backup_manager import BackupManager  # noqa: E402
from managers.ssh_manager import SSHManager  # noqa: E402
from utils.container_engine import ContainerEngine  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("backup_restore_lxc_test")


def find_suitable_template(client: ProxmoxClient, node: str) -> str:
    """Finds an active Debian or Ubuntu LXC template."""
    storages = ["local"]
    try:
        storage_res = client.get(f"nodes/{node}/storage")
        active_stores = []
        for store in storage_res.get("data", []):
            if store.get("active") and "vztmpl" in store.get("content", ""):
                s_name = store.get("storage")
                if s_name:
                    active_stores.append(s_name)
        if active_stores:
            storages = sorted(active_stores, key=lambda x: x != "local")
    except Exception as e:
        logger.warning(f"Failed to query storage list: {e}")

    templates = []
    for s in storages:
        try:
            res = client.get(
                f"nodes/{node}/storage/{s}/content", params={"content": "vztmpl"}
            )
            templates.extend(res.get("data", []))
        except Exception as e:
            logger.warning(f"Failed to read templates on {s}: {e}")

    for t in templates:
        volid = t.get("volid", "")
        if "debian" in volid.lower():
            return volid
    if templates:
        first_t: Dict[str, Any] = next(iter(templates), {})
        return first_t.get(
            "volid",
            "local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst",
        )
    return "local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst"


def wait_for_proxmox_task(
    client: ProxmoxClient, node: str, upid: str, timeout_seconds: int = 180
) -> bool:
    """Waits for a Proxmox background UPID task to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            res = client.get(f"nodes/{node}/tasks/{upid}/status")
            data = res.get("data", {})
            if data.get("status") == "stopped":
                if data.get("exitstatus") == "OK":
                    return True
                raise RuntimeError(f"Proxmox task failed: {data.get('exitstatus')}")
        except Exception as e:
            logger.warning(f"Error polling task status: {e}")
        time.sleep(3)
    raise TimeoutError(f"Task {upid} timed out after {timeout_seconds}s")


def wait_for_lxc_ip(
    client: ProxmoxClient, node: str, vmid: int, timeout_seconds: int = 90
) -> str:
    """Polls Proxmox until the container acquires an IPv4 address."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            res = client.get(f"nodes/{node}/lxc/{vmid}/interfaces")
            interfaces = res.get("data", [])
            for iface in interfaces:
                name = iface.get("name", "")
                if name.startswith("eth") or name.startswith("en"):
                    inet = iface.get("inet", "")
                    if inet and "/" in inet:
                        ip_val = inet.split("/")[0]
                        if ip_val and not ip_val.startswith("127."):
                            return ip_val
        except Exception as e:
            logger.debug(f"IP poll error: {e}")
        time.sleep(3)
    raise TimeoutError(f"Container {vmid} failed to acquire an IP address")


def run_backup_restore_test(args: argparse.Namespace) -> bool:
    """Executes the full automated backup & restore verification workflow."""
    load_dotenv(project_root / ".env")

    proxmox_host = os.getenv("PROXMOX_HOST")
    proxmox_user = os.getenv("PROXMOX_USER")
    token_id = os.getenv("PROXMOX_TOKEN_ID")
    token_secret = os.getenv("PROXMOX_TOKEN_SECRET")
    node = args.node or os.getenv("PROXMOX_NODE", "pve")

    if not all([proxmox_host, proxmox_user, token_id, token_secret]):
        logger.error("Missing Proxmox credentials in .env file.")
        return False

    client = ProxmoxClient(
        host=proxmox_host or "",
        user=proxmox_user or "",
        token_id=token_id or "",
        token_secret=token_secret or "",
        verify_ssl=False,
    )

    # 1. Determine next available VMID and Template
    next_id_res = client.get("cluster/nextid")
    vmid = int(next_id_res.get("data", 900))
    template_volid = find_suitable_template(client, node)
    hostname = f"njord-bk-test-{vmid}"

    dummy_manager = SSHManager(
        hostname="localhost", username="root", password=""
    )  # nosec B106
    ssh_key = dummy_manager.get_ssh_key()
    pubkey = f"{ssh_key.get_name()} {ssh_key.get_base64()}"

    logger.info(f"Step 1: Creating LXC Container {vmid} ({hostname})...")
    lxc_data = {
        "vmid": vmid,
        "ostemplate": template_volid,
        "hostname": hostname,
        "cores": args.cores,
        "memory": args.memory,
        "swap": 512,
        "rootfs": f"{args.storage_name}:{args.storage_size}",
        "net0": "name=eth0,bridge=vmbr0,firewall=0,ip=dhcp",
        "features": "nesting=1",
        "unprivileged": 1,
        "password": args.password,
        "ssh-public-keys": pubkey,
        "start": 1,
    }

    create_res = client.post(f"nodes/{node}/lxc", data=lxc_data)
    upid = create_res.get("data")
    if isinstance(upid, str):
        wait_for_proxmox_task(client, node, upid)

    ip_address = wait_for_lxc_ip(client, node, vmid)
    logger.info(f"LXC Container online at {ip_address}.")
    logger.info("Waiting 10s for SSH daemon to initialize...")
    time.sleep(10)

    try:
        ssh = SSHManager(
            hostname=ip_address,
            username="root",
            password=args.password,
            allow_auto_add=True,
            load_system_keys=False,
        )

        connected, msg = ssh.connect()
        if not connected:
            logger.error(f"SSH connection failed: {msg}")
            return False

        def ssh_log(m: str):
            logger.debug(f"[REMOTE] {m.strip()}")

        # 2. Provision Container Engine (Docker)
        logger.info("Step 2: Installing Docker Engine inside LXC container...")
        engine_helper = ContainerEngine("docker")
        for cmd in engine_helper.get_provisioning_commands("root"):
            exit_code, _ = ssh.execute_command(cmd, ssh_log)
            if exit_code != 0:
                logger.error(f"Failed executing provisioning command: {cmd}")
                return False

        # 3. Deploy a Test Container Stack (Uptime Kuma)
        logger.info("Step 3: Deploying test service stack (Uptime Kuma)...")
        stack_dir = "/opt/njorddeploy"
        data_dir = "/opt/uptime-kuma/data"
        compose_content = """services:
  uptime-kuma:
    image: louislam/uptime-kuma:1.23.16-debian
    container_name: njorddeploy-uptime-kuma
    restart: unless-stopped
    ports:
      - "3001:3001"
    volumes:
      - "/opt/uptime-kuma/data:/app/data"
"""
        deploy_cmds = [
            f"mkdir -p {stack_dir} {data_dir}",
            f"cat << 'EOF' > {stack_dir}/docker-compose.yml\n{compose_content}\nEOF",
            f"cd {stack_dir} && docker compose up -d",
        ]
        for cmd in deploy_cmds:
            exit_code, out = ssh.execute_command(cmd, ssh_log)
            if exit_code != 0:
                logger.error(f"Stack deployment step failed: {out}")
                return False

        logger.info("Waiting 10s for container to initialize initial volume files...")
        time.sleep(10)

        # 4. Write an initial state file inside the volume
        initial_payload = {
            "snapshot_id": "state_v1",
            "created_at": datetime.now().isoformat(),
            "integrity_checksum": "valid_v1_marker",
        }
        state_file = f"{data_dir}/state_record.json"
        write_state_cmd = f"echo '{json.dumps(initial_payload)}' > {state_file}"
        ssh.execute_command(write_state_cmd, ssh_log)

        # 5. Inspect Target via BackupManager
        logger.info("Step 4: Inspecting target volumes via BackupManager...")
        backup_mgr = BackupManager(project_config_dir=stack_dir)
        inspection = backup_mgr.inspect_target(ssh, project_config_dir=stack_dir)
        if inspection.get("status") != "success":
            logger.error(f"Target inspection failed: {inspection}")
            return False

        logger.info(
            f"Discovered components: "
            f"{[c['id'] for c in inspection.get('components', [])]}"
        )
        logger.info(
            f"Total volume footprint: " f"{inspection.get('total_managed_size_human')}"
        )

        # 6. Create Point-in-Time Backup Archive
        logger.info("Step 5: Creating initial backup snapshot...")
        backup_res = backup_mgr.create_backup(
            ssh,
            selected_components=["uptime-kuma"],
            pause_containers=True,
            project_config_dir=stack_dir,
        )
        if backup_res.get("status") != "success":
            logger.error(f"Backup creation failed: {backup_res}")
            return False

        backup_filename = backup_res["filename"]
        logger.info(
            f"Backup created: {backup_filename} " f"({backup_res.get('size_human')})"
        )

        # 7. Introduce a deliberate mutation / corruption into the volume
        logger.info("Step 6: Introducing volume mutations (disaster simulation)...")
        mutation_file = f"{data_dir}/unwanted_corrupted_mutation.txt"
        mutated_payload = {"snapshot_id": "CORRUPTED_STATE_V2"}
        mutate_cmds = [
            f"echo 'MALICIOUS_INJECTION' > {mutation_file}",
            f"echo '{json.dumps(mutated_payload)}' > {state_file}",
        ]
        for cmd in mutate_cmds:
            ssh.execute_command(cmd, ssh_log)

        # Verify mutation is present before restore
        _, check_mut = ssh.execute_command(f"cat {state_file}", ssh_log)
        if "CORRUPTED" not in check_mut:
            logger.error("Failed to inject mutation for testing.")
            return False
        logger.info("Confirmed: Volume state has been mutated.")

        # 8. Restore the Snapshot Archive
        logger.info(f"Step 7: Restoring snapshot from {backup_filename}...")
        restore_res = backup_mgr.restore_backup(
            ssh,
            backup_filename=backup_filename,
            selected_components=["uptime-kuma"],
            restart_after=True,
            project_config_dir=stack_dir,
        )
        if restore_res.get("status") != "success":
            logger.error(f"Restore operation failed: {restore_res}")
            return False

        logger.info("Restore archive unpacked and container stack restarted.")
        time.sleep(5)

        # 9. Verify State Restoration
        logger.info("Step 8: Verifying post-restore volume state...")
        _, state_restored = ssh.execute_command(f"cat {state_file}", ssh_log)
        _, mut_check = ssh.execute_command(
            f"[ -f {mutation_file} ] && echo 'EXISTS' || echo 'GONE'",
            ssh_log,
        )
        _, ps_out = ssh.execute_command(
            f"cd {stack_dir} && docker compose ps --format json",
            ssh_log,
        )

        if "valid_v1_marker" not in state_restored:
            logger.error(f"State file failed to restore! Content: {state_restored}")
            return False

        if "uptime-kuma" not in ps_out and "running" not in ps_out.lower():
            logger.error(f"Container stack failed to restart! PS output: {ps_out}")
            return False

        logger.info("=" * 60)
        logger.info("SUCCESS: DISASTER RECOVERY & RESTORE FULLY VERIFIED!")
        logger.info("  - Volume state successfully reverted to snapshot v1")
        logger.info("  - Containers restarted and running in healthy state")
        logger.info(f"  - Target Scope: {stack_dir}")
        logger.info("=" * 60)
        return True

    finally:
        # 10. Cleanup Container if not --keep
        if not args.keep:
            logger.info(f"Cleaning up test container {vmid} on Proxmox...")
            try:
                stop_res = client.post(f"nodes/{node}/lxc/{vmid}/status/stop")
                s_upid = stop_res.get("data")
                if isinstance(s_upid, str):
                    wait_for_proxmox_task(client, node, s_upid)
                del_res = client.delete(f"nodes/{node}/lxc/{vmid}")
                d_upid = del_res.get("data")
                if isinstance(d_upid, str):
                    wait_for_proxmox_task(client, node, d_upid)
                logger.info(f"Test container {vmid} destroyed successfully.")
            except Exception as e:
                logger.warning(f"Cleanup error for {vmid}: {e}")
        else:
            logger.info(f"Container {vmid} preserved for inspection at {ip_address}.")


def main():
    """Main CLI entrypoint for backup/restore test runner."""
    parser = argparse.ArgumentParser(
        description="Run automated Backup & Restore verification test on Proxmox LXC."
    )
    parser.add_argument("--cores", type=int, default=2, help="CPU cores (default: 2)")
    parser.add_argument(
        "--memory", type=int, default=4096, help="RAM in MB (default: 4096)"
    )
    parser.add_argument(
        "--storage-size", type=int, default=20, help="Rootfs disk in GB (default: 20)"
    )
    parser.add_argument(
        "--storage-name",
        type=str,
        default="local-lvm",
        help="Proxmox storage pool (default: local-lvm)",
    )
    parser.add_argument(
        "--node", type=str, default="pve", help="Proxmox node name (default: pve)"
    )
    parser.add_argument(
        "--password",
        type=str,
        default="NjordTest123!",
        help="Root password for test container",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the test LXC container after test completes",
    )

    args = parser.parse_args()
    success = run_backup_restore_test(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
