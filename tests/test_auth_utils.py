from pathlib import Path
from unittest.mock import MagicMock

# noinspection PyUnresolvedReferences
from passlib.hash import argon2

from src.utils.auth_utils import (
    LoginRateLimiter,
    extract_api_key_from_request,
    generate_api_key,
    generate_basic_auth_hash,
    get_client_ip,
    get_or_create_secret_key,
    hash_password,
    is_admin_configured,
    is_api_request,
    is_auth_enabled,
    load_auth_config,
    save_auth_config,
    validate_password_strength,
    validate_username,
    verify_api_key,
    verify_credentials,
    verify_password,
)


def test_generate_basic_auth_hash_creates_valid_argon2_output():
    """Test that the function generates a securely hashed string in the
    'username:hash' format using the Argon2ID algorithm.
    """
    username = "testuser"
    password = "SecurePassword123"

    result_string = generate_basic_auth_hash(username, password)

    assert result_string.startswith(f"{username}:")
    assert ":" in result_string

    parts = result_string.split(":", 1)
    unpacked_username, hash_string = parts  # Unpacking-First Mandate

    assert hash_string.startswith("$argon2id$")
    assert argon2.verify(password, hash_string)


def test_generate_basic_auth_hash_is_unique_on_each_call():
    """Test that calling the function twice with the same input yields two
    DIFFERENT hashes, verifying that a unique salt is generated.
    """
    username = "testuser"
    password = "SecurePassword123"

    hash_one = generate_basic_auth_hash(username, password)
    hash_two = generate_basic_auth_hash(username, password)

    assert hash_one != hash_two

    parts_one = hash_one.split(":", 1)
    parts_two = hash_two.split(":", 1)

    _, hash_one_string = parts_one  # Unpacking-First Mandate
    _, hash_two_string = parts_two  # Unpacking-First Mandate

    assert argon2.verify(password, hash_one_string)
    assert argon2.verify(password, hash_two_string)


def test_password_hashing_and_verification():
    """Tests password hashing with PBKDF2/Werkzeug and verification."""
    password = "MyStrongAdminPassword123!"
    pw_hash = hash_password(password)

    assert pw_hash.startswith("pbkdf2:sha256:")
    assert verify_password(password, pw_hash) is True
    assert verify_password("WrongPassword", pw_hash) is False
    assert verify_password("", pw_hash) is False
    assert verify_password(password, "") is False


def test_argon2_hash_verification():
    """Tests that verify_password can also verify Argon2 hashes."""
    username = "admin"
    password = "ArgonPassword789!"
    auth_str = generate_basic_auth_hash(username, password)
    parts = auth_str.split(":", 1)
    _, hash_val = parts  # Unpacking-First Mandate

    assert verify_password(password, hash_val) is True
    assert verify_password("WrongPass", hash_val) is False


