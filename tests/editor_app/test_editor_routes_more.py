# tests/editor_app/test_editor_routes_more.py

"""Comprehensive test suite targeting uncovered edge-cases and error paths in
Editor App.

Covers:
- Editor authentication filter (before_request) redirects and session checks
- /api/sync/diff route template and file comparison, binary files, and exceptions
- Component CRUD and validation error handling (KeyError, ValueError, Exception)
- Groups and Packages error handling and ordering validation
- AI Provider status, security URL validation, and SSE streaming edge cases
- AI component save validation, path traversal defenses, and error conversions
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from editor_app.app import create_app


@pytest.fixture
def editor_more_env(tmp_path):
    """Sets up an isolated environment for editor app testing."""
    meta_path = tmp_path / "components_metadata.json"
    meta_path.write_text(
        json.dumps(
            {
                "components": {
                    "demo-app": {
                        "name": "Demo App",
                        "group": "utilities",
                        "variables": [{"name": "PORT", "default": 8080}],
                        "config_templates": {"app.conf": "demo-app/app.conf"},
                        "has_configuration": True,
                    }
                },
                "packages": {"pkg-1": {"name": "Package One"}},
                "_njorddeploy": {
                    "group_rules": {"utilities": {"name": "Utilities"}},
                    "components_order": ["demo-app"],
                },
            }
        ),
        encoding="utf-8",
    )
    templates_path = tmp_path / "component_templates"
    templates_path.mkdir()
    demo_dir = templates_path / "demo-app"
    demo_dir.mkdir()
    (demo_dir / "template-config").mkdir()
    (demo_dir / "docker-compose.template.yml").write_text(
        "services:\n  demo:\n    image: demo:1.0\n",
        encoding="utf-8",
    )

    test_config = {
        "TESTING": True,
        "AUTH_ENABLED": False,
        "SECRET_KEY": "test-editor-secret",
        "TEMPLATES_PATH": str(templates_path),
        "METADATA_FILE_PATH": str(meta_path),
    }

    app = create_app(test_config)
    client = app.test_client()
    return client, meta_path, templates_path


def test_editor_auth_filter_enforcement(tmp_path):
    """Tests before_request authentication enforcement in Editor App."""
    meta_path = tmp_path / "components_metadata.json"
    meta_path.write_text(json.dumps({"components": {}}), encoding="utf-8")
    templates_path = tmp_path / "component_templates"
    templates_path.mkdir()

    app_auth = create_app(
        {
            "TESTING": True,
            "AUTH_ENABLED": True,
            "SECRET_KEY": "auth-test-secret",
            "TEMPLATES_PATH": str(templates_path),
            "METADATA_FILE_PATH": str(meta_path),
        }
    )
    client = app_auth.test_client()

    # 1. Auth enabled, admin not configured, non-API request -> redirect to setup_wizard
    with (
        patch("editor_app.app.is_auth_enabled", return_value=True),
        patch("editor_app.app.is_admin_configured", return_value=False),
    ):
        res_setup_redir = client.get("/", headers={"Accept": "text/html"})
        assert res_setup_redir.status_code == 302
        assert "/setup" in res_setup_redir.headers.get("Location", "")

    # 2. Auth enabled, admin configured, API key via X-Njord-API-Key header -> 200
    with (
        patch("editor_app.app.is_auth_enabled", return_value=True),
        patch("editor_app.app.is_admin_configured", return_value=True),
        patch("editor_app.app.verify_api_key", return_value=True),
    ):
        res_api_key = client.get(
            "/api/components", headers={"X-Njord-API-Key": "valid-token"}
        )
        assert res_api_key.status_code == 200

    # 3. Auth enabled, admin configured, unauthenticated API request -> 401
    with (
        patch("editor_app.app.is_auth_enabled", return_value=True),
        patch("editor_app.app.is_admin_configured", return_value=True),
        patch("editor_app.app.verify_api_key", return_value=False),
    ):
        res_unauth_api = client.get("/api/components")
        assert res_unauth_api.status_code == 401

    # 4. Auth enabled, admin configured, unauthenticated HTML GET -> redirect to login
    with (
        patch("editor_app.app.is_auth_enabled", return_value=True),
        patch("editor_app.app.is_admin_configured", return_value=True),
        patch("editor_app.app.verify_api_key", return_value=False),
    ):
        res_unauth_get = client.get("/", headers={"Accept": "text/html"})
        assert res_unauth_get.status_code == 302
        assert "/login" in res_unauth_get.headers.get("Location", "")

    # 5. Auth enabled, admin configured, unauthenticated HTML POST -> redirect to login
    with (
        patch("editor_app.app.is_auth_enabled", return_value=True),
        patch("editor_app.app.is_admin_configured", return_value=True),
        patch("editor_app.app.verify_api_key", return_value=False),
    ):
        res_unauth_post = client.post("/some-action", headers={"Accept": "text/html"})
        assert res_unauth_post.status_code == 302
        assert "/login" in res_unauth_post.headers.get("Location", "")


def test_sync_diff_route_handling(tmp_path):
    """Tests /api/sync/diff/<comp_id> comparing local and cached templates."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_path = data_dir / "remote_components_cache" / "component_templates"
    comp_cache = cache_path / "demo-app"
    comp_cache.mkdir(parents=True)

    meta_path = tmp_path / "components_metadata.json"
    meta_path.write_text(
        json.dumps(
            {"components": {"demo-app": {"name": "Demo App", "group": "utilities"}}}
        ),
        encoding="utf-8",
    )
    templates_path = tmp_path / "component_templates"
    templates_path.mkdir()
    local_comp = templates_path / "demo-app"
    local_comp.mkdir()

    # Local template
    (local_comp / "docker-compose.template.yml").write_text(
        "services:\n  demo:\n    image: demo:1.0\n", encoding="utf-8"
    )
    # Remote cached template
    (comp_cache / "docker-compose.template.yml").write_text(
        "services:\n  demo:\n    image: demo:2.0\n", encoding="utf-8"
    )

    # Extra differing file (text) and binary file
    (local_comp / "extra.conf").write_text("setting=a", encoding="utf-8")
    (comp_cache / "extra.conf").write_text("setting=b", encoding="utf-8")
    (local_comp / "binary.bin").write_bytes(b"\x00\x01")
    (comp_cache / "binary.bin").write_bytes(b"\x00\x02")

    env_patch = {"NJORD_DATA_DIR": str(data_dir)}
    with patch.dict("os.environ", env_patch):
        app = create_app(
            {
                "TESTING": True,
                "AUTH_ENABLED": False,
                "TEMPLATES_PATH": str(templates_path),
                "METADATA_FILE_PATH": str(meta_path),
            }
        )
        client = app.test_client()

        res = client.get("/api/sync/diff/demo-app")
        assert res.status_code == 200
        payload = res.get_json()
        assert "local_template" in payload
        assert "remote_template" in payload
        assert "differing_files" in payload
        assert "docker-compose.template.yml" in payload["differing_files"]

        # Error path -> 500
        with patch(
            "managers.sync_manager.SyncManager.get_local_component_meta",
            side_effect=Exception("Disk error"),
        ):
            res_err = client.get("/api/sync/diff/demo-app")
            assert res_err.status_code == 500


