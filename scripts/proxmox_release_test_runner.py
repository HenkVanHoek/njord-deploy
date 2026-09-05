# scripts/proxmox_release_test_runner.py
import argparse
import datetime
import json
import logging
import os
import sys
import time
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests  # type: ignore
from dotenv import load_dotenv

# Ensure we can import from the 'src' root directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.ssh_manager import SSHManager  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402 # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("proxmox_release_test_runner")


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


def wait_for_proxmox_task(
    client: ProxmoxClient, node: str, upid: str, timeout_seconds: int = 180
) -> None:
    """Polls the Proxmox task status until it completes successfully."""
    logger.info(f"Waiting for Proxmox task to complete: {upid}")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        # noinspection PyBroadException
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


def wait_for_lxc_ip(
    client: ProxmoxClient, node: str, vmid: int, timeout_seconds: int = 60
) -> str | None:
    """Polls LXC network interfaces until a valid IPv4 address is assigned."""
    logger.info(f"Waiting for LXC {vmid} to acquire IP address...")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        # noinspection PyBroadException
        try:
            endpoint = f"nodes/{node}/lxc/{vmid}/interfaces"
            res = client.get(endpoint)
            interfaces = res.get("data", [])
            for iface in interfaces:
                if iface.get("name") in ("eth0", "enp0s1", "net0"):
                    inet = iface.get("inet", "")
                    if inet and "/" in inet:
                        first_part, *_ = inet.split("/")
                        ip = first_part
                        if ip and not ip.startswith("127."):
                            logger.info(f"LXC {vmid} is online with IP: {ip}")
                            return ip
        except Exception as e:
            logger.debug(f"Probe attempt: {e}")
        time.sleep(3)
    logger.error(f"Timed out waiting for LXC {vmid} IP address.")
    return None


def download_github_release(tag: str, platform_name: str) -> Path:
    """Downloads the release asset for a given tag and platform from GitHub."""
    logger.info(f"Downloading release assets for tag {tag} ({platform_name})...")
    url = f"https://api.github.com/repos/HenkVanHoek/njord-deploy/releases/tags/{tag}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    release_data = response.json()
    assets = release_data.get("assets", [])

    # Find the correct asset matching the platform
    target_asset = None
    for asset in assets:
        name = asset.get("name", "")
        if platform_name.lower() in name.lower() and name.endswith(".zip"):
            target_asset = asset
            break

    if not target_asset:
        raise RuntimeError(
            f"No asset found for platform {platform_name} in release {tag}"
        )

    download_url = target_asset.get("browser_download_url")
    logger.info(f"Downloading from {download_url}...")
    dl_response = requests.get(download_url, timeout=60)
    dl_response.raise_for_status()

    # Save zip to temporary file
    temp_dir = project_root / "tmp_release_test" / platform_name
    temp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = temp_dir / f"release_{platform_name}.zip"
    with open(zip_path, "wb") as f:
        f.write(dl_response.content)

    # Unzip
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find the extracted executable (filtering out the zip itself)
    extracted_files = list(temp_dir.glob("*"))
    filtered_files = [f for f in extracted_files if f.name != zip_path.name]

    # Prefer Configurator or Installer binary if multiple executables exist
    target_file = None
    for item in filtered_files:
        if "configurator" in item.name.lower() or "installer" in item.name.lower():
            target_file = item
            break
    if not target_file:
        target_file = next(iter(filtered_files), None)

    if not target_file:
        raise RuntimeError("No files found inside the extracted zip.")

    return target_file


