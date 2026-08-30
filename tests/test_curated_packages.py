# tests/test_curated_packages.py
import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
import yaml

from src.managers.component_manager import ComponentManager


@pytest.fixture
def project_paths() -> Tuple[Path, Path]:
    """Returns project metadata path and component templates path."""
    project_root = Path(__file__).resolve().parent.parent
    metadata_path = project_root / "config" / "components_metadata.json"
    templates_path = project_root / "component_templates"
    return metadata_path, templates_path


@pytest.fixture
def component_manager(project_paths: Tuple[Path, Path]) -> ComponentManager:
    """Initializes ComponentManager with production metadata."""
    metadata_path, templates_path = project_paths
    return ComponentManager(
        templates_path=str(templates_path),
        metadata_file_path=str(metadata_path),
    )


def test_packages_schema_and_non_empty(component_manager: ComponentManager):
    """
    Verifies that all packages conform to schema with valid names and descriptions.
    """
    packages = component_manager.get_all_packages()
    assert len(packages) >= 5, "Expected at least 5 curated packages in metadata."

    for pkg_id, pkg_data in packages.items():
        assert (
            isinstance(pkg_id, str) and pkg_id.strip()
        ), "Package ID must not be empty"
        assert isinstance(pkg_data, dict), f"Package '{pkg_id}' data must be a dict"
        assert (
            "name" in pkg_data and pkg_data["name"].strip()
        ), f"Package '{pkg_id}' must have a non-empty name."
        assert (
            "description" in pkg_data and pkg_data["description"].strip()
        ), f"Package '{pkg_id}' must have a descriptive summary."
        assert (
            pkg_data.get("network_type") == "bridge"
        ), f"Package '{pkg_id}' network_type must be 'bridge'."


def test_packages_assigned_components_exist(component_manager: ComponentManager):
    """Verifies that every package has valid existing component assignments."""
    packages = component_manager.get_all_packages()
    all_components = component_manager.get_all_components()
    comp_ids = {c["id"] for c in all_components}

    for pkg_id in packages:
        assigned = [c["id"] for c in all_components if c.get("package_id") == pkg_id]
        assert len(assigned) > 0, f"Package '{pkg_id}' has no assigned components."
        for cid in assigned:
            assert (
                cid in comp_ids
            ), f"Assigned component '{cid}' not found in component catalog."


def test_package_templates_and_ports(project_paths: Tuple[Path, Path]):
    """Validates that no host port collisions occur within any curated package."""
    metadata_path, templates_path = project_paths
    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    packages: Dict[str, Any] = meta.get("packages", {})
    components: Dict[str, Any] = meta.get("components", {})

    for pkg_id, pkg_info in packages.items():
        assigned_cids = [
            cid
            for cid, cinfo in components.items()
            if cinfo.get("package_id") == pkg_id
        ]

        package_host_ports: Dict[int, str] = {}

        for cid in assigned_cids:
            # 1. Load component default variables
            var_file = templates_path / cid / "template-config" / "variables.json"
            defaults: Dict[str, str] = {
                "DATA_ROOT": "/var/lib/njorddeploy",
                "CONFIG_BASE_PATH": "/opt/njorddeploy/config",
                "DOMAIN": "localhost",
                "DEFAULT_EMAIL": "admin@example.com",
                "TIMEZONE": "UTC",
                "TZ": "UTC",
            }
            if var_file.exists():
                vdata = json.loads(var_file.read_text(encoding="utf-8"))
                vlist = vdata.get("variables", []) if isinstance(vdata, dict) else vdata
                for v in vlist:
                    vid = v.get("id") or v.get("name")
                    vdef = v.get("default") or v.get("default_value") or ""
                    if vid:
                        defaults[vid] = str(vdef)

            # 2. Load and render compose template
            tmpl_file = templates_path / cid / "docker-compose.template.yml"
            assert tmpl_file.exists(), f"Missing template file for component '{cid}'"
            raw_tmpl = tmpl_file.read_text(encoding="utf-8")

            def replace_var(match: re.Match) -> str:
                expr = match.group(1).strip()
                if "|" in expr:
                    split_parts = expr.split("|", 1)
                    first_part, _ = split_parts
                    var_name = first_part.strip()
                    def_val_match = re.search(
                        r"default\s*\(\s*['\"]?([^'\"]+)['\"]?", expr
                    )
                    fallback = def_val_match.group(1) if def_val_match else ""
                    return defaults.get(var_name, fallback)
                return defaults.get(expr, f"VAR_{expr}")

            rendered = re.sub(r"\{\{\s*(.*?)\s*\}\}", replace_var, raw_tmpl)
            rendered = re.sub(r"\{%.*?%\}", "", rendered)
            rendered = re.sub(r"\{#.*?#\}", "", rendered)

            compose_data = yaml.safe_load(rendered)
            assert isinstance(compose_data, dict), f"Invalid YAML for '{cid}'"
            services = compose_data.get("services", {})

            # 3. Check port mappings
            for sname, sdata in services.items():
                ports = sdata.get("ports", [])
                for p in ports:
                    p_str = str(p)
                    parts = p_str.split(":")
                    if len(parts) >= 2:
                        split_host = parts[0].split("/")
                        last_host = split_host[-1]
                        if last_host.isdigit():
                            port_num = int(last_host)
                            # Exception for identical duplicate container definitions
                            if port_num in package_host_ports:
                                prev_source = package_host_ports[port_num]
                                assert prev_source == cid, (
                                    f"Port collision in package '{pkg_id}': "
                                    f"port {port_num} used by both '{prev_source}' "
                                    f"and '{cid}' ({sname})"
                                )
                            package_host_ports[port_num] = cid