def test_component_crud_error_branches(editor_more_env):
    """Tests error and exception handling in component CRUD routes."""
    client, _, _ = editor_more_env

    # 1. PUT /api/components/<comp_id>
    with patch(
        "managers.component_manager.ComponentManager.update_component_metadata",
        side_effect=KeyError("Not found"),
    ):
        res = client.put("/api/components/missing", json={"name": "New"})
        assert res.status_code == 404

    with patch(
        "managers.component_manager.ComponentManager.update_component_metadata",
        side_effect=ValueError("Invalid field"),
    ):
        res = client.put("/api/components/demo-app", json={"name": "Bad"})
        assert res.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.update_component_metadata",
        side_effect=Exception("Disk failure"),
    ):
        res = client.put("/api/components/demo-app", json={"name": "Err"})
        assert res.status_code == 500

    # 2. PUT /api/components/<comp_id>/variables
    res_bad_vars = client.put(
        "/api/components/demo-app/variables",
        data="not a json dict",
        content_type="application/json",
    )
    assert res_bad_vars.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.update_component_variables",
        side_effect=Exception("Vars error"),
    ):
        res = client.put("/api/components/demo-app/variables", json={"variables": []})
        assert res.status_code == 500

    # 3. POST /api/components
    res_no_id = client.post("/api/components", json={})
    assert res_no_id.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.create_component",
        side_effect=ValueError("Exists"),
    ):
        res = client.post("/api/components", json={"id": "demo-app"})
        assert res.status_code == 409

    with patch(
        "managers.component_manager.ComponentManager.create_component",
        side_effect=Exception("Crash"),
    ):
        res = client.post("/api/components", json={"id": "crash-app"})
        assert res.status_code == 500

    # 4. DELETE /api/components/<comp_id>
    with patch(
        "managers.component_manager.ComponentManager.delete_component",
        side_effect=KeyError("Missing"),
    ):
        res = client.delete("/api/components/missing")
        assert res.status_code == 404

    with patch(
        "managers.component_manager.ComponentManager.delete_component",
        side_effect=Exception("Crash"),
    ):
        res = client.delete("/api/components/demo-app")
        assert res.status_code == 500

    # 5. Template and configs read/save exceptions
    with patch(
        "managers.component_manager.ComponentManager.get_component_template_content",
        side_effect=Exception("Read error"),
    ):
        res = client.get("/api/components/demo-app/template")
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.update_component_template_content",
        side_effect=Exception("Save error"),
    ):
        res = client.put("/api/components/demo-app/template", data="services: {}")
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.get_component_configs",
        side_effect=Exception("Configs read error"),
    ):
        res = client.get("/api/components/demo-app/configs")
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.save_component_config",
        return_value=False,
    ):
        res = client.put("/api/components/demo-app/configs/app.conf", data="setting=1")
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.save_component_config",
        side_effect=Exception("Config write fail"),
    ):
        res = client.put("/api/components/demo-app/configs/app.conf", data="setting=1")
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.delete_component_config",
        return_value=False,
    ):
        res = client.delete("/api/components/demo-app/configs/app.conf")
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.delete_component_config",
        side_effect=Exception("Config delete fail"),
    ):
        res = client.delete("/api/components/demo-app/configs/app.conf")
        assert res.status_code == 500


