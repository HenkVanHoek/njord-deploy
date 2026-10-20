# tests/test_artifact_generator.py
from unittest.mock import MagicMock

import yaml

from src.managers.artifact_generator import ArtifactGenerator


def test_generator_creates_valid_compose_with_traefik(tmp_path):
    """
    Test if the generator correctly renders templates and injects Traefik labels.
    """
    # Setup: Mock the ComponentReader
    mock_reader = MagicMock()

    # Define what the reader returns for metadata
    mock_reader.get_component_details.return_value = {
        "has_traefik_support": True,
        "docker_service_name": "web-svc",
        "traefik_domain": "app.local",
        "traefik_port": 8080,
    }

    # Create a dummy template file
    template_dir = tmp_path / "templates" / "my-app"
    template_dir.mkdir(parents=True)
    template_file = template_dir / "docker-compose.template.yml"
    template_file.write_text(
        "services:\n  web-svc:\n    image: {{ variables.image_name }}", encoding="utf-8"
    )
    mock_reader.get_template_path.return_value = template_file

    # Initialize Generator
    generator = ArtifactGenerator(reader=mock_reader)

    # Execute
    output_dir = tmp_path / "output"
    user_variables = {"my-app": {"image_name": "nginx:alpine"}}

    success = generator.create_artifacts(
        out_path=output_dir, components=["my-app"], user_variables=user_variables
    )

    # Verify
    assert success is True
    compose_path = output_dir / "docker-compose.yml"
    assert compose_path.exists()

    # Parse resulting YAML to check content
    with open(compose_path, "r", encoding="utf-8") as f:
        generated_data = yaml.safe_load(f)

    # Check Jinja2 rendering
    service = generated_data["services"]["web-svc"]
    assert service["image"] == "nginx:alpine"

    # Check Traefik label injection
    labels = service["labels"]
    assert labels["traefik.enable"] == "true"
    assert "app.local" in labels["traefik.http.routers.web-svc.rule"]
    assert labels["traefik.http.services.web-svc.loadbalancer.server.port"] == "8080"


def test_generator_skips_missing_component_and_handles_write_error(tmp_path):
    """Test skipping when component metadata/template missing and IOError handling."""
    mock_reader = MagicMock()
    mock_reader.get_component_details.return_value = None
    mock_reader.get_template_path.return_value = tmp_path / "nonexistent.yml"

    generator = ArtifactGenerator(reader=mock_reader)
    output_dir = tmp_path / "output"

    # Component missing: should skip and write empty services compose
    success = generator.create_artifacts(
        out_path=output_dir, components=["missing-app"], user_variables={}
    )
    assert success is True

    # Component without traefik support
    mock_reader.get_component_details.return_value = {
        "has_traefik_support": False,
        "docker_service_name": "simple-svc",
    }
    tmpl = tmp_path / "simple.yml"
    tmpl.write_text("services:\n  simple-svc:\n    image: redis\n")
    mock_reader.get_template_path.return_value = tmpl

    success_no_traefik = generator.create_artifacts(
        out_path=output_dir, components=["simple-app"], user_variables={}
    )
    assert success_no_traefik is True

    # IOError on write
    from unittest.mock import patch

    with patch("builtins.open", side_effect=IOError("Disk write failed")):
        err_res = generator.create_artifacts(
            out_path=output_dir, components=["simple-app"], user_variables={}
        )
        assert err_res is False
