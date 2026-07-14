import ipaddress
import json
import logging
import os
import re
import socket
import subprocess  # nosec B404

import nmap
import psutil

from utils.resource_utils import resource_path

logger = logging.getLogger(__name__)


def _load_sbc_mac_prefixes():
    """Loads the known SBC MAC address prefixes from a JSON file."""
    try:
        config_path = resource_path(os.path.join("config", "sbc_oui.json"))
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        prefixes = set()
        for vendor_prefixes in data.get("vendors", {}).values():
            for prefix in vendor_prefixes:
                prefixes.add(prefix.lower())
        return prefixes
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error("Could not load SBC MAC prefixes")
        return set()


SBC_MAC_PREFIXES = _load_sbc_mac_prefixes()


def is_supported_sbc(mac_address):
    """Checks if a given MAC address belongs to a supported SBC."""
    if not mac_address:
        return False
    mac_prefix = mac_address[:8].lower().replace("-", ":")
    return mac_prefix in SBC_MAC_PREFIXES


def is_raspberry_pi(mac_address):
    """Alias for is_supported_sbc to maintain backward compatibility."""
    return is_supported_sbc(mac_address)


def is_port_open(host, port):
    """Checks if a TCP port is open on a given host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((host, port))
        s.close()
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False


class NodeScanner:
    """
    Scans the network for nodes/devices and gathers detailed system
    information from them via SSH.
    """

    SSH_SNAPSHOT_COMMAND = (
        "echo '---OS_INFO_START---'; cat /etc/os-release || echo 'error'; "
        "echo '---OS_INFO_END---'; "
        "echo '---SERIAL_START---'; "
        "cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2 || echo 'error'; "
        "echo '---SERIAL_END---'; "
        "echo '---MODEL_START---'; "
        "if [ -f /proc/device-tree/model ]; then cat /proc/device-tree/model; "
        "elif [ -f /etc/njorddeploy-virtual-pi-server ]; "
        "then cat /etc/njorddeploy-virtual-pi-server; fi; "
        "echo '---MODEL_END---'; "
        "echo '---DOCKER_STATUS_START---'; "
        "systemctl is-active --quiet docker && echo 'active' || echo 'inactive'; "
        "echo '---DOCKER_STATUS_END---'; "
        "echo '---DOCKER_PS_START---'; "
        "docker ps --format '{{.Names}}#{{.Ports}}#{{.Mounts}}' || echo 'error'; "
        "echo '---DOCKER_PS_END---'; "
        "echo '---SS_START---'; ss -ltpn || echo 'error'; "
        "echo '---SS_END---'; "
        "echo '---RAM_START---'; free -m || echo 'error'; "
        "echo '---RAM_END---'; "
        "echo '---DISK_START---'; "
        "df -h / --output=size,pcent || echo 'error'; "
        "echo '---DISK_END---';"
    )

    def __init__(self, username, password):
        self.username = username
        self.password = password

    @staticmethod
    def get_primary_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("8.8.8.8", 1))
            ip_address = s.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            s.close()
        return ip_address

    @staticmethod
    def detect_subnet():
        primary_ip = NodeScanner.get_primary_ip()
        if primary_ip == "127.0.0.1":
            return None
        all_addrs = psutil.net_if_addrs()
        for addresses in all_addrs.values():
            for addr in addresses:
                if addr.family == socket.AF_INET and addr.address == primary_ip:
                    network = ipaddress.IPv4Network(
                        f"{addr.address}/{addr.netmask}", strict=False
                    )
                    return str(network.with_prefixlen)
        return None

    def scan(self, subnet=None):
        detection_info = {}
        messages = []
        if subnet is None:
            detected_subnet = self.detect_subnet()
            if detected_subnet:
                subnet = detected_subnet
                detection_info = {"success": True, "method_used": "auto_detect"}
                messages.append(f"✅ Subnet auto-detected: {subnet}")
            else:
                error_msg = "Could not auto-detect subnet."
                detection_info["success"] = False
                return [], messages, error_msg, detection_info
        else:
            detection_info = {"success": True, "method_used": "user_provided"}
            messages.append(f"🎯 Using provided network: {subnet}")
        try:
            nm = nmap.PortScanner()
            result = nm.scan(hosts=subnet, arguments="-sn -PR", sudo=True)
            hosts = []
            for host, host_info in result.get("scan", {}).items():
                mac = host_info.get("addresses", {}).get("mac")
                if mac and is_raspberry_pi(mac):
                    vendor = host_info.get("vendor", {}).get(mac, "Unknown")
                    hostname = host_info.get("hostnames", [{}])[0].get("name", "")
                    hosts.append(
                        {
                            "ip": host,
                            "mac": mac,
                            "vendor": vendor,
                            "hostname": hostname or "Unknown",
                        }
                    )
            return hosts, messages, "", detection_info
        except Exception as e:
            error_msg = f"❌ Scan failed: {str(e)}"
            detection_info["success"] = False
            return [], messages, error_msg, detection_info

    @staticmethod
    def _parse_section(key, output):
        pattern = f"---{key}_START---(.*?)---{key}_END---"
        match = re.search(pattern, output, re.DOTALL)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_docker_ps(raw_output):
        if not raw_output or "error" in raw_output:
            return []
        containers = []
        for line in raw_output.strip().split("\n"):
            parts = line.split("#")
            if len(parts) != 3:
                continue
            name, ports_raw, mounts_raw = parts
            containers.append({"name": name, "ports": ports_raw, "mounts": mounts_raw})
        return containers

    @staticmethod
    def _parse_ss_output(raw_output):
        if not raw_output or "error" in raw_output:
            return []
        processes = []
        proc_regex = re.compile(r'users:\(\("([^"]+)"')
        for line in raw_output.strip().split("\n")[1:]:
            parts = line.split()
            if len(parts) < 4 or "LISTEN" not in parts[0]:
                continue
            try:
                address = parts[3]
                port = address.split(":")[-1]
                proc_match = proc_regex.search(line)
                proc_name = proc_match.group(1) if proc_match else "unknown"
                processes.append({"port": int(port), "process_name": proc_name})
            except (ValueError, IndexError):
                continue
        return processes

    @staticmethod
    def _parse_resource_metrics(ram_raw: str, disk_raw: str):
        resources = {
            "ram": {"total_mb": 0, "used_mb": 0},
            "disk": {"size": "N/A", "pcent": "N/A"},
        }
        if ram_raw:
            mem_line = next(
                (line for line in ram_raw.split("\n") if line.startswith("Mem:")),
                None,
            )
            if mem_line:
                parts = mem_line.split()
                if len(parts) >= 3:
                    resources["ram"] = {
                        "total_mb": int(parts[1]),
                        "used_mb": int(parts[2]),
                    }
        if disk_raw:
            disk_line = disk_raw.strip().split("\n")[-1]
            parts = disk_line.split()
            if len(parts) >= 2:
                resources["disk"] = {"size": parts[0], "pcent": parts[1]}
        return resources

    def get_system_snapshot(self, ip_address):
        if not is_port_open(ip_address, 22):
            return None, f"SSH port 22 is not open on {ip_address}."

        from pathlib import Path

        from appdirs import user_data_dir

        app_data_dir = Path(user_data_dir("NjordDeploy", "NjordDeploy"))
        key_file = app_data_dir / "id_ed25519_njorddeploy"

        result = None
        if key_file.exists():
            try:
                command = [
                    "ssh",
                    "-i",
                    str(key_file),
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "ConnectTimeout=10",
                    "-o",
                    "PreferredAuthentications=publickey",
                    f"{self.username}@{ip_address}",
                    self.SSH_SNAPSHOT_COMMAND,
                ]
                res = subprocess.run(  # nosec B603
                    command, capture_output=True, text=True, timeout=20, check=False
                )
                if res.returncode == 0:
                    result = res
            except Exception as e:
                logger.debug(f"SSH key connection attempt failed: {e}")

        if result is None:
            try:
                command = [
                    "sshpass",
                    "-p",
                    self.password,
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "ConnectTimeout=10",
                    "-o",
                    "PreferredAuthentications=password,keyboard-interactive",
                    f"{self.username}@{ip_address}",
                    self.SSH_SNAPSHOT_COMMAND,
                ]
                result = subprocess.run(  # nosec B603
                    command, capture_output=True, text=True, timeout=20, check=False
                )
            except FileNotFoundError:
                msg = "sshpass is not installed."
                return None, msg
            except subprocess.TimeoutExpired:
                msg = f"SSH command timed out for {ip_address}."
                return None, msg
            except Exception as e:
                msg = f"An unexpected SSH error occurred: {e}"
                logger.error(msg, exc_info=True)
                return None, msg

        if result.returncode != 0:
            return None, f"SSH command failed: {result.stderr.strip()}"

        try:
            output = result.stdout
            os_info_raw = self._parse_section("OS_INFO", output)
            os_info = dict(
                line.split("=", 1)
                for line in os_info_raw.strip().split("\n")
                if "=" in line
            )
            docker_status_str = self._parse_section("DOCKER_STATUS", output)
            docker_ps_raw = self._parse_section("DOCKER_PS", output)
            ss_raw = self._parse_section("SS", output)
            ram_raw = self._parse_section("RAM", output)
            disk_raw = self._parse_section("DISK", output)

            snapshot = {
                "os_version": os_info.get("PRETTY_NAME", "N/A").strip('"'),
                "serial": self._parse_section("SERIAL", output),
                "model": self._parse_section("MODEL", output).replace("\x00", ""),
                "docker_is_active": "active" == docker_status_str,
                "containers": self._parse_docker_ps(docker_ps_raw),
                "native_processes": self._parse_ss_output(ss_raw),
                "resources": self._parse_resource_metrics(ram_raw, disk_raw),
            }
            return snapshot, None
        except Exception as e:
            msg = f"An unexpected SSH error occurred: {e}"
            logger.error(msg, exc_info=True)
            return None, msg
