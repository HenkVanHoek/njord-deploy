"""AI Failure Diagnoser for NjordDeploy Proxmox Component Tests.

Provides single-component and batch systemic failure diagnosis, root-cause
analysis, and patch generation for Docker/Podman container test runs using
Gemini or configured AI providers. Differentiates between Template Configuration
issues, Core Platform Code bugs, and Matrix Incompatibilities (LXC vs VM,
Docker vs Podman).
"""

import difflib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.ai_generator_engine import AIGeneratorEngine
from utils.ai_provider_manager import load_ai_providers_registry

logger = logging.getLogger(__name__)


class AIFailureDiagnoser:
    """Diagnoses test failures using configured AI providers (Gemini/OpenAI/Ollama)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        resolved_provider = provider or os.getenv("AI_PROVIDER")
        if not resolved_provider:
            if os.getenv("GEMINI_API_KEY"):
                resolved_provider = "gemini"
            elif os.getenv("OPENAI_API_KEY"):
                resolved_provider = "openai"
            elif os.getenv("HOSTYOURAI_API_KEY"):
                resolved_provider = "hostyourai"
            else:
                resolved_provider = "ollama"

        self.provider = resolved_provider
        self.engine = AIGeneratorEngine(
            provider=self.provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )

    def is_configured(self) -> bool:
        """Returns True if the active AI provider is properly configured."""
        if self.provider == "ollama":
            return True
        registry = load_ai_providers_registry()
        pdef = registry.get(self.provider, {})
        env_var = pdef.get("env_var")
        if env_var and os.getenv(env_var):
            return True
        if self.engine.api_key:
            return True
        return False

    @staticmethod
    def _get_core_platform_context() -> str:
        """Returns summary of NjordDeploy core architecture and execution pipeline."""
        return (
            "NJORDDEPLOY CORE PLATFORM ARCHITECTURE:\n"
            "- Single Source of Truth: 'config/components_metadata.json' defines "
            "all service metadata, ports, volumes, and supported_matrix "
            "(modes/engines).\n"
            "- Deployment Pipeline: 'src/managers/deployment_manager.py' renders "
            "'component_templates/<id>/docker-compose.template.yml' with Jinja2, "
            "generates '.env' files, uploads files via SSH to target host at "
            "'/opt/njorddeploy/<id>/', and executes 'docker compose up -d' or "
            "'podman compose up -d'.\n"
            "- Host Provisioning: 'src/managers/setup_manager.py' and "
            "'ansible/playbook.yml' configure Debian target hosts, install "
            "Docker/Podman, and set up system permissions and users.\n"
            "- Test Runner: 'scripts/proxmox_test_runner.py' provisions fresh LXC "
            "containers or QEMU VMs on Proxmox VE, invokes the deployment engine, "
            "and probes HTTP endpoints to verify service health.\n"
        )

    @staticmethod
    def extract_component_matrix_status(
        component_id: str,
        history_records: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Calculates pass/fail status across LXC/VM and Docker/Podman matrix."""
        matrix = {
            "LXC/DOCKER": "UNTESTED",
            "VM/DOCKER": "UNTESTED",
            "LXC/PODMAN": "UNTESTED",
            "VM/PODMAN": "UNTESTED",
        }
        for r in history_records:
            if r.get("component_id") == component_id:
                mode = (r.get("mode") or "").upper()
                engine = (r.get("engine") or "").upper()
                key = f"{mode}/{engine}"
                if key in matrix:
                    matrix[key] = "PASSED" if r.get("status") == "success" else "FAILED"
        return matrix

    @staticmethod
    def _get_domain_failure_hints(
        error_msg: str,
        container_logs: str = "",
        mode: str = "LXC",
        engine: str = "DOCKER",
    ) -> str:
        """Extracts specialized container/Linux domain hints to guide AI diagnosis."""
        hints = []
        combined_text = f"{error_msg}\n{container_logs}".lower()

        # 1. SSH / Transient VM network connectivity
        if (
            "unable to connect to port 22" in combined_text
            or "no route to host" in combined_text
            or "connection refused" in combined_text
            or "cannot connect to target host" in combined_text
        ):
            hints.append(
                "INFRASTRUCTURE NOTE: This failure is caused by an SSH / network "
                "connectivity timeout to the Proxmox VM/LXC node (ENVIRONMENT_INFRA). "
                "Do NOT suggest modifying the service docker-compose.template.yml "
                "file for SSH connection drops."
            )

        # 2. Debian podman-compose Python traceback or network_mode host conflict
        if (
            "cannot set multiple networks without bridge network mode" in combined_text
            or (
                "network_mode: host" in combined_text
                and "exit code: 125" in combined_text
            )
            or ("exit code: 125" in combined_text and "podman-compose" in combined_text)
        ):
            hints.append(
                "PODMAN NETWORK_MODE HOST CONFLICT: 'podman-compose' automatically "
                "attempts to attach the project bridge network to containers even "
                "when 'network_mode: host' is specified, causing Podman to reject "
                "container creation with exit code 125. To fix this while keeping "
                "host discovery for Docker, recommend using a Jinja2 conditional: "
                '\'{%- if CONTAINER_ENGINE == "podman" %} '
                'ports: ["<PORT>:<PORT>"] networks: [njorddeploy_net] '
                "{%- else %} network_mode: host {%- endif %}'."
            )
        elif "podman-compose" in combined_text and (
            "traceback" in combined_text or "runtimeerror" in combined_text
        ):
            hints.append(
                "PODMAN ENGINE NOTE: Debian's packaged /usr/bin/podman-compose "
                "encountered a Python parser/runtime error. Known triggers include "
                "nested networks with external=true, certain healthcheck schemas, "
                "or YAML anchor syntax unsupported by podman-compose v1.0.x."
            )

        # 3. Traefik port 8080 double binding conflict
        if "traefik" in combined_text and (
            "address already in use" in combined_text
            or ("api.insecure" in combined_text and "8080" in combined_text)
        ):
            hints.append(
                "TRAEFIK PORT 8080 CONFLICT: '--api.insecure=true' internally "
                "creates an entrypoint listening on port 8080. If "
                "'--entrypoints.dashboard.address=:8080' is also defined, "
                "Traefik will crash on startup with 'bind: address already in use'. "
                "Remove '--api.insecure=true'."
            )

        # 4. Missing image / local build
        if (
            "image not known" in combined_text
            or "dockerfile:" in combined_text
            or "failed to resolve source metadata" in combined_text
        ):
            hints.append(
                "IMAGE REGISTRY NOTE: The image specified in the template could "
                "not be pulled from public registries (Docker Hub/GHCR) or requires "
                "local build context not present on target."
            )

        # 5. Rootless UID / GID namespace restriction in LXC or Podman
        if (
            "usermod: uid" in combined_text
            or "operation not permitted" in combined_text
            or "permission denied" in combined_text
        ):
            hints.append(
                "PERMISSIONS & NAMESPACE NOTE: Under rootless Podman or "
                "unprivileged LXC, entrypoint scripts that attempt to run "
                "'usermod -u 0' or change root ownership of volume mounts "
                "fail due to user namespace mapping. If this service "
                "fundamentally requires root, consider classifying as "
                "MATRIX_CONSTRAINT (Docker-only or VM-only)."
            )

        # 6. Docker daemon socket requirement in Podman
        if "docker.sock" in combined_text and (
            "podman" in combined_text or engine.upper() == "PODMAN"
        ):
            hints.append(
                "DOCKER SOCKET REQUIREMENT: The service depends on "
                "'/var/run/docker.sock' to discover or manage container "
                "instances. Podman does not provide this socket by default. "
                "Classify as MATRIX_CONSTRAINT (engines: ['docker']) if Docker "
                "engine is fundamentally required."
            )

        # 7. Device passthrough / Kernel modules in LXC
        if (
            "/dev/net/tun" in combined_text
            or "not a device node" in combined_text
            or "no such file or directory: /dev/tty" in combined_text
        ):
            hints.append(
                "KERNEL & DEVICE NOTE: The service requires host kernel devices "
                "(e.g. /dev/net/tun or USB) not passed through into unprivileged "
                "LXC containers. Recommend MATRIX_CONSTRAINT (VM-only)."
            )

        # 8. HTTP probe failure
        if "http probe:" in combined_text or "httpconnectionpool" in combined_text:
            hints.append(
                "HTTP PROBE NOTE: The container was running, but the HTTP "
                "health check failed. Check if the service uses a specific "
                "webroot subpath, if multi-container dependent services need "
                "longer startup time, or if port variables match exposed ports."
            )

        return "\n".join(hints) if hints else ""

    def diagnose_single_failure(
        self,
        test_record: Dict[str, Any],
        template_content: str = "",
        container_logs: str = "",
        history_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Performs a deep-dive diagnosis of a single failed component test.

        Classifies failure into TEMPLATE_CONFIG, CORE_PLATFORM_CODE,
        ENVIRONMENT_INFRA, or MATRIX_CONSTRAINT, and produces actionable
        patches, matrix recommendations, or developer plans.
        """
        comp_id = test_record.get("component_id", "unknown")
        mode = test_record.get("mode", "LXC")
        engine_type = test_record.get("engine", "DOCKER")
        deployment_status = test_record.get("deployment", "unknown")
        running_status = test_record.get("running", False)
        http_ok = test_record.get("http_ok")
        error_msg = test_record.get("error_message", "")

        matrix_status = (
            self.extract_component_matrix_status(comp_id, history_records)
            if history_records
            else {}
        )

        platform_context = self._get_core_platform_context()
        domain_hints = self._get_domain_failure_hints(
            error_msg=error_msg,
            container_logs=container_logs,
            mode=mode,
            engine=engine_type,
        )

        hints_section = (
            f"\nSPECIALIZED DOMAIN HINTS:\n{domain_hints}\n" if domain_hints else ""
        )
        matrix_section = (
            f"\nCROSS-ENVIRONMENT TEST MATRIX STATUS FOR THIS COMPONENT:\n"
            f"{json.dumps(matrix_status, indent=2)}\n"
            if matrix_status
            else ""
        )

        system_prompt = (
            "You are a Principal DevOps and Container Architect specializing in "
            "Debian Linux, Docker Compose v2, Rootless Podman 4+, Linux permissions, "
            "Ansible automation, Python Flask backend engines, and Proxmox VE.\n\n"
            f"{platform_context}\n"
            f"{hints_section}\n"
            f"{matrix_section}\n"
            "CRITICAL CROSS-MATRIX COMPATIBILITY MANDATE:\n"
            "Any proposed template or code fix MUST maintain 100% compatibility "
            "across all 4 matrix permutations (LXC/Docker, VM/Docker, "
            "LXC/Podman, and VM/Podman).\n"
            "If a component already passes in Docker but fails in Podman (or passes "
            "in VM but fails in LXC), your fix MUST NOT break working environments.\n"
            "NjordDeploy supports native Jinja2 conditionals in "
            "docker-compose.template.yml using 'CONTAINER_ENGINE' "
            "('docker'/'podman') and 'TARGET_MODE' ('lxc'/'vm'). "
            "Use Jinja2 conditionals when a service needs different networking "
            "or volume mappings between Docker and Podman (e.g. "
            '\'{%- if CONTAINER_ENGINE == "podman" %} ports: ... '
            "{%- else %} network_mode: host {%- endif %}').\n\n"
            "CLASSIFY THE ROOT CAUSE TARGET:\n"
            "1. 'TEMPLATE_CONFIG': Service compose configuration "
            "(docker-compose.template.yml).\n"
            "2. 'CORE_PLATFORM_CODE': NjordDeploy Python code / Ansible playbooks.\n"
            "3. 'ENVIRONMENT_INFRA': Proxmox VE hypervisor / SSH drops / disk full.\n"
            "4. 'MATRIX_CONSTRAINT': The service fundamentally cannot run on this "
            "specific mode (e.g. requires raw VM kernel module / hardware passthrough "
            "not supported in unprivileged LXC) or engine (e.g. requires Docker root "
            "daemon socket not available in rootless Podman). Recommend restricting "
            "supported_matrix in metadata.\n\n"
            "OUTPUT FORMAT (STRICT JSON):\n"
            "{\n"
            '  "component_id": "<id>",\n'
            '  "target_type": "<TEMPLATE_CONFIG | CORE_PLATFORM_CODE | '
            'ENVIRONMENT_INFRA | MATRIX_CONSTRAINT>",\n'
            '  "target_file": "<relative file path e.g. '
            "component_templates/<id>/docker-compose.template.yml, "
            "src/managers/deployment_manager.py, or "
            'config/components_metadata.json>",\n'
            '  "summary": "<1-2 sentence concise summary of failure cause>",\n'
            '  "root_cause_analysis": "<detailed technical explanation>",\n'
            '  "fix_description": "<clear description of necessary fix>",\n'
            '  "category": "<Configuration | Permissions | Network | Timing | '
            'Backend Logic | Matrix Incompatibility>",\n'
            '  "suggested_template": "<full updated template string if '
            'target_type == TEMPLATE_CONFIG, else null>",\n'
            '  "suggested_code_patch": "<exact code diff/snippet for Python or '
            'Ansible if target_type == CORE_PLATFORM_CODE, else null>",\n'
            '  "suggested_matrix": {\n'
            '    "modes": ["vm"],\n'
            '    "engines": ["docker"]\n'
            "  },\n"
            '  "matrix_notes": "<reason why certain modes or engines are '
            'unsupported>",\n'
            '  "action_plan": "<step-by-step instructions for developer in '
            'IDE/PyCharm>",\n'
            '  "cross_matrix_notes": "<verification of compatibility across '
            'Docker, Podman, LXC, and VM>",\n'
            '  "patch_notes": "<specific advice for environment if applicable>"\n'
            "}"
        )

        user_content = {
            "component_id": comp_id,
            "failed_test_target": f"{mode}/{engine_type}",
            "cross_environment_matrix_status": matrix_status,
            "deployment_status": deployment_status,
            "containers_running": running_status,
            "http_probe_status": http_ok,
            "error_details": error_msg,
            "container_logs_snippet": container_logs[:4000] if container_logs else "",
            "active_template_content": template_content,
        }

        user_prompt = (
            f"Please diagnose the following test failure:\n\n"
            f"```json\n{json.dumps(user_content, indent=2)}\n```"
        )

        raw_resp = self.engine.generate(
            prompt=user_prompt,
            system_context=system_prompt,
            response_format={"type": "json_object"},
        )

        result = json.loads(raw_resp)

        # Default fallback for target_type if missing
        if "target_type" not in result:
            result["target_type"] = "TEMPLATE_CONFIG"

        # Compute unified diff if suggested template is provided
        suggested_tpl = result.get("suggested_template")
        if (
            suggested_tpl
            and template_content
            and result.get("target_type") == "TEMPLATE_CONFIG"
        ):
            diff_lines = list(
                difflib.unified_diff(
                    template_content.splitlines(keepends=True),
                    suggested_tpl.splitlines(keepends=True),
                    fromfile=f"a/{comp_id}/docker-compose.template.yml",
                    tofile=f"b/{comp_id}/docker-compose.template.yml",
                )
            )
            result["diff"] = "".join(diff_lines)
        else:
            result["diff"] = ""

        return result

    def diagnose_batch_failures(
        self,
        failed_records: List[Dict[str, Any]],
        templates_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Performs a systemic cross-failure diagnosis across multiple failed tests.

        Identifies systemic patterns, clusters errors by common root cause,
        analyzes cross-environment differences (Docker vs Podman, LXC vs VM),
        and distinguishes between template fixes, platform issues, and matrix
        constraints.
        """
        if not failed_records:
            return {
                "total_analyzed": 0,
                "systemic_summary": "No failed test records provided.",
                "clusters": [],
                "recommendations": [],
            }

        templates_map = templates_map or {}
        condensed_failures = []
        for r in failed_records:
            cid = r.get("component_id", "unknown")
            err = r.get("error_message", "")
            first_err_line = next(iter(err.strip().splitlines()), "Unknown error")
            condensed_failures.append(
                {
                    "component_id": cid,
                    "mode": r.get("mode"),
                    "engine": r.get("engine"),
                    "deployment": r.get("deployment"),
                    "running": r.get("running"),
                    "http_ok": r.get("http_ok"),
                    "error_summary": first_err_line[:200],
                    "error_details": err[:500],
                }
            )

        platform_context = self._get_core_platform_context()

        system_prompt = (
            "You are a Distinguished Infrastructure and System Architect "
            "analyzing a batch of automated component test failures on "
            "Proxmox VE.\n\n"
            f"{platform_context}\n"
            "Your goal is SYSTEMIC PATTERN RECOGNITION across heterogeneous "
            "environments (Docker vs Podman, LXC vs VM). Group failures into "
            "root causes.\n"
            "CRITICAL: Note when a failure is a structural MATRIX_CONSTRAINT "
            "(e.g. /dev/net/tun in LXC or Docker daemon socket in Podman) "
            "versus a fixable TEMPLATE_CONFIG issue.\n\n"
            "OUTPUT FORMAT (STRICT JSON):\n"
            "{\n"
            '  "total_analyzed": <number>,\n'
            '  "systemic_summary": "<high-level architectural overview of patterns>",\n'
            '  "clusters": [\n'
            "    {\n"
            '      "cluster_name": "<name of pattern / issue>",\n'
            '      "target_type": "<TEMPLATE_CONFIG | CORE_PLATFORM_CODE | '
            'ENVIRONMENT_INFRA | MATRIX_CONSTRAINT>",\n'
            '      "category": "<Network | Permissions | Engine Bug | Timing | '
            'Backend Logic | Matrix Constraint>",\n'
            '      "affected_tests": ["<component_id (MODE/ENGINE)>", ...],\n'
            '      "root_cause_explanation": "<deep technical reason for cluster>",\n'
            '      "recommended_action": "<concrete architectural or config fix>",\n'
            '      "cross_matrix_impact": "<impact on other engines/modes>"\n'
            "    }\n"
            "  ],\n"
            '  "individual_quick_fixes": [\n'
            "    {\n"
            '      "component_id": "<id>",\n'
            '      "target_type": "<TEMPLATE_CONFIG | CORE_PLATFORM_CODE | '
            'MATRIX_CONSTRAINT>",\n'
            '      "fix_summary": "<quick fix or matrix constraint recommendation>"\n'
            "    }\n"
            "  ],\n"
            '  "overall_recommendations": [\n'
            '    "<strategic recommendation 1>",\n'
            '    "<strategic recommendation 2>"\n'
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Here are {len(condensed_failures)} failed test runs to analyze for "
            f"systemic patterns:\n\n"
            f"```json\n{json.dumps(condensed_failures, indent=2)}\n```"
        )

        raw_resp = self.engine.generate(
            prompt=user_prompt,
            system_context=system_prompt,
            response_format={"type": "json_object"},
        )

        return json.loads(raw_resp)


def apply_suggested_template(
    component_id: str,
    new_template_content: str,
    project_root: Optional[Path] = None,
) -> bool:
    """Safely updates docker-compose.template.yml with validated content."""
    root = project_root or Path(__file__).resolve().parent.parent.parent
    target_file = (
        root / "component_templates" / component_id / "docker-compose.template.yml"
    )

    if not target_file.parent.exists():
        logger.error(
            f"Component template directory does not exist: {target_file.parent}"
        )
        return False

    try:
        target_file.write_text(new_template_content, encoding="utf-8")
        logger.info(f"Successfully applied AI patch to {target_file}")
        return True
    except Exception as ex:
        logger.error(f"Failed to write template file {target_file}: {ex}")
        return False
