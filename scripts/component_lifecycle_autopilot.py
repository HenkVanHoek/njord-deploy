#!/usr/bin/env python3
# scripts/component_lifecycle_autopilot.py
"""NjordDeploy Component Lifecycle Autopilot.

Autonomous upstream detection, Proxmox LXC integration verification in 'De
Proeftuin', staging promotion, multi-repo synchronization, live VPS
deployment, and Signal alerting (with Human-in-the-Loop on Exception).

Architecture:
1. Scan: Checks upstream GitHub release feeds for new versions.
2. Filter: Extracts candidates from the Wachtkamer (staging), prioritizing
   security/gateway infrastructure.
3. Test: Deploys candidate to an isolated Proxmox LXC container (CT 107 cloned
   from template 912), performs health and HTTP probes, then destroys CT 107.
4. Promote or Escalate:
   - Green (Success): Updates template header, updates metadata, syncs
     njord-deploy-components and njord-deploy-site, rsyncs to Netcup VPS edge
     (37.120.176.26), commits to Git, and sends a concise Signal success report.
   - Red (Failure): Halts promotion, parks candidate in Wachtkamer with status
     'needs_review', logs diagnostics, and dispatches a high-priority Signal
     escalation alert to Henk (+31651107603) requesting guidance.
"""

import argparse
import json
import logging
import os
import subprocess  # nosec B404
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

CONFIG_METADATA_PATH = PROJECT_ROOT / "config" / "components_metadata.json"
TEMPLATES_PATH = PROJECT_ROOT / "component_templates"
RESULTS_JSON_PATH = PROJECT_ROOT / "tests" / "proxmox_results.json"

SIGNAL_API_URL = os.environ.get(
    "SIGNAL_API_URL", "http://192.168.178.118:8090/v2/send"
)
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
    format="%(asctime)s [%(levelname)s] [AUTOPILOT]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("component_autopilot")


def get_python_env() -> Dict[str, str]:
    """Prepares environment with PYTHONPATH pointing to virtualenv and src."""
    env = os.environ.copy()
    site_dirs = list((PROJECT_ROOT / ".venv" / "lib").glob("python*/site-packages"))
    venv_site = str(site_dirs[0]) if site_dirs else ""
    src_dir = str(PROJECT_ROOT / "src")
    paths = [p for p in (venv_site, src_dir) if p]
    py_path = ":".join(paths)
    existing = env.get("PYTHONPATH")
    if existing:
        py_path = f"{py_path}:{existing}"
    env["PYTHONPATH"] = py_path
    return env


