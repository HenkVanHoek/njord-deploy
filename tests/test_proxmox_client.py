# tests/test_proxmox_client.py
import unittest
from unittest.mock import MagicMock, patch

from utils.proxmox_client import ProxmoxClient


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

    @patch("requests.put")
    def test_resize_vm_disk(self, mock_put):
        """Verify calling VM disk resize endpoint with correct parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "UPID:pve:00001"}
        mock_put.return_value = mock_response

        res = self.client.resize_vm_disk(
            node="pve", vmid=9000, disk="scsi0", size="+10G"
        )

        self.assertEqual(res["data"], "UPID:pve:00001")
        mock_put.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/nodes/pve/qemu/9000/resize",
            headers=self.client.headers,
            data={"disk": "scsi0", "size": "+10G"},
            verify=False,
            timeout=15,
        )

    @patch("requests.put")
    def test_resize_lxc_disk(self, mock_put):
        """Verify calling LXC disk resize endpoint with correct parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "UPID:pve:00002"}
        mock_put.return_value = mock_response

        res = self.client.resize_lxc_disk(
            node="pve", vmid=104, disk="rootfs", size="+40G"
        )

        self.assertEqual(res["data"], "UPID:pve:00002")
        mock_put.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/nodes/pve/lxc/104/resize",
            headers=self.client.headers,
            data={"disk": "rootfs", "size": "+40G"},
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

    @patch("requests.get")
    def test_get_lxc_list_returns_containers(self, mock_get):
        """Verify that get_lxc_list returns the data list from the API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"vmid": 101, "name": "ct-101", "status": "running"},
                {"vmid": 102, "name": "ct-102", "status": "stopped"},
            ]
        }
        mock_get.return_value = mock_response

        containers = self.client.get_lxc_list(node="pve")

        self.assertEqual(len(containers), 2)
        first, second = containers
        self.assertEqual(first["vmid"], 101)
        self.assertEqual(second["status"], "stopped")
        mock_get.assert_called_once_with(
            "https://192.168.178.51:8006/api2/json/nodes/pve/lxc",
            headers=self.client.headers,
            params=None,
            verify=False,
            timeout=15,
        )

    @patch("requests.get")
    def test_get_lxc_list_empty(self, mock_get):
        """Verify that get_lxc_list returns an empty list when no CTs exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        containers = self.client.get_lxc_list(node="pve")

        self.assertEqual(containers, [])

    @patch("requests.get")
    def test_get_lxc_list_api_failure_returns_empty(self, mock_get):
        """Verify that get_lxc_list returns [] and does not raise on API error."""
        mock_get.side_effect = Exception("Connection refused")

        containers = self.client.get_lxc_list(node="pve")

        self.assertEqual(containers, [])

    @patch("requests.post")
    def test_post_and_put_http_error(self, mock_post):
        """Verify post and put raise RuntimeError on HTTP error."""
        import requests

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_post.return_value = mock_resp

        with self.assertRaises(RuntimeError):
            self.client.post("test/endpoint", data={"a": 1})

        with patch("requests.put") as mock_put:
            mock_put.return_value = mock_resp
            with self.assertRaises(RuntimeError):
                self.client.put("test/endpoint", data={"a": 1})

    @patch("requests.get")
    def test_get_next_vmid_invalid(self, mock_get):
        """Verify get_next_vmid raises ValueError when data is missing."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": None}
        mock_get.return_value = mock_resp

        with self.assertRaises(ValueError):
            self.client.get_next_vmid()

    @patch("requests.post")
    def test_lxc_lifecycle_methods(self, mock_post):
        """Verify clone_lxc, create_lxc, template conversion, and power actions."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": "OK"}
        mock_post.return_value = mock_resp

        # clone_lxc
        self.client.clone_lxc("pve", 100, 200, hostname="my-lxc", full=True)
        # create_lxc
        self.client.create_lxc("pve", {"vmid": 201})
        # convert_to_template
        self.client.convert_to_template("pve", 200, is_lxc=True)
        self.client.convert_to_template("pve", 100, is_lxc=False)
        # start_lxc and stop_lxc
        self.client.start_lxc("pve", 200)
        self.client.stop_lxc("pve", 200)
        # reset_vm
        self.client.reset_vm("pve", 100)

        self.assertTrue(mock_post.called)

    @patch("requests.put")
    @patch("requests.get")
    @patch("requests.delete")
    def test_status_config_destroy_and_vm_list(self, mock_del, mock_get, mock_put):
        """Verify configure_lxc, get_status, destroy_lxc, and get_vm_list."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"vmid": 100, "name": "vm1"}]}
        mock_get.return_value = mock_resp
        mock_put.return_value = mock_resp
        mock_del.return_value = mock_resp

        self.client.configure_lxc("pve", 200, {"cores": 2})
        self.client.get_vm_status("pve", 100)
        self.client.get_lxc_status("pve", 200)
        self.client.destroy_lxc("pve", 200)

        vm_list = self.client.get_vm_list("pve")
        self.assertEqual(len(vm_list), 1)

        # VM list on API error
        mock_get.side_effect = Exception("API down")
        self.assertEqual(self.client.get_vm_list("pve"), [])

    @patch("requests.get")
    def test_get_vm_ip_edge_cases(self, mock_get):
        """Verify get_vm_ip when no interfaces or non-ipv4 addresses exist."""
        # Empty interfaces
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"result": []}}
        mock_get.return_value = mock_resp
        self.assertIsNone(self.client.get_vm_ip("pve", 100))

        mock_resp.json.return_value = {
            "data": {
                "result": [
                    {
                        "ip-addresses": [
                            {
                                "ip-address-type": "ipv4",
                                "ip-address": "127.0.0.1",
                            },
                            {
                                "ip-address-type": "ipv6",
                                "ip-address": "fe80::1",
                            },
                        ]
                    }
                ]
            }
        }
        self.assertIsNone(self.client.get_vm_ip("pve", 100))

        # Interface without ips (line 257)
        mock_resp.json.return_value = {
            "data": {
                "result": [
                    {"ip-addresses": []},
                    {
                        "ip-addresses": [
                            {
                                "ip-address-type": "ipv4",
                                "ip-address": "192.168.1.50",
                            }
                        ]
                    },
                ]
            }
        }
        self.assertEqual(self.client.get_vm_ip("pve", 100), "192.168.1.50")

    def test_headers_with_exclamation_in_token_id(self):
        """Verify headers when token_id contains username and exclamation."""
        c = ProxmoxClient(
            host="https://192.168.178.51:8006",
            user="root@pam",
            token_id="root@pam!clean-token",
            token_secret="testsecret",
            verify_ssl=False,
        )
        self.assertEqual(
            c.headers["Authorization"],
            "PVEAPIToken=root@pam!clean-token=testsecret",
        )
