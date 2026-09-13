# Hardware-Dependent and Specialized Components

This document tracks components that require physical hardware devices or specialized host kernel configurations and are therefore skipped in standard unprivileged virtual test environments.

## Hardware-Dependent & Specialized Services

### `zigbee2mqtt`
*   **Status**: Active & Supported
*   **Constraint**: Physical Hardware Required (`/dev/ttyUSB0` or `/dev/ttyACM0`).
*   **Description**: Requires a physical USB Zigbee coordinator (e.g. Sonoff Zigbee 3.0 or ConBee II) connected to the host. In a virtual cloud container without hardware passthrough, the daemon safely exits upon startup.

### `lora-service` (LoRa Letterbox Notifier)
*   **Status**: Active & Supported (Custom Hardware)
*   **Constraint**: Physical LoRa Gateway Required.
*   **Description**: Dedicated IoT application designed for physical mailbox monitoring via LoRaWAN gateways and ChirpStack concentrators.

### `gluetun`
*   **Status**: Active & Supported (Kernel Tunnel Required)
*   **Constraint**: Kernel Device Node (`/dev/net/tun`) & VPN Provider Credentials.
*   **Description**: Requires the host `/dev/net/tun` kernel module and valid VPN subscription credentials (WireGuard/OpenVPN). Automated testing is skipped in standard unprivileged LXC environments.

---

## Deprecated & Retired Prototypes

*   **`njorddeploy-service-maintenance`**: Removed. Replaced by the built-in system managers in NjordDeploy.
*   **`voicebox`**: Removed. Unmaintained upstream Docker image with excessive resource footprint; alternative voice/AI workflows are handled via Ollama, Open WebUI, and Piper.
