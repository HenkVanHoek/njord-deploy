# src/managers/fleet_update_manager.py
"""Fleet Update Management System (FUMS) Manager.

Orchestrates update discovery, token-efficient RISA analysis, pre-flight safety checks,
atomic update execution via Ansible, rollback verification, and notifications.
Conforms to FUMS Spec (Step 1).
"""

import logging
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from managers.customer_sandbox_manager import CustomerSandboxManager
from managers.gatekeeper_manager import GatekeeperManager
from utils.fums_notifier import FUMSNotifier
from utils.resource_utils import resource_path
from utils.risa_prefilter import (
    classify_update_risk,
    extract_signal_lines,
    filter_changelog_for_risa,
)

logger = logging.getLogger(__name__)


class FleetUpdateManager:
    """Core coordinator for FUMS update detection, staging and execution."""

    def __init__(
        self,
        component_manager: Any = None,
        notifier: Optional[FUMSNotifier] = None,
        gatekeeper_manager: Optional[GatekeeperManager] = None,
        sandbox_manager: Optional[CustomerSandboxManager] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        self.component_manager = component_manager
        self.notifier = notifier or FUMSNotifier()
        self.gatekeeper_manager = gatekeeper_manager or GatekeeperManager(
            notifier=self.notifier
        )
        self.sandbox_manager = sandbox_manager or CustomerSandboxManager(
            notifier=self.notifier,
            db_path=db_path,
        )
        self.db_path = db_path

    def analyze_release(
        self,
        component_id: str,
        old_version: str,
        new_version: str,
        raw_changelog: str = "",
        compose_diff: str = "",
        has_db_migration: bool = False,
    ) -> Dict[str, Any]:
        """Analyzes an upstream release using RISA Token Filtering rules."""
        # 1. Filter changelog to prevent token explosion
        filtered_notes = filter_changelog_for_risa(raw_changelog)
        signals = extract_signal_lines(raw_changelog)

        if "MIGRATION" in compose_diff.upper() or "DATABASE" in compose_diff.upper():
            has_db_migration = True

        # 2. Risk Classification
        risk_evaluation = classify_update_risk(
            old_version=old_version,
            new_version=new_version,
            signal_lines=signals,
            has_db_migration=has_db_migration,
            has_compose_diff=bool(compose_diff.strip()),
        )

        approval_token = secrets.token_urlsafe(24)

        return {
            "component_id": component_id,
            "old_version": old_version,
            "new_version": new_version,
            "risk_evaluation": risk_evaluation,
            "filtered_changelog": filtered_notes,
            "approval_token": approval_token,
            "status": "pending_approval",
            "created_at": datetime.now().isoformat(),
        }

    def verify_gatekeeper(
        self,
        analysis: Dict[str, Any],
        service_port: Optional[int] = None,
        executor_func: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Runs Gatekeeper verification (Mode A) if release requires it (RED).

        Updates analysis dictionary in-place with certification or quarantine status.
        """
        risk_info = analysis.get("risk_evaluation", {})
        if not risk_info.get("requires_gatekeeper"):
            logger.info("Release does not require Gatekeeper testing (Green/Orange).")
            return analysis

        component_id = analysis.get("component_id", "")
        old_v = analysis.get("old_version", "")
        new_v = analysis.get("new_version", "")

        gk_result = self.gatekeeper_manager.run_gatekeeper_verification(
            component_id=component_id,
            old_version=old_v,
            new_version=new_v,
            service_port=service_port,
            executor_func=executor_func,
        )

        if gk_result.get("certified"):
            analysis["risk_evaluation"]["gatekeeper_certified"] = True
            analysis["status"] = "gatekeeper_certified"
        else:
            analysis["risk_evaluation"]["gatekeeper_certified"] = False
            analysis["status"] = "quarantined"
            analysis["quarantine_error"] = gk_result.get("error", "")

        return analysis

    def notify_client_proposal(
        self,
        analysis: Dict[str, Any],
        client_contact: str,
        channel: str = "signal",
    ) -> bool:
        """Sends customer notification proposal with choice options."""
        component_id = analysis.get("component_id", "Unknown")
        old_v = analysis.get("old_version", "")
        new_v = analysis.get("new_version", "")
        risk_info = analysis.get("risk_evaluation", {})
        token = analysis.get("approval_token", "")

        msg = self.notifier.format_client_proposal(
            component_name=component_id,
            old_version=old_v,
            new_version=new_v,
            risk_info=risk_info,
            approval_token=token,
        )

        if channel == "signal":
            return self.notifier.send_signal(msg, client_contact)
        elif channel == "matrix":
            return self.notifier.send_matrix(client_contact, msg)
        return False

    def handle_client_response(
        self,
        analysis: Dict[str, Any],
        client_response_text: str,
        client_id: str,
    ) -> Dict[str, Any]:
        """Parses and acts upon customer reply (e.g. UPDATE 4 for sandbox,
        UPDATE 1 for prod).

        Conforms to FUMS Spec section 5 (Klant Keuzemenu).
        """
        clean_resp = client_response_text.strip().upper()
        component_id = analysis.get("component_id", "")
        target_version = analysis.get("new_version", "")

        # Keuze 4: Start Trainings-Sandbox (Modus B)
        if "4" in clean_resp or "TRAINING" in clean_resp or "SANDBOX" in clean_resp:
            logger.info(
                f"Customer {client_id} requested training sandbox for "
                f"{component_id} {target_version}"
            )
            sandbox_res = self.sandbox_manager.request_sandbox(
                client_id=client_id,
                component_id=component_id,
                target_version=target_version,
            )
            return {
                "action": "training_sandbox_requested",
                "client_id": client_id,
                "sandbox": sandbox_res,
            }

        # Keuze 1: Direct naar productie
        if re.search(r"\b1\b", clean_resp):
            is_fast = bool(re.search(r"\bB\b", clean_resp))
            safety = "fast_rolling" if is_fast else "high_safety"
            return {
                "action": "production_update_immediate",
                "client_id": client_id,
                "safety_level": safety,
                "component_id": component_id,
                "target_version": target_version,
            }

        # Keuze 2: Nachtelijke uitrol (02:00)
        if re.search(r"\b2\b", clean_resp):
            is_fast = bool(re.search(r"\bB\b", clean_resp))
            safety = "fast_rolling" if is_fast else "high_safety"
            return {
                "action": "production_update_scheduled_night",
                "client_id": client_id,
                "schedule": "02:00",
                "safety_level": safety,
                "component_id": component_id,
                "target_version": target_version,
            }

        # Keuze 5: Uitstellen (14 dagen)
        if "5" in clean_resp or "SNOOZE" in clean_resp:
            return {
                "action": "postponed",
                "client_id": client_id,
                "snooze_days": 14,
            }

        return {
            "action": "unrecognized_option",
            "raw_input": client_response_text,
        }

    def build_ansible_update_args(
        self,
        component_id: str,
        target_host: str,
        new_tag: str,
        old_tag: Optional[str] = None,
        safety_level: str = "high_safety",
        service_port: Optional[int] = None,
        estimated_footprint_mb: int = 1500,
    ) -> Dict[str, Any]:
        """Constructs parameters and extra_vars for ansible/update_playbook.yml."""
        playbook = str(resource_path("ansible/update_playbook.yml"))
        extra_vars = {
            "component_id": component_id,
            "new_tag": new_tag,
            "old_tag": old_tag or "",
            "update_safety": safety_level,
            "service_port": str(service_port) if service_port else "",
            "estimated_footprint_mb": estimated_footprint_mb,
        }
        return {
            "playbook": playbook,
            "inventory": f"{target_host},",
            "extravars": extra_vars,
        }

    def handle_execution_result(
        self,
        component_id: str,
        target_host: str,
        success: bool,
        error_output: str = "",
    ) -> Dict[str, Any]:
        """Handles post-execution telemetry, notifying admin upon rollback."""
        if success:
            logger.info(f"FUMS update succeeded for {component_id} on {target_host}")
            return {
                "status": "success",
                "component_id": component_id,
                "target_host": target_host,
            }

        logger.warning(
            f"FUMS update failed on {target_host} for {component_id}: {error_output}"
        )
        rollback_detected = "FUMS_ROLLBACK_EXECUTED" in error_output

        # Escalate P1 alarm to Henk per FUMS Spec section 4.4
        self.notifier.escalate_p1_admin(
            component_name=component_id,
            target_host=target_host,
            error_reason=error_output,
            rollback_performed=rollback_detected,
        )

        return {
            "status": "failed",
            "rollback_executed": rollback_detected,
            "component_id": component_id,
            "target_host": target_host,
            "error": error_output,
        }
