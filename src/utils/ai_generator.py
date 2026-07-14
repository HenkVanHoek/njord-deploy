# src/utils/ai_generator.py

import json
import logging
import os
import urllib.parse
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class AIGenerator:
    """Handles interaction with the Gemini REST API to generate components."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def generate_component_data(
        self, repo_url: str, custom_instructions: Optional[str] = None
    ) -> dict:
        """Analyzes a GitHub repository and returns structured component configuration.

        Uses the Gemini REST API with structured JSON output configuration.
        """
        # Retrieve the API key from parameter or fallback to
        # the GEMINI_API_KEY environment variable.
        # Ensure the GEMINI_API_KEY is configured in your .env file.
        api_key = self.api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key is not configured.")

        # Clean and validate the repository URL
        parsed_url = urllib.parse.urlparse(repo_url)
        if not parsed_url.netloc or "github.com" not in parsed_url.netloc:
            raise ValueError("A valid GitHub repository URL is required.")

        path_parts = [p for p in parsed_url.path.split("/") if p]
        if len(path_parts) < 2:
            raise ValueError(
                "Invalid repository URL format. Must contain owner and repository name."
            )

        owner = path_parts[0]
        repo_name = path_parts[1].replace(".git", "")
        component_id = repo_name.lower()

        # Compile System Prompt and instructions
        system_prompt = (
            "You are an expert Docker and NjordDeploy configuration engineer.\n"
            "Your task is to analyze the target GitHub repository and generate the "
            "NjordDeploy component files.\n\n"
            "Constraints:\n"
            "1. The component must run in Docker and join the external network "
            'named "njorddeploy_net".\n'
            "2. Expose external ports using configuration variables. "
            'For example, use "{{ CADDY_HTTP_PORT }}" for the host port mapping.\n'
            '3. Use "{{ DATA_ROOT }}" for host-side persistent data paths. '
            'For example: "{{ DATA_ROOT }}/caddy/data:/data".\n'
            "4. Do not include a version key in the "
            "generated Docker Compose template.\n"
            "5. If the service requires a default configuration file "
            "(such as a Caddyfile), define it in the config_templates "
            "property with its relative mount target.\n"
            "6. For the service container image, always use "
            '"{{ image_name }}:{{ component_version }}".\n'
            "7. The container_name property for any service must always start "
            'with the prefix "njorddeploy-" (e.g., '
            '"container_name: njorddeploy-service-name").\n'
            "8. The docker_compose property must be a valid, multi-line "
            "YAML string formatted with standard indentation and "
            "newlines (LF).\n"
            "9. If the repository represents a source project that requires a "
            "local build (contains a Dockerfile or is not a pre-built public "
            "registry image), include a build block with a context pointing "
            'to the repository Git URL (appended with "#main", e.g., '
            '"context: https://github.com/owner/repo.git#main") and '
            '"dockerfile: Dockerfile", and set "pull_policy: build".\n'
            "10. Include the primary docker service name (e.g., the key under "
            '"services" in the Docker Compose template, such as '
            '"fluffychat-web") as "docker_service_name" in the metadata.\n'
            "11. The docker_compose property must start with these exact four "
            "comment lines at the very beginning of the YAML string:\n"
            "    # status: beta\n"
            "    # last_tested_version: <appropriate version, e.g. stable>\n"
            "    # platform_notes: <brief compatibility notes>\n"
            "    # breaking_changes: none\n"
        )

        user_prompt = (
            f"Analyze the repository: {owner}/{repo_name} (URL: {repo_url}).\n"
        )
        if custom_instructions:
            user_prompt += f"Custom User Instructions: {custom_instructions}\n"

        prompt = f"{system_prompt}\n{user_prompt}"

        # Define the expected JSON response schema
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "metadata": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "image_name": {"type": "STRING"},
                        "description": {"type": "STRING"},
                        "group": {"type": "STRING"},
                        "has_ui": {"type": "BOOLEAN"},
                        "has_configuration": {"type": "BOOLEAN"},
                        "conflicts_with": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                        "depends_on": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                        "tags": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                        "resource_profile": {
                            "type": "OBJECT",
                            "properties": {
                                "cpu": {"type": "STRING"},
                                "ram": {"type": "STRING"},
                                "storage_type": {"type": "STRING"},
                                "recommended_cores": {"type": "INTEGER"},
                                "recommended_ram_mb": {"type": "INTEGER"},
                                "recommended_storage_gb": {"type": "INTEGER"},
                            },
                        },
                        "docker_service_name": {"type": "STRING"},
                    },
                    "required": [
                        "name",
                        "image_name",
                        "description",
                        "group",
                        "has_ui",
                        "has_configuration",
                        "docker_service_name",
                    ],
                },
                "docker_compose": {"type": "STRING"},
                "variables": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "label": {"type": "STRING"},
                            "type": {"type": "STRING"},
                            "default": {"type": "STRING"},
                            "description": {"type": "STRING"},
                        },
                        "required": ["id", "label", "type", "default", "description"],
                    },
                },
                "config_templates": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {"type": "STRING"},
                            "content": {"type": "STRING"},
                        },
                        "required": ["name", "content"],
                    },
                },
            },
            "required": ["metadata", "docker_compose", "variables"],
        }

        # Build payload for the API
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": response_schema,
            },
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={api_key}"
        )

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result_json = response.json()

            # Retrieve generated content from the response structure
            candidates = result_json.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini API.")

            # Apply Unpacking-First Mandate from rules
            candidate, *_ = candidates
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError("No parts found in the response content.")

            part, *_ = parts
            text = part.get("text", "")

            # Parse and validate the returned JSON
            data = json.loads(text)

            # Convert config_templates array of {name, content} to a dictionary
            raw_configs = data.get("config_templates", [])
            configs_dict = {}
            if isinstance(raw_configs, list):
                for item in raw_configs:
                    if isinstance(item, dict) and "name" in item and "content" in item:
                        configs_dict[item["name"]] = item["content"]
            else:
                configs_dict = raw_configs
            data["config_templates"] = configs_dict

            data["id"] = component_id
            data["security_warnings"] = self._run_security_checks(data)
            return data

        except requests.exceptions.RequestException as e:
            logger.error("Gemini API request failed")
            if e.response is not None:
                status_code = e.response.status_code
                if status_code == 429:
                    raise RuntimeError(
                        "Gemini API quota exceeded or rate limit reached. "
                        "Please wait a minute before trying again."
                    )
                elif status_code == 503:
                    raise RuntimeError(
                        "Gemini API service is temporarily unavailable or "
                        "overloaded. Please try again in a few moments."
                    )
                elif status_code == 400:
                    raise RuntimeError(
                        "Gemini API rejected the request as invalid "
                        "(400 Bad Request)."
                    )
                else:
                    raise RuntimeError(
                        f"Gemini API returned an HTTP error status: {status_code}"
                    )
            raise RuntimeError(
                f"Failed to communicate with Gemini API: {type(e).__name__}"
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse Gemini API response: {e}")
            raise RuntimeError(f"Received malformed response from Gemini API: {e}")

    def _run_security_checks(self, data: dict) -> list[str]:
        """Runs security validations on the generated component data."""
        warnings = []

        # 1. Parse Docker Compose YAML and check configurations
        docker_compose_str = data.get("docker_compose", "")
        if docker_compose_str:
            try:
                import yaml

                compose_dict = yaml.safe_load(docker_compose_str) or {}
                services = compose_dict.get("services", {})
                if isinstance(services, dict):
                    for service_name, service_conf in services.items():
                        if not isinstance(service_conf, dict):
                            continue

                        # Check privileged
                        if service_conf.get("privileged") is True:
                            warnings.append(
                                f"Service '{service_name}' runs in " "privileged mode."
                            )

                        # Check network mode
                        if service_conf.get("network_mode") == "host":
                            warnings.append(
                                f"Service '{service_name}' uses host " "network mode."
                            )

                        # Check volume mounts
                        volumes = service_conf.get("volumes", [])
                        if isinstance(volumes, list):
                            for vol in volumes:
                                host_path = ""
                                if isinstance(vol, str):
                                    parts = vol.split(":")
                                    host_path = parts[0] if parts else ""
                                elif isinstance(vol, dict):
                                    host_path = vol.get("source", "")

                                if host_path == "/var/run/docker.sock":
                                    warnings.append(
                                        f"Service '{service_name}' mounts the "
                                        "Docker socket "
                                        "(/var/run/docker.sock)."
                                    )
                                elif host_path in [
                                    "/",
                                    "/etc",
                                    "/boot",
                                    "/sys",
                                    "/proc",
                                    "/dev",
                                ]:
                                    warnings.append(
                                        f"Service '{service_name}' mounts a "
                                        f"sensitive host system path: "
                                        f"{host_path}"
                                    )

                        # Check cap_add
                        cap_adds = service_conf.get("cap_add", [])
                        if isinstance(cap_adds, list):
                            for cap in cap_adds:
                                if cap in ["SYS_ADMIN", "ALL"]:
                                    warnings.append(
                                        f"Service '{service_name}' requests "
                                        f"broad capability: {cap}"
                                    )
            except Exception as e:
                warnings.append(
                    f"Failed to parse Docker Compose for security checks: {e}"
                )

        # 2. Check variables for weak default secrets
        variables = data.get("variables", [])
        if isinstance(variables, list):
            secret_keywords = ["password", "secret", "key", "token", "pwd"]
            weak_defaults = ["admin", "root", "password", "123456", "secret"]
            for var in variables:
                if not isinstance(var, dict):
                    continue
                var_id = str(var.get("id", "")).lower()
                var_default = str(var.get("default", ""))

                is_secret = any(kw in var_id for kw in secret_keywords)
                if is_secret and var_default:
                    if var_default.lower() in weak_defaults or len(var_default) < 6:
                        warnings.append(
                            f"Variable '{var.get('id')}' appears to be a "
                            "secret but has a weak default value: "
                            f"'{var_default}'"
                        )

        return warnings
