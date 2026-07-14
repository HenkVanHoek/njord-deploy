# scripts/proxmox_test_runner.py
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import requests  # type: ignore
from dotenv import load_dotenv

# Ensure we can import from the 'src' root directory
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.component_manager import ComponentManager  # noqa: E402
from managers.deployment_manager import DeploymentManager  # noqa: E402
from managers.setup_manager import SetupManager  # noqa: E402
from managers.ssh_manager import SSHManager  # noqa: E402
from utils.proxmox_client import ProxmoxClient  # noqa: E402 # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("proxmox_test_runner")


def setup_proxmox_client() -> ProxmoxClient:
    """Initializes ProxmoxClient from environment variables."""
    host = os.getenv("PROXMOX_HOST", "https://192.168.178.51:8006")
    user = os.getenv("PROXMOX_USER", "root@pam")
    token_id = os.getenv("PROXMOX_TOKEN_ID", "")
    token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")

    if not token_id or not token_secret:
        logger.error("PROXMOX_TOKEN_ID or PROXMOX_TOKEN_SECRET not configured.")
        print(
            "ERROR: Proxmox API Token credentials must be set in your .env file.\n"
            "Required keys:\n"
            "  PROXMOX_HOST=https://192.168.178.51:8006\n"
            "  PROXMOX_USER=root@pam\n"
            "  PROXMOX_TOKEN_ID=<token-id>\n"
            "  PROXMOX_TOKEN_SECRET=<token-secret>\n"
        )
        sys.exit(1)

    return ProxmoxClient(
        host=host,
        user=user,
        token_id=token_id,
        token_secret=token_secret,
        verify_ssl=False,
    )


def wait_for_ip(
    client: ProxmoxClient, node: str, vmid: int, timeout_seconds: int = 120
) -> str | None:
    """Polls the guest agent until it retrieves a valid IP address."""
    logger.info(f"Waiting for VM {vmid} to boot and retrieve dynamic IP...")
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        ip = client.get_vm_ip(node, vmid)
        if ip:
            logger.info(f"VM {vmid} is online with IP: {ip}")
            return ip
        time.sleep(5)
    logger.error(f"Timed out waiting for VM {vmid} IP address.")
    return None


