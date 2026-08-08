# src/utils/ai_generator_engine.py

import os
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI

from utils.ai_provider_manager import get_provider_resolved_config


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
            timeout=60.0,
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
        cfg = get_provider_resolved_config(
            provider=provider,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
        )

        if not cfg["api_key"] and provider != "ollama":
            raise ValueError(
                f"API key missing for provider '{provider}'. "
                "Please check your .env settings."
            )

        return cfg
