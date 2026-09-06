# src/configurator_app/app.py

import logging
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from configurator_app.openapi import get_openapi_spec
from managers.agent_manager import AgentManager
from managers.backup_manager import BackupManager
from managers.billing_manager import BillingManager
from managers.component_manager import ComponentManager
from managers.database_manager import DatabaseManager
from managers.deployment_evaluator import evaluate_deployment
from managers.deployment_manager import DeploymentManager
from managers.setup_manager import SetupManager
from managers.ssh_manager import SSHManager
from node_scanner import NodeScanner, get_tailscale_status
from utils.auth_utils import (
    GLOBAL_RATE_LIMITER,
    extract_api_key_from_request,
    generate_api_key,
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
)
from utils.resource_utils import (
    get_app_data_dir,
    get_components_paths,
    get_project_version,
    is_server_mode,
    seed_user_components_if_needed,
)
from utils.security_utils import is_safe_redirect_url

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def safe_join(base_dir: Path, user_path: str) -> Path:
    """Safely join base dir and user path to prevent path traversal."""
    # 1. Strictly validate characters to prevent traversal strings like dot-dot
    if not re.match(r"^[a-zA-Z0-9_-]+$", user_path):
        raise ValueError(f"Invalid path component: {user_path}")
    # 2. Resolve to absolute path
    resolved_base = base_dir.resolve()
    resolved_target = (resolved_base / user_path).resolve()
    # 3. Double-check path starts with base_dir
    if not resolved_target.is_relative_to(resolved_base):
        raise ValueError(f"Path traversal detected: {user_path}")
    return resolved_target


def analyze_snapshot(components, snapshot, _is_reinstallation):
    """Analyze system snapshot against components for conflicts/warnings."""
    conflicts = {"ports": [], "volumes": []}
    warnings = []
    used_ports = {
        p["port"]: p["process_name"] for p in snapshot.get("native_processes", [])
    }
    for container in snapshot.get("containers", []):
        ports_str = str(container.get("ports", ""))
        # Safe linear-time string scanning to avoid ReDoS polynomial backtracking
        for part in ports_str.replace(",", " ").split():
            if "0.0.0.0:" in part and "->" in part:
                try:
                    after_ip = part.split("0.0.0.0:")[1]
                    port_num_str = after_ip.split("->")[0]
                    if port_num_str.isdigit():
                        used_ports[int(port_num_str)] = (
                            f"docker container ({container.get('name')})"
                        )
                except IndexError:
                    continue

    existing_volumes = set()
    for container in snapshot.get("containers", []):
        mounts_val = container.get("mounts", "")
        mounts = str(mounts_val).split(",") if mounts_val else []
        for mount in mounts:
            if ":" in mount:
                host_path = mount.split(":")[0]
                if "." not in Path(host_path).name:
                    existing_volumes.add(host_path)

    for component in components:
        comp_name = str(component.get("name", "unknown"))
        comp_id = str(component.get("id", comp_name)).lower()
        comp_id_clean = comp_id.replace("-", "")

        for raw_port_str in component.get("ports", []):
            port_str = str(raw_port_str)
            # Safe linear matching of port layout
            if ":" in port_str:
                before_colon = port_str.split(":")[0]
                if before_colon.isdigit():
                    port = int(before_colon)
                    if port in used_ports:
                        conflicting_service = used_ports[port]
                        conflicting_service_clean = conflicting_service.lower().replace(
                            "-", ""
                        )

                        conflict_type = "UNEXPECTED_DOCKER_CONFLICT"
                        if conflicting_service == "unknown":
                            # Treat unknown as expected reinstallation/overwrite
                            # to avoid blocking on unresolvable process names
                            conflict_type = "EXPECTED_REINSTALLATION"
                        elif "docker" not in conflicting_service:
                            conflict_type = "DANGEROUS_NATIVE_PROCESS_CONFLICT"
                        elif (
                            "docker container" in conflicting_service.lower()
                            and comp_id_clean in conflicting_service_clean
                        ):
                            conflict_type = "EXPECTED_REINSTALLATION"

                        conflicts["ports"].append(
                            {
                                "port": port,
                                "conflict_type": conflict_type,
                                "conflicting_service": conflicting_service,
                                "proposed_service": comp_name,
                            }
                        )

        for raw_volume_str in component.get("volumes", []):
            volume_str = str(raw_volume_str)
            if ":" in volume_str:
                host_path = volume_str.split(":")[0]
                if host_path in existing_volumes:
                    conflicts["volumes"].append(
                        {
                            "volume_path": host_path,
                            "conflict_type": "EXISTING_VOLUME_CONFLICT",
                            "proposed_service": comp_name,
                        }
                    )

    ram = snapshot.get("resources", {}).get("ram", {})
    total_mb = int(ram.get("total_mb", 0))
    used_mb = int(ram.get("used_mb", 0))
    if total_mb > 0 and (used_mb / total_mb) > 0.9:
        warnings.append(
            {
                "type": "RAM",
                "message": "The target system is using over 90% of its RAM.",
            }
        )
    return conflicts, warnings


def map_analysis_to_report_errors(analysis_results: dict, target_ip: str) -> list[dict]:
    """Maps analysis results to standard ReportError structures."""
    errors = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conflicts = analysis_results.get("external_conflicts", {})

    port_conflicts = conflicts.get("ports", [])
    for conflict in port_conflicts:
        port = conflict.get("port")
        conflict_type = conflict.get("conflict_type")
        conflicting_service = conflict.get("conflicting_service")
        proposed_service = str(conflict.get("proposed_service", "N/A"))

        error_type = f"Validation:PortConflict:{conflict_type}"
        summary = f"Host port {port} conflict detected."
        details = (
            f"Port {port} is already in use by: '{conflicting_service}'. "
            f"The service '{proposed_service}' requires this port. "
            f"Conflict Type: {conflict_type}."
        )
        component_id = proposed_service.lower().replace(" ", "-")

        errors.append(
            {
                "type": error_type,
                "summary": summary,
                "details": details,
                "component_id": component_id,
                "timestamp": timestamp,
            }
        )

    volume_conflicts = conflicts.get("volumes", [])
    for conflict in volume_conflicts:
        volume_path = conflict.get("volume_path")
        conflict_type = conflict.get("conflict_type")
        proposed_service = str(conflict.get("proposed_service", "N/A"))

        error_type = f"Validation:VolumeConflict:{conflict_type}"
        summary = f"Host volume path conflict detected at '{volume_path}'."
        details = (
            f"The path '{volume_path}' already exists on the target system "
            f"({target_ip}) and is required for volume mounting by the service "
            f"'{proposed_service}'. Conflict Type: {conflict_type}. "
            f"This may lead to data corruption or permission issues."
        )
        component_id = proposed_service.lower().replace(" ", "-")

        errors.append(
            {
                "type": error_type,
                "summary": summary,
                "details": details,
                "component_id": component_id,
                "timestamp": timestamp,
            }
        )

    resource_warnings = analysis_results.get("resource_warnings", [])
    for warning in resource_warnings:
        warning_type = str(warning.get("type", "unknown"))
        message = str(warning.get("message", ""))

        error_type = f"Warning:Resource:{warning_type}"
        summary = f"Resource warning detected: {warning_type}"
        details = (
            f"The resource analysis on {target_ip} generated a warning: "
            f"{message}. Deployment may proceed, but performance may be impacted."
        )

        errors.append(
            {
                "type": error_type,
                "summary": summary,
                "details": details,
                "component_id": "N/A",
                "timestamp": timestamp,
            }
        )

    return errors


