# tests/editor_app/test_editor_routes_extended.py

"""Extended test suite for Editor App covering endpoints, edge cases,
and error handling.
"""

import json
import os
import queue
from pathlib import Path
from unittest.mock import patch

import pytest

from editor_app.app import create_app


@pytest.fixture
def editor_env(tmp_path):
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
                "_njorddeploy": {"group_rules": {"utilities": {"name": "Utilities"}}},
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
        '# status: "testing"\n'
        '# last_tested_version: "1.0"\n'
        '# platform_notes: "None"\n'
        '# breaking_changes: "None"\n'
        "services:\n  demo:\n    image: demo:1.0\n",
        encoding="utf-8",
    )
    (demo_dir / "template-config" / "variables.json").write_text(
        json.dumps({"variables": [{"name": "PORT", "default": 8080}]}),
        encoding="utf-8",
    )
    (demo_dir / "template-config" / "app.conf").write_text(
        "setting=true\n", encoding="utf-8"
    )

    test_config = {
        "TESTING": True,
        "AUTH_ENABLED": False,
        "TEMPLATES_PATH": str(templates_path),
        "METADATA_FILE_PATH": str(meta_path),
    }
    app = create_app(test_config)
    client = app.test_client()
    return client, meta_path, templates_path


def test_language_routes(editor_env):
    client, _, _ = editor_env
    # 1. API endpoint set-language nl
    resp = client.post("/api/v1/set-language/nl")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["language"] == "nl"

    # 2. Browser endpoint set-language en with next param
    resp2 = client.get("/set-language/en?next=/")
    assert resp2.status_code == 302
    assert resp2.headers["Location"] == "/"

    # 3. Unsupported language
    resp3 = client.get("/set-language/unsupported")
    assert resp3.status_code == 400


def test_index_and_static_css(editor_env):
    client, _, _ = editor_env
    # Index page
    resp = client.get("/")
    assert resp.status_code == 200

    # CSS static endpoint
    resp_css = client.get("/static/css/njorddeploy-style.css")
    assert resp_css.status_code in (200, 304, 404)


def test_components_crud_api(editor_env):
    client, _, _ = editor_env

    # 1. GET /api/components
    resp = client.get("/api/components")
    assert resp.status_code == 200
    comps = resp.get_json()
    assert "demo-app" in comps

    # 2. GET /api/components/<comp_id>
    resp_detail = client.get("/api/components/demo-app")
    assert resp_detail.status_code == 200
    assert resp_detail.get_json()["name"] == "Demo App"

    # 3. GET nonexistent component
    resp_404 = client.get("/api/components/nonexistent")
    assert resp_404.status_code == 404

    # 4. PUT /api/components/<comp_id> (update metadata)
    resp_update = client.put(
        "/api/components/demo-app",
        json={"name": "Demo App Updated", "group": "utilities"},
    )
    assert resp_update.status_code == 200

    # 5. PUT /api/components/<comp_id>/variables
    resp_vars = client.put(
        "/api/components/demo-app/variables",
        json={"variables": [{"name": "HOST", "default": "127.0.0.1"}]},
    )
    assert resp_vars.status_code == 200

    # Invalid payload (not a dict)
    resp_bad_vars = client.put(
        "/api/components/demo-app/variables",
        data="not a json",
        content_type="application/json",
    )
    assert resp_bad_vars.status_code == 400

    # 6. POST /api/components (create new component)
    resp_create = client.post(
        "/api/components",
        json={"id": "new-app", "meta": {"name": "New App"}},
    )
    assert resp_create.status_code == 201

    # Missing ID
    resp_bad_create = client.post("/api/components", json={})
    assert resp_bad_create.status_code == 400

    # 7. GET & PUT /api/components/<comp_id>/template
    resp_tpl = client.get("/api/components/demo-app/template")
    assert resp_tpl.status_code == 200
    assert "services:" in resp_tpl.get_data(as_text=True)

    resp_put_tpl = client.put(
        "/api/components/demo-app/template",
        data="services:\n  web:\n    image: nginx\n",
        content_type="text/plain",
    )
    assert resp_put_tpl.status_code == 200

    # 8. Configs GET, PUT, DELETE
    resp_cfgs = client.get("/api/components/demo-app/configs")
    assert resp_cfgs.status_code == 200

    resp_put_cfg = client.put(
        "/api/components/demo-app/configs/extra.conf",
        data="debug=false\n",
        content_type="text/plain",
    )
    assert resp_put_cfg.status_code == 200

    resp_del_cfg = client.delete("/api/components/demo-app/configs/extra.conf")
    assert resp_del_cfg.status_code == 200

    # 9. Validation endpoints
    resp_val = client.post(
        "/api/components/demo-app/validate",
        json={
            "template_content": "services:\n  app:\n    image: test\n",
            "variables": [],
        },
    )
    assert resp_val.status_code == 200

    resp_conflicts = client.post(
        "/api/components/demo-app/validate_metadata_conflicts",
        json={"conflicts_with": []},
    )
    assert resp_conflicts.status_code == 200

    # 10. DELETE /api/components/<comp_id>
    resp_del = client.delete("/api/components/new-app")
    assert resp_del.status_code == 200