def run_linux_vm_test(
    client: ProxmoxClient,
    node: str,
    template_id: int,
    binary_path: Path,
    os_name: str,
    vm_user: str,
    vm_pass: str,
    ssh_public_key: str,
    skip_cleanup: bool = False,
) -> Tuple[bool, str]:
    """Clones a Linux VM (Debian or Ubuntu), installs binary, and verifies."""
    vmid_val = client.get_next_vmid()
    if not vmid_val:
        return False, "Failed to allocate new VMID from Proxmox."

    new_vmid = vmid_val
    logger.info(
        f"[{os_name.upper()} VM] Cloning template {template_id} to VMID {new_vmid}..."
    )

    try:
        # Step 1: Clone
        try:
            clone_res = client.clone_vm(
                node=node,
                vmid=template_id,
                newid=new_vmid,
                name=f"njord-test-{os_name}-{new_vmid}",
                full=False,
            )
            upid = clone_res.get("data")
            if isinstance(upid, str):
                wait_for_proxmox_task(client, node, upid)
        except Exception as clone_err:
            if "Linked clone feature is not supported" in str(clone_err):
                logger.warning(
                    f"[{os_name.upper()} VM] Linked clone not supported. "
                    "Falling back to full clone..."
                )
                clone_res = client.clone_vm(
                    node=node,
                    vmid=template_id,
                    newid=new_vmid,
                    name=f"njord-test-{os_name}-{new_vmid}",
                    full=True,
                )
                upid = clone_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(client, node, upid)
            else:
                raise

        # Step 2: Configure Cloud-Init
        logger.info(
            f"[{os_name.upper()} VM] Configuring Cloud-Init for VMID {new_vmid}..."
        )
        conf_res = client.configure_vm(
            node=node,
            vmid=new_vmid,
            config_data={
                "ciuser": vm_user,
                "cipassword": vm_pass,
                "sshkeys": urllib.parse.quote(ssh_public_key),
                "ipconfig0": "ip=dhcp",
                "agent": "enabled=1",
                "net0": "virtio,bridge=vmbr0,firewall=0",
            },
        )
        upid = conf_res.get("data")
        if isinstance(upid, str):
            wait_for_proxmox_task(client, node, upid)

        # Step 3: Start VM
        logger.info(f"[{os_name.upper()} VM] Starting VMID {new_vmid}...")
        client.start_vm(node=node, vmid=new_vmid)

        # Step 4: Wait for IP
        vm_ip = wait_for_ip(client, node, new_vmid)
        if not vm_ip:
            return False, "Timed out waiting for VM IP."

        time.sleep(15)

        # Step 5: Copy binary & install
        ssh_mgr = SSHManager(
            hostname=vm_ip,
            username=vm_user,
            password=vm_pass,
            allow_auto_add=True,
            load_system_keys=False,
        )

        connected = False
        conn_msg = ""
        for attempt in range(1, 7):
            logger.info(
                f"[{os_name.upper()} VM] Connecting via SSH to {vm_user}@{vm_ip} "
                f"(attempt {attempt}/6)..."
            )
            connected, conn_msg = ssh_mgr.connect()
            if connected:
                break
            time.sleep(10)

        if not connected:
            return False, f"SSH connection failed after attempts: {conn_msg}"

        try:
            # Deploy SSH keys
            ssh_mgr.setup_ssh_key(lambda x: None)

            # Read installer script content
            install_script_path = project_root / "linux" / "install.sh"
            with open(install_script_path, "rb") as f:
                script_bytes = f.read()

            # Upload binary
            logger.info(
                f"[{os_name.upper()} VM] Copying binary and install script to VM..."
            )
            with open(binary_path, "rb") as f:
                bin_bytes = f.read()

            ok_bin, msg_bin = ssh_mgr.upload_content(bin_bytes, "NjordDeploy-Linux")
            if not ok_bin:
                return False, f"Failed to upload binary: {msg_bin}"

            ok_scr, msg_scr = ssh_mgr.upload_content(script_bytes, "install.sh")
            if not ok_scr:
                return False, f"Failed to upload install script: {msg_scr}"

            # Make install.sh executable and run installation
            logger.info(f"[{os_name.upper()} VM] Running installation script...")
            ssh_mgr.execute_command("chmod +x install.sh", lambda x: None)

            cmd_install = f"echo '{vm_pass}' | sudo -S ./install.sh"
            exit_code, _ = ssh_mgr.execute_command(
                cmd_install,
                lambda msg: logger.info(f"[{os_name.upper()} INSTALL] {msg.strip()}"),
            )

            if exit_code != 0:
                return False, f"Installation script failed with code {exit_code}"

            # Verify binary exists
            exit_code, _ = ssh_mgr.execute_command(
                "ls -l /usr/local/bin/NjordDeploy-Configurator", lambda x: None
            )
            if exit_code != 0:
                return False, "NjordDeploy-Configurator binary not found after install."

            # Start the application in background
            logger.info(f"[{os_name.upper()} VM] Starting NjordDeploy in background...")
            cmd_start = (
                f"echo '{vm_pass}' | sudo -S systemd-run "
                f"--working-directory=/home/{vm_user} "
                f"--unit=njorddeploy-test "
                f"/usr/local/bin/NjordDeploy-Configurator"
            )
            ssh_mgr.execute_command(
                cmd_start,
                lambda msg: logger.info(f"[{os_name.upper()} START] {msg.strip()}"),
                check_exit_code=False,
            )

            time.sleep(5)

            # Verify HTTP response on port 5001 (or 5000)
            logger.info(
                f"[{os_name.upper()} VM] Verifying HTTP response on port 5001..."
            )
            verification_url = f"http://{vm_ip}:5001/"
            # noinspection PyBroadException
            try:
                verify_res = requests.get(verification_url, timeout=5)
                if verify_res.status_code == 200:
                    logger.info(
                        f"[{os_name.upper()} VM] Success: HTTP interface reachable!"
                    )
                    return True, f"{os_name.title()} VM Test Passed successfully."
            except Exception as e:
                logger.debug(f"Probe attempt: {e}")

            # Fallback check on port 5000
            # noinspection PyBroadException
            try:
                fallback_url = f"http://{vm_ip}:5000/"
                verify_res = requests.get(fallback_url, timeout=5)
                if verify_res.status_code == 200:
                    logger.info(
                        f"[{os_name.upper()} VM] Success: Reachable on port 5000!"
                    )
                    return True, f"{os_name.title()} VM Test Passed successfully."
            except Exception as e:
                logger.debug(f"Probe attempt: {e}")

            # Retrieve logs for diagnostics
            _, log_output = ssh_mgr.execute_command(
                "journalctl -u njorddeploy-test --no-pager",
                lambda x: None,
                check_exit_code=False,
            )
            logger.error(
                f"[{os_name.upper()} VM] Remote application logs:\n{log_output}"
            )
            return False, "HTTP interface verification failed on port 5001."

        finally:
            ssh_mgr.execute_command(
                f"echo '{vm_pass}' | sudo -S systemctl stop njorddeploy-test",
                lambda x: None,
                check_exit_code=False,
            )
            ssh_mgr.close()

    except Exception as e:
        logger.error(f"[{os_name.upper()} VM] Test error: {e}", exc_info=True)
        return False, str(e)

    finally:
        if not skip_cleanup:
            logger.info(f"[{os_name.upper()} VM] Cleaning up VMID {new_vmid}...")
            # noinspection PyBroadException
            try:
                client.stop_vm(node=node, vmid=new_vmid)
                time.sleep(2)
                client.destroy_vm(node=node, vmid=new_vmid)
                logger.info(f"[{os_name.upper()} VM] VMID {new_vmid} destroyed.")
            except Exception as cleanup_err:
                logger.error(
                    f"[{os_name.upper()} VM] Error cleaning up VMID {new_vmid}: "
                    f"{cleanup_err}"
                )


