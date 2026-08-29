import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.proxmox_release_test_runner import (
    download_github_release,
    run_linux_lxc_test,
    run_linux_vm_test,
    run_macos_vm_test,
    run_windows_vm_test,
    save_test_report,
    wait_for_ip,
    wait_for_lxc_ip,
    wait_for_proxmox_task,
)


@patch("time.sleep", return_value=None)
def test_wait_for_proxmox_task_success(_mock_sleep):
    client = MagicMock()
    client.get.return_value = {"data": {"status": "stopped", "exitstatus": "OK"}}
    wait_for_proxmox_task(client, "pve", "UPID:pve:123", timeout_seconds=5)
    client.get.assert_called_with("nodes/pve/tasks/UPID:pve:123/status")


@patch("time.sleep", return_value=None)
def test_wait_for_ip_success(_mock_sleep):
    client = MagicMock()
    client.get_vm_ip.return_value = "192.168.178.199"
    ip = wait_for_ip(client, "pve", 104, timeout_seconds=5)
    assert ip == "192.168.178.199"


@patch("time.sleep", return_value=None)
def test_wait_for_lxc_ip_success(_mock_sleep):
    client = MagicMock()
    client.get.return_value = {
        "data": [
            {"name": "lo", "inet": "127.0.0.1/8"},
            {"name": "eth0", "inet": "192.168.178.199/24"},
        ]
    }
    ip = wait_for_lxc_ip(client, "pve", 104, timeout_seconds=5)
    assert ip == "192.168.178.199"


def test_download_github_release(tmp_path):
    with patch("requests.get") as mock_get:
        meta_res = MagicMock()
        meta_res.json.return_value = {
            "assets": [
                {
                    "name": "NjordDeploy-Linux.zip",
                    "browser_download_url": "https://example.com/dl.zip",
                }
            ]
        }
        meta_res.raise_for_status.return_value = None

        import io
        import zipfile

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("NjordDeploy-Linux", b"binary content")
        dl_res = MagicMock()
        dl_res.content = zip_buffer.getvalue()
        dl_res.raise_for_status.return_value = None

        mock_get.side_effect = [meta_res, dl_res]

        bin_file = download_github_release("v0.4.46-Alpha", "linux")
        assert bin_file.name == "NjordDeploy-Linux"
        assert bin_file.exists()


@patch("time.sleep", return_value=None)
def test_run_linux_vm_test_success(_mock_sleep, tmp_path):
    bin_path = tmp_path / "NjordDeploy-Linux"
    bin_path.write_bytes(b"dummy binary")

    client = MagicMock()
    client.get_next_vmid.return_value = 104
    client.clone_vm.return_value = {"data": "UPID:clone"}
    client.get.return_value = {"data": {"status": "stopped", "exitstatus": "OK"}}
    client.get_vm_ip.return_value = "192.168.178.199"

    with patch("scripts.proxmox_release_test_runner.SSHManager") as mock_ssh_cls:
        mock_ssh = MagicMock()
        mock_ssh.connect.return_value = (True, "Connected")
        mock_ssh.upload_content.return_value = (True, "Uploaded")
        mock_ssh.execute_command.return_value = (0, "Success")
        mock_ssh_cls.return_value = mock_ssh

        with patch("requests.get") as mock_http:
            http_res = MagicMock()
            http_res.status_code = 200
            mock_http.return_value = http_res

            success, details = run_linux_vm_test(
                client=client,
                node="pve",
                template_id=902,
                binary_path=bin_path,
                os_name="debian",
                vm_user="testuser",
                vm_pass="testpass",
                ssh_public_key="ssh-ed25519 AAAAC3",
            )
            assert success is True
            assert "Debian VM Test Passed" in details