def test_groups_and_packages_api(editor_env):
    client, _, _ = editor_env

    # 1. GET /api/groups
    resp_groups = client.get("/api/groups")
    assert resp_groups.status_code == 200

    # 2. PUT /api/groups/order
    resp_order = client.put("/api/groups/order", json=["utilities"])
    assert resp_order.status_code == 200

    # Invalid order payload
    resp_bad_order = client.put("/api/groups/order", json="not a list")
    assert resp_bad_order.status_code == 400

    # 3. PUT /api/components/order
    resp_comp_order = client.put("/api/components/order", json=["demo-app"])
    assert resp_comp_order.status_code == 200

    # 4. PUT /api/components/<comp_id>/group
    resp_set_group = client.put(
        "/api/components/demo-app/group",
        json={"group": "utilities"},
    )
    assert resp_set_group.status_code == 200

    # 5. PUT /api/groups/<group_id>/rename
    resp_rename = client.put(
        "/api/groups/utilities/rename",
        json={"name": "Tools & Utils"},
    )
    assert resp_rename.status_code == 200

    # 6. Packages GET, PUT, DELETE
    resp_pkgs = client.get("/api/packages")
    assert resp_pkgs.status_code == 200

    resp_pkg_put = client.put(
        "/api/packages/pkg-custom",
        json={"name": "Custom Package", "description": "test"},
    )
    assert resp_pkg_put.status_code == 200

    resp_pkg_del = client.delete("/api/packages/pkg-custom")
    assert resp_pkg_del.status_code == 200


def test_auth_hash_and_ai_providers(editor_env, monkeypatch):
    client, _, _ = editor_env
    monkeypatch.setenv("AI_PROVIDER", "ollama")

    # 1. POST /api/generate_auth_hash
    resp_hash = client.post(
        "/api/generate_auth_hash",
        json={"username": "admin", "password": "SuperSecretPassword123!"},
    )
    assert resp_hash.status_code == 200
    data = resp_hash.get_json()
    assert "hashed_user_string" in data
    assert data["hashed_user_string"].startswith("admin:")

    # Missing username or password
    resp_bad_hash = client.post("/api/generate_auth_hash", json={})
    assert resp_bad_hash.status_code == 400

    # 2. GET /api/ai/providers
    resp_prov = client.get("/api/ai/providers")
    assert resp_prov.status_code == 200
    assert "providers" in resp_prov.get_json()

    # 3. GET /api/ai/status
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [{"name": "llama3:latest"}]
        }
        resp_status = client.get("/api/ai/status")
        assert resp_status.status_code == 200
        assert resp_status.get_json()["provider"] == "ollama"

    # POST /api/ai/status with custom provider
    resp_post_status = client.post(
        "/api/ai/status",
        json={"provider": "anthropic"},
    )
    assert resp_post_status.status_code == 200


