# tests/test_component_manager.py
import json

import pytest
import yaml

from managers.component_manager import ComponentManager


def test_generate_deployment_artifacts_renders_config_templates(tmp_path):
    """Test if generate_deployment_artifacts renders config templates."""
    # Setup paths
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Component directory structure
    comp_dir = templates_dir / "caddy"
    comp_dir.mkdir()

    # Compose template
    compose_template_content = (
        "services:\n"
        "  caddy:\n"
        "    image: caddy:latest\n"
        "    volumes:\n"
        '      - "{{ DATA_ROOT }}/caddy/Caddyfile:/etc/caddy/Caddyfile"\n'
    )
    (comp_dir / "docker-compose.template.yml").write_text(
        compose_template_content, encoding="utf-8"
    )

    # template-config folder and Caddyfile
    template_config_dir = comp_dir / "template-config"
    template_config_dir.mkdir()

    caddyfile_content = ":80 {\n" '    respond "Welcome to {{ DOMAIN }}"\n' "}\n"
    (template_config_dir / "Caddyfile").write_text(caddyfile_content, encoding="utf-8")

    # Component metadata JSON
    meta_data = {
        "components": {
            "caddy": {
                "name": "Caddy",
                "component_version": "latest",
                "image_name": "caddy",
                "config_templates": {"Caddyfile": "caddy/Caddyfile"},
            }
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    # Instantiate ComponentManager
    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # Input data
    selected_components_data = [
        {
            "id": "caddy",
            "name": "Caddy",
            "component_version": "latest",
            "image_name": "caddy",
            "config_templates": {"Caddyfile": "caddy/Caddyfile"},
        }
    ]
    global_vars = {"DOMAIN": "example.com"}
    output_dir = tmp_path / "output"

    # Execute
    manager.generate_deployment_artifacts(
        selected_components_data=selected_components_data,
        global_vars=global_vars,
        output_path=output_dir,
    )

    # Verify docker-compose.yml has DATA_ROOT replaced by its default value
    compose_path = output_dir / "docker-compose.yml"
    assert compose_path.exists()

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    caddy_volumes = compose_data["services"]["caddy"]["volumes"]
    (caddy_volume,) = caddy_volumes
    assert caddy_volume == "/opt/njorddeploy/data/caddy/Caddyfile:/etc/caddy/Caddyfile"

    # Verify rendered Caddyfile exists and has DOMAIN replaced
    rendered_caddyfile_path = output_dir / "data" / "caddy" / "Caddyfile"
    assert rendered_caddyfile_path.exists()

    rendered_content = rendered_caddyfile_path.read_text(encoding="utf-8")
    assert "Welcome to example.com" in rendered_content


def test_validate_component_configuration_with_jinja(tmp_path):
    """Test validate_component_configuration with unquoted Jinja templates."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    unquoted_jinja_yaml = (
        "services:\n"
        "  my-service:\n"
        "    image: {{ image_name }}:{{ component_version }}\n"
        "    ports:\n"
        "      - {{ MY_PORT }}:80\n"
    )

    # Should not raise ValueError/YAMLError
    manager.validate_component_configuration("my-service", unquoted_jinja_yaml, [])


def test_validate_component_configuration_with_complex_database_url(tmp_path):
    """Test validate_component_configuration with complex Jinja connection string."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    litellm_template = (
        "services:\n"
        "  litellm:\n"
        "    container_name: njorddeploy-litellm\n"
        "    image: ghcr.io/berriai/litellm:main-latest\n"
        "    ports:\n"
        '      - "{{ LITELLM_PORT }}:4000"\n'
        "    environment:\n"
        '      - DATABASE_URL="postgresql://{{ POSTGRES_USER }}:'
        '{{ POSTGRES_PASSWORD }}@njorddeploy-litellm-db:5432/{{ POSTGRES_DB }}"\n'
    )

    # Should not raise ValueError/YAMLError
    manager.validate_component_configuration("litellm", litellm_template, [])


def test_validate_component_configuration_fails_with_nested_pull_policy(tmp_path):
    """Test that validation fails if pull_policy is nested inside build block."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    invalid_yaml = (
        "services:\n"
        "  my-service:\n"
        "    build:\n"
        "      context: .\n"
        "      dockerfile: Dockerfile\n"
        "      pull_policy: build\n"
    )

    with pytest.raises(ValueError, match="nested inside the 'build' block"):
        manager.validate_component_configuration("my-service", invalid_yaml, [])


def test_update_component_metadata_test_status(tmp_path):
    """Test that test_status is saved properly when updating component metadata."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    meta_data = {
        "components": {
            "caddy": {
                "name": "Caddy",
                "test_status": "untested",
            }
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    manager.update_component_metadata("caddy", {"test_status": "tested"})
    updated = manager.get_component_details("caddy")
    assert updated is not None
    assert updated.get("test_status") == "tested"


def test_update_component_metadata_validates_ui_port_variable(tmp_path):
    """Test that setting has_ui=True without a ui_port_variable raises ValueError."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    meta_data = {
        "components": {
            "testcomp": {
                "name": "TestComp",
                "has_ui": False,
                "ui_port_variable": None,
            }
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    with pytest.raises(ValueError, match="ui_port_variable"):
        manager.update_component_metadata(
            "testcomp", {"has_ui": True, "ui_port_variable": ""}
        )


def test_render_open_webui_template_default_fallbacks(tmp_path):
    """Test rendering open-webui template without variables succeeds via defaults."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    comp_dir = templates_dir / "open-webui"
    comp_dir.mkdir()

    compose_template_content = (
        "services:\n"
        "  ollama:\n"
        "    container_name: njorddeploy-ollama\n"
        "    image: ollama/ollama:{{ OLLAMA_VERSION | default('latest') }}\n"
        "  open-webui:\n"
        "    container_name: njorddeploy-open-webui\n"
        '    image: \'{{ image_name | default("ghcr.io/open-webui/open-webui") }}:'
        '{{ component_version | default("main") }}\'\n'
        "    ports:\n"
        "      - '{{ OPEN_WEBUI_PORT | default(\"8080\") }}:8080'\n"
    )
    (comp_dir / "docker-compose.template.yml").write_text(
        compose_template_content, encoding="utf-8"
    )

    meta_data = {
        "components": {
            "open-webui": {
                "name": "Open WebUI",
                "component_version": "main",
                "image_name": "ghcr.io/open-webui/open-webui",
                "traefik_internal_port": 8080,
                "ui_port_variable": "OPEN_WEBUI_PORT",
            }
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    selected_components_data = [
        {
            "id": "open-webui",
            "name": "Open WebUI",
            "component_version": "main",
            "image_name": "ghcr.io/open-webui/open-webui",
            "traefik_internal_port": 8080,
            "ui_port_variable": "OPEN_WEBUI_PORT",
        }
    ]
    output_dir = tmp_path / "output"

    manager.generate_deployment_artifacts(
        selected_components_data=selected_components_data,
        global_vars={},
        output_path=output_dir,
    )

    compose_path = output_dir / "docker-compose.yml"
    assert compose_path.exists()

    with open(compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    assert "open-webui" in compose_data["services"]
    assert "ollama" in compose_data["services"]
    assert compose_data["services"]["open-webui"]["ports"] == ["8080:8080"]


def test_config_template_lifecycle(tmp_path):
    """Tests saving, retrieving, and deleting configuration template files."""
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(
        json.dumps({"components": {"litellm": {"name": "LiteLLM"}}}),
        encoding="utf-8",
    )
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # 1. Save config template
    saved = manager.save_component_config(
        "litellm", "config.yaml", "model_list:\n  - model_name: claude\n"
    )
    assert saved is True

    # 2. Get config templates
    configs = manager.get_component_configs("litellm")
    assert "config.yaml" in configs
    assert "model_list:\n  - model_name: claude\n" in configs["config.yaml"]

    # Verify metadata updated
    meta = manager.get_component_details("litellm")
    assert meta is not None
    assert meta.get("config_templates", {}).get("config.yaml") == "litellm/config.yaml"

    # 3. Delete config template
    deleted = manager.delete_component_config("litellm", "config.yaml")
    assert deleted is True

    configs_after = manager.get_component_configs("litellm")
    assert "config.yaml" not in configs_after


def test_component_supported_matrix(tmp_path):
    """Test get_supported_matrix, is_mode_supported, and matrix update."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    meta_data = {
        "components": {
            "gluetun": {
                "name": "Gluetun",
                "supported_matrix": {
                    "modes": ["vm"],
                    "engines": ["docker"],
                    "notes": "Requires /dev/net/tun device",
                },
            },
            "adguard": {
                "name": "AdGuard",
            },
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # 1. Check custom matrix on gluetun
    assert manager.is_mode_supported("gluetun", "vm") is True
    assert manager.is_mode_supported("gluetun", "lxc") is False
    assert manager.is_engine_supported("gluetun", "docker") is True
    assert manager.is_engine_supported("gluetun", "podman") is False

    # 2. Check default matrix on adguard (all supported)
    assert manager.is_mode_supported("adguard", "lxc") is True
    assert manager.is_mode_supported("adguard", "vm") is True
    assert manager.is_engine_supported("adguard", "docker") is True
    assert manager.is_engine_supported("adguard", "podman") is True

    # 3. Update matrix constraint on adguard
    manager.update_component_matrix_constraint(
        component_id="adguard",
        modes=["lxc"],
        engines=["podman"],
        notes="Optimized for rootless LXC",
    )
    assert manager.is_mode_supported("adguard", "lxc") is True
    assert manager.is_mode_supported("adguard", "vm") is False
    assert manager.is_engine_supported("adguard", "docker") is False
    assert manager.is_engine_supported("adguard", "podman") is True
    matrix = manager.get_supported_matrix("adguard")
    assert matrix["notes"] == "Optimized for rootless LXC"


def test_packages_lifecycle_and_constraints(tmp_path):
    """Test package creation, updating, deletion, and constraints."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    meta_data = {
        "components": {
            "caddy": {"name": "Caddy", "package_id": "pkg-web"},
        },
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # Create package
    manager.create_package("pkg-web", "Web Stack")
    packages = manager.get_all_packages()
    assert "pkg-web" in packages
    assert packages["pkg-web"]["name"] == "Web Stack"

    # Duplicate create raises ValueError
    with pytest.raises(ValueError, match="already exists"):
        manager.create_package("pkg-web", "Duplicate Web Stack")

    # Update package
    manager.update_package_metadata("pkg-web", {"description": "Web reverse proxy"})
    packages_updated = manager.get_all_packages()
    assert packages_updated["pkg-web"]["description"] == "Web reverse proxy"

    # Update nonexistent package
    with pytest.raises(ValueError, match="Package not found"):
        manager.update_package_metadata("nonexistent", {"description": "Fail"})

    # Delete package in use raises ValueError
    with pytest.raises(ValueError, match="components are still assigned"):
        manager.delete_package("pkg-web")

    # Create unused package and delete it
    manager.create_package("pkg-unused", "Unused Stack")
    assert "pkg-unused" in manager.get_all_packages()
    manager.delete_package("pkg-unused")
    assert "pkg-unused" not in manager.get_all_packages()


def test_get_all_components_include_variables(tmp_path):
    """Test get_all_components with include_variables=True."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    comp_dir = templates_dir / "vaultwarden"
    config_dir = comp_dir / "template-config"
    config_dir.mkdir(parents=True)

    vars_content = {
        "variables": [{"id": "SIGNUPS_ALLOWED", "type": "boolean", "default": True}]
    }
    (config_dir / "variables.json").write_text(
        json.dumps(vars_content), encoding="utf-8"
    )

    meta_data = {
        "components": {
            "vaultwarden": {"name": "Vaultwarden"},
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    comps = manager.get_all_components(include_variables=True)
    comp, *_ = comps
    assert comp["id"] == "vaultwarden"
    assert len(comp["required_variables"]) == 1
    var_def, *_ = comp["required_variables"]
    assert var_def["id"] == "SIGNUPS_ALLOWED"


def test_update_component_matrix_missing(tmp_path):
    """Test update_component_matrix_constraint on non-existent component."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    meta_path.write_text(json.dumps({"components": {}}), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )
    with pytest.raises(KeyError, match="Component 'missing' not found"):
        manager.update_component_matrix_constraint("missing")


def test_validate_component_configuration_violations(tmp_path):
    """Test validation errors for invalid YAML, nested pull_policy, and naming."""
    manager = ComponentManager(
        templates_path=str(tmp_path), metadata_file_path=str(tmp_path / "meta.json")
    )

    # Invalid YAML
    with pytest.raises(ValueError, match="YAML Parsing Failed"):
        manager.validate_component_configuration("test", ": invalid: : yaml", [])

    # Nested pull_policy inside build
    yaml_nested_pull = (
        "services:\n"
        "  mysvc:\n"
        "    build:\n"
        "      context: .\n"
        "      pull_policy: always\n"
    )
    with pytest.raises(ValueError, match="nested inside the 'build' block"):
        manager.validate_component_configuration("test", yaml_nested_pull, [])

    # Container name missing prefix
    yaml_bad_name = (
        "services:\n" "  mysvc:\n" "    container_name: wrong_prefix_container\n"
    )
    with pytest.raises(ValueError, match="Naming Violation"):
        manager.validate_component_configuration("test", yaml_bad_name, [])


def test_validate_metadata_conflicts(tmp_path):
    """Test validation of metadata conflicts with self and non-existent IDs."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    meta_data = {
        "components": {
            "pihole": {"name": "Pi-hole"},
            "adguard": {"name": "AdGuard"},
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # Self-conflict
    with pytest.raises(ValueError, match="Self-Conflict Error"):
        manager.validate_metadata_conflicts("pihole", ["pihole"])

    # Non-existent conflict
    with pytest.raises(ValueError, match="Non-Existent ID Error"):
        manager.validate_metadata_conflicts("pihole", ["unknown_service"])

    # Valid conflict
    manager.validate_metadata_conflicts("pihole", ["adguard"])


def test_create_component_duplicate_and_update_errors(tmp_path):
    """Test duplicate component creation and metadata update validation."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    meta_data = {
        "components": {
            "existing": {"name": "Existing", "has_ui": False},
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # Duplicate create raises ValueError
    with pytest.raises(ValueError, match="already exists"):
        manager.create_component("existing", "Existing")

    # Update nonexistent raises KeyError
    with pytest.raises(KeyError, match="not found"):
        manager.update_component_metadata("nonexistent", {"name": "Fail"})

    # Update with has_ui=True but missing ui_port_variable raises ValueError
    with pytest.raises(ValueError, match="ui_port_variable.*required"):
        manager.update_component_metadata(
            "existing", {"has_ui": True, "ui_port_variable": ""}
        )

    # Mark tested on nonexistent raises KeyError
    with pytest.raises(KeyError, match="not found"):
        manager.mark_component_tested("nonexistent")

    # Update group on nonexistent raises KeyError
    with pytest.raises(KeyError, match="not found"):
        manager.update_component_group("nonexistent", "group-1")


def test_group_ordering_and_deletion(tmp_path):
    """Test group ordering, renaming, and safe deletion."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    meta_data = {
        "_njorddeploy": {
            "group_order": ["grp_a", "grp_b"],
            "group_rules": {
                "grp_a": {"name": "Group A", "is_exclusive": False},
                "grp_b": {"name": "Group B", "is_exclusive": True},
            },
            "components_order": ["comp2", "comp1"],
        },
        "components": {
            "comp1": {"name": "Comp 1", "group": "grp_a"},
            "comp2": {"name": "Comp 2", "group": "grp_b"},
        },
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # Master order sort
    sorted_comps = manager.sort_components_by_master_order(["comp1", "comp2"])
    first, second, *_ = sorted_comps
    assert first == "comp2"
    assert second == "comp1"

    # Update group and components order
    manager.update_group_order(["grp_b", "grp_a"])
    assert manager.get_njorddeploy_meta()["group_order"] == ["grp_b", "grp_a"]
    manager.update_components_order(["comp1", "comp2"])
    assert manager.get_njorddeploy_meta()["components_order"] == ["comp1", "comp2"]

    # Delete group in use raises ValueError
    with pytest.raises(ValueError, match="still in use"):
        manager.delete_group("grp_a")

    # Rename nonexistent group raises ValueError
    with pytest.raises(ValueError, match="Group 'missing' not found"):
        manager.rename_group("missing", "New Name")

    # Rename existing group
    manager.rename_group("grp_a", "Renamed Group A")
    assert (
        manager.get_njorddeploy_meta()["group_rules"]["grp_a"]["name"]
        == "Renamed Group A"
    )

    # Reassign comp2 and delete grp_b
    manager.update_component_group("comp2", "grp_a")
    manager.delete_group("grp_b")
    assert "grp_b" not in manager.get_njorddeploy_meta()["group_rules"]
    assert "grp_b" not in manager.get_njorddeploy_meta()["group_order"]

    # Delete component
    with pytest.raises(KeyError, match="not found"):
        manager.delete_component("nonexistent")

    manager.delete_component("comp1")
    assert "comp1" not in manager.get_njorddeploy_meta()["components_order"]


def test_render_component_template_advanced_and_fallbacks(tmp_path):
    """Test render_component_template missing, fallback replacements, and errors."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    comp_dir = templates_dir / "media_server"
    comp_dir.mkdir()
    config_sub = comp_dir / "template-config"
    config_sub.mkdir()

    compose_tmpl = (
        "services:\n"
        "  media_server:\n"
        "    image: media:latest\n"
        "    volumes:\n"
        "      - {{ CONFIG_BASE_PATH }}/media:/config\n"
        "      - {{ STORAGE_BASE_PATH }}/media:/storage\n"
        "      - {{ '{{ CONFIG_BASE_PATH }}' }}/sub:/sub\n"
        "      - {{ '{{ STORAGE_BASE_PATH }}' }}/sub2:/sub2\n"
    )
    (comp_dir / "docker-compose.template.yml").write_text(
        compose_tmpl, encoding="utf-8"
    )

    vars_data = {
        "variables": [
            {"id": "MEDIA_PORT", "type": "port", "default": 8096},
            {
                "id": "PORT_EXCLUDE",
                "type": "port_exclude_traefik",
                "default": 8096,
            },
        ]
    }
    (config_sub / "variables.json").write_text(json.dumps(vars_data), encoding="utf-8")

    meta_data = {
        "components": {
            "media_server": {
                "name": "Media Server",
                "has_traefik_support": True,
                "traefik_internal_port": 8096,
                "required_variables": [
                    {
                        "id": "PORT_EXCLUDE",
                        "type": "port_exclude_traefik",
                        "default": 8096,
                    }
                ],
            }
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # 1. Missing component returns empty services dict
    missing_rendered = manager.render_component_template("nonexistent", {})
    assert missing_rendered == "services: {}"

    # 2. Render with excluded port (traefik labels should be suppressed)
    context = {
        "TRAEFIK_HOST": "media",
        "FQDN_SUFFIX": "njord.local",
    }
    rendered = manager.render_component_template("media_server", context)
    assert "traefik.enable=true" not in rendered
    assert "../njorddeploy_data/media:/config" in rendered

    # 3. Render template error handling
    bad_dir = templates_dir / "broken"
    bad_dir.mkdir()
    (bad_dir / "docker-compose.template.yml").write_text(
        "{% invalid jinja syntax %", encoding="utf-8"
    )
    meta_data["components"]["broken"] = {"name": "Broken"}
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    err_rendered = manager.render_component_template("broken", {})
    assert "# ERROR: Template rendering failed" in err_rendered


def test_component_manager_crud_and_wrappers(tmp_path):
    """Test ComponentManager CRUD methods, cache, and wrappers."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    meta_data = {
        "_njorddeploy": {
            "group_order": ["default_grp"],
            "group_rules": {"default_grp": {"name": "Default"}},
        },
        "components": {},
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # load and save metadata wrappers
    data = manager.load_metadata()
    assert "_njorddeploy" in data
    manager.save_metadata()

    # create_component
    manager.create_component("new_svc", "New Service")
    comp = manager.get_component_details("new_svc")
    assert comp is not None
    assert comp["name"] == "New Service"

    # get_docker_service_name
    assert manager.get_docker_service_name("new_svc") == "new_svc"
    assert manager.get_docker_service_name("missing_svc") == "missing_svc"

    # update_component_metadata with a new group
    manager.update_component_metadata(
        "new_svc", {"group": "custom_grp", "description": "Custom Group Service"}
    )
    meta = manager.get_njorddeploy_meta()
    assert "custom_grp" in meta["group_rules"]
    assert "custom_grp" in meta["group_order"]

    # mark_component_tested
    manager.mark_component_tested("new_svc", "stable")
    comp_tested = manager.get_component_details("new_svc")
    assert comp_tested["test_status"] == "stable"

    # update_component_variables and template content
    manager.update_component_variables(
        "new_svc", {"variables": [{"id": "PORT", "default": 80}]}
    )
    manager.update_component_template_content(
        "new_svc", "services:\n  new_svc:\n    image: test:latest\n"
    )
    content = manager.get_component_template_content("new_svc")
    assert "test:latest" in content

    # _get_component_config_path
    cfg_path = manager._get_component_config_path("new_svc")
    assert cfg_path.name == "template-config"


def test_generate_deployment_artifacts_comprehensive(tmp_path):
    """Test deployment artifacts with custom engines, network dicts, and env."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    comp_dir = templates_dir / "complex_svc"
    comp_dir.mkdir()

    # Compose template with dict labels, custom network, and jinja escape
    compose_tmpl = (
        "version: '3.8'\n"
        "services:\n"
        "  complex_svc:\n"
        "    image: test/complex:latest\n"
        "    labels:\n"
        "      custom.key: custom_value\n"
        "    networks:\n"
        "      - custom_net\n"
        "volumes:\n"
        "  complex_vol:\n"
        "networks:\n"
        "  custom_net:\n"
        "    driver: bridge\n"
    )
    (comp_dir / "docker-compose.template.yml").write_text(
        compose_tmpl, encoding="utf-8"
    )

    meta_data = {
        "components": {
            "complex_svc": {
                "name": "Complex Service",
            }
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    selected = [{"id": "complex_svc", "name": "Complex Service"}]
    global_vars = {
        "CONTAINER_ENGINE": "podman",
        "TARGET_MODE": "lxc",
        "SCALAR_VAR": "hello",
        "NON_SCALAR_VAR": {"nested": "value"},
    }
    out_dir = tmp_path / "deploy_out"

    manager.generate_deployment_artifacts(selected, global_vars, out_dir)

    compose_file = out_dir / "docker-compose.yml"
    assert compose_file.exists()
    with open(compose_file, "r", encoding="utf-8") as f:
        compose_obj = yaml.safe_load(f)

    assert compose_obj["version"] == "3.8"
    svc = compose_obj["services"]["complex_svc"]
    assert svc["labels"]["njorddeploy.component.id"] == "complex_svc"
    assert "custom_net" in compose_obj["networks"]
    assert "complex_vol" in compose_obj["volumes"]

    env_file = out_dir / ".env"
    env_text = env_file.read_text(encoding="utf-8")
    assert "SCALAR_VAR=hello" in env_text
    assert "NON_SCALAR_VAR" not in env_text


def test_render_traefik_labels_and_deployment_errors(tmp_path):
    """Test generating Traefik labels and handling template/YAML errors."""
    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    comp_dir = templates_dir / "traefik_svc"
    comp_dir.mkdir()
    cfg_dir = comp_dir / "template-config"
    cfg_dir.mkdir()

    # Broken config template to trigger config rendering error
    (cfg_dir / "bad.conf").write_text("{% broken jinja", encoding="utf-8")

    # Template with traefik labels placeholder
    tmpl_content = (
        "services:\n"
        "  traefik_svc:\n"
        "    image: traefik:latest\n"
        "    labels:\n"
        "{{ traefik_labels_yaml }}\n"
    )
    (comp_dir / "docker-compose.template.yml").write_text(
        tmpl_content, encoding="utf-8"
    )

    meta_data = {
        "components": {
            "traefik_svc": {
                "name": "Traefik Svc",
                "has_traefik_support": True,
                "traefik_internal_port": 8080,
                "config_templates": {"bad.conf": "traefik/bad.conf"},
            }
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # 1. Render template with Traefik labels
    context = {"TRAEFIK_HOST": "myproxy", "FQDN_SUFFIX": "example.com"}
    rendered = manager.render_component_template("traefik_svc", context)
    assert "traefik.enable=true" in rendered
    assert "traefik.http.routers.traefik_svc.rule" in rendered

    # 2. Generate deployment artifacts with config template error and invalid YAML
    out_dir = tmp_path / "out_err"
    manager.generate_deployment_artifacts(
        selected_components_data=[
            {
                "id": "traefik_svc",
                "config_templates": {"bad.conf": "traefik/bad.conf"},
            }
        ],
        global_vars=context,
        output_path=out_dir,
    )

    # 3. Invalid YAML handling in rendered template
    bad_yaml_dir = templates_dir / "bad_yaml_svc"
    bad_yaml_dir.mkdir()
    (bad_yaml_dir / "docker-compose.template.yml").write_text(
        "services: [invalid yaml structure: {", encoding="utf-8"
    )
    meta_data["components"]["bad_yaml_svc"] = {"name": "Bad YAML"}
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    manager.generate_deployment_artifacts(
        selected_components_data=[{"id": "bad_yaml_svc"}],
        global_vars={},
        output_path=tmp_path / "out_bad_yaml",
    )


def test_component_manager_additional_coverage(tmp_path):
    """Verify non-dict services, invalid ports, unmapped IDs, and scalar templates."""
    from unittest.mock import patch

    meta_path = tmp_path / "metadata.json"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    caddy_dir = templates_dir / "caddy"
    caddy_tc = caddy_dir / "template-config"
    caddy_tc.mkdir(parents=True, exist_ok=True)
    (caddy_dir / "docker-compose.template.yml").write_text("services: {}\n")
    (caddy_tc / "variables.json").write_text(
        json.dumps([{"type": "port_exclude_traefik", "id": "PORT_EX"}]),
        encoding="utf-8",
    )

    meta_data = {
        "components": {
            "caddy": {
                "name": "Caddy",
                "has_traefik_support": True,
                "traefik_internal_port": 80,
                "required_variables": [
                    {"type": "port_exclude_traefik", "id": "PORT_EX"}
                ],
            }
        }
    }
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")
    mgr = ComponentManager(
        templates_path=str(templates_dir), metadata_file_path=str(meta_path)
    )

    # 1. Non-dict service in validate_component_configuration (line 259)
    mgr.validate_component_configuration(
        "caddy", "services:\n  bad_svc: 'not a dict'\n", []
    )

    # 2. Non-dict variables raw in update_component_variables (line 453)
    with patch.object(mgr.reader, "get_component_variables_raw", return_value=None):
        with patch.object(mgr.writer, "save_component_variables_raw"):
            mgr.update_component_variables("caddy", {"variables": []})

    # 3. Non-integer port_exclude_traefik value (lines 599-600)
    mgr.render_component_template("caddy", {"PORT_EX": "not_an_int"})

    # 4. Unmapped ID in sort_components_by_master_order (line 698)
    out_dir = tmp_path / "artifacts"
    with patch.object(
        mgr, "sort_components_by_master_order", return_value=["unmapped_id"]
    ):
        mgr.generate_deployment_artifacts([{"id": "caddy"}], {}, out_dir)

    # 5. Scalar rendered template (line 741)
    with patch.object(
        mgr, "render_component_template", return_value="just a scalar string"
    ):
        mgr.generate_deployment_artifacts([{"id": "caddy"}], {}, out_dir)

    # 6. Non-dict service definition in rendered compose (line 754)
    with patch.object(
        mgr, "render_component_template", return_value="services:\n  bad: not_dict\n"
    ):
        mgr.generate_deployment_artifacts([{"id": "caddy"}], {}, out_dir)


def test_component_manager_private_overlay_safety(tmp_path):
    """
    Test that private overlay components are loaded but never written
    to public metadata.
    """
    pub_meta = tmp_path / "public_meta.json"
    pub_meta.write_text(
        json.dumps({"components": {"nginx": {"name": "Nginx"}}}),
        encoding="utf-8",
    )
    pub_templates = tmp_path / "public_templates"
    pub_templates.mkdir()

    priv_meta = tmp_path / "private_meta.json"
    priv_meta.write_text(
        json.dumps(
            {
                "components": {
                    "nedfact": {
                        "name": "NedFact",
                        "private": True,
                        "image_name": "git.piselfhosting.com/hvhoek/nedfact",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    priv_templates = tmp_path / "private_templates"
    priv_comp = priv_templates / "nedfact"
    priv_comp.mkdir(parents=True)
    priv_tpl = priv_comp / "docker-compose.template.yml"
    priv_tpl.write_text(
        "services:\n  nedfact:\n    image: nedfact:latest\n", encoding="utf-8"
    )

    mgr = ComponentManager(
        templates_path=str(pub_templates),
        metadata_file_path=str(pub_meta),
        private_templates_path=str(priv_templates),
        private_metadata_path=str(priv_meta),
    )

    all_comps = mgr.get_all_components()
    comp_ids = [c["id"] for c in all_comps]
    assert "nginx" in comp_ids
    assert "nedfact" in comp_ids

    # Trigger save_metadata and verify nedfact did not leak into public_meta.json
    mgr.save_metadata()
    saved_public = json.loads(pub_meta.read_text(encoding="utf-8"))
    assert "nginx" in saved_public["components"]
    assert "nedfact" not in saved_public["components"]
