# src/editor_app/app.py

import logging
import os
import sys
from pathlib import Path

import requests
from flask import Flask, abort, jsonify, render_template, request
from werkzeug.utils import secure_filename

from managers.component_manager import ComponentManager
from utils.ai_generator import AIGenerator
from utils.resource_utils import get_components_paths

logging.basicConfig(level=logging.INFO)


def create_app(test_config=None):
    """Application factory for the Developer Editor."""
    # Load environment variables from the .env file at the project root.
    from dotenv import load_dotenv

    project_root = Path(__file__).parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")

    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        template_folder = bundle_dir / "src" / "editor_app" / "templates"
        if not template_folder.exists():
            template_folder = bundle_dir / "templates"
        static_folder = bundle_dir / "src" / "editor_app" / "static"
        if not static_folder.exists():
            static_folder = bundle_dir / "static"
        app = Flask(
            __name__,
            template_folder=str(template_folder),
            static_folder=str(static_folder),
        )
    else:
        app = Flask(__name__)

    # Crucial for testing: apply the test_config
    if test_config:
        app.config.update(test_config)

    def save_api_key_to_env(key: str, provider: str = "gemini"):
        """Saves the API key to the local .env file based on the provider."""
        from utils.ai_provider_manager import save_api_key_to_env_file

        save_api_key_to_env_file(key=key, provider=provider, project_root=project_root)

    from utils.resource_utils import seed_user_components_if_needed

    seed_user_components_if_needed()
    meta_file_path, temp_path_obj = get_components_paths()
    meta_file = str(meta_file_path)
    temp_path = str(temp_path_obj)

    # Initialize the unified ComponentManager
    component_manager = ComponentManager(
        templates_path=temp_path, metadata_file_path=meta_file
    )

    from managers.sync_manager import SyncManager  # type: ignore

    sync_manager = SyncManager(
        local_metadata_path=meta_file_path,
        local_templates_path=temp_path_obj,
    )

    @app.route("/api/sync/status", methods=["GET"])
    def sync_status():
        try:
            status_data = sync_manager.get_sync_status()
            from utils.resource_utils import get_last_seed_status

            status_data["initial_seed_info"] = get_last_seed_status()
            return jsonify(status_data), 200
        except Exception as e:
            logging.error(f"Failed to get sync status: {e}", exc_info=True)
            abort(500, "Internal error getting sync status")

    @app.route("/api/sync/check-updates", methods=["GET", "POST"])
    def sync_check_updates():
        try:
            sync_manager.fetch_from_remote(timeout=3)
            status_data = sync_manager.get_sync_status()
            from utils.resource_utils import get_last_seed_status

            status_data["initial_seed_info"] = get_last_seed_status()
            return jsonify(status_data), 200
        except Exception as e:
            logging.error(f"Failed to check updates: {e}", exc_info=True)
            return (
                jsonify(
                    {
                        "status": "error",
                        "is_offline": True,
                        "message": str(e),
                    }
                ),
                200,
            )

    @app.route("/api/components/<comp_id>/mark-tested", methods=["POST"])
    def mark_component_tested_route(comp_id):
        try:
            data = request.get_json(silent=True) or {}
            test_status = data.get("test_status", "stable")
            component_manager.mark_component_tested(comp_id, test_status=test_status)
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Component '{comp_id}' marked as tested",
                    }
                ),
                200,
            )
        except KeyError:
            abort(404, f"Component '{comp_id}' not found")
        except Exception as e:
            logging.error(
                f"Failed to mark component {comp_id} as tested: {e}", exc_info=True
            )
            abort(500, f"Internal error marking component {comp_id} as tested")

    @app.route("/api/sync/fetch", methods=["POST"])
    def sync_fetch():
        try:
            success = sync_manager.fetch_from_remote()
            if success:
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": (
                                "Successfully fetched " "from remote repository"
                            ),
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Failed to fetch from remote repository",
                        }
                    ),
                    500,
                )
        except Exception as e:
            logging.error(f"Failed to fetch remote components: {e}", exc_info=True)
            abort(500, "Internal error fetching from remote")

    @app.route("/api/sync/component/<comp_id>", methods=["POST"])
    def sync_component_route(comp_id):
        try:
            success = sync_manager.sync_component(comp_id)
            if success:
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": (
                                f"Successfully synchronized " f"component {comp_id}"
                            ),
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": (
                                f"Failed to synchronize " f"component {comp_id}"
                            ),
                        }
                    ),
                    500,
                )
        except Exception as e:
            logging.error(f"Failed to sync component {comp_id}: {e}", exc_info=True)
            abort(500, f"Internal error syncing component {comp_id}")

    @app.route("/api/sync/all", methods=["POST"])
    def sync_all_route():
        try:
            success = sync_manager.sync_all()
            if success:
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": "Successfully synchronized " "all components",
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Failed to synchronize all components",
                        }
                    ),
                    500,
                )
        except Exception as e:
            logging.error(f"Failed to sync all components: {e}", exc_info=True)
            abort(500, "Internal error syncing all components")

    @app.route("/api/git/check_permission", methods=["GET"])
    def git_check_permission():
        try:
            has_write, details = sync_manager.check_write_access_details()
            return jsonify({"has_write_access": has_write, "details": details}), 200
        except Exception as e:
            logging.error(f"Failed to check git permissions: {e}", exc_info=True)
            abort(500, "Internal error checking git permissions")

    @app.route("/api/git/upload/<comp_id>", methods=["POST"])
    def git_upload_component(comp_id):
        # 1. Pre-upload completeness/metadata validation (linter)
        if not sync_manager.validate_metadata_header(comp_id):
            return (
                jsonify(
                    {
                        "error": (
                            "Upload aborted: Metadata header "
                            "is incomplete or malformed."
                        )
                    }
                ),
                400,
            )

        # 2. Proceed with commit and push
        try:
            success = sync_manager.upload_component(comp_id)
            if success:
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": f"Successfully uploaded component {comp_id}",
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": f"Failed to upload component {comp_id}",
                        }
                    ),
                    500,
                )
        except Exception as e:
            logging.error(f"Failed to upload component {comp_id}: {e}", exc_info=True)
            err_msg = "Failed to upload component due to an internal error"
            return jsonify({"error": err_msg}), 500

    @app.route("/api/git/upload_all", methods=["POST"])
    def git_upload_all_components():
        try:
            success = sync_manager.upload_all_components()
            if success:
                return (
                    jsonify(
                        {
                            "status": "success",
                            "message": "Successfully uploaded all components in bulk",
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Failed to upload all components",
                        }
                    ),
                    500,
                )
        except ValueError as ve:
            err_msg = str(ve)
            is_val_fail = "validation failed" in err_msg.lower()
            is_inc = "incomplete" in err_msg.lower()
            if is_val_fail or is_inc:
                return (
                    jsonify(
                        {
                            "error": (
                                "Metadata validation failed for "
                                "one or more components"
                            )
                        }
                    ),
                    400,
                )
            else:
                return (
                    jsonify(
                        {
                            "error": (
                                "Failed to upload components "
                                "due to a validation error"
                            )
                        }
                    ),
                    400,
                )
        except Exception as e:
            logging.error(f"Failed to upload all components: {e}", exc_info=True)
            err_msg = "Failed to upload all components due to an internal error"
            return jsonify({"error": err_msg}), 500

    @app.route("/api/sync/diff/<comp_id>", methods=["GET"])
    def sync_diff_route(comp_id):
        try:
            local_tpl_path = (
                sync_manager.local_templates_path
                / comp_id
                / "docker-compose.template.yml"
            )
            remote_tpl_path = (
                sync_manager.cache_templates_path
                / comp_id
                / "docker-compose.template.yml"
            )

            local_template = ""
            if local_tpl_path.exists():
                local_template = local_tpl_path.read_text(encoding="utf-8").replace(
                    "\r\n", "\n"
                )

            remote_template = ""
            if remote_tpl_path.exists():
                remote_template = remote_tpl_path.read_text(encoding="utf-8").replace(
                    "\r\n", "\n"
                )

            local_meta = sync_manager.get_local_component_meta(comp_id)
            remote_meta = sync_manager.get_remote_component_meta(comp_id)

            differing_files = []
            local_dir = sync_manager.local_templates_path / comp_id
            remote_dir = sync_manager.cache_templates_path / comp_id

            if local_dir.exists() and remote_dir.exists():
                files1 = {
                    f.relative_to(local_dir)
                    for f in local_dir.rglob("*")
                    if f.is_file()
                }
                files2 = {
                    f.relative_to(remote_dir)
                    for f in remote_dir.rglob("*")
                    if f.is_file()
                }
                all_files = files1.union(files2)
                for rel_path in all_files:
                    f1 = local_dir / rel_path
                    f2 = remote_dir / rel_path
                    if not f1.exists() or not f2.exists():
                        differing_files.append(str(rel_path))
                        continue
                    # noinspection PyBroadException
                    try:
                        if rel_path.suffix.lower() in (
                            ".yml",
                            ".yaml",
                            ".json",
                            ".conf",
                            ".rb",
                            ".txt",
                            ".sh",
                            ".template",
                        ):
                            c1 = (
                                f1.read_text(encoding="utf-8", errors="ignore")
                                .replace("\r\n", "\n")
                                .strip()
                            )
                            c2 = (
                                f2.read_text(encoding="utf-8", errors="ignore")
                                .replace("\r\n", "\n")
                                .strip()
                            )
                            if c1 != c2:
                                differing_files.append(str(rel_path))
                        else:
                            if f1.read_bytes() != f2.read_bytes():
                                differing_files.append(str(rel_path))
                    except Exception:
                        differing_files.append(str(rel_path))

            return (
                jsonify(
                    {
                        "local_template": local_template,
                        "remote_template": remote_template,
                        "local_meta": local_meta,
                        "remote_meta": remote_meta,
                        "differing_files": differing_files,
                    }
                ),
                200,
            )
        except Exception as e:
            logging.error(
                f"Failed to get diff for component {comp_id}: {e}",
                exc_info=True,
            )
            abort(500, f"Internal error getting diff for {comp_id}")

    @app.route("/static/css/njorddeploy-style.css")
    def serve_shared_css():
        from flask import send_from_directory

        from utils.resource_utils import resource_path

        candidate_dirs = [
            resource_path("src/editor_app/static/css"),
            resource_path("src/configurator_app/static/css"),
            project_root / "src" / "editor_app" / "static" / "css",
            project_root / "src" / "configurator_app" / "static" / "css",
            Path(__file__).parent / "static" / "css",
            Path(__file__).parent.parent / "configurator_app" / "static" / "css",
        ]
        for css_dir in candidate_dirs:
            if (css_dir / "njorddeploy-style.css").exists():
                return send_from_directory(css_dir, "njorddeploy-style.css")

        abort(404, "njorddeploy-style.css not found")

    @app.route("/")
    def index():
        has_gemini_key = bool(os.environ.get("GEMINI_API_KEY"))
        return render_template("editor.html", has_gemini_key=has_gemini_key)

    @app.route("/api/components", methods=["GET"])
    def list_components():
        include_vars = request.args.get("include_variables", "false").lower() == "true"
        all_comps = component_manager.get_all_components(include_variables=include_vars)
        # Return mapped by ID dict for loadComponents frontend utility
        return jsonify({comp["id"]: comp for comp in all_comps}), 200

    @app.route("/api/components/<comp_id>", methods=["GET"])
    def get_component(comp_id):
        details = component_manager.get_component_details(comp_id)
        if details:
            return jsonify(details), 200
        abort(404, f"Component '{comp_id}' not found")

    @app.route("/api/components/<comp_id>", methods=["PUT"])
    def update_component(comp_id):
        data = request.get_json() or {}
        try:
            component_manager.update_component_metadata(comp_id, data)
            return jsonify({"status": "updated"}), 200
        except KeyError:
            abort(404, f"Component '{comp_id}' not found")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logging.error(
                f"Failed to update metadata for {comp_id}: {e}", exc_info=True
            )
            abort(500, "Internal error updating component metadata")

    @app.route("/api/components/<comp_id>/variables", methods=["PUT"])
    def update_vars(comp_id):
        payload = request.get_json() or {}
        if not isinstance(payload, dict):
            abort(400, "Payload must be a dictionary")

        try:
            component_manager.update_component_variables(comp_id, payload)
            return jsonify({"status": "updated"}), 200
        except Exception as e:
            logging.error(f"Failed to save variables for {comp_id}: {e}", exc_info=True)
            abort(500, "Internal error saving component variables")

    @app.route("/api/components", methods=["POST"])
    def add_component():
        data = request.get_json() or {}
        component_id = data.get("id")

        if not component_id or not isinstance(component_id, str):
            abort(400, "A valid Component ID string is required")

        meta = data.get("meta") or {}
        name = meta.get("name", component_id.capitalize())

        try:
            component_manager.create_component(component_id, name)
            if meta:
                component_manager.update_component_metadata(component_id, meta)
            return jsonify({"status": "created"}), 201
        except ValueError:
            abort(409, "Component already exists or invalid ID format")
        except Exception as e:
            logging.error(
                f"Failed to create component {component_id}: {e}", exc_info=True
            )
            abort(500, "Internal error creating component")

    @app.route("/api/components/<comp_id>", methods=["DELETE"])
    def delete_component(comp_id):
        try:
            component_manager.delete_component(comp_id)
            return jsonify({"status": "deleted"}), 200
        except KeyError:
            abort(404, f"Component '{comp_id}' not found")
        except Exception as e:
            logging.error(f"Failed to delete component {comp_id}: {e}", exc_info=True)
            abort(500, "Internal error deleting component")

    @app.route("/api/components/<comp_id>/template", methods=["GET"])
    def get_component_template(comp_id):
        try:
            content = component_manager.get_component_template_content(comp_id)
            return content, 200
        except Exception as e:
            logging.error(f"Failed to read template for {comp_id}: {e}", exc_info=True)
            abort(500, "Internal error reading component template")

    @app.route("/api/components/<comp_id>/template", methods=["PUT"])
    def update_component_template(comp_id):
        try:
            content = request.get_data(as_text=True)
            component_manager.update_component_template_content(comp_id, content)
            return jsonify({"status": "updated"}), 200
        except Exception as e:
            logging.error(f"Failed to save template for {comp_id}: {e}", exc_info=True)
            abort(500, "Internal error saving component template")

    @app.route("/api/components/<comp_id>/validate", methods=["POST"])
    def validate_component(comp_id):
        data = request.get_json() or {}
        template_content = data.get("template_content", "")
        variables = data.get("variables", [])
        try:
            component_manager.validate_component_configuration(
                comp_id, template_content, variables
            )
            return (
                jsonify(
                    {
                        "status": "valid",
                        "message": "Template validation successful!",
                    }
                ),
                200,
            )
        except ValueError as e:
            logging.warning(f"Validation failed for {comp_id}: {e}")
            return jsonify({"error": "Template validation failed"}), 400
        except Exception as e:
            logging.error(
                f"Unexpected validation error for {comp_id}: {e}", exc_info=True
            )
            abort(500, "Unexpected validation error occurred")

    @app.route(
        "/api/components/<comp_id>/validate_metadata_conflicts", methods=["POST"]
    )
    def validate_metadata_conflicts(comp_id):
        data = request.get_json() or {}
        conflicts_list = data.get("conflicts_with", [])
        try:
            component_manager.validate_metadata_conflicts(comp_id, conflicts_list)
            return jsonify({"status": "valid"}), 200
        except ValueError as e:
            logging.warning(f"Metadata conflicts validation failed: {e}")
            return jsonify({"error": "Metadata conflict validation failed"}), 400
        except Exception as e:
            logging.error(
                f"Unexpected validation error for {comp_id}: {e}", exc_info=True
            )
            abort(500, "Unexpected validation error occurred")

    @app.route("/api/components/<comp_id>/group", methods=["PUT"])
    def update_component_group_route(comp_id):
        data = request.get_json() or {}
        new_group = data.get("group")
        if not new_group or not isinstance(new_group, str):
            abort(400, "Group ID is required and must be a string")
        try:
            component_manager.update_component_group(comp_id, new_group)
            return jsonify({"status": "updated"}), 200
        except KeyError:
            abort(404, f"Component '{comp_id}' not found")
        except Exception as e:
            logging.error(f"Failed to update group for {comp_id}: {e}", exc_info=True)
            abort(500, "Internal error updating component group")

    @app.route("/api/components/order", methods=["PUT"])
    def update_components_order_route():
        new_order = request.get_json()
        if not isinstance(new_order, list):
            abort(400, "Payload must be a list of component IDs")
        try:
            component_manager.update_components_order(new_order)
            return jsonify({"status": "updated"}), 200
        except Exception as e:
            logging.error(f"Failed to update components order: {e}", exc_info=True)
            abort(500, "Internal error updating component ordering")

    @app.route("/api/groups/order", methods=["PUT"])
    def update_groups_order_route():
        new_order = request.get_json()
        if not isinstance(new_order, list):
            abort(400, "Payload must be a list of group IDs")
        try:
            component_manager.update_group_order(new_order)
            return jsonify({"status": "updated"}), 200
        except Exception as e:
            logging.error(f"Failed to update groups order: {e}", exc_info=True)
            abort(500, "Internal error updating groups order")

    @app.route("/api/groups/<group_id>/rename", methods=["PUT"])
    def rename_group_route(group_id):
        data = request.get_json() or {}
        new_name = data.get("name")
        if not new_name or not isinstance(new_name, str):
            abort(400, "New name is required and must be a string")
        try:
            component_manager.rename_group(group_id, new_name)
            return jsonify({"status": "updated"}), 200
        except ValueError:
            abort(404, "Group not found or rename failed")
        except Exception as e:
            logging.error(f"Failed to rename group {group_id}: {e}", exc_info=True)
            abort(500, "Internal error renaming group")

    @app.route("/api/groups/<group_id>", methods=["DELETE"])
    def delete_group_route(group_id):
        try:
            component_manager.delete_group(group_id)
            return jsonify({"status": "deleted"}), 200
        except ValueError:
            abort(400, "Failed to delete group")
        except Exception as e:
            logging.error(f"Failed to delete group {group_id}: {e}", exc_info=True)
            abort(500, "Internal error deleting group")

    @app.route("/api/groups", methods=["GET"])
    def list_groups():
        try:
            meta = component_manager.get_njorddeploy_meta()
            group_rules = meta.get("group_rules", {})
            return jsonify(group_rules), 200
        except Exception as e:
            logging.error(f"Failed to list groups: {e}", exc_info=True)
            abort(500, "Internal error listing groups")

    # --- NEW PACKAGE ROUTES ---
    @app.route("/api/packages", methods=["GET"])
    def list_packages():
        return jsonify(component_manager.get_all_packages()), 200

    @app.route("/api/packages/<pkg_id>", methods=["PUT"])
    def update_package(pkg_id):
        data = request.get_json() or {}
        raw_name = data.get("name")
        name = str(raw_name) if raw_name else pkg_id.capitalize()
        try:
            packages = component_manager.get_all_packages()
            if pkg_id not in packages:
                component_manager.create_package(pkg_id, name)
            component_manager.update_package_metadata(pkg_id, data)
            return jsonify({"status": "updated"}), 200
        except Exception as e:
            logging.error(f"Failed to update package {pkg_id}: {e}", exc_info=True)
            abort(400, "Failed to update package metadata")

    @app.route("/api/packages/<pkg_id>", methods=["DELETE"])
    def delete_package(pkg_id):
        try:
            component_manager.delete_package(pkg_id)
            return jsonify({"status": "deleted"}), 200
        except ValueError:
            abort(400, "Failed to delete package")
        except Exception as e:
            logging.error(f"Failed to delete package {pkg_id}: {e}", exc_info=True)
            abort(500, "Internal error deleting package")

    @app.route("/api/generate_auth_hash", methods=["POST"])
    def generate_auth_hash():
        data = request.get_json() or {}
        username = data.get("username")
        password = data.get("password")
        if (
            not username
            or not password
            or not isinstance(username, str)
            or not isinstance(password, str)
        ):
            abort(400, "Username and password are required and must be strings")

        import bcrypt

        # Htpasswd BCrypt string formatting
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        hashed_str = f"{username}:{hashed.decode('utf-8')}"

        return jsonify({"hashed_user_string": hashed_str}), 200

    @app.route("/api/ai/providers", methods=["GET"])
    def get_ai_providers():
        """Returns the registry of supported AI providers."""
        from utils.ai_provider_manager import load_ai_providers_registry

        providers = load_ai_providers_registry()
        return jsonify({"providers": providers}), 200

    @app.route("/api/ai/status", methods=["GET", "POST"])
    def ai_status():
        """Checks the status of the requested or default AI provider."""
        from utils.ai_provider_manager import load_ai_providers_registry

        registry = load_ai_providers_registry()
        provider = None
        base_url = None
        if request.method == "POST":
            data = request.get_json() or {}
            provider = data.get("provider")
            base_url = data.get("base_url")

        if not provider:
            provider = os.getenv("AI_PROVIDER", "ollama")

        status = "offline"
        details = ""

        if provider == "ollama":
            url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            try:
                # Clean path to find raw tags list API
                tags_url = url.replace("/v1", "/api/tags")
                resp = requests.get(tags_url, timeout=3)
                if resp.status_code == 200:
                    status = "online"
                    details = "Ollama is running locally."
                    models_data = resp.json().get("models", [])
                    installed_models = [
                        m.get("name") for m in models_data if m.get("name")
                    ]
                    return (
                        jsonify(
                            {
                                "provider": provider,
                                "status": status,
                                "details": details,
                                "models": installed_models,
                            }
                        ),
                        200,
                    )
                else:
                    status = "offline"
                    details = f"Ollama returned HTTP {resp.status_code}."
            except Exception as e:
                status = "offline"
                details = f"Could not connect to Ollama at {url}: {e}"
        else:
            provider_info = registry.get(provider, {})
            var_name = provider_info.get("env_var")
            requires_key = provider_info.get("requires_api_key", True)

            if not requires_key:
                status = "online"
                details = f"Provider {provider} configured."
            elif not var_name:
                status = "offline"
                details = f"Unknown provider {provider}"
            else:
                key_exists = bool(os.getenv(var_name))
                if key_exists:
                    status = "online"
                    details = f"API Key configured in environment ({var_name})."
                else:
                    status = (
                        "configured_locally_only"
                        if request.method == "POST"
                        else "missing_key"
                    )
                    details = f"API Key ({var_name}) not found in .env file."

        return (
            jsonify({"provider": provider, "status": status, "details": details}),
            200,
        )

    @app.route("/api/ai/generate", methods=["POST"])
    def ai_generate_component():
        data = request.get_json() or {}
        repo_url = data.get("repo_url")
        custom_instructions = data.get("custom_instructions")
        api_key = data.get("api_key")
        save_key = data.get("save_key", False)
        provider = data.get("provider")
        if not provider:
            provider = "gemini" if api_key else os.getenv("AI_PROVIDER", "ollama")
        base_url = data.get("base_url")
        model = data.get("model")

        if not repo_url or not isinstance(repo_url, str):
            abort(400, "A valid Git repository URL is required")

        if isinstance(api_key, str):
            api_key = api_key.strip()

        try:
            # Extract list of existing groups from metadata
            njorddeploy_meta = component_manager.get_njorddeploy_meta()
            group_rules = njorddeploy_meta.get("group_rules", {})
            existing_groups = list(group_rules.keys())

            generator = AIGenerator(
                api_key=api_key,
                provider=provider,
                base_url=base_url,
                model=model,
            )
            result = generator.generate_component_data(
                repo_url, custom_instructions, existing_groups
            )

            key_saved = False
            # Save API key only if generation succeeded (proving key is valid)
            if isinstance(api_key, str) and save_key:
                try:
                    save_api_key_to_env(api_key, provider=provider)
                    key_saved = True
                except Exception as e:
                    logging.error(f"Failed to save API key to .env: {e}")

            return (
                jsonify(
                    {
                        "status": "success",
                        "data": result,
                        "key_saved": key_saved,
                    }
                ),
                200,
            )
        except ValueError as ve:
            err_msg = str(ve)
            if "API key missing for provider" in err_msg:
                msg = err_msg
            elif "repository URL is required" in err_msg:
                msg = "A valid Git repository URL is required"
            elif "repository URL format" in err_msg:
                msg = "Invalid repository URL format"
            else:
                msg = err_msg
            return jsonify({"error": msg}), 400
        except Exception as e:
            logging.error(f"Failed to generate component via AI: {e}", exc_info=True)
            err_msg = str(e)
            err_msg_lower = err_msg.lower()
            if "timeout" in err_msg_lower:
                return (
                    jsonify(
                        {
                            "error": "AI API Timeout",
                            "details": (
                                "The connection to the AI API timed out. "
                                "This is usually a temporary network issue or "
                                "the server is overloaded. Please try again."
                            ),
                        }
                    ),
                    504,
                )
            elif (
                "connection refused" in err_msg_lower
                or "could not connect" in err_msg_lower
                or "apiconnectionerror" in err_msg_lower
                or "connection error" in err_msg_lower
            ):
                return (
                    jsonify(
                        {
                            "error": "AI Connection Error",
                            "details": err_msg,
                        }
                    ),
                    502,
                )
            elif "api error" in err_msg_lower or "openai" in err_msg_lower:
                return (
                    jsonify(
                        {
                            "error": "AI API Error",
                            "details": err_msg,
                        }
                    ),
                    502,
                )
            else:
                return (
                    jsonify(
                        {
                            "error": "AI Generation Failed",
                            "details": err_msg,
                        }
                    ),
                    500,
                )

    @app.route("/api/components/ai", methods=["POST"])
    def save_ai_component():
        data = request.get_json() or {}
        component_id = data.get("id")
        metadata = data.get("metadata") or {}
        docker_compose = data.get("docker_compose")
        variables = data.get("variables") or []
        config_templates = data.get("config_templates") or {}

        if not component_id or not isinstance(component_id, str):
            abort(400, "A valid Component ID string is required")

        import re

        if not re.match(r"^[a-z0-9-]+$", component_id):
            abort(400, "Component ID must be alphanumeric and hyphens only")
        safe_component_id = secure_filename(component_id)

        name = metadata.get("name", component_id.capitalize())

        try:
            # Fallback: Extract docker_service_name from YAML if missing in metadata
            if "docker_service_name" not in metadata and isinstance(
                docker_compose, str
            ):
                try:
                    import yaml

                    cleaned_yaml = re.sub(
                        r'["\']?\{\{.*?\}\}["\']?:["\']?\{\{.*?\}\}["\']?',
                        '"JINJA_VAR"',
                        docker_compose,
                    )
                    cleaned_yaml = re.sub(r"\{\{.*?\}\}", "JINJA_VAR", cleaned_yaml)
                    cleaned_yaml = re.sub(r"\{%.*?%}", "JINJA_BLOCK", cleaned_yaml)
                    cleaned_yaml = re.sub(r"\{#.*?#}", "JINJA_COMMENT", cleaned_yaml)

                    compose_data = yaml.safe_load(cleaned_yaml)
                    if isinstance(compose_data, dict) and "services" in compose_data:
                        services = compose_data["services"]
                        if isinstance(services, dict) and services:
                            first_svc, *_ = list(services.keys())
                            metadata["docker_service_name"] = first_svc
                except Exception as parse_err:
                    logging.warning(
                        f"Failed to parse compose for service name: {parse_err}"
                    )

            # 1. Create component folder and skeleton
            component_manager.create_component(component_id, name)

            # 2. Update master metadata JSON
            component_manager.update_component_metadata(component_id, metadata)

            # 3. Update compose template content
            if isinstance(docker_compose, str) and docker_compose:
                component_manager.update_component_template_content(
                    component_id, docker_compose
                )

            # 4. Update variables JSON
            component_manager.update_component_variables(
                component_id, {"variables": variables}
            )

            # 5. Write other config files to template-config folder
            if config_templates:
                templates_root_path = component_manager.templates_path.resolve()
                config_dir = templates_root_path / safe_component_id / "template-config"
                safe_base = str(config_dir.resolve())
                if not safe_base.startswith(str(templates_root_path)):
                    abort(400, "Path traversal attempt detected")

                config_dir.mkdir(parents=True, exist_ok=True)
                for template_name, content in config_templates.items():
                    safe_name = secure_filename(os.path.basename(template_name))
                    if not re.match(r"^[a-zA-Z0-9._-]+$", safe_name):
                        abort(400, "Invalid configuration template filename")

                    requested_path = os.path.realpath(
                        os.path.join(safe_base, safe_name)
                    )
                    if not requested_path.startswith(safe_base):
                        abort(400, "Path traversal attempt detected")

                    with open(requested_path, "w", encoding="utf-8") as f:
                        f.write(content)

            # 6. Update components_order in _njorddeploy
            meta_data = component_manager.load_metadata()
            njorddeploy = meta_data.setdefault("_njorddeploy", {})
            order = njorddeploy.setdefault("components_order", [])
            if component_id not in order:
                order.append(component_id)
            component_manager.save_metadata()

            return jsonify({"status": "created"}), 201

        except ValueError as ve:
            err_msg = str(ve)
            if "already exists" in err_msg:
                msg = "Component already exists"
            elif "invalid" in err_msg.lower():
                msg = "Invalid component ID format"
            else:
                msg = "Failed to save component due to validation error"
            return jsonify({"error": msg}), 400
        except Exception as e:
            logging.error(
                f"Failed to save AI component {component_id}: {e}",
                exc_info=True,
            )
            err_msg = "Failed to save component due to an internal error"
            return jsonify({"error": err_msg}), 500

    return app


if __name__ == "__main__":
    from waitress import serve

    editor_app = create_app()
    port = int(os.environ.get("EDITOR_PORT", 5000))
    host = os.environ.get("EDITOR_HOST", "0.0.0.0")  # nosec B104
    serve(editor_app, host=host, port=port, threads=6)