def create_app(test_config=None):
    """Factory function to create and configure the Flask application."""
    # Load environment variables from .env
    from dotenv import load_dotenv

    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        project_root = bundle_dir
        exe_dir = Path(sys.executable).parent
        loaded = False
        candidates = [
            exe_dir / ".env",
            Path.cwd() / ".env",
            Path(os.environ.get("NJORD_DATA_DIR", "/var/lib/njorddeploy")) / ".env",
            Path("/opt/njorddeploy/.env"),
        ]
        for env_candidate in candidates:
            if env_candidate.exists():
                load_dotenv(dotenv_path=env_candidate, override=True)
                loaded = True
                break
        if not loaded:
            load_dotenv()
    else:
        project_root = Path(__file__).resolve().parent.parent.parent
        load_dotenv(dotenv_path=project_root / ".env")

    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        template_folder = bundle_dir / "src" / "configurator_app" / "templates"
        if not template_folder.exists():
            template_folder = bundle_dir / "templates"
        static_folder = bundle_dir / "src" / "configurator_app" / "static"
        if not static_folder.exists():
            static_folder = bundle_dir / "static"
        flask_app = Flask(
            __name__,
            template_folder=str(template_folder),
            static_folder=str(static_folder),
            static_url_path="/static",
        )
    else:
        flask_app = Flask(__name__, static_folder="static", static_url_path="/static")

    flask_app.secret_key = get_or_create_secret_key()
    flask_app.config["SESSION_COOKIE_HTTPONLY"] = True
    flask_app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    flask_app.config["SESSION_COOKIE_NAME"] = "njord_session"
    if os.environ.get("NJORD_COOKIE_SECURE", "").lower() in ("true", "1"):
        flask_app.config["SESSION_COOKIE_SECURE"] = True

    from werkzeug.middleware.proxy_fix import ProxyFix

    flask_app.wsgi_app = ProxyFix(  # type: ignore
        flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    # Apply testing configuration if provided
    if test_config:
        flask_app.config.update(test_config)

    seed_user_components_if_needed()
    metadata_path_obj, templates_path_obj = get_components_paths()
    metadata_path = str(metadata_path_obj)
    templates_path = str(templates_path_obj)

    component_manager = ComponentManager(
        metadata_file_path=metadata_path, templates_path=templates_path
    )

    app_data_dir = get_app_data_dir()
    output_dir = app_data_dir / "output"

    setup_manager = SetupManager(component_manager.reader, output_dir=output_dir)
    deployment_manager = DeploymentManager(component_manager=component_manager)
    db_mgr = DatabaseManager.get_instance()
    billing_mgr = BillingManager(db=db_mgr)
    agent_mgr = AgentManager(db=db_mgr)

    flask_app.deployment_tasks = {}
    flask_app.map_analysis_to_report_errors = map_analysis_to_report_errors

    @flask_app.before_request
    def enforce_authentication():
        """
        Global request filter enforcing authentication across all endpoints.
        Whitelists health checks, static assets, and setup/login flows.
        """
        if request.path.startswith("/static/"):
            return None

        public_routes = {
            "/health",
            "/api/health",
            "/api/v1/health",
            "/login",
            "/api/login",
            "/logout",
            "/api/logout",
            "/setup",
            "/api/setup",
            "/register",
            "/api/register",
            "/install-agent",
            "/install-agent.sh",
            "/api/agent/install",
            "/api/agent/heartbeat",
            "/api/stripe/webhook",
            "/api/billing/webhook",
            "/api/v1/billing/webhook",
            "/api/first-run-status",
        }
        if request.path in public_routes:
            return None

        # Check if auth is disabled in test_config or environment
        if flask_app.config.get("AUTH_ENABLED") is False or not is_auth_enabled():
            return None

        # If admin is not configured, require first-run setup
        if not is_admin_configured():
            if is_api_request():
                return (
                    jsonify(
                        {
                            "error": "Setup required",
                            "setup_required": True,
                            "message": (
                                "NjordDeploy initial administrator setup "
                                "is required."
                            ),
                        }
                    ),
                    401,
                )
            return redirect(url_for("setup_wizard"))

        # Check active session
        if session.get("logged_in") and session.get("user"):
            # noinspection PyBroadException
            try:
                user_rec = db_mgr.get_user_by_username(session.get("user"))
                if user_rec and user_rec.get("plan"):
                    session["plan"] = user_rec.get("plan")
            except Exception as ex:
                logging.debug("Session plan sync skipped: %s", ex)
            return None

        # Check API Token / Bearer Key
        api_token = extract_api_key_from_request(request)
        if api_token and verify_api_key(api_token):
            return None

        # Unauthorized request
        if is_api_request():
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": (
                            "Authentication required. Provide a valid session or "
                            "API key via X-Njord-API-Key header."
                        ),
                    }
                ),
                401,
            )

        next_url = request.full_path if request.method == "GET" else "/"
        return redirect(url_for("login_page", next=next_url))

    @flask_app.route("/setup", methods=["GET"])
    def setup_wizard():
        """Renders the first-run onboarding setup wizard."""
        if is_admin_configured():
            if session.get("logged_in"):
                return redirect(url_for("index"))
            return redirect(url_for("login_page"))
        return render_template("setup.html")

    @flask_app.route("/setup", methods=["POST"])
    @flask_app.route("/api/setup", methods=["POST"])
    def process_setup():
        """Initializes the administrator account on first run."""
        if is_admin_configured():
            return (
                jsonify(
                    {
                        "error": "Setup already completed",
                        "message": "NjordDeploy administrator is already configured.",
                    }
                ),
                403,
            )

        data = request.get_json(silent=True) or request.form.to_dict() or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        confirm_password = str(data.get("confirm_password", ""))

        valid_user, user_err = validate_username(username)
        if not valid_user:
            return jsonify({"error": user_err or "Invalid username"}), 400

        valid_pass, pass_err = validate_password_strength(password)
        if not valid_pass:
            return jsonify({"error": pass_err or "Weak password"}), 400

        if confirm_password and password != confirm_password:
            return jsonify({"error": "Passwords do not match."}), 400

        pw_hash = hash_password(password)
        auth_data = save_auth_config(username=username, password_hash=pw_hash)

        session.clear()
        session["user"] = username
        session["logged_in"] = True
        session["login_time"] = time.time()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Administrator account configured successfully.",
                    "api_key": auth_data.get("api_key"),
                    "redirect": "/",
                }
            ),
            200,
        )

    @flask_app.route("/login", methods=["GET"])
    def login_page():
        """Renders the login page."""
        if not is_admin_configured() and is_auth_enabled():
            return redirect(url_for("setup_wizard"))
        if session.get("logged_in") and session.get("user"):
            next_url = request.args.get("next")
            if not next_url or not is_safe_redirect_url(next_url):
                next_url = url_for("index")
            return redirect(next_url)
        return render_template("login.html")

    @flask_app.route("/login", methods=["POST"])
    @flask_app.route("/api/login", methods=["POST"])
    def process_login():
        """Authenticates user credentials and establishes a session."""
        client_ip = get_client_ip(request)
        is_limited, retry_after = GLOBAL_RATE_LIMITER.is_rate_limited(client_ip)
        if is_limited:
            return (
                jsonify(
                    {
                        "error": (
                            "Too many failed login attempts. "
                            f"Please try again in {retry_after} seconds."
                        ),
                        "retry_after": retry_after,
                    }
                ),
                429,
            )

        data = request.get_json(silent=True) or request.form.to_dict() or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))

        if not username or not password:
            return (
                jsonify({"error": "Username and password are required."}),
                400,
            )

        if not verify_credentials(username, password):
            GLOBAL_RATE_LIMITER.record_failure(client_ip)
            return jsonify({"error": "Invalid username or password."}), 401

        GLOBAL_RATE_LIMITER.record_success(client_ip)
        session.clear()
        session["user"] = username
        session["logged_in"] = True
        session["login_time"] = time.time()

        next_url = request.args.get("next") or "/"
        return (
            jsonify(
                {
                    "status": "authenticated",
                    "user": username,
                    "redirect": next_url,
                }
            ),
            200,
        )

    @flask_app.route("/logout", methods=["GET", "POST"])
    @flask_app.route("/api/logout", methods=["POST"])
    def logout():
        """Logs out the current user and terminates session."""
        session.clear()
        if is_api_request():
            return jsonify({"status": "logged_out"}), 200
        return redirect(url_for("login_page"))

    @flask_app.route("/api/auth/status", methods=["GET"])
    def auth_status():
        """Returns the current authentication and configuration status."""
        return (
            jsonify(
                {
                    "authenticated": bool(
                        session.get("logged_in") and session.get("user")
                    ),
                    "user": session.get("user"),
                    "auth_enabled": is_auth_enabled(),
                    "admin_configured": is_admin_configured(),
                }
            ),
            200,
        )

    @flask_app.route("/api/auth/regenerate-api-key", methods=["POST"])
    def regenerate_api_key_route():
        """Regenerates the REST API token for the administrator."""
        if is_auth_enabled():
            if not (session.get("logged_in") and session.get("user")):
                token = extract_api_key_from_request(request)
                if not token or not verify_api_key(token):
                    return jsonify({"error": "Unauthorized"}), 401

        config = load_auth_config()
        if not config:
            return jsonify({"error": "Administrator not configured."}), 400

        new_key = generate_api_key()
        save_auth_config(
            username=config["username"],
            password_hash=config["password_hash"],
            api_key=new_key,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "API key successfully regenerated.",
                    "api_key": new_key,
                }
            ),
            200,
        )

    @flask_app.route("/api/auth/change-password", methods=["POST"])
    def change_password_route():
        """Updates the administrator password."""
        if is_auth_enabled():
            if not (session.get("logged_in") and session.get("user")):
                return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(silent=True) or {}
        current_pw = str(data.get("current_password", ""))
        new_pw = str(data.get("new_password", ""))
        confirm_pw = str(data.get("confirm_password", ""))

        config = load_auth_config()
        if not config:
            return jsonify({"error": "Administrator not configured."}), 400

        username = config["username"]
        if not verify_credentials(username, current_pw):
            return jsonify({"error": "Current password is incorrect."}), 400

        valid_pass, pass_err = validate_password_strength(new_pw)
        if not valid_pass:
            return jsonify({"error": pass_err or "Weak new password."}), 400

        if confirm_pw and new_pw != confirm_pw:
            return jsonify({"error": "New passwords do not match."}), 400

        new_hash = hash_password(new_pw)
        save_auth_config(username=username, password_hash=new_hash)
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Password changed successfully.",
                }
            ),
            200,
        )

    # --------------------------------------------------------------------------
    # SaaS & Multi-Tenancy Routes
    # --------------------------------------------------------------------------

    @flask_app.route("/register", methods=["GET"])
    def register_page():
        """Renders the user registration page."""
        if session.get("logged_in") and session.get("user"):
            return redirect(url_for("index"))
        return render_template("register.html")

    @flask_app.route("/register", methods=["POST"])
    @flask_app.route("/api/register", methods=["POST"])
    def process_registration():
        """Registers a new tenant user with a Free tier plan."""
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        email = str(data.get("email", "")).strip() or None

        valid_user, user_err = validate_username(username)
        if not valid_user:
            return jsonify({"error": user_err or "Invalid username"}), 400

        valid_pass, pass_err = validate_password_strength(password)
        if not valid_pass:
            return jsonify({"error": pass_err or "Weak password"}), 400

        if db_mgr.get_user_by_username(username):
            return jsonify({"error": "Username already taken."}), 409

        if email and db_mgr.get_user_by_email(email):
            return jsonify({"error": "Email address already registered."}), 409

        pw_hash = hash_password(password)
        api_key = generate_api_key()
        new_user = db_mgr.create_user(
            username=username,
            password_hash=pw_hash,
            email=email,
            role="user",
            plan="free",
            api_key=api_key,
        )

        session.clear()
        session["user"] = username
        session["user_id"] = new_user["id"]
        session["role"] = "user"
        session["plan"] = "free"
        session["logged_in"] = True
        session["login_time"] = time.time()

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Account created successfully.",
                    "user": username,
                    "plan": "free",
                    "redirect": "/",
                }
            ),
            201,
        )

    @flask_app.route("/api/servers", methods=["GET"])
    def list_user_servers():
        """Lists servers/nodes belonging to the logged-in user."""
        user_name = session.get("user")
        user = db_mgr.get_user_by_username(user_name) if user_name else None
        user_id = user["id"] if user else 1
        servers = db_mgr.list_servers_for_user(user_id)
        return jsonify({"status": "success", "servers": servers})

    @flask_app.route("/api/servers/add", methods=["POST"])
    def add_user_server():
        """Registers a new server node and generates the Agent install command."""
        user_name = session.get("user")
        user = db_mgr.get_user_by_username(user_name) if user_name else None
        user_id = user["id"] if user else 1

        can_add, err = billing_mgr.can_user_add_server(user_id)
        if not can_add:
            return jsonify({"error": err, "upgrade_required": True}), 403

        data = request.get_json(silent=True) or request.form.to_dict() or {}
        name = str(data.get("name", "")).strip() or "My Server"
        conn_type = str(data.get("connection_type", "agent"))
        ip = str(data.get("ip", "")).strip() or None

        server = agent_mgr.register_node(
            user_id=user_id, server_name=name, connection_type=conn_type, ip=ip
        )
        hub_url = request.host_url.rstrip("/")
        install_cmd = agent_mgr.generate_install_command(server["agent_token"], hub_url)

        return (
            jsonify(
                {
                    "status": "success",
                    "server": server,
                    "install_command": install_cmd,
                }
            ),
            201,
        )

    @flask_app.route("/install-agent", methods=["GET"])
    @flask_app.route("/install-agent.sh", methods=["GET"])
    @flask_app.route("/api/agent/install", methods=["GET"])
    def download_agent_installer():
        """Serves the dynamic node agent bash installer script."""
        hub_url = request.host_url.rstrip("/")
        token = request.args.get("token", "")
        script = agent_mgr.generate_install_script(hub_url=hub_url, agent_token=token)
        return Response(script, mimetype="text/x-shellscript")

    @flask_app.route("/api/agent/heartbeat", methods=["POST"])
    def agent_heartbeat():
        """Receives heartbeat telemetry from a connected node agent."""
        token = request.headers.get("X-Njord-Agent-Token") or request.args.get("token")
        if not token:
            return jsonify({"error": "Missing agent token"}), 401

        data = request.get_json(silent=True) or {}
        client_ip = get_client_ip(request)
        success, msg = agent_mgr.process_heartbeat(token, data, client_ip)
        if not success:
            return jsonify({"error": msg}), 401

        return jsonify({"status": "acknowledged", "message": msg})

    # --------------------------------------------------------------------------
    # Stripe Billing Endpoints
    # --------------------------------------------------------------------------

    @flask_app.route("/api/billing/status", methods=["GET"])
    def billing_status():
        """Returns plan info and server quota for the current user."""
        user_name = session.get("user")
        user = db_mgr.get_user_by_username(user_name) if user_name else None
        user_id = user["id"] if user else 1
        info = billing_mgr.get_user_plan_info(user_id)
        return jsonify({"status": "success", "billing": info})

    @flask_app.route("/api/billing/checkout", methods=["POST"])
    def start_checkout():
        """Creates a Stripe Checkout Session to upgrade to Pro (Monthly or Yearly)."""
        user_name = session.get("user")
        user = db_mgr.get_user_by_username(user_name) if user_name else None
        user_id = user["id"] if user else 1

        data = request.get_json(silent=True) or {}
        interval = data.get("interval", request.args.get("interval", "monthly"))
        price_id = data.get("price_id", request.args.get("price_id"))

        proto = request.headers.get("X-Forwarded-Proto", request.scheme)
        host = request.headers.get("X-Forwarded-Host", request.host)
        base_url = f"{proto}://{host}".rstrip("/")

        success_url = f"{base_url}/?billing=success"
        cancel_url = f"{base_url}/?billing=cancel"

        checkout_url, err = billing_mgr.create_checkout_session(
            user_id, success_url, cancel_url, interval=interval, price_id=price_id
        )
        if err or not checkout_url:
            return jsonify({"error": err or "Could not create checkout session"}), 400

        return jsonify({"status": "success", "checkout_url": checkout_url})

    @flask_app.route("/api/billing/portal", methods=["POST"])
    def start_portal():
        """Creates a Stripe Customer Portal session."""
        user_name = session.get("user")
        user = db_mgr.get_user_by_username(user_name) if user_name else None
        user_id = user["id"] if user else 1

        proto = request.headers.get("X-Forwarded-Proto", request.scheme)
        host = request.headers.get("X-Forwarded-Host", request.host)
        base_url = f"{proto}://{host}".rstrip("/")

        return_url = f"{base_url}/?billing=portal_return"
        portal_url, err = billing_mgr.create_customer_portal_session(
            user_id, return_url
        )
        if err or not portal_url:
            return jsonify({"error": err or "Could not open billing portal"}), 400

        return jsonify({"status": "success", "portal_url": portal_url})

    @flask_app.route("/api/v1/billing/webhook", methods=["POST"])
    @flask_app.route("/api/billing/webhook", methods=["POST"])
    @flask_app.route("/api/stripe/webhook", methods=["POST"])
    def stripe_webhook():
        """Inbound webhook handler for Stripe events."""
        payload = request.get_data()
        sig_header = request.headers.get("Stripe-Signature", "")
        success, msg = billing_mgr.handle_webhook_event(payload, sig_header)
        if not success:
            return jsonify({"error": msg}), 400
        return jsonify({"status": "processed", "message": msg})

    @flask_app.route("/health", methods=["GET"])
    @flask_app.route("/api/health", methods=["GET"])
    @flask_app.route("/api/v1/health", methods=["GET"])
    def health_check():
        """Returns health status, active mode, and catalog size for NjordDeploy."""
        from datetime import timezone

        mode = "service" if is_server_mode() else "standalone"
        all_components = component_manager.reader.get_all_components()
        catalog_count = len(all_components) if isinstance(all_components, dict) else 0

        return (
            jsonify(
                {
                    "status": "ok",
                    "version": get_project_version(),
                    "mode": mode,
                    "services_catalog": catalog_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            200,
        )

    @flask_app.route("/", methods=["GET"])
    def index():
        from managers.sync_manager import SyncManager
        from utils.container_engine import get_configured_engine

        engine = get_configured_engine()
        repo_config = SyncManager.get_repo_config()
        return render_template(
            "index.html",
            container_engine=engine,
            repo_config=repo_config,
        )

    @flask_app.route("/api/docs", methods=["GET"])
    def api_docs_page():
        """Renders interactive Swagger UI documentation."""
        return render_template("swagger.html")

    @flask_app.route("/api/openapi.json", methods=["GET"])
    def openapi_spec_json():
        """Returns the OpenAPI 3.0.3 specification JSON."""
        return jsonify(get_openapi_spec()), 200

    @flask_app.route("/robots.txt", methods=["GET"])
    def robots_txt() -> Response:
        """Serve robots.txt for search engines and AI crawlers."""
        return send_from_directory(
            flask_app.static_folder or "static",
            "robots.txt",
            mimetype="text/plain",
        )

    @flask_app.route("/llms.txt", methods=["GET"])
    def llms_txt() -> Response:
        """Serve machine-readable llms.txt standard index for AI models."""
        return send_from_directory(
            flask_app.static_folder or "static",
            "llms.txt",
            mimetype="text/markdown",
        )

    @flask_app.route("/llms-full.txt", methods=["GET"])
    def llms_full_txt() -> Response:
        """Serve consolidated documentation for LLM prompt context & RAG."""
        return send_from_directory(
            flask_app.static_folder or "static",
            "llms-full.txt",
            mimetype="text/markdown",
        )

    @flask_app.route("/help", methods=["GET"])
    def help_page():
        from utils.resource_utils import resource_path

        docs = {}
        for doc_name, filename in [
            ("Beginner's Quick Start", "docs/GETTING_STARTED_FOR_BEGINNERS.md"),
            ("Configurator Feature Tour", "docs/CONFIGURATOR_FEATURE_GUIDE.md"),
            ("Editor Feature Tour", "docs/EDITOR_FEATURE_GUIDE.md"),
            ("Introduction", "README.md"),
            ("REST API Reference", "docs/API_REFERENCE.md"),
            ("User & Network Guide", "docs/USER_GUIDE.md"),
            ("Contributing Guide", "CONTRIBUTING.md"),
            ("Helper Utilities", "UTILITIES.md"),
        ]:
            path = resource_path(filename)
            content = "Documentation file not found."
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading file: {e}"
            docs[doc_name] = content

        return render_template("help.html", docs=docs)

    @flask_app.route("/settings", methods=["GET"])
    def settings_page():
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        raw_content = ""
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()
            except Exception as e:
                logging.error(f"Error reading .env: {e}")

        # Parse key-values for form fields
        env_vars = {}
        for line in raw_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("\"'")
                env_vars[key] = val

        auth_config = load_auth_config() or {}
        auth_info = {
            "auth_enabled": is_auth_enabled(),
            "admin_configured": is_admin_configured(),
            "username": auth_config.get("username", "admin"),
            "api_key": auth_config.get("api_key", ""),
        }

        return render_template(
            "settings.html",
            env_vars=env_vars,
            raw_content=raw_content,
            auth_info=auth_info,
        )

    @flask_app.route("/api/settings", methods=["POST"])
    def update_settings():
        data = request.get_json() or {}
        mode = data.get("mode")
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"

        if mode == "raw":
            raw_content = data.get("raw_content", "")
            try:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(raw_content)

                # Re-load env vars into os.environ
                for line in raw_content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        os.environ[k] = v

                return (
                    jsonify({"message": "Settings updated successfully"}),
                    200,
                )
            except Exception as e:
                logging.error(f"Failed to save .env file: {e}", exc_info=True)
                return (
                    jsonify({"error": "Failed to save .env file."}),
                    500,
                )

        elif mode == "form":
            new_vars = data.get("settings", {})
            if not isinstance(new_vars, dict):
                return jsonify({"error": "Invalid settings payload"}), 400

            try:
                # Read current content to merge/preserve comments
                current_content = ""
                if env_path.exists():
                    with open(env_path, "r", encoding="utf-8") as f:
                        current_content = f.read()

                lines = current_content.splitlines()
                updated_keys = set()
                new_lines = []

                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        key, val = stripped.split("=", 1)
                        key = key.strip()
                        if key in new_vars:
                            val_str = str(new_vars[key])
                            new_lines.append(f'{key}="{val_str}"')
                            updated_keys.add(key)
                            # Update in running process environment
                            os.environ[key] = val_str
                            continue
                    new_lines.append(line)

                # Append any new keys
                for key, val in new_vars.items():
                    if key not in updated_keys:
                        val_str = str(val)
                        new_lines.append(f'{key}="{val_str}"')
                        os.environ[key] = val_str

                new_content = "\n".join(new_lines) + "\n"
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                return (
                    jsonify({"message": "Settings updated successfully"}),
                    200,
                )
            except Exception as e:
                logging.error(f"Failed to update settings: {e}", exc_info=True)
                return (
                    jsonify({"error": "Failed to update settings."}),
                    500,
                )

        else:
            return jsonify({"error": "Invalid update mode"}), 400

    @flask_app.route("/api/engine-status", methods=["GET"])
    def get_engine_status():
        """Returns the active container engine and repository configuration."""
        from managers.sync_manager import SyncManager
        from utils.container_engine import ContainerEngine

        engine = ContainerEngine()
        repo_config = SyncManager.get_repo_config()
        return jsonify(
            {
                "engine": engine.engine,
                "is_docker": engine.is_docker,
                "is_podman": engine.is_podman,
                "supported_engines": ["docker", "podman"],
                "repo_url": repo_config.get("url"),
                "repo_branch": repo_config.get("branch"),
                "is_remote_sync_enabled": repo_config.get("is_enabled"),
            }
        )

    @flask_app.route("/api/engine-switch", methods=["POST"])
    def switch_engine():
        """Switches the active container engine dynamically and persists to .env."""
        data = request.get_json(force=True) or {}
        new_engine = data.get("engine", "").strip().lower()
        if new_engine not in ("docker", "podman"):
            return (
                jsonify(
                    {"error": "Invalid container engine. Must be 'docker' or 'podman'."}
                ),
                400,
            )

        os.environ["CONTAINER_ENGINE"] = new_engine
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        try:
            current_content = ""
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    current_content = f.read()

            lines = current_content.splitlines()
            updated = False
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("CONTAINER_ENGINE="):
                    new_lines.append(f'CONTAINER_ENGINE="{new_engine}"')
                    updated = True
                else:
                    new_lines.append(line)
            if not updated:
                new_lines.append(f'CONTAINER_ENGINE="{new_engine}"')

            with open(env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")

            return (
                jsonify(
                    {
                        "status": "success",
                        "engine": new_engine,
                        "message": (
                            f"Container engine successfully switched to "
                            f"{new_engine.upper()}."
                        ),
                    }
                ),
                200,
            )
        except Exception as e:
            logging.error(f"Failed to persist engine setting: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to persist engine setting."}),
                500,
            )

    @flask_app.route("/api/validate-repo", methods=["POST"])
    def validate_repository():
        """Validates connectivity to a candidate components repository URL."""
        from managers.sync_manager import SyncManager

        data = request.get_json(force=True) or {}
        repo_url = str(data.get("url", "")).strip()
        branch = str(data.get("branch", "main")).strip()
        token = str(data.get("token", "")).strip()

        if not repo_url:
            return (
                jsonify({"valid": False, "message": "Repository URL cannot be empty."}),
                400,
            )

        is_valid, msg = SyncManager.validate_remote_repo(
            repo_url, branch, token or None
        )
        return jsonify({"valid": is_valid, "message": msg}), (200 if is_valid else 400)

    @flask_app.route("/api/first-run-status", methods=["GET"])
    def first_run_status():
        """Returns whether first-run onboarding is pending."""
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        is_first_run = not env_path.exists()
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "CONTAINER_ENGINE=" in content or "COMPONENTS_REPO_URL=" in content:
                    is_first_run = False
            except Exception as e:
                logging.debug(f"Could not read .env: {e}")
        return jsonify({"first_run": is_first_run})

    @flask_app.route("/nmap-status", methods=["GET"])
    def nmap_status():
        import shutil

        installed = shutil.which("nmap") is not None
        return jsonify(
            {
                "installed": installed,
                "message": (
                    "nmap is installed."
                    if installed
                    else (
                        "nmap is not installed. Install via "
                        "'sudo apt install nmap' for L2 subnet scanning."
                    )
                ),
            }
        )

    @flask_app.route("/tailscale-status", methods=["GET"])
    def tailscale_status():
        return jsonify(get_tailscale_status())

    @flask_app.route("/scan-pis", methods=["POST"])
    def scan_pis():
        data = request.get_json(silent=True) or {}
        discovery_method = data.get("discovery_method")
        if discovery_method == "tailscale":
            ts_status = get_tailscale_status()
            if ts_status.get("active"):
                return jsonify(
                    {
                        "hosts": ts_status.get("peers", []),
                        "messages": [
                            "✅ Tailscale Mesh Discovery found "
                            f"{len(ts_status.get('peers', []))} online node(s)."
                        ],
                        "error": None,
                        "detection_info": {
                            "success": True,
                            "method_used": "tailscale",
                        },
                    }
                )
            return (
                jsonify(
                    {
                        "error": (
                            "Tailscale discovery failed: "
                            f"{ts_status.get('reason', 'Tailscale inactive')}"
                        ),
                        "messages": [],
                    }
                ),
                400,
            )

        if discovery_method == "direct_ip":
            target_ip = data.get("direct_target_ip", "").strip()
            if not target_ip:
                return (
                    jsonify({"error": "Direct IP target address cannot be blank."}),
                    400,
                )

            # If target_ip is a MAC address, resolve it by scanning the network
            if re.match(r"^([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})$", target_ip):
                subnet = data.get("subnet")
                if subnet is not None and not isinstance(subnet, str):
                    subnet = None
                try:
                    scanner = NodeScanner(
                        username=os.environ.get("PI_SCANNER_USERNAME", "dummy"),
                        password=os.environ.get("PI_SCANNER_PASSWORD", "dummy"),
                    )
                    hosts, messages, error, detection_info = scanner.scan(subnet=subnet)
                    if error:
                        logging.error(
                            f"Scanner scan failed for MAC resolution: {error}"
                        )
                        return (
                            jsonify(
                                {
                                    "error": (
                                        "Failed to scan network to resolve "
                                        f"MAC address: {error}"
                                    ),
                                    "messages": messages,
                                }
                            ),
                            500,
                        )

                    search_mac = target_ip.replace("-", ":").lower()
                    resolved_host: dict | None = None
                    for h in hosts:
                        if h.get("mac", "").replace("-", ":").lower() == search_mac:
                            resolved_host = h
                            break

                    if resolved_host is None:
                        return (
                            jsonify(
                                {
                                    "error": (
                                        "Could not find any device with MAC "
                                        f"address {target_ip} on the network."
                                    ),
                                    "messages": messages
                                    + [f"Scanned network to find MAC: {target_ip}"],
                                }
                            ),
                            404,
                        )

                    resolved_ip = resolved_host["ip"]
                    logging.info(f"Resolved MAC {target_ip} to IP {resolved_ip}")
                    return jsonify(
                        {
                            "hosts": [
                                {
                                    "ip": resolved_ip,
                                    "mac": resolved_host.get("mac"),
                                    "vendor": resolved_host.get("vendor"),
                                    "hostname": resolved_host.get(
                                        "hostname", "remote-target"
                                    ),
                                    "status": "selected",
                                }
                            ],
                            "messages": messages
                            + [
                                "Resolved MAC address "
                                f"{target_ip} to IP address {resolved_ip}."
                            ],
                            "error": None,
                            "detection_info": detection_info,
                        }
                    )
                except Exception as e:
                    logging.error(f"MAC resolution failed: {e}", exc_info=True)
                    return (
                        jsonify(
                            {
                                "error": (
                                    "An unexpected error occurred "
                                    "resolving MAC address."
                                ),
                                "messages": [],
                            }
                        ),
                        500,
                    )

            print(
                "Antigravity bypass: Skipping subnet scan. "
                f"Directly targeting host: {target_ip}"
            )
            return jsonify(
                {
                    "hosts": [
                        {
                            "ip": target_ip,
                            "hostname": "remote-tailscale-target",
                            "status": "selected",
                        }
                    ],
                    "messages": [f"Directly targeting host: {target_ip}"],
                    "error": None,
                    "detection_info": {},
                }
            )

        subnet = data.get("subnet")
        if subnet is not None and not isinstance(subnet, str):
            subnet = None
        try:
            scanner = NodeScanner(
                username=os.environ.get("PI_SCANNER_USERNAME", "dummy"),
                password=os.environ.get("PI_SCANNER_PASSWORD", "dummy"),
            )
            hosts, messages, error, detection_info = scanner.scan(subnet=subnet)
            if error:
                logging.error(f"Scanner scan failed: {error}")
                return (
                    jsonify({"error": error, "messages": messages}),
                    500,
                )
            return jsonify(
                {
                    "hosts": hosts,
                    "messages": messages,
                    "error": error,
                    "detection_info": detection_info,
                }
            )
        except Exception as e:
            logging.error(f"Pi scanning failed: {e}", exc_info=True)
            return (
                jsonify(
                    {
                        "error": "An unexpected error occurred "
                        "during network scanning.",
                        "messages": [],
                    }
                ),
                500,
            )

    @flask_app.route("/api/proxmox/create-lxc", methods=["POST"])
    def create_proxmox_lxc():
        from managers.ssh_manager import SSHManager
        from utils.proxmox_client import ProxmoxClient

        data = request.get_json() or {}
        cores = int(data.get("cores", 4))
        memory = int(data.get("memory", 8192))
        storage_size = str(data.get("storage_size", "40"))
        storage_name = str(data.get("storage_name", "local-lvm"))
        node = str(data.get("node", os.getenv("PROXMOX_NODE", "pve")))
        password = str(data.get("password", "PiSelfhostLXC2026!"))
        hostname = str(data.get("hostname", "")).strip()

        if hostname:
            import re

            hostname = re.sub(r"[\s_]+", "-", hostname)
            hostname = re.sub(r"[^a-zA-Z0-9\-]", "", hostname)
            hostname = re.sub(r"-+", "-", hostname)
            hostname = hostname.strip("-")
            hostname = hostname[:63]

        host = os.getenv("PROXMOX_HOST", "https://192.168.178.51:8006")
        user = os.getenv("PROXMOX_USER", "root@pam")
        token_id = os.getenv("PROXMOX_TOKEN_ID", "")
        token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")

        if not token_id or not token_secret:
            return (
                jsonify(
                    {
                        "error": (
                            "Proxmox API token credentials "
                            "are not configured in your .env file."
                        )
                    }
                ),
                500,
            )

        try:
            client = ProxmoxClient(host, user, token_id, token_secret)

            # Pre-flight: guard against DHCP pool exhaustion.
            # If too many stopped CTs exist, the DHCP server may be out of
            # leases. Refuse to create a new one and report the stale VMIDs.
            stale_ct_threshold = 10
            existing_lxc = client.get_lxc_list(node)
            if hostname:
                duplicate_cts = [
                    ct
                    for ct in existing_lxc
                    if str(ct.get("name", "")).lower() == hostname.lower()
                ]
                if duplicate_cts:
                    dup_vmids = sorted(int(ct.get("vmid", 0)) for ct in duplicate_cts)
                    return (
                        jsonify(
                            {
                                "error": (
                                    f"Pre-flight check failed: A container with the "
                                    f"hostname '{hostname}' already exists on node "
                                    f"'{node}'. Hostnames must be unique to avoid "
                                    f"DHCP and DNS conflicts. Please delete the "
                                    f"existing container or choose a different name. "
                                    f"Conflicting VMID(s): {dup_vmids}"
                                )
                            }
                        ),
                        409,
                    )

            stopped_cts = [ct for ct in existing_lxc if ct.get("status") == "stopped"]
            if len(stopped_cts) >= stale_ct_threshold:
                stale_vmids = sorted(int(ct.get("vmid", 0)) for ct in stopped_cts)
                return (
                    jsonify(
                        {
                            "error": (
                                f"Pre-flight check failed: {len(stopped_cts)} "
                                f"stopped LXC containers detected on node "
                                f"'{node}'. This may exhaust the DHCP lease "
                                f"pool and prevent new containers from "
                                f"receiving an IPv4 address. Please destroy "
                                f"stale containers before provisioning a new "
                                f"one. Stale VMIDs: {stale_vmids}"
                            )
                        }
                    ),
                    409,
                )

            # 1. Next VMID
            vmid = client.get_next_vmid()

            # 2. SSH key from SSHManager
            dummy_manager = SSHManager(
                hostname="localhost", username="root", password=""
            )  # nosec B106
            ssh_key = dummy_manager.get_ssh_key()
            pubkey = f"{ssh_key.get_name()} {ssh_key.get_base64()}"

            # 3. Locate template
            storages = ["local"]
            try:
                storage_res = client.get(f"nodes/{node}/storage")
                active_vztmpl_storages = []
                for store in storage_res.get("data", []):
                    is_active = store.get("active")
                    content_types = store.get("content", "")
                    if is_active and "vztmpl" in content_types:
                        name = store.get("storage")
                        if name:
                            active_vztmpl_storages.append(name)
                if active_vztmpl_storages:
                    # Prioritize 'local' but include all others
                    storages = sorted(
                        active_vztmpl_storages, key=lambda x: x != "local"
                    )
            except Exception as e:
                logging.warning(f"Failed to list Proxmox storage pools: {e}")

            templates = []
            for s in storages:
                try:
                    res = client.get(
                        f"nodes/{node}/storage/{s}/content",
                        params={"content": "vztmpl"},
                    )
                    templates.extend(res.get("data", []))
                except Exception as e:
                    logging.warning(f"Failed to query templates on storage '{s}': {e}")

            debian_templates = [
                t for t in templates if "debian" in t.get("volid", "").lower()
            ]
            ostemplate = ""
            if debian_templates:
                debian_templates.sort(key=lambda x: x.get("volid", ""), reverse=True)
                newest_deb = next(iter(debian_templates), None)
                if isinstance(newest_deb, dict):
                    volid = newest_deb.get("volid")
                    if isinstance(volid, str) and volid:
                        ostemplate = volid

            if not ostemplate:
                ubuntu_templates = [
                    t for t in templates if "ubuntu" in t.get("volid", "").lower()
                ]
                if ubuntu_templates:
                    ubuntu_templates.sort(
                        key=lambda x: x.get("volid", ""), reverse=True
                    )
                    newest_ubu = next(iter(ubuntu_templates), None)
                    if isinstance(newest_ubu, dict):
                        volid = newest_ubu.get("volid")
                        if isinstance(volid, str) and volid:
                            ostemplate = volid

            if not ostemplate:
                any_temp = next(iter(templates), None)
                if isinstance(any_temp, dict):
                    volid = any_temp.get("volid")
                    if isinstance(volid, str) and volid:
                        ostemplate = volid

            if not ostemplate:
                default_storage = next(iter(storages), "local")
                try:
                    aplinfo_res = client.get(f"nodes/{node}/aplinfo")
                    apl_data = aplinfo_res.get("data", [])
                    deb_apls = [
                        item
                        for item in apl_data
                        if "debian" in item.get("package", "").lower()
                        and "standard" in item.get("package", "").lower()
                    ]
                    if not deb_apls:
                        deb_apls = [
                            item
                            for item in apl_data
                            if "ubuntu" in item.get("package", "").lower()
                        ]
                    if deb_apls:
                        deb_apls.sort(key=lambda x: x.get("template", ""), reverse=True)
                        target_tpl = deb_apls[0].get("template")
                        if target_tpl:
                            logging.info(
                                f"Downloading LXC template '{target_tpl}' "
                                f"to '{default_storage}' storage on node '{node}'..."
                            )
                            dl_res = client.post(
                                f"nodes/{node}/aplinfo",
                                data={
                                    "template": target_tpl,
                                    "storage": default_storage,
                                },
                            )
                            upid = dl_res.get("data")
                            if upid and isinstance(upid, str):
                                for _ in range(30):
                                    time.sleep(3)
                                    status_res = client.get(
                                        f"nodes/{node}/tasks/{upid}/status"
                                    )
                                    s_data = status_res.get("data", {})
                                    if s_data.get("status") == "stopped":
                                        break
                            ostemplate = f"{default_storage}:vztmpl/{target_tpl}"
                except Exception as apl_err:
                    logging.warning(
                        f"Failed to auto-download LXC template via aplinfo: {apl_err}"
                    )

            if not ostemplate:
                storage_display = storages[0] if storages else "local"
                return (
                    jsonify(
                        {
                            "error": (
                                f"No LXC template found on Proxmox host. "
                                f"Please download a Debian LXC template in Proxmox "
                                f"(Storage '{storage_display}' -> "
                                f"CT Templates -> Templates)."
                            )
                        }
                    ),
                    400,
                )

            # 4. Create LXC
            net_config = "name=eth0,bridge=vmbr0,firewall=0,ip=dhcp"
            rootfs_config = f"{storage_name}:{storage_size}"
            features_config = "nesting=1"

            create_data = {
                "vmid": vmid,
                "ostemplate": ostemplate,
                "cores": cores,
                "memory": memory,
                "swap": 512,
                "rootfs": rootfs_config,
                "net0": net_config,
                "features": features_config,
                "unprivileged": 1,
                "password": password,
                "ssh-public-keys": pubkey,
                "start": 1,
            }
            if hostname:
                create_data["hostname"] = hostname

            result = client.post(f"nodes/{node}/lxc", data=create_data)
            upid = result.get("data")

            # 5. Wait for the Proxmox provisioning task to complete
            #    (same approach as proxmox_test_runner.py — wait for UPID)
            if upid:
                logging.info(f"Waiting for Proxmox task to complete: {upid}")
                task_deadline = 180
                task_start = time.time()
                while time.time() - task_start < task_deadline:
                    # noinspection PyBroadException
                    try:
                        task_res = client.get(f"nodes/{node}/tasks/{upid}/status")
                        task_data = task_res.get("data", {})
                        current_task_status = task_data.get("status")
                        if current_task_status == "stopped":
                            exit_status = task_data.get("exitstatus")
                            if exit_status == "OK":
                                logging.info("Proxmox task completed successfully.")
                                break
                            else:
                                return (
                                    jsonify(
                                        {
                                            "error": (
                                                f"LXC creation task failed: "
                                                f"{exit_status}"
                                            )
                                        }
                                    ),
                                    500,
                                )
                    except Exception:  # nosec B110
                        pass
                    time.sleep(2)

            # 6. Poll for IPv4 address (UPID task already confirmed container is up)
            ip_address = None
            for attempt in range(30):
                try:
                    res_if = client.get(f"nodes/{node}/lxc/{vmid}/interfaces")
                    interfaces = res_if.get("data", [])
                    logging.info(
                        f"[LXC IP poll #{attempt + 1}] interfaces: {interfaces}"
                    )
                    for iface in interfaces:
                        if iface.get("name") != "eth0":
                            continue
                        # Only accept IPv4 from `inet`; ignore `inet6` entirely.
                        inet = iface.get("inet", "")
                        if not inet:
                            continue
                        ip_candidate, *_rest = inet.split("/")
                        if (
                            ip_candidate
                            and not ip_candidate.startswith("127.")
                            and not ip_candidate.startswith("169.254.")
                        ):
                            ip_address = ip_candidate
                            break
                    if ip_address:
                        break
                except Exception as poll_err:  # nosec B110
                    logging.warning(f"[LXC IP poll #{attempt + 1}] error: {poll_err}")
                time.sleep(4)

            if not isinstance(ip_address, str):
                return (
                    jsonify(
                        {
                            "error": (
                                "LXC container created, but failed to acquire "
                                "an IPv4 address in time. Check server logs."
                            )
                        }
                    ),
                    500,
                )

            # 7. Install Docker via SSH — wait for SSH daemon to start
            time.sleep(10)
            ssh = SSHManager(
                hostname=ip_address,
                username="root",
                password=password,
                allow_auto_add=True,
                load_system_keys=False,
            )
            connected, conn_msg = ssh.connect()
            if not connected:
                return (
                    jsonify(
                        {
                            "error": (
                                f"Failed to connect to container via SSH: "
                                f"{conn_msg}"
                            )
                        }
                    ),
                    500,
                )

            from utils.container_engine import ContainerEngine

            engine = ContainerEngine()
            install_commands = engine.get_provisioning_commands(username="root")

            for cmd in install_commands:
                max_retries = 12 if ("apt-get" in cmd or "get-docker.sh" in cmd) else 1
                for attempt in range(max_retries):
                    exit_code, stdout = ssh.execute_command(cmd, lambda x: None)
                    if exit_code == 0:
                        break
                    if "lock" in stdout and attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    return (
                        jsonify(
                            {
                                "error": (
                                    f"Provisioning failed on command "
                                    f"'{cmd}': {stdout}"
                                )
                            }
                        ),
                        500,
                    )

            return (
                jsonify(
                    {
                        "status": "success",
                        "ip": ip_address,
                        "vmid": vmid,
                        "hostname": hostname or f"CT{vmid}",
                        "username": "root",
                        "password": password,
                    }
                ),
                201,
            )

        except Exception as e:
            logging.error(f"Failed to create Proxmox LXC: {e}", exc_info=True)
            return (
                jsonify({"error": "Proxmox LXC creation failed."}),
                500,
            )

    @flask_app.route("/api/proxmox/list-templates", methods=["POST"])
    def list_proxmox_templates():
        from utils.proxmox_client import ProxmoxClient

        host = os.getenv("PROXMOX_HOST", "https://192.168.178.51:8006")
        user = os.getenv("PROXMOX_USER", "root@pam")
        token_id = os.getenv("PROXMOX_TOKEN_ID", "")
        token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")
        node = os.getenv("PROXMOX_NODE", "pve")

        if not token_id or not token_secret:
            return (
                jsonify(
                    {
                        "error": (
                            "Proxmox API token credentials "
                            "are not configured in your .env file."
                        )
                    }
                ),
                500,
            )

        try:
            client = ProxmoxClient(host, user, token_id, token_secret)
            qemu_res = client.get(f"nodes/{node}/qemu")
            qemu_list = qemu_res.get("data", [])
            templates = []
            for item in qemu_list:
                if item.get("template") or item.get("template") == 1:
                    templates.append(
                        {
                            "vmid": int(item.get("vmid", 0)),
                            "name": str(item.get("name", f"VM{item.get('vmid')}")),
                        }
                    )
            return (
                jsonify({"templates": sorted(templates, key=lambda x: x["vmid"])}),
                200,
            )

        except Exception as e:
            logging.error(f"Failed to list Proxmox QEMU templates: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to list templates."}),
                500,
            )

    @flask_app.route("/api/proxmox/create-vm", methods=["POST"])
    def create_proxmox_vm():
        from managers.ssh_manager import SSHManager
        from utils.proxmox_client import ProxmoxClient

        data = request.get_json() or {}
        cores = int(data.get("cores", 4))
        memory = int(data.get("memory", 8192))
        storage_name = str(data.get("storage_name", "local-lvm"))
        storage_size = data.get("storage_size")
        node = str(data.get("node", os.getenv("PROXMOX_NODE", "pve")))
        password = str(data.get("password", "PiSelfhostLXC2026!"))
        hostname = str(data.get("hostname", "")).strip()
        template_vmid = data.get("template_vmid")
        username = str(data.get("username", "debian")).strip()

        if not template_vmid:
            return jsonify({"error": "Template VMID is required."}), 400

        try:
            template_vmid = int(template_vmid)
        except ValueError:
            return jsonify({"error": "Template VMID must be an integer."}), 400

        if hostname:
            import re

            hostname = re.sub(r"[\s_]+", "-", hostname)
            hostname = re.sub(r"[^a-zA-Z0-9\-]", "", hostname)
            hostname = re.sub(r"-+", "-", hostname)
            hostname = hostname.strip("-")
            hostname = hostname[:63]

        host = os.getenv("PROXMOX_HOST", "https://192.168.178.51:8006")
        user = os.getenv("PROXMOX_USER", "root@pam")
        token_id = os.getenv("PROXMOX_TOKEN_ID", "")
        token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")

        if not token_id or not token_secret:
            return (
                jsonify(
                    {
                        "error": (
                            "Proxmox API token credentials "
                            "are not configured in your .env file."
                        )
                    }
                ),
                500,
            )

        try:
            client = ProxmoxClient(host, user, token_id, token_secret)

            # Pre-flight check: duplicate VM name
            qemu_res = client.get(f"nodes/{node}/qemu")
            qemu_list = qemu_res.get("data", [])
            if hostname:
                duplicate_vms = [
                    vm
                    for vm in qemu_list
                    if str(vm.get("name", "")).lower() == hostname.lower()
                ]
                if duplicate_vms:
                    dup_vmids = sorted(int(vm.get("vmid", 0)) for vm in duplicate_vms)
                    return (
                        jsonify(
                            {
                                "error": (
                                    f"Pre-flight check failed: A VM with the "
                                    f"hostname '{hostname}' already exists on node "
                                    f"'{node}'. Hostnames must be unique. "
                                    f"Conflicting VMID(s): {dup_vmids}"
                                )
                            }
                        ),
                        409,
                    )

            # 1. Get next unused VMID
            vmid = client.get_next_vmid()

            # 2. Retrieve public SSH key
            dummy_manager = SSHManager(
                hostname="localhost", username="root", password=""
            )  # nosec B106
            ssh_key = dummy_manager.get_ssh_key()
            pubkey = f"{ssh_key.get_name()} {ssh_key.get_base64()}"

            # 3. Clone VM template (try linked clone, fallback to full clone)
            logging.info(f"Cloning VM template {template_vmid} to {vmid}...")
            try:
                clone_res = client.clone_vm(
                    node=node,
                    vmid=template_vmid,
                    newid=vmid,
                    name=hostname or f"VM{vmid}",
                    full=False,
                )
                upid = clone_res.get("data")
            except Exception as clone_err:
                if "Linked clone feature is not supported" in str(clone_err):
                    logging.warning(
                        "Linked clone not supported, falling back to full clone..."
                    )
                    clone_res = client.clone_vm(
                        node=node,
                        vmid=template_vmid,
                        newid=vmid,
                        name=hostname or f"VM{vmid}",
                        full=True,
                    )
                    upid = clone_res.get("data")
                else:
                    raise

            # 4. Wait for cloning task to complete
            if upid:
                logging.info(f"Waiting for Proxmox clone task to complete: {upid}")
                task_deadline = 240  # cloning can take slightly longer
                task_start = time.time()
                while time.time() - task_start < task_deadline:
                    try:
                        task_res = client.get(f"nodes/{node}/tasks/{upid}/status")
                        task_data = task_res.get("data", {})
                        current_task_status = task_data.get("status")
                        if current_task_status == "stopped":
                            exit_status = task_data.get("exitstatus")
                            if exit_status == "OK":
                                logging.info("VM clone task completed successfully.")
                                break
                            else:
                                return (
                                    jsonify(
                                        {
                                            "error": (
                                                f"VM clone task failed: "
                                                f"{exit_status}"
                                            )
                                        }
                                    ),
                                    500,
                                )
                    except Exception:  # nosec B110
                        pass
                    time.sleep(2)

            # 4.5 Resize Disk (if requested)
            if storage_size:
                try:
                    storage_size_gb = int(storage_size)
                    vm_cfg_res = client.get(f"nodes/{node}/qemu/{vmid}/config")
                    vm_cfg = vm_cfg_res.get("data", {})
                    bootdisk = vm_cfg.get("bootdisk")
                    if not bootdisk:
                        for candidate in ["scsi0", "virtio0", "sata0", "ide0"]:
                            if candidate in vm_cfg:
                                bootdisk = candidate
                                break
                    if not bootdisk:
                        bootdisk = "scsi0"

                    logging.info(
                        f"Resizing VM {vmid} disk '{bootdisk}' to {storage_size_gb}G..."
                    )
                    client.resize_vm_disk(
                        node=node,
                        vmid=vmid,
                        disk=bootdisk,
                        size=f"{storage_size_gb}G",
                    )
                except Exception as resize_err:
                    logging.warning(f"Could not resize VM {vmid} disk: {resize_err}")

            # 5. Configure Cloud-Init
            import urllib.parse

            logging.info(f"Configuring Cloud-Init for VMID {vmid}...")
            config_data = {
                "cores": cores,
                "memory": memory,
                "ciuser": username,
                "cipassword": password,
                "sshkeys": urllib.parse.quote(pubkey),
                "ipconfig0": "ip=dhcp",
                "agent": "enabled=1",
                "cpu": "host",
            }
            try:
                client.configure_vm(node=node, vmid=vmid, config_data=config_data)
            except Exception as cfg_err:
                if "already exists" in str(cfg_err):
                    logging.warning(
                        f"Cloud-Init drive already exists for VM {vmid}: {cfg_err}"
                    )
                else:
                    config_data["ide2"] = f"{storage_name}:cloudinit"
                    client.configure_vm(node=node, vmid=vmid, config_data=config_data)

            # 6. Start the VM
            logging.info(f"Starting VM {vmid}...")
            client.start_vm(node=node, vmid=vmid)

            # 7. Poll for guest agent to report IP
            ip_address = None
            for attempt in range(40):  # VMs can take longer to boot than containers
                try:
                    ip = client.get_vm_ip(node, vmid)
                    if (
                        ip
                        and not ip.startswith("127.")
                        and not ip.startswith("169.254.")
                    ):
                        ip_address = ip
                        break
                except Exception as poll_err:
                    logging.warning(f"[VM IP poll #{attempt + 1}] error: {poll_err}")
                time.sleep(4)

            if not isinstance(ip_address, str):
                return (
                    jsonify(
                        {
                            "error": (
                                "VM created, but failed to acquire "
                                "an IPv4 address in time via QEMU guest agent. "
                                "Check server logs."
                            )
                        }
                    ),
                    500,
                )

            # 8. Install Docker via SSH
            time.sleep(15)  # wait for boot completion
            ssh = SSHManager(
                hostname=ip_address,
                username=username,
                password=password,
                allow_auto_add=True,
                load_system_keys=False,
            )

            connected = False
            conn_msg = ""
            for conn_attempt in range(5):
                connected, conn_msg = ssh.connect()
                if connected:
                    break
                time.sleep(5)

            if not connected:
                return (
                    jsonify(
                        {"error": (f"Failed to connect to VM via SSH: " f"{conn_msg}")}
                    ),
                    500,
                )

            from utils.container_engine import ContainerEngine

            engine = ContainerEngine()
            install_commands = engine.get_provisioning_commands(username=username)

            for cmd in install_commands:
                max_retries = 12 if ("apt-get" in cmd or "get-docker.sh" in cmd) else 1
                for attempt in range(max_retries):
                    exit_code, stdout = ssh.execute_command(cmd, lambda x: None)
                    if exit_code == 0:
                        break
                    if "lock" in stdout and attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    return (
                        jsonify(
                            {
                                "error": (
                                    f"Provisioning failed on command "
                                    f"'{cmd}': {stdout}"
                                )
                            }
                        ),
                        500,
                    )

            return (
                jsonify(
                    {
                        "status": "success",
                        "ip": ip_address,
                        "vmid": vmid,
                        "hostname": hostname or f"VM{vmid}",
                        "username": username,
                        "password": password,
                    }
                ),
                201,
            )

        except Exception as e:
            logging.error(f"Failed to create Proxmox VM: {e}", exc_info=True)
            return (
                jsonify({"error": "Proxmox VM creation failed."}),
                500,
            )

    @flask_app.route("/api/proxmox/list-targets", methods=["POST"])
    def list_proxmox_targets():
        from utils.proxmox_client import ProxmoxClient

        host = os.getenv("PROXMOX_HOST", "https://192.168.178.51:8006")
        user = os.getenv("PROXMOX_USER", "root@pam")
        token_id = os.getenv("PROXMOX_TOKEN_ID", "")
        token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")
        node = os.getenv("PROXMOX_NODE", "pve")

        if not token_id or not token_secret:
            return (
                jsonify(
                    {
                        "error": (
                            "Proxmox API token credentials "
                            "are not configured in your .env file."
                        )
                    }
                ),
                500,
            )

        try:
            client = ProxmoxClient(host, user, token_id, token_secret)
            targets = []

            # 1. Query LXC containers on the node
            # noinspection PyBroadException
            try:
                lxc_res = client.get(f"nodes/{node}/lxc")
                lxc_list = lxc_res.get("data", [])
                for item in lxc_list:
                    if item.get("template"):
                        continue
                    targets.append(
                        {
                            "vmid": int(item.get("vmid", 0)),
                            "name": str(item.get("name", f"CT{item.get('vmid')}")),
                            "type": "lxc",
                            "status": str(item.get("status", "unknown")),
                            "node": node,
                        }
                    )
            except Exception as e:
                logging.warning(f"Failed to fetch Proxmox LXCs: {e}")

            # 2. Query QEMU VMs on the node
            # noinspection PyBroadException
            try:
                qemu_res = client.get(f"nodes/{node}/qemu")
                qemu_list = qemu_res.get("data", [])
                for item in qemu_list:
                    if item.get("template"):
                        continue
                    targets.append(
                        {
                            "vmid": int(item.get("vmid", 0)),
                            "name": str(item.get("name", f"VM{item.get('vmid')}")),
                            "type": "qemu",
                            "status": str(item.get("status", "unknown")),
                            "node": node,
                        }
                    )
            except Exception as e:
                logging.warning(f"Failed to fetch Proxmox QEMU VMs: {e}")

            return jsonify({"targets": sorted(targets, key=lambda x: x["vmid"])}), 200

        except Exception as e:
            logging.error(f"Failed to list Proxmox targets: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to list Proxmox targets."}),
                500,
            )

    @flask_app.route("/api/proxmox/get-target-ip", methods=["POST"])
    def get_proxmox_target_ip():
        from utils.proxmox_client import ProxmoxClient

        data = request.get_json() or {}
        vmid = int(data.get("vmid", 0))
        target_type = str(data.get("type", "")).strip()
        node = str(data.get("node", os.getenv("PROXMOX_NODE", "pve"))).strip()

        if not vmid or target_type not in ["lxc", "qemu"]:
            return jsonify({"error": "Invalid VMID or target type"}), 400

        host = os.getenv("PROXMOX_HOST", "https://192.168.178.51:8006")
        user = os.getenv("PROXMOX_USER", "root@pam")
        token_id = os.getenv("PROXMOX_TOKEN_ID", "")
        token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")

        try:
            client = ProxmoxClient(host, user, token_id, token_secret)
            ip_address = None

            if target_type == "lxc":
                res_if = client.get(f"nodes/{node}/lxc/{vmid}/interfaces")
                interfaces = res_if.get("data", [])
                for iface in interfaces:
                    if iface.get("name") != "eth0":
                        continue
                    inet = iface.get("inet", "")
                    if not inet:
                        continue
                    ip_candidate, *_rest = inet.split("/")
                    if (
                        ip_candidate
                        and not ip_candidate.startswith("127.")
                        and not ip_candidate.startswith("169.254.")
                    ):
                        ip_address = ip_candidate
                        break
            else:
                ip_address = client.get_vm_ip(node, vmid)

            return jsonify({"ip": ip_address}), 200

        except Exception as e:
            logging.error(f"Failed to query Proxmox target IP: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to query target IP."}),
                500,
            )

    @flask_app.route("/api/proxmox/start-target", methods=["POST"])
    def start_proxmox_target():
        from utils.proxmox_client import ProxmoxClient

        data = request.get_json() or {}
        vmid = int(data.get("vmid", 0))
        target_type = str(data.get("type", "")).strip()
        node = str(data.get("node", os.getenv("PROXMOX_NODE", "pve"))).strip()

        if not vmid or target_type not in ["lxc", "qemu"]:
            return jsonify({"error": "Invalid VMID or target type"}), 400

        host = os.getenv("PROXMOX_HOST", "https://192.168.178.51:8006")
        user = os.getenv("PROXMOX_USER", "root@pam")
        token_id = os.getenv("PROXMOX_TOKEN_ID", "")
        token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")

        try:
            client = ProxmoxClient(host, user, token_id, token_secret)

            endpoint = f"nodes/{node}/{target_type}/{vmid}/status/start"
            client.post(endpoint)

            ip_address = None
            for attempt in range(15):
                # noinspection PyBroadException
                try:
                    if target_type == "lxc":
                        res_if = client.get(f"nodes/{node}/lxc/{vmid}/interfaces")
                        interfaces = res_if.get("data", [])
                        for iface in interfaces:
                            if iface.get("name") != "eth0":
                                continue
                            inet = iface.get("inet", "")
                            if not inet:
                                continue
                            ip_candidate, *_rest = inet.split("/")
                            if (
                                ip_candidate
                                and not ip_candidate.startswith("127.")
                                and not ip_candidate.startswith("169.254.")
                            ):
                                ip_address = ip_candidate
                                break
                    else:
                        ip_address = client.get_vm_ip(node, vmid)

                    if ip_address:
                        break
                except Exception:  # nosec B110
                    pass
                time.sleep(4)

            if not ip_address:
                return (
                    jsonify(
                        {
                            "error": (
                                "Target started, but failed to acquire "
                                "an IP address in time."
                            )
                        }
                    ),
                    500,
                )

            return jsonify({"ip": ip_address}), 200

        except Exception as e:
            logging.error(f"Failed to start Proxmox target: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to start target."}),
                500,
            )

    @flask_app.route("/set-ip", methods=["POST"])
    def set_ip_address():
        data = request.get_json() or {}
        ip = data.get("ip")
        if not ip or not isinstance(ip, str):
            return jsonify({"error": "No valid IP address provided"}), 400
        session["target_ip"] = ip
        return jsonify({"message": "IP address set successfully"}), 200

    @flask_app.route("/get-device-details", methods=["POST"])
    def get_device_details():
        data = request.get_json() or {}
        ip_address = data.get("ip")
        username = data.get("username")
        password = data.get("password")
        if (
            not isinstance(ip_address, str)
            or not isinstance(username, str)
            or not isinstance(password, str)
        ):
            return (
                jsonify({"error": "Missing or invalid IP, username, or password"}),
                400,
            )
        try:
            device_scanner = NodeScanner(username=username, password=password)
            snapshot, error = device_scanner.get_system_snapshot(ip_address)
            if error:
                logging.error(f"Snapshot retrieval failed: {error}")
                return jsonify({"error": "Failed to retrieve device details."}), 400
            if snapshot:
                ram_total_mb = (
                    snapshot.get("resources", {}).get("ram", {}).get("total_mb", 0)
                )
                details = {
                    "model": snapshot.get("model"),
                    "serial": snapshot.get("serial"),
                    "os_version": snapshot.get("os_version", "Linux"),
                    "docker_is_active": snapshot.get("docker_is_active", False),
                    "ram": f"{ram_total_mb} MB",
                    "disks": [
                        {
                            "mounted_on": "/",
                            "size": snapshot.get("resources", {})
                            .get("disk", {})
                            .get("size"),
                            "pcent": snapshot.get("resources", {})
                            .get("disk", {})
                            .get("pcent"),
                        }
                    ],
                }
                return jsonify(details)
            else:
                return jsonify({"error": "No device details retrieved"}), 400
        except Exception as e:
            logging.error(
                f"Error getting details for IP {ip_address}: {e}", exc_info=True
            )
            return jsonify({"error": "An unexpected internal error occurred."}), 500

    @flask_app.route("/api/components", methods=["GET"])
    def api_components():
        try:
            all_components = component_manager.get_all_components()
            components_dict = {comp["id"]: comp for comp in all_components}
            return jsonify(components_dict), 200
        except Exception as e:
            logging.error(f"Failed to retrieve components: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve components."}), 500

    @flask_app.route("/get-available-software", methods=["POST"])
    def get_available_software():
        try:
            all_components = component_manager.get_all_components(
                include_variables=True
            )
            all_packages = component_manager.get_all_packages()
            return (
                jsonify(
                    {
                        "available_software": all_components,
                        "available_packages": all_packages,
                    }
                ),
                200,
            )
        except Exception as e:
            logging.error(f"Failed to get available software: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve software list."}), 500

    @flask_app.route("/get-software-groups", methods=["GET"])
    def get_software_groups():
        try:
            all_components = component_manager.get_all_components()
            meta = component_manager.get_njorddeploy_meta()
            group_rules = meta.get("group_rules", {})
            group_order = meta.get("group_order", [])
            id_to_name_map = {
                gid: rules.get("name", gid.replace("_", " ").title())
                for gid, rules in group_rules.items()
            }
            id_to_exclusive_map = {
                gid: rules.get("is_exclusive", False)
                for gid, rules in group_rules.items()
            }
            components_by_group_id = {}
            for component in all_components:
                group_id = component.get("group")
                component_id = component.get("id")
                if group_id and component_id:
                    if group_id not in components_by_group_id:
                        components_by_group_id[group_id] = []
                    components_by_group_id[group_id].append(component_id)
            groups_to_components = {}
            for group_id in group_order:
                if group_id in components_by_group_id:
                    display_name = id_to_name_map.get(group_id, group_id)
                    is_exclusive = id_to_exclusive_map.get(group_id, False)
                    comps = components_by_group_id.pop(group_id)
                    if display_name in groups_to_components:
                        groups_to_components[display_name]["components"].extend(comps)
                    else:
                        groups_to_components[display_name] = {
                            "is_exclusive": is_exclusive,
                            "components": comps,
                        }
            for group_id, comp_list in sorted(components_by_group_id.items()):
                display_name = id_to_name_map.get(group_id, group_id)
                is_exclusive = id_to_exclusive_map.get(group_id, False)
                if display_name in groups_to_components:
                    groups_to_components[display_name]["components"].extend(comp_list)
                else:
                    groups_to_components[display_name] = {
                        "is_exclusive": is_exclusive,
                        "components": comp_list,
                    }
            return jsonify({"groups": groups_to_components}), 200
        except Exception as e:
            logging.error(f"Failed to get software groups: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve software groups."}), 500

    @flask_app.route("/get-required-variables", methods=["POST"])
    def get_required_variables():
        try:
            data = request.get_json(force=True) or {}
            selected_components = data.get("selected_components")
            if not isinstance(selected_components, list):
                return jsonify({"error": "Missing or invalid selected_components"}), 400

            all_components_list = component_manager.get_all_components(
                include_variables=True
            )
            all_components_dict = {comp["id"]: comp for comp in all_components_list}
            components_for_ui = {}

            for component_id in selected_components:
                component_data = all_components_dict.get(component_id)
                if component_data:
                    vars_list = component_data.get("variables") or component_data.get(
                        "required_variables"
                    )
                    if not vars_list:
                        vars_list = component_manager.reader.get_component_variables(
                            component_id
                        )
                    if vars_list:
                        components_for_ui[component_id] = {
                            "name": component_data.get("name", component_id),
                            "variables": vars_list,
                        }
            return jsonify({"components": components_for_ui}), 200
        except Exception as e:
            logging.error(f"Failed to get variables: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to retrieve configuration variables."}),
                500,
            )

    @flask_app.route("/validate-selection", methods=["POST"])
    def validate_selection():
        try:
            data = request.get_json(force=True) or {}
            selected_components = data.get("selected_components")
            if not isinstance(selected_components, list):
                return jsonify({"error": "Missing or invalid selected_components"}), 400

            base_template_path = templates_path_obj
            all_components_dict = {
                comp["id"]: comp for comp in component_manager.get_all_components()
            }

            for component_id in selected_components:
                # Mitigate Path Traversal / CWE-22 using safe_join helper
                try:
                    template_path_obj = safe_join(base_template_path, component_id)
                except ValueError:
                    logging.warning(
                        f"Validation failed for component ID: {component_id}"
                    )
                    return (
                        jsonify(
                            {
                                "error": "Invalid component ID format "
                                "or path traversal.",
                                "component_id": component_id,
                            }
                        ),
                        400,
                    )

                if not template_path_obj.exists():
                    return (
                        jsonify(
                            {
                                "error": f"Template directory "
                                f"missing: '{component_id}'.",
                                "component_id": component_id,
                            }
                        ),
                        400,
                    )
                component_data = all_components_dict.get(component_id)
                if component_data and component_data.get("has_configuration"):
                    variables_path = (
                        template_path_obj / "template-config" / "variables.json"
                    )
                    if not variables_path.is_file():
                        return (
                            jsonify(
                                {
                                    "error": f"'variables.json'"
                                    f" missing: '{component_id}'.",
                                    "component_id": component_id,
                                }
                            ),
                            400,
                        )
            return jsonify({"message": "Selection is valid."}), 200
        except Exception as e:
            logging.error(f"Validation process failed: {e}", exc_info=True)
            return jsonify({"error": "An unexpected validation error occurred."}), 500

    @flask_app.route("/api/v1/system/analyze", methods=["POST"])
    def system_analyze():
        data = request.get_json() or {}
        is_reinstallation = bool(data.get("is_reinstallation", False))
        devices = data.get("devices")
        raw_components = data.get("components")

        if not isinstance(devices, list) or not isinstance(raw_components, list):
            return jsonify({"error": "Missing 'devices' or 'components' list"}), 400

        enriched_components = []
        all_components_list = component_manager.get_all_components()
        all_components_dict = {comp["id"]: comp for comp in all_components_list}

        for raw_comp in raw_components:
            comp_id = raw_comp.get("id")
            meta = all_components_dict.get(comp_id, {})
            enriched_components.append(
                {
                    "id": comp_id,
                    "name": raw_comp.get("name", comp_id),
                    "ports": raw_comp.get("ports") or meta.get("ports", []),
                    "volumes": raw_comp.get("volumes") or meta.get("volumes", []),
                }
            )

        internal_port_map = {}
        for component in enriched_components:
            for port_str in component.get("ports", []):
                # Safe linear parsing to avoid ReDoS
                if ":" in port_str:
                    before_colon = port_str.split(":")[0]
                    if before_colon.isdigit():
                        port = before_colon
                        if port in internal_port_map:
                            conflict_msg = (
                                f"Port {port} is used by "
                                f"'{internal_port_map[port]}' and "
                                f"'{component.get('name')}'."
                            )
                            return (
                                jsonify(
                                    {
                                        "status": "error",
                                        "error": conflict_msg,
                                        "internal_conflicts": [conflict_msg],
                                    }
                                ),
                                400,
                            )
                        internal_port_map[port] = component.get("name")

        if not devices:
            return jsonify({"error": "No target devices provided for analysis."}), 400

        device = next(iter(devices), None)
        if not isinstance(device, dict):
            return jsonify({"error": "No target devices provided for analysis."}), 400

        analysis_scanner = NodeScanner(
            username=device.get("username"), password=device.get("password")
        )
        snapshot, err = analysis_scanner.get_system_snapshot(device.get("ip"))

        if err:
            logging.error(
                f"Pre-deployment analysis failed for {device.get('ip')}: {err}"
            )
            return (
                jsonify(
                    {
                        "error": (
                            f"Failed to retrieve system details for analysis: {err}"
                        )
                    }
                ),
                500,
            )

        external_conflicts, resource_warnings = analyze_snapshot(
            enriched_components, snapshot, is_reinstallation
        )

        return (
            jsonify(
                {
                    "status": "success",
                    "internal_conflicts": [],
                    "external_conflicts": external_conflicts,
                    "resource_warnings": resource_warnings,
                }
            ),
            200,
        )

    @flask_app.route("/start-installation", methods=["POST"])
    def start_installation():
        try:
            data = request.get_json(force=True) or {}
            selected_components = data.get("selected_components")
            managed_devices = data.get("devices")
            user_variables = data.get("env_vars", {})

            if not isinstance(selected_components, list) or not isinstance(
                managed_devices, list
            ):
                return (
                    jsonify({"error": "Missing or invalid selection or devices"}),
                    400,
                )

            if not isinstance(user_variables, dict):
                user_variables = {}

            success, errors = setup_manager.prepare_deployment_package(
                selected_components, user_variables, managed_devices
            )
            if not success:
                logging.error(f"Installation preparation failed: {errors}")
                return jsonify({"error": "File generation failed."}), 400

            # Generate the unified docker-compose.yml and .env files
            all_components_list = component_manager.get_all_components()
            selected_components_data = [
                c for c in all_components_list if c.get("id") in selected_components
            ]
            component_manager.generate_deployment_artifacts(
                selected_components_data=selected_components_data,
                global_vars=user_variables,
                output_path=Path(setup_manager.output_dir),
            )

            return (
                jsonify(
                    {
                        "message": "Configuration files generated.",
                        "output_path": str(setup_manager.output_dir),
                    }
                ),
                200,
            )
        except Exception as e:
            logging.error(f"Installation failed: {e}", exc_info=True)
            return (
                jsonify(
                    {"error": "An unexpected deployment packaging error occurred."}
                ),
                500,
            )

    @flask_app.route("/deploy-configuration", methods=["POST"])
    def deploy_configuration():
        data = request.get_json(force=True) or {}
        output_path = data.get("output_path")
        managed_devices = data.get("devices", [])
        components_to_clean = data.get("components_to_clean", [])
        components_to_restart = data.get("components_to_restart", [])
        analysis_results = data.get("analysis_results", {})
        selected_components_data = data.get("selected_components_data", [])
        global_vars = data.get("global_vars", {})

        if not isinstance(output_path, str) or not isinstance(managed_devices, list):
            return jsonify({"error": "Missing or invalid output_path or devices"}), 400

        if not isinstance(components_to_clean, list):
            components_to_clean = []
        if not isinstance(components_to_restart, list):
            components_to_restart = []
        if not isinstance(analysis_results, dict):
            analysis_results = {}
        if not isinstance(selected_components_data, list):
            selected_components_data = []
        if not isinstance(global_vars, dict):
            global_vars = {}

        first_device = next(iter(managed_devices), {})
        if not first_device:
            return jsonify({"error": "No target device provided for deployment"}), 400

        target_ip = first_device.get("ip", "unknown")
        all_errors = flask_app.map_analysis_to_report_errors(
            analysis_results, target_ip
        )

        blocking_types = [
            "Validation:PortConflict:DANGEROUS_NATIVE_PROCESS_CONFLICT",
            "Validation:VolumeConflict:EXISTING_VOLUME_CONFLICT",
            "Validation:PortConflict:UNEXPECTED_DOCKER_CONFLICT",
        ]

        blocking_errors = [err for err in all_errors if err["type"] in blocking_types]

        if blocking_errors:
            logging.error(
                f"Blocking pre-deployment conflicts detected: "
                f"{len(blocking_errors)} errors."
            )
            return (
                jsonify(
                    {
                        "error": "Pre-deployment conflicts detected.",
                        "details": "Critical conflicts must be resolved first.",
                        "errors": blocking_errors,
                    }
                ),
                400,
            )

        task_id = uuid.uuid4().hex

        non_blocking_errors = [
            err for err in all_errors if err["type"] not in blocking_types
        ]
        logs_start = [
            f"WARNING/INFO: {err['summary']}. See task status for details."
            for err in non_blocking_errors
        ]

        flask_app.deployment_tasks[task_id] = {
            "status": "running",
            "logs": logs_start,
            "errors": non_blocking_errors,
        }

        flask_app.deployment_tasks[task_id]["logs"].append(
            "Starting deployment process..."
        )

        thread = threading.Thread(
            target=deployment_manager.start_deployment,
            args=(
                task_id,
                flask_app.deployment_tasks,
                output_path,
                managed_devices,
                components_to_clean,
                components_to_restart,
                selected_components_data,
                global_vars,
            ),
        )
        thread.start()
        return jsonify({"task_id": task_id}), 202

    @flask_app.route("/stream-deployment/<target_task_id>")
    def stream_deployment(target_task_id):
        def generate():
            last_sent_index = 0
            while True:
                task = flask_app.deployment_tasks.get(target_task_id)
                if not isinstance(task, dict):
                    break

                logs_to_send = task.get("logs", [])[last_sent_index:]
                for log_line in logs_to_send:
                    yield f"data: {log_line}\n\n"
                last_sent_index += len(logs_to_send)

                if task.get("status") != "running":
                    break
                time.sleep(0.5)

        return Response(generate(), mimetype="text/event-stream")

    @flask_app.route("/task-status/<target_task_id>")
    def task_status(target_task_id):
        task = flask_app.deployment_tasks.get(target_task_id)
        if not isinstance(task, dict):
            return jsonify({"error": "Task not found"}), 404
        return jsonify(task)

    @flask_app.route("/api/deployment/<target_task_id>/evaluate", methods=["POST"])
    def evaluate_deployment_task(target_task_id):
        """Evaluates deployment session logs and returns a health report."""
        task = flask_app.deployment_tasks.get(target_task_id)
        if not isinstance(task, dict):
            return jsonify({"error": "Deployment task not found"}), 404

        data = request.get_json(force=True) if request.data else {}
        component_name = data.get("component_name", "deployed-stack")
        use_ai = data.get("use_ai", True)

        logs_list = task.get("logs", [])
        log_text = "\n".join(logs_list)
        status_str = task.get("status", "failed")
        exit_code = 0 if status_str == "completed" else 1

        result = evaluate_deployment(
            component_name=component_name,
            log_text=log_text,
            exit_code=exit_code,
            container_status={"running": exit_code == 0},
            use_ai=use_ai,
        )
        return jsonify(result)

    @flask_app.route("/get-container-logs", methods=["POST"])
    def get_container_logs():
        """Retrieve the latest docker logs for a specific container."""
        try:
            data = request.get_json(force=True) or {}
            ip_address = data.get("ip")
            username = data.get("username")
            password = data.get("password")
            container_name = data.get("container_name", "njorddeploy-portainer")

            if (
                not isinstance(ip_address, str)
                or not isinstance(username, str)
                or not isinstance(password, str)
                or not isinstance(container_name, str)
            ):
                return (
                    jsonify(
                        {
                            "error": (
                                "Missing or invalid IP, username, "
                                "password, or container name"
                            )
                        }
                    ),
                    400,
                )

            # Prevent shell injection by validating container name characters
            if not re.match(r"^[a-zA-Z0-9_-]+$", container_name):
                return jsonify({"error": "Invalid container name format."}), 400

            import shlex
            import time

            from managers.ssh_manager import SSHManager

            ssh = SSHManager(
                hostname=ip_address,
                username=username,
                password=password,
                allow_auto_add=True,
                load_system_keys=False,
            )
            connected = False
            msg = ""
            # Retry connection up to 3 times to handle transient SSH banner timeouts
            for attempt in range(3):
                connected, msg = ssh.connect()
                if connected:
                    break
                time.sleep(1)

            if not connected:
                return jsonify({"error": f"Failed to connect to host: {msg}"}), 400

            # Determine command using ContainerEngine
            from utils.container_engine import ContainerEngine

            engine = ContainerEngine()
            if engine.is_docker:
                exit_code_group, _ = ssh.execute_command(
                    "docker ps", lambda x: None, check_exit_code=False
                )
                if exit_code_group == 0:
                    cmd = (
                        f"CID=$(docker ps -a --filter name={container_name} "
                        f"--format '{{{{.ID}}}}' | head -n 1); "
                        f'if [ -n "$CID" ]; then docker logs --tail 200 "$CID"; '
                        f"else docker logs --tail 200 {container_name}; fi"
                    )
                else:
                    quoted_password = shlex.quote(password)
                    cmd = (
                        f"echo {quoted_password} | "
                        f'sudo -S sh -c "CID=\\$(docker ps -a '
                        f"--filter name={container_name} --format '{{{{.ID}}}}' "
                        f'| head -n 1); if [ -n \\"\\$CID\\" ]; then '
                        f'docker logs --tail 200 \\"\\$CID\\"; '
                        f'else docker logs --tail 200 {container_name}; fi"'
                    )
            else:
                cmd = (
                    f"CID=$(podman ps -a --filter name={container_name} "
                    f"--format '{{{{.ID}}}}' | head -n 1); "
                    f'if [ -n "$CID" ]; then podman logs --tail 200 "$CID"; '
                    f"else podman logs --tail 200 {container_name}; fi"
                )

            log_lines = []

            def log_callback(chunk: str):
                log_lines.append(chunk)

            exit_code, stdout = ssh.execute_command(
                cmd, log_callback, check_exit_code=False
            )
            ssh.close()

            full_log = "".join(log_lines)

            # Strip ANSI escape sequences (color codes)
            ansi_escape = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
            full_log = ansi_escape.sub("", full_log)

            # Filter out the sudo password prompt from logs if present
            clean_lines = [
                line
                for line in full_log.split("\n")
                if "[sudo] password for" not in line
            ]
            full_log = "\n".join(clean_lines).strip()

            if not full_log and exit_code != 0:
                return (
                    jsonify(
                        {
                            "error": (
                                "Failed to retrieve logs. Container "
                                "may not be running or does not exist."
                            )
                        }
                    ),
                    404,
                )

            return (
                jsonify({"container_name": container_name, "logs": full_log}),
                200,
            )
        except Exception as e:
            logging.error(f"Failed to get container logs: {e}", exc_info=True)
            return (
                jsonify({"error": "An unexpected error occurred retrieving logs."}),
                500,
            )

    @flask_app.route("/get-generated-files", methods=["POST"])
    def get_generated_files():
        """Retrieve list of generated files and their contents for UI preview."""
        try:
            data = request.get_json(force=True) or {}
            output_path_str = data.get("output_path")
            if not isinstance(output_path_str, str) or not output_path_str.strip():
                return jsonify({"error": "Missing or invalid output_path"}), 400

            clean_dir = secure_filename(os.path.basename(output_path_str.strip()))
            if not clean_dir:
                return jsonify({"error": "Invalid output directory"}), 400

            base_dir = get_app_data_dir().resolve()
            target_path = (base_dir / clean_dir).resolve()

            if not target_path.is_relative_to(base_dir):
                return jsonify({"error": "Unauthorized path access"}), 403

            if not target_path.exists() or not target_path.is_dir():
                return jsonify({"error": "Output directory does not exist"}), 404

            selected_components = data.get("selected_components", [])
            if not isinstance(selected_components, list):
                selected_components = []
            selected_components = [
                secure_filename(str(c)).lower() for c in selected_components if c
            ]

            # Recursively find and filter files
            files_dict = {}
            for file_path in target_path.rglob("*"):
                resolved_file = file_path.resolve()
                if not resolved_file.is_relative_to(target_path):
                    continue
                if resolved_file.is_file():
                    relative_path = resolved_file.relative_to(target_path)
                    parts = relative_path.parts

                    should_show = False
                    if len(parts) == 1:
                        # Root files (except internal deployment state)
                        if parts[0] != "deployment_state.json":
                            should_show = True
                    elif len(parts) > 1:
                        # Subdirectory files: only show if top-level dir
                        # is selected
                        first_dir = parts[0].lower()
                        if first_dir in selected_components:
                            should_show = True

                    if should_show:
                        rel_name = str(relative_path)
                        try:
                            with open(resolved_file, "r", encoding="utf-8") as f:
                                files_dict[rel_name] = f.read()
                        except (UnicodeDecodeError, IOError):
                            # Skip binary or unreadable files
                            continue

            return jsonify({"files": files_dict}), 200

        except Exception as e:
            logging.error(f"Failed to read generated files: {e}", exc_info=True)
            return (
                jsonify({"error": "An unexpected error occurred reading files."}),
                500,
            )

    @flask_app.route("/api/backup/discover-compose", methods=["POST"])
    def api_backup_discover_compose():
        """Scans target host filesystem for existing docker-compose stack files."""
        try:
            data = request.get_json(force=True) or {}
            ip = data.get("ip") or session.get("device_ip")
            username = data.get("username") or session.get("ssh_user", "root")
            password = data.get("password") or session.get("ssh_password", "")
            port = int(data.get("port") or session.get("ssh_port", 22))

            if not ip or not username:
                return (
                    jsonify({"error": "Missing IP or username for target host."}),
                    400,
                )

            ssh = SSHManager(
                hostname=ip,
                username=username,
                password=password,
                port=port,
                allow_auto_add=True,
            )
            success, msg = ssh.connect()
            if not success:
                return jsonify({"error": f"SSH connection failed: {msg}"}), 400

            backup_mgr = BackupManager()
            discovered = backup_mgr.discover_compose_files(ssh)
            ssh.close()
            suggested = discovered[0]["directory"] if discovered else None
            return (
                jsonify(
                    {
                        "status": "success",
                        "discovered_paths": discovered,
                        "suggested_path": suggested,
                    }
                ),
                200,
            )
        except Exception as e:
            logging.error(f"Discover compose failed: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to discover compose files."}),
                500,
            )

    @flask_app.route("/api/backup/inspect", methods=["POST"])
    def api_backup_inspect():
        """Inspects target machine for NjordDeploy volumes and storage usage."""
        try:
            data = request.get_json(force=True) or {}
            ip = data.get("ip") or session.get("device_ip")
            username = data.get("username") or session.get("ssh_user", "root")
            password = data.get("password") or session.get("ssh_password", "")
            port = int(data.get("port") or session.get("ssh_port", 22))
            project_config_dir = data.get("project_config_dir") or data.get("stack_dir")

            if not ip or not username:
                return (
                    jsonify({"error": "Missing IP or username for target host."}),
                    400,
                )

            ssh = SSHManager(
                hostname=ip,
                username=username,
                password=password,
                port=port,
                allow_auto_add=True,
            )
            success, msg = ssh.connect()
            if not success:
                return jsonify({"error": f"SSH connection failed: {msg}"}), 400

            backup_mgr = BackupManager()
            inspection = backup_mgr.inspect_target(
                ssh, project_config_dir=project_config_dir
            )
            ssh.close()
            status_code = 200 if inspection.get("status") == "success" else 404
            return jsonify(inspection), status_code
        except Exception as e:
            logging.error(f"Backup inspect failed: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to inspect target host."}),
                500,
            )

    @flask_app.route("/api/backup/create", methods=["POST"])
    def api_backup_create():
        """Generates a compressed backup tarball for NjordDeploy components."""
        try:
            data = request.get_json(force=True) or {}
            ip = data.get("ip") or session.get("device_ip")
            username = data.get("username") or session.get("ssh_user", "root")
            password = data.get("password") or session.get("ssh_password", "")
            port = int(data.get("port") or session.get("ssh_port", 22))
            project_config_dir = data.get("project_config_dir") or data.get("stack_dir")

            selected_components = data.get("selected_components")
            exclude_paths = data.get("exclude_paths", [])
            pause_containers = bool(data.get("pause_containers", False))

            if not ip or not username:
                return (
                    jsonify({"error": "Missing IP or username for target host."}),
                    400,
                )

            ssh = SSHManager(
                hostname=ip,
                username=username,
                password=password,
                port=port,
                allow_auto_add=True,
            )
            success, msg = ssh.connect()
            if not success:
                return jsonify({"error": f"SSH connection failed: {msg}"}), 400

            backup_mgr = BackupManager()
            res = backup_mgr.create_backup(
                ssh,
                selected_components=selected_components,
                exclude_paths=exclude_paths,
                pause_containers=pause_containers,
                project_config_dir=project_config_dir,
            )
            ssh.close()
            status_code = 200 if res.get("status") == "success" else 400
            return jsonify(res), status_code
        except Exception as e:
            logging.error(f"Backup create failed: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to create backup archive."}),
                500,
            )

    @flask_app.route("/api/backup/list", methods=["POST"])
    def api_backup_list():
        """Lists existing backups on the remote host."""
        try:
            data = request.get_json(force=True) or {}
            ip = data.get("ip") or session.get("device_ip")
            username = data.get("username") or session.get("ssh_user", "root")
            password = data.get("password") or session.get("ssh_password", "")
            port = int(data.get("port") or session.get("ssh_port", 22))
            project_config_dir = data.get("project_config_dir") or data.get("stack_dir")

            if not ip or not username:
                return (
                    jsonify({"error": "Missing IP or username for target host."}),
                    400,
                )

            ssh = SSHManager(
                hostname=ip,
                username=username,
                password=password,
                port=port,
                allow_auto_add=True,
            )
            success, msg = ssh.connect()
            if not success:
                return jsonify({"error": f"SSH connection failed: {msg}"}), 400

            backup_mgr = BackupManager()
            backups = backup_mgr.list_backups(
                ssh, project_config_dir=project_config_dir
            )
            ssh.close()
            return jsonify({"status": "success", "backups": backups}), 200
        except Exception as e:
            logging.error(f"Backup list failed: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to list backups."}),
                500,
            )

    @flask_app.route("/api/backup/restore", methods=["POST"])
    def api_backup_restore():
        """Restores services and volumes from a specific NjordDeploy backup."""
        try:
            data = request.get_json(force=True) or {}
            ip = data.get("ip") or session.get("device_ip")
            username = data.get("username") or session.get("ssh_user", "root")
            password = data.get("password") or session.get("ssh_password", "")
            port = int(data.get("port") or session.get("ssh_port", 22))
            project_config_dir = data.get("project_config_dir") or data.get("stack_dir")

            backup_filename = data.get("backup_filename")
            selected_components = data.get("selected_components")
            restart_after = bool(data.get("restart_after", True))

            if not ip or not username or not backup_filename:
                return (
                    jsonify(
                        {
                            "error": (
                                "Missing required fields: ip, username, "
                                "or backup_filename."
                            )
                        }
                    ),
                    400,
                )

            ssh = SSHManager(
                hostname=ip,
                username=username,
                password=password,
                port=port,
                allow_auto_add=True,
            )
            success, msg = ssh.connect()
            if not success:
                return jsonify({"error": f"SSH connection failed: {msg}"}), 400

            backup_mgr = BackupManager()
            res = backup_mgr.restore_backup(
                ssh,
                backup_filename=str(backup_filename),
                selected_components=selected_components,
                restart_after=restart_after,
                project_config_dir=project_config_dir,
            )
            ssh.close()
            status_code = 200 if res.get("status") == "success" else 400
            return jsonify(res), status_code
        except Exception as e:
            logging.error(f"Backup restore failed: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to restore backup."}),
                500,
            )

    @flask_app.route("/api/backup/download/<filename>", methods=["GET"])
    def api_backup_download(filename: str):
        """Downloads a backup archive from the remote host or local staging."""
        try:
            from werkzeug.utils import secure_filename

            clean_name = secure_filename(os.path.basename(filename.strip()))
            if not re.match(r"^njorddeploy_backup_[0-9_]+\.tar\.gz$", clean_name):
                return jsonify({"error": "Invalid backup filename."}), 400

            ip = request.args.get("ip") or session.get("device_ip")
            username = request.args.get("username") or session.get("ssh_user", "root")
            password = request.args.get("password") or session.get("ssh_password", "")
            port = int(request.args.get("port") or session.get("ssh_port", 22))
            project_config_dir = request.args.get(
                "project_config_dir"
            ) or request.args.get("stack_dir")

            staging_dir = get_app_data_dir().resolve() / "backups_download"
            staging_dir.mkdir(parents=True, exist_ok=True)
            local_target = (staging_dir / clean_name).resolve()

            if not local_target.is_relative_to(staging_dir):
                return jsonify({"error": "Unauthorized path access."}), 403

            if not local_target.exists():
                if not ip or not username:
                    return (
                        jsonify(
                            {
                                "error": (
                                    "Missing target host credentials to fetch "
                                    "remote archive."
                                )
                            }
                        ),
                        400,
                    )
                ssh = SSHManager(
                    hostname=ip,
                    username=username,
                    password=password,
                    port=port,
                    allow_auto_add=True,
                )
                success, msg = ssh.connect()
                if not success:
                    return jsonify({"error": f"SSH connection failed: {msg}"}), 400
                backup_mgr = BackupManager()
                dl_ok, dl_msg, local_file = backup_mgr.download_backup_sftp(
                    ssh,
                    clean_name,
                    staging_dir,
                    project_config_dir=project_config_dir,
                )
                ssh.close()
                if not dl_ok:
                    return (
                        jsonify({"error": f"Failed to download archive: {dl_msg}"}),
                        500,
                    )

            from flask import send_file

            return send_file(local_target, as_attachment=True, download_name=clean_name)
        except Exception as e:
            logging.error(f"Backup download failed: {e}", exc_info=True)
            return (
                jsonify({"error": "Failed to download backup."}),
                500,
            )

    return flask_app


if __name__ == "__main__":
    from waitress import serve

    app = create_app()
    port = int(os.environ.get("CONFIGURATOR_PORT", 5001))
    host = os.environ.get("CONFIGURATOR_HOST", "0.0.0.0")  # nosec B104
    serve(app, host=host, port=port, threads=6)
