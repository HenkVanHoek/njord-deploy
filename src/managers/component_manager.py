# src/managers/component_manager.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, cast

import yaml
from jinja2 import Template

from managers.component_reader import ComponentReader
from managers.component_writer import ComponentWriter

logger = logging.getLogger(__name__)


class ComponentManager:
    """Manages component metadata and template files."""

    def __init__(self, templates_path: str, metadata_file_path: str):
        self.templates_path = Path(templates_path)
        self.metadata_file = Path(metadata_file_path)

        # Initialize Query & Command side DAL
        self.reader = ComponentReader(
            metadata_path=self.metadata_file, templates_path=self.templates_path
        )
        self.writer = ComponentWriter(
            metadata_path=self.metadata_file, templates_path=self.templates_path
        )

        self._components_data: Dict[str, Any] = self._load_metadata()
        self._variables_cache: Dict[str, List[Dict[str, Any]]] = (
            self._load_all_variables()
        )

    def _load_metadata(self) -> Dict[str, Any]:
        """Loads the main components metadata file."""
        data = self.reader.get_all_metadata()
        if not data:
            return {"_njorddeploy": {}, "components": {}}
        return data

    def _load_all_variables(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scans all component directories for variables.json and loads them
        into a central cache.
        """
        variables: Dict[str, List[Dict[str, Any]]] = {}
        components = self._components_data.get("components", {})
        for comp_id in components:
            variables[comp_id] = self.reader.get_component_variables(comp_id)
        return variables

    def _save_metadata(self):
        """Saves the current components data back to the JSON file."""
        self.writer.save_metadata(self._components_data)

    def create_package(self, pkg_id: str, name: str):
        """Adds a new package definition to the metadata."""
        if "packages" not in self._components_data:
            self._components_data["packages"] = {}
        if pkg_id in self._components_data["packages"]:
            raise ValueError(f"Package ID '{pkg_id}' already exists.")
        self._components_data["packages"][pkg_id] = {
            "name": name,
            "description": "",
            "network_type": "bridge",
        }
        self._save_metadata()

    def update_package_metadata(self, pkg_id: str, update_data: dict):
        """Updates existing package metadata fields."""
        if (
            "packages" not in self._components_data
            or pkg_id not in self._components_data["packages"]
        ):
            raise ValueError("Package not found.")
        self._components_data["packages"][pkg_id].update(update_data)
        self._save_metadata()

    def delete_package(self, pkg_id: str):
        """Removes a package definition if no components are assigned to it."""
        in_use = any(
            c.get("package_id") == pkg_id
            for c in self._components_data.get("components", {}).values()
        )
        if in_use:
            raise ValueError("Cannot delete package: components are still assigned.")
        if (
            "packages" in self._components_data
            and pkg_id in self._components_data["packages"]
        ):
            del self._components_data["packages"][pkg_id]
            self._save_metadata()

    def get_all_components(self) -> List[Dict[str, Any]]:
        """Returns a list of all components with their essential data."""
        self._components_data = self._load_metadata()
        components = self._components_data.get("components", {})
        all_comps: List[Dict[str, Any]] = []
        for comp_id, comp_data in components.items():
            full_data = comp_data.copy()
            full_data["id"] = comp_id
            full_data["required_variables"] = self.reader.get_component_variables(
                comp_id
            )
            full_data["variables"] = full_data["required_variables"]
            all_comps.append(full_data)
        return all_comps

    def get_all_packages(self) -> dict:
        """Returns the 'packages' section from the metadata file."""
        self._components_data = self._load_metadata()
        return self._components_data.get("packages", {})

    def get_component_details(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Returns the full details for a single component, including AI metadata."""
        self._components_data = self._load_metadata()
        component_data = self._components_data.get("components", {}).get(component_id)
        if not component_data:
            return None

        details = component_data.copy()
        details["id"] = component_id
        details["required_variables"] = self.reader.get_component_variables(
            component_id
        )
        details["variables"] = details["required_variables"]

        # Explicitly ensure the new AI and Package fields are present for the UI
        details.setdefault("package_id", "general-stack")
        details.setdefault("tags", [])
        details.setdefault(
            "resource_profile",
            {"cpu": "medium", "ram": "medium", "storage_type": "persistent"},
        )

        details["has_traefik_support"] = component_data.get(
            "has_traefik_support", False
        )
        details["traefik_internal_port"] = component_data.get(
            "traefik_internal_port", None
        )
        details["conflicts_with"] = component_data.get("conflicts_with", [])

        return details

    def validate_component_configuration(
        self,
        _component_id: str,
        template_content: str,
        _variables: List[Dict[str, Any]],
    ) -> None:
        """Validates a component's template and variables."""
        try:
            data = yaml.safe_load(template_content)
        except yaml.YAMLError as e:
            raise ValueError(
                f"YAML Parsing Failed: The template content is not valid YAML. "
                f"Error: {e}"
            )
        services = data.get("services", {}) if isinstance(data, dict) else {}
        for service_name, service_data in services.items():
            if not isinstance(service_data, dict):
                continue
            container_name = service_data.get("container_name")
            if isinstance(container_name, str) and container_name:
                mandatory_prefix = "njorddeploy-"
                if not container_name.lower().startswith(mandatory_prefix):
                    raise ValueError(
                        f"Naming Violation: The container_name '{container_name}' "
                        f"for service '{service_name}' must begin with the "
                        f"mandatory prefix '{mandatory_prefix}'."
                    )

    def validate_metadata_conflicts(
        self, component_id: str, conflicts_with_list: List[str]
    ) -> None:
        """Validates the 'conflicts_with' list for a component."""
        if component_id in conflicts_with_list:
            raise ValueError(
                f"Self-Conflict Error: Component '{component_id}' cannot "
                "conflict with itself."
            )
        self._components_data = self._load_metadata()
        all_component_ids = set(self._components_data.get("components", {}).keys())
        non_existent_conflicts = [
            cid for cid in conflicts_with_list if cid not in all_component_ids
        ]
        if non_existent_conflicts:
            non_existent_str = ", ".join(non_existent_conflicts)
            raise ValueError(
                "Non-Existent ID Error: The following component ID(s) "
                f"listed in 'Conflicts With' do not exist: "
                f"{non_existent_str}."
            )

    def create_component(self, component_id: str, component_name: str):
        """Creates the folder structure and initial files for a new component."""
        self._components_data = self._load_metadata()
        components = self._components_data.setdefault("components", {})
        if component_id in components:
            raise ValueError(f"Component '{component_id}' already exists.")

        self.writer.create_component_skeleton(
            component_id,
            {
                "name": component_name,
                "group": self.get_njorddeploy_meta().get("default_group", None),
                "description": "",
                "has_ui": False,
                "has_configuration": True,
                "depends_on": [],
                "conflicts_with": [],
                "ui_port_variable": None,
            },
        )

        self._components_data = self._load_metadata()
        self._variables_cache[component_id] = []

    def get_docker_service_name(self, component_id: str) -> str:
        """Gets the primary service name for a component's template."""
        component_details = self.get_component_details(component_id)
        if component_details:
            return component_details.get("docker_service_name", component_id)
        return component_id

    def update_component_metadata(self, component_id: str, update_data: Dict[str, Any]):
        self._components_data = self._load_metadata()
        components = self._components_data.setdefault("components", {})
        if component_id not in components:
            raise KeyError(f"Component '{component_id}' not found.")
        new_group_id = update_data.get("group")
        if isinstance(new_group_id, str) and new_group_id:
            njorddeploy_meta = self._components_data.setdefault("_njorddeploy", {})
            group_rules = njorddeploy_meta.setdefault("group_rules", {})
            if new_group_id not in group_rules:
                group_rules[new_group_id] = {
                    "name": new_group_id.replace("_", " ").title(),
                    "is_exclusive": False,
                }
                njorddeploy_meta.setdefault("group_order", []).append(new_group_id)
        components[component_id].update(update_data)
        self._save_metadata()

    def update_component_group(self, component_id: str, new_group_id: str):
        self._components_data = self._load_metadata()
        components = self._components_data.get("components", {})
        if component_id in components:
            components[component_id]["group"] = new_group_id
            self._save_metadata()
        else:
            raise KeyError(f"Component '{component_id}' not found.")

    def get_njorddeploy_meta(self) -> Dict[str, Any]:
        self._components_data = self._load_metadata()
        return self._components_data.get("_njorddeploy", {})

    def sort_components_by_master_order(self, component_ids: List[str]) -> List[str]:
        master_order = self.get_njorddeploy_meta().get("components_order", [])
        order_map = {comp_id: i for i, comp_id in enumerate(master_order)}
        return sorted(
            component_ids, key=lambda cid: order_map.get(cid, len(master_order))
        )

    def update_group_order(self, new_order: List[str]):
        self._components_data = self._load_metadata()
        njorddeploy_meta = self._components_data.setdefault("_njorddeploy", {})
        njorddeploy_meta["group_order"] = new_order
        self._save_metadata()

    def update_components_order(self, new_order: List[str]):
        self._components_data = self._load_metadata()
        njorddeploy_meta = self._components_data.setdefault("_njorddeploy", {})
        njorddeploy_meta["components_order"] = new_order
        self._save_metadata()

    def delete_group(self, group_id: str):
        all_components = self.get_all_components()
        is_in_use = any(comp.get("group") == group_id for comp in all_components)
        if is_in_use:
            raise ValueError(
                f"Group '{group_id}' is still in use and cannot be deleted."
            )
        self._components_data = self._load_metadata()
        njorddeploy_meta = self._components_data.setdefault("_njorddeploy", {})
        if (
            "group_rules" in njorddeploy_meta
            and group_id in njorddeploy_meta["group_rules"]
        ):
            del njorddeploy_meta["group_rules"][group_id]
        if (
            "group_order" in njorddeploy_meta
            and group_id in njorddeploy_meta["group_order"]
        ):
            njorddeploy_meta["group_order"].remove(group_id)
        self._save_metadata()

    def rename_group(self, group_id: str, new_name: str):
        """Renames the display name of an existing group."""
        self._components_data = self._load_metadata()
        njorddeploy_meta = self._components_data.setdefault("_njorddeploy", {})
        group_rules = njorddeploy_meta.setdefault("group_rules", {})
        if group_id not in group_rules:
            raise ValueError(f"Group '{group_id}' not found.")
        group_rules[group_id]["name"] = new_name
        self._save_metadata()

    def _get_component_config_path(self, component_id: str) -> Path:
        return self.templates_path / component_id / "template-config"

    def update_component_variables(
        self, component_id: str, variables_payload: Dict[str, Any]
    ):
        """Performs a non-destructive update of the variables.json file."""
        original_data = self.reader.get_component_variables_raw(component_id)
        if not isinstance(original_data, dict):
            original_data = {}

        original_data["variables"] = variables_payload.get("variables", [])

        self.writer.save_component_variables_raw(component_id, original_data)
        self._variables_cache[component_id] = original_data["variables"]

    def get_component_template_content(self, component_id: str) -> str:
        return self.reader.get_template_content(component_id)

    def update_component_template_content(self, component_id: str, content: str):
        self.writer.update_template_content(component_id, content)

    def delete_component(self, component_id: str):
        self._components_data = self._load_metadata()
        components = self._components_data.get("components", {})
        if component_id not in components:
            raise KeyError(f"Component '{component_id}' not found.")
        del components[component_id]
        njorddeploy_meta = self._components_data.get("_njorddeploy", {})
        if (
            "components_order" in njorddeploy_meta
            and component_id in njorddeploy_meta["components_order"]
        ):
            njorddeploy_meta["components_order"].remove(component_id)

        self.writer.delete_component_files(component_id)
        self._save_metadata()

    def _get_traefik_labels(
        self,
        component_id: str,
        traefik_host: str,
        fqdn_suffix: str,
        traefik_internal_port: int,
    ) -> List[str]:
        """Generates the standard Traefik labels for a service."""
        return [
            "traefik.enable=true",
            f"traefik.http.routers.{component_id}.entrypoints=websecure",
            (
                f"traefik.http.routers.{component_id}.rule="
                f"Host(`{traefik_host}.{fqdn_suffix}`)"
            ),
            f"traefik.http.routers.{component_id}.tls=true",
            (
                f"traefik.http.services.{component_id}.loadbalancer."
                f"server.port={traefik_internal_port}"
            ),
        ]

    def _get_traefik_labels_yaml_block(
        self,
        component_id: str,
        traefik_host: str,
        fqdn_suffix: str,
        traefik_internal_port: int,
    ) -> str:
        """
        Generates the standard Traefik labels as a fully formatted,
        indented YAML block string.
        """
        labels = self._get_traefik_labels(
            component_id, traefik_host, fqdn_suffix, traefik_internal_port
        )
        yaml_block = "\n".join(f"      - {label}" for label in labels)
        return yaml_block

    def render_component_template(
        self,
        component_id: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Loads a component's template, injects Traefik labels, and renders it.
        Includes a brute-force fallback for stubborn variables.
        """
        component_details = self.get_component_details(component_id)
        if not component_details:
            logger.error(f"Component '{component_id}' not found for rendering.")
            return "services: {}"

        component_variable_definitions = self.reader.get_component_variables(
            component_id
        )
        for var_def in component_variable_definitions:
            var_id = var_def.get("id")
            # Mitigation: isinstance check narrows the type of var_id to str
            if (
                isinstance(var_id, str)
                and var_id not in context
                and "default" in var_def
            ):
                context[var_id] = var_def["default"]

        if "CONFIG_BASE_PATH" not in context:
            context["CONFIG_BASE_PATH"] = "../njorddeploy_data"

        if "DATA_ROOT" not in context:
            context["DATA_ROOT"] = "/opt/njorddeploy/data"

        template_content = self.get_component_template_content(component_id)

        has_traefik_support = component_details.get("has_traefik_support", False)
        context["has_traefik_support"] = has_traefik_support
        context["component_id"] = component_id
        context["component_version"] = component_details.get(
            "component_version", "latest"
        )
        context["image_name"] = component_details.get("image_name", "")

        traefik_internal_port = component_details.get("traefik_internal_port")
        traefik_host = context.get("TRAEFIK_HOST")
        fqdn_suffix = context.get("FQDN_SUFFIX")

        excluded_ports: Set[int] = set()
        component_vars = component_details.get("required_variables", [])
        for var in component_vars:
            if var.get("type") == "port_exclude_traefik":
                var_id = var.get("id")
                if isinstance(var_id, str):
                    val = context.get(var_id)
                    try:
                        if isinstance(val, (str, int, float)):
                            excluded_ports.add(int(val))
                    except (ValueError, TypeError):
                        pass

        is_internal_port_excluded = (
            isinstance(traefik_internal_port, int)
            and traefik_internal_port in excluded_ports
        )

        should_generate_labels = (
            has_traefik_support
            and isinstance(traefik_internal_port, int)
            and traefik_host is not None
            and fqdn_suffix is not None
            and not is_internal_port_excluded
        )

        if should_generate_labels:
            my_casted_traefik_internal_port = cast(int, traefik_internal_port)
            yaml_block = self._get_traefik_labels_yaml_block(
                component_id=component_id,
                traefik_host=str(traefik_host),
                fqdn_suffix=str(fqdn_suffix),
                traefik_internal_port=my_casted_traefik_internal_port,
            )
            context["traefik_labels_yaml"] = yaml_block
        else:
            context["traefik_labels_yaml"] = ""

        try:
            template = Template(template_content)
            rendered = template.render(**context)

            if "{{ CONFIG_BASE_PATH }}" in rendered:
                logger.warning(
                    f"Jinja missed CONFIG_BASE_PATH in {component_id}. "
                    f"Using brute force replace."
                )
                base_path = str(context.get("CONFIG_BASE_PATH", "../njorddeploy_data"))
                rendered = rendered.replace("{{ CONFIG_BASE_PATH }}", base_path)

            return rendered
        except Exception as e:
            logger.error(
                f"Error rendering template for {component_id}: {e}",
                exc_info=True,
            )
            return f"# ERROR: Template rendering failed: {e}"

    def generate_deployment_artifacts(
        self,
        selected_components_data: List[Dict[str, Any]],
        global_vars: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """
        Generates docker-compose.yml AND a .env file.
        Injects identification labels for the DeploymentManager.
        """
        logger.info("Starting deployment artifact generation.")
        output_path.mkdir(parents=True, exist_ok=True)

        docker_compose_data: Dict[str, Any] = {
            "services": {},
            "networks": {"njorddeploy-network": {"external": True}},
            "volumes": {},
        }

        deployment_context = global_vars.copy()
        deployment_context["CONFIG_BASE_PATH"] = "../njorddeploy_data"
        if "DATA_ROOT" not in deployment_context:
            deployment_context["DATA_ROOT"] = "/opt/njorddeploy/data"

        component_ids: List[str] = [
            str(comp_id)
            for comp in selected_components_data
            if (comp_id := comp.get("id")) is not None
        ]
        sorted_ids = self.sort_components_by_master_order(component_ids)
        comp_data_map = {comp.get("id"): comp for comp in selected_components_data}

        for component_id in sorted_ids:
            component_data = comp_data_map.get(component_id)
            if not component_data:
                continue

            render_context = deployment_context.copy()
            rendered_yaml = self.render_component_template(component_id, render_context)

            config_templates = component_data.get("config_templates")
            if isinstance(config_templates, dict):
                for template_name, raw_location in config_templates.items():
                    template_file = (
                        self.templates_path
                        / component_id
                        / "template-config"
                        / template_name
                    )
                    if template_file.exists():
                        try:
                            with open(template_file, "r", encoding="utf-8") as tf:
                                template_content = tf.read()

                            config_template = Template(template_content)
                            rendered_config = config_template.render(**render_context)

                            target_file_path = output_path / "data" / raw_location
                            target_file_path.parent.mkdir(parents=True, exist_ok=True)

                            with open(
                                target_file_path, "w", encoding="utf-8"
                            ) as tf_out:
                                tf_out.write(rendered_config)
                            logger.info(
                                f"Generated config template {template_name} "
                                f"at {target_file_path}"
                            )
                        except Exception as config_err:
                            logger.error(
                                f"Error rendering config template {template_name} "
                                f"for {component_id}: {config_err}",
                                exc_info=True,
                            )

            try:
                comp_compose = yaml.safe_load(rendered_yaml)
                if not isinstance(comp_compose, dict):
                    comp_compose = {}
            except yaml.YAMLError as e:
                logger.error(f"YAML Syntax Error in component '{component_id}': {e}")
                continue

            if "version" in comp_compose:
                docker_compose_data["version"] = comp_compose["version"]

            new_services = comp_compose.get("services", {})

            # Inject ID labels
            for svc_name, svc_def in new_services.items():
                if not isinstance(svc_def, dict):
                    continue

                if "labels" not in svc_def or svc_def["labels"] is None:
                    svc_def["labels"] = []

                label_val = f"njorddeploy.component.id={component_id}"

                if isinstance(svc_def["labels"], list):
                    if label_val not in svc_def["labels"]:
                        svc_def["labels"].append(label_val)
                elif isinstance(svc_def["labels"], dict):
                    svc_def["labels"]["njorddeploy.component.id"] = component_id

            docker_compose_data["services"].update(new_services)

            for net_name, net_def in comp_compose.get("networks", {}).items():
                if net_name not in docker_compose_data.get("networks", {}):
                    net_copy = net_def.copy()
                    net_copy.setdefault("external", False)
                    docker_compose_data["networks"][net_name] = net_copy

            docker_compose_data["volumes"].update(comp_compose.get("volumes", {}))

        logger.info("Writing final artifacts.")

        compose_path = output_path / "docker-compose.yml"
        with open(compose_path, "w", encoding="utf-8") as f:
            yaml.dump(docker_compose_data, f, sort_keys=False)

        context_path = output_path / "deployment_context.json"
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(deployment_context, f, indent=2, sort_keys=True)

        env_path = output_path / ".env"
        with open(env_path, "w", encoding="utf-8") as f:
            for key, value in deployment_context.items():
                if isinstance(value, (str, int, float, bool)):
                    f.write(f"{key}={value}\n")

        logger.info("Artifact generation completed.")
