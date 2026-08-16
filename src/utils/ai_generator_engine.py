# src/utils/ai_generator_engine.py

import os
from typing import Any, Dict, List, Optional, Union

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore

from utils.ai_provider_manager import get_ai_timeout, get_provider_resolved_config


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
        timeout = get_ai_timeout(self.provider, config.get("base_url"))

        if self.provider == "anthropic":
            return self._generate_anthropic(
                prompt=prompt,
                system_context=system_context,
                config=config,
                timeout=timeout,
            )

        return self._generate_openai_compatible(
            prompt=prompt,
            system_context=system_context,
            response_format=response_format,
            config=config,
            timeout=timeout,
        )

    def _generate_anthropic(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_context: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        timeout: float = 90.0,
    ) -> str:
        """Sends a prompt to Anthropic Claude Messages API (/v1/messages)."""
        import requests

        if config is None:
            config = self._get_provider_config("anthropic")

        # Extract system prompt if present in messages or parameter
        system_text = system_context or ""
        anthropic_messages: List[Dict[str, str]] = []

        if isinstance(prompt, list):
            for msg in prompt:
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    if not system_text:
                        system_text = content
                    else:
                        system_text = f"{system_text}\n\n{content}"
                else:
                    anthropic_messages.append({"role": role, "content": content})
        else:
            anthropic_messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json",
            "x-api-key": config["api_key"] or "",
            "anthropic-version": "2023-06-01",
        }

        body: Dict[str, Any] = {
            "model": config["model"],
            "max_tokens": 4096,
            "temperature": 0.2,
            "messages": anthropic_messages,
        }
        if system_text:
            body["system"] = system_text

        base_url = config.get("base_url", "https://api.anthropic.com/v1").rstrip("/")
        url = f"{base_url}/messages"
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content_list = data.get("content", [])
        if not isinstance(content_list, list) or not content_list:
            return ""

        first_block, *_ = content_list
        if not isinstance(first_block, dict):
            return ""

        text_pieces = [
            block.get("text", "")
            for block in content_list
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "".join(text_pieces)

    def _generate_openai_compatible(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_context: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        timeout: float = 90.0,
    ) -> str:
        """Sends a prompt to an OpenAI-compatible chat completions endpoint."""
        if config is None:
            config = self._get_provider_config(self.provider)

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

        if OpenAI is not None:
            client = OpenAI(
                api_key=config["api_key"] or "none",
                base_url=config["base_url"],
                timeout=timeout,
            )
            response = client.chat.completions.create(**kwargs)
            if not response.choices:
                return ""
            choice, *_ = response.choices
            content = choice.message.content
            return content or ""

        # Fallback to requests if openai package is not installed
        import requests

        headers = {"Content-Type": "application/json"}
        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"

        url = f"{config['base_url'].rstrip('/')}/chat/completions"
        resp = requests.post(url, headers=headers, json=kwargs, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        choice, *_ = choices
        message = choice.get("message", {})
        return message.get("content") or ""

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
