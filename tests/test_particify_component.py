"""Unit tests verifying the Particify multi-container component stack."""

import tempfile
from pathlib import Path
from typing import Any, Dict

import yaml

from src.managers.component_manager import ComponentManager
from src.managers.sync_manager import SyncManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "component_templates"
METADATA_FILE = PROJECT_ROOT / "config" / "components_metadata.json"

EXPECTED_SERVICES = {
    "particify",
    "arsnova-web",
    "arsnova-backend-core",
    "arsnova-http-gateway",
    "arsnova-ws-gateway",
    "arsnova-auth-service",
    "arsnova-comment-service",
    "arsnova-formatting-service",
    "particify-couchdb",
    "particify-postgres-auth",
    "particify-postgres-comment",
    "particify-rabbitmq",
}


def _make_component_manager() -> ComponentManager:
    return ComponentManager(
        templates_path=str(TEMPLATES_DIR),
        metadata_file_path=str(METADATA_FILE),
    )


def test_particify_metadata_contract() -> None:
    """Particify metadata adheres to NjordDeploy Data Contracts."""
    cm = _make_component_manager()
    details = cm.get_component_details("particify")
    assert details is not None
    assert details["name"] == "Particify"
    assert details["docker_service_name"] == "particify"
    assert details["has_ui"] is True
    assert details["ui_port_variable"] == "PARTICIFY_WEB_PORT"
    assert details["has_configuration"] is True
    assert details["has_traefik_support"] is True
    assert details["traefik_internal_port"] == 80
    assert details["project_url"] == "https://particify.de"

    supported_matrix = cm.get_supported_matrix("particify")
    assert "docker" in supported_matrix["engines"]
    assert "lxc" in supported_matrix["modes"]
    assert "AMD64" in supported_matrix["notes"]


def test_particify_header_and_validation() -> None:
    """Particify template passes ComponentManager and SyncManager gates."""
    cm = _make_component_manager()
    template_content = cm.get_component_template_content("particify")
    variables = cm.reader.get_component_variables("particify")

    cm.validate_component_configuration("particify", template_content, variables)
    sync_mgr = SyncManager(METADATA_FILE, TEMPLATES_DIR)
    assert sync_mgr.validate_metadata_header(
        "particify"
    ), "Invalid Particify template metadata header."


def test_particify_render_and_network_isolation() -> None:
    """Rendered docker-compose.yml contains all 12 services with network isolation."""
    cm = _make_component_manager()
    details = cm.get_component_details("particify")
    assert details is not None

    custom_vars: Dict[str, Any] = {
        "PARTICIFY_WEB_PORT": "8123",
        "PARTICIFY_HOSTNAME": "poll.example.org",
        "PARTICIFY_JWT_SECRET": "TestJwtSecretValueWithMoreThan32Characters!",
        "PARTICIFY_DB_PASSWORD": "TestDbPasswordValue123!",
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir)
        cm.generate_deployment_artifacts([details], custom_vars, out_path)
        compose_text = (out_path / "docker-compose.yml").read_text(encoding="utf-8")
        compose = yaml.safe_load(compose_text)

    services = compose.get("services", {})
    assert set(services.keys()) == EXPECTED_SERVICES

    # Every container must follow the mandatory njorddeploy- prefix
    for svc_name, svc_def in services.items():
        container_name = svc_def.get("container_name", "")
        assert container_name.startswith(
            "njorddeploy-"
        ), f"Service '{svc_name}' container_name '{container_name}' lacks prefix."
        assert "njorddeploy.component.id=particify" in svc_def.get("labels", [])

    # Proxy bridges njorddeploy_net and particify_internal; backend stays isolated
    proxy = services["particify"]
    assert set(proxy["networks"]) == {"njorddeploy_net", "particify_internal"}
    assert "8123:80" in proxy["ports"]

    for svc_name, svc_def in services.items():
        if svc_name != "particify":
            assert svc_def["networks"] == ["particify_internal"]

    # Credentials must propagate to DB and backend services; RabbitMQ stays isolated
    assert (
        services["particify-couchdb"]["environment"]["COUCHDB_PASSWORD"]
        == "TestDbPasswordValue123!"
    )
    assert (
        services["particify-postgres-auth"]["environment"]["POSTGRES_PASSWORD"]
        == "TestDbPasswordValue123!"
    )
    assert (
        services["particify-postgres-comment"]["environment"]["POSTGRES_PASSWORD"]
        == "TestDbPasswordValue123!"
    )
    assert "ports" not in services["particify-rabbitmq"]
    assert services["particify-rabbitmq"]["networks"] == ["particify_internal"]
    assert (
        services["arsnova-backend-core"]["environment"]["SECURITY_JWT_SECRET"]
        == "TestJwtSecretValueWithMoreThan32Characters!"
    )
    assert (
        services["arsnova-backend-core"]["environment"][
            "SECURITY_AUTHENTICATIONPROVIDERS_GUEST_ALLOWEDROLES"
        ]
        == "participant"
    )
    assert (
        services["arsnova-backend-core"]["environment"][
            "SECURITY_AUTHENTICATIONPROVIDERS_REGISTERED_TITLE"
        ]
        == "Particify"
    )

    networks = compose.get("networks", {})
    assert "njorddeploy_net" in networks
    assert "particify_internal" in networks
    assert networks["particify_internal"]["external"] is False
