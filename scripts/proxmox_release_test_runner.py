# scripts/proxmox_release_test_runner.py
import argparse
import logging
import os
import sys
import time
import urllib.parse
import zipfile
from pathlib import Path
from typing import Tuple

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
    temp_dir = project_root / "tmp_release_test"
    temp_dir.mkdir(exist_ok=True)
    zip_path = temp_dir / f"release_{platform_name}.zip"
    with open(zip_path, "wb") as f:
        f.write(dl_response.content)

    # Unzip
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find the extracted executable (filtering out the zip itself)
    extracted_files = list(temp_dir.glob("*"))
    filtered_files = [f for f in extracted_files if f.name != zip_path.name]

    # Rule check: list unpacking or next(iter()) for first elements
    target_file = next(iter(filtered_files), None)
    if not target_file:
        raise RuntimeError("No files found inside the extracted zip.")

    return target_file


def run_linux_vm_test(
    client: ProxmoxClient,
    node: str,
    template_id: int,
    binary_path: Path,
    vm_user: str,
    vm_pass: str,
    ssh_public_key: str,
) -> Tuple[bool, str]:
    """Clones a Linux VM, installs the binary, and verifies status."""
    vmid_val = client.get_next_vmid()
    if not vmid_val:
        return False, "Failed to allocate new VMID from Proxmox."

    new_vmid = vmid_val
    logger.info(
        f"[LINUX] Cloning master template {template_id} to new VMID {new_vmid}..."
    )

    try:
        # Step 1: Clone
        try:
            clone_res = client.clone_vm(
                node=node,
                vmid=template_id,
                newid=new_vmid,
                name=f"njord-rel-test-linux-{new_vmid}",
                full=False,
            )
            upid = clone_res.get("data")
            if isinstance(upid, str):
                wait_for_proxmox_task(client, node, upid)
        except Exception as clone_err:
            if "Linked clone feature is not supported" in str(clone_err):
                logger.warning(
                    "[LINUX] Linked clone not supported. Falling back to full clone..."
                )
                clone_res = client.clone_vm(
                    node=node,
                    vmid=template_id,
                    newid=new_vmid,
                    name=f"njord-rel-test-linux-{new_vmid}",
                    full=True,
                )
                upid = clone_res.get("data")
                if isinstance(upid, str):
                    wait_for_proxmox_task(client, node, upid)
            else:
                raise

        # Step 2: Configure Cloud-Init
        logger.info(f"[LINUX] Configuring Cloud-Init for VMID {new_vmid}...")
        client.configure_vm(
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

        # Step 3: Start VM
        logger.info(f"[LINUX] Starting VMID {new_vmid}...")
        client.start_vm(node=node, vmid=new_vmid)

        # Step 4: Wait for IP
        vm_ip = wait_for_ip(client, node, new_vmid)
        if not vm_ip:
            return False, "Timed out waiting for VM IP."

        # Wait a little bit for SSH daemon to fully initialize
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
        for attempt in range(1, 6):
            logger.info(
                f"[LINUX] Connecting via SSH to {vm_user}@{vm_ip} "
                f"(attempt {attempt}/5)..."
            )
            connected, conn_msg = ssh_mgr.connect()
            if connected:
                break
            time.sleep(10)

        if not connected:
            return False, f"SSH connection failed after 5 attempts: {conn_msg}"

        try:
            # Deploy SSH keys for passwordless communication
            ssh_mgr.setup_ssh_key(lambda x: None)

            # Read installer script content
            install_script_path = project_root / "linux" / "install.sh"
            with open(install_script_path, "rb") as f:
                script_bytes = f.read()

            # Upload files
            logger.info("[LINUX] Copying binary and install script to VM...")
            with open(binary_path, "rb") as f:
                bin_bytes = f.read()

            # Upload binary as temporary name
            ok_bin, msg_bin = ssh_mgr.upload_content(bin_bytes, "NjordDeploy-Linux")
            if not ok_bin:
                return False, f"Failed to upload binary: {msg_bin}"

            ok_scr, msg_scr = ssh_mgr.upload_content(script_bytes, "install.sh")
            if not ok_scr:
                return False, f"Failed to upload install script: {msg_scr}"

            # Make install.sh executable and run installation
            logger.info("[LINUX] Running installation script...")
            ssh_mgr.execute_command("chmod +x install.sh", lambda x: None)

            # Run installer using password for sudo (user needs sudo privs)
            # The script requires running as root
            cmd_install = f"echo '{vm_pass}' | sudo -S ./install.sh"
            exit_code, output = ssh_mgr.execute_command(
                cmd_install, lambda msg: logger.info(f"[LINUX INSTALL] {msg.strip()}")
            )

            if exit_code != 0:
                return False, f"Installation script failed with code {exit_code}"

            # Verify binary exists at expected location
            exit_code, output = ssh_mgr.execute_command(
                "ls -l /usr/local/bin/NjordDeploy-Configurator", lambda x: None
            )
            if exit_code != 0:
                return False, "NjordDeploy-Configurator binary not found after install."

            # Run diagnostic command to capture instant crashes
            logger.info("[LINUX] Running binary with 5s timeout for diagnostics...")
            cmd_diag = "timeout 5 /usr/local/bin/NjordDeploy-Configurator"
            ssh_mgr.execute_command(
                cmd_diag,
                lambda msg: logger.info(f"[DIAGNOSTIC] {msg.strip()}"),
                check_exit_code=False,
            )

            # Start the application in the background
            logger.info("[LINUX] Starting NjordDeploy Configurator in background...")
            cmd_start = (
                f"nohup /usr/local/bin/NjordDeploy-Configurator > "
                f"/home/{vm_user}/njorddeploy.log 2>&1 &"
            )
            ssh_mgr.execute_command(
                cmd_start,
                lambda msg: logger.info(f"[LINUX START] {msg.strip()}"),
                check_exit_code=False,
            )

            # Allow application startup time
            time.sleep(5)

            # Verify it is listening on port 5001 (default) or 5000
            # Let's perform a simple HTTP GET verification
            logger.info("[LINUX] Verifying HTTP response on port 5001...")
            verification_url = f"http://{vm_ip}:5001/"
            try:
                verify_res = requests.get(verification_url, timeout=5)
                if verify_res.status_code == 200:
                    logger.info("[LINUX] Success: HTTP interface is reachable!")
                    return True, "Linux VM Test Passed successfully."
                else:
                    return (
                        False,
                        f"HTTP interface returned code {verify_res.status_code}",
                    )
            except Exception as http_err:
                # Try port 5000 just in case
                try:
                    verification_url_fallback = f"http://{vm_ip}:5000/"
                    verify_res = requests.get(verification_url_fallback, timeout=5)
                    if verify_res.status_code == 200:
                        logger.info(
                            "[LINUX] Success: HTTP interface reachable on port 5000!"
                        )
                        return True, "Linux VM Test Passed successfully."
                except Exception:  # nosec B110
                    pass
                # Read remote application logs for diagnostics before failing
                logger.info(
                    "[LINUX] Verification failed. "
                    "Retrieving remote logs for diagnostics..."
                )
                _, log_output = ssh_mgr.execute_command(
                    f"cat /home/{vm_user}/njorddeploy.log",
                    lambda x: None,
                    check_exit_code=False,
                )
                logger.error(f"[LINUX] Remote application logs:\n{log_output}")

                return (
                    False,
                    f"HTTP interface verification failed on port 5001: {http_err}",
                )

        finally:
            ssh_mgr.close()

    except Exception as e:
        logger.error(f"[LINUX] Test error: {e}", exc_info=True)
        return False, str(e)

    finally:
        # Clean up VM
        logger.info(f"[LINUX] Cleaning up VMID {new_vmid}...")
        try:
            client.stop_vm(node=node, vmid=new_vmid)
            time.sleep(2)
            client.destroy_vm(node=node, vmid=new_vmid)
            logger.info(f"[LINUX] VMID {new_vmid} destroyed.")
        except Exception as cleanup_err:
            logger.error(f"[LINUX] Error cleaning up VMID {new_vmid}: {cleanup_err}")


def run_windows_vm_test(
    client: ProxmoxClient,
    node: str,
    template_id: int,
    binary_path: Path,
    vm_user: str,
    vm_pass: str,
) -> Tuple[bool, str]:
    """Clones a Windows VM, copies executable, runs and verifies."""
    vmid_val = client.get_next_vmid()
    if not vmid_val:
        return False, "Failed to allocate new VMID from Proxmox."

    new_vmid = vmid_val
    logger.info(
        f"[WINDOWS] Cloning master template {template_id} to new VMID {new_vmid}..."
    )

    try:
        # Step 1: Clone
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
                    "[WINDOWS] Linked clone not supported. "
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

        # Cloud init password for Windows templates is set if template supports it.
        # Otherwise password configured in template image is used.
        logger.info("[WINDOWS] Configuring Cloud-Init credentials...")
        client.configure_vm(
            node=node,
            vmid=new_vmid,
            config_data={
                "ciuser": vm_user,
                "cipassword": vm_pass,
            },
        )

        # Step 2: Start VM
        logger.info(f"[WINDOWS] Starting VMID {new_vmid}...")
        client.start_vm(node=node, vmid=new_vmid)

        # Step 3: Wait for IP
        vm_ip = wait_for_ip(client, node, new_vmid)
        if not vm_ip:
            return False, "Timed out waiting for VM IP."

        # Wait a little bit for Windows OpenSSH server to start
        time.sleep(25)

        # Step 4: SSH and run
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
                f"[WINDOWS] Connecting via SSH to {vm_user}@{vm_ip} "
                f"(attempt {attempt}/5)..."
            )
            connected, conn_msg = ssh_mgr.connect()
            if connected:
                break
            time.sleep(10)

        if not connected:
            return False, f"SSH connection failed after 5 attempts: {conn_msg}"

        try:
            # Upload Windows executable
            logger.info("[WINDOWS] Uploading NjordDeployInstaller.exe...")
            with open(binary_path, "rb") as f:
                bin_bytes = f.read()

            ok_bin, msg_bin = ssh_mgr.upload_content(
                bin_bytes, "NjordDeployInstaller.exe"
            )
            if not ok_bin:
                return False, f"Failed to upload Windows binary: {msg_bin}"

            # Start executable in background
            logger.info("[WINDOWS] Launching executable on Windows guest...")
            # Using start-process in PowerShell to run background task
            cmd_start = (
                'powershell -Command "Start-Process '
                "-FilePath '.\\NjordDeployInstaller.exe' "
                "-WindowStyle Hidden -RedirectStandardOutput 'njorddeploy.log'\""
            )
            ssh_mgr.execute_command(cmd_start, lambda x: None, check_exit_code=False)

            # Allow startup time
            time.sleep(10)

            # Verify it is listening on port 5001
            logger.info("[WINDOWS] Verifying HTTP response on port 5001...")
            verification_url = f"http://{vm_ip}:5001/"
            try:
                verify_res = requests.get(verification_url, timeout=5)
                if verify_res.status_code == 200:
                    logger.info("[WINDOWS] Success: HTTP interface is reachable!")
                    return True, "Windows VM Test Passed successfully."
                else:
                    return (
                        False,
                        f"HTTP interface returned code {verify_res.status_code}",
                    )
            except Exception as http_err:
                # Try port 5000 just in case
                try:
                    verification_url_fallback = f"http://{vm_ip}:5000/"
                    verify_res = requests.get(verification_url_fallback, timeout=5)
                    if verify_res.status_code == 200:
                        logger.info(
                            "[WINDOWS] Success: HTTP interface reachable on port 5000!"
                        )
                        return True, "Windows VM Test Passed successfully."
                except Exception:  # nosec B110
                    pass
                return (
                    False,
                    f"HTTP interface verification failed on port 5001: {http_err}",
                )

        finally:
            ssh_mgr.close()

    except Exception as e:
        logger.error(f"[WINDOWS] Test error: {e}", exc_info=True)
        return False, str(e)

    finally:
        # Clean up VM
        logger.info(f"[WINDOWS] Cleaning up VMID {new_vmid}...")
        try:
            client.stop_vm(node=node, vmid=new_vmid)
            time.sleep(2)
            client.destroy_vm(node=node, vmid=new_vmid)
            logger.info(f"[WINDOWS] VMID {new_vmid} destroyed.")
        except Exception as cleanup_err:
            logger.error(f"[WINDOWS] Error cleaning up VMID {new_vmid}: {cleanup_err}")