def verify_service_health(
    vm_ip: str,
    vm_user: str,
    vm_pass: str,
    component_id: str,
    component_details: Dict[str, Any],
    variables_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Runs SSH-based checks and optional HTTP requests to verify health."""
    results: Dict[str, Any] = {
        "running": False,
        "http_ok": None,
        "details": "",
        "logs_error": False,
    }

    # Initialize SSHManager to run checks
    ssh_mgr = SSHManager(hostname=vm_ip, username=vm_user, password=vm_pass)
    connected, conn_msg = ssh_mgr.connect()
    if not connected:
        results["details"] = f"SSH verification failed: {conn_msg}"
        return results

    try:
        # Check container status
        log_lines: List[str] = []

        def append_log(msg: str):
            log_lines.append(msg)

        # List containers running in the compose project
        cmd_docker_ps = (
            "docker ps --filter "
            "label=com.docker.compose.project=njorddeploy "
            "--format '{{.Names}} ({{.Status}})'"
        )
        exit_code, output = ssh_mgr.execute_command(
            cmd_docker_ps,
            append_log,
            check_exit_code=False,
        )

        if exit_code == 0 and output:
            results["running"] = True
            results["details"] = f"Running containers:\n{output}"
        else:
            results["details"] = (
                f"No running containers found " f"(exit code: {exit_code})."
            )

        # Check docker logs for tracebacks or fatal errors
        # Find matching container name
        container_list = [line.split()[0] for line in output.splitlines() if line]
        matched_container = next(iter(container_list), None)

        if matched_container:
            ssh_mgr.execute_command(
                f"docker logs {matched_container} --tail 100",
                append_log,
                check_exit_code=False,
            )
            logs_content = "\n".join(log_lines).lower()
            if "traceback" in logs_content or "fatal" in logs_content:
                results["logs_error"] = True

        # Check UI access if applicable
        if component_details.get("has_ui", False):
            ui_var = component_details.get("ui_port_variable")
            port = None
            if ui_var:
                for var in variables_list:
                    if var.get("name") == ui_var:
                        port = var.get("default")
                        break
            # Fallback to standard port if not in vars
            if not port:
                port = component_details.get("traefik_internal_port")

            if port:
                protocol = component_details.get("protocol", "http")
                url = f"{protocol}://{vm_ip}:{port}"
                logger.info(f"Probing HTTP UI endpoint: {url}")
                try:
                    res = requests.get(url, timeout=10)
                    results["http_ok"] = res.status_code in [200, 301, 302, 401]
                    results["details"] += f"\nHTTP Probe: {res.status_code} ({url})"
                except Exception as ex:
                    results["http_ok"] = False
                    results["details"] += f"\nHTTP Probe failed: {ex} ({url})"

    finally:
        ssh_mgr.close()

    return results


def run_proxmox_tests(args) -> int:
    """Orchestrates cloning, deploying, verifying, and tearing down VMs."""
    load_dotenv()
    proxmox_client = setup_proxmox_client()

    node = args.node or os.getenv("PROXMOX_NODE", "pve")
    template_id = int(args.template_id or os.getenv("PROXMOX_TEMPLATE_ID", "900"))
    vm_user = os.getenv("PROXMOX_VM_USER", "hvhoek")
    vm_pass = os.getenv("PROXMOX_VM_PASSWORD", "testpass")

    # Load local directories and config
    metadata_path = project_root / "config" / "components_metadata.json"
    templates_path = project_root / "component_templates"

    comp_mgr = ComponentManager(
        metadata_file_path=str(metadata_path), templates_path=str(templates_path)
    )
    setup_output_dir = project_root / "tmp_proxmox_test"

    # Get target components list
    all_components = comp_mgr.get_all_components()
    target_components = []

    if args.components:
        selected_ids = [c.strip() for c in args.components.split(",")]
        for comp in all_components:
            if comp.get("id") in selected_ids:
                target_components.append(comp)
    else:
        target_components = all_components

    # Filter out excluded components
    if args.exclude:
        excluded_ids = [c.strip() for c in args.exclude.split(",")]
        target_components = [
            c for c in target_components if c.get("id") not in excluded_ids
        ]

    if not target_components:
        logger.info("No components matching criteria to test.")
        return 0

    logger.info(f"Starting test run for {len(target_components)} components...")
    results_summary = []
    failed_count = 0

    # Ensure a local SSH key is generated to copy to the VMs
    dummy_mgr = SSHManager(
        hostname="localhost", username="test", password="key"
    )  # nosec B106
    ssh_key_obj = dummy_mgr._get_or_create_key()
    ssh_public_key = f"{ssh_key_obj.get_name()} {ssh_key_obj.get_base64()}"

    for comp in target_components:
        comp_id = comp.get("id", "unknown")
        logger.info("----------------------------------------")
        logger.info(f"Testing component: {comp_id}")
        logger.info("----------------------------------------")

        test_record = {
            "component_id": comp_id,
            "status": "failed",
            "vmid": None,
            "ip": None,
            "deployment": "failed",
            "running": False,
            "http_ok": None,
            "error_logs": False,
            "error_message": "",
        }

        new_vmid = None
        try:
            # 1. Clone VM
            new_vmid = proxmox_client.get_next_vmid()
            test_record["vmid"] = new_vmid
            logger.info(f"Cloning master template VMID {template_id} to {new_vmid}...")
            proxmox_client.clone_vm(
                node=node,
                vmid=template_id,
                newid=new_vmid,
                name=f"pish-test-{comp_id}",
                full=False,  # Linked clone
            )

            # 2. Configure Cloud-Init (injecting our local SSH Key)
            logger.info(f"Configuring Cloud-Init for VMID {new_vmid}...")
            proxmox_client.configure_vm(
                node=node,
                vmid=new_vmid,
                config_data={
                    "ciuser": vm_user,
                    "cipassword": vm_pass,
                    "sshkeys": ssh_public_key,
                    "ipconfig0": "ip=dhcp",
                },
            )

            # 3. Start VM
            logger.info(f"Starting VMID {new_vmid}...")
            proxmox_client.start_vm(node=node, vmid=new_vmid)

            # 4. Wait for dynamic IP
            vm_ip = wait_for_ip(proxmox_client, node, new_vmid)
            if not vm_ip:
                raise TimeoutError("Unable to retrieve IP address for cloned VM.")
            test_record["ip"] = vm_ip

            # Give cloud-init and network services a few seconds to settle
            time.sleep(10)

            # 5. Build configuration package locally
            logger.info(f"Generating deployment configurations for {comp_id}...")
            comp_output_dir = setup_output_dir / str(new_vmid)
            setup_mgr = SetupManager(
                component_manager=comp_mgr, output_dir=comp_output_dir
            )
            setup_mgr.initialize_environment()

            # Ensure we fetch appropriate variables
            variables_list = comp_mgr.reader.get_component_variables(comp_id)
            user_vars = {}
            for var in variables_list:
                user_vars[var.get("name")] = var.get("default")

            # Inject target IP
            user_vars["PISelfhosting_HOST_IP"] = vm_ip

            success, errors = setup_mgr.prepare_deployment_package(
                selected_components=[comp_id],
                user_variables=user_vars,
                managed_devices=[{"ip": vm_ip}],
            )
            if not success:
                errors_summary = ", ".join([err.get("summary") for err in errors])
                raise RuntimeError(f"Configuration packaging failed: {errors_summary}")

            # Generate artifacts
            comp_mgr.generate_deployment_artifacts(
                selected_components_data=[comp],
                global_vars=user_vars,
                output_path=comp_output_dir,
            )

            # 6. Deploy via DeploymentManager (Ansible)
            logger.info(f"Executing Ansible deployment to {vm_ip}...")
            deploy_mgr = DeploymentManager(component_manager=comp_mgr)
            task_id = f"test-{comp_id}-{new_vmid}"
            tasks_dict = {task_id: {"logs": [], "status": "pending"}}

            deploy_mgr.start_deployment(
                task_id=task_id,
                tasks=tasks_dict,
                output_path=str(comp_output_dir),
                devices=[{"ip": vm_ip, "username": vm_user, "password": vm_pass}],
                selected_components_data=[comp],
                global_vars=user_vars,
            )

            # Check deployment outcome
            task_outcome: Dict[str, Any] = tasks_dict.get(task_id, {})
            if task_outcome.get("status") == "completed":
                test_record["deployment"] = "success"
                logger.info("Ansible deployment completed successfully.")
            else:
                test_record["deployment"] = "failed"
                errors_list: List[Dict[str, Any]] = task_outcome.get("errors", [])
                first_error: Dict[str, Any] = next(iter(errors_list), {})
                err_details = first_error.get("details", "Ansible execution error")
                raise RuntimeError(f"Deployment failed: {err_details}")

            # 7. Run Health Verification Probe
            logger.info("Running service health verification probe...")
            health = verify_service_health(
                vm_ip=vm_ip,
                vm_user=vm_user,
                vm_pass=vm_pass,
                component_id=comp_id,
                component_details=comp,
                variables_list=variables_list,
            )

            test_record["running"] = health["running"]
            test_record["http_ok"] = health["http_ok"]
            test_record["error_logs"] = health["logs_error"]

            if health["running"] and (
                health["http_ok"] is None or health["http_ok"] is True
            ):
                test_record["status"] = "success"
                logger.info(f"✅ Component {comp_id} verified successfully!")
            else:
                test_record["status"] = "failed"
                test_record["error_message"] = health["details"]
                logger.error(
                    f"❌ Component {comp_id} verification failed: {health['details']}"
                )
                failed_count += 1

        except Exception as ex:
            logger.error(f"❌ Error during test of {comp_id}: {ex}")
            test_record["status"] = "failed"
            test_record["error_message"] = str(ex)
            failed_count += 1
        finally:
            # 8. Teardown (Stop and destroy the test VM)
            if new_vmid:
                logger.info(f"Stopping and destroying test VMID {new_vmid}...")
                try:
                    proxmox_client.stop_vm(node, new_vmid)
                    time.sleep(5)  # Let it shutdown
                    proxmox_client.destroy_vm(node, new_vmid)
                    logger.info(f"VMID {new_vmid} destroyed.")
                except Exception as ex:
                    logger.error(f"Failed to destroy VMID {new_vmid}: {ex}")

            # Cleanup local folder
            if new_vmid:
                comp_output_dir = setup_output_dir / str(new_vmid)
                if comp_output_dir.exists():
                    import shutil

                    shutil.rmtree(comp_output_dir)

        results_summary.append(test_record)

    # Ensure output dirs exist
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)
    tests_dir = project_root / "tests"
    tests_dir.mkdir(exist_ok=True)

    # Save JSON results
    json_path = tests_dir / "proxmox_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=4)
    logger.info(f"Saved raw test results to: {json_path}")

    # Generate Markdown Report
    report_path = docs_dir / "PROXMOX_TESTS.md"
    write_markdown_report(report_path, results_summary, failed_count)
    logger.info(f"Saved human-readable markdown report to: {report_path}")

    return failed_count


def write_markdown_report(
    report_path: Path, results: List[Dict[str, Any]], failed_count: int
):
    """Writes a clean, formatted Markdown report of the test outcomes."""
    total_count = len(results)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    md_lines = [
        "# Proxmox Automated Component Testing Report",
        "",
        f"**Run Timestamp:** {timestamp}",
        (
            f"**Total Tested:** {total_count} | "
            f"**Passed:** {total_count - failed_count} | "
            f"**Failed:** {failed_count}"
        ),
        "",
        "## Results Table",
        "",
        (
            "| Component ID | VM ID | IP Address | "
            "Deployment | Containers | HTTP | Status |"
        ),
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for record in results:
        status_emoji = "✅ PASS" if record["status"] == "success" else "❌ FAIL"
        http_val = (
            "N/A"
            if record["http_ok"] is None
            else ("OK" if record["http_ok"] else "FAIL")
        )
        md_lines.append(
            f"| `{record['component_id']}` | {record['vmid']} | "
            f"{record['ip'] or 'N/A'} | {record['deployment']} | "
            f"{'Running' if record['running'] else 'Stopped'} | "
            f"{http_val} | **{status_emoji}** |"
        )

    md_lines.append("")
    md_lines.append("## Details & Failures")
    md_lines.append("")

    has_failures = False
    for record in results:
        if record["status"] != "success":
            has_failures = True
            md_lines.append(f"### Component: `{record['component_id']}`")
            md_lines.append(f"- **VMID:** {record['vmid']}")
            md_lines.append(f"- **IP:** {record['ip'] or 'N/A'}")
            md_lines.append(f"- **Deployment Outcome:** {record['deployment']}")
            md_lines.append("- **Error / Logs:**")
            md_lines.append("```")
            md_lines.append(record["error_message"] or "Unknown error")
            md_lines.append("```")
            md_lines.append("")

    if not has_failures:
        md_lines.append(
            "All components completed execution and " "verification successfully!"
        )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Run automated integration tests for "
            "NjordDeploy components on Proxmox VE."
        )
    )
    parser.add_argument(
        "--components",
        type=str,
        help="Comma-separated list of component IDs to test. Defaults to all.",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Comma-separated list of component IDs to exclude from test run.",
    )
    parser.add_argument(
        "--template-id", type=str, help="VMID of the master template to clone."
    )
    parser.add_argument("--node", type=str, help="Proxmox node name.")
    args = parser.parse_args()

    exit_code = run_proxmox_tests(args)
    sys.exit(0 if exit_code == 0 else 1)