def test_sync_and_git_routes(editor_env):
    client, _, _ = editor_env

    with (
        patch(
            "managers.sync_manager.SyncManager.get_sync_status",
            return_value={"status": "synced"},
        ),
        patch("managers.sync_manager.SyncManager.fetch_from_remote", return_value=True),
        patch(
            "managers.sync_manager.SyncManager.check_write_access_details",
            return_value=(True, "Writable"),
        ),
        patch(
            "managers.sync_manager.SyncManager.validate_metadata_header",
            return_value=True,
        ),
        patch("managers.sync_manager.SyncManager.upload_component", return_value=True),
        patch(
            "managers.sync_manager.SyncManager.upload_all_components", return_value=True
        ),
        patch(
            "managers.sync_manager.SyncManager.get_local_component_meta",
            return_value={"name": "Demo"},
        ),
        patch(
            "managers.sync_manager.SyncManager.get_remote_component_meta",
            return_value={"name": "Demo"},
        ),
        patch("managers.sync_manager.SyncManager.sync_component", return_value=True),
        patch("managers.sync_manager.SyncManager.sync_all", return_value=True),
    ):

        # 1. GET /api/sync/status
        r1 = client.get("/api/sync/status")
        assert r1.status_code == 200

        # 2. POST /api/sync/check-updates
        r2 = client.post("/api/sync/check-updates")
        assert r2.status_code == 200

        # 3. POST /api/sync/fetch
        r3 = client.post("/api/sync/fetch")
        assert r3.status_code == 200

        # 4. POST /api/components/<comp_id>/mark-tested
        r4 = client.post(
            "/api/components/demo-app/mark-tested", json={"test_status": "stable"}
        )
        assert r4.status_code == 200

        # 5. POST /api/sync/component/<comp_id>
        r5 = client.post("/api/sync/component/demo-app")
        assert r5.status_code == 200

        # 6. POST /api/sync/all
        r6 = client.post("/api/sync/all")
        assert r6.status_code == 200

        # 7. GET /api/sync/diff/<comp_id>
        r7 = client.get("/api/sync/diff/demo-app")
        assert r7.status_code == 200

        # 8. GET /api/git/check_permission
        r8 = client.get("/api/git/check_permission")
        assert r8.status_code == 200

        # 9. POST /api/git/upload/<comp_id>
        r9 = client.post("/api/git/upload/demo-app")
        assert r9.status_code == 200

        # 10. POST /api/git/upload_all
        r10 = client.post("/api/git/upload_all")
        assert r10.status_code == 200


