# tests/test_cmmi_coverage_gaps.py
"""Targeted tests to eliminate defensive fallback and branch coverage gaps

across modules under CMMI Level 5 quality gates.
"""

import json
import os
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_component_writer_private_templates_status(tmp_path: Path):
    """Cover component_writer.py line 122 when template is in private_templates_path."""
    from managers.component_writer import ComponentWriter

    meta_file = tmp_path / "components_metadata.json"
    meta_file.write_text(json.dumps({"components": {"priv-app": {}}}))
    public_tpl = tmp_path / "public_tpl"
    public_tpl.mkdir()
    priv_tpl = tmp_path / "priv_tpl"
    comp_dir = priv_tpl / "priv-app"
    comp_dir.mkdir(parents=True)
    tpl_file = comp_dir / "docker-compose.template.yml"
    tpl_file.write_text(
        "# Status: Verified\nversion: '3.8'\nservices:\n  app:\n    image: test\n"
    )

    writer = ComponentWriter(
        metadata_path=meta_file,
        templates_path=public_tpl,
        private_templates_path=priv_tpl,
    )
    result = writer.update_template_status("priv-app", "Candidate")
    assert result is True
    assert '# status: "Candidate"' in tpl_file.read_text()


def test_component_manager_private_meta_corrupt(tmp_path: Path):
    """Cover component_manager.py lines 117-118 when private metadata is corrupt."""
    from managers.component_manager import ComponentManager

    meta_file = tmp_path / "meta.json"
    meta_file.write_text(
        json.dumps(
            {"components": {"priv_app": {"is_private": True, "name": "Private App"}}}
        )
    )
    priv_meta = tmp_path / "private_meta.json"
    priv_meta.write_text("CORRUPT_NOT_JSON")
    tpl_dir = tmp_path / "tpl"
    tpl_dir.mkdir()

    cm = ComponentManager(
        templates_path=str(tpl_dir),
        metadata_file_path=str(meta_file),
        private_templates_path=str(tpl_dir),
        private_metadata_path=str(priv_meta),
    )
    all_comps = cm.get_all_components()
    assert any(c.get("id") == "priv_app" for c in all_comps)
    cm._save_metadata()
    saved = json.loads(priv_meta.read_text())
    assert "priv_app" in saved.get("components", {})


def test_component_manager_create_package_missing_packages_key(tmp_path: Path):
    """Cover component_manager.py line 126 when packages key is not present."""
    from managers.component_manager import ComponentManager

    meta_file = tmp_path / "meta.json"
    meta_file.write_text(json.dumps({"components": {}}))
    tpl_dir = tmp_path / "tpl"
    tpl_dir.mkdir()

    cm = ComponentManager(
        templates_path=str(tpl_dir),
        metadata_file_path=str(meta_file),
    )
    if "packages" in cm._components_data:
        del cm._components_data["packages"]

    cm.create_package("test_pkg", "Test Package")
    assert "test_pkg" in cm._components_data["packages"]


