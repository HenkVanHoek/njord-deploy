# src/utils/resource_utils.py
import sys
import tomllib
from pathlib import Path


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

    from appdirs import user_data_dir

    # 1. Check environment variable override
    env_dir = os.environ.get("PI_SELFHOSTING_COMPONENTS_DIR")
    if env_dir:
        components_dir = Path(env_dir).resolve()
        return (
            components_dir / "components_metadata.json",
            components_dir / "component_templates",
        )

    # 2. Check user data directory
    app_data_dir = Path(user_data_dir("NjordDeploy", "NjordDeploy"))
    user_components_dir = app_data_dir / "components"
    user_metadata = user_components_dir / "components_metadata.json"
    user_templates = user_components_dir / "component_templates"

    if user_metadata.exists() and user_templates.exists():
        return user_metadata, user_templates

    # 3. Fallback to built-in resources
    fallback_metadata = resource_path("config/components_metadata.json")
    fallback_templates = resource_path("component_templates")
    return fallback_metadata, fallback_templates