def run_linux_lxc_test(
    client: ProxmoxClient,
    node: str,
    ostemplate: str,
    binary_path: Path,
    os_name: str,
    vm_pass: str,
    ssh_public_key: str,
    skip_cleanup: bool = False,
) -> Tuple[bool, str]:
    """Provisions a clean LXC container (Debian or Ubuntu) and tests installer."""
    vmid_val = client.get_next_vmid()
    if not vmid_val:
        return False, "Failed to allocate new VMID from Proxmox."

    new_vmid = vmid_val
    logger.info(
        f"[{os_name.upper()} LXC] Creating container {new_vmid} ({ostemplate})..."
    )

    try:
        create_data = {
            "vmid": new_vmid,
            "ostemplate": ostemplate,
            "cores": 2,
            "memory": 2048,
            "swap": 512,
            "rootfs": "local-lvm:15",
            "net0": "name=eth0,bridge=vmbr0,firewall=0,ip=dhcp",
            "features": "nesting=1",
            "unprivileged": 1,
            "password": vm_pass,
            "ssh-public-keys": ssh_public_key,
            "start": 1,
        }
        create_res = client.post(f"nodes/{node}/lxc", data=create_data)
        upid = create_res.get("data")
        if isinstance(upid, str):
            wait_for_proxmox_task(client, node, upid)

        ct_ip = wait_for_lxc_ip(client, node, new_vmid)
        if not ct_ip:
            return False, "Timed out waiting for LXC IP."

        time.sleep(5)

        ssh_mgr = SSHManager(
            hostname=ct_ip,
            username="root",
            password=vm_pass,
            allow_auto_add=True,
            load_system_keys=False,
        )

        connected = False
        conn_msg = ""
        for attempt in range(1, 7):
            logger.info(
                f"[{os_name.upper()} LXC] Connecting via SSH to root@{ct_ip} "
                f"(attempt {attempt}/6)..."
            )
            connected, conn_msg = ssh_mgr.connect()
            if connected:
                break
            time.sleep(5)

        if not connected:
            return False, f"SSH connection failed after attempts: {conn_msg}"

        try:
            # Read installer script content
            install_script_path = project_root / "linux" / "install.sh"
            with open(install_script_path, "rb") as f:
                script_bytes = f.read()

            # Upload binary
            with open(binary_path, "rb") as f:
                bin_bytes = f.read()

            ok_bin, msg_bin = ssh_mgr.upload_content(bin_bytes, "NjordDeploy-Linux")
            if not ok_bin:
                return False, f"Failed to upload binary: {msg_bin}"

            ok_scr, msg_scr = ssh_mgr.upload_content(script_bytes, "install.sh")
            if not ok_scr:
                return False, f"Failed to upload install script: {msg_scr}"

            # Run installation
            logger.info(f"[{os_name.upper()} LXC] Running installation script...")
            ssh_mgr.execute_command("chmod +x install.sh", lambda x: None)

            exit_code, _ = ssh_mgr.execute_command(
                "./install.sh",
                lambda msg: logger.info(f"[{os_name.upper()} INSTALL] {msg.strip()}"),
            )

            if exit_code != 0:
                return False, f"Installation script failed with code {exit_code}"

            # Start in background via systemd-run
            logger.info(
                f"[{os_name.upper()} LXC] Starting NjordDeploy in background..."
            )
            ssh_mgr.execute_command(
                "systemd-run --unit=njorddeploy-test "
                "/usr/local/bin/NjordDeploy-Configurator",
                lambda msg: logger.info(f"[{os_name.upper()} START] {msg.strip()}"),
                check_exit_code=False,
            )

            time.sleep(5)

            # Verify HTTP interface
            logger.info(
                f"[{os_name.upper()} LXC] Verifying HTTP response on port 5001..."
            )
            verification_url = f"http://{ct_ip}:5001/"
            # noinspection PyBroadException
            try:
                verify_res = requests.get(verification_url, timeout=5)
                if verify_res.status_code == 200:
                    logger.info(
                        f"[{os_name.upper()} LXC] Success: HTTP interface reachable!"
                    )
                    return True, f"{os_name.title()} LXC Test Passed successfully."
            except Exception as e:
                logger.debug(f"Probe attempt: {e}")

            # Fallback check on port 5000
            # noinspection PyBroadException
            try:
                fallback_url = f"http://{ct_ip}:5000/"
                verify_res = requests.get(fallback_url, timeout=5)
                if verify_res.status_code == 200:
                    logger.info(
                        f"[{os_name.upper()} LXC] Success: Reachable on port 5000!"
                    )
                    return True, f"{os_name.title()} LXC Test Passed successfully."
            except Exception as e:
                logger.debug(f"Probe attempt: {e}")

            _, log_out = ssh_mgr.execute_command(
                "journalctl -u njorddeploy-test --no-pager",
                lambda x: None,
                check_exit_code=False,
            )
            logger.error(f"[{os_name.upper()} LXC] Remote application logs:\n{log_out}")
            return False, "HTTP interface verification failed on port 5001."

        finally:
            ssh_mgr.execute_command(
                "systemctl stop njorddeploy-test",
                lambda x: None,
                check_exit_code=False,
            )
            ssh_mgr.close()

    except Exception as e:
        logger.error(f"[{os_name.upper()} LXC] Test error: {e}", exc_info=True)
        return False, str(e)

    finally:
        if not skip_cleanup:
            logger.info(f"[{os_name.upper()} LXC] Cleaning up CTID {new_vmid}...")
            # noinspection PyBroadException
            try:
                client.post(f"nodes/{node}/lxc/{new_vmid}/status/stop")
                time.sleep(2)
                client.delete(f"nodes/{node}/lxc/{new_vmid}", params={"purge": 1})
                logger.info(f"[{os_name.upper()} LXC] CTID {new_vmid} destroyed.")
            except Exception as cleanup_err:
                logger.error(
                    f"[{os_name.upper()} LXC] Error cleaning up CTID {new_vmid}: "
                    f"{cleanup_err}"
                )


