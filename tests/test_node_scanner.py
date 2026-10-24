import socket
import subprocess
from unittest.mock import MagicMock, patch

import pytest

# Assuming your file is named node_scanner.py
from node_scanner import (
    NodeScanner,
    get_tailscale_status,
    is_port_open,
    is_raspberry_pi,
    is_supported_sbc,
)


# Fixture for a reusable NodeScanner instance
@pytest.fixture
def scanner():
    """Provides a default NodeScanner instance for tests."""
    return NodeScanner("testuser", "testpass")


class TestIsPortOpen:
    """Tests for the is_port_open utility function."""

    @patch("socket.socket")
    def test_port_is_open(self, mock_socket):
        """Verify it returns True when a connection is successful."""
        mock_instance = mock_socket.return_value
        mock_instance.connect.return_value = None
        assert is_port_open("192.168.1.1", 22) is True

    @patch("socket.socket")
    def test_port_is_closed(self, mock_socket):
        """Verify it returns False when a connection is refused."""
        mock_instance = mock_socket.return_value
        mock_instance.connect.side_effect = ConnectionRefusedError
        assert is_port_open("192.168.1.1", 22) is False


class TestNodeScannerStaticMethods:
    """Tests for the static methods in the NodeScanner class."""

    def test_is_raspberry_pi(self):
        """Test the MAC address checker."""
        assert is_raspberry_pi("B8:27:EB:XX:XX:XX") is True
        assert is_supported_sbc("b8:27:eb:00:00:00") is True
        assert is_supported_sbc("cc:7b:35:11:22:33") is True
        assert is_supported_sbc("00:1e:06:aa:bb:cc") is True
        assert is_supported_sbc("00:00:00:00:00:00") is False

    @patch("socket.socket")
    def test_get_primary_ip_success(self, mock_socket):
        """Test successful IP detection."""
        mock_sock_instance = MagicMock()
        mock_sock_instance.getsockname.return_value = ("192.168.1.10", 12345)
        mock_socket.return_value = mock_sock_instance
        assert NodeScanner.get_primary_ip() == "192.168.1.10"

    @patch("psutil.net_if_addrs")
    @patch("node_scanner.NodeScanner.get_primary_ip")
    def test_detect_subnet_success(self, mock_get_ip, mock_psutil):
        """Test successful subnet detection."""
        mock_get_ip.return_value = "192.168.1.10"
        mock_addr = MagicMock()
        mock_addr.family = socket.AF_INET
        mock_addr.address = "192.168.1.10"
        mock_addr.netmask = "255.255.255.0"
        mock_psutil.return_value = {"eth0": [mock_addr]}
        assert NodeScanner.detect_subnet() == "192.168.1.0/24"


@patch("nmap.PortScanner")
class TestNodeScannerScan:
    """Tests for the main network scan functionality."""

    @patch("shutil.which", return_value="/usr/bin/nmap")
    def test_scan_finds_pi(self, mock_which, mock_nmap, scanner):
        """Test a scan where a Raspberry Pi is found."""
        mock_nmap_instance = mock_nmap.return_value
        mock_nmap_instance.scan.return_value = {
            "scan": {
                "192.168.1.5": {
                    "addresses": {"mac": "B8:27:EB:01:02:03"},
                    "vendor": {"B8:27:EB:01:02:03": "Raspberry Pi Foundation"},
                }
            }
        }
        hosts, _, err, _ = scanner.scan(subnet="192.168.1.0/24")
        assert not err
        assert len(hosts) == 1

    @patch("shutil.which", return_value=None)
    def test_scan_nmap_not_installed(self, mock_which, mock_nmap, scanner):
        """Test that scan returns clear error when nmap is not installed."""
        hosts, _, err, info = scanner.scan(subnet="192.168.1.0/24")
        assert hosts == []
        assert "nmap' is not installed" in err
        assert info["success"] is False


