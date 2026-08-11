# tests/configurator_app/test_engine_routes.py
import json
import os
from unittest.mock import patch

import pytest

from configurator_app.app import create_app


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    orig_env = os.environ.get("CONTAINER_ENGINE")
    yield
    if orig_env is not None:
        os.environ["CONTAINER_ENGINE"] = orig_env
    else:
        os.environ.pop("CONTAINER_ENGINE", None)


@pytest.fixture
def client():
    with (
        patch("src.configurator_app.app.ComponentManager"),
        patch("src.configurator_app.app.SetupManager"),
        patch("src.configurator_app.app.NodeScanner"),
        patch("src.configurator_app.app.DeploymentManager"),
    ):
        app = create_app({"TESTING": True, "SECRET_KEY": "test-key"})
        return app.test_client()


def test_get_engine_status(client, monkeypatch):
    monkeypatch.setenv("CONTAINER_ENGINE", "docker")
    res = client.get("/api/engine-status")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["engine"] == "docker"
    assert data["is_docker"] is True
    assert "podman" in data["supported_engines"]


def test_switch_engine(client):
    res = client.post(
        "/api/engine-switch",
        data=json.dumps({"engine": "podman"}),
        content_type="application/json",
    )
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert data["engine"] == "podman"

    # Test invalid engine
    res_inv = client.post(
        "/api/engine-switch",
        data=json.dumps({"engine": "invalid_engine"}),
        content_type="application/json",
    )
    assert res_inv.status_code == 400


def test_validate_repo_route(client):
    # Empty url
    res = client.post(
        "/api/validate-repo",
        data=json.dumps({"url": ""}),
        content_type="application/json",
    )
    assert res.status_code == 400

    # Local mode
    res_loc = client.post(
        "/api/validate-repo",
        data=json.dumps({"url": "none"}),
        content_type="application/json",
    )
    assert res_loc.status_code == 200
    data = json.loads(res_loc.data)
    assert data["valid"] is True


def test_first_run_status_route(client):
    res = client.get("/api/first-run-status")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "first_run" in data
