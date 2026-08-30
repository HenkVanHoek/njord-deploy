import pytest

from configurator_app.app import create_app
from utils.auth_utils import hash_password, save_auth_config


@pytest.fixture
def auth_env(tmp_path, monkeypatch):
    """Sets up a clean temporary data environment for auth tests."""
    data_dir = tmp_path / "njord_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("NJORD_DATA_DIR", str(data_dir))
    monkeypatch.delenv("NJORD_ADMIN_USER", raising=False)
    monkeypatch.delenv("NJORD_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("NJORD_ADMIN_HASH", raising=False)
    monkeypatch.delenv("NJORD_API_KEY", raising=False)
    monkeypatch.delenv("NJORD_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("NJORD_SERVER_MODE", raising=False)
    return data_dir


def test_whitelisted_health_routes_publicly_accessible(auth_env, monkeypatch):
    """Verifies that /health, /api/health, and /api/v1/health are accessible
    without any authentication even when server mode is active.
    """
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")
    app = create_app({"TESTING": True})
    client = app.test_client()

    for endpoint in ["/health", "/api/health", "/api/v1/health"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


def test_first_run_setup_redirection(auth_env, monkeypatch):
    """Verifies that in server mode without admin configured, web requests
    are redirected to /setup and API requests return 401 with setup_required.
    """
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")
    app = create_app({"TESTING": True})
    client = app.test_client()

    # Web UI GET request -> redirect to /setup
    response = client.get("/")
    assert response.status_code == 302
    assert "/setup" in response.headers["Location"]

    # REST API request -> 401 JSON error
    api_resp = client.post("/scan-pis", json={"discovery_method": "direct_ip"})
    assert api_resp.status_code == 401
    data = api_resp.get_json()
    assert data["setup_required"] is True


def test_first_run_setup_wizard_flow(auth_env, monkeypatch):
    """Verifies the complete onboarding setup wizard flow."""
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")
    app = create_app({"TESTING": True})
    client = app.test_client()

    # GET /setup renders setup page
    get_setup = client.get("/setup")
    assert get_setup.status_code == 200
    assert b"NjordDeploy Setup Wizard" in get_setup.data

    # POST /api/setup with weak password (< 8 chars) fails
    weak_resp = client.post(
        "/api/setup",
        json={
            "username": "admin",
            "password": "123",
            "confirm_password": "123",
        },
    )
    assert weak_resp.status_code == 400
    assert "at least 8 characters" in weak_resp.get_json()["error"]

    # POST /api/setup with mismatched passwords fails
    mismatch_resp = client.post(
        "/api/setup",
        json={
            "username": "admin",
            "password": "StrongPassword123!",
            "confirm_password": "DifferentPassword123!",
        },
    )
    assert mismatch_resp.status_code == 400
    assert "do not match" in mismatch_resp.get_json()["error"]

    # POST /api/setup with valid credentials succeeds
    success_resp = client.post(
        "/api/setup",
        json={
            "username": "admin",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        },
    )
    assert success_resp.status_code == 200
    data = success_resp.get_json()
    assert data["status"] == "success"
    assert data["api_key"].startswith("njord_sec_")

    # Subsequent call to /setup should now be locked (403 or redirect)
    locked_resp = client.post(
        "/api/setup",
        json={
            "username": "hacker",
            "password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )
    assert locked_resp.status_code == 403


def test_login_and_session_management(auth_env, monkeypatch):
    """Verifies authentication, session cookie issuance, and logout."""
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")
    # Pre-configure admin credentials
    pw_hash = hash_password("ValidPassword123!")
    save_auth_config("admin", pw_hash)

    app = create_app({"TESTING": True})
    client = app.test_client()

    # Unauthenticated request to / returns redirect to /login
    unauth_resp = client.get("/")
    assert unauth_resp.status_code == 302
    assert "/login" in unauth_resp.headers["Location"]

    # Login with wrong password returns 401
    bad_login = client.post(
        "/api/login",
        json={"username": "admin", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401
    assert "Invalid username or password" in bad_login.get_json()["error"]

    # Login with correct credentials returns 200 and sets session cookie
    good_login = client.post(
        "/api/login",
        json={"username": "admin", "password": "ValidPassword123!"},
    )
    assert good_login.status_code == 200
    assert good_login.get_json()["status"] == "authenticated"

    # Authenticated user can now access /
    index_resp = client.get("/")
    assert index_resp.status_code == 200

    # Logout terminates session
    logout_resp = client.post("/api/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.get_json()["status"] == "logged_out"

    # Subsequent access to / redirects to /login again
    post_logout_resp = client.get("/")
    assert post_logout_resp.status_code == 302
    assert "/login" in post_logout_resp.headers["Location"]


def test_api_token_header_authentication(auth_env, monkeypatch):
    """Verifies that API requests authenticate with X-Njord-API-Key and
    Authorization: Bearer headers without requiring a session cookie.
    """
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")
    pw_hash = hash_password("ValidPassword123!")
    test_key = "njord_sec_abcdef1234567890abcdef1234567890"
    save_auth_config("admin", pw_hash, api_key=test_key)

    app = create_app({"TESTING": True})
    client = app.test_client()

    # Unauthenticated API call to /api/components -> 401
    unauth_api = client.get("/api/components")
    assert unauth_api.status_code == 401

    # Authenticated via X-Njord-API-Key header -> 200
    headers_custom = {"X-Njord-API-Key": test_key}
    auth_custom = client.get("/api/components", headers=headers_custom)
    assert auth_custom.status_code == 200

    # Authenticated via Authorization: Bearer <token> -> 200
    headers_bearer = {"Authorization": f"Bearer {test_key}"}
    auth_bearer = client.get("/api/components", headers=headers_bearer)
    assert auth_bearer.status_code == 200

    # Invalid API token -> 401
    headers_invalid = {"X-Njord-API-Key": "njord_sec_invalid_key_xyz"}
    bad_api = client.get("/api/components", headers=headers_invalid)
    assert bad_api.status_code == 401


def test_login_rate_limiting(auth_env, monkeypatch):
    """Verifies that brute force attempts on /login are rate-limited with 429."""
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")
    pw_hash = hash_password("CorrectAdminPassword123!")
    save_auth_config("admin", pw_hash)

    app = create_app({"TESTING": True})
    client = app.test_client()

    # Submit 5 consecutive failed login attempts
    for _ in range(5):
        client.post(
            "/api/login",
            json={"username": "admin", "password": "WrongPassword"},
            headers={"X-Forwarded-For": "198.51.100.42"},
        )

    # 6th attempt should receive HTTP 429 Too Many Requests
    rate_limited_resp = client.post(
        "/api/login",
        json={"username": "admin", "password": "WrongPassword"},
        headers={"X-Forwarded-For": "198.51.100.42"},
    )
    assert rate_limited_resp.status_code == 429
    data = rate_limited_resp.get_json()
    assert "Too many failed login attempts" in data["error"]
    assert "retry_after" in data


def test_regenerate_api_key_and_change_password(auth_env, monkeypatch):
    """Verifies regenerating API token and changing administrator password."""
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")
    pw_hash = hash_password("InitialPassword123!")
    initial_key = "njord_sec_initial_key_12345"
    save_auth_config("admin", pw_hash, api_key=initial_key)

    app = create_app({"TESTING": True})
    client = app.test_client()

    # Login to establish session
    client.post(
        "/api/login",
        json={"username": "admin", "password": "InitialPassword123!"},
    )

    # Regenerate API Key
    regen_resp = client.post("/api/auth/regenerate-api-key")
    assert regen_resp.status_code == 200
    new_key = regen_resp.get_json()["api_key"]
    assert new_key != initial_key
    assert new_key.startswith("njord_sec_")

    # Logout session to test standalone API key validation
    client.post("/api/logout")

    # Verify old key no longer works
    old_call = client.get("/api/components", headers={"X-Njord-API-Key": initial_key})
    assert old_call.status_code == 401

    # Verify new key works
    new_call = client.get("/api/components", headers={"X-Njord-API-Key": new_key})
    assert new_call.status_code == 200

    # Change password
    # Login again to test password change
    client.post(
        "/api/login",
        json={"username": "admin", "password": "InitialPassword123!"},
    )
    change_resp = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "InitialPassword123!",
            "new_password": "NewUpdatedPassword123!",
            "confirm_password": "NewUpdatedPassword123!",
        },
    )
    assert change_resp.status_code == 200
    assert change_resp.get_json()["status"] == "success"

    # Logout and verify login with new password
    client.post("/api/logout")

    login_new = client.post(
        "/api/login",
        json={"username": "admin", "password": "NewUpdatedPassword123!"},
    )
    assert login_new.status_code == 200


def test_standalone_desktop_mode_without_auth_does_not_block(auth_env, monkeypatch):
    """Verifies that standalone local desktop mode does not block local usage
    when NJORD_SERVER_MODE is unset and auth.json does not exist.
    """
    monkeypatch.delenv("NJORD_SERVER_MODE", raising=False)
    monkeypatch.delenv("NJORD_AUTH_ENABLED", raising=False)

    app = create_app({"TESTING": True})
    client = app.test_client()

    # Web UI is directly accessible without redirection
    response = client.get("/")
    assert response.status_code == 200