def test_auth_workflow_and_enforcement(tmp_path):
    """Verifies setup, login, logout and auth enforcement when AUTH_ENABLED=True."""
    meta_path = tmp_path / "components_metadata.json"
    meta_path.write_text(json.dumps({"components": {}}), encoding="utf-8")
    templates_path = tmp_path / "templates"
    templates_path.mkdir()

    app = create_app(
        {
            "TESTING": True,
            "AUTH_ENABLED": True,
            "TEMPLATES_PATH": str(templates_path),
            "METADATA_FILE_PATH": str(meta_path),
        }
    )
    client = app.test_client()

    with patch("editor_app.app.is_auth_enabled", return_value=True):
        # 1. When admin is NOT configured
        with patch("editor_app.app.is_admin_configured", return_value=False):
            # API request requires setup
            r_api = client.get(
                "/api/components", headers={"Accept": "application/json"}
            )
            assert r_api.status_code == 401
            assert r_api.get_json()["setup_required"] is True

            # GET /setup renders wizard
            r_setup_page = client.get("/setup")
            assert r_setup_page.status_code == 200

            # POST /setup invalid password
            r_weak = client.post(
                "/api/setup",
                json={"username": "admin", "password": "123"},
            )
            assert r_weak.status_code == 400

            # POST /setup valid admin
            with patch(
                "editor_app.app.save_auth_config", return_value={"api_key": "key_123"}
            ):
                r_setup_ok = client.post(
                    "/api/setup",
                    json={
                        "username": "admin",
                        "password": "CorrectPassword123#",
                        "confirm_password": "CorrectPassword123#",
                    },
                )
                assert r_setup_ok.status_code == 200
                assert r_setup_ok.get_json()["status"] == "success"

        # 2. When admin IS configured
        with patch("editor_app.app.is_admin_configured", return_value=True):
            # Setup returns 403
            r_setup_done = client.post(
                "/api/setup", json={"username": "admin", "password": "xyz"}
            )
            assert r_setup_done.status_code == 403

            # Clear session from setup by logging out
            client.get("/logout")

            # Login page GET
            r_login_page = client.get("/login")
            assert r_login_page.status_code == 200

            # POST /login invalid
            with patch("editor_app.app.verify_credentials", return_value=False):
                r_bad_login = client.post(
                    "/api/login",
                    json={"username": "admin", "password": "wrong"},
                )
                assert r_bad_login.status_code == 401

            # POST /login valid
            with patch("editor_app.app.verify_credentials", return_value=True):
                r_login_ok = client.post(
                    "/api/login",
                    json={"username": "admin", "password": "correct"},
                )
                assert r_login_ok.status_code == 200
                assert r_login_ok.get_json()["status"] == "authenticated"

            # GET /api/auth/status
            r_status = client.get("/api/auth/status")
            assert r_status.status_code == 200

            # GET /logout
            r_logout = client.get("/logout")
            assert r_logout.status_code == 302


def test_editor_error_handling_and_edge_cases(editor_env):
    """Tests failure branches, 400s, 404s, and 500s across editor API."""
    client, _, _ = editor_env

    # 1. Component CRUD errors
    assert (
        client.put("/api/components/nonexistent", json={"name": "X"}).status_code == 404
    )
    assert client.delete("/api/components/nonexistent").status_code == 404
    assert client.post("/api/components", json={"id": "demo-app"}).status_code == 409
    assert (
        client.put(
            "/api/components/nonexistent/group", json={"group": "utilities"}
        ).status_code
        == 404
    )
    assert client.put("/api/components/demo-app/group", json={}).status_code == 400

    # 2. Groups & Packages errors (cannot delete when in use)
    assert (
        client.put(
            "/api/groups/nonexistent_grp/rename", json={"name": "New"}
        ).status_code
        == 404
    )
    assert client.put("/api/groups/utilities/rename", json={}).status_code == 400
    assert client.delete("/api/groups/utilities").status_code == 400
    # Link demo-app to pkg-1 and verify pkg-1 cannot be deleted while in use
    client.put("/api/components/demo-app", json={"package_id": "pkg-1"})
    assert client.delete("/api/packages/pkg-1").status_code == 400

    # 3. Validation failure
    r_val = client.post(
        "/api/components/demo-app/validate",
        json={"template_content": "invalid: yaml: [unclosed", "variables": []},
    )
    assert r_val.status_code in (400, 500)

    # 4. Sync & Git failure responses
    with patch(
        "managers.sync_manager.SyncManager.fetch_from_remote", return_value=False
    ):
        assert client.post("/api/sync/fetch").status_code == 500

    with patch("managers.sync_manager.SyncManager.sync_component", return_value=False):
        assert client.post("/api/sync/component/demo-app").status_code == 500

    with patch("managers.sync_manager.SyncManager.sync_all", return_value=False):
        assert client.post("/api/sync/all").status_code == 500

    with patch(
        "managers.sync_manager.SyncManager.validate_metadata_header", return_value=False
    ):
        assert client.post("/api/git/upload/demo-app").status_code == 400

    with (
        patch(
            "managers.sync_manager.SyncManager.validate_metadata_header",
            return_value=True,
        ),
        patch("managers.sync_manager.SyncManager.upload_component", return_value=False),
    ):
        assert client.post("/api/git/upload/demo-app").status_code == 500

    with patch(
        "managers.sync_manager.SyncManager.upload_all_components",
        side_effect=ValueError("validation failed"),
    ):
        assert client.post("/api/git/upload_all").status_code == 400


