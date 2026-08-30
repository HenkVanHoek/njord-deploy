import logging
import sys
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)

_LAST_SEED_STATUS: dict[str, str] = {
    "status": "already_seeded",
    "message": "",
}


def get_last_seed_status() -> dict[str, str]:
    """Returns the status dictionary from the last auto-seeding attempt."""
    return dict(_LAST_SEED_STATUS)


def get_app_data_dir() -> Path:
    """
    Returns the application data directory.
    Respects NJORD_DATA_DIR environment variable if provided,
    falling back to user_data_dir("NjordDeploy", "NjordDeploy").
    """
    import os

    from appdirs import user_data_dir

    custom_dir = os.environ.get("NJORD_DATA_DIR")
    if custom_dir:
        return Path(custom_dir).resolve()
    return Path(user_data_dir("NjordDeploy", "NjordDeploy"))


def get_ssh_key_path() -> Path:
    """
    Returns the path to the SSH private key used by NjordDeploy.
    Respects NJORD_SSH_KEY_PATH if set, else defaults to id_ed25519_njorddeploy
    in the application data directory.
    """
    import os

    custom_key = os.environ.get("NJORD_SSH_KEY_PATH")
    if custom_key:
        return Path(custom_key).resolve()
    return get_app_data_dir() / "id_ed25519_njorddeploy"


def is_server_mode() -> bool:
    """Returns True if NjordDeploy is configured to run in 24/7 server mode."""
    import os

    return os.environ.get("NJORD_SERVER_MODE", "").lower() in (
        "true",
        "1",
        "yes",
        "service",
        "daemon",
    )


def seed_user_components_if_needed() -> dict[str, str]:
    """
    Ensures local user data components directory is seeded with the latest
    component templates and metadata from GitHub if not already present.
    """
    global _LAST_SEED_STATUS
    import os
    import shutil

    if os.environ.get("PI_SELFHOSTING_COMPONENTS_DIR"):
        _LAST_SEED_STATUS = {
            "status": "already_seeded",
            "message": "Using environment variable components path.",
        }
        return _LAST_SEED_STATUS

    app_data_dir = get_app_data_dir()
    user_components_dir = app_data_dir / "components"
    user_metadata = user_components_dir / "components_metadata.json"
    user_templates = user_components_dir / "component_templates"

    # noinspection PyBroadException
    try:
        has_templates = user_templates.exists() and any(user_templates.iterdir())
    except Exception:
        has_templates = False

    # In development mode, auto-sync repository changes to user data dir
    if not getattr(sys, "frozen", False) and "pytest" not in sys.modules:
        fallback_meta = resource_path("config/components_metadata.json")
        fallback_temp = resource_path("component_templates")
        if fallback_meta.exists():
            try:
                user_components_dir.mkdir(parents=True, exist_ok=True)
                if (
                    not user_metadata.exists()
                    or fallback_meta.stat().st_mtime > user_metadata.stat().st_mtime
                ):
                    shutil.copy2(fallback_meta, user_metadata)
                if fallback_temp.exists():
                    user_templates.mkdir(parents=True, exist_ok=True)
                    for item in fallback_temp.iterdir():
                        dest_item = user_templates / item.name
                        if item.is_dir():
                            if not dest_item.exists():
                                shutil.copytree(item, dest_item)
                            elif item.stat().st_mtime > dest_item.stat().st_mtime:
                                shutil.rmtree(dest_item)
                                shutil.copytree(item, dest_item)
                        elif item.is_file():
                            shutil.copy2(item, dest_item)
            except Exception as ex:
                logger.debug(f"Dev auto-sync to user_components_dir: {ex}")

    if user_metadata.exists() and has_templates:
        _LAST_SEED_STATUS = {
            "status": "already_seeded",
            "message": "Components already initialized.",
        }
        return _LAST_SEED_STATUS

    # If running inside pytest unit test suite, skip network download and seed fallback
    if "pytest" in sys.modules:
        user_components_dir.mkdir(parents=True, exist_ok=True)
        fallback_meta = resource_path("config/components_metadata.json")
        fallback_temp = resource_path("component_templates")
        if fallback_meta.exists() and not user_metadata.exists():
            shutil.copy2(fallback_meta, user_metadata)
        if fallback_temp.exists() and not user_templates.exists():
            shutil.copytree(fallback_temp, user_templates)
        _LAST_SEED_STATUS = {
            "status": "already_seeded",
            "message": "Test mode fallback seeded.",
        }
        return _LAST_SEED_STATUS

    # Attempt to fetch latest packages from remote repo
    # noinspection PyBroadException
    try:
        from managers.sync_manager import SyncManager

        user_components_dir.mkdir(parents=True, exist_ok=True)
        sync = SyncManager(
            local_metadata_path=user_metadata,
            local_templates_path=user_templates,
        )
        if not sync.is_remote_sync_enabled():
            logger.info("Remote sync is disabled. Seeding local built-in components.")
        elif sync.fetch_from_remote() and sync.sync_all():
            _LAST_SEED_STATUS = {
                "status": "downloaded",
                "message": (
                    "De nieuwste componentpakketten en templates zijn "
                    "automatisch gedownload van de repository."
                ),
            }
            return _LAST_SEED_STATUS
    except Exception as e:
        logger.warning(f"Auto-fetch remote components failed: {e}")

    # Fallback to built-in resources if download fails or offline
    # noinspection PyBroadException
    try:
        user_components_dir.mkdir(parents=True, exist_ok=True)
        fallback_meta = resource_path("config/components_metadata.json")
        fallback_temp = resource_path("component_templates")

        if fallback_meta.exists() and not user_metadata.exists():
            shutil.copy2(fallback_meta, user_metadata)

        if fallback_temp.exists() and not user_templates.exists():
            shutil.copytree(fallback_temp, user_templates)
    except Exception as e:
        logger.error(f"Failed to copy fallback components to user directory: {e}")

    _LAST_SEED_STATUS = {
        "status": "fallback",
        "message": (
            "Kon geen verbinding maken met GitHub om de nieuwste "
            "pakketten te downloaden. Er is een actieve internetverbinding "
            "nodig om pakket-updates op te halen. "
            "Ingebouwde componentpakketten zijn geïnstalleerd als fallback."
        ),
    }
    return _LAST_SEED_STATUS


