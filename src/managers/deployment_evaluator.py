# src/managers/deployment_evaluator.py

import json
import logging
import re
from typing import Any, Dict, Optional

from utils.ai_generator_engine import AIGeneratorEngine

logger = logging.getLogger(__name__)

# Patterns for scrubbing sensitive credentials from logs
SENSITIVE_PATTERNS = [
    (
        r"(?i)(PASSWORD|SECRET|TOKEN|AUTH|PASS|KEY|PRIVATE_KEY)=([^\s\n]+)",
        r"\1=***MASKED***",
    ),
    (
        r"(?i)(Bearer\s+)[A-Za-z0-9\-\_\.\=]+",
        r"\1***MASKED***",
    ),
    (
        r"(://[^:]+:)[^@]+(@)",
        r"\1***MASKED***\2",
    ),
]


def sanitize_logs(log_text: str) -> str:
    """Removes sensitive passwords, tokens, and private credentials from log output."""
    sanitized = log_text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


class DeploymentEvaluator:
    """Evaluates deployment execution logs and statuses into
    human-actionable reports.
    """

    def evaluate_with_rules(
        self,
        component_name: str,
        log_text: str,
        exit_code: int,
        container_status: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Deterministic rule-based log analysis when AI is offline or disabled."""
        sanitized = sanitize_logs(log_text)
        is_running = container_status.get("running", True)

        if exit_code == 0 and is_running and "error" not in sanitized.lower():
            return {
                "status": "GREEN",
                "summary": (
                    f"Component '{component_name}' was deployed successfully and "
                    "all health checks passed."
                ),
                "user_action": "",
                "doc_anchor": "",
                "github_keywords": "",
            }

        # Check for user cancellation or process abort
        if (
            exit_code in (130, -15, -9, 143)
            or "abort" in sanitized.lower()
            or "interrupted" in sanitized.lower()
            or "sigterm" in sanitized.lower()
            or "sigkill" in sanitized.lower()
            or "keyboardinterrupt" in sanitized.lower()
            or "cancelled" in sanitized.lower()
            or "canceled" in sanitized.lower()
        ):
            return {
                "status": "YELLOW",
                "summary": (
                    f"Deployment of '{component_name}' was cancelled by the user."
                ),
                "user_action": (
                    "The deployment process was intentionally stopped. "
                    "No error report is needed."
                ),
                "doc_anchor": "",
                "github_keywords": "",
            }

        # Rule checks for Scenario 2 (Yellow - User/Config Tuning)
        if "bind: address already in use" in sanitized:
            return {
                "status": "YELLOW",
                "summary": (
                    f"Port conflict detected for component '{component_name}'. "
                    "A required network port is already in use by another service."
                ),
                "user_action": (
                    "Change the conflicting port parameter in the service "
                    "configuration or stop the existing service on the node."
                ),
                "doc_anchor": "USER_GUIDE.md#port-conflicts",
                "github_keywords": "",
            }

        if "permission denied" in sanitized.lower():
            return {
                "status": "YELLOW",
                "summary": (
                    f"Permission denied error during deployment of '{component_name}'."
                ),
                "user_action": (
                    "Verify file storage permissions and path mappings on the node."
                ),
                "doc_anchor": "USER_GUIDE.md#storage-permissions",
                "github_keywords": "",
            }

        if "no space left on device" in sanitized.lower():
            return {
                "status": "YELLOW",
                "summary": "Node storage is full.",
                "user_action": "Free up disk space on the target node before retrying.",
                "doc_anchor": "USER_GUIDE.md#disk-space",
                "github_keywords": "",
            }

        if (
            "/dev/net/tun" in sanitized.lower()
            or "not a device node" in sanitized.lower()
        ):
            return {
                "status": "YELLOW",
                "summary": (
                    f"Kernel device access error for '{component_name}'. "
                    "The service requires host device access (/dev/net/tun) "
                    "not available in standard unprivileged LXC containers."
                ),
                "user_action": (
                    "Deploy this component on a full Virtual Machine (VM) or "
                    "configure device passthrough on your Proxmox host."
                ),
                "doc_anchor": "USER_GUIDE.md#lxc-tun-devices",
                "github_keywords": "lxc dev net tun",
            }

        # Rule checks for Scenario 3 (Red - System/Package Bug)
        if (
            "jinja2.exceptions" in sanitized
            or "syntax error" in sanitized.lower()
            or "undefinederror" in sanitized.lower()
        ):
            # Extract error keyword safely using unpacking mandate
            lines = [line for line in sanitized.splitlines() if "Error" in line]
            err_line = next(iter(lines), "template execution error")
            return {
                "status": "RED",
                "summary": (
                    f"Fatal template rendering error in component '{component_name}'."
                ),
                "user_action": (
                    "Report this issue on GitHub so developers can update "
                    "the service template."
                ),
                "doc_anchor": "",
                "github_keywords": f"{component_name} {err_line}",
            }

        # Default fallback for unknown non-zero exit
        return {
            "status": "RED" if exit_code != 0 else "YELLOW",
            "summary": f"Deployment of '{component_name}' finished with errors.",
            "user_action": "Inspect the container logs for details.",
            "doc_anchor": "",
            "github_keywords": f"{component_name} deployment failure",
        }

    def evaluate_with_ai(
        self,
        component_name: str,
        log_text: str,
        exit_code: int,
        container_status: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluates deployment logs using the configured AI provider engine."""
        sanitized_logs = sanitize_logs(log_text)

        system_prompt = (
            "You are an expert DevOps AI assistant for NjordDeploy. "
            "Analyze the deployment execution log and status of a self-hosted service. "
            "Categorize the result into one of 3 statuses:\n"
            "- GREEN: Service deployed cleanly, zero errors.\n"
            "- YELLOW: Configuration/parameter tuning issue fixable by user "
            "(e.g., port conflict, invalid env var, missing permissions).\n"
            "- RED: Fatal software bug in NjordDeploy or docker template.\n\n"
            "Return strictly JSON with keys: "
            '{"status": "GREEN|YELLOW|RED", "summary": "...", "user_action": "...", '
            '"doc_anchor": "...", "github_keywords": "..."}'
        )

        user_prompt = (
            f"Component: {component_name}\n"
            f"Exit Code: {exit_code}\n"
            f"Container Status: {container_status}\n"
            f"Sanitized Logs (last 100 lines):\n{sanitized_logs[-3000:]}"
        )

        engine = AIGeneratorEngine()
        raw_response = engine.generate(
            prompt=user_prompt,
            system_context=system_prompt,
        )

        # Clean potential markdown formatting ```json ... ```
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # Enforce Unpacking-First Mandate for slicing list
            if len(lines) >= 2:
                # Omit first and last line if fenced codeblock
                cleaned = "\n".join(lines[1:-1])

        parsed_data = json.loads(cleaned)
        return {
            "status": str(parsed_data.get("status", "YELLOW")).upper(),
            "summary": str(parsed_data.get("summary", "")),
            "user_action": str(parsed_data.get("user_action", "")),
            "doc_anchor": str(parsed_data.get("doc_anchor", "")),
            "github_keywords": str(parsed_data.get("github_keywords", "")),
        }


def evaluate_deployment(
    component_name: str,
    log_text: str,
    exit_code: int = 0,
    container_status: Optional[Dict[str, Any]] = None,
    use_ai: bool = True,
) -> Dict[str, Any]:
    """Main entry point for evaluating a deployment session result."""
    status_dict = container_status or {"running": exit_code == 0}
    evaluator = DeploymentEvaluator()

    sanitized_check = log_text.lower()
    if (
        exit_code in (130, -15, -9, 143)
        or "aborted by user" in sanitized_check
        or "abort requested" in sanitized_check
        or "keyboardinterrupt" in sanitized_check
        or "interrupted" in sanitized_check
    ):
        return evaluator.evaluate_with_rules(
            component_name=component_name,
            log_text=log_text,
            exit_code=exit_code,
            container_status=status_dict,
        )

    if use_ai:
        # noinspection PyBroadException
        try:
            return evaluator.evaluate_with_ai(
                component_name=component_name,
                log_text=log_text,
                exit_code=exit_code,
                container_status=status_dict,
            )
        except Exception as err:
            logger.warning(
                f"AI evaluation failed or unavailable: {err}. "
                "Falling back to rule-based evaluation."
            )

    return evaluator.evaluate_with_rules(
        component_name=component_name,
        log_text=log_text,
        exit_code=exit_code,
        container_status=status_dict,
    )