@patch("time.sleep", return_value=None)
def test_run_linux_lxc_test_success(_mock_sleep, tmp_path):
    bin_path = tmp_path / "NjordDeploy-Linux"
    bin_path.write_bytes(b"dummy binary")

    client = MagicMock()
    client.get_next_vmid.return_value = 104
    client.post.return_value = {"data": "UPID:lxc"}
    client.get.side_effect = [
        {"data": {"status": "stopped", "exitstatus": "OK"}},
        {"data": [{"name": "eth0", "inet": "192.168.178.199/24"}]},
    ]

    with patch("scripts.proxmox_release_test_runner.SSHManager") as mock_ssh_cls:
        mock_ssh = MagicMock()
        mock_ssh.connect.return_value = (True, "Connected")
        mock_ssh.upload_content.return_value = (True, "Uploaded")
        mock_ssh.execute_command.return_value = (0, "Success")
        mock_ssh_cls.return_value = mock_ssh

        with patch("requests.get") as mock_http:
            http_res = MagicMock()
            http_res.status_code = 200
            mock_http.return_value = http_res

            success, details = run_linux_lxc_test(
                client=client,
                node="pve",
                ostemplate="local:vztmpl/debian-12-standard.tar.zst",
                binary_path=bin_path,
                os_name="debian",
                vm_pass="testpass",
                ssh_public_key="ssh-ed25519 AAAAC3",
            )
            assert success is True
            assert "Debian LXC Test Passed" in details


@patch("time.sleep", return_value=None)
def test_run_windows_vm_test_success(_mock_sleep, tmp_path):
    bin_path = tmp_path / "NjordDeployInstaller.exe"
    bin_path.write_bytes(b"dummy exe")

    client = MagicMock()
    client.get_next_vmid.return_value = 104
    client.clone_vm.return_value = {"data": "UPID:clone"}
    client.get.return_value = {"data": {"status": "stopped", "exitstatus": "OK"}}
    client.get_vm_ip.return_value = "192.168.178.199"

    with patch("scripts.proxmox_release_test_runner.SSHManager") as mock_ssh_cls:
        mock_ssh = MagicMock()
        mock_ssh.connect.return_value = (True, "Connected")
        mock_ssh.upload_content.return_value = (True, "Uploaded")
        mock_ssh.execute_command.return_value = (0, "Success")
        mock_ssh_cls.return_value = mock_ssh

        with patch("requests.get") as mock_http:
            http_res = MagicMock()
            http_res.status_code = 200
            mock_http.return_value = http_res

            success, details = run_windows_vm_test(
                client=client,
                node="pve",
                template_id=910,
                binary_path=bin_path,
                vm_user="testuser",
                vm_pass="testpass",
            )
            assert success is True
            assert "Windows VM Test Passed" in details


def test_run_macos_vm_test_skipped_when_no_template():
    client = MagicMock()
    success, details = run_macos_vm_test(
        client=client,
        node="pve",
        template_id=None,
        binary_path=None,
        vm_user="testuser",
        vm_pass="testpass",
    )
    assert success is True
    assert "SKIPPED" in details


def test_save_test_report_and_signal(tmp_path):
    results = [
        ("Debian 12 (VM)", True, "Passed"),
        ("Ubuntu 24.04 (LXC)", True, "Passed"),
        ("Windows (VM)", True, "Passed"),
        ("macOS (OSX-KVM / CI)", True, "Skipped"),
    ]

    with patch.dict(
        "os.environ",
        {
            "SIGNAL_API_URL": "http://127.0.0.1:8080",
            "SIGNAL_SENDER": "+31600000000",
            "SIGNAL_RECIPIENT": "+31611111111",
        },
    ):
        with patch("requests.post") as mock_post:
            mock_res = MagicMock()
            mock_res.status_code = 201
            mock_post.return_value = mock_res

            save_test_report(results, "v0.4.46-Alpha")

            json_file = Path("tests/release_installer_results.json")
            assert json_file.exists()
            data = json.loads(json_file.read_text(encoding="utf-8"))
            last_entry = data[-1]
            assert last_entry["total"] == 4
            assert last_entry["passed"] == 4
