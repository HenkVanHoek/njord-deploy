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
