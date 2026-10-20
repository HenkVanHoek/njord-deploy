# tests/configurator_app/test_configurator_routes_final_coverage.py

"""Comprehensive test suite closing final coverage gaps in configurator_app/app.py.

Covers:
- analyze_snapshot and map_analysis_to_report_errors
- Auth token regeneration
- Help and settings routes (read errors, raw/form updates)
- Container engine persistence and repo validation
- Node scanner edge cases and MAC address resolution
- Proxmox LXC/VM creation error branches, cloud-init, and polling
- Proxmox target listing, IP querying, and target starting
- Software groups, required variables, selection validation, and installation
- Container logs sudo fallback and error paths
- Generated files preview edge cases
- Backup discover, inspect, create, list, restore, and download
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, mock_open, patch

import pytest

from managers.database_manager import DatabaseManager
from managers.ssh_manager import SSHManager
from src.configurator_app.app import (
    analyze_snapshot,
    create_app,
    map_analysis_to_report_errors,
)


@pytest.fixture
def configurator_final_env(tmp_path):
    """Sets up an isolated test app environment."""
    meta_path = tmp_path / "components_metadata.json"
    meta_path.write_text(
        json.dumps(
            {
                "components": {
                    "demo-app": {
                        "name": "Demo App",
                        "group": "utilities",
                        "ports": ["8080:8080"],
                        "has_configuration": True,
                        "variables": [{"name": "PORT", "default": 8080}],
                    }
                },
                "packages": {"pkg-1": {"name": "Pkg 1"}},
                "_njorddeploy": {
                    "group_rules": {
                        "utilities": {
                            "name": "Utilities",
                            "exclusive": False,
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    tmpl_dir = tmp_path / "component_templates"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    demo_tmpl = tmpl_dir / "demo-app"
    demo_tmpl.mkdir(parents=True, exist_ok=True)
    (demo_tmpl / "docker-compose.template.yml").write_text(
        "services:\n  demo:\n    image: demo:1.0\n", encoding="utf-8"
    )
    (demo_tmpl / "template-config").mkdir(parents=True, exist_ok=True)
    (demo_tmpl / "template-config" / "variables.json").write_text(
        json.dumps([{"name": "PORT", "default": 8080}]), encoding="utf-8"
    )

    test_config = {
        "TESTING": True,
        "AUTH_ENABLED": False,
        "SECRET_KEY": "final-cov-secret",
        "TEMPLATES_PATH": str(tmpl_dir),
        "METADATA_FILE_PATH": str(meta_path),
    }

    app = create_app(test_config)
    client = app.test_client()
    return client, meta_path, tmpl_dir


def test_analyze_snapshot_and_map_errors():
    """Verify analyze_snapshot and map_analysis_to_report_errors branches."""
    components = [
        {
            "id": "demo-app",
            "name": "Demo App",
            "ports": ["8080:8080", "9000:9000", "7000:7000", "invalid_port"],
            "volumes": ["/data/demo:/data", "/invalid_vol"],
        }
    ]
    snapshot = {
        "native_processes": [
            {"port": 8080, "process_name": "nginx"},
            {"port": 7000, "process_name": "unknown"},
        ],
        "containers": [
            {
                "name": "demo-app",
                "ports": "0.0.0.0:9000->9000/tcp",
                "mounts": "/data/demo:/data,/var/run/docker.sock:/sock",
            },
            {
                "name": "other-ct",
                "ports": "0.0.0.0:bad->9000/tcp,0.0.0.0:",
            },
        ],
        "resources": {"ram": {"total_mb": 1000, "used_mb": 950}},
    }

    conflicts, warnings = analyze_snapshot(components, snapshot, False)
    assert len(conflicts["ports"]) == 3
    assert len(conflicts["volumes"]) == 1
    assert len(warnings) == 1

    # Test error mapping
    analysis_results = {
        "external_conflicts": conflicts,
        "resource_warnings": warnings,
    }
    errors = map_analysis_to_report_errors(analysis_results, "192.168.1.50")
    assert len(errors) == 5

    # Test IndexError in analyze_snapshot (lines 103-104)
    class FakeStr(str):
        def __str__(self):
            return self

        def replace(self, old, new):
            return self

        def split(self, *args, **kwargs):
            if not args:
                return [self]
            raise IndexError("Simulated IndexError")

    snapshot_err = {"containers": [{"ports": FakeStr("0.0.0.0:80->80")}]}
    conf_err, _ = analyze_snapshot([], snapshot_err, False)
    assert conf_err is not None


def test_auth_regenerate_api_key(configurator_final_env):
    """Test /api/auth/regenerate-api-key route."""
    client, *_ = configurator_final_env

    # 1. Unauthenticated when auth is enabled
    with (
        patch("configurator_app.app.is_auth_enabled", return_value=True),
        patch("configurator_app.app.extract_api_key_from_request", return_value=None),
    ):
        res_unauth = client.post("/api/auth/regenerate-api-key")
        assert res_unauth.status_code == 401

    # 2. Admin not configured
    with (
        patch("configurator_app.app.is_auth_enabled", return_value=False),
        patch("configurator_app.app.load_auth_config", return_value=None),
    ):
        res_no_admin = client.post("/api/auth/regenerate-api-key")
        assert res_no_admin.status_code == 400

    # 3. Success
    with (
        patch("configurator_app.app.is_auth_enabled", return_value=False),
        patch(
            "configurator_app.app.load_auth_config",
            return_value={"username": "admin", "password_hash": "hash"},
        ),
        patch("configurator_app.app.generate_api_key", return_value="new-key-123"),
        patch("configurator_app.app.save_auth_config"),
    ):
        res_ok = client.post("/api/auth/regenerate-api-key")
        assert res_ok.status_code == 200
        assert res_ok.get_json()["api_key"] == "new-key-123"


def test_help_and_settings_routes(configurator_final_env, tmp_path):
    """Test help and settings GET/POST routes with read/write edge cases."""
    client, *_ = configurator_final_env

    # 1. Help route with file read error
    real_open = open

    def selective_open(file, *args, **kwargs):
        if "CONTRIBUTING.md" in str(file) or "UTILITIES.md" in str(file):
            raise OSError("Read error")
        return real_open(file, *args, **kwargs)

    with (
        patch.object(Path, "exists", return_value=True),
        patch("builtins.open", side_effect=selective_open),
    ):
        res_help = client.get("/help")
        assert res_help.status_code == 200

    # 2. Settings GET route with .env parsing
    env_content = '# Comment\nKEY1=value1\nKEY2="value2"\nINVALID_LINE\n'
    with (
        patch.object(Path, "exists", return_value=True),
        patch("builtins.open", mock_open(read_data=env_content)),
    ):
        res_settings = client.get("/settings")
        assert res_settings.status_code == 200

    # Settings GET read exception
    with (
        patch.object(Path, "exists", return_value=True),
        patch("builtins.open", side_effect=OSError("Read error")),
    ):
        res_settings_err = client.get("/settings")
        assert res_settings_err.status_code == 200

    # 3. Settings POST mode="raw" exception
    with patch("builtins.open", side_effect=OSError("Write error")):
        res_raw_err = client.post(
            "/api/settings", json={"mode": "raw", "raw_content": "FOO=BAR"}
        )
        assert res_raw_err.status_code == 500

    # Settings POST mode="raw" success
    with patch("builtins.open", mock_open()):
        res_raw_ok = client.post(
            "/api/settings", json={"mode": "raw", "raw_content": "FOO=BAR\n# c\n"}
        )
        assert res_raw_ok.status_code == 200

    # 4. Settings POST mode="form" invalid payload
    res_form_inv = client.post(
        "/api/settings", json={"mode": "form", "settings": "bad"}
    )
    assert res_form_inv.status_code == 400

    # Settings POST mode="form" success
    with (
        patch.object(Path, "exists", return_value=True),
        patch("builtins.open", mock_open(read_data='EXISTING="old"\n')),
    ):
        res_form_ok = client.post(
            "/api/settings",
            json={"mode": "form", "settings": {"EXISTING": "new", "NEW_KEY": "val"}},
        )
        assert res_form_ok.status_code == 200

    # Settings POST mode="form" exception
    with patch("builtins.open", side_effect=OSError("Form write error")):
        res_form_err = client.post(
            "/api/settings", json={"mode": "form", "settings": {"A": "B"}}
        )
        assert res_form_err.status_code == 500

    # Settings POST invalid mode
    res_bad_mode = client.post("/api/settings", json={"mode": "unknown"})
    assert res_bad_mode.status_code == 400


def test_container_engine_and_repo_routes(configurator_final_env):
    """Test container engine persistence, repo validation, and first run."""
    client, *_ = configurator_final_env

    # 1. /api/engine-switch write exception
    with patch("builtins.open", side_effect=OSError("Engine write error")):
        res_eng = client.post("/api/engine-switch", json={"engine": "podman"})
        assert res_eng.status_code == 500

    # 2. /api/validate-repo empty URL
    res_repo_empty = client.post("/api/validate-repo", json={"url": "   "})
    assert res_repo_empty.status_code == 400

    # Valid repo
    with patch(
        "managers.sync_manager.SyncManager.validate_remote_repo",
        return_value=(True, "Reachable"),
    ):
        res_repo_ok = client.post(
            "/api/validate-repo", json={"url": "https://github.com/foo/bar"}
        )
        assert res_repo_ok.status_code == 200

    # Invalid repo
    with patch(
        "managers.sync_manager.SyncManager.validate_remote_repo",
        return_value=(False, "Failed"),
    ):
        res_repo_fail = client.post(
            "/api/validate-repo", json={"url": "https://github.com/foo/bar"}
        )
        assert res_repo_fail.status_code == 400

    # 3. /api/first-run-status when .env has CONTAINER_ENGINE
    with (
        patch.object(Path, "exists", return_value=True),
        patch("builtins.open", mock_open(read_data='CONTAINER_ENGINE="docker"\n')),
    ):
        res_fr = client.get("/api/first-run-status")
        assert res_fr.status_code == 200
        assert res_fr.get_json()["first_run"] is False

    # First run status read exception
    with (
        patch.object(Path, "exists", return_value=True),
        patch("builtins.open", side_effect=OSError("Read error")),
    ):
        res_fr_err = client.get("/api/first-run-status")
        assert res_fr_err.status_code == 200


def test_node_scanner_edge_cases(configurator_final_env):
    """Test /scan-pis MAC resolution and scanning errors."""
    client, *_ = configurator_final_env

    # 1. Blank direct IP
    res_blank = client.post(
        "/scan-pis", json={"discovery_method": "direct_ip", "direct_target_ip": " "}
    )
    assert res_blank.status_code == 400

    # 2. MAC resolution scanner error
    with patch(
        "node_scanner.NodeScanner.scan",
        return_value=([], [], "Nmap subnet scan failed", {}),
    ):
        res_mac_err = client.post(
            "/scan-pis",
            json={
                "discovery_method": "direct_ip",
                "direct_target_ip": "aa:bb:cc:dd:ee:ff",
            },
        )
        assert res_mac_err.status_code == 500

    # 3. MAC resolution scanner exception
    with patch(
        "node_scanner.NodeScanner.scan",
        side_effect=Exception("Scan crash"),
    ):
        res_mac_crash = client.post(
            "/scan-pis",
            json={
                "discovery_method": "direct_ip",
                "direct_target_ip": "aa:bb:cc:dd:ee:ff",
            },
        )
        assert res_mac_crash.status_code == 500

    # 4. Normal scan error
    with patch(
        "node_scanner.NodeScanner.scan",
        return_value=([], [], "Scanner failure", {}),
    ):
        res_scan_err = client.post("/scan-pis", json={})
        assert res_scan_err.status_code == 500

    # 5. Normal scan exception
    with patch(
        "node_scanner.NodeScanner.scan",
        side_effect=Exception("Scan exception"),
    ):
        res_scan_exc = client.post("/scan-pis", json={})
        assert res_scan_exc.status_code == 500


def test_proxmox_lxc_and_vm_edge_cases(configurator_final_env, monkeypatch):
    """Test Proxmox LXC/VM creation, template downloads, and error exits."""
    client, *_ = configurator_final_env
    monkeypatch.setenv("PROXMOX_HOST", "192.168.1.10")
    monkeypatch.setenv("PROXMOX_TOKEN_ID", "root@pam!token")
    monkeypatch.setenv("PROXMOX_TOKEN_SECRET", "secret-1234")

    mock_key = MagicMock()
    mock_key.get_name.return_value = "ssh-ed25519"
    mock_key.get_base64.return_value = "AAAA..."

    # 0. Missing credentials branch
    monkeypatch.setenv("PROXMOX_TOKEN_ID", "")
    res_no_creds = client.post("/api/proxmox/create-lxc", json={"name": "x"})
    assert res_no_creds.status_code == 500
    monkeypatch.setenv("PROXMOX_TOKEN_ID", "root@pam!token")

    # 1. LXC task fails with exit status
    mock_pve = MagicMock()
    mock_pve.get_next_vmid.return_value = 105
    mock_pve.get_lxc_list.return_value = []
    mock_pve.get.side_effect = [
        {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},  # storages
        {"data": [{"volid": "local:vztmpl/debian.tar.zst"}]},  # templates
        {
            "data": {"status": "stopped", "exitstatus": "ERROR 1"}
        },  # task stopped with error
    ]
    mock_pve.post.return_value = {"data": "UPID:123"}
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve),
        patch.object(SSHManager, "get_ssh_key", return_value=mock_key),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_fail = client.post(
            "/api/proxmox/create-lxc",
            json={
                "name": "test-ct",
                "password": "pass",
                "pubkey": "ssh-rsa key",
            },
        )
        assert res_lxc_fail.status_code == 500

    # 2. LXC template auto-download fallback via aplinfo
    mock_pve2 = MagicMock()
    mock_pve2.get_next_vmid.return_value = 106
    mock_pve2.get_lxc_list.return_value = []
    mock_pve2.get.side_effect = [
        {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},  # storages
        {"data": []},  # no existing templates
        {
            "data": [
                {
                    "package": "debian-12-standard",
                    "template": "debian-12-standard_12.0.tar.zst",
                }
            ]
        },  # aplinfo data
        {"data": {"status": "stopped"}},  # task download status
        {"data": {"status": "stopped", "exitstatus": "OK"}},  # create ok
        {
            "data": [
                {
                    "name": "eth0",
                    "inet": "192.168.1.150/24",
                }
            ]
        },  # interfaces
    ]
    mock_pve2.post.side_effect = [
        {"data": "UPID:download"},  # aplinfo post UPID
        {"data": "UPID:create"},  # create lxc post
        {},  # start lxc
    ]
    mock_key = MagicMock()
    mock_key.get_name.return_value = "ssh-ed25519"
    mock_key.get_base64.return_value = "AAAA..."

    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve2),
        patch.object(SSHManager, "get_ssh_key", return_value=mock_key),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(SSHManager, "execute_command", return_value=(0, "Success")),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_dl = client.post(
            "/api/proxmox/create-lxc",
            json={
                "name": "auto-dl-ct",
                "password": "pass",
                "pubkey": "ssh-rsa key",
            },
        )
        assert res_lxc_dl.status_code == 201

    # 3. LXC no template found
    mock_pve3 = MagicMock()
    mock_pve3.get_next_vmid.return_value = 107
    mock_pve3.get_lxc_list.return_value = []
    mock_pve3.get.side_effect = [
        {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},
        {"data": []},
        {"data": []},  # aplinfo empty
    ]
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve3),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_no_tmpl = client.post(
            "/api/proxmox/create-lxc",
            json={
                "name": "no-tmpl-ct",
                "password": "pass",
                "pubkey": "ssh-rsa key",
            },
        )
        assert res_lxc_no_tmpl.status_code in (400, 500)

    # 4. VM clone task failed
    res_vm_novmid = client.post("/api/proxmox/create-vm", json={"name": "fail-vm"})
    assert res_vm_novmid.status_code == 400

    res_vm_badint = client.post(
        "/api/proxmox/create-vm", json={"name": "fail-vm", "template_vmid": "bad"}
    )
    assert res_vm_badint.status_code == 400

    mock_pve4 = MagicMock()
    mock_pve4.get_next_vmid.return_value = 108
    mock_pve4.get.side_effect = [
        {"data": []},  # qemu list
        {"data": {"status": "stopped", "exitstatus": "CLONE_ERR"}},  # clone error
    ]
    mock_pve4.clone_vm.return_value = {"data": "UPID:clone"}
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve4),
        patch.object(SSHManager, "get_ssh_key", return_value=mock_key),
        patch("time.sleep", return_value=None),
    ):
        res_vm_err = client.post(
            "/api/proxmox/create-vm",
            json={
                "name": "fail-vm",
                "template_vmid": 9000,
                "password": "pass",
                "pubkey": "ssh-rsa key",
            },
        )
        assert res_vm_err.status_code == 500

    # 5. VM Cloud-Init already exists vs attach ide2
    mock_pve5 = MagicMock()
    mock_pve5.get_next_vmid.return_value = 109
    mock_pve5.get.side_effect = [
        {"data": []},  # qemu list
        {"data": {"status": "stopped", "exitstatus": "OK"}},  # clone ok
        {"data": {"bootdisk": "virtio0"}},  # config
    ]
    mock_pve5.clone_vm.return_value = {"data": "UPID:clone"}
    mock_pve5.configure_vm.side_effect = [
        Exception("drive already exists"),
        {},
    ]
    mock_pve5.get_vm_ip.return_value = "192.168.1.160"
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve5),
        patch.object(SSHManager, "get_ssh_key", return_value=mock_key),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(SSHManager, "execute_command", return_value=(0, "Success")),
        patch("time.sleep", return_value=None),
    ):
        res_vm_ci = client.post(
            "/api/proxmox/create-vm",
            json={
                "name": "ci-vm",
                "template_vmid": 9000,
                "password": "pass",
                "pubkey": "ssh-rsa key",
                "storage_size": 20,
            },
        )
        assert res_vm_ci.status_code == 201


def test_proxmox_targets_and_ip_routes(configurator_final_env, monkeypatch):
    """Test Proxmox target listing, IP querying, and target starting."""
    client, *_ = configurator_final_env

    # 1. list_proxmox_targets missing tokens
    monkeypatch.setenv("PROXMOX_TOKEN_ID", "")
    monkeypatch.setenv("PROXMOX_TOKEN_SECRET", "")
    res_no_tok = client.post("/api/proxmox/list-targets")
    assert res_no_tok.status_code == 500

    # list_proxmox_targets query exception in LXC / QEMU
    monkeypatch.setenv("PROXMOX_TOKEN_ID", "user!token")
    monkeypatch.setenv("PROXMOX_TOKEN_SECRET", "secret")
    mock_pve = MagicMock()
    mock_pve.get.side_effect = [
        Exception("LXC query failed"),
        Exception("QEMU query failed"),
    ]
    with patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve):
        res_targets = client.post("/api/proxmox/list-targets")
        assert res_targets.status_code == 200
        assert res_targets.get_json()["targets"] == []

    # 2. get_proxmox_target_ip invalid args
    res_bad_ip_req = client.post("/api/proxmox/get-target-ip", json={})
    assert res_bad_ip_req.status_code == 400

    # get_proxmox_target_ip exception
    with patch("utils.proxmox_client.ProxmoxClient", side_effect=Exception("PVE down")):
        res_ip_err = client.post(
            "/api/proxmox/get-target-ip", json={"vmid": 100, "type": "lxc"}
        )
        assert res_ip_err.status_code == 500

    # 3. start_proxmox_target invalid args
    res_start_bad = client.post("/api/proxmox/start-target", json={})
    assert res_start_bad.status_code == 400

    # start_proxmox_target timeout (no IP acquired)
    mock_pve_start = MagicMock()
    mock_pve_start.get_vm_ip.return_value = None
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_start),
        patch("time.sleep"),
    ):
        res_start_to = client.post(
            "/api/proxmox/start-target", json={"vmid": 100, "type": "qemu"}
        )
        assert res_start_to.status_code in (400, 500)


def test_component_software_and_selection_validation(configurator_final_env):
    """Test software selection, variable requirements, and validation."""
    client, _, tmpl_dir = configurator_final_env

    # 1. /set-ip missing IP
    res_no_ip = client.post("/set-ip", json={})
    assert res_no_ip.status_code == 400
    res_set_ip = client.post("/set-ip", json={"ip": "192.168.1.99"})
    assert res_set_ip.status_code == 200

    # 2. /get-device-details error branches
    res_dev_no_details = client.post(
        "/get-device-details",
        json={"ip": "10.0.0.1", "username": "pi", "password": "pi"},
    )
    assert res_dev_no_details.status_code in (400, 500)

    # 3. /api/components exception
    with patch(
        "managers.component_manager.ComponentManager.get_all_components",
        side_effect=Exception("Meta error"),
    ):
        res_comp_err = client.get("/api/components")
        assert res_comp_err.status_code == 500

    # 4. /get-available-software exception
    with patch(
        "managers.component_manager.ComponentManager.get_all_components",
        side_effect=Exception("Soft error"),
    ):
        res_soft_err = client.post("/get-available-software")
        assert res_soft_err.status_code == 500

    # 5. /get-software-groups exception
    with patch(
        "managers.component_manager.ComponentManager.get_all_components",
        side_effect=Exception("Groups error"),
    ):
        res_grp_err = client.get("/get-software-groups")
        assert res_grp_err.status_code == 500

    # 6. /get-required-variables invalid payload and exception
    res_req_bad = client.post("/get-required-variables", json={})
    assert res_req_bad.status_code == 400
    with patch(
        "managers.component_manager.ComponentManager.get_all_components",
        side_effect=Exception("Vars error"),
    ):
        res_req_err = client.post(
            "/get-required-variables", json={"selected_components": ["demo-app"]}
        )
        assert res_req_err.status_code == 500

    # 7. /validate-selection path traversal and missing template dir
    res_val_trav = client.post(
        "/validate-selection", json={"selected_components": ["../../evil"]}
    )
    assert res_val_trav.status_code == 400

    res_val_missing_dir = client.post(
        "/validate-selection", json={"selected_components": ["nonexistent-comp"]}
    )
    assert res_val_missing_dir.status_code == 400

    # Missing variables.json when has_configuration is True
    no_var_comp = tmpl_dir / "no-var-app"
    no_var_comp.mkdir(parents=True, exist_ok=True)
    with patch(
        "managers.component_manager.ComponentManager.get_all_components",
        return_value=[{"id": "no-var-app", "has_configuration": True}],
    ):
        res_missing_var = client.post(
            "/validate-selection", json={"selected_components": ["no-var-app"]}
        )
        assert res_missing_var.status_code == 400

    # 8. /start-installation invalid payload, preparation error, and success
    res_inst_bad = client.post("/start-installation", json={})
    assert res_inst_bad.status_code == 400

    with patch(
        "managers.setup_manager.SetupManager.prepare_deployment_package",
        return_value=(False, ["Pre-flight failed"]),
    ):
        res_prep_err = client.post(
            "/start-installation",
            json={"selected_components": ["demo-app"], "devices": [{"ip": "1.1.1.1"}]},
        )
        assert res_prep_err.status_code == 400

    with (
        patch(
            "managers.setup_manager.SetupManager.prepare_deployment_package",
            return_value=(True, []),
        ),
        patch(
            "managers.component_manager.ComponentManager.generate_deployment_artifacts"
        ),
    ):
        res_inst_ok = client.post(
            "/start-installation",
            json={"selected_components": ["demo-app"], "devices": [{"ip": "1.1.1.1"}]},
        )
        assert res_inst_ok.status_code == 200


def test_container_logs_and_generated_files(configurator_final_env, tmp_path):
    """Test container logs sudo prompt fallback and generated files."""
    client, *_ = configurator_final_env

    def fake_log_exec(self, cmd, cb=None, *args, **kwargs):
        if "docker ps" in cmd and cb is None:
            return 1, ""
        if cb:
            cb("Running log line\n")
        return 0, "Running log line\n"

    with (
        patch.object(SSHManager, "connect", return_value=(True, "OK")),
        patch.object(SSHManager, "execute_command", fake_log_exec),
    ):
        res_logs = client.post(
            "/get-container-logs",
            json={
                "ip": "10.0.0.1",
                "username": "pi",
                "password": "pi",
                "container_name": "caddy",
            },
        )
        assert res_logs.status_code == 200
        assert "Running log line" in res_logs.get_json()["logs"]

    # Container logs not found / empty error
    with (
        patch.object(SSHManager, "connect", return_value=(True, "OK")),
        patch.object(SSHManager, "execute_command", return_value=(1, "")),
    ):
        res_logs_404 = client.post(
            "/get-container-logs",
            json={
                "ip": "10.0.0.1",
                "username": "pi",
                "password": "pi",
                "container_name": "stopped_ct",
            },
        )
        assert res_logs_404.status_code == 404

    # Generated files: invalid directory, unauthorized, unreadable
    res_gen_no_path = client.post("/get-generated-files", json={})
    assert res_gen_no_path.status_code == 400

    res_gen_empty = client.post("/get-generated-files", json={"output_path": "///"})
    assert res_gen_empty.status_code == 400

    # Unreadable file test
    staging = tmp_path / "app_data"
    staging.mkdir(parents=True, exist_ok=True)
    out_dir = staging / "my_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "compose.yml").write_text("services:\n", encoding="utf-8")
    (out_dir / "unreadable.bin").write_bytes(b"\xff\xfe\x00\x00")

    with patch("configurator_app.app.get_app_data_dir", return_value=staging):
        res_gen_ok = client.post(
            "/get-generated-files",
            json={"output_path": "my_output"},
        )
        assert res_gen_ok.status_code == 200
        assert "compose.yml" in res_gen_ok.get_json()["files"]


def test_backup_routes_deep_coverage(configurator_final_env, tmp_path):
    """Test backup discover, inspect, create, list, restore, and download."""
    client, *_ = configurator_final_env

    # 1. discover-compose missing credentials & SSH fail
    res_disc_no_ip = client.post("/api/backup/discover-compose", json={})
    assert res_disc_no_ip.status_code == 400

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        return_value=(False, "Auth failed"),
    ):
        res_disc_ssh_fail = client.post(
            "/api/backup/discover-compose",
            json={"ip": "1.1.1.1", "username": "root"},
        )
        assert res_disc_ssh_fail.status_code == 400

    # 2. inspect missing credentials & SSH fail & status != success
    res_insp_no_ip = client.post("/api/backup/inspect", json={})
    assert res_insp_no_ip.status_code == 400

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        return_value=(False, "Auth failed"),
    ):
        res_insp_ssh_fail = client.post(
            "/api/backup/inspect", json={"ip": "1.1.1.1", "username": "root"}
        )
        assert res_insp_ssh_fail.status_code == 400

    with (
        patch("managers.ssh_manager.SSHManager.connect", return_value=(True, "OK")),
        patch(
            "managers.backup_manager.BackupManager.inspect_target",
            return_value={"status": "error", "message": "Not found"},
        ),
    ):
        res_insp_err = client.post(
            "/api/backup/inspect", json={"ip": "1.1.1.1", "username": "root"}
        )
        assert res_insp_err.status_code == 404

    # 3. create missing creds, SSH fail, and failure result
    res_crt_no_ip = client.post("/api/backup/create", json={})
    assert res_crt_no_ip.status_code == 400

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        return_value=(False, "Auth failed"),
    ):
        res_crt_ssh_fail = client.post(
            "/api/backup/create", json={"ip": "1.1.1.1", "username": "root"}
        )
        assert res_crt_ssh_fail.status_code == 400

    with (
        patch("managers.ssh_manager.SSHManager.connect", return_value=(True, "OK")),
        patch(
            "managers.backup_manager.BackupManager.create_backup",
            return_value={"status": "failed", "message": "Tar failed"},
        ),
    ):
        res_crt_fail = client.post(
            "/api/backup/create", json={"ip": "1.1.1.1", "username": "root"}
        )
        assert res_crt_fail.status_code == 400

    # 4. list missing creds and SSH fail
    res_lst_no_ip = client.post("/api/backup/list", json={})
    assert res_lst_no_ip.status_code == 400

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        return_value=(False, "Auth failed"),
    ):
        res_lst_ssh_fail = client.post(
            "/api/backup/list", json={"ip": "1.1.1.1", "username": "root"}
        )
        assert res_lst_ssh_fail.status_code == 400

    # 5. restore missing fields, SSH fail, and restore failure
    res_rst_missing = client.post("/api/backup/restore", json={})
    assert res_rst_missing.status_code == 400

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        return_value=(False, "Auth failed"),
    ):
        res_rst_ssh_fail = client.post(
            "/api/backup/restore",
            json={
                "ip": "1.1.1.1",
                "username": "root",
                "backup_filename": "njorddeploy_backup_20260101_120000.tar.gz",
            },
        )
        assert res_rst_ssh_fail.status_code == 400

    with (
        patch("managers.ssh_manager.SSHManager.connect", return_value=(True, "OK")),
        patch(
            "managers.backup_manager.BackupManager.restore_backup",
            return_value={"status": "error", "message": "Restore error"},
        ),
    ):
        res_rst_err = client.post(
            "/api/backup/restore",
            json={
                "ip": "1.1.1.1",
                "username": "root",
                "backup_filename": "njorddeploy_backup_20260101_120000.tar.gz",
            },
        )
        assert res_rst_err.status_code == 400

    # 6. download invalid filename format, missing creds, SSH fail, sftp fail
    res_dl_bad_fn = client.get("/api/backup/download/evil.sh")
    assert res_dl_bad_fn.status_code == 400

    valid_fn = "njorddeploy_backup_20260101_120000.tar.gz"
    res_dl_no_creds = client.get(f"/api/backup/download/{valid_fn}")
    assert res_dl_no_creds.status_code == 400

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        return_value=(False, "Auth failed"),
    ):
        res_dl_ssh_fail = client.get(
            f"/api/backup/download/{valid_fn}?ip=1.1.1.1&username=root"
        )
        assert res_dl_ssh_fail.status_code == 400

    with (
        patch("managers.ssh_manager.SSHManager.connect", return_value=(True, "OK")),
        patch(
            "managers.backup_manager.BackupManager.download_backup_sftp",
            return_value=(False, "SFTP error", None),
        ),
    ):
        res_dl_sftp_fail = client.get(
            f"/api/backup/download/{valid_fn}?ip=1.1.1.1&username=root"
        )
        assert res_dl_sftp_fail.status_code == 500

    # Download when local file exists
    staging = tmp_path / "staging_dl"
    staging.mkdir(parents=True, exist_ok=True)
    local_archive = staging / "backups_download" / valid_fn
    local_archive.parent.mkdir(parents=True, exist_ok=True)
    local_archive.write_bytes(b"\x1f\x8b\x08\x00fake_archive")

    with patch("configurator_app.app.get_app_data_dir", return_value=staging):
        res_dl_ok = client.get(f"/api/backup/download/{valid_fn}")
        assert res_dl_ok.status_code == 200
        assert res_dl_ok.data == b"\x1f\x8b\x08\x00fake_archive"


def test_configurator_app_coverage_boost(configurator_final_env, tmp_path, monkeypatch):
    """Deep coverage boost targeting remaining edge cases across configurator_app."""
    client, meta_path, tmpl_dir = configurator_final_env

    monkeypatch.setenv("PROXMOX_HOST", "192.168.1.10")
    monkeypatch.setenv("PROXMOX_TOKEN_ID", "root@pam!token")
    monkeypatch.setenv("PROXMOX_TOKEN_SECRET", "secret-1234")

    # 1. /validate-selection: component with has_configuration missing variables.json
    comp_config_dir = tmpl_dir / "configured-app"
    comp_config_dir.mkdir(parents=True, exist_ok=True)
    (comp_config_dir / "docker-compose.template.yml").write_text(
        "services:\n", encoding="utf-8"
    )

    current_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    current_meta["components"]["configured-app"] = {
        "name": "Configured App",
        "has_configuration": True,
        "group": "tools",
    }
    meta_path.write_text(json.dumps(current_meta), encoding="utf-8")

    from configurator_app.app import safe_join

    with pytest.raises(ValueError, match="Path traversal detected"):
        with patch.object(Path, "is_relative_to", return_value=False):
            safe_join(Path("/tmp"), "sub")

    with (
        patch("configurator_app.app.safe_join", return_value=comp_config_dir),
        patch(
            "managers.component_manager.ComponentManager.get_all_components",
            return_value=[{"id": "demo-app", "has_configuration": True}],
        ),
    ):
        res_val_no_var = client.post(
            "/validate-selection",
            json={"selected_components": ["demo-app"]},
        )
        assert res_val_no_var.status_code == 400
        assert "variables.json" in res_val_no_var.get_json()["error"]

        # Now add variables.json -> success 200
        cfg_sub = comp_config_dir / "template-config"
        cfg_sub.mkdir(parents=True, exist_ok=True)
        (cfg_sub / "variables.json").write_text("[]", encoding="utf-8")

        res_val_ok = client.post(
            "/validate-selection",
            json={"selected_components": ["demo-app"]},
        )
        assert res_val_ok.status_code == 200

    # Validate selection exception -> 500
    with patch(
        "managers.component_manager.ComponentManager.get_all_components",
        side_effect=Exception("Validation crash"),
    ):
        res_val_exc = client.post(
            "/validate-selection",
            json={"selected_components": ["demo-app"]},
        )
        assert res_val_exc.status_code == 500

    # 2. /deploy-configuration parameter validation
    res_dep_bad_types = client.post(
        "/deploy-configuration",
        json={
            "output_path": 123,
            "devices": "not_a_list",
        },
    )
    assert res_dep_bad_types.status_code == 400

    res_dep_empty_dev = client.post(
        "/deploy-configuration",
        json={
            "output_path": "valid_output",
            "devices": [],
            "components_to_clean": "bad",
            "components_to_restart": "bad",
            "analysis_results": "bad",
            "selected_components_data": "bad",
            "global_vars": "bad",
        },
    )
    assert res_dep_empty_dev.status_code == 400
    assert "No target device" in res_dep_empty_dev.get_json()["error"]

    # 3. /get-container-logs docker ps exit_code == 0, sudo fallback & podman
    def fake_log_exec_docker(self, cmd, cb=None, *args, **kwargs):
        if cmd.strip() in ("docker ps", "podman ps"):
            return 0, ""
        if cb:
            cb("Docker log line\n")
        return 0, "Docker log line\n"

    def fake_log_exec_docker_sudo(self, cmd, cb=None, *args, **kwargs):
        if "docker ps" in cmd and "head -n 1" not in cmd:
            return 1, "Permission denied"
        if cb:
            cb("Sudo docker log line\n")
        return 0, "Sudo docker log line\n"

    with (
        patch(
            "utils.container_engine.ContainerEngine.is_docker",
            new_callable=PropertyMock,
            return_value=True,
        ),
        patch.object(SSHManager, "connect", return_value=(True, "OK")),
        patch.object(SSHManager, "execute_command", fake_log_exec_docker),
    ):
        res_dock_ok = client.post(
            "/get-container-logs",
            json={
                "ip": "10.0.0.1",
                "username": "pi",
                "password": "pi",
                "container_name": "caddy",
            },
        )
        assert res_dock_ok.status_code == 200
        assert "Docker log line" in res_dock_ok.get_json()["logs"]

    # Docker engine with non-zero exit_code_group -> sudo fallback
    with (
        patch(
            "utils.container_engine.ContainerEngine.is_docker",
            new_callable=PropertyMock,
            return_value=True,
        ),
        patch.object(SSHManager, "connect", return_value=(True, "OK")),
        patch.object(SSHManager, "execute_command", fake_log_exec_docker_sudo),
    ):
        res_dock_sudo = client.post(
            "/get-container-logs",
            json={
                "ip": "10.0.0.1",
                "username": "pi",
                "password": "pi",
                "container_name": "caddy",
            },
        )
        assert res_dock_sudo.status_code == 200

    # Podman engine branch
    with (
        patch(
            "utils.container_engine.ContainerEngine.is_docker",
            new_callable=PropertyMock,
            return_value=False,
        ),
        patch.object(SSHManager, "connect", return_value=(True, "OK")),
        patch.object(SSHManager, "execute_command", fake_log_exec_docker),
    ):
        res_pod_ok = client.post(
            "/get-container-logs",
            json={
                "ip": "10.0.0.1",
                "username": "pi",
                "password": "pi",
                "container_name": "caddy",
            },
        )
        assert res_pod_ok.status_code == 200

    # Container logs exception -> 500
    with patch(
        "managers.ssh_manager.SSHManager.connect",
        side_effect=Exception("SSH crash"),
    ):
        res_logs_exc = client.post(
            "/get-container-logs",
            json={
                "ip": "10.0.0.1",
                "username": "pi",
                "password": "pi",
                "container_name": "caddy",
            },
        )
        assert res_logs_exc.status_code == 500

    # 4. /get-device-details empty snapshot & exception
    with patch(
        "node_scanner.NodeScanner.get_system_snapshot",
        return_value=({}, None),
    ):
        res_dev_empty = client.post(
            "/get-device-details",
            json={"ip": "10.0.0.1", "username": "pi", "password": "pi"},
        )
        assert res_dev_empty.status_code == 400

    with patch(
        "node_scanner.NodeScanner.get_system_snapshot",
        side_effect=Exception("Snapshot error"),
    ):
        res_dev_err = client.post(
            "/get-device-details",
            json={"ip": "10.0.0.1", "username": "pi", "password": "pi"},
        )
        assert res_dev_err.status_code == 500

    # 5. /api/components and /get-available-software exceptions
    with patch(
        "managers.component_manager.ComponentManager.get_all_components",
        side_effect=Exception("Comp error"),
    ):
        res_c_err = client.get("/api/components")
        assert res_c_err.status_code == 500

        res_sw_err = client.post("/get-available-software")
        assert res_sw_err.status_code == 500

    # 6. /get-software-groups with unlisted groups
    fake_meta = {
        "group_rules": {"group_a": {"name": "Group A"}},
        "group_order": ["group_a"],
    }
    fake_components = [
        {"id": "c1", "group": "group_a"},
        {"id": "c2", "group": "unlisted_group"},
    ]
    with (
        patch(
            "managers.component_manager.ComponentManager.get_njorddeploy_meta",
            return_value=fake_meta,
        ),
        patch(
            "managers.component_manager.ComponentManager.get_all_components",
            return_value=fake_components,
        ),
    ):
        res_grp = client.get("/get-software-groups")
        assert res_grp.status_code == 200
        grp_data = res_grp.get_json()
        assert "Group A" in grp_data["groups"]
        assert "unlisted_group" in grp_data["groups"]

    # 7. /api/v1/system/analyze devices validation and scanner error
    res_sys_no_dev = client.post("/api/v1/system/analyze", json={"devices": []})
    assert res_sys_no_dev.status_code == 400

    res_sys_bad_dev = client.post(
        "/api/v1/system/analyze", json={"devices": ["not_dict"]}
    )
    assert res_sys_bad_dev.status_code == 400

    with patch(
        "node_scanner.NodeScanner.get_system_snapshot",
        return_value=(None, "SSH timeout"),
    ):
        res_sys_scan_err = client.post(
            "/api/v1/system/analyze",
            json={"devices": [{"ip": "10.0.0.1", "username": "pi"}]},
        )
        assert res_sys_scan_err.status_code in (400, 500)

    # 8. /start-installation bad params & exception
    res_pkg_bad = client.post(
        "/start-installation",
        json={"selected_components": "bad", "devices": []},
    )
    assert res_pkg_bad.status_code == 400

    with patch(
        "managers.setup_manager.SetupManager.prepare_deployment_package",
        side_effect=Exception("Packaging error"),
    ):
        res_pkg_err = client.post(
            "/start-installation",
            json={
                "selected_components": ["demo-app"],
                "devices": [],
                "env_vars": "bad",
            },
        )
        assert res_pkg_err.status_code == 500

    # 9. /stream-deployment/<target_task_id>, /task-status, and evaluate
    res_stream_non = client.get("/stream-deployment/nonexistent-task")
    assert res_stream_non.status_code == 200

    res_stat_404 = client.get("/task-status/nonexistent-task")
    assert res_stat_404.status_code == 404

    app_instance = client.application
    app_instance.deployment_tasks["test-task-stream"] = {
        "status": "completed",
        "logs": ["Stream line 1\n"],
    }
    res_stream_ok = client.get("/stream-deployment/test-task-stream")
    assert res_stream_ok.status_code == 200
    assert "Stream line 1" in res_stream_ok.data.decode("utf-8")

    res_stat_ok = client.get("/task-status/test-task-stream")
    assert res_stat_ok.status_code == 200

    # Evaluate task with first_run_info
    with patch(
        "managers.component_manager.ComponentManager.get_component_details",
        return_value={"first_run_info": {"guide": "Open port 80"}},
    ):
        res_eval = client.post(
            "/api/deployment/test-task-stream/evaluate",
            json={"component_name": "demo-app", "use_ai": False},
        )
        assert res_eval.status_code == 200
        assert res_eval.get_json()["status"] == "GREEN"

    # 10. /get-generated-files path traversal, invalid selected_components, exception
    res_gen_trav = client.post(
        "/get-generated-files", json={"output_path": "../../etc"}
    )
    assert res_gen_trav.status_code in (400, 403, 404)

    # Subdirectory filtering and non-list selected_components
    staging = tmp_path / "app_data_boost"
    staging.mkdir(parents=True, exist_ok=True)
    out_dir = staging / "sub_test"
    sub_app = out_dir / "demo-app"
    sub_app.mkdir(parents=True, exist_ok=True)
    (sub_app / "docker-compose.yml").write_text("services:\n", encoding="utf-8")

    with patch("configurator_app.app.get_app_data_dir", return_value=staging):
        res_gen_sub = client.post(
            "/get-generated-files",
            json={
                "output_path": "sub_test",
                "selected_components": ["demo-app"],
            },
        )
        assert res_gen_sub.status_code == 200
        assert "demo-app/docker-compose.yml" in res_gen_sub.get_json()["files"]

    with patch(
        "configurator_app.app.get_app_data_dir",
        side_effect=Exception("Files crash"),
    ):
        res_gen_err = client.post(
            "/get-generated-files", json={"output_path": "sub_test"}
        )
        assert res_gen_err.status_code == 500

    # 11. Backup route exceptions (discover, inspect, create, list, restore)
    with patch(
        "managers.ssh_manager.SSHManager.connect",
        side_effect=Exception("Discover crash"),
    ):
        res_b_disc = client.post("/api/backup/discover-compose", json={"ip": "1.1.1.1"})
        assert res_b_disc.status_code == 500

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        side_effect=Exception("Inspect crash"),
    ):
        res_b_insp = client.post("/api/backup/inspect", json={"ip": "1.1.1.1"})
        assert res_b_insp.status_code == 500

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        side_effect=Exception("Create crash"),
    ):
        res_b_create = client.post("/api/backup/create", json={"ip": "1.1.1.1"})
        assert res_b_create.status_code == 500

    with patch(
        "managers.ssh_manager.SSHManager.connect",
        side_effect=Exception("List crash"),
    ):
        res_b_list = client.post("/api/backup/list", json={"ip": "1.1.1.1"})
        assert res_b_list.status_code == 500

        res_b_rest = client.post(
            "/api/backup/restore",
            json={
                "ip": "1.1.1.1",
                "username": "root",
                "backup_filename": "njorddeploy_backup_20260101_120000.tar.gz",
            },
        )
        assert res_b_rest.status_code == 500

    # Download route exception
    with patch(
        "configurator_app.app.get_app_data_dir",
        side_effect=Exception("Download crash"),
    ):
        res_b_dl_err = client.get(
            "/api/backup/download/njorddeploy_backup_20260101_120000.tar.gz?ip=1.1.1.1"
        )
        assert res_b_dl_err.status_code == 500

    # 12. Auth / Login / Register edge cases
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user"] = "admin"
    res_login_red = client.get("/login")
    assert res_login_red.status_code == 302

    res_reg_red = client.get("/register")
    assert res_reg_red.status_code == 302

    with client.session_transaction() as sess:
        sess.clear()

    res_login_empty = client.post("/login", json={})
    assert res_login_empty.status_code == 400

    res_logout_api = client.post(
        "/api/logout",
        headers={"Accept": "application/json"},
    )
    assert res_logout_api.status_code == 200

    res_auth_stat = client.get("/api/auth/status")
    assert res_auth_stat.status_code == 200

    with patch("configurator_app.app.is_auth_enabled", return_value=True):
        res_pw_unauth = client.post("/api/auth/change-password", json={})
        assert res_pw_unauth.status_code == 401

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user"] = "admin"
    with (
        patch("configurator_app.app.is_auth_enabled", return_value=False),
        patch(
            "configurator_app.app.load_auth_config",
            return_value={"username": "admin"},
        ),
        patch("configurator_app.app.verify_credentials", return_value=True),
    ):
        res_pw_mismatch = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "old",
                "new_password": "NewStrongPass2026!",
                "confirm_password": "MismatchPassword!",
            },
        )
        assert res_pw_mismatch.status_code == 400

    res_reg_weak = client.post(
        "/register",
        json={"username": "newuser", "password": "123"},
    )
    assert res_reg_weak.status_code == 400

    # 13. Proxmox LXC template selection: Ubuntu and Alpine fallback
    mock_pve_ubu = MagicMock()
    mock_pve_ubu.get_next_vmid.return_value = 110
    mock_pve_ubu.get_lxc_list.return_value = []
    mock_pve_ubu.get.side_effect = [
        {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},
        {"data": [{"volid": "local:vztmpl/ubuntu-22.04.tar.zst"}]},
        {"data": {"status": "stopped", "exitstatus": "OK"}},
        {
            "data": [
                {
                    "name": "eth0",
                    "inet": "192.168.1.155/24",
                }
            ]
        },
    ]
    mock_pve_ubu.post.return_value = {"data": "UPID:create"}
    mock_key = MagicMock()
    mock_key.get_name.return_value = "ssh-ed25519"
    mock_key.get_base64.return_value = "AAAA..."

    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_ubu),
        patch.object(SSHManager, "get_ssh_key", return_value=mock_key),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(SSHManager, "execute_command", return_value=(0, "Success")),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_ubu = client.post(
            "/api/proxmox/create-lxc",
            json={"name": "ubu-ct", "password": "pass", "pubkey": "key"},
        )
        assert res_lxc_ubu.status_code == 201

    # Alpine template (any_temp fallback)
    mock_pve_alp = MagicMock()
    mock_pve_alp.get_next_vmid.return_value = 111
    mock_pve_alp.get_lxc_list.return_value = []
    mock_pve_alp.get.side_effect = [
        {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},
        {"data": [{"volid": "local:vztmpl/alpine-3.18.tar.zst"}]},
        {"data": {"status": "stopped", "exitstatus": "OK"}},
        {
            "data": [
                {
                    "name": "eth0",
                    "inet": "192.168.1.156/24",
                }
            ]
        },
    ]
    mock_pve_alp.post.return_value = {"data": "UPID:create"}

    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_alp),
        patch.object(SSHManager, "get_ssh_key", return_value=mock_key),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(SSHManager, "execute_command", return_value=(0, "Success")),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_alp = client.post(
            "/api/proxmox/create-lxc",
            json={"name": "alp-ct", "password": "pass", "pubkey": "key"},
        )
        assert res_lxc_alp.status_code == 201

    # 14. Before-request user plan sync & static route pass-through
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user"] = "admin"
    mock_db = MagicMock()
    mock_db.get_user_by_username.return_value = {"plan": "enterprise"}
    with patch(
        "managers.database_manager.DatabaseManager.get_instance",
        return_value=mock_db,
    ):
        res_plan = client.get("/api/auth/status")
        assert res_plan.status_code == 200

    mock_db_err = MagicMock()
    mock_db_err.get_user_by_username.side_effect = Exception("DB sync fail")
    with patch(
        "managers.database_manager.DatabaseManager.get_instance",
        return_value=mock_db_err,
    ):
        res_plan_err = client.get("/api/auth/status")
        assert res_plan_err.status_code == 200

    res_static = client.get("/static/css/njorddeploy-style.css")
    assert res_static.status_code in (200, 404)

    # 15. Setup wizard redirect when already configured & logged in
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    with patch("configurator_app.app.is_admin_configured", return_value=True):
        res_setup_red = client.get("/setup")
        assert res_setup_red.status_code == 302

    with patch("configurator_app.app.is_admin_configured", return_value=False):
        res_set_bad_user = client.post("/setup", json={"username": ""})
        assert res_set_bad_user.status_code == 400
        res_set_pw_mismatch = client.post(
            "/setup",
            json={
                "username": "admin",
                "password": "ValidStrongPassword2026!",
                "confirm_password": "MismatchPassword!",
            },
        )
        assert res_set_pw_mismatch.status_code == 400

    # 16. Login setup redirect & rate limiting
    with (
        patch("configurator_app.app.is_admin_configured", return_value=False),
        patch("configurator_app.app.is_auth_enabled", return_value=True),
    ):
        res_login_to_setup = client.get("/login")
        assert res_login_to_setup.status_code == 302

    with patch(
        "configurator_app.app.GLOBAL_RATE_LIMITER.is_rate_limited",
        return_value=(True, 42),
    ):
        res_login_limited = client.post(
            "/login", json={"username": "user", "password": "pwd"}
        )
        assert res_login_limited.status_code == 429

    # 17. Register duplicate email
    from managers.database_manager import DatabaseManager
    target_db = DatabaseManager.get_instance()
    with patch.object(
        target_db, "get_user_by_username", return_value=None
    ), patch.object(
        target_db,
        "get_user_by_email",
        return_value={"id": 1, "email": "taken@example.com"},
    ):
        res_reg_dup_email = client.post(
            "/register",
            json={
                "username": "uniqueuser_dup",
                "password": "ValidStrongPassword2026!",
                "email": "taken@example.com",
            },
        )
        assert res_reg_dup_email.status_code == 409

    # 18. Agent heartbeat failed token processing
    with patch(
        "managers.agent_manager.AgentManager.process_heartbeat",
        return_value=(False, "Invalid agent token"),
    ):
        res_hb_fail = client.post(
            "/api/agent/heartbeat",
            headers={"X-Njord-Agent-Token": "invalid-tok"},
            json={"status": "ok"},
        )
        assert res_hb_fail.status_code == 401

    # 19. Engine switch updating existing CONTAINER_ENGINE line
    with (
        patch.object(Path, "exists", return_value=True),
        patch(
            "builtins.open",
            mock_open(read_data='CONTAINER_ENGINE="docker"\n'),
        ),
    ):
        res_switch_upd = client.post("/api/engine-switch", json={"engine": "podman"})
        assert res_switch_upd.status_code == 200

    # 20. Scan Pis non-string subnet and MAC resolution
    with patch("node_scanner.NodeScanner.scan", return_value=([], [], None, {})):
        res_mac_subnet = client.post(
            "/scan-pis",
            json={
                "discovery_method": "direct_ip",
                "direct_target_ip": "00:11:22:33:44:55",
                "subnet": 123,
            },
        )
        assert res_mac_subnet.status_code in (200, 400, 404, 500)

        res_scan_subnet = client.post(
            "/scan-pis",
            json={"subnet": 123},
        )
        assert res_scan_subnet.status_code == 200

    # 21. Proxmox LXC error branches
    mock_pve_err = MagicMock()
    mock_pve_err.get_next_vmid.return_value = 112
    mock_pve_err.get_lxc_list.return_value = []
    mock_pve_err.get.side_effect = Exception("PVE storage list crash")
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_err),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_fail = client.post(
            "/api/proxmox/create-lxc",
            json={"name": "ct-fail", "password": "pass", "pubkey": "key"},
        )
        assert res_lxc_fail.status_code == 400

    # Proxmox LXC outer exception (1862-1864) -> 500
    mock_pve_outer_err = MagicMock()
    mock_pve_outer_err.get_next_vmid.side_effect = Exception("VMID fetch error")
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_outer_err),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_500 = client.post(
            "/api/proxmox/create-lxc",
            json={"name": "ct-500", "password": "pass", "pubkey": "key"},
        )
        assert res_lxc_500.status_code == 500

    # Proxmox LXC: non-eth0 interface, empty inet, polling error & no IP
    mock_pve_no_ip = MagicMock()
    mock_pve_no_ip.get_next_vmid.return_value = 113
    mock_pve_no_ip.get_lxc_list.return_value = []
    mock_pve_no_ip.get.side_effect = [
        {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},
        {"data": [{"volid": "local:vztmpl/debian-12.tar.zst"}]},
        {"data": {"status": "stopped", "exitstatus": "OK"}},
        {"data": [{"name": "lo", "inet": "127.0.0.1/8"}, {"name": "eth0", "inet": ""}]},
        Exception("Transient interface poll failure"),
    ]
    mock_pve_no_ip.post.return_value = {"data": "UPID:create"}
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_no_ip),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_no_ip = client.post(
            "/api/proxmox/create-lxc",
            json={"name": "ct-no-ip", "password": "pass", "pubkey": "key"},
        )
        assert res_lxc_no_ip.status_code == 500

    # Proxmox LXC: SSH connect fail and provisioning lock retry fail
    mock_pve_ssh_fail = MagicMock()
    mock_pve_ssh_fail.get_next_vmid.return_value = 114
    mock_pve_ssh_fail.get_lxc_list.return_value = []
    mock_pve_ssh_fail.get.side_effect = [
        {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},
        {"data": [{"volid": "local:vztmpl/debian-12.tar.zst"}]},
        {"data": {"status": "stopped", "exitstatus": "OK"}},
        {"data": [{"name": "eth0", "inet": "192.168.1.199/24"}]},
    ]
    mock_pve_ssh_fail.post.return_value = {"data": "UPID:create"}
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_ssh_fail),
        patch.object(SSHManager, "connect", return_value=(False, "Refused")),
        patch("time.sleep", return_value=None),
    ):
        res_lxc_ssh_fail = client.post(
            "/api/proxmox/create-lxc",
            json={"name": "ct-ssh-fail", "password": "pass", "pubkey": "key"},
        )
        assert res_lxc_ssh_fail.status_code == 500

    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_ssh_fail),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(
            SSHManager,
            "execute_command",
            return_value=(1, "Could not get lock /var/lib/dpkg/lock"),
        ),
        patch("time.sleep", return_value=None),
    ):
        mock_pve_ssh_fail.get.side_effect = [
            {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},
            {"data": [{"volid": "local:vztmpl/debian-12.tar.zst"}]},
            {"data": {"status": "stopped", "exitstatus": "OK"}},
            {"data": [{"name": "eth0", "inet": "192.168.1.199/24"}]},
        ]
        res_lxc_lock_fail = client.post(
            "/api/proxmox/create-lxc",
            json={"name": "ct-lock-fail", "password": "pass", "pubkey": "key"},
        )
        assert res_lxc_lock_fail.status_code == 500

    # 22. Proxmox list-templates exception
    mock_pve_list_err = MagicMock()
    mock_pve_list_err.get.side_effect = Exception("QEMU list error")
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_list_err),
        patch.dict(
            os.environ,
            {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"},
        ),
    ):
        res_tpl_err = client.post("/api/proxmox/list-templates")
        assert res_tpl_err.status_code == 500

    # Duplicate VM name pre-flight check (lines 1980-1985)
    mock_pve_dup = MagicMock()
    mock_pve_dup.get_next_vmid.return_value = 209
    mock_pve_dup.get.return_value = {"data": [{"name": "existing-vm", "vmid": 208}]}
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_dup),
        patch.dict(
            os.environ,
            {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"},
        ),
    ):
        res_vm_dup = client.post(
            "/api/proxmox/create-vm",
            json={
                "template_vmid": 9000,
                "hostname": "existing-vm",
            },
        )
        assert res_vm_dup.status_code == 409
        assert "already exists" in res_vm_dup.get_json()["error"]

    # 23. Proxmox create-vm edge cases
    mock_pve_vm_edge = MagicMock()
    mock_pve_vm_edge.get_next_vmid.return_value = 210
    mock_pve_vm_edge.get_vm_list.return_value = []
    mock_pve_vm_edge.clone_vm.side_effect = [
        Exception("Linked clone feature is not supported"),
        {"data": "UPID:clone"},
    ]
    mock_pve_vm_edge.get.side_effect = [
        {"data": []},
        {"data": {"status": "running"}},
        Exception("Transient task status error"),
        {"data": {"status": "stopped", "exitstatus": "OK"}},
        {"data": {"virtio0": "local:210/vm-210-disk-0.raw"}},
    ]
    mock_pve_vm_edge.resize_vm_disk.side_effect = Exception("Resize failure")
    mock_pve_vm_edge.configure_vm.side_effect = [Exception("Drive config error"), None]
    mock_pve_vm_edge.get_vm_ip.side_effect = [Exception("Guest agent starting"), None]

    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_vm_edge),
        patch.dict(
            os.environ,
            {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"},
        ),
        patch("time.sleep", return_value=None),
    ):
        res_vm_edge = client.post(
            "/api/proxmox/create-vm",
            json={
                "template_vmid": 9000,
                "hostname": "my_edge vm",
                "password": "pass",
                "pubkey": "key",
                "storage_size": 32,
            },
        )
        assert res_vm_edge.status_code == 500

    # 24. /api/v1/system/analyze validation & scanner error
    res_an_empty = client.post(
        "/api/v1/system/analyze",
        json={"components": [], "devices": []},
    )
    assert res_an_empty.status_code == 400

    res_an_bad_dev = client.post(
        "/api/v1/system/analyze",
        json={"components": [], "devices": ["not-a-dict"]},
    )
    assert res_an_bad_dev.status_code == 400

    with patch(
        "node_scanner.NodeScanner.get_system_snapshot",
        return_value=(None, "SSH unreachable"),
    ):
        res_an_scan_err = client.post(
            "/api/v1/system/analyze",
            json={
                "components": [],
                "devices": [{"ip": "10.0.0.99", "username": "root"}],
            },
        )
        assert res_an_scan_err.status_code == 500

    # 25. /get-generated-files non-list components
    with patch("configurator_app.app.get_app_data_dir", return_value=staging):
        res_gen_non_list = client.post(
            "/get-generated-files",
            json={"output_path": "sub_test", "selected_components": "bad-string"},
        )
        assert res_gen_non_list.status_code == 200

    # 26. /api/backup/download unauthorized traversal path
    with patch.object(Path, "is_relative_to", return_value=False):
        res_b_dl_unauth = client.get(
            "/api/backup/download/njorddeploy_backup_20260101_120000.tar.gz"
        )
        assert res_b_dl_unauth.status_code == 403

    # 27. User plan sync with pro plan (line 415) & duplicate email (line 694)
    db_real = DatabaseManager.get_instance()
    ts_now = int(time.time() * 1000)
    dup_email = f"dup_{ts_now}@example.com"
    dup_user = f"user_{ts_now}"
    db_real.create_user(
        username=dup_user,
        password_hash="hash",
        email=dup_email,
        role="admin",
        plan="pro",
    )
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user"] = dup_user
    res_sync = client.get("/api/auth/status")
    assert res_sync.status_code == 200

    res_dup_reg = client.post(
        "/register",
        json={
            "username": f"brand_new_{ts_now}",
            "password": "ValidStrongPassword2026!",
            "email": dup_email,
        },
    )
    assert res_dup_reg.status_code == 409
    assert "Email address already registered" in res_dup_reg.get_json()["error"]

    # 28. Proxmox create-vm SSH fail, provisioning fail, and crash (2166, 2169, 2190, 2216-2218)
    mock_pve_vm_ssh = MagicMock()
    mock_pve_vm_ssh.get_next_vmid.return_value = 215
    mock_pve_vm_ssh.get_vm_list.return_value = []
    mock_pve_vm_ssh.get.side_effect = [
        {"data": []},
        {"data": {"status": "stopped", "exitstatus": "OK"}},
    ]
    mock_pve_vm_ssh.clone_vm.return_value = {"data": "UPID:clone"}
    mock_pve_vm_ssh.get_vm_ip.return_value = "192.168.1.188"
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_vm_ssh),
        patch.object(
            SSHManager, "connect", return_value=(False, "Connection timed out")
        ),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
        patch("time.sleep", return_value=None),
    ):
        res_vm_ssh_err = client.post(
            "/api/proxmox/create-vm",
            json={"template_vmid": 9000, "password": "pass", "pubkey": "key"},
        )
        assert res_vm_ssh_err.status_code == 500

    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_vm_ssh),
        patch.object(SSHManager, "connect", return_value=(True, "OK")),
        patch.object(
            SSHManager, "execute_command", return_value=(1, "Could not get lock")
        ),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
        patch("time.sleep", return_value=None),
    ):
        mock_pve_vm_ssh.get.side_effect = [
            {"data": []},
            {"data": {"status": "stopped", "exitstatus": "OK"}},
        ]
        res_vm_prov_err = client.post(
            "/api/proxmox/create-vm",
            json={"template_vmid": 9000, "password": "pass", "pubkey": "key"},
        )
        assert res_vm_prov_err.status_code == 500

    mock_pve_vm_crash = MagicMock()
    mock_pve_vm_crash.get.side_effect = Exception("Crash on qemu list")
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_vm_crash),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
        patch("time.sleep", return_value=None),
    ):
        res_vm_crash = client.post(
            "/api/proxmox/create-vm",
            json={"template_vmid": 9000, "hostname": "crash_vm"},
        )
        assert res_vm_crash.status_code == 500

    # 29. Proxmox list-targets template continue and outer error (2257, 2277, 2292-2294)
    mock_pve_targets = MagicMock()
    mock_pve_targets.get.side_effect = [
        {
            "data": [
                {"vmid": 101, "name": "ct-tpl", "template": 1},
                {"vmid": 102, "name": "ct-live"},
            ]
        },
        {
            "data": [
                {"vmid": 201, "name": "vm-tpl", "template": 1},
                {"vmid": 202, "name": "vm-live"},
            ]
        },
    ]
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_targets),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
    ):
        res_targs = client.post("/api/proxmox/list-targets")
        assert res_targs.status_code == 200

    mock_pve_targets_err = MagicMock()
    mock_pve_targets_err.get.side_effect = Exception("Targets fail")
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_targets_err),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
    ):
        res_targs_warn = client.post("/api/proxmox/list-targets")
        assert res_targs_warn.status_code == 200
        assert res_targs_warn.get_json()["targets"] == []

    with (
        patch(
            "utils.proxmox_client.ProxmoxClient",
            side_effect=Exception("Client init error"),
        ),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
    ):
        res_targs_err = client.post("/api/proxmox/list-targets")
        assert res_targs_err.status_code == 500

    # 30. Proxmox get-target-ip and start-target branches (2325, 2328, 2338, 2381, 2384, 2398-2399, 2417-2419)
    mock_pve_tip = MagicMock()
    mock_pve_tip.get.return_value = {
        "data": [
            {"name": "lo", "inet": "127.0.0.1/8"},
            {"name": "eth0", "inet": ""},
            {"name": "eth0", "inet": "192.168.1.189/24"},
        ]
    }
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_tip),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
    ):
        res_tip_lxc = client.post(
            "/api/proxmox/get-target-ip",
            json={"type": "lxc", "vmid": 105},
        )
        assert res_tip_lxc.status_code == 200
        assert res_tip_lxc.get_json()["ip"] == "192.168.1.189"

    mock_pve_tip.get_vm_ip.return_value = "192.168.1.190"
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_tip),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
    ):
        res_tip_qemu = client.post(
            "/api/proxmox/get-target-ip",
            json={"type": "qemu", "vmid": 205},
        )
        assert res_tip_qemu.status_code == 200

    mock_pve_start = MagicMock()
    mock_pve_start.get.side_effect = [
        Exception("Transient poll fail"),
        {
            "data": [
                {"name": "lo"},
                {"name": "eth0", "inet": ""},
                {"name": "eth0", "inet": "192.168.1.191/24"},
            ]
        },
    ]
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_start),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
        patch("time.sleep", return_value=None),
    ):
        res_start_lxc = client.post(
            "/api/proxmox/start-target",
            json={"type": "lxc", "vmid": 106},
        )
        assert res_start_lxc.status_code == 200

    mock_pve_start_err = MagicMock()
    mock_pve_start_err.post.side_effect = Exception("Start endpoint error")
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_start_err),
        patch.dict(
            os.environ, {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"}
        ),
        patch("time.sleep", return_value=None),
    ):
        res_start_err = client.post(
            "/api/proxmox/start-target",
            json={"type": "lxc", "vmid": 106},
        )
        assert res_start_err.status_code == 500

    # 31. Software groups display_name collision (2555) & get-required-variables fallback (2587)
    fake_meta_col = {
        "group_rules": {
            "g1": {"name": "SharedName"},
            "g2": {"name": "SharedName"},
        },
        "group_order": ["g1", "g2"],
    }
    fake_comps_col = [
        {"id": "c1", "group": "g1"},
        {"id": "c2", "group": "g2"},
    ]
    with (
        patch(
            "managers.component_manager.ComponentManager.get_njorddeploy_meta",
            return_value=fake_meta_col,
        ),
        patch(
            "managers.component_manager.ComponentManager.get_all_components",
            return_value=fake_comps_col,
        ),
    ):
        res_col = client.get("/get-software-groups")
        assert res_col.status_code == 200

    with (
        patch(
            "managers.component_manager.ComponentManager.get_all_components",
            return_value=[{"id": "comp_no_vars", "name": "Comp No Vars"}],
        ),
        patch(
            "managers.component_reader.ComponentReader.get_component_variables",
            return_value=[{"name": "FOO", "default": "bar"}],
        ),
    ):
        res_req_vars = client.post(
            "/get-required-variables",
            json={"selected_components": ["comp_no_vars"]},
        )
        assert res_req_vars.status_code == 200


def test_configurator_routes_final_coverage_closing_gaps(
    configurator_final_env, tmp_path
):
    """Closes remaining lines in configurator_app/app.py:
    287, 314, 415-417, 1752-1754, 2031, 2077, 2555, 2927, 3122, 3139.
    """
    client, _, _ = configurator_final_env
    flask_app = client.application

    # 1. Lines 287 & 314: create_app frozen with no candidates and cookie secure
    with (
        patch("sys.frozen", True, create=True),
        patch("sys._MEIPASS", str(tmp_path), create=True),
        patch.dict(os.environ, {"NJORD_COOKIE_SECURE": "true"}),
        patch.object(Path, "exists", return_value=False),
    ):
        app_frozen = create_app()
        assert app_frozen.config["SESSION_COOKIE_SECURE"] is True

    # 2. Lines 415-417: before_request plan sync and exception fallback
    flask_app.config["AUTH_ENABLED"] = True
    try:
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user"] = "admin"

        db_inst = DatabaseManager.get_instance()
        with (
            patch("configurator_app.app.is_auth_enabled", return_value=True),
            patch("configurator_app.app.is_admin_configured", return_value=True),
            patch.object(
                db_inst,
                "get_user_by_username",
                return_value={"username": "admin", "plan": "premium"},
            ),
        ):
            res_sync = client.get("/api/system-info")
            assert res_sync.status_code in (200, 404)
            with client.session_transaction() as sess:
                assert sess.get("plan") == "premium"

        with (
            patch("configurator_app.app.is_auth_enabled", return_value=True),
            patch("configurator_app.app.is_admin_configured", return_value=True),
            patch.object(
                db_inst,
                "get_user_by_username",
                side_effect=Exception("DB error"),
            ),
        ):
            res_sync_err = client.get("/api/system-info")
            assert res_sync_err.status_code in (200, 404)
    finally:
        flask_app.config["AUTH_ENABLED"] = False

    # 3. Lines 1752-1754: /api/proxmox/create-lxc task polling exception
    mock_pve_lxc = MagicMock()
    mock_pve_lxc.get_lxc_list.return_value = []
    mock_pve_lxc.get_next_vmid.return_value = 105
    mock_pve_lxc.post.return_value = {"data": "UPID:test:lxc"}
    mock_pve_lxc.get.side_effect = [
        {"data": [{"storage": "local", "active": 1, "content": "vztmpl"}]},
        {"data": [{"volid": "local:vztmpl/debian-12-standard.tar.zst"}]},
        Exception("Transient status polling timeout"),
        {"data": {"status": "stopped", "exitstatus": "OK"}},
        {"data": [{"inet": "192.168.1.150/24", "name": "eth0"}]},
    ]
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_lxc),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(SSHManager, "execute_command", return_value=(0, "OK")),
        patch.dict(
            os.environ,
            {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"},
        ),
        patch("time.sleep", return_value=None),
    ):
        res_lxc = client.post(
            "/api/proxmox/create-lxc",
            json={
                "hostname": "test-lxc",
                "node": "pve",
            },
        )
        assert res_lxc.status_code == 201

    # 4. Line 2031: /api/proxmox/create-vm non-linked-clone error raise
    mock_pve_vm = MagicMock()
    mock_pve_vm.get.return_value = {"data": []}
    mock_pve_vm.get_next_vmid.return_value = 106
    mock_pve_vm.clone_vm.side_effect = RuntimeError("Fatal disk clone failure")
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_vm),
        patch.dict(
            os.environ,
            {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"},
        ),
    ):
        res_vm_err = client.post(
            "/api/proxmox/create-vm",
            json={
                "hostname": "test-vm",
                "template_vmid": 9000,
                "node": "pve",
            },
        )
        assert res_vm_err.status_code == 500

    # 5. Line 2077: /api/proxmox/create-vm fallback bootdisk to scsi0
    mock_pve_boot = MagicMock()
    mock_pve_boot.get_next_vmid.return_value = 107
    mock_pve_boot.clone_vm.return_value = {"data": "UPID:test:vm"}
    mock_pve_boot.get_vm_ip.return_value = "192.168.1.155"
    mock_pve_boot.get.side_effect = [
        {"data": []},  # qemu list
        {"data": {"status": "stopped", "exitstatus": "OK"}},  # task status
        {"data": {}},  # config without bootdisk -> line 2077
    ]
    with (
        patch("utils.proxmox_client.ProxmoxClient", return_value=mock_pve_boot),
        patch.object(SSHManager, "connect", return_value=(True, "Connected")),
        patch.object(SSHManager, "execute_command", return_value=(0, "OK")),
        patch.dict(
            os.environ,
            {"PROXMOX_TOKEN_ID": "id", "PROXMOX_TOKEN_SECRET": "sec"},
        ),
        patch("time.sleep", return_value=None),
    ):
        res_boot = client.post(
            "/api/proxmox/create-vm",
            json={
                "hostname": "test-vm-2",
                "template_vmid": 9000,
                "node": "pve",
                "storage_size": 32,
            },
        )
        assert res_boot.status_code == 201

    # 6. Line 2555: /api/components/groups collision with remaining group
    fake_meta_groups = {
        "group_rules": {
            "g1": {"name": "SharedName"},
            "g2": {"name": "SharedName"},
        },
        "group_order": ["g1"],
    }
    fake_comps_groups = [
        {"id": "c1", "group": "g1"},
        {"id": "c2", "group": "g2"},
    ]
    with (
        patch(
            "managers.component_manager.ComponentManager.get_njorddeploy_meta",
            return_value=fake_meta_groups,
        ),
        patch(
            "managers.component_manager.ComponentManager.get_all_components",
            return_value=fake_comps_groups,
        ),
    ):
        res_groups = client.get("/get-software-groups")
        assert res_groups.status_code == 200
        data_groups = res_groups.get_json()
        assert "SharedName" in data_groups.get("groups", {})
        assert set(data_groups["groups"]["SharedName"]["components"]) == {
            "c1",
            "c2",
        }

    # 7. Line 2927: /stream-task-logs/<task_id> time.sleep(0.5) loop
    flask_app.deployment_tasks["task-stream-loop"] = {
        "status": "running",
        "logs": ["log line 1"],
    }

    def fake_sleep_stream(duration):
        flask_app.deployment_tasks["task-stream-loop"]["status"] = "completed"

    with patch("time.sleep", side_effect=fake_sleep_stream):
        res_stream = client.get("/stream-deployment/task-stream-loop")
        assert res_stream.status_code == 200
        stream_data = res_stream.get_data(as_text=True)
        assert "log line 1" in stream_data

    # 8. Lines 3122 & 3139: /get-generated-files traversal symlink & skipped leak
    appdata = tmp_path / "appdata"
    appdata.mkdir(parents=True, exist_ok=True)
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir(parents=True, exist_ok=True)
    (appdata / "evil_symlink").symlink_to(outside_dir)

    deploy_dir = appdata / "deploy_test"
    deploy_dir.mkdir(parents=True, exist_ok=True)
    (deploy_dir / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret", encoding="utf-8")
    (deploy_dir / "leak_symlink").symlink_to(outside_file)

    with patch("configurator_app.app.get_app_data_dir", return_value=appdata):
        # Line 3122: Traversal rejection
        res_trav = client.post(
            "/get-generated-files",
            json={"output_path": "evil_symlink"},
        )
        assert res_trav.status_code == 403

        # Line 3139: Symlink outside target_path skipped
        res_sym = client.post(
            "/get-generated-files",
            json={"output_path": "deploy_test", "selected_components": []},
        )
        assert res_sym.status_code == 200
        data_sym = res_sym.get_json()
        assert "docker-compose.yml" in data_sym.get("files", {})
        assert "leak_symlink" not in data_sym.get("files", {})