def test_component_manager_render_config_templates_in_private_tpl(
    tmp_path: Path,
):
    """Cover component_manager.py line 770 with private_templates_path."""
    from managers.component_manager import ComponentManager

    meta_file = tmp_path / "meta.json"
    meta_file.write_text(
        json.dumps(
            {
                "components": {
                    "my_svc": {
                        "id": "my_svc",
                        "category": "Tools",
                        "config_templates": {"app.conf": "template-config/app.conf"},
                    }
                }
            }
        )
    )
    public_tpl = tmp_path / "public_tpl"
    public_tpl.mkdir()
    priv_tpl = tmp_path / "priv_tpl"
    svc_dir = priv_tpl / "my_svc"
    cfg_dir = svc_dir / "template-config"
    cfg_dir.mkdir(parents=True)
    (svc_dir / "docker-compose.template.yml").write_text(
        "services:\n  svc:\n    image: test\n"
    )
    (cfg_dir / "app.conf").write_text("port = {{ port | default(8080) }}\n")

    cm = ComponentManager(
        templates_path=str(public_tpl),
        metadata_file_path=str(meta_file),
        private_templates_path=str(priv_tpl),
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    cm.generate_deployment_artifacts(
        selected_components_data=[
            {
                "id": "my_svc",
                "config_templates": {"app.conf": "template-config/app.conf"},
            }
        ],
        global_vars={"port": 9000},
        output_path=out_dir,
    )
    assert (out_dir / "data" / "template-config" / "app.conf").exists()
    assert (
        "port = 9000" in (out_dir / "data" / "template-config" / "app.conf").read_text()
    )


def test_deployment_manager_registry_ip_resolution(tmp_path: Path):
    """Cover deployment_manager.py lines 204-209 for registry IP resolution."""
    from managers.deployment_manager import DeploymentManager

    mock_cm = MagicMock()
    dm = DeploymentManager(component_manager=mock_cm)

    devices = [
        {
            "ip": "192.168.1.50",
            "username": "root",
            "registry_server": "reg.local",
            "registry_username": "admin",
            "registry_password": "secret",
        }
    ]
    tasks = {
        "t1": {"status": "pending", "logs": []},
        "t2": {"status": "pending", "logs": []},
    }

    # Case 1: Successful resolution to non-loopback IP
    with patch("socket.gethostbyname", return_value="192.168.1.10"):
        with patch("threading.Thread"):
            dm.start_deployment(
                task_id="t1",
                tasks=tasks,
                output_path=str(tmp_path),
                devices=devices,
                global_vars={},
            )
            assert any(
                "Private registry auth configured for: reg.local" in log
                for log in tasks["t1"]["logs"]
            )

    # Case 2: Resolution raises exception
    with patch("socket.gethostbyname", side_effect=socket.gaierror("lookup failed")):
        with patch("threading.Thread"):
            dm.start_deployment(
                task_id="t2",
                tasks=tasks,
                output_path=str(tmp_path),
                devices=devices,
                global_vars={},
            )
            assert any(
                "Private registry auth configured for: reg.local" in log
                for log in tasks["t2"]["logs"]
            )


def test_sync_manager_missing_cache_and_disabled_remote(tmp_path: Path):
    """Cover sync_manager.py lines 508, 528, 538, 603, 639."""
    from managers.sync_manager import SyncManager

    data_dir = tmp_path / "njord_data"
    data_dir.mkdir(parents=True)
    with patch.dict(os.environ, {"NJORD_DATA_DIR": str(data_dir)}):
        local_meta = tmp_path / "local_meta.json"
        local_meta.write_text(
            json.dumps(
                {
                    "components": {"comp1": {}},
                    "packages": {
                        "local_pkg": {"components": ["comp1"]},
                    },
                    "_njorddeploy": {},
                }
            )
        )
        local_tpl = tmp_path / "local_tpl"
        local_tpl.mkdir()

        sm = SyncManager(
            local_metadata_path=local_meta,
            local_templates_path=local_tpl,
        )

        # Line 508: get_local_only_components when cache_metadata_path does not exist
        if sm.cache_metadata_path.exists():
            sm.cache_metadata_path.unlink()
        assert sm.get_local_only_components() == []

        # Line 528: check_preflight_sync when remote sync disabled
        with patch.object(sm, "is_remote_sync_enabled", return_value=False):
            res = sm.check_preflight_sync()
            assert res["reason"] == "remote_sync_disabled"

        # Line 538: check_preflight_sync when cache does not exist fetches from remote
        with patch.object(sm, "is_remote_sync_enabled", return_value=True):
            with patch.object(sm, "fetch_from_remote") as mock_fetch:
                with patch.object(
                    sm, "get_sync_status", return_value={"components": {}}
                ):
                    res2 = sm.check_preflight_sync()
                    assert res2 is not None
                    assert mock_fetch.called

        # Line 603 & 639: sync_all with local-only package & existing dir
        sm.cache_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        sm.cache_metadata_path.write_text(
            json.dumps(
                {
                    "components": {"comp_remote": {}},
                    "packages": {},
                    "_njorddeploy": {},
                }
            )
        )
        sm.cache_templates_path.mkdir(parents=True, exist_ok=True)
        remote_comp_dir = sm.cache_templates_path / "comp_remote"
        remote_comp_dir.mkdir(parents=True, exist_ok=True)
        (remote_comp_dir / "docker-compose.template.yml").write_text("services: {}\n")

        # Existing local target dir to test line 639 (shutil.rmtree)
        existing_target = local_tpl / "comp_remote"
        existing_target.mkdir(parents=True, exist_ok=True)
        (existing_target / "old.txt").write_text("old")

        with patch.object(sm, "get_local_only_components", return_value=["comp1"]):
            sync_ok = sm.sync_all(force=False, preserve_local=True)
            assert sync_ok is True
            assert (local_tpl / "comp_remote" / "docker-compose.template.yml").exists()
            assert not (local_tpl / "comp_remote" / "old.txt").exists()


@pytest.fixture(name="editor_client")
def fixture_editor_client():
    from editor_app.app import create_app

    app = create_app({"TESTING": True, "LOGIN_DISABLED": True})
    with app.test_client() as c:
        yield c


@pytest.fixture(name="configurator_client")
def fixture_configurator_client():
    from configurator_app.app import create_app

    app = create_app({"TESTING": True, "LOGIN_DISABLED": True})
    with app.test_client() as c:
        yield c


def test_editor_app_preflight_and_tokens_css(editor_client, tmp_path: Path):
    """Cover editor_app/app.py lines 587-594 and 844."""
    # Test preflight GET normal
    with patch(
        "managers.sync_manager.SyncManager.check_preflight_sync",
        return_value={"is_synced": True},
    ):
        resp = editor_client.get("/api/sync/preflight")
        assert resp.status_code == 200
        assert resp.get_json()["is_synced"] is True

    # Test preflight GET error
    with patch(
        "managers.sync_manager.SyncManager.check_preflight_sync",
        side_effect=RuntimeError("sync err"),
    ):
        resp = editor_client.get("/api/sync/preflight")
        assert resp.status_code == 500

    # Test tokens.css not found (line 844)
    with patch.object(Path, "exists", return_value=False):
        resp_css = editor_client.get("/static/css/tokens.css")
        assert resp_css.status_code == 404


def test_configurator_app_safe_join_mismatch():
    """Cover safe_join line 78 when secure_filename changes path component."""
    from configurator_app.app import safe_join

    with patch("configurator_app.app.secure_filename", return_value="different_name"):
        with pytest.raises(ValueError, match="Invalid path component"):
            safe_join(Path("/tmp"), "valid_name")


def test_configurator_app_proxmox_live_check_failure(configurator_client):
    """Cover configurator_app/app.py lines 1897-1899 for failed live Proxmox check."""
    with patch.dict(
        os.environ,
        {
            "PROXMOX_HOST": "192.168.1.200",
            "PROXMOX_TOKEN_ID": "test",
            "PROXMOX_TOKEN_SECRET": "secret",
        },
    ):
        with patch(
            "utils.proxmox_client.ProxmoxClient.get",
            side_effect=RuntimeError("Connection refused"),
        ):
            resp = configurator_client.get("/api/config/proxmox/status?check=true")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["configured"] is True
            assert data["connection_healthy"] is False


def test_configurator_app_dns_custom_and_autodetect(configurator_client):
    """Cover configurator_app/app.py lines 2352 and 2357-2361."""
    from managers.ssh_manager import SSHManager

    mock_client = MagicMock()
    mock_client.get_next_vmid.return_value = 108
    mock_client.clone_vm.return_value = {"data": "UPID:test:vm"}
    mock_client.get_vm_ip.return_value = "192.168.1.155"

    # Line 2352: custom DNS
    mock_client.get.side_effect = [
        {"data": []},  # qemu list
        {"data": {"status": "stopped", "exitstatus": "OK"}},  # task status
        {"data": {}},  # config
    ]
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_client),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(SSHManager, "execute_command", return_value=(0, "OK")),
        patch.dict(
            os.environ,
            {
                "PROXMOX_TOKEN_ID": "id",
                "PROXMOX_TOKEN_SECRET": "sec",
                "PROXMOX_NAMESERVER": "10.0.0.5",
            },
        ),
        patch("time.sleep", return_value=None),
    ):
        resp = configurator_client.post(
            "/api/proxmox/create-vm",
            json={
                "hostname": "dns-test-1",
                "template_vmid": 9000,
                "node": "pve",
            },
        )
        assert resp.status_code == 201

    # Lines 2357-2361: autodetect Proxmox DNS (dns1, dns2)
    mock_client2 = MagicMock()
    mock_client2.get_next_vmid.return_value = 109
    mock_client2.clone_vm.return_value = {"data": "UPID:test:vm2"}
    mock_client2.get_vm_ip.return_value = "192.168.1.156"
    mock_client2.get.side_effect = [
        {"data": []},  # qemu list
        {"data": {"status": "stopped", "exitstatus": "OK"}},  # task status
        {"data": {"dns1": "192.168.1.1", "dns2": "1.1.1.1"}},  # nodes/pve/dns
    ]
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_client2),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(SSHManager, "execute_command", return_value=(0, "OK")),
        patch.dict(
            os.environ,
            {
                "PROXMOX_TOKEN_ID": "id",
                "PROXMOX_TOKEN_SECRET": "sec",
                "PROXMOX_NAMESERVER": "",
            },
        ),
        patch("time.sleep", return_value=None),
    ):
        resp2 = configurator_client.post(
            "/api/proxmox/create-vm",
            json={
                "hostname": "dns-test-2",
                "template_vmid": 9000,
                "node": "pve",
            },
        )
        assert resp2.status_code == 201