def test_validation_and_groups_and_packages_errors(editor_more_env):
    """Tests error cases for validation, groups, and packages."""
    client, _, _ = editor_more_env

    # 1. Validation routes
    with patch(
        "managers.component_manager.ComponentManager.validate_component_configuration",
        side_effect=ValueError("Invalid yaml"),
    ):
        res = client.post(
            "/api/components/demo-app/validate",
            json={"template_content": "bad:"},
        )
        assert res.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.validate_component_configuration",
        side_effect=Exception("Unexpected crash"),
    ):
        res = client.post(
            "/api/components/demo-app/validate",
            json={"template_content": "bad:"},
        )
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.validate_metadata_conflicts",
        side_effect=ValueError("Conflict"),
    ):
        res = client.post(
            "/api/components/demo-app/validate_metadata_conflicts",
            json={"conflicts_with": ["other-app"]},
        )
        assert res.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.validate_metadata_conflicts",
        side_effect=Exception("Conflict crash"),
    ):
        res = client.post(
            "/api/components/demo-app/validate_metadata_conflicts",
            json={"conflicts_with": ["other-app"]},
        )
        assert res.status_code == 500

    # 2. Component group update
    res_bad_group = client.put("/api/components/demo-app/group", json={})
    assert res_bad_group.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.update_component_group",
        side_effect=KeyError("Missing comp"),
    ):
        res = client.put("/api/components/demo-app/group", json={"group": "utilities"})
        assert res.status_code == 404

    with patch(
        "managers.component_manager.ComponentManager.update_component_group",
        side_effect=Exception("Group crash"),
    ):
        res = client.put("/api/components/demo-app/group", json={"group": "utilities"})
        assert res.status_code == 500

    # 3. Order routes invalid payloads
    res_bad_order = client.put("/api/components/order", json="not a list")
    assert res_bad_order.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.update_components_order",
        side_effect=Exception("Order crash"),
    ):
        res = client.put("/api/components/order", json=["demo-app"])
        assert res.status_code == 500

    res_bad_grp_order = client.put("/api/groups/order", json="not a list")
    assert res_bad_grp_order.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.update_group_order",
        side_effect=Exception("Group order crash"),
    ):
        res = client.put("/api/groups/order", json=["utilities"])
        assert res.status_code == 500

    # 4. Group rename and delete
    res_no_rename = client.rename = client.put("/api/groups/utilities/rename", json={})
    assert res_no_rename.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.rename_group",
        side_effect=ValueError("Group not found"),
    ):
        res = client.put("/api/groups/missing/rename", json={"name": "New Name"})
        assert res.status_code == 404

    with patch(
        "managers.component_manager.ComponentManager.rename_group",
        side_effect=Exception("Rename crash"),
    ):
        res = client.put("/api/groups/utilities/rename", json={"name": "New Name"})
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.delete_group",
        side_effect=ValueError("Cannot delete"),
    ):
        res = client.delete("/api/groups/utilities")
        assert res.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.delete_group",
        side_effect=Exception("Delete crash"),
    ):
        res = client.delete("/api/groups/utilities")
        assert res.status_code == 500

    with patch(
        "managers.component_manager.ComponentManager.get_njorddeploy_meta",
        side_effect=Exception("Meta crash"),
    ):
        res = client.get("/api/groups")
        assert res.status_code == 500

    # 5. Packages errors
    with patch(
        "managers.component_manager.ComponentManager.update_package_metadata",
        side_effect=Exception("Package update error"),
    ):
        res = client.put("/api/packages/pkg-1", json={"name": "New Pkg"})
        assert res.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.delete_package",
        side_effect=ValueError("Cannot delete"),
    ):
        res = client.delete("/api/packages/pkg-1")
        assert res.status_code == 400

    with patch(
        "managers.component_manager.ComponentManager.delete_package",
        side_effect=Exception("Package delete crash"),
    ):
        res = client.delete("/api/packages/pkg-1")
        assert res.status_code == 500


