# src/utils/proxmox_client.py
import logging
from typing import Any, Dict, Optional

import requests
import urllib3

logger = logging.getLogger(__name__)


class ProxmoxClient:
    """
    Client for interacting with the Proxmox VE REST API.
    Handles VM cloning, cloud-init configuration, power state management,
    and retrieving network interface details from the QEMU guest agent.
    """

    def __init__(
        self,
        host: str,
        user: str,
        token_id: str,
        token_secret: str,
        verify_ssl: bool = False,
    ):
        self.host = host.rstrip("/")
        self.api_url = f"{self.host}/api2/json"
        self.user = user
        self.token_id = token_id
        self.token_secret = token_secret
        self.verify_ssl = verify_ssl

        if not verify_ssl:
            # Disable warnings for self-signed certificates
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def headers(self) -> dict:
        """Constructs authorization headers for PVE API Token."""
        # Robustly handle if token_id already includes username + !
        clean_token_id = self.token_id
        if "!" in clean_token_id:
            clean_token_id = clean_token_id.split("!", 1)[1]
        token_str = f"PVEAPIToken={self.user}!{clean_token_id}={self.token_secret}"
        return {"Authorization": token_str, "Accept": "application/json"}

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict:
        """Executes a GET request to the Proxmox API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            verify=self.verify_ssl,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> dict:
        """Executes a POST request to the Proxmox API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = requests.post(
            url,
            headers=self.headers,
            data=data,
            verify=self.verify_ssl,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict:
        """Executes a DELETE request to the Proxmox API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = requests.delete(
            url,
            headers=self.headers,
            params=params,
            verify=self.verify_ssl,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def get_next_vmid(self) -> int:
        """Retrieves the next unused VMID from the cluster."""
        res = self.get("cluster/nextid")
        data = res.get("data")
        if data is None:
            raise ValueError("Proxmox API returned no next VMID data")
        return int(data)

    def clone_vm(
        self, node: str, vmid: int, newid: int, name: str, full: bool = False
    ) -> dict:
        """Triggers a clone of the source VM/Template."""
        endpoint = f"nodes/{node}/qemu/{vmid}/clone"
        data = {
            "newid": newid,
            "name": name,
            "full": 1 if full else 0,
        }
        return self.post(endpoint, data=data)

    def configure_vm(self, node: str, vmid: int, config_data: dict) -> dict:
        """Configures VM hardware and Cloud-Init parameters."""
        endpoint = f"nodes/{node}/qemu/{vmid}/config"
        return self.post(endpoint, data=config_data)

    def start_vm(self, node: str, vmid: int) -> dict:
        """Starts the VM."""
        endpoint = f"nodes/{node}/qemu/{vmid}/status/start"
        return self.post(endpoint)

    def stop_vm(self, node: str, vmid: int) -> dict:
        """Stops the VM."""
        endpoint = f"nodes/{node}/qemu/{vmid}/status/stop"
        return self.post(endpoint)

    def destroy_vm(self, node: str, vmid: int) -> dict:
        """Destroys the VM (purging all associated resources)."""
        endpoint = f"nodes/{node}/qemu/{vmid}"
        return self.delete(endpoint, params={"purge": 1})

    def get_vm_ip(self, node: str, vmid: int) -> str | None:
        """
        Retrieves the first non-loopback IPv4 address of the VM
        from the QEMU Guest Agent.
        """
        endpoint = f"nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
        try:
            res = self.get(endpoint)
            data = res.get("data", {})
            interfaces = data.get("result", [])
            if not interfaces:
                return None

            for interface in interfaces:
                ips = interface.get("ip-addresses", [])
                if not ips:
                    continue
                for ip in ips:
                    ip_addr = ip.get("ip-address")
                    ip_type = ip.get("ip-address-type")
                    if ip_type == "ipv4" and ip_addr and not ip_addr.startswith("127."):
                        return ip_addr
        except Exception as e:
            logger.debug(f"Failed to query guest agent network interfaces: {e}")
        return None
