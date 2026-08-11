# src/utils/container_engine.py
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SUPPORTED_ENGINES = ["docker", "podman"]
DEFAULT_ENGINE = "docker"


def get_configured_engine() -> str:
    """
    Returns the configured container engine ('docker' or 'podman').
    Defaults to 'docker' if unset or unrecognized.
    """
    engine = os.environ.get("CONTAINER_ENGINE", DEFAULT_ENGINE).strip().lower()
    if engine not in SUPPORTED_ENGINES:
        logger.warning(
            f"Unsupported CONTAINER_ENGINE '{engine}'. "
            f"Falling back to '{DEFAULT_ENGINE}'."
        )
        return DEFAULT_ENGINE
    return engine


class ContainerEngine:
    """
    Engine-agnostic helper class providing CLI commands and provisioning routines
    for Docker and Podman (rootless).
    """

    def __init__(self, engine_name: Optional[str] = None):
        self.engine = (
            engine_name.strip().lower() if engine_name else get_configured_engine()
        )
        if self.engine not in SUPPORTED_ENGINES:
            self.engine = DEFAULT_ENGINE

    @property
    def is_podman(self) -> bool:
        return self.engine == "podman"

    @property
    def is_docker(self) -> bool:
        return self.engine == "docker"

    @property
    def cli(self) -> str:
        """Returns the primary CLI binary name ('docker' or 'podman')."""
        return self.engine

    @property
    def compose_cli(self) -> str:
        """Returns the Compose command invocation."""
        return f"{self.engine} compose"

    def get_network_create_cmd(self, network_name: str = "njorddeploy_net") -> str:
        """Returns command to create the default network."""
        return f"{self.engine} network create {network_name}"

    def get_ps_cmd(
        self, all_containers: bool = False, format_str: Optional[str] = None
    ) -> str:
        """Returns command to list containers."""
        cmd = f"{self.engine} ps"
        if all_containers:
            cmd += " -a"
        if format_str:
            cmd += f" --format {format_str}"
        return cmd

    def get_logs_cmd(
        self, container_name: str, tail: int = 200, sudo: bool = False
    ) -> str:
        """Returns command to fetch container logs."""
        prefix = "sudo -S " if (sudo and self.is_docker) else ""
        return f"{prefix}{self.engine} logs --tail {tail} {container_name}"

    def get_compose_up_cmd(self, detach: bool = True) -> str:
        """Returns compose up command."""
        flag = " -d" if detach else ""
        return f"{self.engine} compose up{flag}"

    def get_compose_down_cmd(self, remove_volumes: bool = False) -> str:
        """Returns compose down command."""
        flag = " -v" if remove_volumes else ""
        return f"{self.engine} compose down{flag}"

    def get_compose_pull_cmd(self) -> str:
        """Returns compose pull command."""
        if self.is_docker:
            return "docker compose pull --ignore-buildable"
        return "podman compose pull"

    def get_compose_clean_cmd(self, service_name: str) -> str:
        """Returns compose rm / clean command for a specific service."""
        return f"{self.engine} compose rm -f -s -v {service_name}"

    def get_compose_restart_cmd(self, service_name: str) -> str:
        """Returns compose restart command for a specific service."""
        return f"{self.engine} compose restart {service_name}"

    def get_exec_cmd(self, container_name: str, command: str) -> str:
        """Returns container exec command."""
        return f"{self.engine} exec {container_name} {command}"

    def get_provisioning_commands(
        self, username: str = "root", unprivileged_port_start: int = 53
    ) -> List[str]:
        """
        Returns the sequence of provisioning shell commands for setting up
        the engine on Debian / Ubuntu / Raspberry Pi OS hosts.
        """
        is_root = username == "root"
        cmd_prefix = "" if is_root else "sudo "

        if self.is_docker:
            commands = [
                f"{cmd_prefix}apt-get update",
                f"{cmd_prefix}apt-get install -y curl ca-certificates gnupg",
                "curl -fsSL https://get.docker.com -o get-docker.sh",
                f"{cmd_prefix}sh get-docker.sh",
                f"{cmd_prefix}systemctl enable --now docker",
            ]
            if not is_root:
                commands.append(f"sudo usermod -aG docker {username}")
            commands.append(f"{cmd_prefix}docker network create njorddeploy_net")
            return commands

        # Podman rootless provisioning
        commands = [
            f"{cmd_prefix}apt-get update",
            (
                f"{cmd_prefix}apt-get install -y podman podman-compose "
                "slirp4netns uidmap dbus-user-session curl ca-certificates"
            ),
            # Configure kernel unprivileged port start (for port 53 DNS, 80/443 web)
            (
                f"{cmd_prefix}sh -c 'echo "
                f'"net.ipv4.ip_unprivileged_port_start={unprivileged_port_start}" '
                "> /etc/sysctl.d/99-podman-ports.conf'"
            ),
            f"{cmd_prefix}sysctl --system",
        ]

        if not is_root:
            # Enable systemd linger for rootless user session persistence
            commands.append(f"{cmd_prefix}loginctl enable-linger {username}")
            # Ensure subuid / subgid exist for rootless namespace mapping
            commands.append(
                f'{cmd_prefix}sh -c \'grep -q "^{username}:" /etc/subuid || '
                f"usermod --add-subuids 100000-165535 {username}'"
            )
            commands.append(
                f'{cmd_prefix}sh -c \'grep -q "^{username}:" /etc/subgid || '
                f"usermod --add-subgids 100000-165535 {username}'"
            )

        commands.append(f"{cmd_prefix}podman network create njorddeploy_net")
        return commands

    def to_dict(self) -> Dict[str, Any]:
        """Returns dictionary representation of engine status/config."""
        return {
            "engine": self.engine,
            "cli": self.cli,
            "compose_cli": self.compose_cli,
            "is_docker": self.is_docker,
            "is_podman": self.is_podman,
        }
