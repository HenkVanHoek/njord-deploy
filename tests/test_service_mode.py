import pytest

from configurator_app.app import create_app
from configurator_app.openapi import get_openapi_spec
from managers.ssh_manager import SSHManager
from run_service import initialize_service_environment
from utils.resource_utils import (
    get_app_data_dir,
    get_project_version,
    get_ssh_key_path,
    is_server_mode,
)


@pytest.fixture
def app():
    """Create test application fixture."""
    app = create_app({"TESTING": True})
    return app


@pytest.fixture
def client(app):
    """Test client fixture."""
    return app.test_client()


def test_resource_utils_environment_overrides(tmp_path, monkeypatch):
    """Verifies that NJORD_DATA_DIR and NJORD_SSH_KEY_PATH override paths."""
    custom_data = tmp_path / "custom_data"
    custom_key = tmp_path / "custom_keys" / "id_njord"

    monkeypatch.setenv("NJORD_DATA_DIR", str(custom_data))
    monkeypatch.setenv("NJORD_SSH_KEY_PATH", str(custom_key))
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")

    assert get_app_data_dir() == custom_data.resolve()
    assert get_ssh_key_path() == custom_key.resolve()
    assert is_server_mode() is True

    monkeypatch.setenv("NJORD_SERVER_MODE", "false")
    assert is_server_mode() is False


def test_health_endpoints(client, monkeypatch):
    """Verifies /health, /api/health, and /api/v1/health endpoints."""
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")

    for endpoint in ["/health", "/api/health", "/api/v1/health"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        assert data["status"] == "ok"
        assert data["version"] == get_project_version()
        assert data["mode"] == "service"
        assert isinstance(data["services_catalog"], int)
        assert data["services_catalog"] >= 0
        assert "timestamp" in data


def test_health_endpoint_standalone_mode(client, monkeypatch):
    """Verifies health endpoint reflects standalone mode when env unset."""
    monkeypatch.delenv("NJORD_SERVER_MODE", raising=False)

    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["mode"] == "standalone"


def test_ssh_manager_respects_custom_key_path(tmp_path, monkeypatch):
    """Verifies that SSHManager persists key in custom NJORD_SSH_KEY_PATH."""
    custom_key_path = tmp_path / "keys" / "custom_ed25519"
    monkeypatch.setenv("NJORD_SSH_KEY_PATH", str(custom_key_path))

    mgr = SSHManager(hostname="127.0.0.1", username="testuser", password="")
    key = mgr.get_ssh_key()
    assert key is not None
    assert custom_key_path.exists()

    pub_str = mgr.get_public_key_string()
    assert pub_str.startswith("ssh-ed25519 ")


def test_initialize_service_environment(tmp_path, monkeypatch):
    """Verifies that initialize_service_environment sets up folders and keys."""
    custom_data = tmp_path / "njord_service_data"
    monkeypatch.setenv("NJORD_DATA_DIR", str(custom_data))
    monkeypatch.delenv("NJORD_SSH_KEY_PATH", raising=False)

    data_dir, pub_key = initialize_service_environment()
    assert data_dir == custom_data.resolve()
    assert data_dir.exists()
    assert (data_dir / "id_ed25519_njorddeploy").exists()
    assert (data_dir / "id_ed25519_njorddeploy.pub").exists()
    assert pub_key.startswith("ssh-ed25519 ")


def test_openapi_spec_includes_health():
    """Verifies that OpenAPI spec documents the /api/health path."""
    spec = get_openapi_spec()
    assert "/api/health" in spec["paths"]
    assert "get" in spec["paths"]["/api/health"]