def main():
    load_dotenv(dotenv_path=project_root / ".env")

    parser = argparse.ArgumentParser(
        description="Automated Release Integration Testing on Proxmox VMs"
    )
    parser.options = parser.add_argument(
        "--binary-path",
        type=str,
        help="Path to local binary (defaults to dist/NjordDeployInstaller).",
    )
    parser.add_argument(
        "--github-tag",
        type=str,
        help="GitHub release tag to fetch the release binary from.",
    )
    parser.add_argument(
        "--node",
        type=str,
        default=os.getenv("PROXMOX_NODE") or "pve",
        help="Proxmox node to use.",
    )
    parser.add_argument(
        "--skip-linux", action="store_true", help="Skip the Linux VM release test."
    )
    parser.add_argument(
        "--skip-windows", action="store_true", help="Skip the Windows VM release test."
    )

    args = parser.parse_args()

    # Determine templates and credentials
    linux_template = int(os.getenv("RELEASE_TEST_LINUX_TEMPLATE") or 900)
    windows_template = int(os.getenv("RELEASE_TEST_WINDOWS_TEMPLATE") or 910)
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

    results = []

    # Run Linux Test
    if not args.skip_linux:
        # Determine Linux binary path
        if args.github_tag:
            try:
                linux_bin = download_github_release(args.github_tag, "linux")
            except Exception as dl_err:
                logger.error(f"Failed to download Linux asset: {dl_err}")
                sys.exit(1)
        else:
            local_path = (
                Path(args.binary_path)
                if args.binary_path
                else project_root / "dist" / "NjordDeployInstaller"
            )
            if not local_path.exists():
                # Try fallback NjordDeploy-Linux
                fallback = project_root / "dist" / "NjordDeploy-Linux"
                if fallback.exists():
                    local_path = fallback
                else:
                    logger.error(
                        f"Linux binary not found at '{local_path}'. "
                        "Run PyInstaller first or use --github-tag."
                    )
                    sys.exit(1)
            linux_bin = local_path

        logger.info(f"Using Linux binary: {linux_bin}")
        success, details = run_linux_vm_test(
            client=proxmox_client,
            node=args.node,
            template_id=linux_template,
            binary_path=linux_bin,
            vm_user=vm_user,
            vm_pass=vm_pass,
            ssh_public_key=ssh_public_key,
        )
        results.append(("Linux VM Release Test", success, details))

    # Run Windows Test
    if not args.skip_windows:
        # Determine Windows binary path
        if args.github_tag:
            try:
                windows_bin = download_github_release(args.github_tag, "windows")
            except Exception as dl_err:
                logger.error(f"Failed to download Windows asset: {dl_err}")
                sys.exit(1)
        else:
            # Expecting either arg binary_path (if it's .exe) or default
            local_path = None
            if args.binary_path and args.binary_path.endswith(".exe"):
                local_path = Path(args.binary_path)
            else:
                local_path = project_root / "dist" / "NjordDeployInstaller.exe"
                if not local_path.exists():
                    # Try fallback NjordDeploy-Windows.exe
                    fallback = project_root / "dist" / "NjordDeploy-Windows.exe"
                    if fallback.exists():
                        local_path = fallback

            if not local_path or not local_path.exists():
                logger.error(
                    f"Windows binary not found at '{local_path}'. "
                    "Run PyInstaller on Windows, provide --binary-path, "
                    "or use --github-tag."
                )
                sys.exit(1)
            windows_bin = local_path

        logger.info(f"Using Windows binary: {windows_bin}")
        success, details = run_windows_vm_test(
            client=proxmox_client,
            node=args.node,
            template_id=windows_template,
            binary_path=windows_bin,
            vm_user=vm_user,
            vm_pass=vm_pass,
        )
        results.append(("Windows VM Release Test", success, details))

    # Summary Report
    print("\n" + "=" * 50)
    print("           RELEASE INTEGRATION TEST REPORT")
    print("=" * 50)
    failures = 0
    for name, success, details in results:
        status_str = "✅ PASS" if success else "❌ FAIL"
        if not success:
            failures += 1
        print(f"{name:30} : {status_str}")
        print(f"  Details: {details}\n")
    print("=" * 50)

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