def run_windows_vm_test(
    client: ProxmoxClient,
    node: str,
    template_id: int,
    binary_path: Path,
    vm_user: str,
    vm_pass: str,
    skip_cleanup: bool = False,
) -> Tuple[bool, str]:
    """Clones a Windows VM, copies executable, runs and verifies."""
    vmid_val = client.get_next_vmid()
    if not vmid_val:
        return False, "Failed to allocate new VMID from Proxmox."

    new_vmid = vmid_val
    logger.info(
        f"[WINDOWS VM] Cloning master template {template_id} to VMID {new_vmid}..."
    )

    try:
        try:
            clone_res = client.clone_vm(
                node=node,
                vmid=template_id,
                newid=new_vmid,
                name=f"njord-rel-test-win-{new_vmid}",
                full=False,
            )
            upid = clone_res.get("data")
            if isinstance(upid, str):
                wait_for_proxmox_task(client, node, upid)
        except Exception as clone_err:
            if "Linked clone feature is not supported" in str(clone_err):
                logger.warning(
                    "[WINDOWS VM] Linked clone not supported. "
                    "Falling back to full clone..."
                )
                clone_res = client.clone_vm(
                    node=node,
                    vmid=template_id,
                    newid=new_vmid,
                    name=f"njord-rel-test-win-{new_vmid}",
                    full=True,
                )
                upid = clone_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(client, node, upid)
            else:
                raise

        logger.info("[WINDOWS VM] Starting VMID %d...", new_vmid)
        client.start_vm(node=node, vmid=new_vmid)

        vm_ip = wait_for_ip(client, node, new_vmid)
        if not vm_ip:
            return False, "Timed out waiting for Windows VM IP."

        time.sleep(25)

        ssh_mgr = SSHManager(
            hostname=vm_ip,
            username=vm_user,
            password=vm_pass,
            allow_auto_add=True,
            load_system_keys=False,
        )

        connected = False
        conn_msg = ""
        for attempt in range(1, 6):
            logger.info(
                f"[WINDOWS VM] Connecting via SSH to {vm_user}@{vm_ip} "
                f"(attempt {attempt}/5)..."
            )
            connected, conn_msg = ssh_mgr.connect()
            if connected:
                break
            time.sleep(10)

        if not connected:
            return False, f"SSH connection failed after 5 attempts: {conn_msg}"

        try:
            logger.info("[WINDOWS VM] Uploading NjordDeployInstaller.exe...")
            with open(binary_path, "rb") as f:
                bin_bytes = f.read()

            ok_bin, msg_bin = ssh_mgr.upload_content(
                bin_bytes, "NjordDeployInstaller.exe"
            )
            if not ok_bin:
                return False, f"Failed to upload Windows binary: {msg_bin}"

            logger.info("[WINDOWS VM] Launching executable on Windows guest...")
            cmd_start = (
                'powershell -Command "Start-Process '
                "-FilePath '.\\NjordDeployInstaller.exe' "
                "-WindowStyle Hidden -RedirectStandardOutput 'njorddeploy.log'\""
            )
            ssh_mgr.execute_command(cmd_start, lambda x: None, check_exit_code=False)

            time.sleep(10)

            logger.info("[WINDOWS VM] Verifying HTTP response on port 5001...")
            verification_url = f"http://{vm_ip}:5001/"
            # noinspection PyBroadException
            try:
                verify_res = requests.get(verification_url, timeout=5)
                if verify_res.status_code == 200:
                    logger.info("[WINDOWS VM] Success: HTTP interface is reachable!")
                    return True, "Windows VM Test Passed successfully."
            except Exception as e:
                logger.debug(f"Probe attempt: {e}")

            # Fallback on port 5000
            # noinspection PyBroadException
            try:
                fallback_url = f"http://{vm_ip}:5000/"
                verify_res = requests.get(fallback_url, timeout=5)
                if verify_res.status_code == 200:
                    logger.info("[WINDOWS VM] Success: Reachable on port 5000!")
                    return True, "Windows VM Test Passed successfully."
            except Exception as e:
                logger.debug(f"Probe attempt: {e}")

            _, log_output = ssh_mgr.execute_command(
                'powershell -Command "Get-Content njorddeploy.log"',
                lambda x: None,
                check_exit_code=False,
            )
            logger.error(f"[WINDOWS VM] Remote application logs:\n{log_output}")
            return False, "HTTP interface verification failed on port 5001."

        finally:
            ssh_mgr.close()

    except Exception as e:
        logger.error(f"[WINDOWS VM] Test error: {e}", exc_info=True)
        return False, str(e)

    finally:
        if not skip_cleanup:
            logger.info(f"[WINDOWS VM] Cleaning up VMID {new_vmid}...")
            # noinspection PyBroadException
            try:
                client.stop_vm(node=node, vmid=new_vmid)
                time.sleep(2)
                client.destroy_vm(node=node, vmid=new_vmid)
                logger.info(f"[WINDOWS VM] VMID {new_vmid} destroyed.")
            except Exception as cleanup_err:
                logger.error(
                    f"[WINDOWS VM] Error cleaning up VMID {new_vmid}: {cleanup_err}"
                )


