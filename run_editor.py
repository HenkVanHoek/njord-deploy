# run_editor.py

"""
Development runner for the NjordDeploy Editor application.

This script provides a dedicated entry point for running the editor in
debug mode. It configures the Flask auto-reloader to watch for changes
in the core metadata and all component variable files, ensuring that
any data modification is immediately reflected in the running application
without requiring a manual restart.
"""

import os
from pathlib import Path

from src.editor_app.app import create_app


def find_files_to_watch():
    """
    Finds the main metadata file and all component-specific variables.json
    files to be monitored by the Flask reloader.
    """
    project_root = Path(__file__).parent
    config_path = project_root / "config"
    templates_path = project_root / "component_templates"

    # The primary metadata file
    files = [str(config_path / "components_metadata.json")]

    # All component-specific variables files
    variable_files = templates_path.glob("**/variables.json")
    files.extend([str(p) for p in variable_files])

    return files


if __name__ == "__main__":
    # Create an instance of the editor application using the factory
    editor_app = create_app()

    # Find all JSON data files that should trigger a reload on change
    extra_files_to_watch = find_files_to_watch()

    # Run the app dynamically based on environmental configuration
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")

    editor_app.run(
        debug=debug_mode,
        port=5001,  # Using 5001 to avoid conflicts with the main app
        extra_files=extra_files_to_watch,
    )
