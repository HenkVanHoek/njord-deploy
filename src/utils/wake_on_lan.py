"""Wake-on-LAN (WOL) utility for waking remote machines.

Sends standard magic packets (UDP broadcast) to wake powered-down systems,
such as a local Windows RTX machine for offline emergency AI failover.
"""

import logging
import re
import socket

logger = logging.getLogger(__name__)


def send_wake_on_lan(
    mac_address: str,
    broadcast_ip: str = "255.255.255.255",
    port: int = 9,
) -> bool:
    """Sends a Wake-on-LAN magic packet to the specified MAC address.

    Args:
        mac_address: Target MAC (e.g. "e8:9c:25:29:f0:0c" or "E8-9C-25-29-F0-0C").
        broadcast_ip: The broadcast destination IP (defaults to 255.255.255.255).
        port: Destination UDP port (usually 9 or 7).

    Returns:
        bool: True if the packet was successfully transmitted, False otherwise.
    """
    cleaned_mac = re.sub(r"[^0-9A-Fa-f]", "", mac_address)
    if len(cleaned_mac) != 12:
        logger.error("Invalid MAC address provided for Wake-on-LAN: %s", mac_address)
        return False

    try:
        mac_bytes = bytes.fromhex(cleaned_mac)
    except ValueError as err:
        logger.error("Failed to parse MAC address hex: %s", err)
        return False

    # Magic packet consists of 6 bytes of 0xFF followed by 16 repetitions of the MAC
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, (broadcast_ip, port))
        logger.info(
            "Wake-on-LAN magic packet dispatched to %s (%s:%d)",
            mac_address,
            broadcast_ip,
            port,
        )
        return True
    except Exception as exc:
        logger.error("Failed to send Wake-on-LAN packet: %s", exc)
        return False