def test_api_key_generation_and_verification(tmp_path, monkeypatch):
    """Tests generating and verifying API keys."""
    monkeypatch.setenv("NJORD_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("NJORD_API_KEY", raising=False)

    key = generate_api_key()
    assert key.startswith("njord_sec_")
    assert len(key) >= 40

    # Save to auth.json
    pw_hash = hash_password("Secret12345")
    save_auth_config("admin", pw_hash, api_key=key)

    assert verify_api_key(key) is True
    assert verify_api_key("njord_sec_invalid") is False
    assert verify_api_key("") is False
    assert verify_api_key(None) is False

    # Test environment variable override for API key
    monkeypatch.setenv("NJORD_API_KEY", "custom_env_token_xyz")
    assert verify_api_key("custom_env_token_xyz") is True
    assert verify_api_key(key) is True


def test_secret_key_generation_and_persistence(tmp_path, monkeypatch):
    """Tests that persistent .secret_key is created and reused."""
    monkeypatch.setenv("NJORD_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("NJORD_SECRET_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)

    key1 = get_or_create_secret_key()
    assert len(key1) == 64  # 32 bytes hex
    secret_file = tmp_path / ".secret_key"
    assert secret_file.exists()

    # Second call should read existing key
    key2 = get_or_create_secret_key()
    assert key1 == key2

    # Environment variable takes priority
    monkeypatch.setenv("NJORD_SECRET_KEY", "explicit_env_secret")
    assert get_or_create_secret_key() == "explicit_env_secret"


def test_auth_config_lifecycle(tmp_path, monkeypatch):
    """Tests saving, loading, and verifying admin credentials."""
    monkeypatch.setenv("NJORD_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("NJORD_ADMIN_USER", raising=False)
    monkeypatch.delenv("NJORD_ADMIN_PASSWORD", raising=False)
    assert is_admin_configured() is False
    assert is_auth_enabled() is False
    assert load_auth_config() is None

    pw_hash = hash_password("SuperSecretPass123")
    saved = save_auth_config("sysadmin", pw_hash)

    assert saved["username"] == "sysadmin"
    assert is_admin_configured() is True
    assert is_auth_enabled() is True

    loaded = load_auth_config()
    assert loaded is not None
    assert loaded["username"] == "sysadmin"

    assert verify_credentials("sysadmin", "SuperSecretPass123") is True
    assert verify_credentials("sysadmin", "WrongPass") is False
    assert verify_credentials("otheruser", "SuperSecretPass123") is False


def test_validation_helpers():
    """Tests username and password strength validation."""
    valid_u, err_u = validate_username("admin_123")
    assert valid_u is True
    assert err_u is None

    invalid_u, err_u = validate_username("a")
    assert invalid_u is False
    assert "at least 3 characters" in str(err_u)

    invalid_chars, err_chars = validate_username("admin@invalid spaces!")
    assert invalid_chars is False
    assert "alphanumeric" in str(err_chars)

    valid_p, err_p = validate_password_strength("LongEnoughPassword123")
    assert valid_p is True
    assert err_p is None

    short_p, err_p = validate_password_strength("short")
    assert short_p is False
    assert "at least 8 characters" in str(err_p)


def test_rate_limiter():
    """Tests the in-memory sliding window rate limiter."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    ip = "192.168.1.100"

    assert limiter.is_rate_limited(ip) == (False, 0)

    limiter.record_failure(ip)
    assert limiter.is_rate_limited(ip) == (False, 0)

    limiter.record_failure(ip)
    assert limiter.is_rate_limited(ip) == (False, 0)

    limiter.record_failure(ip)
    is_limited, retry_after = limiter.is_rate_limited(ip)
    assert is_limited is True
    assert retry_after > 0

    # Successful login resets the rate limit
    limiter.record_success(ip)
    assert limiter.is_rate_limited(ip) == (False, 0)


def test_get_client_ip():
    """Tests client IP extraction with X-Forwarded-For."""
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    req.remote_addr = "10.0.0.1"

    ip = get_client_ip(req)
    assert ip == "203.0.113.195"

    req.headers = {}
    ip2 = get_client_ip(req)
    assert ip2 == "10.0.0.1"


def test_extract_api_key_from_request():
    """Tests extraction of API tokens from headers and query parameters."""
    # Header X-Njord-API-Key
    req1 = MagicMock()
    req1.headers = {"X-Njord-API-Key": "key_from_header"}
    req1.args = {}
    assert extract_api_key_from_request(req1) == "key_from_header"

    # Header Authorization: Bearer
    req2 = MagicMock()
    req2.headers = {"Authorization": "Bearer key_from_bearer"}
    req2.args = {}
    assert extract_api_key_from_request(req2) == "key_from_bearer"

    # Query param ?api_key=
    req3 = MagicMock()
    req3.headers = {}
    req3.args = {"api_key": "key_from_query"}
    assert extract_api_key_from_request(req3) == "key_from_query"

    # None when no key
    req4 = MagicMock()
    req4.headers = {}
    req4.args = {}
    assert extract_api_key_from_request(req4) is None


def test_auth_validation_boundaries():
    """Tests extreme length and formatting boundary conditions for usernames
    and passwords.
    """
    ok, err = validate_username("a" * 33)
    assert ok is False
    assert "must not exceed 32 characters" in str(err)

    ok, err = validate_username("invalid user with spaces!")
    assert ok is False
    assert "alphanumeric" in str(err)

    ok, err = validate_password_strength("a" * 257)
    assert ok is False
    assert "must not exceed 256 characters" in str(err)


def test_auth_enabled_and_admin_configured_variations(monkeypatch, tmp_path):
    """Tests diverse environment flags for auth enabled and admin configuration."""
    monkeypatch.setenv("NJORD_DATA_DIR", str(tmp_path))

    # NJORD_AUTH_ENABLED variants
    monkeypatch.setenv("NJORD_AUTH_ENABLED", "enabled")
    assert is_auth_enabled() is True

    monkeypatch.setenv("NJORD_AUTH_ENABLED", "disabled")
    assert is_auth_enabled() is False

    monkeypatch.delenv("NJORD_AUTH_ENABLED", raising=False)
    monkeypatch.setenv("NJORD_SERVER_MODE", "true")
    assert is_auth_enabled() is True

    monkeypatch.delenv("NJORD_SERVER_MODE", raising=False)
    # NJORD_ADMIN_HASH
    monkeypatch.setenv("NJORD_ADMIN_USER", "env_admin")
    monkeypatch.setenv("NJORD_ADMIN_HASH", hash_password("AdminPass123"))
    assert is_admin_configured() is True
    assert verify_credentials("env_admin", "AdminPass123") is True
    assert verify_credentials("env_admin", "WrongPass") is False


def test_verify_credentials_with_database_user(tmp_path, monkeypatch):
    """Tests that verify_credentials checks multi-tenant DatabaseManager users."""
    from managers.database_manager import DatabaseManager

    db_file = tmp_path / "auth_db_test.db"
    db = DatabaseManager(db_file)
    monkeypatch.setattr(DatabaseManager, "get_instance", lambda: db)
    monkeypatch.setenv("NJORD_DATA_DIR", str(tmp_path))

    user_pass = "DbSecretPassword123"
    db.create_user(
        "tenant_user",
        hash_password(user_pass),
        api_key="njord_sec_tenant_valid_key",
    )

    assert verify_credentials("tenant_user", user_pass) is True
    assert verify_credentials("tenant_user", "wrong_pass") is False
    assert verify_api_key("njord_sec_tenant_valid_key") is True
    assert verify_api_key("njord_sec_invalid_key") is False


def test_corrupt_auth_config_and_secret_key(tmp_path, monkeypatch):
    """Tests handling of corrupt auth.json and unreadable .secret_key file."""
    monkeypatch.setenv("NJORD_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("NJORD_SECRET_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)

    auth_file = tmp_path / "auth.json"
    auth_file.write_text("NOT A VALID JSON", encoding="utf-8")
    assert load_auth_config() is None

    # Secret key generation
    secret = get_or_create_secret_key()
    assert secret is not None
    assert len(secret) >= 32
    # Second read retrieves existing
    assert get_or_create_secret_key() == secret


def test_login_required_decorator(monkeypatch):
    """Tests login_required decorator across API, browser, and authenticated states."""
    from flask import Flask

    from utils.auth_utils import login_required

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"

    @app.route("/login")
    def login_page():
        return "Login Page", 200

    @app.route("/api/protected", methods=["GET"])
    @login_required
    def api_protected():
        return {"status": "ok"}, 200

    @app.route("/protected-page", methods=["GET"])
    @login_required
    def page_protected():
        return "Protected Content", 200

    client = app.test_client()

    # 1. Auth disabled
    monkeypatch.setattr("utils.auth_utils.is_auth_enabled", lambda: False)
    res = client.get("/api/protected")
    assert res.status_code == 200

    # 2. Auth enabled - unauthenticated API request -> 401 JSON
    monkeypatch.setattr("utils.auth_utils.is_auth_enabled", lambda: True)
    monkeypatch.setattr("utils.auth_utils.verify_api_key", lambda k: False)
    res_api = client.get("/api/protected")
    assert res_api.status_code == 401
    assert "Unauthorized" in res_api.get_json()["error"]

    # 3. Auth enabled - unauthenticated browser request -> 302 redirect
    res_page = client.get("/protected-page")
    assert res_page.status_code == 302
    assert "/login" in res_page.headers["Location"]

    # 4. Auth enabled - valid API Key -> 200 OK
    monkeypatch.setattr("utils.auth_utils.verify_api_key", lambda k: k == "valid_key")
    res_key = client.get("/api/protected", headers={"X-Njord-API-Key": "valid_key"})
    assert res_key.status_code == 200

    # 5. Auth enabled - valid session -> 200 OK
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user"] = "admin"
    res_sess = client.get("/protected-page")
    assert res_sess.status_code == 200

    # 6. JSON header / request detection in login_required (unauthenticated)
    with client.session_transaction() as sess:
        sess.clear()
    res_json_accept = client.get(
        "/protected-page", headers={"Accept": "application/json"}
    )
    assert res_json_accept.status_code == 401


def test_auth_utils_edge_cases_and_exceptions(tmp_path, monkeypatch):
    """Test exception branches, secret key IO errors, and db failures."""
    from unittest.mock import patch

    # 1. verify_password exception
    with patch(
        "src.utils.auth_utils.check_password_hash",
        side_effect=Exception("hash err"),
    ):
        assert verify_password("pwd", "pbkdf2:sha256:1000$bad") is False

    # 2. get_or_create_secret_key IO errors
    monkeypatch.delenv("NJORD_SECRET_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setenv("NJORD_DATA_DIR", str(tmp_path))
    dummy_key_file = tmp_path / ".secret_key"
    dummy_key_file.touch()

    with patch.object(Path, "read_text", side_effect=IOError("read fail")):
        with patch.object(Path, "write_text", side_effect=IOError("write fail")):
            k = get_or_create_secret_key()
            assert len(k) == 64

    # 3. verify_credentials empty and env plaintext password
    assert verify_credentials("", "pass") is False
    assert verify_credentials("admin", "") is False

    monkeypatch.setenv("NJORD_ADMIN_USER", "envadmin")
    monkeypatch.setenv("NJORD_ADMIN_PASSWORD", "plainsecret")
    assert verify_credentials("envadmin", "plainsecret") is True

    # 4. verify_credentials and verify_api_key DB exceptions
    monkeypatch.delenv("NJORD_ADMIN_USER", raising=False)
    monkeypatch.delenv("NJORD_ADMIN_PASSWORD", raising=False)
    with patch("src.utils.auth_utils.load_auth_config", return_value=None):
        with patch(
            "managers.database_manager.DatabaseManager.get_instance",
            side_effect=Exception("db dead"),
        ):
            assert verify_credentials("user", "pass") is False
            assert verify_api_key("token123") is False

    # 5. verify_api_key empty inputs
    assert verify_api_key("") is False
    assert verify_api_key("   ") is False
    assert verify_api_key(None) is False

    # 6. is_api_request with is_json=True on non-standard route
    from flask import Flask

    test_flask_app = Flask("test_auth_req")
    with test_flask_app.test_request_context(
        "/custom-non-api-route",
        json={"data": 123},
    ):
        assert is_api_request() is True
