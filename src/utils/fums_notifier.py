# src/utils/fums_notifier.py
"""FUMS Notification Dispatcher & Admin Escalation Engine.

Dispatches update proposals, approval prompts, operational reports,
and P1 rollback alerts to client and admin channels (Signal & Matrix).
Conforms to FUMS Spec sections 4.4 and 5.
"""

import logging
import os
from typing import Any, Dict, Optional

import requests  # type: ignore

from utils.security_utils import validate_and_sanitize_url

logger = logging.getLogger(__name__)


class FUMSNotifier:
    """Dispatches notifications and alerts for the Fleet Update Management System."""

    def __init__(
        self,
        signal_api: Optional[str] = None,
        signal_sender: Optional[str] = None,
        matrix_homeserver: Optional[str] = None,
        matrix_token: Optional[str] = None,
        admin_signal_recipient: Optional[str] = None,
    ) -> None:
        self.signal_api = signal_api or os.getenv("SIGNAL_API")
        self.signal_sender = signal_sender or os.getenv("SIGNAL_SENDER")
        self.matrix_homeserver = matrix_homeserver or os.getenv("MATRIX_HOMESERVER")
        self.matrix_token = matrix_token or os.getenv("MATRIX_TOKEN")
        self.admin_signal_recipient = admin_signal_recipient or os.getenv(
            "ADMIN_SIGNAL_RECIPIENT"
        )

    def send_signal(
        self,
        message: str,
        recipient: str,
    ) -> bool:
        """Sends a notification via Signal REST API."""
        if not (self.signal_api and self.signal_sender and recipient):
            logger.debug(
                "Signal notification skipped: API or recipient not configured."
            )
            return False

        is_valid, safe_url, _ = validate_and_sanitize_url(self.signal_api)
        if not is_valid or not safe_url:
            logger.error("Signal API URL failed security validation.")
            return False

        payload = {
            "message": message,
            "number": self.signal_sender,
            "recipients": [recipient],
        }
        # noinspection PyBroadException
        try:
            res = requests.post(safe_url, json=payload, timeout=15)
            if res.status_code in (200, 201):
                logger.info(f"Signal notification sent to {recipient}")
                return True
            logger.warning(f"Signal API returned status code {res.status_code}")
        except Exception as exc:
            logger.error(f"Failed to send Signal message: {exc}")
        return False

    def send_matrix(
        self,
        room_id: str,
        message: str,
    ) -> bool:
        """Sends a message to a Matrix room via Client-Server API."""
        if not (self.matrix_homeserver and self.matrix_token and room_id):
            logger.debug(
                "Matrix notification skipped: Homeserver, token or room_id missing."
            )
            return False

        clean_hs = self.matrix_homeserver.rstrip("/")
        url = f"{clean_hs}/_matrix/client/v3/rooms/{room_id}/send/m.room.message"
        is_valid, safe_url, _ = validate_and_sanitize_url(url)
        if not is_valid or not safe_url:
            logger.error("Matrix API URL failed security validation.")
            return False

        headers = {
            "Authorization": f"Bearer {self.matrix_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "msgtype": "m.text",
            "body": message,
        }
        # noinspection PyBroadException
        try:
            res = requests.post(safe_url, json=payload, headers=headers, timeout=15)
            if res.status_code in (200, 201):
                logger.info(f"Matrix message sent to room {room_id}")
                return True
            logger.warning(f"Matrix API returned status code {res.status_code}")
        except Exception as exc:
            logger.error(f"Failed to send Matrix message: {exc}")
        return False

    def format_client_proposal(
        self,
        component_name: str,
        old_version: str,
        new_version: str,
        risk_info: Dict[str, Any],
        approval_token: str,
        base_portal_url: str = "https://hub.njorddeploy.com",
    ) -> str:
        """Formats structured proposal menu for the customer per FUMS Spec."""
        gatekeeper_status = (
            "GECERTIFICEERD (100% geslaagd in Proxmox sandbox)"
            if risk_info.get("gatekeeper_certified")
            else "N.v.t. (Routine patch)"
        )
        risk_level = risk_info.get("risk_level", "GREEN")
        reasons = "; ".join(risk_info.get("reasons", []))

        text = (
            f"📦 [NjordDeploy Update Advies]\n"
            f"Component: {component_name} {old_version} -> {new_version}\n"
            f"🧪 Gatekeeper Status: {gatekeeper_status}\n"
            f"AI Risico-Analyse: {risk_level} ({reasons})\n\n"
            f"Kies uw vervolgstap:\n"
            f"[ 1 ] Direct naar productie uitrollen\n"
            f"[ 2 ] Productie-uitrol plannen voor komende nacht om 02:00\n"
            f"[ 3 ] Specifieke datum & tijd voor productie: [ JJJJ-MM-DD UU:MM ]\n"
            f"[ 4 ] Start Trainings-Sandbox (14 dagen toegang voor medewerkers & UAT)\n"
            f"[ 5 ] Uitstellen (herinner mij over 14 dagen)\n\n"
            f"Kies veiligheidsniveau voor productie:\n"
            f"(A) High-Safety: Atomaire DB-dump + Snapshot + Auto-rollback\n"
            f"(B) Fast Rolling: Directe container herstart\n\n"
            f'Reageer: "UPDATE 4" (voor training) of "UPDATE 2 A" (voor nacht)\n'
            f"Of beheer via: {base_portal_url}/approve?token={approval_token}"
        )
        return text

    def escalate_p1_admin(
        self,
        component_name: str,
        target_host: str,
        error_reason: str,
        rollback_performed: bool = True,
    ) -> bool:
        """Sends a high-priority P1 alert to the platform administrator (Henk).

        Triggered immediately whenever a production health check fails and
        a rollback occurs.
        """
        if not self.admin_signal_recipient:
            logger.warning("Admin Signal recipient not configured; escalation dropped.")
            return False

        rb_status = (
            "HERSTELD (Atomaire DB restore & image revert geslaagd)"
            if rollback_performed
            else "LET OP: ROLLBACK NIET BEVESTIGD!"
        )
        alert_msg = (
            f"🚨 [NJORDDEPLOY P1 ESCALATIE]\n"
            f"Doelhost: {target_host}\n"
            f"Component: {component_name}\n"
            f"Status: UPDATE GEFAALD\n"
            f"Rollback Status: {rb_status}\n"
            f"Foutdetails: {error_reason}\n"
            f"Actie vereist: Inspecteer recept en logs op VM 140."
        )
        return self.send_signal(alert_msg, self.admin_signal_recipient)
