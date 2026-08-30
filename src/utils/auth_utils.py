# src/utils/auth_utils.py

import functools
import hmac
import json
import logging
import os
import re
import secrets
import stat
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

from argon2 import PasswordHasher
from argon2.low_level import Type
from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from utils.resource_utils import get_app_data_dir, is_server_mode

logger = logging.getLogger(__name__)

# Initialize the PasswordHasher with standard Argon2ID parameters for Traefik htpasswd
PH = PasswordHasher(time_cost=4, memory_cost=65536, parallelism=2, type=Type.ID)


def generate_basic_auth_hash(username: str, password: str) -> str:
    """
    Generates a username:hashed_password string suitable for Traefik and
    other basic authentication systems using the Argon2ID algorithm.
    """
    hashed_password = PH.hash(password)
    return f"{username}:{hashed_password}"


def hash_password(password: str) -> str:
    """
    Generates a secure password hash for web and user authentication.
    Uses PBKDF2 with SHA-256 for cross-platform reliability and security.
    """
    return generate_password_hash(password, method="pbkdf2:sha256")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored password hash.
    Supports Werkzeug hashes (scrypt, pbkdf2) and Argon2 hashes.
    """
    if not password or not password_hash:
        return False

    if password_hash.startswith("$argon2"):
        try:
            return PH.verify(password_hash, password)
        except Exception:
            return False

    try:
        return check_password_hash(password_hash, password)
    except Exception as ex:
        logger.debug(f"Password hash check failed with exception: {ex}")
        return False


def generate_api_key() -> str:
    """Generates a secure, cryptographically random API token."""
    return f"njord_sec_{secrets.token_hex(24)}"


def get_or_create_secret_key() -> str:
    """
    Retrieves or generates a persistent secret key for Flask session signing.
    Checks NJORD_SECRET_KEY -> FLASK_SECRET_KEY -> .secret_key file.
    """
    env_key = os.environ.get("NJORD_SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY")
    if env_key:
        return env_key.strip()

    data_dir = get_app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    key_file = data_dir / ".secret_key"

    if key_file.exists():
        try:
            content = key_file.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception as ex:
            logger.warning(f"Failed to read secret key from {key_file}: {ex}")

    new_key = secrets.token_hex(32)
    try:
        key_file.write_text(new_key + "\n", encoding="utf-8")
        key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except Exception as ex:
        logger.warning(f"Failed to persist generated secret key: {ex}")

    return new_key


def get_auth_file_path() -> Path:
    """Returns the path to the auth.json configuration file."""
    return get_app_data_dir() / "auth.json"


def load_auth_config() -> Optional[dict[str, Any]]:
    """
    Loads and parses the auth.json file from the application data directory.
    Returns the parsed dictionary or None if unconfigured/invalid.
    """
    auth_file = get_auth_file_path()
    if not auth_file.exists():
        return None

    try:
        raw_text = auth_file.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        if isinstance(data, dict) and "username" in data and "password_hash" in data:
            return data
    except Exception as ex:
        logger.error(f"Failed to load auth config from {auth_file}: {ex}")

    return None


def save_auth_config(
    username: str,
    password_hash: str,
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    Saves or updates the administrator credentials and API token in auth.json.
    Ensures secure 0600 file permissions.
    """
    auth_file = get_auth_file_path()
    auth_file.parent.mkdir(parents=True, exist_ok=True)

    existing = load_auth_config() or {}
    now_iso = datetime.now(timezone.utc).isoformat()

    resolved_api_key = api_key or existing.get("api_key") or generate_api_key()

    auth_data = {
        "username": username.strip(),
        "password_hash": password_hash,
        "api_key": resolved_api_key,
        "created_at": existing.get("created_at", now_iso),
        "updated_at": now_iso,
    }

    temp_file = auth_file.with_suffix(".tmp")
    temp_file.write_text(json.dumps(auth_data, indent=2) + "\n", encoding="utf-8")
    temp_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
    temp_file.replace(auth_file)

    return auth_data


def is_admin_configured() -> bool:
    """
    Returns True if an administrator account is configured via auth.json
    or environment variables (NJORD_ADMIN_USER and NJORD_ADMIN_PASSWORD/HASH).
    """
    config = load_auth_config()
    if config and config.get("username") and config.get("password_hash"):
        return True

    env_user = os.environ.get("NJORD_ADMIN_USER")
    env_pass = os.environ.get("NJORD_ADMIN_PASSWORD")
    env_hash = os.environ.get("NJORD_ADMIN_HASH")
    if env_user and (env_pass or env_hash):
        return True

    return False


def is_auth_enabled() -> bool:
    """
    Determines whether authentication enforcement is active.
    Authentication is enabled if explicitly requested via NJORD_AUTH_ENABLED,
    if running in server daemon mode (NJORD_SERVER_MODE=true), or if auth.json exists.
    """
    env_flag = os.environ.get("NJORD_AUTH_ENABLED", "").lower()
    if env_flag in ("true", "1", "yes", "enabled"):
        return True
    if env_flag in ("false", "0", "no", "disabled"):
        return False

    if is_server_mode():
        return True

    if is_admin_configured():
        return True

    return False


