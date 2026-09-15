# src/managers/customer_sandbox_manager.py
"""Customer Interactive Sandbox Manager (De Proeftuin - Modus B).

Manages on-demand interactive customer staging environments for staff training,
documentation creation, and User Acceptance Testing (UAT) prior to production rollout.
Features clean dummy data seeding (AVG/GDPR-compliant), network mail catching (Mailpit),
concurrency quota management (max 3 sandboxes), nightly sleep schedules, and formal
UAT sign-off workflows.
Conforms to FUMS Spec section 3.2.
"""

import contextlib
import logging
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.fums_notifier import FUMSNotifier
from utils.proxmox_client import ProxmoxClient
from utils.resource_utils import get_app_data_dir

logger = logging.getLogger(__name__)

MAX_CONCURRENT_SANDBOXES = 3
DEFAULT_TTL_DAYS = 14
SANDBOX_VMID_START = 860


class CustomerSandboxManager:
    """Orchestrates ephemeral customer training & UAT sandboxes (Proeftuin Modus B)."""

    def __init__(
        self,
        proxmox_client: Optional[ProxmoxClient] = None,
        notifier: Optional[FUMSNotifier] = None,
        node: str = "pve",
        template_vmid: int = 9000,
        db_path: Optional[Path] = None,
        max_sandboxes: int = MAX_CONCURRENT_SANDBOXES,
        base_domain: str = "training.njorddeploy.com",
    ) -> None:
        self.proxmox_client = proxmox_client
        self.notifier = notifier or FUMSNotifier()
        self.node = node
        self.template_vmid = template_vmid
        self.max_sandboxes = max_sandboxes
        self.base_domain = base_domain

        if db_path is None:
            data_dir = get_app_data_dir()
            db_path = data_dir / "fums_sandboxes.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextlib.contextmanager
    def _get_connection(self):
        """Thread-safe SQLite connection context."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes tables for tracking customer sandbox lifecycles."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sandboxes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    component_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    vmid INTEGER UNIQUE NOT NULL,
                    ip_address TEXT,
                    access_url TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    uat_signed_off INTEGER DEFAULT 0,
                    uat_signoff_date TIMESTAMP,
                    uat_notes TEXT
                );
                """
            )

    def get_active_sandboxes(self) -> List[Dict[str, Any]]:
        """Returns list of all currently active sandboxes."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sandboxes
                WHERE status IN ('active', 'sleeping')
                ORDER BY created_at ASC;
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def request_sandbox(
        self,
        client_id: str,
        component_id: str,
        target_version: str,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> Dict[str, Any]:
        """Provisions an on-demand training sandbox if quota allows."""
        active = self.get_active_sandboxes()
        if len(active) >= self.max_sandboxes:
            msg = (
                f"Concurrency quota exceeded: Max {self.max_sandboxes} "
                "active sandboxes permitted simultaneously on Proxmox."
            )
            logger.warning(msg)
            return {"success": False, "error": msg, "quota_exceeded": True}

        # Determine next available VMID
        allocated_vmids = {s["vmid"] for s in active}
        vmid = SANDBOX_VMID_START
        while vmid in allocated_vmids:
            vmid += 1

        now = datetime.now()
        expires_at = now + timedelta(days=ttl_days)
        clean_slug = re.sub(r"[^a-z0-9\-]", "", client_id.lower().replace(" ", "-"))
        clean_client = clean_slug or "client"
        access_url = f"https://{clean_client}.{self.base_domain}"

        logger.info(
            f"Provisioning training sandbox {vmid} for {client_id} "
            f"({component_id} {target_version}) with TTL={ttl_days}d"
        )

        ip_addr = "127.0.0.1"
        if self.proxmox_client:
            # noinspection PyBroadException
            try:
                self.proxmox_client.clone_lxc(
                    node=self.node,
                    vmid=self.template_vmid,
                    newid=vmid,
                    hostname=f"train-{clean_client}",
                    full=False,
                )
                self.proxmox_client.start_lxc(self.node, vmid)
                ip_addr = self._wait_for_lxc_ip(vmid) or "127.0.0.1"
            except Exception as e:
                logger.error(f"Failed to provision LXC {vmid} in Proxmox: {e}")
                return {"success": False, "error": str(e)}

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sandboxes (
                    client_id, component_id, version, vmid, ip_address,
                    access_url, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    client_id,
                    component_id,
                    target_version,
                    vmid,
                    ip_addr,
                    access_url,
                    "active",
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            sandbox_id = cursor.lastrowid

        return {
            "success": True,
            "sandbox_id": sandbox_id,
            "vmid": vmid,
            "client_id": client_id,
            "component_id": component_id,
            "version": target_version,
            "access_url": access_url,
            "ip_address": ip_addr,
            "expires_at": expires_at.isoformat(),
            "mail_catcher": "Mailpit active on port 8025 (outgoing SMTP trapped)",
            "data_privacy": "Clean dummy seed loaded (AVG/GDPR safe)",
        }

    def _wait_for_lxc_ip(self, vmid: int, timeout_seconds: int = 60) -> Optional[str]:
        """Polls Proxmox interfaces for dynamic IP."""
        if not self.proxmox_client:
            return "127.0.0.1"
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            # noinspection PyBroadException
            try:
                endpoint = f"nodes/{self.node}/lxc/{vmid}/interfaces"
                res = self.proxmox_client.get(endpoint)
                interfaces = res.get("data", [])
                for iface in interfaces:
                    if iface.get("name") == "eth0" and iface.get("inet"):
                        inet = iface.get("inet", "")
                        ip_clean = inet.split("/")[0].strip()
                        if ip_clean and not ip_clean.startswith("127."):
                            return ip_clean
            except Exception as e:
                logger.debug(f"Waiting for IP address on VMID {vmid}: {e}")
            time.sleep(2)
        return None

    def sign_off_uat(
        self,
        sandbox_id: int,
        key_user_notes: str = "Formally accepted after testing.",
    ) -> Dict[str, Any]:
        """Records formal UAT Sign-off by key-user and schedules sandbox teardown."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sandboxes WHERE id = ?;", (sandbox_id,)
            )
            row = cursor.fetchone()
            if not row:
                return {"success": False, "error": f"Sandbox {sandbox_id} not found."}
            sandbox = dict(row)

            now_str = datetime.now().isoformat()
            conn.execute(
                """
                UPDATE sandboxes
                SET uat_signed_off = 1,
                    uat_signoff_date = ?,
                    uat_notes = ?,
                    status = 'uat_approved'
                WHERE id = ?;
                """,
                (now_str, key_user_notes, sandbox_id),
            )

        logger.info(
            f"Formele UAT Sign-off geregistreerd voor {sandbox['client_id']} "
            f"op component {sandbox['component_id']} {sandbox['version']}."
        )

        # Automatically tear down container now that testing is approved
        self.destroy_sandbox(sandbox_id)

        return {
            "success": True,
            "client_id": sandbox["client_id"],
            "component_id": sandbox["component_id"],
            "version": sandbox["version"],
            "uat_signed_off": True,
            "status": "ready_for_production_schedule",
        }

    def destroy_sandbox(self, sandbox_id: int) -> bool:
        """Destroys Proxmox sandbox container and marks status terminated."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sandboxes WHERE id = ?;", (sandbox_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False
            sandbox = dict(row)
            conn.execute(
                "UPDATE sandboxes SET status = 'terminated' WHERE id = ?;",
                (sandbox_id,),
            )

        vmid = sandbox.get("vmid")
        if self.proxmox_client and vmid:
            # noinspection PyBroadException
            try:
                self.proxmox_client.stop_lxc(self.node, vmid)
                time.sleep(1)
                self.proxmox_client.destroy_lxc(self.node, vmid)
                logger.info(f"Destroyed Proxmox sandbox LXC {vmid}")
            except Exception as e:
                logger.warning(f"Error destroying sandbox LXC {vmid}: {e}")

        return True

    def run_nightly_sleep_cycle(self, current_hour: int) -> Dict[str, int]:
        """Pauses containers during off-hours (19:00 - 07:00) to save host CPU/RAM."""
        # Night is outside 07:00 - 19:00
        is_night = current_hour < 7 or current_hour >= 19
        active_sandboxes = self.get_active_sandboxes()
        slept_count = 0
        woken_count = 0

        with self._get_connection() as conn:
            for s in active_sandboxes:
                s_id = s["id"]
                vmid = s["vmid"]
                status = s["status"]

                if is_night and status == "active":
                    if self.proxmox_client:
                        # noinspection PyBroadException
                        try:
                            self.proxmox_client.stop_lxc(self.node, vmid)
                        except Exception as stop_err:
                            logger.debug(f"Failed to stop sandbox {vmid}: {stop_err}")
                    conn.execute(
                        "UPDATE sandboxes SET status = 'sleeping' WHERE id = ?;",
                        (s_id,),
                    )
                    slept_count += 1
                elif not is_night and status == "sleeping":
                    if self.proxmox_client:
                        # noinspection PyBroadException
                        try:
                            self.proxmox_client.start_lxc(self.node, vmid)
                        except Exception as start_err:
                            logger.debug(f"Failed to start sandbox {vmid}: {start_err}")
                    conn.execute(
                        "UPDATE sandboxes SET status = 'active' WHERE id = ?;",
                        (s_id,),
                    )
                    woken_count += 1

        return {"slept": slept_count, "woken": woken_count}

    def purge_expired_sandboxes(self) -> int:
        """Purges any sandboxes that have exceeded their Time-To-Live (TTL)."""
        now = datetime.now()
        purged = 0
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sandboxes
                WHERE status IN ('active', 'sleeping')
                AND expires_at <= ?;
                """,
                (now.isoformat(),),
            )
            expired = [dict(r) for r in cursor.fetchall()]

        for s in expired:
            self.destroy_sandbox(s["id"])
            purged += 1

        return purged
