# tests/test_component_manager.py
import json

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
