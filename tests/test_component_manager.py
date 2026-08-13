# tests/test_component_manager.py
import json

import pytest
import yaml

from src.managers.component_manager import ComponentManager


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