def test_ai_generate_error_responses(editor_env):
    """Tests status codes for various AI API failures."""
    client, _, _ = editor_env

    # 1. Invalid base_url
    r_bad_url = client.post(
        "/api/ai/generate",
        json={
            "repo_url": "https://github.com/test/app",
            "base_url": "file:///etc/passwd",
        },
    )
    assert r_bad_url.status_code == 400

    # 2. ValueError branches
    with patch(
        "editor_app.app.AIGenerator.generate_component_data",
        side_effect=ValueError("API key missing for provider"),
    ):
        r_nokey = client.post(
            "/api/ai/generate",
            json={"repo_url": "https://github.com/test/app"},
        )
        assert r_nokey.status_code == 400

    with patch(
        "editor_app.app.AIGenerator.generate_component_data",
        side_effect=ValueError("Invalid repository URL format"),
    ):
        r_badrepo = client.post(
            "/api/ai/generate",
            json={"repo_url": "https://github.com/test/app"},
        )
        assert r_badrepo.status_code == 400

    # 3. Timeout -> 504
    with patch(
        "editor_app.app.AIGenerator.generate_component_data",
        side_effect=Exception("API request timeout after 30s"),
    ):
        r_timeout = client.post(
            "/api/ai/generate",
            json={"repo_url": "https://github.com/test/app"},
        )
        assert r_timeout.status_code == 504

    # 4. Connection refused -> 502
    with patch(
        "editor_app.app.AIGenerator.generate_component_data",
        side_effect=Exception("Connection refused"),
    ):
        r_conn = client.post(
            "/api/ai/generate",
            json={"repo_url": "https://github.com/test/app"},
        )
        assert r_conn.status_code == 502

    # 5. Generic exception -> 500
    with patch(
        "editor_app.app.AIGenerator.generate_component_data",
        side_effect=Exception("Unexpected crash"),
    ):
        r_err = client.post(
            "/api/ai/generate",
            json={"repo_url": "https://github.com/test/app"},
        )
        assert r_err.status_code == 500


def test_save_ai_component_edge_cases(editor_env):
    """Tests validation and edge cases when saving AI generated component."""
    client, _, _ = editor_env

    # 1. Invalid component_id format
    r_bad_id = client.post(
        "/api/components/ai",
        json={"id": "Invalid_ID_Uppercase!"},
    )
    assert r_bad_id.status_code == 400

    # 2. Existing component without overwrite -> 409
    r_dup = client.post(
        "/api/components/ai",
        json={"id": "demo-app", "metadata": {"name": "Demo"}, "overwrite": False},
    )
    assert r_dup.status_code == 409
    assert r_dup.get_json()["code"] == "component_exists"

    # 3. Auto-extract docker_service_name with Jinja tags
    yaml_with_jinja = (
        "{# Jinja comment #}\n"
        "{% if true %}\n"
        "services:\n"
        "  custom_worker:\n"
        "    image: test:latest\n"
        "    ports:\n"
        "      - '{{ PORT }}:8080'\n"
        "{% endif %}\n"
    )
    r_save = client.post(
        "/api/components/ai",
        json={
            "id": "worker-app",
            "metadata": {"name": "Worker App"},
            "docker_compose": yaml_with_jinja,
            "overwrite": True,
            "config_templates": {"sample.txt": "sample content"},
        },
    )
    assert r_save.status_code == 201