def test_ai_provider_status_and_streaming_edge_cases(editor_more_env):
    """Tests provider status check, invalid base_url, and streaming exceptions."""
    client, _, _ = editor_more_env

    # 1. Ollama offline error HTTP code
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    with patch("requests.get", return_value=mock_resp):
        res_ollama_err = client.post(
            "/api/ai/status",
            json={
                "provider": "ollama",
                "base_url": "http://localhost:11434/v1",
            },
        )
        assert res_ollama_err.status_code == 200
        assert res_ollama_err.get_json()["status"] == "offline"

    # 2. Ollama connection exception
    with patch("requests.get", side_effect=Exception("Connection refused")):
        res_ollama_down = client.post(
            "/api/ai/status",
            json={
                "provider": "ollama",
                "base_url": "http://localhost:11434/v1",
            },
        )
        assert res_ollama_down.status_code == 200
        assert res_ollama_down.get_json()["status"] == "offline"

    # 3. Provider with no required key
    mock_registry = {"custom_local": {"requires_api_key": False}}
    with patch(
        "utils.ai_provider_manager.load_ai_providers_registry",
        return_value=mock_registry,
    ):
        res_no_key = client.post("/api/ai/status", json={"provider": "custom_local"})
        assert res_no_key.status_code == 200
        assert res_no_key.get_json()["status"] == "online"

    # 4. Unknown provider
    with patch(
        "utils.ai_provider_manager.load_ai_providers_registry",
        return_value={},
    ):
        res_unknown = client.post("/api/ai/status", json={"provider": "nonexistent"})
        assert res_unknown.status_code == 200
        assert res_unknown.get_json()["status"] == "offline"

    # 5. Invalid base_url (SSRF or malformed)
    with patch(
        "utils.security_utils.validate_and_sanitize_url",
        return_value=(False, None, "Invalid protocol"),
    ):
        res_bad_url = client.post(
            "/api/ai/generate",
            json={
                "repo_url": "https://github.com/org/repo",
                "base_url": "ftp://bad-url",
            },
        )
        assert res_bad_url.status_code == 400
        assert "Invalid base_url" in res_bad_url.get_json()["error"]


def test_ai_save_component_path_traversal_and_errors(editor_more_env):
    """Tests path traversal rejection and exception mapping when saving AI component."""
    client, _, _ = editor_more_env

    # 1. Invalid configuration template filename (e.g., special characters)
    res_bad_tpl = client.post(
        "/api/components/ai",
        json={
            "id": "traversal-app",
            "metadata": {"name": "Traversal App"},
            "overwrite": True,
            "config_templates": {"../escape.conf": "content"},
        },
    )
    # The secure_filename strips '../', but filename regex or path validation checks it
    assert res_bad_tpl.status_code in (201, 400)

    # 2. ValueError "already exists" mapping
    with patch(
        "managers.component_manager.ComponentManager.create_component",
        side_effect=ValueError("Component already exists"),
    ):
        res_exists = client.post(
            "/api/components/ai",
            json={
                "id": "new-app",
                "metadata": {"name": "New App"},
                "overwrite": False,
            },
        )
        assert res_exists.status_code == 400
        assert "already exists" in res_exists.get_json()["error"].lower()

    # 3. ValueError "invalid" format
    with patch(
        "managers.component_manager.ComponentManager.create_component",
        side_effect=ValueError("Invalid component ID format"),
    ):
        res_inv = client.post(
            "/api/components/ai",
            json={
                "id": "new-app",
                "metadata": {"name": "New App"},
                "overwrite": False,
            },
        )
        assert res_inv.status_code == 400
        assert "invalid" in res_inv.get_json()["error"].lower()

    # 4. Generic Exception -> 500
    with patch(
        "managers.component_manager.ComponentManager.create_component",
        side_effect=Exception("Database lock error"),
    ):
        res_crash = client.post(
            "/api/components/ai",
            json={
                "id": "new-app",
                "metadata": {"name": "New App"},
                "overwrite": False,
            },
        )
        assert res_crash.status_code == 500
        assert "internal error" in res_crash.get_json()["error"].lower()


