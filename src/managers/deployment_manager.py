# src/managers/deployment_manager.py
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from appdirs import user_data_dir

from utils.resource_utils import resource_path

try:
    import ansible_runner
except ImportError:
    from unittest.mock import MagicMock

    ansible_runner = MagicMock()
    sys.modules["ansible_runner"] = ansible_runner

logger = logging.getLogger(__name__)


class DeploymentManager:
    """
    Orchestrates the deployment of components to target devices using Ansible.
    Uses the locally generated artifacts as the Single Source of Truth (SST).
    """

    def __init__(self, component_manager: Any):
        """
        Initialize the DeploymentManager.
        """
        self.reader = component_manager
        self.tasks: Dict[str, Any] = {}
        self._docker_prefix: str = "njorddeploy_"

    def start_deployment(
        self,
        task_id: str,
        tasks: Dict[str, Any],
        output_path: str,
        devices: List[Dict[str, Any]],
        components_to_clean: Optional[List[str]] = None,
        components_to_restart: Optional[List[str]] = None,
        selected_components_data: Optional[List[Dict[str, Any]]] = None,
        global_vars: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Executes the deployment by calling Ansible with the local artifact path.
        Now safely accepts additional configuration flags from the UI.
        """
        # Ensure default values if none are provided
        components_to_clean = components_to_clean or []
        components_to_restart = components_to_restart or []
        selected_components_data = selected_components_data or []
        global_vars = global_vars or {}

        runner: Any = None
        self.tasks[task_id] = tasks[task_id]
        self.tasks[task_id]["status"] = "running"

        # Base directory for Ansible execution (project root) resolved via resource path
        project_root = str(resource_path(""))
        playbook_path = str(resource_path("ansible/playbook.yml"))

        for device in devices:
            ip = device.get("ip", "unknown")
            ssh_user = device.get("username", os.getenv("SSH_USER", "admin"))
            ssh_password = device.get("password")

            self.tasks[task_id]["logs"].append(f"Deploying unified config to {ip}...")

            if components_to_clean:
                self.tasks[task_id]["logs"].append(
                    f"INFO: Scheduled for clean install: "
                    f"{', '.join(components_to_clean)}"
                )
            if components_to_restart:
                self.tasks[task_id]["logs"].append(
                    f"INFO: Scheduled for post-install restart: "
                    f"{', '.join(components_to_restart)}"
                )

            # noinspection PyBroadException
            try:
                # Map component IDs to actual docker service names for Ansible tasks
                mapped_clean = []
                for c_id in components_to_clean:
                    if hasattr(self.reader, "get_docker_service_name"):
                        svc_name = self.reader.get_docker_service_name(c_id)
                        if isinstance(svc_name, str):
                            mapped_clean.append(svc_name)
                        else:
                            mapped_clean.append(c_id)
                    else:
                        mapped_clean.append(c_id)

                mapped_restart = []
                for c_id in components_to_restart:
                    if hasattr(self.reader, "get_docker_service_name"):
                        svc_name = self.reader.get_docker_service_name(c_id)
                        if isinstance(svc_name, str):
                            mapped_restart.append(svc_name)
                        else:
                            mapped_restart.append(c_id)
                    else:
                        mapped_restart.append(c_id)

                # Prepare extravars for Ansible
                extravars = {
                    "ansible_user": ssh_user,
                    "local_output_path": output_path,
                    "components_to_clean": mapped_clean,
                    "components_to_restart": mapped_restart,
                    "selected_components_data": selected_components_data,
                    "global_vars": global_vars,
                }

                app_data_dir = Path(user_data_dir("NjordDeploy", "NjordDeploy"))
                key_file = app_data_dir / "id_ed25519_njorddeploy"
                if key_file.exists():
                    extravars["ansible_ssh_private_key_file"] = str(key_file)
                # Add password if we have it from the UI,
                # otherwise Ansible assumes SSH keys
                if ssh_password:
                    extravars["ansible_password"] = ssh_password
                    extravars["ansible_become_password"] = ssh_password

                # Prevent host key checking errors for dynamic test/reinstalled VMs
                extravars["ansible_ssh_common_args"] = (
                    "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
                )

                # Log deployment manifest and docker-compose.yml contents
                out_path_obj = Path(output_path)
                if out_path_obj.exists():
                    file_list = [
                        str(p.relative_to(out_path_obj))
                        for p in out_path_obj.rglob("*")
                        if p.is_file()
                    ]
                    self.tasks[task_id]["logs"].append(
                        f"MANIFEST: Transferring {len(file_list)} files to "
                        f"target /opt/njorddeploy: {', '.join(file_list)}"
                    )
                    compose_file = out_path_obj / "docker-compose.yml"
                    if compose_file.exists():
                        try:
                            compose_text = compose_file.read_text(encoding="utf-8")
                            self.tasks[task_id]["logs"].append(
                                "MANIFEST: Target docker-compose.yml contents:"
                            )
                            for line in compose_text.splitlines():
                                self.tasks[task_id]["logs"].append(f"  {line}")
                        except Exception as read_ex:
                            logger.warning(
                                f"Could not read compose file manifest: {read_ex}"
                            )

                processed_events: set[str] = set()

                def handle_single_event(evt: Dict[str, Any]) -> bool:
                    event_uuid = evt.get("uuid")
                    if not event_uuid:
                        event_uuid = str(len(processed_events))
                    if event_uuid in processed_events:
                        return True
                    processed_events.add(event_uuid)

                    event_name = evt.get("event")
                    event_data = evt.get("event_data", {})

                    if event_name == "runner_on_ok":
                        task_name = event_data.get("task", "Unknown Task")
                        self.tasks[task_id]["logs"].append(f"OK: {task_name}")

                        # Catch warnings embedded in the task result
                        res = event_data.get("res", {})
                        if isinstance(res, dict):
                            stdout_val = res.get("stdout")
                            if isinstance(stdout_val, str) and stdout_val.strip():
                                for line in stdout_val.strip().splitlines():
                                    self.tasks[task_id]["logs"].append(
                                        f"STDOUT [{task_name}]: {line}"
                                    )
                            if (
                                "msg" in res
                                and str(res["msg"]).strip()
                                # Filter out generic/expected non-error indicators
                                and str(res["msg"]) != "All items completed"
                                and "HTTP Error 304" not in str(res["msg"])
                                and "non-zero return code" not in str(res["msg"])
                            ):
                                self.tasks[task_id]["logs"].append(
                                    f"DEBUG: {res['msg']}"
                                )
                            for warning_msg in res.get("warnings", []):
                                self.tasks[task_id]["logs"].append(
                                    f"WARN: [{task_name}] {warning_msg}"
                                )

                    elif event_name == "runner_on_item_ok":
                        res = event_data.get("res", {})
                        if isinstance(res, dict):
                            if (
                                "msg" in res
                                and str(res["msg"]).strip()
                                and "HTTP Error 304" not in str(res["msg"])
                                and "non-zero return code" not in str(res["msg"])
                            ):
                                self.tasks[task_id]["logs"].append(
                                    f"DEBUG: {res['msg']}"
                                )

                    elif event_name in [
                        "runner_on_failed",
                        "runner_on_unreachable",
                        "runner_on_item_failed",
                    ]:
                        res = event_data.get("res", {})
                        err_msg = res.get("msg", "Unknown error")
                        self.tasks[task_id]["logs"].append(f"FAILED: {err_msg}")

                        # Catch detailed shell outputs or tracebacks
                        if isinstance(res, dict):
                            stderr = res.get("stderr")
                            if stderr:
                                self.tasks[task_id]["logs"].append(
                                    f"FAILED_STDERR: {stderr}"
                                )

                            module_stderr = res.get("module_stderr")
                            if module_stderr:
                                self.tasks[task_id]["logs"].append(
                                    f"MODULE_STDERR: {module_stderr}"
                                )

                            results = res.get("results")
                            if isinstance(results, list):
                                for r in results:
                                    if isinstance(r, dict) and r.get("failed", False):
                                        sub_msg = (
                                            r.get("msg")
                                            or r.get("stderr")
                                            or "Sub-task failed"
                                        )
                                        self.tasks[task_id]["logs"].append(
                                            f"SUB_FAILED: {sub_msg}"
                                        )

                        if "errors" not in self.tasks[task_id]:
                            self.tasks[task_id]["errors"] = []

                        task_name = event_data.get("task", "Unknown Task")
                        event_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # Gather detailed reasons for failure
                        details_list = [err_msg]
                        if isinstance(res, dict):
                            stderr_val = res.get("stderr")
                            if stderr_val:
                                details_list.append(f"stderr: {stderr_val}")

                            m_stderr = res.get("module_stderr")
                            if m_stderr:
                                details_list.append(f"module_stderr: {m_stderr}")

                            results_val = res.get("results")
                            if isinstance(results_val, list):
                                for r in results_val:
                                    if isinstance(r, dict) and r.get("failed", False):
                                        sub_m = (
                                            r.get("msg")
                                            or r.get("stderr")
                                            or "Sub-task failed"
                                        )
                                        details_list.append(f"sub_failed: {sub_m}")

                        details_str = " | ".join(details_list)

                        # Try to identify related component
                        component_id = "N/A"
                        if selected_components_data:
                            for comp in selected_components_data:
                                comp_id = comp.get("id", "")
                                if comp_id and (
                                    comp_id in task_name
                                    or comp_id.lower() in task_name.lower()
                                ):
                                    component_id = comp_id
                                    break

                        err_type = (
                            f"Ansible:{event_name.replace('runner_on_', '').upper()}"
                        )
                        self.tasks[task_id]["errors"].append(
                            {
                                "type": err_type,
                                "summary": f"Ansible task failed: {task_name}",
                                "details": details_str,
                                "component_id": component_id,
                                "timestamp": event_ts,
                            }
                        )

                    # Catch standalone global warnings
                    elif event_name == "warning":
                        warn_msg = event_data.get("warning", "")
                        if warn_msg:
                            self.tasks[task_id]["logs"].append(f"WARN: {warn_msg}")
                    return True

                # Execute Ansible and pass the local path and new flags as variables
                try:

                    Path(project_root, "artifacts").mkdir(parents=True, exist_ok=True)

                    runner = ansible_runner.run(
                        private_data_dir=project_root,
                        playbook=playbook_path,
                        inventory={"all": {"hosts": {ip: {}}}},
                        extravars=extravars,
                        quiet=False,
                        event_handler=handle_single_event,
                    )

                    if hasattr(runner, "events") and runner.events:
                        for event in runner.events:
                            handle_single_event(event)

                    if runner.status == "successful":
                        self.tasks[task_id]["logs"].append(
                            f"SUCCESS: Node {ip} deployed successfully."
                        )
                    else:
                        self.tasks[task_id]["status"] = "failed"
                        self.tasks[task_id]["logs"].append(
                            f"ERROR: Deployment to {ip} did not complete successfully."
                        )

                        # Extract raw Ansible/runner stdout console to
                        # capture global crashes
                        # like Out of Memory (OOM) or syntax/process compilation issues.
                        if hasattr(runner, "stdout") and runner.stdout:
                            # noinspection PyBroadException
                            try:
                                runner.stdout.seek(0)
                                stdout_content = runner.stdout.read()
                                if stdout_content:
                                    self.tasks[task_id]["logs"].append(
                                        "--- GLOBAL ANSIBLE CONSOLE OUTPUT ---"
                                    )
                                    # Grab the last few lines of the raw process stdout
                                    raw_lines = stdout_content.splitlines()
                                    last_lines = (
                                        raw_lines[-20:]
                                        if len(raw_lines) > 20
                                        else raw_lines
                                    )
                                    for line in last_lines:
                                        clean_line = line.strip()
                                        if clean_line:
                                            self.tasks[task_id]["logs"].append(
                                                f"CONSOLE: {clean_line}"
                                            )
                            except Exception as read_err:
                                logger.error(
                                    f"Failed to read runner stdout: {read_err}"
                                )
                finally:
                    # Cleanup sensitive/temporary Ansible files from disk
                    p_root = Path(project_root)
                    extravars_file = p_root / "env" / "extravars"
                    hosts_file = p_root / "inventory" / "hosts.json"
                    artifacts_dir = p_root / "artifacts"

                    if extravars_file.exists():
                        # noinspection PyBroadException
                        try:
                            extravars_file.unlink()
                        except Exception as ex_vars:
                            logger.error(f"Failed to delete extravars: {ex_vars}")

                    if hosts_file.exists():
                        # noinspection PyBroadException
                        try:
                            hosts_file.unlink()
                        except Exception as ex_hosts:
                            logger.error(f"Failed to delete hosts: {ex_hosts}")

                    if runner:
                        config = getattr(runner, "config", None)
                        artifact_dir_path = getattr(config, "artifact_dir", None)
                        if isinstance(artifact_dir_path, str):
                            specific_artifact_dir = Path(artifact_dir_path)
                            if specific_artifact_dir.exists():
                                # noinspection PyBroadException
                                try:
                                    shutil.rmtree(specific_artifact_dir)
                                except Exception as ex_rm:
                                    logger.error(
                                        "Failed to delete specific artifacts: "
                                        f"{ex_rm}"
                                    )

                    if artifacts_dir.exists():
                        # noinspection PyBroadException
                        try:
                            # Only delete root artifacts directory if it is empty
                            if not any(artifacts_dir.iterdir()):
                                artifacts_dir.rmdir()
                        except Exception:  # nosec B110
                            pass

            except Exception as e:
                logger.error(f"Ansible execution error: {e}")
                self.tasks[task_id]["logs"].append(f"FATAL: {str(e)}")
                self.tasks[task_id]["status"] = "failed"

        if self.tasks[task_id]["status"] != "failed":
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["logs"].append(
                "--- Global deployment sequence finished successfully ---"
            )
        else:
            if "errors" not in self.tasks[task_id]:
                self.tasks[task_id]["errors"] = []
            if not any(
                err.get("type", "").startswith("Ansible:")
                for err in self.tasks[task_id]["errors"]
            ):
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.tasks[task_id]["errors"].append(
                    {
                        "type": "Ansible:Deployment:Failure",
                        "summary": "Deployment failed",
                        "details": (
                            "The deployment sequence failed. See the console logs "
                            "for detailed execution output."
                        ),
                        "component_id": "N/A",
                        "timestamp": timestamp_str,
                    }
                )

        # Update the final status in the shared dictionary so the UI polling sees it
        tasks[task_id] = self.tasks[task_id]