class TestTailscaleStatus:
    """Tests for the Tailscale mesh discovery helper."""

    @patch("shutil.which", return_value=None)
    def test_tailscale_not_installed(self, mock_which):
        status = get_tailscale_status()
        assert status["active"] is False
        assert "CLI not installed" in status["reason"]

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/tailscale")
    def test_tailscale_active_with_peers(self, mock_which, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = """{
            "BackendState": "Running",
            "Self": {"HostName": "my-desktop", "TailscaleIPs": ["100.1.1.1"]},
            "Peer": {
                "p1": {
                    "Online": true,
                    "HostName": "pi-node",
                    "OS": "linux",
                    "TailscaleIPs": ["100.1.1.2"]
                }
            }
        }"""
        mock_run.return_value = mock_res
        status = get_tailscale_status()
        assert status["active"] is True
        assert len(status["peers"]) == 1
        assert status["peers"][0]["ip"] == "100.1.1.2"
        assert status["peers"][0]["hostname"] == "pi-node"


# --- NEW TEST SUITE FOR SYSTEM SNAPSHOT ---

MOCK_SNAPSHOT_SUCCESS_OUTPUT = (
    "\n---DOCKER_STATUS_START---\n"
    "active\n"
    "---DOCKER_STATUS_END---\n"
    "---DOCKER_PS_START---\n"
    "portainer#0.0.0.0:9443->9443/tcp#/data\n"
    "---DOCKER_PS_END---\n"
    "---SS_START---\n"
    "State    Recv-Q   Send-Q   Local Address:Port    Peer Address:Port   Process\n"
    "LISTEN   0        128            0.0.0.0:22             0.0.0.0:*       "
    'users:(("sshd",pid=914,fd=3))\n'
    "---SS_END---\n"
    "---RAM_START---\n"
    "Mem:            3874         629        2069\n"
    "---RAM_END---\n"
    "---DISK_START---\n"
    "/dev/vda1        59G  5.3G   54G   9% /\n"
    "---DISK_END---\n"
)

MOCK_SNAPSHOT_DOCKER_INACTIVE_OUTPUT = (
    "\n---DOCKER_STATUS_START---\n"
    "inactive\n"
    "---DOCKER_STATUS_END---\n"
    "---DOCKER_PS_START---\n"
    "error\n"
    "---DOCKER_PS_END---\n"
    "---SS_START---\n"
    "State    Recv-Q   Send-Q   Local Address:Port    Peer Address:Port   Process\n"
    "LISTEN   0        128            0.0.0.0:22             0.0.0.0:*       "
    'users:(("sshd",pid=914,fd=3))\n'
    "---SS_END---\n"
    "---RAM_START---\n"
    "Mem:            3874         629        2069\n"
    "---RAM_END---\n"
    "---DISK_START---\n"
    "/dev/vda1        59G  5.3G   54G   9% /\n"
    "---DISK_END---\n"
)


class TestNodeScannerGetSystemSnapshot:
    """Tests for the get_system_snapshot method."""

    @patch("subprocess.run")
    @patch("node_scanner.is_port_open", return_value=True)
    def test_snapshot_success_and_parsing(
        self, _mock_port_open, mock_subprocess, scanner
    ):
        """
        Test successful snapshot retrieval and correct parsing of all sections.
        """
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = MOCK_SNAPSHOT_SUCCESS_OUTPUT
        mock_subprocess.return_value = mock_result
        snapshot, err = scanner.get_system_snapshot("192.168.1.5")
        assert err is None
        assert snapshot is not None
        assert snapshot["docker_is_active"] is True

    @patch("subprocess.run")
    @patch("node_scanner.is_port_open", return_value=True)
    def test_snapshot_when_docker_is_inactive(
        self, _mock_port_open, mock_subprocess, scanner
    ):
        """Test parsing when Docker is not active on the remote host."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = MOCK_SNAPSHOT_DOCKER_INACTIVE_OUTPUT
        mock_subprocess.return_value = mock_result
        snapshot, err = scanner.get_system_snapshot("192.168.1.5")
        assert err is None
        assert snapshot is not None
        assert snapshot["docker_is_active"] is False

    @patch("node_scanner.is_port_open", return_value=False)
    def test_snapshot_fails_if_port_is_closed(self, mock_port_open, scanner):
        """Test that the snapshot is aborted if SSH port 22 is not open."""
        snapshot, err = scanner.get_system_snapshot("192.168.1.5")
        assert snapshot is None
        assert "SSH port 22 is not open" in err
        mock_port_open.assert_called_once_with("192.168.1.5", 22)

    @patch("subprocess.run")
    @patch("node_scanner.is_port_open", return_value=True)
    def test_snapshot_handles_ssh_command_failure(
        self, _mock_port_open, mock_subprocess, scanner
    ):
        """Test handling of a non-zero exit code from the SSH command."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Permission denied"
        mock_subprocess.return_value = mock_result
        snapshot, err = scanner.get_system_snapshot("192.168.1.5")
        assert snapshot is None
        assert "SSH command failed: Permission denied" in err

    @patch("subprocess.run")
    @patch("node_scanner.is_port_open", return_value=True)
    def test_snapshot_handles_timeout(self, _mock_port_open, mock_subprocess, scanner):
        """Test handling of a subprocess timeout."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd="ssh", timeout=20)
        snapshot, err = scanner.get_system_snapshot("192.168.1.5")
        assert snapshot is None
        assert "SSH command timed out" in err

    @patch("subprocess.run")
    @patch("node_scanner.is_port_open", return_value=True)
    def test_snapshot_handles_sshpass_not_found(
        self, _mock_port_open, mock_subprocess, scanner
    ):
        """Test handling of FileNotFoundError if sshpass is not installed."""
        mock_subprocess.side_effect = FileNotFoundError
        snapshot, err = scanner.get_system_snapshot("192.168.1.5")
        assert snapshot is None
        assert "sshpass is not installed" in err

    @patch("subprocess.run")
    @patch("node_scanner.is_port_open", return_value=True)
    def test_snapshot_handles_unexpected_exception(
        self, _mock_port_open, mock_subprocess, scanner
    ):
        """Test handling of an unexpected Exception during SSH execution."""
        mock_subprocess.side_effect = RuntimeError("Broken pipe")
        snapshot, err = scanner.get_system_snapshot("192.168.1.5")
        assert snapshot is None
        assert "An unexpected SSH error occurred" in err

    @patch("subprocess.run")
    @patch("node_scanner.is_port_open", return_value=True)
    def test_snapshot_handles_parsing_exception(
        self, _mock_port_open, mock_subprocess, scanner
    ):
        """Test handling of an unexpected Exception during snapshot parsing."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Malformed stdout"
        mock_subprocess.return_value = mock_result
        with patch.object(
            scanner, "_parse_section", side_effect=Exception("Parse crash")
        ):
            snapshot, err = scanner.get_system_snapshot("192.168.1.5")
            assert snapshot is None
            assert "An unexpected SSH error occurred" in err


class TestTailscaleAndScanEdgeCases:
    """Tests tailscale status checks and network scan error conditions."""

    def test_is_supported_sbc_empty(self):
        """Test empty MAC address checks."""
        assert is_supported_sbc("") is False
        assert is_supported_sbc(None) is False

    @patch("shutil.which", return_value="/usr/bin/tailscale")
    @patch("subprocess.run")
    def test_tailscale_non_running_or_error_status(self, mock_run, _mock_which):
        """Test non-running states and non-zero exit codes."""
        # 1. Non-zero return code
        mock_run.return_value = MagicMock(returncode=1)
        st_err = get_tailscale_status()
        assert st_err["active"] is False
        assert "not running" in st_err["reason"]

        # 2. BackendState != Running
        import json

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"BackendState": "Stopped"}),
        )
        st_stopped = get_tailscale_status()
        assert st_stopped["active"] is False
        assert "Stopped" in st_stopped["reason"]

        # 3. Running with peers (offline vs online)
        peer_data = {
            "BackendState": "Running",
            "Peer": {
                "p1": {"Online": False},
                "p2": {"Online": True, "TailscaleIPs": []},
                "p3": {
                    "Online": True,
                    "TailscaleIPs": ["100.64.0.5"],
                    "DNSName": "my-pi.tailnet.ts.net.",
                    "OS": "linux",
                },
            },
            "Self": {"HostName": "local-host", "TailscaleIPs": ["100.64.0.1"]},
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(peer_data))
        st_online = get_tailscale_status()
        assert st_online["active"] is True
        assert len(st_online["peers"]) == 1
        peer, *_ = st_online["peers"]
        assert peer["ip"] == "100.64.0.5"
        assert peer["hostname"] == "my-pi"

        # 4. TimeoutExpired
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="tailscale", timeout=10)
        st_timeout = get_tailscale_status()
        assert st_timeout["active"] is False
        assert st_timeout.get("timed_out") is True

        # 5. Generic exception
        mock_run.side_effect = RuntimeError("System crash")
        st_exc = get_tailscale_status()
        assert st_exc["active"] is False
        assert "Error checking Tailscale" in st_exc["reason"]

    def test_scan_subnet_failure_and_nmap_errors(self, scanner):
        """Test scan error conditions for auto-detect and nmap exceptions."""
        import nmap

        # 1. Could not auto-detect subnet
        with patch.object(scanner, "detect_subnet", return_value=None):
            hosts, msgs, err, info = scanner.scan(subnet=None)
            assert hosts == []
            assert "Could not auto-detect subnet" in err
            assert info["success"] is False

        # 2. PortScannerError
        with (
            patch("shutil.which", return_value="/usr/bin/nmap"),
            patch.object(nmap.PortScanner, "__init__", return_value=None),
            patch(
                "nmap.PortScanner.scan",
                side_effect=nmap.PortScannerError("Nmap scan aborted"),
            ),
        ):
            hosts, msgs, err, info = scanner.scan(subnet="192.168.1.0/24")
            assert hosts == []
            assert "Nmap scan aborted" in err

        # 3. Generic Exception during scan
        with (
            patch("shutil.which", return_value="/usr/bin/nmap"),
            patch.object(nmap.PortScanner, "__init__", return_value=None),
            patch(
                "nmap.PortScanner.scan",
                side_effect=Exception("Unexpected nmap crash"),
            ),
        ):
            hosts, msgs, err, info = scanner.scan(subnet="192.168.1.0/24")
            assert hosts == []
            assert "Unexpected nmap crash" in err

    def test_node_scanner_additional_coverage(self, scanner):
        """Test sbc loader errors, ip resolution, subnet autodetect,
        and parsing edges."""
        from node_scanner import NodeScanner, _load_sbc_mac_prefixes

        # 1. SBC MAC prefix loader error
        with patch("builtins.open", side_effect=FileNotFoundError):
            assert _load_sbc_mac_prefixes() == set()

        # 2. get_primary_ip OSError fallback
        with patch("socket.socket") as mock_sock:
            mock_sock.return_value.connect.side_effect = OSError("Network down")
            assert NodeScanner.get_primary_ip() == "127.0.0.1"

        # 3. detect_subnet returns None on localhost or unmatched interface
        with patch.object(NodeScanner, "get_primary_ip", return_value="127.0.0.1"):
            assert NodeScanner.detect_subnet() is None

        with patch.object(NodeScanner, "get_primary_ip", return_value="10.99.99.99"):
            with patch("psutil.net_if_addrs", return_value={}):
                assert NodeScanner.detect_subnet() is None

        # 4. scan() subnet auto-detection success
        with patch.object(scanner, "detect_subnet", return_value="192.168.1.0/24"):
            with patch("shutil.which", return_value="/usr/bin/nmap"):
                with patch("nmap.PortScanner") as mock_ps_cls:
                    mock_ps = MagicMock()
                    mock_ps.scan.return_value = {"scan": {}}
                    mock_ps_cls.return_value = mock_ps
                    hosts, msgs, err, info = scanner.scan(subnet=None)
                    assert info["success"] is True
                    assert info["method_used"] == "auto_detect"

        # 5. _parse_docker_ps malformed line
        assert NodeScanner._parse_docker_ps("name_without_hash") == []

        # 6. _parse_ss_output error, non-listen, and malformed port
        assert NodeScanner._parse_ss_output("command error occurred") == []
        bad_ss = (
            "State Recv-Q Send-Q Local Address:Port\n"
            "ESTAB 0 0 10.0.0.1:80\n"
            'LISTEN 0 0 10.0.0.1:badport users:(("proc"))\n'
        )
        assert NodeScanner._parse_ss_output(bad_ss) == []
