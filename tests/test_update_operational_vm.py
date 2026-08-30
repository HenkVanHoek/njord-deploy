# tests/test_update_operational_vm.py
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from scripts.update_operational_vm import (  # noqa: E402
    get_operational_ip,
    save_obsidian_log,
    send_signal_notification,
    update_operational_environment,
    verify_http_endpoint,
)


def test_get_operational_ip():
    mock_client = MagicMock()
    mock_client.get_vm_ip.return_value = "192.168.178.40"
    ip = get_operational_ip(mock_client, "pve", 140, "192.168.178.1")
    assert ip == "192.168.178.40"

    # Fallback when None
    ip_fallback = get_operational_ip(None, "pve", 140, "192.168.178.99")
    assert ip_fallback == "192.168.178.99"


def test_verify_http_endpoint():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        ok, code = verify_http_endpoint("http://localhost:5001/")
        assert ok is True
        assert code == 200

        mock_get.return_value.status_code = 502
        ok, code = verify_http_endpoint("http://localhost:5001/")
        assert ok is False
        assert code == 502

        mock_get.side_effect = Exception("Connection refused")
        ok, code = verify_http_endpoint("http://localhost:5001/")
        assert ok is False
        assert code is None


def test_send_signal_notification():
    with patch.dict(
        os.environ,
        {
            "SIGNAL_API_URL": "http://mock-signal:8080",
            "SIGNAL_SENDER": "+31600000000",
            "SIGNAL_RECIPIENT": "+31611111111",
        },
    ):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.status = 200
            res = send_signal_notification("Test update alert")
            assert res is True


def test_save_obsidian_log(tmp_path):
    with patch("scripts.update_operational_vm.OBSIDIAN_LOG_DIR", tmp_path):
        results = {
            "Configurator (5001)": (True, 200),
            "Component Editor (5000)": (True, 200),
            "Proxmox Test Suite (5050)": (True, 200),
        }
        saved_file = save_obsidian_log("192.168.178.40", results)
        assert saved_file is not None
        assert saved_file.exists()
        content = saved_file.read_text(encoding="utf-8")
        assert "Operationele NjordDeploy Installatie" in content
        assert "192.168.178.40" in content
        assert "✅ HTTP 200 OK" in content


@patch("scripts.update_operational_vm.SSHManager")
@patch("scripts.update_operational_vm.verify_http_endpoint")
@patch("scripts.update_operational_vm.save_obsidian_log")
def test_update_operational_environment(
    mock_save_log, mock_verify, mock_ssh_class, tmp_path
):
    mock_ssh = MagicMock()
    mock_ssh.connect.return_value = (True, "Connected")
    mock_ssh.execute_command.return_value = (0, "Success")
    mock_sftp = MagicMock()
    mock_ssh.client.open_sftp.return_value = mock_sftp
    mock_ssh_class.return_value = mock_ssh

    mock_verify.return_value = (True, 200)

    # Ensure isolated dist binaries exist in tmp_path
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    for b_name in [
        "NjordDeployConfigurator",
        "NjordDeployEditor",
        "NjordDeployProxmoxTest",
    ]:
        (dist_dir / b_name).write_bytes(b"dummy_binary")

    with patch("scripts.update_operational_vm.project_root", tmp_path):
        with patch(
            "scripts.update_operational_vm.build_binaries_if_needed",
            return_value=True,
        ):
            success = update_operational_environment(
                target_ip="192.168.178.40",
                user="pivm",
                password="testpass",
                force_build=False,
                skip_backup=False,
                signal=False,
                save_log=True,
            )

            assert success is True
            assert mock_ssh.connect.called
            assert mock_sftp.put.called
            assert mock_save_log.called
