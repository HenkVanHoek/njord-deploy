# src/managers/component_reader.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComponentReader:
    """
    The Query side of the CQRS pattern.
    Handles all read operations for component metadata and variables.
    """

    def __init__(
        self,
        metadata_path: Path,
        templates_path: Path,
        private_templates_path: Optional[Path] = None,
        private_metadata_path: Optional[Path] = None,
    ):
        self.metadata_file = Path(metadata_path)
        self.templates_path = Path(templates_path)
        self.private_templates_path = (
            Path(private_templates_path) if private_templates_path else None
        )
        self.private_metadata_file = (
            Path(private_metadata_path) if private_metadata_path else None
        )
        self._cached_metadata: Dict[str, Any] = self.get_all_metadata()

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Centralized JSON loader to ensure consistent error handling."""
        try:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return {}
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load JSON from {file_path}: {e}")
            return {}

    def get_all_metadata(self) -> Dict[str, Any]:
        """Loads and returns the fresh metadata file dictionary."""
        self._cached_metadata = self._load_json(self.metadata_file)
        if self.private_metadata_file and self.private_metadata_file.exists():
            if not self._cached_metadata:
                self._cached_metadata = {"_njorddeploy": {}, "components": {}}
            private_data = self._load_json(self.private_metadata_file)
            if isinstance(private_data, dict):
                priv_comps = private_data.get("components", {})
                if isinstance(priv_comps, dict):
                    comps = self._cached_metadata.setdefault("components", {})
                    for comp_id, comp_meta in priv_comps.items():
                        if isinstance(comp_meta, dict):
                            comp_meta["private"] = True
                            comp_meta["is_private"] = True
                            comps[comp_id] = comp_meta
                priv_pkgs = private_data.get("packages", {})
                if isinstance(priv_pkgs, dict):
                    pkgs = self._cached_metadata.setdefault("packages", {})
                    for pkg_id, pkg_meta in priv_pkgs.items():
                        if isinstance(pkg_meta, dict):
                            pkg_meta["private"] = True
                            pkg_meta["is_private"] = True
                            pkgs[pkg_id] = pkg_meta
        return self._cached_metadata

    def get_template_status(self, component_id: str) -> str:
        """Reads the status of a component from its template header."""
        template_file = self.get_template_path(component_id)
        if not template_file.exists():
            return "untested"
        # noinspection PyBroadException
        try:
            content = template_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("#"):
                    stripped = line[1:].strip()
                    if stripped.startswith("status:"):
                        parts = stripped.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip().strip('"').strip("'")
        except Exception:  # nosec B110
            pass
        return "untested"

    def get_all_components(self) -> Dict[str, Any]:
        """Returns all components enriched with template status if missing."""
        components = self.get_all_metadata().get("components", {})
        for comp_id, comp in components.items():
            if isinstance(comp, dict) and "test_status" not in comp:
                comp["test_status"] = self.get_template_status(comp_id)
        return components

    def get_component_details(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Returns metadata for a specific component ID."""
        comp = self.get_all_components().get(component_id)
        if isinstance(comp, dict) and "test_status" not in comp:
            comp["test_status"] = self.get_template_status(component_id)
        return comp

    def get_docker_service_name(self, component_id: str) -> str:
        """Gets the primary service name for a component's template."""
        component_details = self.get_component_details(component_id)
        if component_details:
            return component_details.get("docker_service_name", component_id)
        return component_id

    def get_component_variables_raw(self, component_id: str) -> Dict[str, Any]:
        """Reads the full variables.json dictionary under template-config."""
        if self.private_templates_path:
            priv_var = (
                self.private_templates_path
                / component_id
                / "template-config"
                / "variables.json"
            )
            if priv_var.exists():
                return self._load_json(priv_var)
        var_path = (
            self.templates_path / component_id / "template-config" / "variables.json"
        )
        return self._load_json(var_path)

    def get_component_variables(self, component_id: str) -> List[Dict[str, Any]]:
        """Reads variables list directly from template-config/variables.json."""
        data = self.get_component_variables_raw(component_id)
        if isinstance(data, dict) and "variables" in data:
            return data["variables"]
        return data if isinstance(data, list) else []

    def get_template_path(self, component_id: str) -> Path:
        """Returns the path to the docker-compose template file."""
        if self.private_templates_path:
            priv_tpl = (
                self.private_templates_path
                / component_id
                / "docker-compose.template.yml"
            )
            if priv_tpl.exists():
                return priv_tpl
        return self.templates_path / component_id / "docker-compose.template.yml"

    def get_template_content(self, component_id: str) -> str:
        """Reads template file content, falling back to empty services."""
        template_file = self.get_template_path(component_id)
        try:
            if template_file.exists():
                return template_file.read_text(encoding="utf-8")
            return "services:\n"
        except IOError as e:
            logger.error(f"Could not read template for {component_id}: {e}")
            return f"# Template for {component_id} not found.\n"

    def get_all_packages(self) -> Dict[str, Any]:
        """Returns all defined packages from the master metadata."""
        return self.get_all_metadata().get("packages", {})

    def get_component_configs(self, component_id: str) -> Dict[str, str]:
        """Returns all config files in template-config (except variables.json)."""
        config_dir = None
        if self.private_templates_path:
            priv_dir = self.private_templates_path / component_id / "template-config"
            if priv_dir.exists() and priv_dir.is_dir():
                config_dir = priv_dir
        if config_dir is None:
            config_dir = self.templates_path / component_id / "template-config"
        configs = {}
        if config_dir.exists() and config_dir.is_dir():
            for file_path in sorted(config_dir.iterdir()):
                if file_path.is_file() and file_path.name != "variables.json":
                    try:
                        configs[file_path.name] = file_path.read_text(encoding="utf-8")
                    except IOError as e:
                        logger.error(f"Could not read config {file_path}: {e}")
        return configs