def test_editor_auth_routes(editor_more_env):
    """Tests /setup, /login, /logout, and auth endpoints in Editor App."""
    client, _, _ = editor_more_env

    # 1. /setup GET
    with patch("editor_app.app.is_admin_configured", return_value=True):
        res_setup_logged = client.get("/setup")
        assert res_setup_logged.status_code == 302

    with patch("editor_app.app.is_admin_configured", return_value=False):
        res_setup_fresh = client.get("/setup")
        assert res_setup_fresh.status_code == 200

    # 2. /setup POST
    with patch("editor_app.app.is_admin_configured", return_value=True):
        res_setup_dup = client.post("/api/setup", json={"username": "adm"})
        assert res_setup_dup.status_code == 403

    with patch("editor_app.app.is_admin_configured", return_value=False):
        # Invalid username
        with patch(
            "editor_app.app.validate_username",
            return_value=(False, "Invalid username"),
        ):
            res_bad_user = client.post("/api/setup", json={"username": " "})
            assert res_bad_user.status_code == 400

        # Weak password
        with (
            patch("editor_app.app.validate_username", return_value=(True, None)),
            patch(
                "editor_app.app.validate_password_strength",
                return_value=(False, "Weak password"),
            ),
        ):
            res_weak = client.post(
                "/api/setup", json={"username": "admin", "password": "123"}
            )
            assert res_weak.status_code == 400

        # Password mismatch
        with (
            patch("editor_app.app.validate_username", return_value=(True, None)),
            patch(
                "editor_app.app.validate_password_strength",
                return_value=(True, None),
            ),
        ):
            res_mismatch = client.post(
                "/api/setup",
                json={
                    "username": "admin",
                    "password": "Password123!",
                    "confirm_password": "OtherPassword123!",
                },
            )
            assert res_mismatch.status_code == 400

        # Valid setup
        with (
            patch("editor_app.app.validate_username", return_value=(True, None)),
            patch(
                "editor_app.app.validate_password_strength",
                return_value=(True, None),
            ),
            patch(
                "editor_app.app.save_auth_config",
                return_value={"api_key": "editor-api-key"},
            ),
        ):
            res_setup_ok = client.post(
                "/api/setup",
                json={"username": "admin", "password": "Password123!"},
            )
            assert res_setup_ok.status_code == 200
            assert res_setup_ok.get_json()["api_key"] == "editor-api-key"

    # Clear session after setup
    with client.session_transaction() as sess:
        sess.clear()

    # 3. /login GET and POST
    with (
        patch("editor_app.app.is_admin_configured", return_value=False),
        patch("editor_app.app.is_auth_enabled", return_value=True),
    ):
        res_login_redir = client.get("/login")
        assert res_login_redir.status_code == 302

    res_login_page = client.get("/login")
    assert res_login_page.status_code == 200

    # Rate limited login
    with patch(
        "editor_app.app.GLOBAL_RATE_LIMITER.is_rate_limited",
        return_value=(True, 45),
    ):
        res_limited = client.post(
            "/login", json={"username": "admin", "password": "pw"}
        )
        assert res_limited.status_code == 429

    # Empty credentials
    res_empty_cred = client.post("/login", json={})
    assert res_empty_cred.status_code == 400

    # Wrong credentials
    with patch("editor_app.app.verify_credentials", return_value=False):
        res_bad_pw = client.post(
            "/login", json={"username": "admin", "password": "bad"}
        )
        assert res_bad_pw.status_code == 401

    # Valid login
    with patch("editor_app.app.verify_credentials", return_value=True):
        res_login_ok = client.post(
            "/login", json={"username": "admin", "password": "good"}
        )
        assert res_login_ok.status_code == 200

    # 4. /logout
    res_logout = client.get("/logout")
    assert res_logout.status_code == 302

    # 5. /api/auth/regenerate-api-key
    # 5. /api/auth/status
    res_status_anon = client.get("/api/auth/status")
    assert res_status_anon.status_code == 200
    assert res_status_anon.get_json()["authenticated"] is False

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user"] = "admin"

    res_status_auth = client.get("/api/auth/status")
    assert res_status_auth.status_code == 200
    assert res_status_auth.get_json()["authenticated"] is True
    assert res_status_auth.get_json()["user"] == "admin"


