# tests/test_container_engine.py
from utils.container_engine import (
    DEFAULT_ENGINE,
    SUPPORTED_ENGINES,
    ContainerEngine,
    get_configured_engine,
)


def test_supported_engines():
    assert "docker" in SUPPORTED_ENGINES
    assert "podman" in SUPPORTED_ENGINES
    assert DEFAULT_ENGINE == "docker"


def test_get_configured_engine(monkeypatch):
    monkeypatch.delenv("CONTAINER_ENGINE", raising=False)
    assert get_configured_engine() == "docker"

    monkeypatch.setenv("CONTAINER_ENGINE", "podman")
    assert get_configured_engine() == "podman"

    monkeypatch.setenv("CONTAINER_ENGINE", "PODMAN")
    assert get_configured_engine() == "podman"

    monkeypatch.setenv("CONTAINER_ENGINE", "invalid_engine")
    assert get_configured_engine() == "docker"


def test_container_engine_docker():
    engine = ContainerEngine("docker")
    assert engine.is_docker is True
    assert engine.is_podman is False
    assert engine.cli == "docker"
    assert engine.compose_cli == "docker compose"
    assert engine.get_network_create_cmd("test_net") == "docker network create test_net"
    assert engine.get_ps_cmd() == "docker ps"
    assert engine.get_ps_cmd(all_containers=True) == "docker ps -a"
    assert engine.get_logs_cmd("my-cont", tail=100) == "docker logs --tail 100 my-cont"
    assert (
        engine.get_logs_cmd("my-cont", tail=50, sudo=True)
        == "sudo -S docker logs --tail 50 my-cont"
    )
    assert engine.get_compose_up_cmd() == "docker compose up -d"
    assert engine.get_compose_down_cmd(remove_volumes=True) == "docker compose down -v"
    assert engine.get_compose_pull_cmd() == "docker compose pull --ignore-buildable"
    assert engine.get_compose_clean_cmd("svc1") == "docker compose rm -f -s -v svc1"
    assert engine.get_compose_restart_cmd("svc1") == "docker compose restart svc1"
    assert engine.get_exec_cmd("my-cont", "whoami") == "docker exec my-cont whoami"


def test_container_engine_podman():
    engine = ContainerEngine("podman")
    assert engine.is_docker is False
    assert engine.is_podman is True
    assert engine.cli == "podman"
    assert engine.compose_cli == "podman-compose"
    assert engine.get_network_create_cmd("test_net") == "podman network create test_net"
    assert engine.get_ps_cmd() == "podman ps"
    assert engine.get_ps_cmd(all_containers=True) == "podman ps -a"
    assert engine.get_logs_cmd("my-cont", tail=100) == "podman logs --tail 100 my-cont"
    # Podman rootless doesn't use sudo for container logs
    assert (
        engine.get_logs_cmd("my-cont", tail=50, sudo=True)
        == "podman logs --tail 50 my-cont"
    )
    assert engine.get_compose_up_cmd() == "podman-compose up -d"
    assert engine.get_compose_down_cmd(remove_volumes=True) == "podman-compose down -v"
    assert engine.get_compose_pull_cmd() == "podman-compose pull"
    assert engine.get_compose_clean_cmd("svc1") == "podman-compose rm -f -s -v svc1"
    assert engine.get_compose_restart_cmd("svc1") == "podman-compose restart svc1"


def test_provisioning_commands_docker():
    engine = ContainerEngine("docker")
    root_cmds = engine.get_provisioning_commands("root")
    assert any("get-docker.sh" in c for c in root_cmds)
    assert any("docker network create njorddeploy_net" in c for c in root_cmds)

    user_cmds = engine.get_provisioning_commands("pi")
    assert any("sudo usermod -aG docker pi" in c for c in user_cmds)


def test_provisioning_commands_podman():
    engine = ContainerEngine("podman")
    root_cmds = engine.get_provisioning_commands("root")
    assert any("apt-get install -y podman podman-compose" in c for c in root_cmds)
    assert any("net.ipv4.ip_unprivileged_port_start=53" in c for c in root_cmds)
    assert any("systemctl enable --now podman.socket" in c for c in root_cmds)
    assert any("podman network create njorddeploy_net" in c for c in root_cmds)

    user_cmds = engine.get_provisioning_commands("debian")
    assert any("loginctl enable-linger debian" in c for c in user_cmds)
    assert any("usermod --add-subuids" in c for c in user_cmds)
