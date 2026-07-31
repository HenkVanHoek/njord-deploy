import os
import sys
from typing import Generator

from dotenv import load_dotenv

from managers.artifact_generator import ArtifactGenerator
from managers.component_reader import ComponentReader

# Import verified utilities and managers
from utils.resource_utils import get_project_root, get_project_version


def run_installation() -> Generator[str, None, None]:
    """
    Orchestrates the installation process:
    1. Generates unified Docker Compose artifacts.
    2. Executes deployment via Ansible.
    """
    project_root = get_project_root()
    src_path = project_root / "src"

    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    import ansible_runner

    load_dotenv(dotenv_path=project_root / ".env")

    yield "--- NjordDeploy Installer ---"

    version = get_project_version()
    yield f"Project Version: {version}"

    # --- Initialize Managers ---
    reader = ComponentReader(
        metadata_path=project_root / "config" / "components_metadata.json",
        templates_path=project_root / "component_templates",
    )
    generator = ArtifactGenerator(reader)

    # --- Step 1: Load Selections ---
    selected_file = project_root / "selected_components.txt"
    if not selected_file.exists():
        yield f"ERROR: '{selected_file}' missing. Run the UI first."
        return

    selected_ids = selected_file.read_text().strip().split()
    if not selected_ids:
        yield "ERROR: No components selected."
        return

    # --- Step 2: Generate Artifacts ---
    yield "Generating unified deployment package..."

    deployment_vars = {}
    for cid in selected_ids:
        deployment_vars[cid] = {
            "PI_IP": os.getenv("PI_IP"),
            "DOMAIN": os.getenv("DOMAIN", "njorddeploy.com"),
        }

    output_path = project_root / "generated_deployments"

    # Call your existing create_artifacts method
    success = generator.create_artifacts(
        out_path=output_path, components=selected_ids, user_variables=deployment_vars
    )

    if not success:
        yield "FATAL ERROR: Could not create deployment artifacts."
        return

    yield "Deployment package generated successfully."
    yield "---------------------------------"

    # --- Step 3: Deployment ---
    pi_ip = os.getenv("PI_IP")
    ssh_user = os.getenv("SSH_USER")

    if not all([pi_ip, ssh_user]):
        yield "ERROR: Missing PI_IP or SSH_USER in .env."
        return

    inventory = {"hosts": {pi_ip: None}}
    playbook_path = project_root / "ansible" / "playbook.yml"

    yield f"Deploying to {ssh_user}@{pi_ip} via Ansible..."

    try:
        runner = ansible_runner.run(
            private_data_dir=str(project_root),
            playbook=str(playbook_path),
            inventory=inventory,
            extravars={"ansible_user": ssh_user, "project_version": version},
            quiet=True,
        )

        for event in runner.events:
            if event["event"] == "runner_on_ok":
                res = event["event_data"].get("res", {})
                if "stdout_lines" in res:
                    for line in res["stdout_lines"]:
                        yield line
            elif event["event"] in ["runner_on_failed", "runner_on_unreachable"]:
                task = event["event_data"].get("task", "Unknown Task")
                msg = event["event_data"].get("res", {}).get("msg", "No message")
                yield f"TASK FAILED [{task}]: {msg}"

        yield "---------------------------------"
        yield f"Installation finished with status: {runner.status}"

    except Exception as e:
        yield f"FATAL Error during Ansible run: {e}"