def test_editor_app_create_app_branches(tmp_path):
    """Tests create_app frozen, dotenv, and development paths."""
    # 1. Frozen with env candidates not existing -> line 70: load_dotenv()
    # and NJORD_COOKIE_SECURE="1" -> line 99
    meipass = tmp_path / "meipass"
    meipass.mkdir()
    tpl = meipass / "src" / "editor_app" / "templates"
    tpl.mkdir(parents=True)
    stat = meipass / "src" / "editor_app" / "static"
    stat.mkdir(parents=True)

    orig_path_exists = Path.exists

    def fake_exists_no_dotenv(path_obj):
        if str(path_obj).endswith(".env"):
            return False
        return orig_path_exists(path_obj)

    with (
        patch("sys.frozen", True, create=True),
        patch("sys._MEIPASS", str(meipass), create=True),
        patch.dict(os.environ, {"NJORD_COOKIE_SECURE": "1"}),
        patch.object(Path, "exists", side_effect=fake_exists_no_dotenv, autospec=True),
        patch("dotenv.load_dotenv") as mock_dotenv,
        patch("editor_app.app.init_i18n"),
    ):
        app = create_app(test_config={"TESTING": True})
        assert app.config["SESSION_COOKIE_SECURE"] is True
        assert mock_dotenv.called

    # 2. Frozen where template_folder & static_folder do not exist in src/
    # but exist in meipass root -> branches 78->80, 81->83
    meipass_fallback = tmp_path / "meipass_fallback"
    meipass_fallback.mkdir()
    (meipass_fallback / "templates").mkdir()
    (meipass_fallback / "static").mkdir()

    with (
        patch("sys.frozen", True, create=True),
        patch("sys._MEIPASS", str(meipass_fallback), create=True),
        patch("dotenv.load_dotenv"),
        patch("editor_app.app.init_i18n"),
    ):
        app_fb = create_app(test_config={"TESTING": True})
        assert app_fb is not None

    # 3. Frozen where candidate .env exists -> branch 64->69
    env_dir = tmp_path / "env_bin"
    env_dir.mkdir()
    (env_dir / ".env").write_text("TEST=1\n", encoding="utf-8")

    def fake_exists_with_dotenv(path_obj):
        if "env_bin" in str(path_obj) and str(path_obj).endswith(".env"):
            return True
        return orig_path_exists(path_obj)

    with (
        patch("sys.frozen", True, create=True),
        patch("sys._MEIPASS", str(meipass), create=True),
        patch("sys.executable", str(env_dir / "python")),
        patch.object(
            Path, "exists", side_effect=fake_exists_with_dotenv, autospec=True
        ),
        patch("dotenv.load_dotenv"),
        patch("editor_app.app.init_i18n"),
    ):
        app_cand = create_app(test_config={"TESTING": True})
        assert app_cand is not None

    # 4. Development mode without test_config -> lines 133-134
    with (
        patch("sys.frozen", False, create=True),
        patch("editor_app.app.init_i18n"),
        patch("editor_app.app.ComponentManager"),
    ):
        app_dev = create_app(test_config=None)
        assert app_dev is not None


def test_git_upload_all_generic_value_error(editor_env):
    """Tests git_upload_all when ValueError is generic (line 660)."""
    client, *_ = editor_env
    with patch(
        "managers.sync_manager.SyncManager.upload_all_components",
        side_effect=ValueError("A completely unexpected internal error"),
    ):
        res = client.post("/api/git/upload_all")
        assert res.status_code == 400
        data = res.get_json()
        assert "Failed to upload components due to a validation error" in data["error"]


