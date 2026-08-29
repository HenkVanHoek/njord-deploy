# scripts/build_linux_binary_proxmox.py
"""
Universal Linux Release Binary Builder on Proxmox VE
-----------------------------------------------------
Provisions a temporary, clean Debian 12 LXC container on Proxmox VE,
uploads the project source tree, and runs PyInstaller for all 3 NjordDeploy
applications inside the Debian 12 environment:
1. NjordDeployConfigurator
2. NjordDeployEditor
3. NjordDeployProxmoxTest

This guarantees maximum backwards compatibility (GLIBC 2.36) across all
Linux distributions (Debian 12/13, Ubuntu 22.04/24.04, Raspberry Pi OS, etc.).
"""

import io
import logging
import os
import sys
import tarfile
import time
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from managers.ssh_manager import SSHManager  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("build_linux_binary_proxmox")


def main():
    load_dotenv(project_root / ".env")

    host = os.getenv("PROXMOX_HOST") or "https://192.168.178.51:8006"
    user = os.getenv("PROXMOX_USER") or "root@pam"
    token_id = os.getenv("PROXMOX_TOKEN_ID") or ""
    token_secret = os.getenv("PROXMOX_TOKEN_SECRET") or ""

    if not token_id or not token_secret:
        logger.error("Proxmox API credentials missing in .env.")
        sys.exit(1)

    client = ProxmoxClient(
        host=host,
        user=user,
        token_id=token_id,
        token_secret=token_secret,
        verify_ssl=False,
    )
    node = os.getenv("PROXMOX_NODE", "pve")

    vmid_val = client.get_next_vmid()
    if not vmid_val:
        logger.error("Failed to allocate VMID from Proxmox.")
        sys.exit(1)

    vmid = vmid_val
    logger.info(f"Allocating Debian 12 Build Container CTID {vmid} on Proxmox...")

    dummy_mgr = SSHManager(
        hostname="localhost", username="test", password="key"
    )  # nosec B106
    ssh_key_obj = dummy_mgr.get_ssh_key()
    ssh_public_key = f"{ssh_key_obj.get_name()} {ssh_key_obj.get_base64()}"
    vm_pass = (
        os.getenv("RELEASE_TEST_VM_PASSWORD")
        or os.getenv("PROXMOX_VM_PASSWORD")
        or "testpass"
    )

    create_data = {
        "vmid": vmid,
        "ostemplate": "local:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst",
        "cores": 4,
        "memory": 4096,
        "swap": 1024,
        "rootfs": "local-lvm:20",
        "net0": "name=eth0,bridge=vmbr0,firewall=0,ip=dhcp",
        "features": "nesting=1",
        "unprivileged": 1,
        "password": vm_pass,
        "ssh-public-keys": ssh_public_key,
        "start": 1,
    }

    res = client.post(f"nodes/{node}/lxc", data=create_data)
    upid = res.get("data")
    if upid:
        while True:
            t_status = client.get(f"nodes/{node}/tasks/{upid}/status").get("data", {})
            if t_status.get("status") == "stopped":
                break
            time.sleep(2)

    logger.info(f"Container {vmid} created. Waiting for IP...")
    ct_ip = None
    for _ in range(20):
        # noinspection PyBroadException
        try:
            ifaces_res = client.get(f"nodes/{node}/lxc/{vmid}/interfaces")
            for iface in ifaces_res.get("data", []):
                if iface.get("name") in ("eth0", "net0"):
                    inet = iface.get("inet", "")
                    if inet and "/" in inet:
                        first_ip, *_ = inet.split("/")
                        if first_ip and not first_ip.startswith("127."):
                            ct_ip = first_ip
                            break
        except Exception as e:
            logger.debug(f"IP resolution probe: {e}")
        if ct_ip:
            break
        time.sleep(3)

    if not ct_ip:
        logger.error("Timed out waiting for build container IP.")
        client.delete(f"nodes/{node}/lxc/{vmid}", params={"purge": 1})
        sys.exit(1)

    logger.info(f"Build Container online at {ct_ip}. Connecting via SSH...")
    time.sleep(5)
    ssh = SSHManager(
        hostname=ct_ip,
        username="root",
        password=vm_pass,
        allow_auto_add=True,
        load_system_keys=False,
    )
    for _ in range(6):
        ok, _ = ssh.connect()
        if ok:
            break
        time.sleep(5)

    logger.info("Packaging local source code archive...")
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        for folder in [
            "src",
            "config",
            "component_templates",
            "ansible",
            "docs",
            "images",
            "scripts",
            "tests",
        ]:
            fpath = project_root / folder
            if fpath.exists():
                tar.add(fpath, arcname=folder)
        for f in [
            "NjordDeployConfigurator.spec",
            "NjordDeployEditor.spec",
            "NjordDeployProxmoxTest.spec",
            "run_configurator.py",
            "run_editor.py",
            "run_proxmox_gui.py",
            "pyproject.toml",
            "README.md",
        ]:
            fpath = project_root / f
            if fpath.exists():
                tar.add(fpath, arcname=f)

    tar_bytes = tar_buffer.getvalue()
    logger.info(f"Uploading source archive ({len(tar_bytes)} bytes)...")
    ssh.upload_content(tar_bytes, "source.tar.gz")
    ssh.execute_command(
        "mkdir -p /root/build && tar -xzf source.tar.gz -C /root/build",
        lambda x: None,
    )

    logger.info("Setting up Python build environment in Debian 12 container...")
    cmd_prep = (
        "apt-get update -qq && "
        "apt-get install -y -qq python3-full python3-pip python3-venv "
        "build-essential && "
        "cd /root/build && "
        "python3 -m venv .venv && "
        ".venv/bin/pip install --upgrade pip -q && "
        ".venv/bin/pip install -e . pyinstaller waitress requests "
        "pyinstaller-hooks-contrib -q"
    )
    ssh.execute_command(
        cmd_prep, lambda msg: logger.info(f"[BUILD-DEPS] {msg.strip()}")
    )

    specs = [
        ("NjordDeployConfigurator", "NjordDeployConfigurator.spec"),
        ("NjordDeployEditor", "NjordDeployEditor.spec"),
        ("NjordDeployProxmoxTest", "NjordDeployProxmoxTest.spec"),
    ]

    local_dist = project_root / "dist"
    local_dist.mkdir(exist_ok=True)
    sftp = ssh.client.open_sftp()

    for bin_name, spec_file in specs:
        logger.info(f"Compiling {bin_name} via PyInstaller on Debian 12...")
        cmd_build = f"cd /root/build && .venv/bin/pyinstaller {spec_file} --noconfirm"
        exit_code, _ = ssh.execute_command(
            cmd_build, lambda msg: logger.info(f"[{bin_name}] {msg.strip()}")
        )
        if exit_code == 0:
            target_bin = local_dist / bin_name
            sftp.get(f"/root/build/dist/{bin_name}", str(target_bin))
            target_bin.chmod(0o755)
            logger.info(
                f"✅ Universal binary saved: {target_bin} "
                f"({target_bin.stat().st_size} bytes)"
            )
        else:
            logger.error(f"❌ Failed to build {bin_name}")

    sftp.close()

    logger.info(f"Cleaning up build container {vmid}...")
    client.post(f"nodes/{node}/lxc/{vmid}/status/stop")
    time.sleep(2)
    client.delete(f"nodes/{node}/lxc/{vmid}", params={"purge": 1})
    logger.info("Build container destroyed. All binaries ready in dist/.")


if __name__ == "__main__":
    main()
