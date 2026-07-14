# src/managers/artifact_generator.py
import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml
from jinja2 import Template

logger = logging.getLogger(__name__)


class ArtifactGenerator:
    """
    Generates deployment artifacts (Docker Compose, .env)
    by merging templates with user-provided variables.
    """

    def __init__(self, reader: Any):
        """
        Initialize with a ComponentReader to access templates and metadata.
        """
        self.reader = reader

    def _generate_traefik_labels(self, comp_id: str, meta: Dict) -> Dict[str, str]:
        """Generates standardized Traefik labels for components."""
        labels: dict[str, str] = {}
        if not meta.get("has_traefik_support"):
            return labels

        svc = meta.get("docker_service_name", comp_id)
        domain = meta.get("traefik_domain", f"{comp_id}.local")
        port = meta.get("traefik_port", 80)

        labels.update(
            {
                "traefik.enable": "true",
                "traefik.http.routers." + svc + ".rule": f"Host(`{domain}`)",
                "traefik.http.services." + svc + ".loadbalancer.server.port": str(port),
            }
        )
        return labels

    def create_artifacts(
        self, out_path: Path, components: List[str], user_variables: Dict
    ) -> bool:
        """
        Creates the final docker-compose.yml in the target directory.
        Renamed 'vars' to 'user_variables' to avoid shadowing built-in names.
        """
        compose_data = {
            "services": {},
            "networks": {"njorddeploy_net": {"external": False}},
            "volumes": {},
        }

        for comp_id in components:
            meta = self.reader.get_component_details(comp_id)
            template_file = self.reader.get_template_path(comp_id)

            if not meta or not template_file.exists():
                logger.warning(f"Skipping {comp_id}: Missing metadata or template.")
                continue

            # Render Jinja2 template using variables specific to this component
            raw_tpl = template_file.read_text(encoding="utf-8")
            rendered = Template(raw_tpl).render(
                variables=user_variables.get(comp_id, {})
            )
            comp_yaml = yaml.safe_load(rendered)

            # Merge services and inject Traefik labels where applicable
            if comp_yaml and "services" in comp_yaml:
                for svc_name, svc_def in comp_yaml["services"].items():
                    labels = self._generate_traefik_labels(comp_id, meta)
                    if labels:
                        svc_def.setdefault("labels", {}).update(labels)
                    compose_data["services"][svc_name] = svc_def

        # Atomic-like write: ensure directory exists before dumping YAML
        out_path.mkdir(parents=True, exist_ok=True)
        try:
            with open(out_path / "docker-compose.yml", "w", encoding="utf-8") as f:
                yaml.dump(compose_data, f, sort_keys=False)
            return True
        except IOError as e:
            logger.error(f"Failed to write deployment artifacts: {e}")
            return False
