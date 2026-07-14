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

    def __init__(self, metadata_path: Path, templates_path: Path):
        self.metadata_file = Path(metadata_path)
        self.templates_path = Path(templates_path)
        self._cached_metadata: Dict[str, Any] = self._load_json(self.metadata_file)

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
        return self._cached_metadata

    def get_all_components(self) -> Dict[str, Any]:
        """Returns all defined components from the master metadata."""
        return self.get_all_metadata().get("components", {})

    def get_component_details(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Returns metadata for a specific component ID."""
        return self.get_all_components().get(component_id)

    def get_docker_service_name(self, component_id: str) -> str:
        """Gets the primary service name for a component's template."""
        component_details = self.get_component_details(component_id)
        if component_details:
            return component_details.get("docker_service_name", component_id)
        return component_id

    def get_component_variables_raw(self, component_id: str) -> Dict[str, Any]:
        """Reads the full variables.json dictionary under template-config."""
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
