# Failed and Difficult-to-Fix Components

This document tracks components that failed verification or could not be tested/fixed within 3 attempts, along with the reasons and current status.

## Skipped / Untestable Components

### `gluetun`
*   **Date**: 2026-08-14
*   **Reason**: The component requires access to the host kernel device `/dev/net/tun` for VPN tunneling. Standard unprivileged Proxmox LXC containers do not have this device node passed through by default, causing container startup to fail with `error gathering device information while adding custom device "/dev/net/tun": not a device node`.
*   **Action**: Skipped for automated LXC runs. Requires privileged LXC or VM with `/dev/net/tun` passthrough.

### `zigbee2mqtt`
*   **Date**: 2026-07-15
*   **Reason**: The component requires a physical USB Zigbee coordinator (e.g., `/dev/ttyUSB0`) to start up. Spawning a fresh Proxmox container without a physical USB device passed through causes the container startup to fail with "no such file or directory" for the custom device path.
*   **Action**: Skipped. Fundamentally requires physical hardware setup.

### `lora-service` (LoRa Letterbox Notifier)
*   **Date**: 2026-07-16
*   **Reason**: Incomplete placeholder component. It lacks required metadata (no image_name or component_version defined in metadata) and its template mounts configurations (`chirpstack.toml`, `mosquitto.conf`) that do not exist in the repository, making it impossible to deploy.
*   **Action**: Skipped. Needs complete stack templates and configuration files.

### `njorddeploy-service-maintenance`
*   **Date**: 2026-07-15
*   **Reason**: The component's docker-compose template (`component_templates/njorddeploy-service-maintenance/docker-compose.template.yml`) is completely empty and contains no service definitions or port mappings.
*   **Action**: Skipped for further developer inspection.

### `voicebox`
*   **Date**: 2026-08-15
*   **Reason**: Upstream repository (`https://github.com/jamiepine/voicebox.git#main`) Dockerfile build fails on line 66 trying to install `git+https://github.com/QwenLM/Qwen3-TTS.git` which is non-existent or moved.
*   **Action**: Skipped until upstream repository fixes its Dockerfile or publishes prebuilt images.