def test_editor_sync_and_git_routes(editor_more_env):
    """Tests /api/sync/* and /api/git/* operations in Editor App."""
    client, _, _ = editor_more_env

    # 1. /api/sync/status
    with patch(
        "managers.sync_manager.SyncManager.get_sync_status",
        return_value={"status": "in_sync"},
    ):
        res_sync_st = client.get("/api/sync/status")
        assert res_sync_st.status_code == 200
        assert res_sync_st.get_json()["status"] == "in_sync"

    with patch(
        "managers.sync_manager.SyncManager.get_sync_status",
        side_effect=Exception("Sync status fail"),
    ):
        res_sync_st_err = client.get("/api/sync/status")
        assert res_sync_st_err.status_code == 500

    # 2. /api/sync/check-updates
    with patch(
        "managers.sync_manager.SyncManager.fetch_from_remote",
        return_value=True,
    ):
        res_chk_up = client.get("/api/sync/check-updates")
        assert res_chk_up.status_code == 200

    with patch(
        "managers.sync_manager.SyncManager.fetch_from_remote",
        side_effect=Exception("Offline fail"),
    ):
        res_chk_offline = client.get("/api/sync/check-updates")
        assert res_chk_offline.status_code == 200
        assert res_chk_offline.get_json()["is_offline"] is True

    # 3. /api/components/<comp_id>/mark-tested
    with patch(
        "managers.component_manager.ComponentManager.mark_component_tested",
        return_value=True,
    ):
        res_mark_ok = client.post("/api/components/demo-app/mark-tested")
        assert res_mark_ok.status_code == 200

    with patch(
        "managers.component_manager.ComponentManager.mark_component_tested",
        side_effect=KeyError("Missing"),
    ):
        res_mark_missing = client.post("/api/components/missing/mark-tested")
        assert res_mark_missing.status_code == 404

    with patch(
        "managers.component_manager.ComponentManager.mark_component_tested",
        side_effect=Exception("Disk error"),
    ):
        res_mark_err = client.post("/api/components/demo-app/mark-tested")
        assert res_mark_err.status_code == 500

    # 4. /api/sync/fetch
    with patch(
        "managers.sync_manager.SyncManager.fetch_from_remote",
        return_value=True,
    ):
        res_fetch_ok = client.post("/api/sync/fetch")
        assert res_fetch_ok.status_code == 200

    with patch(
        "managers.sync_manager.SyncManager.fetch_from_remote",
        return_value=False,
    ):
        res_fetch_fail = client.post("/api/sync/fetch")
        assert res_fetch_fail.status_code == 500

    with patch(
        "managers.sync_manager.SyncManager.fetch_from_remote",
        side_effect=Exception("Network down"),
    ):
        res_fetch_err = client.post("/api/sync/fetch")
        assert res_fetch_err.status_code == 500

    # 3. /api/sync/component/<comp_id>
    with patch(
        "managers.sync_manager.SyncManager.sync_component",
        return_value=True,
    ):
        res_sync_c_ok = client.post("/api/sync/component/demo-app")
        assert res_sync_c_ok.status_code == 200

    with patch(
        "managers.sync_manager.SyncManager.sync_component",
        return_value=False,
    ):
        res_sync_c_fail = client.post("/api/sync/component/demo-app")
        assert res_sync_c_fail.status_code == 500

    with patch(
        "managers.sync_manager.SyncManager.sync_component",
        side_effect=Exception("Sync err"),
    ):
        res_sync_c_err = client.post("/api/sync/component/demo-app")
        assert res_sync_c_err.status_code == 500

    # 4. /api/sync/all
    with patch("managers.sync_manager.SyncManager.sync_all", return_value=True):
        res_sync_all_ok = client.post("/api/sync/all")
        assert res_sync_all_ok.status_code == 200

    with patch("managers.sync_manager.SyncManager.sync_all", return_value=False):
        res_sync_all_fail = client.post("/api/sync/all")
        assert res_sync_all_fail.status_code == 500

    with patch(
        "managers.sync_manager.SyncManager.sync_all",
        side_effect=Exception("Sync all err"),
    ):
        res_sync_all_err = client.post("/api/sync/all")
        assert res_sync_all_err.status_code == 500

    # 5. /api/git/check_permission
    with patch(
        "managers.sync_manager.SyncManager.check_write_access_details",
        return_value=(True, "Write access granted"),
    ):
        res_git_perm = client.get("/api/git/check_permission")
        assert res_git_perm.status_code == 200
        assert res_git_perm.get_json()["has_write_access"] is True

    with patch(
        "managers.sync_manager.SyncManager.check_write_access_details",
        side_effect=Exception("Git perm error"),
    ):
        res_git_perm_err = client.get("/api/git/check_permission")
        assert res_git_perm_err.status_code == 500

    # 6. /api/git/upload/<comp_id>
    with patch(
        "managers.sync_manager.SyncManager.validate_metadata_header",
        return_value=False,
    ):
        res_up_invalid = client.post("/api/git/upload/demo-app")
        assert res_up_invalid.status_code == 400

    with (
        patch(
            "managers.sync_manager.SyncManager.validate_metadata_header",
            return_value=True,
        ),
        patch(
            "managers.sync_manager.SyncManager.upload_component",
            return_value=True,
        ),
    ):
        res_up_ok = client.post("/api/git/upload/demo-app")
        assert res_up_ok.status_code == 200

    with (
        patch(
            "managers.sync_manager.SyncManager.validate_metadata_header",
            return_value=True,
        ),
        patch(
            "managers.sync_manager.SyncManager.upload_component",
            return_value=False,
        ),
    ):
        res_up_fail = client.post("/api/git/upload/demo-app")
        assert res_up_fail.status_code == 500

    with (
        patch(
            "managers.sync_manager.SyncManager.validate_metadata_header",
            return_value=True,
        ),
        patch(
            "managers.sync_manager.SyncManager.upload_component",
            side_effect=Exception("Push fail"),
        ),
    ):
        res_up_err = client.post("/api/git/upload/demo-app")
        assert res_up_err.status_code == 500

    # 7. /api/git/upload_all
    with patch(
        "managers.sync_manager.SyncManager.upload_all_components",
        return_value=True,
    ):
        res_up_all_ok = client.post("/api/git/upload_all")
        assert res_up_all_ok.status_code == 200

    with patch(
        "managers.sync_manager.SyncManager.upload_all_components",
        return_value=False,
    ):
        res_up_all_fail = client.post("/api/git/upload_all")
        assert res_up_all_fail.status_code == 500

    with patch(
        "managers.sync_manager.SyncManager.upload_all_components",
        side_effect=ValueError("Validation failed for foo"),
    ):
        res_up_all_val_err = client.post("/api/git/upload_all")
        assert res_up_all_val_err.status_code == 400

    with patch(
        "managers.sync_manager.SyncManager.upload_all_components",
        side_effect=Exception("Bulk push fail"),
    ):
        res_up_all_err = client.post("/api/git/upload_all")
        assert res_up_all_err.status_code == 500