def test_remote_diff_matching_files_and_exception(tmp_path):
    """Tests sync diff with matching files and error (754-755)."""
    meta_path = tmp_path / "components_metadata.json"
    meta_path.write_text(
        json.dumps({"components": {"test-app": {"name": "Test"}}}),
        encoding="utf-8",
    )
    local_tpl = tmp_path / "local_templates"
    data_dir = tmp_path / "njord_data"
    cache_tpl = data_dir / "remote_components_cache" / "component_templates"

    local_app = local_tpl / "test-app"
    remote_app = cache_tpl / "test-app"
    local_app.mkdir(parents=True)
    remote_app.mkdir(parents=True)

    # Identical text file (.template suffix)
    (local_app / "docker-compose.template.yml").write_text(
        "services: {}\n", encoding="utf-8"
    )
    (remote_app / "docker-compose.template.yml").write_text(
        "services: {}\n", encoding="utf-8"
    )
    # Identical binary file (.dat suffix)
    (local_app / "data.dat").write_bytes(b"\x01\x02\x03")
    (remote_app / "data.dat").write_bytes(b"\x01\x02\x03")

    with patch.dict(os.environ, {"NJORD_DATA_DIR": str(data_dir)}):
        app = create_app(
            {
                "TESTING": True,
                "AUTH_ENABLED": False,
                "METADATA_FILE_PATH": str(meta_path),
                "TEMPLATES_PATH": str(local_tpl),
            }
        )
        client = app.test_client()

        with (
            patch(
                "managers.sync_manager.SyncManager.get_local_component_meta",
                return_value={},
            ),
            patch(
                "managers.sync_manager.SyncManager.get_remote_component_meta",
                return_value={},
            ),
        ):
            res = client.get("/api/sync/diff/test-app")
            assert res.status_code == 200
            assert res.get_json()["differing_files"] == []

            # Test exception during read (lines 754-755)
            orig_read_text = Path.read_text

            def mock_read_text(path_obj, *args, **kwargs):
                if path_obj.name == "err.txt":
                    raise OSError("Read error")
                return orig_read_text(path_obj, *args, **kwargs)

            (local_app / "err.txt").write_text("error", encoding="utf-8")
            (remote_app / "err.txt").write_text("error", encoding="utf-8")

            with patch.object(
                Path, "read_text", side_effect=mock_read_text, autospec=True
            ):
                res_err = client.get("/api/sync/diff/test-app")
                assert res_err.status_code == 200
                diff = res_err.get_json()["differing_files"]
                first_diff, *_ = diff
                assert first_diff is not None


def test_static_css_njorddeploy_style_not_found(editor_env):
    """Tests /static/css/njorddeploy-style.css 404 when file absent (line 794)."""
    client, *_ = editor_env
    orig_exists = Path.exists

    def mock_exists(self):
        if self.name == "njorddeploy-style.css":
            return False
        return orig_exists(self)

    with patch.object(Path, "exists", side_effect=mock_exists, autospec=True):
        res = client.get("/static/css/njorddeploy-style.css")
        assert res.status_code == 404
        assert "njorddeploy-style.css not found" in res.get_data(as_text=True)


def test_update_vars_not_a_dict(editor_env):
    """Tests PUT /api/components/<comp_id>/variables invalid payload (line 836)."""
    client, *_ = editor_env
    res = client.put("/api/components/demo-app/variables", json="not-a-dict")
    assert res.status_code == 400
    assert "Payload must be a dictionary" in res.get_data(as_text=True)


def test_create_component_empty_meta(editor_env):
    """Tests POST /api/components with empty meta (branch 858->860)."""
    client, *_ = editor_env
    res = client.post("/api/components", json={"id": "empty-meta-comp", "meta": {}})
    assert res.status_code == 201


def test_delete_group_success(editor_env):
    """Tests DELETE /api/groups/<group_id> successful deletion (line 1042)."""
    client, *_ = editor_env
    with patch("managers.component_manager.ComponentManager.delete_group") as mock_del:
        res = client.delete("/api/groups/utilities")
        assert res.status_code == 200
        assert res.get_json()["status"] == "deleted"
        assert mock_del.called


