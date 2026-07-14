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
