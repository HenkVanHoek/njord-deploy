# scripts/update_operational_vm.py
"""
Operational NjordDeploy Update & Deployment Script
--------------------------------------------------
Safely builds, synchronizes, deploys, and verifies the latest NjordDeploy
applications on the operational Proxmox server (VM 140 / njorddeploy-vm).

Applications updated:
1. NjordDeployConfigurator (Port 5001)
2. NjordDeployEditor (Port 5000)
3. NjordDeployProxmoxTest (Port 5050)

Safety Features:
- Pre-deployment point-in-time snapshot backup of /opt/njorddeploy
- Graceful systemd service orchestration (stop -> update -> reload -> start)
- Automated HTTP 200 health check verification on all 3 ports
- Optional Obsidian Logbook entry generation (Henks Geheugen)
- Optional Signal Messenger alert integration
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
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
logger = logging.getLogger("update_operational_vm")

DEFAULT_TARGET_IP = "192.168.178.40"
DEFAULT_TARGET_USER = "hvhoek"
DEFAULT_VMID = 140
OBSIDIAN_LOG_DIR = Path(
    "/home/hvhoek/Nextcloud/Henks Geheugen/Projecten/Njord-deploy/Logboek"
)


def get_operational_ip(
    client: Optional[ProxmoxClient], node: str, vmid: int, fallback_ip: str
) -> str:
    """Retrieve dynamic IP for operational VM from Proxmox or return fallback."""
    if not client:
        return fallback_ip
    # noinspection PyBroadException
    try:
        ip = client.get_vm_ip(node, vmid)
        if ip:
            return ip
    except Exception as e:
        logger.debug(f"Could not retrieve VM IP from Proxmox API: {e}")
    return fallback_ip


def build_binaries_if_needed(force_build: bool = False) -> bool:
    """Trigger the universal Debian 12 binary builder on Proxmox."""
    dist_dir = project_root / "dist"
    required_binaries = [
        "NjordDeployConfigurator",
        "NjordDeployEditor",
        "NjordDeployProxmoxTest",
    ]
    missing = [b for b in required_binaries if not (dist_dir / b).exists()]

    if not force_build and not missing:
        logger.info("All required binaries present in dist/. Skipping build.")
        return True

    logger.info("Building universal Debian 12 binaries via Proxmox LXC builder...")
    # noinspection PyBroadException
    try:
        from scripts.build_linux_binary_proxmox import main as run_builder  # noqa: E402

        run_builder()
        return True
    except Exception as e:
        logger.error(f"Binary compilation failed: {e}", exc_info=True)
        return False


def verify_http_endpoint(url: str, timeout: int = 6) -> Tuple[bool, Optional[int]]:
    """Verify HTTP reachable endpoint with status 200 OK."""
    # noinspection PyBroadException
    try:
        res = requests.get(url, timeout=timeout)
        return res.status_code == 200, res.status_code
    except Exception as e:
        logger.debug(f"HTTP check failed for {url}: {e}")
        return False, None


def send_signal_notification(message: str) -> bool:
    """Send Signal notification if configured in .env."""
    load_dotenv(project_root / ".env")
    signal_url = os.getenv("SIGNAL_API_URL")
    signal_sender = os.getenv("SIGNAL_SENDER")
    signal_recipient = os.getenv("SIGNAL_RECIPIENT")

    if not signal_url or not signal_sender or not signal_recipient:
        logger.debug("Signal notification skipped: credentials not set.")
        return False

    payload = {
        "message": message,
        "number": signal_sender,
        "recipients": [signal_recipient],
    }
    # noinspection PyBroadException
    try:
        req = urllib.request.Request(
            f"{signal_url.rstrip('/')}/v2/send",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            return resp.status in (200, 201)
    except Exception as e:
        logger.debug(f"Signal notification failed: {e}")
        return False


def save_obsidian_log(
    target_ip: str, results: Dict[str, Tuple[bool, Optional[int]]]
) -> Optional[Path]:
    """Save an update report to Henks Geheugen."""
    if not OBSIDIAN_LOG_DIR.exists():
        logger.debug("Obsidian log directory not accessible.")
        return None

    now = datetime.now()
    ts_str = now.strftime("%Y-%m-%d_%H%M")
    report_file = (
        OBSIDIAN_LOG_DIR / f"{ts_str}_Operationele_Installatie_VM140_Geupdate.md"
    )

    rows: List[str] = []
    for name, (ok, code) in results.items():
        status = f"✅ HTTP {code} OK" if ok else f"❌ HTTP {code or 'DOWN'}"
        rows.append(f"| **{name}** | {status} |")

    content = f"""---