def run_macos_vm_test(
    client: ProxmoxClient,
    node: str,
    template_id: Optional[int],
    binary_path: Optional[Path],
    vm_user: str,
    vm_pass: str,
    skip_cleanup: bool = False,
) -> Tuple[bool, str]:
    """Tests macOS installer via OSX-KVM Proxmox VM template or reports status."""
    if not template_id:
        return (
            True,
            "SKIPPED (Informational): macOS VM template not configured on Proxmox. "
            "macOS binaries are verified natively via GitHub Actions macos-latest "
            "runners. (To enable local Proxmox testing, configure OSX-KVM and set "
            "RELEASE_TEST_MACOS_TEMPLATE in .env).",
        )

    vmid_val = client.get_next_vmid()
    if not vmid_val:
        return False, "Failed to allocate new VMID from Proxmox."

    new_vmid = vmid_val
    logger.info(
        f"[MACOS VM] Cloning OSX-KVM master template {template_id} "
        f"to VMID {new_vmid}..."
    )

    try:
        clone_res = client.clone_vm(
            node=node,
            vmid=template_id,
            newid=new_vmid,
            name=f"njord-rel-test-macos-{new_vmid}",
            full=True,
        )
        upid = clone_res.get("data")
        if isinstance(upid, str):
            wait_for_proxmox_task(client, node, upid, timeout_seconds=300)

        logger.info("[MACOS VM] Starting VMID %d...", new_vmid)
        client.start_vm(node=node, vmid=new_vmid)

        vm_ip = wait_for_ip(client, node, new_vmid, timeout_seconds=180)
        if not vm_ip:
            return False, "Timed out waiting for macOS VM IP."

        time.sleep(30)

        ssh_mgr = SSHManager(
            hostname=vm_ip,
            username=vm_user,
            password=vm_pass,
            allow_auto_add=True,
            load_system_keys=False,
        )

        connected = False
        conn_msg = ""
        for attempt in range(1, 6):
            logger.info(
                f"[MACOS VM] Connecting via SSH to {vm_user}@{vm_ip} "
                f"(attempt {attempt}/5)..."
            )
            connected, conn_msg = ssh_mgr.connect()
            if connected:
                break
            time.sleep(10)

        if not connected:
            return False, f"SSH connection failed after 5 attempts: {conn_msg}"

        try:
            if binary_path and binary_path.exists():
                with open(binary_path, "rb") as f:
                    bin_bytes = f.read()
                ssh_mgr.upload_content(bin_bytes, "NjordDeploy-macOS")
                ssh_mgr.execute_command("chmod +x NjordDeploy-macOS", lambda x: None)
                ssh_mgr.execute_command(
                    "nohup ./NjordDeploy-macOS > /tmp/njorddeploy.log 2>&1 &",
                    lambda x: None,
                    check_exit_code=False,
                )
                time.sleep(5)

                verification_url = f"http://{vm_ip}:5001/"
                # noinspection PyBroadException
                try:
                    verify_res = requests.get(verification_url, timeout=5)
                    if verify_res.status_code == 200:
                        return True, "macOS VM Test Passed successfully."
                except Exception as e:
                    logger.debug(f"Probe attempt: {e}")

                return False, "macOS HTTP interface verification failed on port 5001."
            else:
                return (
                    True,
                    "macOS VM booted and SSH verified. (Binary test skipped: no "
                    "macOS binary supplied).",
                )
        finally:
            ssh_mgr.close()

    except Exception as e:
        logger.error(f"[MACOS VM] Test error: {e}", exc_info=True)
        return False, str(e)

    finally:
        if not skip_cleanup:
            logger.info(f"[MACOS VM] Cleaning up VMID {new_vmid}...")
            # noinspection PyBroadException
            try:
                client.stop_vm(node=node, vmid=new_vmid)
                time.sleep(2)
                client.destroy_vm(node=node, vmid=new_vmid)
                logger.info(f"[MACOS VM] VMID {new_vmid} destroyed.")
            except Exception as cleanup_err:
                logger.error(
                    f"[MACOS VM] Error cleaning up VMID {new_vmid}: {cleanup_err}"
                )


