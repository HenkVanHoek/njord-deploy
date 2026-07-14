# tests/test_proxmox_client.py
import unittest
from unittest.mock import MagicMock, patch

from src.utils.proxmox_client import ProxmoxClient


class TestProxmoxClient(unittest.TestCase):
    """Unit tests for the ProxmoxClient helper utility."""

    def setUp(self):
        self.client = ProxmoxClient(
            host="https://192.168.178.51:8006",
            user="root@pam",
            token_id="clone-token",
            token_secret="testsecret",
            verify_ssl=False,
        )

    def test_headers_format(self):
        """Verify the PVE API Token header string format."""
        headers = self.client.headers
        self.assertEqual(
            headers["Authorization"],
            "PVEAPIToken=root@pam!clone-token=testsecret",
        )
        self.assertEqual(headers["Accept"], "application/json")

    @patch("requests.get")
    def test_get_next_vmid(self, mock_get):
        """Verify retrieving the next available VMID."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "9000"}
        mock_get.return_value = mock_response

        vmid = self.client.get_next_vmid()

        self.assertEqual(vmid, 9000)
        mock_get.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/cluster/nextid",
            headers=self.client.headers,
            params=None,
            verify=False,
            timeout=15,
        )

    @patch("requests.post")
    def test_clone_vm(self, mock_post):
        """Verify calling the clone endpoint with correct parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "UPID:pve:00001"}
        mock_post.return_value = mock_response

        res = self.client.clone_vm(
            node="pve", vmid=100, newid=9000, name="test-vm", full=False
        )

        self.assertEqual(res["data"], "UPID:pve:00001")
        mock_post.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/nodes/pve/qemu/100/clone",
            headers=self.client.headers,
            data={"newid": 9000, "name": "test-vm", "full": 0},
            verify=False,
            timeout=15,
        )

    @patch("requests.post")
    def test_configure_vm(self, mock_post):
        """Verify setting VM configuration options."""
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        config = {"memory": "2048", "cores": "2"}
        self.client.configure_vm(node="pve", vmid=9000, config_data=config)

        mock_post.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/nodes/pve/qemu/9000/config",
            headers=self.client.headers,
            data=config,
            verify=False,
            timeout=15,
        )

    @patch("requests.post")
    def test_start_vm(self, mock_post):
        """Verify initiating VM power start."""
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        self.client.start_vm(node="pve", vmid=9000)

        mock_post.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/nodes/pve/qemu/9000/status/start",
            headers=self.client.headers,
            data=None,
            verify=False,
            timeout=15,
        )

    @patch("requests.post")
    def test_stop_vm(self, mock_post):
        """Verify initiating VM power stop."""
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        self.client.stop_vm(node="pve", vmid=9000)

        mock_post.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/nodes/pve/qemu/9000/status/stop",
            headers=self.client.headers,
            data=None,
            verify=False,
            timeout=15,
        )

    @patch("requests.delete")
    def test_destroy_vm(self, mock_delete):
        """Verify initiating VM deletion with purge option."""
        mock_response = MagicMock()
        mock_delete.return_value = mock_response

        self.client.destroy_vm(node="pve", vmid=9000)

        mock_delete.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/nodes/pve/qemu/9000",
            headers=self.client.headers,
            params={"purge": 1},
            verify=False,
            timeout=15,
        )

    @patch("requests.get")
    def test_get_vm_ip_success(self, mock_get):
        """Verify extracting IPv4 from guest agent network interfaces response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "result": [
                    {
                        "name": "lo",
                        "ip-addresses": [
                            {"ip-address": "127.0.0.1", "ip-address-type": "ipv4"}
                        ],
                    },
                    {
                        "name": "eth0",
                        "ip-addresses": [
                            {
                                "ip-address": "fe80::215:5dff:fe00:1122",
                                "ip-address-type": "ipv6",
                            },
                            {
                                "ip-address": "192.168.178.150",
                                "ip-address-type": "ipv4",
                            },
                        ],
                    },
                ]
            }
        }
        mock_get.return_value = mock_response

        ip = self.client.get_vm_ip(node="pve", vmid=9000)

        self.assertEqual(ip, "192.168.178.150")

    @patch("requests.get")
    def test_get_vm_ip_no_agent(self, mock_get):
        """Verify handling cases where guest agent is not running/responsive."""
        mock_get.side_effect = Exception("500 Qemu guest agent not running")

        ip = self.client.get_vm_ip(node="pve", vmid=9000)

        self.assertIsNone(ip)


if __name__ == "__main__":
    unittest.main()
