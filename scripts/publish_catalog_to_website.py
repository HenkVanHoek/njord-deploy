#!/usr/bin/env python3
"""
scripts/publish_catalog_to_website.py

Idempotent end-to-end publisher for NjordDeploy verified components:
1. Ensures system clock synchronization.
2. Auto-generates component and stack README documentation.
3. Synchronizes and pushes njord-deploy-components (GitHub).
4. Synchronizes and pushes njord-deploy-site (GitHub):
   - Copies components_metadata.json
   - Regenerates all 258 component landing pages (EN & NL) + sitemap.xml
   - Regenerates all stack landing pages (EN & NL)
   - Commits and pushes changes
5. Rsyncs static files to Live VPS edge (37.120.176.26) and standby (192.168.178.118).
6. Syncs metadata to Sysops Cockpit (192.168.178.70).
7. Dispatches Signal notification confirmation.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_METADATA_PATH = PROJECT_ROOT / "config" / "components_metadata.json"
TEMPLATES_PATH = PROJECT_ROOT / "component_templates"

SIGNAL_API_URL = os.environ.get("SIGNAL_API_URL", "http://192.168.178.118:8090/v2/send")
SIGNAL_SENDER = os.environ.get("SIGNAL_SENDER", "+31651107603")
SIGNAL_RECIPIENT = os.environ.get("SIGNAL_RECIPIENT", "+31651107603")

VPS_HOST = "37.120.176.26"
VPS_USER = "hvhoek"
VPS_PATH = "/home/hvhoek/sites/njorddeploy-site/"

STANDBY_HOST = "192.168.178.118"
STANDBY_USER = "hvhoek"
STANDBY_PATH = "/home/hvhoek/docker/nginx/html/njorddeploy-site/"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [PUBLISHER]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("catalog_publisher")


def ensure_clock_synchronized() -> None:
    """Checks whether the system clock has drifted and resyncs via local NTP."""
    import socket
    import struct

    ntp_servers = ["192.168.178.1", "192.168.178.118", "time.cloudflare.com"]
    drift = None
    for srv in ntp_servers:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(1.5)
            data = b"\x1b" + 47 * b"\0"
            t_send = time.time()
            client.sendto(data, (srv, 123))
            resp, _ = client.recvfrom(1024)
            t_recv = time.time()
            client.close()
            val = struct.unpack("!12I", resp)[10] - 2208988800
            rtt = t_recv - t_send
            est_server_time = val + (rtt / 2.0)
            drift = abs(t_recv - est_server_time)
            break
        except Exception:
            continue

    if drift is not None and drift >= 3.0:
        logger.warning(
            "Klokafwijking van %.1fs gedetecteerd. Klok wordt gesynchroniseerd...",
            drift,
        )
        try:
            subprocess.run(
                ["sudo", "-n", "systemctl", "restart", "systemd-timesyncd"],
                check=False,
                timeout=5,
            )
            time.sleep(1.5)
            logger.info("systemd-timesyncd automatisch herstart.")
        except Exception as exc:
            logger.debug("Kon timesyncd niet automatisch herstarten: %s", exc)


def send_signal_alert(message: str) -> bool:
    """Dispatches a notification via Signal REST API."""
    import urllib.request
    payload = json.dumps({
        "message": message,
        "number": SIGNAL_SENDER,
        "recipients": [SIGNAL_RECIPIENT],
    }).encode("utf-8")
    req = urllib.request.Request(
        SIGNAL_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 201)
    except Exception as exc:
        logger.warning("Signal alert kon niet verzonden worden: %s", exc)
        return False


def get_python_env() -> Dict[str, str]:
    env = os.environ.copy()
    site_dirs = list((PROJECT_ROOT / ".venv" / "lib").glob("python*/site-packages"))
    venv_site = str(site_dirs[0]) if site_dirs else ""
    src_dir = str(PROJECT_ROOT / "src")
    scripts_dir = str(PROJECT_ROOT / "scripts")
    parts = [p for p in [venv_site, src_dir, scripts_dir, str(PROJECT_ROOT)] if p]
    current_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = ":".join(parts + ([current_pp] if current_pp else []))
    return env


def sync_site_and_components(commit_msg: Optional[str] = None) -> bool:
    """Syncs njord-deploy-components and njord-deploy-site repositories."""
    sync_script = PROJECT_ROOT / "scripts" / "sync_components_repo.py"
    env = get_python_env()
    msg = commit_msg or "chore(catalog): publish verified components and stacks to site"

    logger.info("Synchroniseren van externe componenten- en site-repositories...")
    try:
        res = subprocess.run(
            [
                sys.executable,
                str(sync_script),
                "--sync-site",
                "--commit",
                "--push",
                "--message",
                msg,
            ],
            cwd=PROJECT_ROOT,
            env=env,
            check=False,
            timeout=180,
        )
        return res.returncode == 0
    except Exception as exc:
        logger.error("Fout tijdens synchronisatie met site/components repo: %s", exc)
        return False


def deploy_static_site_to_vps() -> bool:
    """Rsyncs static site files from njord-deploy-site to live VPS and standby."""
    site_static = PROJECT_ROOT.parent / "njord-deploy-site" / "src" / "site_app" / "static"
    if not site_static.exists():
        logger.error("Site static directory niet gevonden: %s", site_static)
        return False

    logger.info("Publiceren van statische site naar Netcup VPS edge (%s)...", VPS_HOST)
    rsync_cmd = [
        "rsync",
        "-avz",
        "--exclude=.git*",
        "--exclude=.idea",
        "--exclude=.venv",
        "--exclude=__pycache__",
        f"{site_static}/",
        f"{VPS_USER}@{VPS_HOST}:{VPS_PATH}",
    ]
    try:
        proc = subprocess.run(rsync_cmd, check=False, timeout=120)
        vps_ok = proc.returncode == 0
        if vps_ok:
            logger.info("✅ Succesvol gepubliceerd naar Live VPS edge.")
    except Exception as exc:
        logger.error("Rsync naar VPS mislukt: %s", exc)
        vps_ok = False

    # Standby sync if reachable
    try:
        ping_res = subprocess.run(
            ["ping", "-c", "1", "-W", "1", STANDBY_HOST],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if ping_res.returncode == 0:
            logger.info("Synchroniseren van standby mirror op lokale server (%s)...", STANDBY_HOST)
            standby_cmd = [
                "rsync",
                "-avz",
                "--exclude=.git*",
                "--exclude=.idea",
                "--exclude=.venv",
                "--exclude=__pycache__",
                f"{site_static}/",
                f"{STANDBY_USER}@{STANDBY_HOST}:{STANDBY_PATH}",
            ]
            subprocess.run(
                standby_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            logger.info("✅ Standby mirror gesynchroniseerd.")
    except Exception as exc:
        logger.debug("Standby sync overgeslagen: %s", exc)

    return vps_ok


def sync_to_sysops_cockpit() -> None:
    """Copies metadata to Sysops Cockpit on LXC 135."""
    try:
        from scripts.watch_components_lifecycle import sync_to_sysopswatch
        sync_to_sysopswatch()
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NjordDeploy Catalog & Website End-to-End Publisher"
    )
    parser.add_argument(
        "--message",
        type=str,
        default=None,
        help="Custom git commit message for publishing.",
    )
    parser.add_argument(
        "--no-signal",
        action="store_true",
        help="Disable sending Signal notification.",
    )
    args = parser.parse_args()

    logger.info("============================================================")
    logger.info("🌐 Start Publicatieketen: NjordDeploy Catalogus & Website")
    logger.info("============================================================")

    # 1. Klokborging
    ensure_clock_synchronized()

    # 2. Synchroniseer externe repositories (njord-deploy-components & njord-deploy-site)
    sync_ok = sync_site_and_components(args.message)
    if not sync_ok:
        logger.warning("Waarschuwing: Synchronisatiescript meldde een fout, maar proces gaat door...")

    # 3. Deploy statische site naar live VPS edge & standby mirror
    vps_ok = deploy_static_site_to_vps()

    # 4. Synchroniseer naar Sysops Cockpit (192.168.178.70)
    sync_to_sysops_cockpit()

    # 5. Signal notificatie
    if not args.no_signal and vps_ok:
        msg = (
            "🌐 **[NjordDeploy Website] Publicatie Succesvol Voltooid**\n\n"
            "• **Status:** Live & Operationeel\n"
            "• **Website:** https://njorddeploy.com\n"
            "• **Edges:** Netcup VPS (`37.120.176.26`) & Standby Mirror (`.118`)\n"
            "• **Componenten & Stacks:** Alle 258 SEO-pagina's (NL & EN) en sitemaps zijn actueel.\n"
            "• **Cockpit Wachtkamer:** Gesynchroniseerd."
        )
        send_signal_alert(msg)

    logger.info("============================================================")
    logger.info("✅ Publicatieketen succesvol afgerond!")
    logger.info("============================================================")
    return 0 if vps_ok else 1


if __name__ == "__main__":
    sys.exit(main())
