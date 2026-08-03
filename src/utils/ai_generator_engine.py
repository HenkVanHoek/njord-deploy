# src/utils/ai_generator_engine.py

import os
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI


class AIGeneratorEngine:
    """Core interface for routing queries to different AI providers."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider: str = provider or (os.getenv("AI_PROVIDER") or "ollama")
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_context: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Sends a prompt to the configured provider and returns the response."""
        config = self._get_provider_config(self.provider)

        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )

        if isinstance(prompt, list):
            messages = list(prompt)
            if system_context and not any(m.get("role") == "system" for m in messages):
                messages.insert(0, {"role": "system", "content": system_context})
        else:
            messages = []
            if system_context:
                messages.append({"role": "system", "content": system_context})
            messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = {
            "model": config["model"],
            "messages": messages,
            "temperature": 0.2,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)

        # Enforce the Unpacking-First Mandate for precise list element access
        choice, *_ = response.choices
        content = choice.message.content
        return content or ""

    def _get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Retrieves config parameters for the active provider."""
        configs: Dict[str, Dict[str, Any]] = {
            "gemini": {
                "api_key": os.getenv("GEMINI_API_KEY"),
                "base_url": (
                    "https://generativelanguage.googleapis.com/v1beta/openai/"
                ),
                "model": "gemini-2.5-flash",
            },
            "hostyourai": {
                "api_key": os.getenv("HOSTYOURAI_API_KEY", "dummy"),
                "base_url": os.getenv(
                    "HOSTYOURAI_BASE_URL", "https://api.hostyourai.eu/v1"
                ),
                "model": "mistral-7b-instruct",
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
            },
            "ollama": {
                "api_key": "ollama",  # Required by OpenAI SDK
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                "model": os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b-instruct-q4_K_M"),
            },
            "custom": {
                "api_key": os.getenv("CUSTOM_AI_API_KEY", "dummy"),
                "base_url": os.getenv(
                    "CUSTOM_AI_BASE_URL", "http://localhost:11434/v1"
                ),
                "model": "default",
            },
        }

        if provider not in configs:
            raise ValueError(f"Unsupported AI provider: {provider}")

        cfg = configs[provider]

        # Apply any runtime overrides passed via constructor
        if self.api_key:
            cfg["api_key"] = self.api_key
        if self.base_url:
            cfg["base_url"] = self.base_url
        if self.model:
            cfg["model"] = self.model

        if not cfg["api_key"] and provider != "ollama":
            raise ValueError(
                f"API key missing for provider '{provider}'. "
                "Please check your .env settings."
            )

        return cfg