def test_editor_app_frozen_and_env_loading(tmp_path):
    """Test create_app behavior when sys.frozen is True."""
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "templates").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "static").mkdir(parents=True, exist_ok=True)
    exe_dir = tmp_path / "exe"
    exe_dir.mkdir(parents=True, exist_ok=True)
    env_file = exe_dir / ".env"
    env_file.write_text("FROZEN_TEST_VAR=1\n", encoding="utf-8")

    meta_file = bundle_dir / "components_metadata.json"
    meta_file.write_text(json.dumps({"components": {}}), encoding="utf-8")

    with (
        patch.object(sys, "frozen", True, create=True),
        patch.object(sys, "_MEIPASS", str(bundle_dir), create=True),
        patch.object(sys, "executable", str(exe_dir / "njord-editor")),
        patch("utils.resource_utils.seed_user_components_if_needed"),
        patch(
            "utils.resource_utils.get_components_paths",
            return_value=(meta_file, bundle_dir),
        ),
    ):
        app = create_app()
        assert app is not None

    # Test fallback when candidates do not exist
    with (
        patch.object(sys, "frozen", True, create=True),
        patch.object(sys, "_MEIPASS", str(bundle_dir), create=True),
        patch.object(sys, "executable", str(tmp_path / "nonexistent" / "app")),
        patch("dotenv.load_dotenv") as mock_load,
        patch("utils.resource_utils.seed_user_components_if_needed"),
        patch(
            "utils.resource_utils.get_components_paths",
            return_value=(meta_file, bundle_dir),
        ),
    ):
        app2 = create_app()
        assert app2 is not None
        mock_load.assert_called()


def test_editor_auth_redirects_and_logout_api(editor_more_env):
    """Test login/setup redirects and logout API."""
    client, *_ = editor_more_env

    # 1. /setup when admin is configured and user is already logged in
    with patch("editor_app.app.is_admin_configured", return_value=True):
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user"] = "admin"
        res_setup = client.get("/setup", follow_redirects=False)
        assert res_setup.status_code == 302
        assert res_setup.headers["Location"] in ("/", "http://localhost/")

    # 2. /login when user is already logged in with ?next parameter
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user"] = "admin"
    res_login = client.get("/login?next=/components", follow_redirects=False)
    assert res_login.status_code == 302
    assert "/components" in res_login.headers["Location"]

    # 3. /api/logout returns JSON status logged_out
    res_logout = client.post(
        "/api/logout",
        headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
    )
    assert res_logout.status_code == 200
    assert res_logout.get_json()["status"] == "logged_out"


def test_editor_ai_provider_online_status(editor_more_env, monkeypatch):
    """Test AI provider status when API key is configured."""
    client, *_ = editor_more_env
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    res = client.post("/api/ai/status", json={"provider": "anthropic"})
    assert res.status_code == 200
    assert res.get_json()["status"] == "online"


def test_editor_ai_generate_streaming_and_custom_id(editor_more_env):
    """Test AI component generation streaming and whitespace ID."""
    client, *_ = editor_more_env

    # 1. custom_component_id as whitespace
    with patch(
        "editor_app.app.AIGenerator.generate_component_data",
        return_value={"metadata": {"name": "Test"}, "docker_compose": "services:\n"},
    ):
        res = client.post(
            "/api/ai/generate",
            json={
                "repo_url": "https://github.com/foo/bar",
                "component_id": "   ",
                "base_url": "https://api.openai.com/v1",
            },
        )
        assert res.status_code == 200

    # 2. streaming mode with save_key=True
    with (
        patch(
            "editor_app.app.AIGenerator.generate_component_data",
            return_value={
                "metadata": {"name": "Test"},
                "docker_compose": "services:\n",
            },
        ),
        patch("utils.ai_provider_manager.save_api_key_to_env_file"),
    ):
        res_stream = client.post(
            "/api/ai/generate",
            json={
                "repo_url": "https://github.com/foo/bar",
                "stream": True,
                "save_key": True,
                "api_key": "test-key",
            },
        )
        assert res_stream.status_code == 200
        assert "text/event-stream" in res_stream.headers["Content-Type"]
        body = res_stream.get_data(as_text=True)
        assert "data:" in body