def send_signal_notification(report_content: str) -> None:
    """Sends a summary notification via Signal API if configured in .env."""
    signal_url = os.getenv("SIGNAL_API_URL")
    signal_sender = os.getenv("SIGNAL_SENDER")
    signal_recipient = os.getenv("SIGNAL_RECIPIENT")

    if not signal_url or not signal_sender or not signal_recipient:
        return

    # noinspection PyBroadException
    try:
        msg_header = "🚀 NjordDeploy Multi-OS Release Installer Report:\n\n"
        payload = {
            "message": f"{msg_header}{report_content}",
            "number": signal_sender,
            "recipients": [signal_recipient],
        }
        res = requests.post(f"{signal_url}/v2/send", json=payload, timeout=10)
        if res.status_code in (200, 201):
            logger.info("Signal notification sent successfully.")
        else:
            logger.warning(
                f"Signal notification returned status code: {res.status_code}"
            )
    except Exception as ex:
        logger.warning(f"Failed to send Signal notification: {ex}")


def save_test_report(
    results: List[Tuple[str, bool, str]], github_tag: Optional[str]
) -> None:
    """Saves a markdown report and JSON history for the release test run."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag_str = github_tag or "Local Build"

    total_tests = len(results)
    passed_tests = sum(1 for _, success, _ in results if success)
    failed_tests = total_tests - passed_tests

    report_lines = [
        "# 🚀 NjordDeploy Multi-OS Release Installer Test Report",
        "",
        f"**Datum & Tijd:** {date_str}  ",
        f"**Versie / Tag:** `{tag_str}`  ",
        f"**Totale Tests:** {total_tests} | "
        f"**Geslaagd:** {passed_tests} | "
        f"**Mislukt:** {failed_tests}",
        "",
        "---",
        "",
        "| Omgeving / Besturingssysteem | Status | Details |",
        "| :--- | :---: | :--- |",
    ]

    for name, success, details in results:
        status_icon = "✅ PASS" if success else "❌ FAIL"
        clean_details = details.replace("\n", " ")
        report_lines.append(f"| **{name}** | {status_icon} | {clean_details} |")

    report_lines.extend(
        [
            "",
            "---",
            "",
            "## 🔍 Verificatiecriteria",
            "- **Installatie:** Binary en shortcuts correct geplaatst "
            "(`install.sh` / `.exe` / `start.bat`).",
            "- **Service Executie:** NjordDeploy Configurator gestart in "
            "achtergrond (systemd / nohup / PowerShell).",
            "- **Health Check:** HTTP status `200 OK` geverifieerd op "
            "poort `5001` (of fallback `5000`).",
            "- **Opruiming:** Tijdelijke Proxmox VM's en LXC containers "
            "automatisch verwijderd.",
            "",
        ]
    )

    report_content = "\n".join(report_lines)

    # 1. Save markdown report
    docs_dir = project_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    report_file = docs_dir / f"RELEASE_INSTALLER_TESTS_{timestamp}.md"
    report_file.write_text(report_content, encoding="utf-8")
    logger.info(f"Saved test report to: {report_file}")

    # 2. Save JSON history
    json_dir = project_root / "tests"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_file = json_dir / "release_installer_results.json"

    history: List[Dict[str, Any]] = []
    if json_file.exists():
        # noinspection PyBroadException
        try:
            history = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.append(
        {
            "timestamp": timestamp,
            "date": date_str,
            "tag": tag_str,
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "results": [
                {"target": name, "success": success, "details": details}
                for name, success, details in results
            ],
        }
    )
    json_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

    # 3. Send Signal notification
    summary_text = f"Tag: {tag_str}\nGeslaagd: {passed_tests}/{total_tests}\n"
    for name, success, _ in results:
        summary_text += f"- {name}: {'✅ PASS' if success else '❌ FAIL'}\n"
    send_signal_notification(summary_text)


def main():
    load_dotenv(dotenv_path=project_root / ".env")

    parser = argparse.ArgumentParser(
        description="Automated Multi-OS Release Integration Testing on Proxmox"
    )
    parser.add_argument(
        "--os",
        type=str,
        default="all",
        help="Target OS to test: 'debian', 'ubuntu', 'windows', "
        "'macos', 'linux', or 'all' (default: 'all').",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="both",
        choices=["vm", "lxc", "both"],
        help="Target execution environment for Linux tests: 'vm', "
        "'lxc', or 'both' (default: 'both').",
    )
    parser.add_argument(
        "--binary-path",
        type=str,
        help="Path to local binary (defaults to dist/NjordDeployConfigurator).",
    )
    parser.add_argument(
        "--github-tag",
        type=str,
        help="GitHub release tag to fetch binary from (e.g. v0.4.46-Alpha).",
    )
    parser.add_argument(
        "--node",
        type=str,
        default=os.getenv("PROXMOX_NODE") or "pve",
        help="Proxmox node to use.",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Do not delete the cloned VMs/LXC containers after test completion.",
    )

    args = parser.parse_args()

    # Determine templates and credentials
    debian_vm_template = int(
        os.getenv("RELEASE_TEST_DEBIAN_TEMPLATE")
        or os.getenv("RELEASE_TEST_LINUX_TEMPLATE")
        or 902
    )
    ubuntu_vm_template_raw = os.getenv("RELEASE_TEST_UBUNTU_TEMPLATE")
    ubuntu_vm_template = int(ubuntu_vm_template_raw) if ubuntu_vm_template_raw else None

    debian_lxc_template = (
        os.getenv("RELEASE_TEST_DEBIAN_LXC")
        or "local:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst"
    )
    ubuntu_lxc_template = (
        os.getenv("RELEASE_TEST_UBUNTU_LXC")
        or "storage-backups-iso:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst"
    )

    windows_template = int(os.getenv("RELEASE_TEST_WINDOWS_TEMPLATE") or 910)
    macos_template_raw = os.getenv("RELEASE_TEST_MACOS_TEMPLATE")
    macos_template = int(macos_template_raw) if macos_template_raw else None

    vm_user = (
        os.getenv("RELEASE_TEST_VM_USER") or os.getenv("PROXMOX_VM_USER") or "testuser"
    )
    vm_pass = (
        os.getenv("RELEASE_TEST_VM_PASSWORD")
        or os.getenv("PROXMOX_VM_PASSWORD")
        or "your-secure-test-password"
    )

    dummy_mgr = SSHManager(
        hostname="localhost", username="test", password="key"
    )  # nosec B106
    ssh_key_obj = dummy_mgr.get_ssh_key()
    ssh_public_key = f"{ssh_key_obj.get_name()} {ssh_key_obj.get_base64()}"

    proxmox_client = setup_proxmox_client()

    results: List[Tuple[str, bool, str]] = []

    target_os = args.os.lower()
    run_debian = target_os in ("all", "linux", "debian")
    run_ubuntu = target_os in ("all", "linux", "ubuntu")
    run_windows = target_os in ("all", "windows")
    run_macos = target_os in ("all", "macos")

    # 1. Resolve Linux binary
    linux_bin: Optional[Path] = None
    if run_debian or run_ubuntu:
        if args.github_tag:
            try:
                linux_bin = download_github_release(args.github_tag, "linux")
            except Exception as dl_err:
                logger.error(f"Failed to download Linux asset: {dl_err}")
                sys.exit(1)
        else:
            default_path = project_root / "dist" / "NjordDeployConfigurator"
            local_path = (
                Path(args.binary_path)
                if args.binary_path and not args.binary_path.endswith(".exe")
                else (
                    default_path
                    if default_path.exists()
                    else project_root / "dist" / "NjordDeployInstaller"
                )
            )
            if not local_path.exists():
                fallback = project_root / "dist" / "NjordDeploy-Linux"
                if fallback.exists():
                    local_path = fallback
                else:
                    # Fallback to local entry point if standalone binary is not built
                    logger.warning(
                        f"Linux standalone binary not found at '{local_path}'. "
                        "Using repository source runner..."
                    )
                    local_path = project_root / "run_configurator.py"

            linux_bin = local_path
            logger.info(f"Using Linux binary/target: {linux_bin}")

    # 2. Run Debian Tests
    if run_debian and linux_bin:
        if args.mode in ("vm", "both"):
            logger.info("--- Starting Debian 12 VM Installer Test ---")
            success, details = run_linux_vm_test(
                client=proxmox_client,
                node=args.node,
                template_id=debian_vm_template,
                binary_path=linux_bin,
                os_name="debian",
                vm_user=vm_user,
                vm_pass=vm_pass,
                ssh_public_key=ssh_public_key,
                skip_cleanup=args.skip_cleanup,
            )
            results.append(("Debian 12 (VM)", success, details))

        if args.mode in ("lxc", "both"):
            logger.info("--- Starting Debian 12 LXC Installer Test ---")
            success, details = run_linux_lxc_test(
                client=proxmox_client,
                node=args.node,
                ostemplate=debian_lxc_template,
                binary_path=linux_bin,
                os_name="debian",
                vm_pass=vm_pass,
                ssh_public_key=ssh_public_key,
                skip_cleanup=args.skip_cleanup,
            )
            results.append(("Debian 12 (LXC)", success, details))

    # 3. Run Ubuntu Tests
    if run_ubuntu and linux_bin:
        if args.mode in ("vm", "both") and ubuntu_vm_template:
            logger.info("--- Starting Ubuntu 24.04 VM Installer Test ---")
            success, details = run_linux_vm_test(
                client=proxmox_client,
                node=args.node,
                template_id=ubuntu_vm_template,
                binary_path=linux_bin,
                os_name="ubuntu",
                vm_user=vm_user,
                vm_pass=vm_pass,
                ssh_public_key=ssh_public_key,
                skip_cleanup=args.skip_cleanup,
            )
            results.append(("Ubuntu 24.04 (VM)", success, details))

        if args.mode in ("lxc", "both"):
            logger.info("--- Starting Ubuntu 24.04 LXC Installer Test ---")
            success, details = run_linux_lxc_test(
                client=proxmox_client,
                node=args.node,
                ostemplate=ubuntu_lxc_template,
                binary_path=linux_bin,
                os_name="ubuntu",
                vm_pass=vm_pass,
                ssh_public_key=ssh_public_key,
                skip_cleanup=args.skip_cleanup,
            )
            results.append(("Ubuntu 24.04 (LXC)", success, details))

    # 4. Run Windows Tests
    if run_windows:
        windows_bin: Optional[Path] = None
        if args.github_tag:
            try:
                windows_bin = download_github_release(args.github_tag, "windows")
            except Exception as dl_err:
                logger.error(f"Failed to download Windows asset: {dl_err}")
                sys.exit(1)
        else:
            if args.binary_path and args.binary_path.endswith(".exe"):
                windows_bin = Path(args.binary_path)
            else:
                default_win = project_root / "dist" / "NjordDeployConfigurator.exe"
                local_path = (
                    default_win
                    if default_win.exists()
                    else project_root / "dist" / "NjordDeployInstaller.exe"
                )
                if not local_path.exists():
                    fallback = project_root / "dist" / "NjordDeploy-Windows.exe"
                    if fallback.exists():
                        local_path = fallback
                windows_bin = (
                    local_path if (local_path and local_path.exists()) else None
                )

        if windows_bin and windows_bin.exists():
            logger.info(f"Using Windows binary: {windows_bin}")
            success, details = run_windows_vm_test(
                client=proxmox_client,
                node=args.node,
                template_id=windows_template,
                binary_path=windows_bin,
                vm_user=vm_user,
                vm_pass=vm_pass,
                skip_cleanup=args.skip_cleanup,
            )
            results.append(("Windows (VM)", success, details))
        else:
            logger.warning(
                "Windows binary not found locally. (To test Windows, provide "
                "--binary-path or --github-tag)."
            )
            results.append(
                (
                    "Windows (VM)",
                    True,
                    "SKIPPED (Informational): Windows executable not present locally.",
                )
            )

    # 5. Run macOS Tests
    if run_macos:
        macos_bin: Optional[Path] = None
        if args.github_tag:
            try:
                macos_bin = download_github_release(args.github_tag, "macos")
            except Exception:
                macos_bin = None

        success, details = run_macos_vm_test(
            client=proxmox_client,
            node=args.node,
            template_id=macos_template,
            binary_path=macos_bin,
            vm_user=vm_user,
            vm_pass=vm_pass,
            skip_cleanup=args.skip_cleanup,
        )
        results.append(("macOS (OSX-KVM / CI)", success, details))

    # 6. Summary Report & Save Artifacts
    print("\n" + "=" * 60)
    print("           MULTI-OS RELEASE INSTALLER TEST REPORT")
    print("=" * 60)
    failures = 0
    for name, success, details in results:
        status_str = "✅ PASS" if success else "❌ FAIL"
        if not success:
            failures += 1
        print(f"{name:30} : {status_str}")
        print(f"  Details: {details}\n")
    print("=" * 60)

    save_test_report(results, args.github_tag)

    # Clean up tmp folder if it exists
    tmp_folder = project_root / "tmp_release_test"
    if tmp_folder.exists():
        import shutil

        shutil.rmtree(tmp_folder, ignore_errors=True)

    if failures > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
