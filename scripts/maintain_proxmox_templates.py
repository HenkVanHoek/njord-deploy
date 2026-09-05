#!/usr/bin/env python3
"""Maintains and updates dedicated Proxmox test templates.

Builds, updates, pre-caches base images, and converts to templates for:
  - 911: Docker on VM (QEMU)
  - 912: Docker on LXC (Container)
  - 913: Podman on VM (QEMU)
  - 914: Podman on LXC (Container)
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))

from managers.ssh_manager import SSHManager  # noqa: E402
from utils.container_engine import ContainerEngine  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("maintain_templates")

# Top dependency base images to pre-cache in templates
COMMON_BASE_IMAGES = [
    "docker.io/library/alpine:latest",
    "docker.io/library/postgres:15-alpine",
    "docker.io/library/postgres:16-alpine",
    "docker.io/library/redis:alpine",
    "docker.io/library/mariadb:lts",
    "docker.io/library/traefik:v3.1",
]


def setup_client() -> ProxmoxClient:
    """Initializes ProxmoxClient from environment variables."""
    load_dotenv()
    host = os.getenv("PROXMOX_HOST", "")
    user = os.getenv("PROXMOX_USER", "root@pam")
    token_id = os.getenv("PROXMOX_TOKEN_ID", "")
    token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")
    verify_ssl = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"

    if not (host and token_id and token_secret):
        logger.error("Proxmox API credentials missing in .env")
        sys.exit(1)

    return ProxmoxClient(
        host=host,
        user=user,
        token_id=token_id,
        token_secret=token_secret,
        verify_ssl=verify_ssl,
    )


def check_host_memory_headroom(
    client: ProxmoxClient, node: str, min_free_mb: int = 3584
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
                "Aborting template build to protect host and operational VMs!"
            )
            return False
        return True
    except Exception as ex:
        logger.warning(f"Could not check host memory status: {ex}")
        return True


def cleanup_stale_test_instances(client: ProxmoxClient, node: str) -> None:
    """Finds and destroys any leftover test VMs or LXC containers from aborted runs."""
    stale_prefixes = (
        "pish-test-",
        "pish-diag-",
        "njord-test-",
        "test-vm-",
        "test-lxc-",
    )
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
        for lxc in lxcs:
            lxc_name = lxc.get("name", "")
            vmid = lxc.get("vmid")
            if any(lxc_name.startswith(pfx) for pfx in stale_prefixes) and vmid:
                logger.warning(
                    f"Found stale test LXC '{lxc_name}' (VMID: {vmid}). Cleaning up..."
                )
                # noinspection PyBroadException
                try:
                    client.stop_lxc(node, vmid)
                    time.sleep(2)
                except Exception:  # nosec B110
                    pass
                # noinspection PyBroadException
                try:
                    client.destroy_lxc(node, vmid)
                    logger.info(f"Stale test LXC {vmid} destroyed.")
                except Exception as ex:
                    logger.warning(f"Could not destroy stale test LXC {vmid}: {ex}")
    except Exception as ex:
        logger.warning(f"Error checking for stale test LXCs: {ex}")


def wait_task(client: ProxmoxClient, node: str, upid: str, timeout: int = 240) -> None:
    """Polls Proxmox task until completion."""
    start = time.time()
    while time.time() - start < timeout:
        # noinspection PyBroadException
        try:
            res = client.get(f"nodes/{node}/tasks/{upid}/status")
            data = res.get("data", {})
            if data.get("status") == "stopped":
                exitstatus = data.get("exitstatus")
                if exitstatus == "OK" or (
                    isinstance(exitstatus, str) and exitstatus.startswith("WARNINGS")
                ):
                    return
                raise RuntimeError(f"Task failed: {exitstatus}")
        except Exception as exc:
            if "Task failed" in str(exc):
                raise
        time.sleep(2)
    raise TimeoutError(f"Task {upid} timed out after {timeout}s")


def wait_ip(
    client: ProxmoxClient,
    node: str,
    vmid: int,
    is_lxc: bool = False,
    timeout: int = 120,
) -> str:
    """Waits for instance IP address."""
    start = time.time()
    while time.time() - start < timeout:
        # noinspection PyBroadException
        try:
            if is_lxc:
                res = client.get(f"nodes/{node}/lxc/{vmid}/interfaces")
                for iface in res.get("data", []):
                    if iface.get("name") in ("eth0", "net0"):
                        inet = iface.get("inet", "")
                        if inet and "/" in inet:
                            return inet.split("/")[0]
            else:
                ip = client.get_vm_ip(node, vmid)
                if ip:
                    return ip
        except Exception as e:
            logger.debug(f"IP retrieval attempt failed: {e}")
        time.sleep(3)
    raise TimeoutError(f"Unable to retrieve IP for VMID {vmid}")


def pre_cache_images(
    ssh: SSHManager,
    engine: str,
    username: str,
    sudo_pfx: str,
    images: List[str],
) -> None:
    """Pre-caches common container images in the template."""
    logger.info(f"Pre-caching {len(images)} base container images ({engine})...")
    for img in images:
        logger.info(f"  📥 Pulling {img}...")
        if engine == "podman" and username != "root":
            cmd = (
                f"XDG_RUNTIME_DIR=/run/user/$(id -u) "
                f"podman pull -q {img} 2>/dev/null || true"
            )
        else:
            cmd = f"{sudo_pfx}{engine} pull -q {img} 2>/dev/null || true"
        ssh.execute_command(cmd, lambda msg: logger.info(f"     {msg}"))


def wait_for_apt_lock(ssh: SSHManager, sudo_pfx: str = "") -> None:
    """Waits until background cloud-init and systemd apt timers release dpkg locks."""
    logger.info("Waiting for cloud-init and background apt locks to release...")
    wait_script = (
        "cloud-init status --wait 2>/dev/null || true; "
        "systemctl stop apt-daily.service apt-daily-upgrade.service "
        "apt-daily.timer apt-daily-upgrade.timer unattended-upgrades.service "
        "2>/dev/null || true; "
        "systemctl kill --kill-who=all apt-daily.service apt-daily-upgrade.service "
        "unattended-upgrades.service 2>/dev/null || true; "
        "while fuser /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock "
        "/var/lib/apt/lists/lock >/dev/null 2>&1; do sleep 2; done"
    )
    ssh.execute_command(f"{sudo_pfx}sh -c '{wait_script}'", lambda msg: None)


def sanitize_instance(ssh: SSHManager, sudo_pfx: str = "") -> None:
    """Cleans machine ID, logs, and temporary caches before templating."""
    logger.info("Sanitizing instance filesystem before template conversion...")
    clean_script = (
        "cloud-init clean --logs --reboot 2>/dev/null || true; "
        "systemctl stop apt-daily.service apt-daily-upgrade.service "
        "apt-daily.timer apt-daily-upgrade.timer unattended-upgrades.service "
        "2>/dev/null || true; "
        "systemctl disable apt-daily.timer apt-daily-upgrade.timer "
        "unattended-upgrades.service 2>/dev/null || true; "
        "systemctl mask apt-daily.service apt-daily-upgrade.service "
        "unattended-upgrades.service 2>/dev/null || true; "
        "truncate -s 0 /etc/machine-id 2>/dev/null || true; "
        "rm -f /var/lib/dbus/machine-id 2>/dev/null || true; "
        "apt-get clean 2>/dev/null || true; "
        "chattr -i /etc/resolv.conf 2>/dev/null || true; "
        "printf 'nameserver 1.1.1.1\\nnameserver 8.8.8.8\\n' > /etc/resolv.conf "
        "2>/dev/null || true; "
        "rm -rf /tmp/* /var/tmp/* /var/log/*.log /var/log/journal/* "
        "/var/cache/apt/archives/* /root/.bash_history "
        "/home/*/.bash_history 2>/dev/null || true"
    )
    ssh.execute_command(f"{sudo_pfx}sh -c '{clean_script}'", lambda msg: None)


def build_vm_template(
    client: ProxmoxClient,
    node: str,
    base_template_id: int,
    target_template_id: int,
    engine: str,
    name: str,
    vm_user: str = "pivm",
    vm_pass: Optional[str] = None,
    ram_mb: int = 4096,
    cores: int = 4,
) -> bool:
    """Builds and updates a dedicated VM template."""
    vm_pass = vm_pass or os.getenv("PROXMOX_VM_PASSWORD") or ""
    logger.info("=" * 60)
    logger.info(
        f"🛠️ Building VM Template {target_template_id} ({name}) "
        f"from Base {base_template_id}..."
    )
    logger.info("=" * 60)

    # 1. Destroy existing target template/VM if present
    # noinspection PyBroadException
    try:
        client.stop_vm(node, target_template_id)
        time.sleep(2)
    except Exception as e:
        logger.debug(
            f"Target VM {target_template_id} already stopped or nonexistent: {e}"
        )
    # noinspection PyBroadException
    try:
        del_res = client.destroy_vm(node, target_template_id)
        upid = del_res.get("data")
        if isinstance(upid, str):
            wait_task(client, node, upid)
        logger.info(f"Replaced previous template {target_template_id}.")
    except Exception as e:
        logger.debug(f"Target VM {target_template_id} cleanup skipped: {e}")

    # 2. Clone base template directly to target_template_id
    logger.info(
        f"Cloning base template {base_template_id} to VM {target_template_id}..."
    )
    clone_res = client.clone_vm(
        node=node,
        vmid=base_template_id,
        newid=target_template_id,
        name=name,
        full=True,
    )
    upid = clone_res.get("data")
    if isinstance(upid, str):
        wait_task(client, node, upid)

    # 3. Configure VM parameters and resize disk
    client.configure_vm(
        node=node,
        vmid=target_template_id,
        config_data={
            "ciuser": vm_user,
            "cipassword": vm_pass,
            "cores": cores,
            "memory": ram_mb,
            "balloon": 2048,
            "agent": "enabled=1",
        },
    )
    try:
        resize_res = client.put(
            f"nodes/{node}/qemu/{target_template_id}/resize",
            data={"disk": "scsi0", "size": "+40G"},
        )
        if resize_res.get("data"):
            wait_task(client, node, resize_res["data"])
    except Exception as re_err:
        logger.warning(f"Could not resize VM disk: {re_err}")

    # 4. Start VM & wait for IP
    logger.info(f"Starting VM {target_template_id}...")
    client.start_vm(node, target_template_id)
    vm_ip = wait_ip(client, node, target_template_id, is_lxc=False)
    logger.info(f"VM {target_template_id} online at IP: {vm_ip}")

    # 5. Connect via SSH
    ssh = SSHManager(
        hostname=vm_ip,
        username=vm_user,
        password=vm_pass,
        allow_auto_add=True,
        load_system_keys=False,
    )
    connected = False
    for _ in range(15):
        connected, _ = ssh.connect()
        if connected:
            break
        time.sleep(3)

    if not connected:
        logger.error(f"Failed to connect to VM {target_template_id} via SSH")
        return False

    try:
        sudo_pfx = "" if vm_user == "root" else f"echo '{vm_pass}' | sudo -S "

        # Wait for systemd/cloud-init apt lock release
        wait_for_apt_lock(ssh, sudo_pfx=sudo_pfx)

        # OS Update
        logger.info("Updating Debian base packages (apt-get dist-upgrade)...")
        ssh.execute_command(
            f"{sudo_pfx}env DEBIAN_FRONTEND=noninteractive apt-get update -qq && "
            f"{sudo_pfx}env DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y -qq",
            lambda msg: logger.info(f"  [update] {msg}"),
        )

        # Grow partition
        grow_cmd = (
            f"{sudo_pfx}env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
            "cloud-guest-utils fdisk parted e2fsprogs 2>/dev/null || true; "
            f"{sudo_pfx}growpart /dev/sda 1 2>/dev/null || true; "
            f"{sudo_pfx}resize2fs /dev/sda1 2>/dev/null || true"
        )
        ssh.execute_command(grow_cmd, lambda msg: logger.info(f"  [disk] {msg}"))

        # Install Engine
        logger.info(f"Installing {engine.upper()} on VM...")
        engine_helper = ContainerEngine(engine)
        for cmd in engine_helper.get_provisioning_commands(username=vm_user):
            clean_cmd = (
                cmd.replace("sudo ", sudo_pfx) if "sudo " in cmd else f"{sudo_pfx}{cmd}"
            )
            code, out = ssh.execute_command(
                clean_cmd, lambda msg: logger.info(f"  [engine] {msg}")
            )
            if code != 0:
                logger.error(f"Engine provisioning failed on: {clean_cmd}")
                raise RuntimeError(f"Engine command failed: {clean_cmd} -> {out}")

        # Tune SSH limits
        ssh.execute_command(
            f"{sudo_pfx}sh -c \"printf 'MaxStartups 100:30:200\\n"
            "MaxSessions 100\\nClientAliveInterval 30\\n' > "
            '/etc/ssh/sshd_config.d/njorddeploy-limits.conf" 2>/dev/null || true; '
            f"{sudo_pfx}systemctl reload ssh 2>/dev/null || "
            f"{sudo_pfx}systemctl restart ssh 2>/dev/null || true",
            lambda msg: None,
        )

        # Free up port 53 (disable systemd-resolved)
        ssh.execute_command(
            f"{sudo_pfx}sh -c \"printf '[Resolve]\\n"
            "DNSStubListener=no\\nMulticastDNS=no\\nLLMNR=no\\n' > "
            '/etc/systemd/resolved.conf" 2>/dev/null || true; '
            f"{sudo_pfx}chmod 000 /lib/systemd/systemd-resolved "
            "/usr/lib/systemd/systemd-resolved 2>/dev/null || true; "
            f"{sudo_pfx}pkill -9 -f systemd-resolve 2>/dev/null || true; "
            f"{sudo_pfx}pkill -9 -f dnsmasq 2>/dev/null || true; "
            f"{sudo_pfx}systemctl stop systemd-resolved "
            "systemd-resolved.socket 2>/dev/null || true; "
            f"{sudo_pfx}systemctl disable --now systemd-resolved "
            "systemd-resolved.socket 2>/dev/null || true; "
            f"{sudo_pfx}systemctl mask systemd-resolved "
            "systemd-resolved.socket 2>/dev/null || true; "
            f"{sudo_pfx}chattr -i /etc/resolv.conf 2>/dev/null || true; "
            f"{sudo_pfx}rm -f /etc/resolv.conf; "
            f"{sudo_pfx}sh -c \"printf 'nameserver 1.1.1.1\\nnameserver 8.8.8.8\\n' > "
            '/etc/resolv.conf"; '
            f"{sudo_pfx}chattr +i /etc/resolv.conf 2>/dev/null || true",
            lambda msg: None,
        )

        # Pre-cache Images
        pre_cache_images(ssh, engine, vm_user, sudo_pfx, COMMON_BASE_IMAGES)

        # Sanitize
        sanitize_instance(ssh, sudo_pfx=sudo_pfx)
    finally:
        ssh.close()

    # 6. Stop VM and Convert to Template
    logger.info(f"Stopping VM {target_template_id}...")
    client.stop_vm(node, target_template_id)
    for _ in range(15):
        time.sleep(1)
        stat = client.get_vm_status(node, target_template_id).get("data", {})
        if stat.get("status") == "stopped":
            break

    logger.info(f"Converting VM {target_template_id} to Proxmox Template...")
    client.convert_to_template(node, target_template_id, is_lxc=False)
    logger.info(f"✅ VM Template {target_template_id} ({name}) created successfully!")
    return True


def build_lxc_template(
    client: ProxmoxClient,
    node: str,
    target_template_id: int,
    engine: str,
    name: str,
    password: Optional[str] = None,
    ram_mb: int = 2048,
    cores: int = 4,
) -> bool:
    """Builds and updates a dedicated LXC template."""
    password = password or os.getenv("PROXMOX_VM_PASSWORD") or ""
    logger.info("=" * 60)
    logger.info(
        f"🛠️ Building LXC Template {target_template_id} ({name}) "
        f"for {engine.upper()}..."
    )
    logger.info("=" * 60)

    # 1. Destroy existing target template/LXC if present
    # noinspection PyBroadException
    try:
        client.stop_lxc(node, target_template_id)
        time.sleep(2)
    except Exception as e:
        logger.debug(
            f"Target LXC {target_template_id} already stopped or nonexistent: {e}"
        )
    # noinspection PyBroadException
    try:
        del_res = client.destroy_lxc(node, target_template_id)
        upid = del_res.get("data")
        if isinstance(upid, str):
            wait_task(client, node, upid)
        logger.info(f"Replaced previous template {target_template_id}.")
    except Exception as e:
        logger.debug(f"Target LXC {target_template_id} cleanup skipped: {e}")

    # 2. Get SSH Key & Find suitable Debian template
    from create_proxmox_lxc import (  # type: ignore[import-not-found]
        find_suitable_template,
    )

    dummy_manager = SSHManager(
        hostname="localhost", username="root", password=""
    )  # nosec B106
    pubkey = dummy_manager.get_public_key_string()

    ostemplate = find_suitable_template(client, node)
    logger.info(f"Using base LXC template: {ostemplate}")

    # 3. Create fresh LXC container directly as target_template_id
    lxc_data = {
        "vmid": target_template_id,
        "ostemplate": ostemplate,
        "hostname": name,
        "cores": cores,
        "memory": ram_mb,
        "swap": 512,
        "rootfs": "local-lvm:20",
        "net0": "name=eth0,bridge=vmbr0,ip=dhcp,firewall=0",
        "unprivileged": 1,
        "features": "nesting=1",
        "password": password,
        "ssh-public-keys": pubkey,
        "start": 1,
    }
    create_res = client.create_lxc(node, lxc_data)
    upid = create_res.get("data")
    if isinstance(upid, str):
        wait_task(client, node, upid)

    lxc_ip = wait_ip(client, node, target_template_id, is_lxc=True)
    logger.info(f"LXC {target_template_id} online at IP: {lxc_ip}")
    time.sleep(5)

    # 4. Connect via SSH
    ssh = SSHManager(
        hostname=lxc_ip,
        username="root",
        password=password,
        allow_auto_add=True,
        load_system_keys=False,
    )
    connected = False
    for _ in range(15):
        connected, _ = ssh.connect()
        if connected:
            break
        time.sleep(3)

    if not connected:
        logger.error(f"Failed to connect to LXC {target_template_id} via SSH")
        return False

    try:
        # Wait for any background apt lock release
        wait_for_apt_lock(ssh)

        # OS Update
        logger.info("Updating Debian LXC packages...")
        ssh.execute_command(
            "env DEBIAN_FRONTEND=noninteractive apt-get update -qq && "
            "env DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y -qq && "
            "env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
            "curl jq openssh-server",
            lambda msg: logger.info(f"  [update] {msg}"),
        )

        # Install Engine
        logger.info(f"Installing {engine.upper()} in LXC...")
        engine_helper = ContainerEngine(engine)
        for cmd in engine_helper.get_provisioning_commands(username="root"):
            code, out = ssh.execute_command(
                cmd, lambda msg: logger.info(f"  [engine] {msg}")
            )
            if code != 0:
                logger.error(f"Engine provisioning failed on: {cmd}")
                raise RuntimeError(f"Engine command failed: {cmd} -> {out}")

        # SSH Limits, PAM, and PermitRootLogin
        ssh.execute_command(
            "sed -i 's/^session.*pam_systemd.so/# &/' /etc/pam.d/common-session "
            "/etc/pam.d/sshd 2>/dev/null || true; "
            "systemctl mask systemd-logind.service 2>/dev/null || true; "
            "sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' "
            "/etc/ssh/sshd_config 2>/dev/null || true",
            lambda msg: None,
        )
        ssh.execute_command(
            "sh -c \"printf 'MaxStartups 100:30:200\\n"
            "MaxSessions 100\\nClientAliveInterval 30\\n' > "
            '/etc/ssh/sshd_config.d/njorddeploy-limits.conf" 2>/dev/null || true; '
            "systemctl reload ssh 2>/dev/null || "
            "systemctl restart ssh 2>/dev/null || true",
            lambda msg: None,
        )

        # Free up port 53 (disable systemd-resolved)
        ssh.execute_command(
            "printf '[Resolve]\\nDNSStubListener=no\\nMulticastDNS=no\\n"
            "LLMNR=no\\n' > /etc/systemd/resolved.conf 2>/dev/null || true; "
            "chmod 000 /lib/systemd/systemd-resolved "
            "/usr/lib/systemd/systemd-resolved 2>/dev/null || true; "
            "pkill -9 -f systemd-resolve 2>/dev/null || true; "
            "pkill -9 -f dnsmasq 2>/dev/null || true; "
            "systemctl stop systemd-resolved systemd-resolved.socket "
            "2>/dev/null || true; "
            "systemctl disable --now systemd-resolved "
            "systemd-resolved.socket 2>/dev/null || true; "
            "systemctl mask systemd-resolved systemd-resolved.socket "
            "2>/dev/null || true; "
            "chattr -i /etc/resolv.conf 2>/dev/null || true; "
            "rm -f /etc/resolv.conf; "
            "printf 'nameserver 1.1.1.1\\nnameserver 8.8.8.8\\n' > "
            "/etc/resolv.conf; "
            "chattr +i /etc/resolv.conf 2>/dev/null || true",
            lambda msg: None,
        )

        # Pre-cache Images
        pre_cache_images(ssh, engine, "root", "", COMMON_BASE_IMAGES)

        # Sanitize
        sanitize_instance(ssh)
    finally:
        ssh.close()

    # 5. Stop and Convert to Template
    logger.info(f"Stopping LXC {target_template_id}...")
    client.stop_lxc(node, target_template_id)
    for _ in range(15):
        time.sleep(1)
        stat = client.get_lxc_status(node, target_template_id).get("data", {})
        if stat.get("status") == "stopped":
            break

    logger.info(f"Converting LXC {target_template_id} to Proxmox Template...")
    client.convert_to_template(node, target_template_id, is_lxc=True)
    logger.info(f"✅ LXC Template {target_template_id} ({name}) created successfully!")
    return True


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Builds and updates dedicated NjordDeploy Proxmox templates."
    )
    parser.add_argument(
        "--target",
        choices=["all", "docker-vm", "docker-lxc", "podman-vm", "podman-lxc"],
        default="all",
        help="Which template(s) to maintain (default: all)",
    )
    parser.add_argument(
        "--node", default="pve", help="Proxmox node name (default: pve)"
    )
    parser.add_argument(
        "--base-vm-template",
        type=int,
        default=902,
        help="Base Debian VM template ID (default: 902)",
    )
    parser.add_argument(
        "--docker-vm-id",
        type=int,
        default=911,
        help="Docker VM Template ID (default: 911)",
    )
    parser.add_argument(
        "--docker-lxc-id",
        type=int,
        default=912,
        help="Docker LXC Template ID (default: 912)",
    )
    parser.add_argument(
        "--podman-vm-id",
        type=int,
        default=913,
        help="Podman VM Template ID (default: 913)",
    )
    parser.add_argument(
        "--podman-lxc-id",
        type=int,
        default=914,
        help="Podman LXC Template ID (default: 914)",
    )

    args = parser.parse_args()
    client = setup_client()

    cleanup_stale_test_instances(client, args.node)
    if not check_host_memory_headroom(client, args.node, min_free_mb=3584):
        sys.exit(1)

    target = args.target
    success = True
    if target in ("all", "docker-vm"):
        if not build_vm_template(
            client=client,
            node=args.node,
            base_template_id=args.base_vm_template,
            target_template_id=args.docker_vm_id,
            engine="docker",
            name="njorddeploy-docker-vm-template",
        ):
            success = False

    if target in ("all", "podman-vm"):
        if not build_vm_template(
            client=client,
            node=args.node,
            base_template_id=args.base_vm_template,
            target_template_id=args.podman_vm_id,
            engine="podman",
            name="njorddeploy-podman-vm-template",
        ):
            success = False

    if target in ("all", "docker-lxc"):
        if not build_lxc_template(
            client=client,
            node=args.node,
            target_template_id=args.docker_lxc_id,
            engine="docker",
            name="njorddeploy-docker-lxc-template",
        ):
            success = False

    if target in ("all", "podman-lxc"):
        if not build_lxc_template(
            client=client,
            node=args.node,
            target_template_id=args.podman_lxc_id,
            engine="podman",
            name="njorddeploy-podman-lxc-template",
        ):
            success = False

    if not success:
        logger.error("❌ One or more template builds failed.")
        sys.exit(1)

    logger.info("🎉 All selected templates maintained and ready!")


if __name__ == "__main__":
    main()
