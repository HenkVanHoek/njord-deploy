# src/cli/runner.py
"""Headless CLI runner for NjordDeploy.

Enables programmatic deployment orchestration, disaster recovery backups,
volume restoration, and stack inspection directly from the terminal or CI/CD.
"""

import argparse
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from appdirs import user_data_dir

from configurator_app.app import get_components_paths, seed_user_components_if_needed
from managers.backup_manager import BackupManager
from managers.component_manager import ComponentManager
from managers.deployment_manager import DeploymentManager
from managers.setup_manager import SetupManager
from managers.ssh_manager import SSHManager
from utils.container_engine import get_configured_engine

logger = logging.getLogger("njorddeploy_cli")


class NjordCliRunner:
    """Headless CLI orchestration engine for NjordDeploy."""

    def __init__(self):
        """Initializes core managers."""
        seed_user_components_if_needed()
        metadata_path_obj, templates_path_obj = get_components_paths()
        metadata_path = str(metadata_path_obj)
        templates_path = str(templates_path_obj)

        self.component_mgr = ComponentManager(
            metadata_file_path=metadata_path, templates_path=templates_path
        )
        app_data_dir = Path(user_data_dir("NjordDeploy", "NjordDeploy"))
        output_dir = app_data_dir / "output"
        self.setup_mgr = SetupManager(self.component_mgr.reader, output_dir=output_dir)
        self.deployment_mgr = DeploymentManager(component_manager=self.component_mgr)

    def deploy(
        self,
        config: Dict[str, Any],
        stream_logs: bool = True,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Executes a headless deployment from a configuration dictionary.

        Args:
            config: Deployment configuration payload.
            stream_logs: Whether to print streaming log lines to console.
            log_callback: Optional custom callback for received log messages.

        Returns:
            True if deployment completed successfully, False otherwise.
        """
        # 1. Resolve Target Devices
        devices: List[Dict[str, Any]] = []
        if "devices" in config and isinstance(config["devices"], list):
            devices = config["devices"]
        elif "target" in config and isinstance(config["target"], dict):
            devices = [config["target"]]

        if not devices:
            logger.error("No target device specified in configuration.")
            return False

        first_device = next(iter(devices), {})
        target_ip = first_device.get("ip", "unknown")
        logger.info(f"Target host for headless deployment: {target_ip}")

        # 2. Resolve Selected Components
        selected_ids: List[str] = (
            config.get("components") or config.get("selected_components") or []
        )
        if not selected_ids:
            logger.error("No components selected for deployment.")
            return False

        logger.info(
            f"Selected components ({len(selected_ids)}): {', '.join(selected_ids)}"
        )

        # Validate component IDs against Single Source of Truth
        all_components = self.component_mgr.get_all_components()
        valid_ids = {c.get("id") for c in all_components if "id" in c}
        invalid_ids = [c for c in selected_ids if c not in valid_ids]
        if invalid_ids:
            logger.error(f"Unknown component IDs requested: {', '.join(invalid_ids)}")
            return False

        selected_components_data = [
            c for c in all_components if c.get("id") in selected_ids
        ]

        # 3. Resolve Environment Variables and Engine
        global_vars: Dict[str, str] = (
            config.get("env_vars") or config.get("global_vars") or {}
        )
        engine_type = (
            config.get("engine")
            or global_vars.get("CONTAINER_ENGINE")
            or get_configured_engine()
        )
        global_vars["CONTAINER_ENGINE"] = engine_type

        components_to_clean = config.get("components_to_clean", [])
        components_to_restart = config.get("components_to_restart", [])

        # 4. Prepare Deployment Package & Artifacts
        logger.info("Generating deployment templates and docker-compose.yml...")
        success, prep_errors = self.setup_mgr.prepare_deployment_package(
            selected_ids, global_vars, devices
        )
        if not success:
            logger.error(f"Deployment preparation failed: {prep_errors}")
            return False

        output_path = Path(self.setup_mgr.output_dir)
        self.component_mgr.generate_deployment_artifacts(
            selected_components_data=selected_components_data,
            global_vars=global_vars,
            output_path=output_path,
        )

        # 5. Execute Deployment via DeploymentManager
        task_id = uuid.uuid4().hex
        tasks: Dict[str, Any] = {
            task_id: {
                "status": "running",
                "logs": [f"Initializing headless deployment ({task_id})..."],
                "errors": [],
            }
        }

        logger.info(f"Starting Ansible deployment task: {task_id}")
        last_log_idx = 0

        # Run deployment synchronously in this process
        self.deployment_mgr.start_deployment(
            task_id=task_id,
            tasks=tasks,
            output_path=str(output_path),
            devices=devices,
            components_to_clean=components_to_clean,
            components_to_restart=components_to_restart,
            selected_components_data=selected_components_data,
            global_vars=global_vars,
        )

        # Stream remaining logs
        task_record = tasks.get(task_id, {})
        logs = task_record.get("logs", [])
        for log_line in logs[last_log_idx:]:
            if stream_logs:
                print(f"[DEPLOY] {log_line}")
            if log_callback:
                log_callback(log_line)

        final_status = task_record.get("status")
        if final_status == "completed":
            logger.info("==================================================")
            logger.info("HEADLESS DEPLOYMENT COMPLETED SUCCESSFULLY!")
            logger.info(f"Target: {target_ip} | Components: {len(selected_ids)}")
            logger.info("==================================================")
            return True
        else:
            logger.error(f"Deployment failed with status: {final_status}")
            return False

    def inspect_stack(
        self,
        ip: str,
        username: str = "root",
        password: str = "",  # nosec B107
        port: int = 22,
        stack_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspects docker-compose services and volume storage footprint."""
        ssh = SSHManager(
            hostname=ip,
            username=username,
            password=password,
            port=port,
            allow_auto_add=True,
            load_system_keys=False,
        )
        connected, msg = ssh.connect()
        if not connected:
            logger.error(f"SSH connection failed: {msg}")
            return {"status": "error", "message": msg}

        backup_mgr = BackupManager(project_config_dir=stack_dir or "/opt/njorddeploy")
        return backup_mgr.inspect_target(ssh, project_config_dir=stack_dir)

    def backup(
        self,
        ip: str,
        username: str = "root",
        password: str = "",  # nosec B107
        port: int = 22,
        stack_dir: Optional[str] = None,
        components: Optional[List[str]] = None,
        pause_containers: bool = False,
    ) -> Dict[str, Any]:
        """Creates a timestamped point-in-time backup archive."""
        ssh = SSHManager(
            hostname=ip,
            username=username,
            password=password,
            port=port,
            allow_auto_add=True,
            load_system_keys=False,
        )
        connected, msg = ssh.connect()
        if not connected:
            logger.error(f"SSH connection failed: {msg}")
            return {"status": "error", "message": msg}

        backup_mgr = BackupManager(project_config_dir=stack_dir or "/opt/njorddeploy")
        return backup_mgr.create_backup(
            ssh,
            selected_components=components,
            pause_containers=pause_containers,
            project_config_dir=stack_dir,
            log_callback=lambda m: logger.info(f"[BACKUP] {m.strip()}"),
        )

    def restore(
        self,
        ip: str,
        backup_filename: str,
        username: str = "root",
        password: str = "",  # nosec B107
        port: int = 22,
        stack_dir: Optional[str] = None,
        components: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Restores a backup archive onto the target server."""
        ssh = SSHManager(
            hostname=ip,
            username=username,
            password=password,
            port=port,
            allow_auto_add=True,
            load_system_keys=False,
        )
        connected, msg = ssh.connect()
        if not connected:
            logger.error(f"SSH connection failed: {msg}")
            return {"status": "error", "message": msg}

        backup_mgr = BackupManager(project_config_dir=stack_dir or "/opt/njorddeploy")
        return backup_mgr.restore_backup(
            ssh,
            backup_filename=backup_filename,
            selected_components=components,
            restart_after=True,
            project_config_dir=stack_dir,
            log_callback=lambda m: logger.info(f"[RESTORE] {m.strip()}"),
        )

    def list_backups(
        self,
        ip: str,
        username: str = "root",
        password: str = "",  # nosec B107
        port: int = 22,
        stack_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists available backup archives on target host."""
        ssh = SSHManager(
            hostname=ip,
            username=username,
            password=password,
            port=port,
            allow_auto_add=True,
            load_system_keys=False,
        )
        connected, msg = ssh.connect()
        if not connected:
            logger.error(f"SSH connection failed: {msg}")
            return []

        backup_mgr = BackupManager(project_config_dir=stack_dir or "/opt/njorddeploy")
        return backup_mgr.list_backups(ssh, project_config_dir=stack_dir)

    def scan_stacks(
        self,
        ip: str,
        username: str = "root",
        password: str = "",  # nosec B107
        port: int = 22,
    ) -> List[Dict[str, str]]:
        """Scans target host filesystem for existing docker-compose stacks."""
        ssh = SSHManager(
            hostname=ip,
            username=username,
            password=password,
            port=port,
            allow_auto_add=True,
            load_system_keys=False,
        )
        connected, msg = ssh.connect()
        if not connected:
            logger.error(f"SSH connection failed: {msg}")
            return []

        backup_mgr = BackupManager()
        return backup_mgr.discover_compose_files(ssh)

    @staticmethod
    def get_example_config() -> Dict[str, Any]:
        """Generates a sample JSON configuration for headless deployment."""
        return {
            "target": {
                "ip": "192.168.178.31",
                "username": "root",
                "password": "",
                "port": 22,
            },
            "components": [
                "uptime-kuma",
                "homarr",
                "portainer",
            ],
            "env_vars": {
                "GLOBAL_DOMAIN": "local.home",
                "CONTAINER_ENGINE": "docker",
            },
            "engine": "docker",
            "components_to_clean": [],
            "components_to_restart": [],
        }


def parse_cli_args(args_list: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command line arguments for headless CLI operations."""
    parser = argparse.ArgumentParser(
        description=(
            "NjordDeploy Headless CLI Runner for automated deployments & ops."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Main action modes
    action_group = parser.add_argument_group("CLI Action Modes")
    action_group.add_argument(
        "--deploy",
        nargs="?",
        const="DEFAULT",
        metavar="CONFIG_JSON",
        help="Execute deployment. Accepts a config JSON path or uses CLI flags.",
    )
    action_group.add_argument(
        "--inspect",
        action="store_true",
        help="Inspect target host stack, containers, and volume footprint.",
    )
    action_group.add_argument(
        "--backup",
        action="store_true",
        help="Create a point-in-time backup archive of managed volumes.",
    )
    action_group.add_argument(
        "--restore",
        metavar="ARCHIVE_FILENAME",
        help="Restore a backup snapshot archive onto target host.",
    )
    action_group.add_argument(
        "--list-backups",
        action="store_true",
        help="List available backup archives on target host.",
    )
    action_group.add_argument(
        "--scan-stacks",
        action="store_true",
        help="Auto-discover docker-compose stacks on target host filesystem.",
    )
    action_group.add_argument(
        "--example-config",
        action="store_true",
        help="Output sample JSON deployment configuration to stdout.",
    )

    # Target connection parameters
    conn_group = parser.add_argument_group("Target Host Parameters")
    conn_group.add_argument(
        "--ip", type=str, help="Target host IP address or hostname."
    )
    conn_group.add_argument(
        "--user",
        type=str,
        default="root",
        help="SSH username (default: root).",
    )
    conn_group.add_argument("--password", type=str, default="", help="SSH password.")
    conn_group.add_argument(
        "--port", type=int, default=22, help="SSH port (default: 22)."
    )
    conn_group.add_argument(
        "--stack-dir",
        type=str,
        default="/opt/njorddeploy",
        help="Stack directory (default: /opt/njorddeploy).",
    )

    # Options
    opt_group = parser.add_argument_group("Deployment & Backup Options")
    opt_group.add_argument(
        "--components",
        type=str,
        help="Comma-separated component IDs (e.g. uptime-kuma,homarr).",
    )
    opt_group.add_argument(
        "--engine",
        type=str,
        choices=["docker", "podman"],
        default="docker",
        help="Container engine (default: docker).",
    )
    opt_group.add_argument(
        "--pause-containers",
        action="store_true",
        help="Pause containers during backup for database consistency.",
    )

    return parser.parse_args(args_list)


def main(args_list: Optional[List[str]] = None) -> int:
    """Main CLI execution router."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_cli_args(args_list)
    runner = NjordCliRunner()

    if args.example_config:
        print(json.dumps(runner.get_example_config(), indent=2))
        return 0

    if args.deploy is not None:
        config: Dict[str, Any] = {}
        if args.deploy != "DEFAULT" and os.path.exists(args.deploy):
            with open(args.deploy, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            if not args.ip:
                logger.error("Missing target --ip for deployment.")
                return 1
            comp_list = (
                [c.strip() for c in args.components.split(",") if c.strip()]
                if args.components
                else []
            )
            config = {
                "target": {
                    "ip": args.ip,
                    "username": args.user,
                    "password": args.password,
                    "port": args.port,
                },
                "components": comp_list,
                "engine": args.engine,
            }
        success = runner.deploy(config)
        return 0 if success else 1

    if args.inspect:
        if not args.ip:
            logger.error("Missing target --ip address.")
            return 1
        res = runner.inspect_stack(
            ip=args.ip,
            username=args.user,
            password=args.password,
            port=args.port,
            stack_dir=args.stack_dir,
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "success" else 1

    if args.backup:
        if not args.ip:
            logger.error("Missing target --ip address.")
            return 1
        comp_list_backup: Optional[List[str]] = (
            [c.strip() for c in args.components.split(",") if c.strip()]
            if args.components
            else None
        )
        res = runner.backup(
            ip=args.ip,
            username=args.user,
            password=args.password,
            port=args.port,
            stack_dir=args.stack_dir,
            components=comp_list_backup,
            pause_containers=args.pause_containers,
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "success" else 1

    if args.restore:
        if not args.ip:
            logger.error("Missing target --ip address.")
            return 1
        comp_list_restore: Optional[List[str]] = (
            [c.strip() for c in args.components.split(",") if c.strip()]
            if args.components
            else None
        )
        res = runner.restore(
            ip=args.ip,
            backup_filename=args.restore,
            username=args.user,
            password=args.password,
            port=args.port,
            stack_dir=args.stack_dir,
            components=comp_list_restore,
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "success" else 1

    if args.list_backups:
        if not args.ip:
            logger.error("Missing target --ip address.")
            return 1
        res_list = runner.list_backups(
            ip=args.ip,
            username=args.user,
            password=args.password,
            port=args.port,
            stack_dir=args.stack_dir,
        )
        print(json.dumps(res_list, indent=2))
        return 0

    if args.scan_stacks:
        if not args.ip:
            logger.error("Missing target --ip address.")
            return 1
        found = runner.scan_stacks(
            ip=args.ip,
            username=args.user,
            password=args.password,
            port=args.port,
        )
        print(json.dumps(found, indent=2))
        return 0

    logger.error(
        "No valid CLI action specified. Run with --help for usage instructions."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