def resource_path(relative_path: str = "") -> Path:
    """
    Get absolute path to a resource, works for dev and for PyInstaller.
    Uses getattr to prevent PyCharm from flagging sys._MEIPASS as unresolved.
    """
    base_path_str: str | None = getattr(sys, "_MEIPASS", None)

    if base_path_str is None:
        # Development path: three levels up from src/utils/resource_utils.py
        # to the project root
        base_path = Path(__file__).resolve().parent.parent.parent
    else:
        base_path = Path(base_path_str)

    return base_path / relative_path


def get_project_root() -> Path:
    """Returns the project root directory as a Path object."""
    return Path(resource_path("")).resolve()


def get_project_version() -> str:
    """Reads the project version from pyproject.toml at the project root."""
    project_root = get_project_root()
    pyproject_path = project_root / "pyproject.toml"
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return str(data["project"]["version"])
    except (FileNotFoundError, KeyError, PermissionError):
        # Fallback to ensure the application continues even if the file is missing
        return "latest"


def get_global_template_context():
    """
    Provides the required context variables for the base Jinja templates
    to access global macros and placeholder values.
    """
    return {
        "DOTENV": {},
        "CONFIG_BASE_PATH": "/default/path",
    }


def get_components_paths() -> tuple[Path, Path]:
    """
    Get the paths for components_metadata.json and component_templates.
    Supports development overrides via environment variable,
    user data directory for downloaded templates, and fallback to built-in resources.
    """
    import os

    # 1. Check environment variable override
    env_dir = os.environ.get("NJORD_COMPONENTS_DIR") or os.environ.get(
        "PI_SELFHOSTING_COMPONENTS_DIR"
    )
    if env_dir:
        components_dir = Path(env_dir).resolve()
        return (
            components_dir / "components_metadata.json",
            components_dir / "component_templates",
        )

    # 2. Check user data directory
    app_data_dir = get_app_data_dir()
    user_components_dir = app_data_dir / "components"
    user_metadata = user_components_dir / "components_metadata.json"
    user_templates = user_components_dir / "component_templates"

    # noinspection PyBroadException
    try:
        has_templates = user_templates.exists() and any(user_templates.iterdir())
    except Exception:
        has_templates = False

    if user_metadata.exists() and has_templates:
        return user_metadata, user_templates

    # 3. Fallback to built-in resources
    fallback_metadata = resource_path("config/components_metadata.json")
    fallback_templates = resource_path("component_templates")
    return fallback_metadata, fallback_templates
