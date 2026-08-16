"""AI Provider Manager for NjordDeploy.

Manages registration, configuration resolution, and persistence of AI providers
(Ollama, Google Gemini, HostYourAI, OpenAI, Custom Endpoints).

Architecture Note on Google Gemini:
Google Gemini is integrated via its official OpenAI-compatible endpoint
(`https://generativelanguage.googleapis.com/v1beta/openai/`). This allows
AIGeneratorEngine to use a single unified OpenAI client across all local
and cloud providers without fragmented SDK dependencies (e.g. google-genai).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


DEFAULT_PROVIDERS_REGISTRY: Dict[str, Any] = {
    "ollama": {
        "name": "Ollama Local (RTX 3060)",
        "env_var": None,
        "requires_api_key": False,
        "default_base_url": "http://localhost:11434/v1",
        "allow_custom_base_url": True,
        "default_model": "qwen2.5-coder:14b-instruct-q4_K_M",
        "models": [],
    },
    "gemini": {
        "name": "Google Gemini",
        "env_var": "GEMINI_API_KEY",
        "requires_api_key": True,
        # Uses Google's official OpenAI-compatible Chat Completions endpoint
        "default_base_url": (
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        ),
        "allow_custom_base_url": False,
        "default_model": "gemini-2.5-flash",
        "models": [],
    },
    "hostyourai": {
        "name": "HostYourAI / Loes (EU)",
        "env_var": "HOSTYOURAI_API_KEY",
        "requires_api_key": True,
        "default_base_url": "https://api.hostyourai.eu/v1",
        "allow_custom_base_url": True,
        "default_model": "mistral-7b-instruct",
        "models": [],
    },
    "openai": {
        "name": "OpenAI",
        "env_var": "OPENAI_API_KEY",
        "requires_api_key": True,
        "default_base_url": "https://api.openai.com/v1",
        "allow_custom_base_url": False,
        "default_model": "gpt-4o-mini",
        "models": [],
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "env_var": "ANTHROPIC_API_KEY",
        "requires_api_key": True,
        "default_base_url": "https://api.anthropic.com/v1",
        "allow_custom_base_url": False,
        "default_model": "claude-3-5-sonnet-20241022",
        "models": [],
    },
    "custom": {
        "name": "Custom Endpoint",
        "env_var": "CUSTOM_AI_API_KEY",
        "requires_api_key": False,
        "default_base_url": "http://localhost:11434/v1",
        "allow_custom_base_url": True,
        "default_model": "default",
        "models": [],
    },
}


def _parse_float_or_none(val: Optional[str]) -> Optional[float]:
    """Safely parses a string value to float, returning None on failure."""
    if not val:
        return None
    # noinspection PyBroadException
    try:
        return float(val.strip())
    except (ValueError, TypeError) as ex:
        logger.debug("Failed to parse float timeout value '%s': %s", val, ex)
        return None


def get_ai_timeout(provider: str, base_url: Optional[str] = None) -> float:
    """Calculates timeout in seconds based on provider locality and env vars.

    - Local providers (Ollama, localhost / 127.0.0.1):
      Reads AI_LOCALHOST_TIMEOUT (default 120.0s), with fallback to
      AI_TIMEOUT / AI_TIME_OUT.
    - Cloud/remote providers (HostYourAI, OpenAI, Gemini, Anthropic, etc.):
      Reads AI_TIMEOUT or AI_TIME_OUT (default 90.0s).
    """
    url_str = (base_url or "").lower()
    is_local = provider == "ollama" or "localhost" in url_str or "127.0.0.1" in url_str

    if is_local:
        timeout = _parse_float_or_none(os.getenv("AI_LOCALHOST_TIMEOUT"))
        if timeout is not None:
            return timeout

        fallback = _parse_float_or_none(
            os.getenv("AI_TIMEOUT") or os.getenv("AI_TIME_OUT")
        )
        if fallback is not None:
            return fallback
        return 120.0

    # Remote / cloud provider
    remote_timeout = _parse_float_or_none(
        os.getenv("AI_TIMEOUT") or os.getenv("AI_TIME_OUT")
    )
    if remote_timeout is not None:
        return remote_timeout
    return 90.0


def get_providers_json_path() -> Path:
    """Returns the path to the ai_providers.json configuration file."""
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    return project_root / "config" / "ai_providers.json"


def load_ai_providers_registry() -> Dict[str, Any]:
    """Loads the AI providers registry from config/ai_providers.json."""
    json_path = get_providers_json_path()
    if not json_path.exists():
        logger.warning(f"AI providers config file not found at {json_path}")
        return DEFAULT_PROVIDERS_REGISTRY

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("providers", DEFAULT_PROVIDERS_REGISTRY)
    except Exception as e:
        logger.error(f"Failed to load AI providers registry: {e}")
        return DEFAULT_PROVIDERS_REGISTRY


def get_provider_resolved_config(
    provider: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolves full configuration for a given provider combining defaults,

    environment variables, and runtime overrides.
    """
    registry = load_ai_providers_registry()

    if provider not in registry:
        raise ValueError(f"Unsupported AI provider: {provider}")

    provider_def = registry[provider]
    env_var = provider_def.get("env_var")

    # Determine API key: explicit override -> env var -> dummy fallback
    resolved_api_key = api_key
    if not resolved_api_key and env_var:
        resolved_api_key = os.getenv(env_var)

    if not resolved_api_key:
        resolved_api_key = os.getenv(f"{provider.upper()}_API_KEY", "")

    # Determine Base URL
    resolved_base_url = base_url
    if not resolved_base_url:
        if env_var and f"{provider.upper()}_BASE_URL" in os.environ:
            resolved_base_url = os.getenv(f"{provider.upper()}_BASE_URL")
        elif provider == "ollama" and os.getenv("OLLAMA_BASE_URL"):
            resolved_base_url = os.getenv("OLLAMA_BASE_URL")
        elif provider == "custom" and os.getenv("CUSTOM_AI_BASE_URL"):
            resolved_base_url = os.getenv("CUSTOM_AI_BASE_URL")
        else:
            resolved_base_url = provider_def.get("default_base_url")

    # Determine Model
    resolved_model = model
    if not resolved_model:
        if provider == "ollama" and os.getenv("OLLAMA_MODEL"):
            resolved_model = os.getenv("OLLAMA_MODEL")
        else:
            resolved_model = provider_def.get("default_model")

    return {
        "provider": provider,
        "name": provider_def.get("name"),
        "api_key": resolved_api_key,
        "base_url": resolved_base_url,
        "model": resolved_model,
        "env_var": env_var,
        "requires_api_key": provider_def.get("requires_api_key", True),
    }


def save_api_key_to_env_file(
    key: str, provider: str = "gemini", project_root: Optional[Path] = None
) -> bool:
    """Saves the API key to the local .env file using provider's env_var."""
    registry = load_ai_providers_registry()
    provider_def = registry.get(provider, {})
    var_name = provider_def.get("env_var")

    if not var_name:
        logger.warning(f"No env_var defined for provider '{provider}'. Key not saved.")
        return False

    if not project_root:
        project_root = Path(__file__).resolve().parent.parent.parent

    env_path = project_root / ".env"
    lines = []
    key_written = False

    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if line.strip().startswith(f"{var_name}="):
                lines[i] = f"{var_name}={key}\n"
                key_written = True
                break

    if not key_written:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f"{var_name}={key}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    os.environ[var_name] = key
    return True