def test_ai_generate_remaining_branches_and_errors(editor_env):
    """Tests AI generate edge cases and error handling."""
    client, *_ = editor_env

    # 1. custom_component_id and save_key=True with save error (lines 1307-1308)
    with (
        patch(
            "editor_app.app.AIGenerator.generate_component_data",
            return_value={"name": "Generated"},
        ),
        patch(
            "utils.ai_provider_manager.save_api_key_to_env_file",
            side_effect=Exception("Failed to write env"),
        ),
    ):
        res_stream = client.post(
            "/api/ai/generate",
            json={
                "repo_url": "https://github.com/test/app",
                "stream": True,
                "save_key": True,
                "api_key": "test-key",
                "component_id": "custom-comp",
            },
        )
        assert res_stream.status_code == 200
        body = res_stream.get_data(as_text=True)
        assert "Generated" in body

    # 2. SSE generator timeout via queue.Empty (lines 1337-1343)
    with patch.object(queue.Queue, "get", side_effect=queue.Empty):
        res_timeout = client.post(
            "/api/ai/generate",
            json={
                "repo_url": "https://github.com/test/app",
                "stream": True,
            },
        )
        assert res_timeout.status_code == 200
        body_timeout = res_timeout.get_data(as_text=True)
        assert "Request timed out waiting for AI response." in body_timeout

    # 3. Non-streaming with save_key=True and save error (lines 1378-1379)
    with (
        patch(
            "editor_app.app.AIGenerator.generate_component_data",
            return_value={"name": "Generated"},
        ),
        patch(
            "utils.ai_provider_manager.save_api_key_to_env_file",
            side_effect=Exception("Failed to write env"),
        ),
    ):
        res_non_stream = client.post(
            "/api/ai/generate",
            json={
                "repo_url": "https://github.com/test/app",
                "save_key": True,
                "api_key": "test-key",
            },
        )
        assert res_non_stream.status_code == 200
        assert res_non_stream.get_json()["key_saved"] is False

    # 4. ValueError: "repository URL is required" -> 400 (line 1397)
    with patch(
        "editor_app.app.AIGenerator.generate_component_data",
        side_effect=ValueError("repository URL is required"),
    ):
        res_url_err = client.post(
            "/api/ai/generate",
            json={"repo_url": "https://github.com/test/app"},
        )
        assert res_url_err.status_code == 400
        err_json = res_url_err.get_json()
        assert "A valid Git repository URL is required" in err_json["error"]

    # 5. Exception: OpenAI API error -> 502 (line 1438)
    with patch(
        "editor_app.app.AIGenerator.generate_component_data",
        side_effect=Exception("OpenAI API error"),
    ):
        res_api_err = client.post(
            "/api/ai/generate",
            json={"repo_url": "https://github.com/test/app"},
        )
        assert res_api_err.status_code == 502
        assert res_api_err.get_json()["error"] == "AI API Error"


def test_save_ai_component_additional_branches(editor_env):
    """Tests save AI component edge cases and traversal validation."""
    client, meta_path, _ = editor_env

    # 1. Invalid component_id type (non-string) -> line 1473
    res_bad_id = client.post("/api/components/ai", json={"id": 12345})
    assert res_bad_id.status_code == 400
    assert "A valid component ID is required" in res_bad_id.get_data(as_text=True)

    # 2. docker_compose without services -> branch 1571->1582
    # and component_id already in components_order -> branch 1642->1644
    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
    order = meta_data.setdefault("_njorddeploy", {}).setdefault("components_order", [])
    order.append("order-app")
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    res_no_services = client.post(
        "/api/components/ai",
        json={
            "id": "order-app",
            "docker_compose": "version: '3.8'\n",
            "overwrite": True,
        },
    )
    assert res_no_services.status_code == 201

    # 3. Path traversal detection in config_templates -> line 1608
    orig_resolve = Path.resolve

    def mock_resolve(self):
        if "template-config" in str(self):
            return Path("/etc/shadow/template-config")
        return orig_resolve(self)

    with patch.object(Path, "resolve", side_effect=mock_resolve, autospec=True):
        res_traversal = client.post(
            "/api/components/ai",
            json={
                "id": "traversal-comp",
                "config_templates": {"sample.txt": "sample data"},
                "overwrite": True,
            },
        )
        assert res_traversal.status_code == 400
        assert "Path traversal attempt detected" in res_traversal.get_data(as_text=True)