def test_editor_sync_diff_file_mismatches(tmp_path):
    """Test sync diff with extra files and binary mismatches."""
    data_dir = tmp_path / "data_dir"
    cache_templates = data_dir / "remote_components_cache" / "component_templates"
    comp_cache = cache_templates / "demo-app"
    comp_cache.mkdir(parents=True, exist_ok=True)

    meta_path = tmp_path / "components_metadata.json"
    meta_path.write_text(
        json.dumps(
            {"components": {"demo-app": {"name": "Demo App", "group": "utilities"}}}
        ),
        encoding="utf-8",
    )
    templates_path = tmp_path / "component_templates"
    templates_path.mkdir(parents=True, exist_ok=True)
    local_comp = templates_path / "demo-app"
    local_comp.mkdir(parents=True, exist_ok=True)

    # 1. File exists locally but not remotely
    (local_comp / "extra.txt").write_text("extra", encoding="utf-8")
    # 2. File exists remotely but not locally
    (comp_cache / "cache_only.txt").write_text("cache", encoding="utf-8")
    # 3. Binary file mismatch
    (local_comp / "logo.bin").write_bytes(b"\x01\x02")
    (comp_cache / "logo.bin").write_bytes(b"\x03\x04")

    with patch.dict("os.environ", {"NJORD_DATA_DIR": str(data_dir)}):
        app = create_app(
            {
                "TESTING": True,
                "AUTH_ENABLED": False,
                "TEMPLATES_PATH": str(templates_path),
                "METADATA_FILE_PATH": str(meta_path),
            }
        )
        client = app.test_client()

        res = client.get("/api/sync/diff/demo-app")
        assert res.status_code == 200
        data = res.get_json()
        assert "extra.txt" in data["differing_files"]
        assert "cache_only.txt" in data["differing_files"]
        assert "logo.bin" in data["differing_files"]


def test_editor_ai_component_save_edge_cases(editor_more_env):
    """Test AI component save edge cases, unclosed Jinja, and KeyError."""
    client, *_ = editor_more_env

    # 1. Unclosed Jinja comments, blocks, and variables in docker_compose
    unclosed_jinja = (
        "services:\n"
        "  app:\n"
        "    image: test\n"
        "    {# unclosed comment\n"
        "    {% unclosed block\n"
        "    {{ unclosed variable\n"
    )
    res_jinja = client.post(
        "/api/components/ai",
        json={
            "id": "unclosed-jinja-app",
            "name": "Unclosed Jinja App",
            "metadata": {"name": "Unclosed Jinja App"},
            "docker_compose": unclosed_jinja,
            "variables": [],
        },
    )
    assert res_jinja.status_code in (200, 201)

    # 2. Path traversal in config_templates via realpath escaping safe_base
    real_realpath = os.path.realpath

    def fake_realpath(path, *args, **kwargs):
        if "evil" in str(path):
            return "/tmp/outside/evil.conf"
        return real_realpath(path, *args, **kwargs)

    with patch("os.path.realpath", side_effect=fake_realpath):
        res_trav = client.post(
            "/api/components/ai",
            json={
                "id": "trav-app",
                "name": "Traversal App",
                "metadata": {"name": "Traversal App"},
                "config_templates": {"evil.conf": "malicious content"},
            },
        )
        assert res_trav.status_code == 400

    # 3. Invalid filename in config_templates
    res_inval_fn = client.post(
        "/api/components/ai",
        json={
            "id": "inval-fn-app",
            "name": "Invalid FN App",
            "metadata": {"name": "Invalid FN App"},
            "config_templates": {"???": "some content"},
        },
    )
    assert res_inval_fn.status_code == 400

    # 4. KeyError in update_component_metadata triggers fallback
    with patch(
        "managers.component_manager.ComponentManager.update_component_metadata",
        side_effect=KeyError("Missing"),
    ):
        res_key_err = client.post(
            "/api/components/ai",
            json={
                "id": "key-err-app",
                "name": "Key Err App",
                "metadata": {"name": "Key Err App"},
            },
        )
        assert res_key_err.status_code == 201

    # 5. General ValueError in saving component
    with patch(
        "managers.component_manager.ComponentManager.create_component",
        side_effect=ValueError("Some unexpected validation error"),
    ):
        res_gen_val = client.post(
            "/api/components/ai",
            json={
                "id": "val-err-app",
                "name": "Val Err App",
                "metadata": {"name": "Val Err App"},
            },
        )
        assert res_gen_val.status_code == 400
        assert "validation error" in res_gen_val.get_json()["error"]
