# src/utils/ai_generator.py

import json
import logging
import re
import urllib.parse
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class AIGenerator:
    """Handles interaction with the Gemini REST API to generate components."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key
        self.provider = provider
        self.base_url = base_url
        self.model = model

    def generate_component_data(
        self,
        repo_url: str,
        custom_instructions: Optional[str] = None,
        existing_groups: Optional[list[str]] = None,
    ) -> dict:
        """Analyzes a Git repository and returns structured component configuration.

        Uses the multi-provider AIGeneratorEngine.
        """
        # Clean and validate the repository URL
        parsed_url = urllib.parse.urlparse(repo_url.strip())
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("A valid Git repository URL is required.")

        raw_path = parsed_url.path.strip("/")
        if raw_path.endswith(".git"):
            raw_path = raw_path[:-4]

        path_parts = [p for p in raw_path.split("/") if p]
        if not path_parts:
            raise ValueError(
                "Invalid repository URL format. "
                "Must contain at least a repository name."
            )

        repo_name = path_parts[-1]
        owner = path_parts[0] if len(path_parts) > 1 else ""
        repo_path = "/".join(path_parts)
        component_id = repo_name.lower()

        # Fetch README and compose files from the repository
        readme_content = self._fetch_repo_file(
            parsed_url.netloc, repo_path, ["README.md", "readme.md", "README"]
        )
        compose_content = self._fetch_repo_file(
            parsed_url.netloc,
            repo_path,
            [
                "docker-compose.yml",
                "docker-compose.yaml",
                "compose.yml",
                "compose.yaml",
            ],
        )

        # Compile System Prompt and instructions
        from utils.resource_utils import resource_path

        rules_path = resource_path("config/ai_generator_rules.json")
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                rules_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load AI generator rules from {rules_path}: {e}")
            raise RuntimeError(f"Failed to load AI generator rules: {e}") from e

        system_instruction = rules_data.get("system_instruction", "")
        rules_list = rules_data.get("rules", [])

        system_prompt = f"{system_instruction}\n\nConstraints:\n"
        for i, rule in enumerate(rules_list):
            rule_num = i + 1
            if isinstance(rule, dict) and rule.get("type") == "group_rule":
                if existing_groups:
                    groups_str = ", ".join(f"'{g}'" for g in existing_groups)
                    resolved_rule = rule.get("template", "").format(
                        groups_str=groups_str
                    )
                else:
                    resolved_rule = rule.get("fallback", "")
                system_prompt += f"{rule_num}. {resolved_rule}\n"
            else:
                system_prompt += f"{rule_num}. {rule}\n"

        repo_display = f"{owner}/{repo_name}" if owner else repo_name
        user_prompt = f"Analyze the repository: {repo_display} (URL: {repo_url}).\n"
        if readme_content:
            user_prompt += (
                f"\n--- START OF REPOSITORY README.MD ---\n"
                f"{readme_content[:15000]}"
                f"\n--- END OF REPOSITORY README.MD ---\n"
            )
        if compose_content:
            user_prompt += (
                f"\n--- START OF REPOSITORY DOCKER COMPOSE CONFIGURATION ---\n"
                f"{compose_content[:5000]}"
                f"\n--- END OF REPOSITORY DOCKER COMPOSE CONFIGURATION ---\n"
            )
        if custom_instructions:
            user_prompt += f"Custom User Instructions: {custom_instructions}\n"

        # Initialize the AIGeneratorEngine
        from utils.ai_generator_engine import AIGeneratorEngine

        engine = AIGeneratorEngine(
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
        )

        # Define conversation history for multi-turn correction loop
        messages = [{"role": "user", "content": user_prompt}]
        max_attempts = 3
        attempt = 0

        while True:
            try:
                # Request structured JSON format
                text = engine.generate(
                    prompt=messages,
                    system_context=system_prompt,
                    response_format={"type": "json_object"},
                )

                # Parse and validate the returned JSON
                data = json.loads(text)

                # Convert config_templates array of {name, content} to a dictionary
                raw_configs = data.get("config_templates", [])
                configs_dict = {}
                if isinstance(raw_configs, list):
                    for item in raw_configs:
                        if (
                            isinstance(item, dict)
                            and "name" in item
                            and "content" in item
                        ):
                            configs_dict[item["name"]] = item["content"]
                else:
                    configs_dict = raw_configs
                data["config_templates"] = configs_dict

                data["id"] = component_id

                metadata = data.setdefault("metadata", {})
                if custom_instructions:
                    metadata["ai_instructions"] = custom_instructions.strip()
                if data.get("variables") or data.get("config_templates"):
                    metadata["has_configuration"] = True

                # Run security and validation checks
                warnings = self._run_security_checks(data)

                # Filter to only fixable structure/variable/syntax warnings
                fixable_warnings = [
                    w for w in warnings if "was not found on Docker Hub" not in w
                ]

                # If no fixable warnings, or we reached max correction attempts
                if not fixable_warnings or attempt >= max_attempts:
                    data["security_warnings"] = warnings
                    return data

                attempt += 1
                logger.info(
                    f"AI validation failed with warnings: {fixable_warnings}. "
                    f"Attempting self-correction (attempt "
                    f"{attempt}/{max_attempts})..."
                )

                # Formulate correction prompt
                correction_prompt = (
                    "The generated component configuration had the following "
                    "validation/security warnings:\n"
                )
                for w in fixable_warnings:
                    correction_prompt += f"- {w}\n"
                correction_prompt += (
                    "\nPlease correct the JSON configuration to resolve "
                    "these warnings. Ensure that:\n"
                    "1. Every custom Jinja variable referenced in "
                    "`docker_compose` is defined in the `variables` list, "
                    "and all defined variables are referenced in "
                    "`docker_compose`.\n"
                    "2. If `has_ui` is true, the `ui_port_variable` in "
                    "the metadata matches the exact port variable ID defined "
                    "in the variables list and referenced in "
                    "`docker_compose`.\n"
                    "3. Any variables defined in the variables list but "
                    "not used in the docker-compose template are either "
                    "removed from the variables list or added to the template "
                    "as needed.\n"
                    "4. If there are syntax or parsing errors in the Docker "
                    "Compose YAML template (such as nested double quotes, "
                    "mismatched quotes, or bad indentation), correct the "
                    "formatting to ensure it is valid, parseable YAML.\n"
                    "Return the complete corrected JSON configuration "
                    "according to the original schema."
                )

                # Append model's response and correction prompt to history
                messages.append({"role": "assistant", "content": text})
                messages.append({"role": "user", "content": correction_prompt})

            except Exception as e:
                logger.error(f"AI Generator inference failed: {e}")
                err_msg = str(e).lower()
                if "rate limit" in err_msg or "quota" in err_msg or "429" in err_msg:
                    raise RuntimeError(
                        "AI API quota exceeded or rate limit reached. "
                        "Please wait a minute before trying again."
                    ) from e
                elif (
                    "503" in err_msg
                    or "unavailable" in err_msg
                    or "overloaded" in err_msg
                ):
                    raise RuntimeError(
                        "AI API service is temporarily unavailable or "
                        "overloaded. Please try again in a few moments."
                    ) from e
                elif "400" in err_msg or "bad request" in err_msg:
                    raise RuntimeError(
                        "AI API rejected the request as invalid (400 Bad Request)."
                    ) from e
                elif (
                    "connection error" in err_msg
                    or "connection refused" in err_msg
                    or "connect error" in err_msg
                    or "connecterror" in err_msg
                    or "[errno 111]" in err_msg
                    or "apiconnectionerror" in err_msg
                ):
                    provider_name = self.provider or "ollama"
                    target_url = self.base_url or (
                        "http://localhost:11434/v1" if provider_name == "ollama" else ""
                    )
                    if (
                        provider_name == "ollama"
                        or "localhost" in target_url
                        or "127.0.0.1" in target_url
                    ):
                        url_str = f" at {target_url}" if target_url else ""
                        raise RuntimeError(
                            f"Could not connect to Ollama local server{url_str} "
                            "(Connection refused). Please ensure Ollama is installed "
                            "and running locally, or select a cloud provider "
                            "(such as Gemini or OpenAI) with an API key."
                        ) from e
                    else:
                        url_str = f" at {target_url}" if target_url else ""
                        raise RuntimeError(
                            f"Could not connect to AI API endpoint{url_str}. "
                            "Please check your internet connection and API base URL."
                        ) from e
                elif isinstance(e, (json.JSONDecodeError, KeyError, ValueError)):
                    if attempt < max_attempts:
                        attempt += 1
                        logger.info(
                            "Failed to parse response as JSON. Attempting "
                            f"self-correction (attempt {attempt}/{max_attempts})..."
                        )
                        correction_prompt = (
                            "The previous response failed to parse as JSON with "
                            f"error: {e}. Please return the complete, valid JSON "
                            "adhering strictly to the original schema."
                        )
                        text_val = text if "text" in locals() else ""
                        messages.append({"role": "assistant", "content": text_val})
                        messages.append({"role": "user", "content": correction_prompt})
                        continue
                    raise RuntimeError(
                        f"Received malformed response from AI API: {e}"
                    ) from e
                else:
                    raise RuntimeError(
                        f"Failed to communicate with AI API: {type(e).__name__} - {e}"
                    ) from e

    def _get_raw_file_urls(
        self, netloc: str, repo_path: str, filename: str
    ) -> list[str]:
        """Builds a list of potential raw file URLs across supported Git platforms."""
        urls: list[str] = []
        branches = ["main", "master"]
        parts = [p for p in repo_path.split("/") if p]
        owner = parts[0] if parts else ""
        repo = parts[-1] if len(parts) > 1 else ""

        host = netloc.lower()

        if "github.com" in host and owner and repo:
            for branch in branches:
                urls.append(
                    f"https://raw.githubusercontent.com/{owner}/{repo}/"
                    f"{branch}/{filename}"
                )
        elif "gitlab" in host:
            for branch in branches:
                urls.append(f"https://{netloc}/{repo_path}/-/raw/{branch}/{filename}")
        elif "bitbucket.org" in host:
            for branch in branches:
                urls.append(
                    f"https://bitbucket.org/{repo_path}/raw/{branch}/{filename}"
                )
        elif "codeberg.org" in host or "gitea" in host or "forgejo" in host:
            for branch in branches:
                urls.append(
                    f"https://{netloc}/{repo_path}/raw/branch/{branch}/{filename}"
                )
        else:
            # Generic / self-hosted: try Gitea/Forgejo, GitLab, and direct raw
            for branch in branches:
                urls.append(
                    f"https://{netloc}/{repo_path}/raw/branch/{branch}/{filename}"
                )
                urls.append(f"https://{netloc}/{repo_path}/-/raw/{branch}/{filename}")
                urls.append(f"https://{netloc}/{repo_path}/raw/{branch}/{filename}")

        return urls

    def _fetch_repo_file(
        self, netloc: str, repo_path: str, filenames: list[str]
    ) -> Optional[str]:
        """Tries to fetch content for candidate filenames across multiple patterns."""
        for filename in filenames:
            urls = self._get_raw_file_urls(netloc, repo_path, filename)
            for url in urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200 and response.text:
                        return response.text
                except Exception:  # nosec B110
                    pass
        return None

    def _fetch_github_file(self, owner: str, repo: str, filename: str) -> Optional[str]:
        """Tries to fetch a file from a GitHub repository's main or master branch."""
        return self._fetch_repo_file("github.com", f"{owner}/{repo}", [filename])

    def _check_docker_image_exists(self, image_name: str) -> bool:
        """Verifies if a given docker image exists on its registry."""
        if not image_name:
            return False

        if "/" in image_name:
            first_part, rest = image_name.split("/", 1)
            if "." in first_part or ":" in first_part or first_part == "localhost":
                registry = first_part
                if ":" in rest:
                    repository, _ = rest.split(":", 1)
                else:
                    repository = rest
                return self._check_oci_image(registry, repository)
            else:
                namespace = first_part
                if ":" in rest:
                    repository, _ = rest.split(":", 1)
                else:
                    repository = rest
        else:
            namespace = "library"
            if ":" in image_name:
                repository, _ = image_name.split(":", 1)
            else:
                repository = image_name

        url = f"https://hub.docker.com/v2/repositories/{namespace}/{repository}/"
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _check_oci_image(self, registry: str, repository: str) -> bool:
        """Verifies image existence via standard OCI V2 API with token auth."""
        url = f"https://{registry}/v2/{repository}/tags/list"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return True
            if res.status_code == 401:
                auth_header = res.headers.get("Www-Authenticate")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return False

                params = {}
                for match in re.finditer(r'(\w+)="([^"]+)"', auth_header):
                    params[match.group(1)] = match.group(2)

                realm = params.get("realm")
                if not realm:
                    return False

                token_params = {k: v for k, v in params.items() if k != "realm"}
                token_res = requests.get(realm, params=token_params, timeout=5)
                if token_res.status_code != 200:
                    return False

                token_data = token_res.json()
                token = token_data.get("token") or token_data.get("access_token")
                if not token:
                    return False

                headers = {"Authorization": f"Bearer {token}"}
                res_with_token = requests.get(url, headers=headers, timeout=5)
                return res_with_token.status_code == 200
            return False
        except Exception:
            return False

    def _run_security_checks(self, data: dict) -> list[str]:
        """Runs security validations on the generated component data."""
        warnings = []

        # 1. Parse Docker Compose YAML and check configurations
        docker_compose_str = data.get("docker_compose", "")
        if docker_compose_str:
            try:
                import yaml

                cleaned_yaml = re.sub(
                    r"\{#.*?#\}", "", docker_compose_str, flags=re.DOTALL
                )
                cleaned_yaml = re.sub(r"\{%.*?%\}", "# jinja block", cleaned_yaml)
                cleaned_yaml = re.sub(r"\{\{.*?\}\}", "JINJA_VAR", cleaned_yaml)

                compose_dict = yaml.safe_load(cleaned_yaml) or {}

                services = compose_dict.get("services", {})

                if isinstance(services, dict):
                    for service_name, service_conf in services.items():
                        if not isinstance(service_conf, dict):
                            continue

                        # Check privileged
                        if service_conf.get("privileged"):
                            warnings.append(
                                f"Service '{service_name}' runs in " "privileged mode."
                            )

                        # Check network mode
                        if service_conf.get("network_mode") == "host":
                            warnings.append(
                                f"Service '{service_name}' uses host " "network mode."
                            )

                        # Check if pull_policy is nested inside build block
                        build_conf = service_conf.get("build")
                        if isinstance(build_conf, dict) and "pull_policy" in build_conf:
                            warnings.append(
                                f"Service '{service_name}' has 'pull_policy' "
                                "nested inside the 'build' block. "
                                "It must be placed at the service level instead."
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

        # 3. Check variable consistency between compose and variables list
        docker_compose_str = data.get("docker_compose", "")
        metadata = data.get("metadata", {})
        if isinstance(docker_compose_str, str) and docker_compose_str:
            jinja_vars = set(
                re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", docker_compose_str)
            )
            system_vars = {
                "DATA_ROOT",
                "DOMAIN",
                "image_name",
                "component_version",
                "has_traefik_support",
                "traefik_labels_yaml",
                "traefik_internal_port",
                "CONFIG_BASE_PATH",
            }
            custom_vars_in_compose = jinja_vars - system_vars
            defined_var_ids = set()
            if isinstance(variables, list):
                for var in variables:
                    if isinstance(var, dict) and var.get("id"):
                        defined_var_ids.add(var.get("id"))

            # Report missing definitions
            for var in custom_vars_in_compose - defined_var_ids:
                warnings.append(
                    f"Variable '{var}' is used in docker-compose template "
                    "but not defined in the variables list."
                )

            # Report unused definitions
            for var in defined_var_ids - jinja_vars:
                warnings.append(
                    f"Variable '{var}' is defined in variables list "
                    "but not used in the docker-compose template."
                )

            # Check UI port variable consistency
            if isinstance(metadata, dict) and metadata.get("has_ui"):
                ui_port_var = metadata.get("ui_port_variable")
                if not ui_port_var:
                    warnings.append(
                        "Component has UI but 'ui_port_variable' is "
                        "missing in metadata."
                    )
                elif ui_port_var not in defined_var_ids:
                    warnings.append(
                        f"The UI port variable '{ui_port_var}' specified in "
                        "metadata is not defined in the variables list."
                    )
                elif ui_port_var not in jinja_vars:
                    warnings.append(
                        f"The UI port variable '{ui_port_var}' is defined "
                        "but not referenced in the docker-compose template."
                    )

        # 4. Check if the docker image exists on Docker Hub
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            image_name = metadata.get("image_name")
            if isinstance(image_name, str) and image_name:
                if not self._check_docker_image_exists(image_name):
                    # Check if it exists on ghcr.io (e.g., ghcr.io/owner/repo)
                    is_corrected = False
                    has_registry = any(r in image_name for r in [".", "localhost"])
                    if "/" in image_name and not has_registry:
                        ghcr_image = f"ghcr.io/{image_name}"
                        if self._check_docker_image_exists(ghcr_image):
                            metadata["image_name"] = ghcr_image
                            docker_compose_str = data.get("docker_compose", "")
                            if (
                                isinstance(docker_compose_str, str)
                                and docker_compose_str
                            ):
                                pattern = (
                                    r"(\bimage\s*:\s*[\"']?)"
                                    + re.escape(image_name)
                                    + r"(\b)"
                                )
                                data["docker_compose"] = re.sub(
                                    pattern,
                                    lambda m: m.group(1) + ghcr_image + m.group(2),
                                    docker_compose_str,
                                )
                            is_corrected = True

                    if not is_corrected:
                        warnings.append(
                            f"Docker image '{image_name}' was not found on "
                            "Docker Hub. Please check for spelling mistakes "
                            "or ensure the repository is public."
                        )

        return warnings