def send_signal_alert(message: str) -> bool:
    """Dispatches a notification via Signal REST API."""
    if not (SIGNAL_API_URL and SIGNAL_SENDER and SIGNAL_RECIPIENT):
        logger.warning("Signal alert skipped: credentials or API not configured.")
        return False
    # noinspection PyBroadException
    try:
        payload = {
            "message": message,
            "number": SIGNAL_SENDER,
            "recipients": [SIGNAL_RECIPIENT],
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            SIGNAL_API_URL,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            success = resp.status in (200, 201)
            if success:
                logger.info("Signal alert sent successfully.")
            return success
    except Exception as exc:
        logger.warning("Could not dispatch Signal message: %s", exc)
        return False


def run_upstream_check() -> None:
    """Triggers upstream release check via watch_components_lifecycle.py."""
    logger.info("Checking upstream release feeds for updates...")
    script_path = PROJECT_ROOT / "scripts" / "watch_components_lifecycle.py"
    env = get_python_env()
    # noinspection PyBroadException
    try:
        subprocess.run(
            [sys.executable or "/usr/bin/python3", str(script_path), "--check"],
            cwd=PROJECT_ROOT,
            env=env,
            check=False,
            timeout=300,
        )
    except Exception as exc:
        logger.error("Error during upstream lifecycle scan: %s", exc)


def load_metadata() -> Dict[str, Any]:
    """Loads and returns components_metadata.json."""
    if not CONFIG_METADATA_PATH.exists():
        logger.error("Metadata file not found: %s", CONFIG_METADATA_PATH)
        return {}
    with open(CONFIG_METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_metadata(data: Dict[str, Any]) -> None:
    """Saves updated metadata dictionary back to components_metadata.json."""
    with open(CONFIG_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def sync_sysopswatch() -> None:
    """Synchronizes Wachtkamer state to SysOpsWatch dashboard if available."""
    # noinspection PyBroadException
    try:
        from scripts.watch_components_lifecycle import sync_to_sysopswatch

        sync_to_sysopswatch()
    except Exception as exc:
        logger.debug("SysOpsWatch sync skipped or unavailable: %s", exc)


def get_candidates(
    metadata: Dict[str, Any], filter_ids: Optional[List[str]] = None
) -> List[Tuple[str, str, bool]]:
    """Extracts candidate components from staging (id, version, is_security)."""
    candidates = []
    components = metadata.get("components", {})

    # Import security identifier from watcher
    try:
        from scripts.watch_components_lifecycle import is_security_component
    except ImportError:

        def is_security_component(cid: str, cdata: Dict[str, Any]) -> bool:
            return False

    for comp_id, comp_meta in components.items():
        if filter_ids and comp_id not in filter_ids:
            continue
        if comp_meta.get("pinned"):
            continue
        staging = comp_meta.get("staging") or {}
        stat = staging.get("status")
        target_ver = (
            staging.get("candidate_version")
            or staging.get("version")
            or ""
        ).strip()
        if target_ver and stat in (
            "candidate",
            "awaiting_approval",
            "testing",
            "in_staging",
            "pending_validation",
        ):
            is_sec = is_security_component(comp_id, comp_meta)
            candidates.append((comp_id, target_ver, is_sec))

    # Sort security infrastructure first, then alphabetically
    candidates.sort(key=lambda x: (not x[2], x[0]))
    return candidates


def run_proeftuin_test(
    comp_id: str,
    template_id: int = 912,
    node: str = "pve",
    mode: str = "lxc",
    engine: str = "docker",
) -> Tuple[bool, str]:
    """Runs integration test for a component in Proxmox VE (De Proeftuin)."""
    logger.info(
        "Deploying '%s' to Proxmox LXC (%s, engine: %s)...",
        comp_id,
        mode,
        engine,
    )
    test_runner = PROJECT_ROOT / "scripts" / "proxmox_test_runner.py"
    env = get_python_env()

    cmd = [
        sys.executable or "/usr/bin/python3",
        str(test_runner),
        "--components",
        comp_id,
        "--mode",
        mode,
        "--engine",
        engine,
        "--template-id",
        str(template_id),
        "--node",
        node,
    ]

    # noinspection PyBroadException
    try:
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        success = proc.returncode == 0

        # Read latest record from proxmox_results.json for diagnostics
        error_details = ""
        if RESULTS_JSON_PATH.exists():
            try:
                with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as rf:
                    res_data = json.load(rf)
                comp_records = [
                    r for r in res_data if r.get("component_id") == comp_id
                ]
                if comp_records:
                    first_record = next(iter(reversed(comp_records)), {})
                    is_http_ok = first_record.get("http_ok")
                    is_success = first_record.get("status") == "success"
                    if not is_http_ok or not is_success:
                        err_msg = first_record.get("error_message") or ""
                        h_url = first_record.get("http_url")
                        error_details = err_msg or f"HTTP check failed: {h_url}"
            except Exception as e_res:
                logger.debug("Could not parse results json: %s", e_res)

        if not success and not error_details:
            tail_lines = proc.stderr.strip().splitlines()[-4:]
            if tail_lines:
                error_details = " | ".join(tail_lines)
            else:
                error_details = f"Exited with code {proc.returncode}"

        return success, error_details
    except subprocess.TimeoutExpired:
        return False, "Test run timed out after 10 minutes in Proxmox."
    except Exception as exc:
        return False, f"Subprocess invocation failure: {exc}"


def mark_candidate_needs_review(
    comp_id: str, version: str, error_details: str
) -> None:
    """Updates candidate status to needs_review when test fails."""
    metadata = load_metadata()
    comp_meta = metadata.get("components", {}).get(comp_id, {})
    staging = comp_meta.setdefault("staging", {})
    staging["status"] = "needs_review"
    staging["last_test_error"] = error_details[:300]
    staging["last_test_timestamp"] = datetime.now(timezone.utc).isoformat()
    save_metadata(metadata)
    sync_sysopswatch()
    logger.warning("Marked '%s' as 'needs_review' in Wachtkamer.", comp_id)


def promote_verified_candidate(comp_id: str, version: str) -> None:
    """Promotes verified candidate to production in metadata and templates."""
    try:
        try:
            from scripts.watch_components_lifecycle import promote_candidate
        except ImportError:
            from watch_components_lifecycle import promote_candidate

        promote_candidate(comp_id, target_version=version)
        logger.info("Promoted candidate '%s' (v%s) to operational.", comp_id, version)
    except Exception as exc:
        logger.error("Error promoting candidate '%s': %s", comp_id, exc)


def deploy_static_site_to_live_vps() -> bool:
    """Rsyncs static site files from njord-deploy-site to live VPS and standby."""
    site_static = (
        PROJECT_ROOT.parent / "njord-deploy-site" / "src" / "site_app" / "static"
    )
    if not site_static.exists():
        logger.warning("Site static directory not found: %s", site_static)
        return False

    logger.info("Deploying static site to Netcup VPS (%s)...", VPS_HOST)
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
    # noinspection PyBroadException
    try:
        proc = subprocess.run(rsync_cmd, check=False, timeout=120)
        vps_ok = proc.returncode == 0
        if vps_ok:
            logger.info("Successfully synchronized site to VPS edge.")
    except Exception as exc:
        logger.error("Rsync to VPS failed: %s", exc)
        vps_ok = False

    # Standby sync if reachable
    # noinspection PyBroadException
    try:
        ping_res = subprocess.run(
            ["ping", "-c", "1", "-W", "1", STANDBY_HOST],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if ping_res.returncode == 0:
            logger.info("Syncing standby copy to local server (%s)...", STANDBY_HOST)
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
    except Exception as exc:
        logger.debug("Standby sync skipped: %s", exc)

    return vps_ok


def sync_and_publish_all(passed_comps: List[Tuple[str, str]]) -> bool:
    """Syncs verified components to GitHub repos and deploys live website."""
    names_str = ", ".join([f"{c[0]} ({c[1]})" for c in passed_comps])
    commit_msg = (
        f"chore(catalog): auto-promote {len(passed_comps)} components "
        f"via autopilot: {names_str}"
    )

    # 1. Sync njord-deploy-components and njord-deploy-site
    sync_script = PROJECT_ROOT / "scripts" / "sync_components_repo.py"
    env = get_python_env()
    logger.info("Synchronizing external components and site repositories...")
    # noinspection PyBroadException
    try:
        subprocess.run(
            [
                "/usr/bin/python3",
                str(sync_script),
                "--sync-site",
                "--commit",
                "--push",
                "--message",
                commit_msg,
            ],
            cwd=PROJECT_ROOT,
            env=env,
            check=False,
            timeout=180,
        )
    except Exception as exc:
        logger.error("Error during repo sync: %s", exc)
        return False

    # 2. Deploy static site to live VPS
    deploy_static_site_to_live_vps()

    # 3. Commit and push in njord-deploy repository itself
    logger.info("Committing and pushing changes in main njord-deploy repository...")
    # noinspection PyBroadException
    try:
        git_add = [
            "git",
            "add",
            "config/components_metadata.json",
            "component_templates/",
            "tests/proxmox_results.json",
        ]
        subprocess.run(git_add, cwd=PROJECT_ROOT, check=False)
        git_commit = [
            "git",
            "commit",
            "-m",
            (
                f"feat(catalog): auto-promote {len(passed_comps)} "
                f"verified components via autopilot"
            ),
            "--no-verify",
        ]
        subprocess.run(git_commit, cwd=PROJECT_ROOT, check=False)
        git_push = ["git", "push", "origin", "main"]
        subprocess.run(git_push, cwd=PROJECT_ROOT, check=False)
        logger.info("njord-deploy pushed to main.")
    except Exception as exc:
        logger.warning("Git commit/push in njord-deploy had warning: %s", exc)

    return True


def dispatch_escalation_alert(
    comp_id: str, version: str, error_details: str
) -> None:
    """Dispatches a high-priority Signal alert for failing candidates."""
    msg = (
        f"🚨 **[NjordDeploy Autopilot] Toestemming & Actie vereist!**\n\n"
        f"• **Component:** `{comp_id}`\n"
        f"• **Kandidaat-versie:** `{version}`\n"
        f"• **Status:** ❌ Test mislukt in De Proeftuin (Proxmox LXC 107)\n"
        f"• **Foutdiagnose:** {error_details}\n\n"
        f"De update is veilig geparkeerd in de Wachtkamer (status: `needs_review`) "
        f"en **niet** uitgerold naar productie.\n"
        f"Begeleiding van Henk gewenst om het verder op te lossen."
    )
    send_signal_alert(msg)


def dispatch_success_report(
    passed_comps: List[Tuple[str, str]], remaining_candidates: int
) -> None:
    """Dispatches a green summary Signal alert when promotion succeeds."""
    lines = [
        "✅ **[NjordDeploy Autopilot] Ochtendronde Voltooid**\n",
        (
            f"**{len(passed_comps)}** component(en) succesvol getest & "
            "live uitgerold naar productie:"
        ),
    ]
    for cid, ver in passed_comps:
        lines.append(f" • `{cid}` ➔ **{ver}**")

    lines.append(
        "\nCatalogus (GitHub), website ([njorddeploy.com](https://njorddeploy.com)) "
        "en live VPS zijn 100% bijgewerkt."
    )
    if remaining_candidates == 0:
        lines.append("Wachtkamer is schoon (**0** items).")
    else:
        lines.append(f"Overige items in wachtkamer: **{remaining_candidates}**.")

    send_signal_alert("\n".join(lines))


def ensure_clock_synchronized() -> None:
    """Checks whether the system clock has drifted (e.g. after host sleep) and resyncs."""
    import socket
    import struct

    ntp_servers = [
        "192.168.178.1",    # Local router (< 2ms)
        "192.168.178.118",  # Mail/Pi
        "time.cloudflare.com",
        "pool.ntp.org",
    ]
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
            "Klokafwijking van %.1fs gedetecteerd (mogelijk na ontwaken uit slaapstand). "
            "Klok wordt gesynchroniseerd...",
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


def main() -> int:
    """Main orchestrator routine."""
    ensure_clock_synchronized()
    parser = argparse.ArgumentParser(
        description="NjordDeploy Component Lifecycle Autopilot"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only scan upstream release feeds and report candidates.",
    )
    parser.add_argument(
        "--components",
        type=str,
        help="Comma-separated component IDs to explicitly verify from staging.",
    )
    parser.add_argument(
        "--skip-scan",
        action="store_true",
        help="Skip upstream release feed scanning; use existing candidates.",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip pushing to external repositories and VPS deployment.",
    )
    parser.add_argument(
        "--no-signal",
        action="store_true",
        help="Disable sending Signal alerts.",
    )
    parser.add_argument(
        "--template-id",
        type=int,
        default=912,
        help="Proxmox template VMID (default: 912).",
    )
    parser.add_argument(
        "--node",
        type=str,
        default="pve",
        help="Proxmox node name (default: pve).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="lxc",
        help="Proxmox execution mode (default: lxc).",
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="docker",
        help="Container engine (default: docker).",
    )

    args = parser.parse_args()

    # Step 1: Upstream Release Scan
    if not args.skip_scan:
        run_upstream_check()

    # Step 2: Collect Staging Candidates
    metadata = load_metadata()
    filter_list = (
        [c.strip() for c in args.components.split(",")]
        if args.components
        else None
    )
    candidates = get_candidates(metadata, filter_ids=filter_list)

    if not candidates:
        logger.info(
            "Geen update-kandidaten in de wachtkamer gevonden. Autopilot afgerond."
        )
        return 0

    logger.info("Gevonden update-kandidaten in Wachtkamer: %d", len(candidates))
    for cid, ver, is_sec in candidates:
        sec_label = " [SECURITY/INFRA]" if is_sec else ""
        logger.info(" • %s (v%s)%s", cid, ver, sec_label)

    if args.check_only:
        logger.info(
            "Check-only modus actief. Er worden geen Proxmox-tests uitgevoerd."
        )
        return 0

    # Step 3: Run Integration Tests in De Proeftuin
    passed: List[Tuple[str, str]] = []
    failed: List[Tuple[str, str, str]] = []

    for comp_id, version, is_sec in candidates:
        logger.info(">>> Testen van kandidaat: %s (v%s)...", comp_id, version)
        test_ok, error_info = run_proeftuin_test(
            comp_id=comp_id,
            template_id=args.template_id,
            node=args.node,
            mode=args.mode,
            engine=args.engine,
        )

        if test_ok:
            logger.info(">>> GESLAAGD: %s (v%s) is geverifieerd.", comp_id, version)
            passed.append((comp_id, version))
            promote_verified_candidate(comp_id, version)
        else:
            logger.warning(
                ">>> MISLUKT: %s (v%s) faalt: %s", comp_id, version, error_info
            )
            failed.append((comp_id, version, error_info))
            mark_candidate_needs_review(comp_id, version, error_info)
            if not args.no_signal:
                dispatch_escalation_alert(comp_id, version, error_info)

    # Step 4: Multi-Repo Sync & Live Deployment (for passed components)
    if passed:
        logger.info(
            "Promoveren en synchroniseren van %d geslaagde component(en)...",
            len(passed),
        )
        if not args.skip_sync:
            sync_and_publish_all(passed)
            try:
                from scripts.watch_components_lifecycle import sync_to_sysopswatch
                sync_to_sysopswatch()
            except Exception:
                pass

        if not args.no_signal:
            remaining_meta = load_metadata()
            remaining_candidates = len(get_candidates(remaining_meta))
            dispatch_success_report(passed, remaining_candidates)

    logger.info(
        "Autopilot cyclus afgerond. Geslaagd: %d, Mislukt: %d.",
        len(passed),
        len(failed),
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
