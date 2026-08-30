# tests/test_agent_manager.py

import tempfile
from pathlib import Path

import pytest

from managers.agent_manager import AgentManager
from managers.database_manager import DatabaseManager


@pytest.fixture
def agent_setup():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test_agent.db")
        agent_mgr = AgentManager(db=db)
        user = db.create_user("david", "mockhash", email="david@example.com")
        yield db, agent_mgr, user


def test_register_node_and_generate_script(agent_setup):
    db, agent_mgr, user = agent_setup
    server = agent_mgr.register_node(
        user["id"], "Office Raspberry Pi 4", connection_type="agent"
    )
    assert server["name"] == "Office Raspberry Pi 4"
    assert server["agent_token"].startswith("njord_agt_")

    cmd = agent_mgr.generate_install_command(
        server["agent_token"], "https://deploy.njorddeploy.com"
    )
    assert "curl -sSL https://deploy.njorddeploy.com/install-agent" in cmd
    assert server["agent_token"] in cmd

    script = agent_mgr.generate_install_script(
        "https://deploy.njorddeploy.com", server["agent_token"]
    )
    assert "#!/usr/bin/env bash" in script
    assert 'HUB_URL="https://deploy.njorddeploy.com"' in script
    assert server["agent_token"] in script


def test_heartbeat_processing(agent_setup):
    db, agent_mgr, user = agent_setup
    server = agent_mgr.register_node(user["id"], "Remote Hetzner VPS")
    token = server["agent_token"]

    success, msg = agent_mgr.process_heartbeat(
        agent_token=token,
        telemetry={
            "hostname": "hetzner-node-01",
            "os_info": "Ubuntu 24.04 LTS",
            "memory": "2.4/8.0 GB",
        },
        client_ip="85.10.20.30",
    )
    assert success is True
    assert msg == "Heartbeat acknowledged."

    updated_server = db.get_server_by_agent_token(token)
    assert updated_server["status"] == "online"
    assert updated_server["ip"] == "85.10.20.30"
    assert "Ubuntu 24.04" in updated_server["os_info"]
