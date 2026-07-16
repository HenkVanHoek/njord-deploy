# Failed and Difficult-to-Fix Components

This document tracks components that failed verification or could not be tested/fixed within 3 attempts, along with the reasons and current status.

## Skipped / Untestable Components

### `njorddeploy-service-maintenance`
*   **Date**: 2026-07-15
*   **Reason**: The component's docker-compose template (`component_templates/njorddeploy-service-maintenance/docker-compose.template.yml`) is completely empty and contains no service definitions or port mappings.
*   **Action**: Skipped for further developer inspection.

### `web-notepad`
*   **Date**: 2026-07-15
*   **Reason**: Both the metadata image (`dprandzioch/docker-http-notepad`) and the template image (`pajikos/minimalist-web-notepad`) are unavailable on the public Docker Hub registry, returning `pull access denied` (either deleted or made private).
*   **Action**: Skipped. Needs a replacement public image.

### `zigbee2mqtt`
*   **Date**: 2026-07-15
*   **Reason**: The component requires a physical USB Zigbee coordinator (e.g., `/dev/ttyUSB0`) to start up. Spawning a fresh Proxmox LXC container without a USB device passed through causes the container startup to fail with "no such file or directory" for the custom device path.
*   **Action**: Skipped. Fundamentally requires physical hardware setup.

### `lora-service` (LoRa Letterbox Notifier)
*   **Date**: 2026-07-16
*   **Reason**: Incomplete placeholder component. It lacks required metadata (no image_name or component_version defined in metadata) and its template mounts configurations (`chirpstack.toml`, `mosquitto.conf`) that do not exist in the repository, making it impossible to deploy.
*   **Action**: Skipped. Needs complete stack templates and configuration files.
