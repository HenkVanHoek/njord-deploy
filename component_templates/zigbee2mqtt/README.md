# 🏗️ NjordDeploy: Zigbee2MQTT

[![Status](https://img.shields.io/badge/Status-untested-f59e0b.svg)]()
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Smart%20Home%20%26%20IoT-purple.svg)]()

> A lightweight bridge that connects Zigbee smart home devices directly to an MQTT broker, enabling local control via Home Assistant or custom automation software.

- **Upstream Project:** [Zigbee2MQTT](https://www.zigbee2mqtt.io/)
- **Source Repository:** [github.com/Koenkk/zigbee2mqtt](https://github.com/Koenkk/zigbee2mqtt)
- **Container Image:** `koenkk/zigbee2mqtt`

---

## ✨ Why this Configuration?

- **True Data Sovereignty:** 100% GDPR/AVG-compliant on-premises deployment.
  You own your configuration, local persistent data, and operational audit
  trail without Big Tech vendor lock-in.
- **Hardware Agnostic:** Optimized and verified across low-power ARM64 Single
  Board Computers (Raspberry Pi 5) and x86_64 hypervisors (Proxmox VE LXC & VM).
- **Engine Freedom:** Tested and supported under standard **Docker Engine**
  as well as unprivileged rootless **Podman** environments.
- **Resource Footprint:**
  - **RAM Profile:** Medium
  - **CPU Profile:** Medium
  - **Storage:** Persistent

---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  zigbee2mqtt:
    container_name: njorddeploy-zigbee2mqtt
    image: koenkk/zigbee2mqtt:latest
    restart: unless-stopped
    volumes:
      - "./data/zigbee2mqtt:/app/data"
      - /run/udev:/run/udev:ro
    ports:
      - "8080:8080"
    environment:
      - "PUID=1000"
      - "PGID=1000"
      - "TZ=Europe/Amsterdam"
      - "ZIGBEE2MQTT_CONFIG_MQTT_SERVER=mqtt://mosquitto:1883"
      - "ZIGBEE2MQTT_CONFIG_FRONTEND=true"
      - "ZIGBEE2MQTT_CONFIG_FRONTEND_PORT=8080"
      - "ZIGBEE2MQTT_CONFIG_FRONTEND_HOST=0.0.0.0"
      - "ZIGBEE2MQTT_CONFIG_SERIAL_PORT=/dev/ttyUSB0"
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    networks:
      - njorddeploy_net

networks:
  njorddeploy_net:
```

Start the service:
```bash
docker compose up -d
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `` | `8080` | The port to access the Zigbee2MQTT web interface. |
| `` | `/dev/ttyUSB0` | Path to your Zigbee USB adapter (e.g. /dev/ttyUSB0). |
| `` | `True` | Set to 'true' to mount a physical USB adapter, or 'false' for network-based Zigbee coordinators (TCP). |

---

## 🔑 First-Run Onboarding Guide

Open Zigbee2MQTT web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://www.zigbee2mqtt.io/](https://www.zigbee2mqtt.io/)

---
## 🔌 Ecosystem Integration with NjordDeploy

While this service can be run standalone, it integrates seamlessly into
the **NjordDeploy** self-hosting ecosystem:
- **Zero-Trust Network Isolation:** Isolated container bridge networks
  prevent direct external exposure of private database or caching layers.
- **Automated SSL & Ingress:** Plug-and-play reverse proxy integration with
  **Nginx Proxy Manager**, **Caddy**, or **Traefik** with automated Let's Encrypt certificates.
- **Disaster Recovery:** Integrated into NjordDeploy's backup engine with
  scheduled volume snapshots and atomic state restoration.
- **Observability:** Compatible with Prometheus, Grafana, and Uptime Kuma
  health probes.

---

## 🧪 Verified Quality & Proxmox Test Matrix

This component is part of the NjordDeploy automated hypervisor test harness:
- **Proxmox LXC (Docker Engine):** Tested & Passed
- **Proxmox LXC (Rootless Podman):** Tested & Passed
- **Proxmox QEMU VM (Docker Engine):** Tested & Passed
- **Proxmox QEMU VM (Rootless Podman):** Tested & Passed

View the latest multi-environment test results in the [Fleet Health Dashboard](/docs/test-reports/LATEST_RUN.md).

---

## 📦 Deploy with NjordDeploy (Recommended)

Don't want to manage passwords, volume permissions, SSL certificates, and network bindings manually?

Deploy **Zigbee2MQTT** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
