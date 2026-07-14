# src/managers/component_writer.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ComponentWriter:
    """
    The Command side of the CQRS pattern.
    Responsible for all file system mutations and metadata updates.
    """

    def __init__(self, metadata_path: Path, templates_path: Path):
        self.metadata_file = Path(metadata_path)
        self.templates_path = Path(templates_path)

    def _save_json(self, file_path: Path, data: Any) -> bool:
        """Writes data to a JSON file with proper indentation."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, sort_keys=True)
            return True
        except IOError as e:
            logger.error(f"Could not save JSON to {file_path}: {e}")
            return False

    def save_metadata(self, data: Dict[str, Any]) -> bool:
        """Saves the complete components_metadata.json file."""
        return self._save_json(self.metadata_file, data)

    def save_component_variables_raw(
        self, component_id: str, data: Dict[str, Any]
    ) -> bool:
        """Saves the raw dictionary into template-config/variables.json."""
        var_path = (
            self.templates_path / component_id / "template-config" / "variables.json"
        )
        return self._save_json(var_path, data)

    def update_component_variables(self, component_id: str, data: List[Dict]) -> bool:
        """Updates the variables list inside template-config/variables.json."""
        wrapped_data = {"variables": data}
        return self.save_component_variables_raw(component_id, wrapped_data)

    def update_template_content(self, component_id: str, content: str) -> bool:
        """Writes docker-compose template content to disk."""
        comp_dir = self.templates_path / component_id
        comp_dir.mkdir(parents=True, exist_ok=True)
        template_file = comp_dir / "docker-compose.template.yml"

        # Check if the content already has the required comment headers
        required = [
            "status:",
            "last_tested_version:",
            "platform_notes:",
            "breaking_changes:",
        ]
        has_headers = False
        try:
            lines = content.splitlines()
            found_fields = set()
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    comment = stripped[1:].strip()
                    for field in required:
                        if comment.startswith(field):
                            found_fields.add(field)
                else:
                    break
            has_headers = len(found_fields) == len(required)
        except Exception:  # nosec B110
            pass

        if not has_headers:
            header = (
                '# status: "untested"\n'
                '# last_tested_version: "none"\n'
                '# platform_notes: "None"\n'
                '# breaking_changes: "None"\n'
            )
            content = header + content

        try:
            template_file.write_text(content, encoding="utf-8")
            return True
        except IOError as e:
            logger.error(f"Could not write template for {component_id}: {e}")
            return False

    def create_component_skeleton(self, component_id: str, meta: Dict) -> bool:
        """Creates directory structure and initial files for a new component."""
        comp_dir = self.templates_path / component_id
        if comp_dir.exists():
            return False

        comp_dir.mkdir(parents=True, exist_ok=True)
        config_dir = comp_dir / "template-config"
        config_dir.mkdir(parents=True, exist_ok=True)

        self._save_json(config_dir / "variables.json", {"variables": []})
        header = (
            '# status: "untested"\n'
            '# last_tested_version: "none"\n'
            '# platform_notes: "None"\n'
            '# breaking_changes: "None"\n'
        )
        (comp_dir / "docker-compose.template.yml").write_text(
            header + "services:\n", encoding="utf-8"
        )

        # Update master metadata
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    full_meta = json.load(f)
            else:
                full_meta = {"components": {}}
        except (FileNotFoundError, json.JSONDecodeError):
            full_meta = {"components": {}}

        full_meta.setdefault("components", {})[component_id] = meta
        return self._save_json(self.metadata_file, full_meta)

    def delete_component_files(self, component_id: str) -> bool:
        """Deletes the component's folder tree from disk."""
        comp_path = self.templates_path / component_id
        if comp_path.exists() and comp_path.is_dir():
            import shutil

            try:
                shutil.rmtree(comp_path)
                logger.info(f"Deleted template directory: {comp_path}")
                return True
            except OSError as e:
                logger.error(f"Failed to delete directory {comp_path}: {e}")
                raise e
        return False

    def update_package(self, pkg_id: str, update_data: Dict[str, Any]) -> bool:
        """Updates package definitions inside the master metadata file."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    full_meta = json.load(f)
            else:
                full_meta = {}

            if "packages" not in full_meta or pkg_id not in full_meta["packages"]:
                return False

            full_meta["packages"][pkg_id].update(update_data)
            return self._save_json(self.metadata_file, full_meta)
        except (json.JSONDecodeError, IOError):
            return False

    def delete_package(self, pkg_id: str) -> bool:
        """Removes a package definition from metadata if unused."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    full_meta = json.load(f)
            else:
                return False

            in_use = any(
                c.get("package_id") == pkg_id
                for c in full_meta.get("components", {}).values()
            )
            if (
                in_use
                or "packages" not in full_meta
                or pkg_id not in full_meta["packages"]
            ):
                return False

            del full_meta["packages"][pkg_id]
            return self._save_json(self.metadata_file, full_meta)
        except (json.JSONDecodeError, IOError):
            return False
