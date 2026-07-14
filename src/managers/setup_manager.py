# src/managers/setup_manager.py
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List

from managers.component_reader import ComponentReader
from utils.resource_utils import resource_path

logger = logging.getLogger(__name__)


class SetupManager:
    """
    Handles the initial setup and directory structure for the self-hosting environment.
    Uses ComponentReader to validate component existence during setup tasks.
    """

    def __init__(self, component_manager: ComponentReader, output_dir: Path):
        """
        Initialize the SetupManager.
        """
        self.reader = component_manager
        self.output_dir = output_dir

    def initialize_environment(self) -> bool:
        """
        Creates the necessary base directories for the deployment.
        """
        try:
            if not self.output_dir.exists():
                self.output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created base directory at {self.output_dir}")

            # Create a sub-folder for logs
            log_dir = self.output_dir / "logs"
            log_dir.mkdir(exist_ok=True)

            return True
        except Exception as e:
            logger.error(f"Failed to initialize environment: {e}")
            return False

    def verify_component_setup(self, component_id: str) -> bool:
        """
        Checks if a component exists in the metadata before attempting setup.
        """
        details = self.reader.get_component_details(component_id)
        if not details:
            logger.warning(f"Component {component_id} not found in metadata.")
            return False

        logger.info(f"Verified component {component_id} for setup.")
        return True

    def get_setup_report(self) -> Dict[str, Any]:
        """
        Returns a summary of the current environment setup.
        """
        return {
            "base_path": str(self.output_dir),
            "status": "ready" if self.output_dir.exists() else "uninitialized",
            "components_available": len(self.reader.get_all_components()),
        }

    def prepare_deployment_package(
        self, selected_components: list, user_variables: dict, managed_devices: list
    ) -> tuple[bool, list]:
        """
        Prepares the deployment files by generating the .env file and copying templates.
        Returns a tuple of (success_boolean, list_of_errors).
        """
        errors: List[str] = []
        try:
            # Ensure the base directories exist
            self.initialize_environment()

            # 1. Write all user-provided variables (from the UI) to a hidden .env file
            env_path = self.output_dir / ".env"
            with open(env_path, "w") as f:
                for key, value in user_variables.items():
                    f.write(f"{key}={value}\n")
            logger.info(f"Generated .env file at {env_path}")

            # 2. Save a state file documenting the deployment configuration
            state_path = self.output_dir / "deployment_state.json"
            state_data = {"components": selected_components, "devices": managed_devices}
            with open(state_path, "w") as f:
                json.dump(state_data, f, indent=4)

            # 3. Copy the appropriate template directories
            # (containing docker-compose files) to the output directory
            if hasattr(self.reader, "templates_path"):
                base_template_path = Path(self.reader.templates_path)
                for comp_id in selected_components:
                    src_dir = base_template_path / comp_id
                    dst_dir = self.output_dir / comp_id

                    if src_dir.exists():
                        # If the directory already exists from a previous run,
                        # clear it first
                        if dst_dir.exists():
                            shutil.rmtree(dst_dir)
                        shutil.copytree(src_dir, dst_dir)
                        logger.info(f"Copied template for {comp_id} to {dst_dir}")

                        # Copy project docs if this is the docs component
                        if comp_id == "njorddeploy-docs":
                            src_docs_dir = dst_dir / "src-docs"
                            src_docs_dir.mkdir(parents=True, exist_ok=True)

                            readme_src = resource_path("README.md")
                            if readme_src.exists():
                                shutil.copy2(readme_src, src_docs_dir / "index.md")

                            contrib_src = resource_path("CONTRIBUTING.md")
                            if contrib_src.exists():
                                shutil.copy2(
                                    contrib_src, src_docs_dir / "contributing.md"
                                )

                            utils_src = resource_path("UTILITIES.md")
                            if utils_src.exists():
                                shutil.copy2(utils_src, src_docs_dir / "utilities.md")

                            docs_src = resource_path("docs")
                            if docs_src.exists():
                                dst_docs_dir = src_docs_dir / "docs"
                                if dst_docs_dir.exists():
                                    shutil.rmtree(dst_docs_dir)
                                shutil.copytree(docs_src, dst_docs_dir)
                            logger.info(
                                "Copied documentation files to "
                                "njorddeploy-docs context"
                            )
                    else:
                        logger.warning(
                            f"Template directory for {comp_id} not found at {src_dir}"
                        )

            return True, errors

        except Exception as e:
            logger.error(f"Failed to prepare deployment package: {e}", exc_info=True)
            errors.append(str(e))
            return False, errors