def verify_credentials(username: str, password: str) -> bool:
    """
    Validates provided username and password against configured admin credentials.
    """
    if not username or not password:
        return False

    clean_user = username.strip().lower()

    # 1. Check environment variable override
    env_user = os.environ.get("NJORD_ADMIN_USER", "").strip().lower()
    if env_user and env_user == clean_user:
        env_hash = os.environ.get("NJORD_ADMIN_HASH")
        if env_hash and verify_password(password, env_hash):
            return True
        env_pass = os.environ.get("NJORD_ADMIN_PASSWORD")
        if env_pass and hmac.compare_digest(password, env_pass):
            return True

    # 2. Check auth.json
    config = load_auth_config()
    if not config:
        return False

    stored_user = str(config.get("username", "")).strip().lower()
    stored_hash = str(config.get("password_hash", ""))

    if stored_user == clean_user and stored_hash:
        return verify_password(password, stored_hash)

    # 3. Check Multi-Tenant Database
    try:
        from managers.database_manager import DatabaseManager

        db_user = DatabaseManager.get_instance().get_user_by_username(username)
        if db_user and db_user.get("password_hash"):
            return verify_password(password, str(db_user["password_hash"]))
    except Exception as e:
        logger.debug(f"Database user credential check exception: {e}")

    return False


def verify_api_key(provided_key: Optional[str]) -> bool:
    """
    Validates an API token against NJORD_API_KEY environment variable, auth.json,
    or multi-tenant user API keys in SQLite database.
    Uses constant-time comparison to prevent timing attacks.
    """
    if not provided_key or not isinstance(provided_key, str):
        return False

    clean_provided = provided_key.strip()
    if not clean_provided:
        return False

    env_key = os.environ.get("NJORD_API_KEY")
    if env_key and hmac.compare_digest(clean_provided, env_key.strip()):
        return True

    config = load_auth_config()
    if config:
        stored_key = config.get("api_key")
        if stored_key and hmac.compare_digest(clean_provided, str(stored_key).strip()):
            return True

    # Check multi-tenant database for user API keys
    try:
        from managers.database_manager import DatabaseManager

        db_user = DatabaseManager.get_instance().get_user_by_api_key(clean_provided)
        if db_user:
            return True
    except Exception as e:
        logger.debug(f"Database user API key check exception: {e}")

    return False


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a username meets format and length requirements.
    """
    clean = (username or "").strip()
    if len(clean) < 3:
        return False, "Username must be at least 3 characters long."
    if len(clean) > 32:
        return False, "Username must not exceed 32 characters."
    if not re.match(r"^[a-zA-Z0-9_.-]+$", clean):
        return (
            False,
            "Username can only contain alphanumeric characters, dots, "
            "underscores, and hyphens.",
        )
    return True, None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validates password strength (minimum 8 characters).
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 256:
        return False, "Password must not exceed 256 characters."
    return True, None


def get_client_ip(req: Any) -> str:
    """
    Extracts the client IP address from the request, respecting X-Forwarded-For.
    Follows the Unpacking-First Mandate for header parsing.
    """
    forwarded = req.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",")]
        client_ip, *_ = parts
        if client_ip:
            return client_ip

    return str(req.remote_addr or "127.0.0.1")


class LoginRateLimiter:
    """
    In-memory, thread-safe sliding window rate limiter for login attempts.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}

    def record_failure(self, client_ip: str) -> None:
        """Records a failed authentication attempt for a given IP."""
        now = time.time()
        with self._lock:
            attempts = self._failures.setdefault(client_ip, [])
            attempts.append(now)
            self._failures[client_ip] = [
                t for t in attempts if now - t < self.window_seconds
            ]

    def is_rate_limited(self, client_ip: str) -> Tuple[bool, int]:
        """
        Checks if an IP has exceeded the allowed failure attempts.
        Returns (is_limited, retry_after_seconds).
        Follows the Unpacking-First Mandate.
        """
        now = time.time()
        with self._lock:
            attempts = self._failures.get(client_ip, [])
            valid_attempts = [t for t in attempts if now - t < self.window_seconds]
            self._failures[client_ip] = valid_attempts

            if len(valid_attempts) >= self.max_attempts:
                earliest, *_ = valid_attempts
                retry_after = int(self.window_seconds - (now - earliest))
                return True, max(1, retry_after)

            return False, 0

    def record_success(self, client_ip: str) -> None:
        """Clears the failure counter on successful authentication."""
        with self._lock:
            self._failures.pop(client_ip, None)


GLOBAL_RATE_LIMITER = LoginRateLimiter()


def is_api_request() -> bool:
    """
    Determines whether the incoming request is an API request expecting JSON
    or a browser page navigation.
    """
    path = request.path
    api_prefixes = (
        "/api/",
        "/stream-",
        "/scan-",
        "/start-",
        "/deploy-",
        "/get-",
        "/validate-",
        "/set-",
        "/task-status/",
        "/nmap-status",
        "/tailscale-status",
    )
    if any(path.startswith(prefix) for prefix in api_prefixes):
        return True
    if request.is_json:
        return True
    accept = request.headers.get("Accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return True
    return False


def extract_api_key_from_request(req: Any) -> Optional[str]:
    """
    Extracts the API token from headers (X-Njord-API-Key or Authorization Bearer)
    or query parameters. Follows the Unpacking-First Mandate.
    """
    header_key = req.headers.get("X-Njord-API-Key")
    if header_key:
        return str(header_key).strip()

    auth_header = req.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        parts = auth_header.split(" ", 1)
        _, bearer_token = parts
        if bearer_token:
            return bearer_token.strip()

    query_key = req.args.get("api_key")
    if query_key:
        return str(query_key).strip()

    return None


def login_required(f: Callable) -> Callable:
    """
    Decorator that requires an active user session or valid API token.
    """

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_auth_enabled():
            return f(*args, **kwargs)

        if session.get("logged_in") and session.get("user"):
            return f(*args, **kwargs)

        api_key = extract_api_key_from_request(request)
        if api_key and verify_api_key(api_key):
            return f(*args, **kwargs)

        if is_api_request():
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": (
                            "Authentication required. Provide a valid session or "
                            "API key via X-Njord-API-Key."
                        ),
                    }
                ),
                401,
            )

        return redirect(url_for("login_page", next=request.full_path))

    return decorated_function