date: {now.strftime('%Y-%m-%d %H:%M')}
project: Njord-deploy
tags:
  - logboek
  - njord-deploy
  - proxmox
  - vm140
  - operational
  - configurator
  - editor
  - proxmox-gui
---

# 📝 Chat Log: Operationele NjordDeploy Installatie Bijgewerkt

- **Datum/Tijd**: {now.strftime('%Y-%m-%d %H:%M')}
- **Project**: Njord-deploy
- **Target Host**: `{target_ip}` (VM 140 `njorddeploy-vm`)

---

## 🔍 Live Status & Verificatie

| Applicatie | Status |
| :--- | :---: |
{chr(10).join(rows)}
"""
    report_file.write_text(content, encoding="utf-8")
    logger.info(f"Saved update report to: {report_file}")
    return report_file


def update_operational_environment(
    target_ip: str,
    user: str,
    password: str,
    force_build: bool = False,
    skip_backup: bool = False,
    signal: bool = False,
    save_log: bool = True,
) -> bool:
    """Execute the end-to-end update of the operational VM."""
    logger.info(f"=== Starting Operational Update for {target_ip} ({user}) ===")

    if force_build or not (project_root / "dist" / "NjordDeployConfigurator").exists():
        if not build_binaries_if_needed(force_build=force_build):
            logger.error("Aborting operational update due to build failure.")
            return False

    ssh = SSHManager(
        hostname=target_ip,
        username=user,
        password=password,
        allow_auto_add=True,
        load_system_keys=False,
    )
    ok, msg = ssh.connect()
    if not ok:
        logger.error(f"Failed to connect to {target_ip}: {msg}")
        return False

    try:
        # 1. Stop services
        logger.info("Stopping running NjordDeploy services on remote host...")
        ssh.execute_command(
            "sudo systemctl stop njorddeploy-configurator "
            "njorddeploy-editor njorddeploy-proxmox-test",
            lambda msg: logger.info(f"[STOP] {msg.strip()}"),
            check_exit_code=False,
        )

        # 2. Point-in-time Backup
        if not skip_backup:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_dir = f"/opt/njorddeploy.bak_{ts}"
            logger.info(f"Creating backup snapshot: {bak_dir}...")
            ssh.execute_command(
                f"sudo mkdir -p {bak_dir} && "
                f"sudo cp -r /opt/njorddeploy/* {bak_dir}/ 2>/dev/null || true",
                lambda x: None,
                check_exit_code=False,
            )

        # 3. Upload new binaries
        sftp = ssh.client.open_sftp()
        binaries = [
            "NjordDeployConfigurator",
            "NjordDeployEditor",
            "NjordDeployProxmoxTest",
        ]
        for b_name in binaries:
            local_bin = project_root / "dist" / b_name
            if not local_bin.exists():
                logger.error(f"Missing required binary: {local_bin}")
                sftp.close()
                return False

            remote_tmp = f"/tmp/{b_name}"  # nosec B108
            remote_target = f"/opt/njorddeploy/{b_name}"
            logger.info(f"Uploading {b_name} ({local_bin.stat().st_size} bytes)...")
            sftp.put(str(local_bin), remote_tmp)
            ssh.execute_command(
                f"sudo mv {remote_tmp} {remote_target} && "
                f"sudo chmod 755 {remote_target} && "
                f"sudo chown hvhoek:hvhoek {remote_target}",
                lambda x: None,
                check_exit_code=False,
            )
        sftp.close()

        # 4. Restart services
        logger.info("Restarting remote systemd services...")
        ssh.execute_command(
            "sudo systemctl daemon-reload && "
            "sudo systemctl start njorddeploy-configurator "
            "njorddeploy-editor njorddeploy-proxmox-test",
            lambda msg: logger.info(f"[START] {msg.strip()}"),
            check_exit_code=False,
        )

        time.sleep(6)

        # 5. Verify Health Checks
        logger.info("Verifying application endpoints...")
        endpoints = {
            "Configurator (5001)": f"http://{target_ip}:5001/",
            "REST API Health (5001)": f"http://{target_ip}:5001/api/health",
            "Component Editor (5000)": f"http://{target_ip}:5000/",
            "Proxmox Test Suite (5050)": f"http://{target_ip}:5050/",
        }

        results: Dict[str, Tuple[bool, Optional[int]]] = {}
        all_passed = True
        for name, url in endpoints.items():
            success, code = verify_http_endpoint(url)
            results[name] = (success, code)
            if success:
                logger.info(f"✅ {name}: HTTP {code} OK")
            else:
                logger.error(f"❌ {name}: Failed verification (code: {code})")
                all_passed = False

        if save_log:
            save_obsidian_log(target_ip, results)

        if signal:
            status_symbol = "✅" if all_passed else "⚠️"
            c_ok = "OK" if results.get("Configurator (5001)", (False, 0))[0] else "FAIL"
            e_ok = (
                "OK"
                if results.get("Component Editor (5000)", (False, 0))[0]
                else "FAIL"
            )
            p_ok = (
                "OK"
                if results.get("Proxmox Test Suite (5050)", (False, 0))[0]
                else "FAIL"
            )
            sig_lines = [
                f"{status_symbol} NjordDeploy Operational Update ({target_ip})",
                f"- Configurator (5001): {c_ok}",
                f"- Editor (5000): {e_ok}",
                f"- Proxmox GUI (5050): {p_ok}",
            ]
            send_signal_notification("\n".join(sig_lines))

        if all_passed:
            logger.info("🎉 Operational environment updated and 100% healthy!")
        else:
            logger.warning(
                "⚠️ Update completed with one or more endpoint check warnings."
            )

        return all_passed

    finally:
        ssh.close()


def main():
    load_dotenv(project_root / ".env")

    parser = argparse.ArgumentParser(
        description="Update operational NjordDeploy installation on Proxmox VM."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("OPERATIONAL_VM_IP") or DEFAULT_TARGET_IP,
        help=f"Target host IP (default: {DEFAULT_TARGET_IP})",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("PROXMOX_VM_USER") or DEFAULT_TARGET_USER,
        help=f"SSH username (default: {DEFAULT_TARGET_USER})",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("PROXMOX_VM_PASSWORD") or "",
        help="SSH password",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Force re-compilation of binaries before deployment",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip taking backup of remote /opt/njorddeploy",
    )
    parser.add_argument(
        "--signal",
        action="store_true",
        help="Send summary alert via Signal Messenger",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Do not save log report in Henks Geheugen",
    )

    args = parser.parse_args()

    target_host = args.host
    pve_client = None
    if os.getenv("PROXMOX_HOST") and os.getenv("PROXMOX_TOKEN_ID"):
        # noinspection PyBroadException
        try:
            pve_client = ProxmoxClient(
                host=os.getenv("PROXMOX_HOST", ""),
                user=os.getenv("PROXMOX_USER", "root@pam"),
                token_id=os.getenv("PROXMOX_TOKEN_ID", ""),
                token_secret=os.getenv("PROXMOX_TOKEN_SECRET", ""),
            )
        except Exception as e:
            logger.debug(f"Proxmox client initialization error: {e}")

    node = os.getenv("PROXMOX_NODE", "pve")
    if pve_client:
        # noinspection PyBroadException
        try:
            vm_st = pve_client.get_vm_status(node, DEFAULT_VMID).get("data", {})
            if vm_st.get("status") == "stopped":
                logger.info(f"VM {DEFAULT_VMID} is stopped. Starting VM...")
                pve_client.start_vm(node, DEFAULT_VMID)
                for _ in range(20):
                    time.sleep(2)
                    cur_st = pve_client.get_vm_status(node, DEFAULT_VMID).get(
                        "data", {}
                    )
                    if cur_st.get("status") == "running":
                        break
        except Exception as e:
            logger.debug(f"Could not verify VM status via Proxmox API: {e}")

    target_host = get_operational_ip(pve_client, node, DEFAULT_VMID, target_host)

    success = update_operational_environment(
        target_ip=target_host,
        user=args.user,
        password=args.password,
        force_build=args.build,
        skip_backup=args.skip_backup,
        signal=args.signal,
        save_log=not args.no_log,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
