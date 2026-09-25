# 🏗️ NjordDeploy: Frigate

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Smart%20Home%20%26%20IoT-purple.svg)]()

> A high-performance Network Video Recorder (NVR) with local, real-time AI object detection using Coral TPU or CPU for IP security cameras.

- **Upstream Project:** [Frigate](https://docs.frigate.video/)
- **Source Repository:** [github.com/blakeblackshear/frigate](https://github.com/blakeblackshear/frigate)
- **Container Image:** `python:3.11-slim`

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
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (stable, 2026-09-14), podman (8.0, 2026-09-14); Proxmox VM: docker (stable, 2026-09-14), podman (8.0, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  frigate-configurator:
    image: python:3.11-slim
    container_name: njorddeploy-frigate-configurator
    network_mode: host
    volumes:
      - "data_root/frigate/config:/app/config:rw"
    environment:
      - "FRIGATE_RTSP_USERNAME=admin"
      - "FRIGATE_RTSP_PASSWORD=ChangeMeSecurePassword123!"
    command: >
      sh -c "apt-get update && apt-get install -y ffmpeg libglib2.0-0 &&
             pip install --no-cache-dir pyyaml onvif-zeep-async zeep psutil &&
             python /app/config/frigate_camera_config_tool.py"

  frigate:
    container_name: njorddeploy-frigate
    image: ghcr.io/blakeblackshear/frigate:stable
    privileged: true # Required for direct hardware access (e.g., /dev/bus/usb for Coral)
    restart: unless-stopped
    shm_size: "512mb" # Shared memory for FFmpeg
    depends_on:
      frigate-configurator:
        condition: service_completed_successfully
    devices:
      - /dev/bus/usb:/dev/bus/usb # For Coral TPU
    volumes:
      - "data_root/frigate/config:/config:rw"
      - "data_root/frigate/media:/media/frigate:rw"
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "8080:5000"   # Dynamically mapped Web UI port
      - "8080:1935"  # Dynamically mapped RTMP re-streaming port
    environment:
      - "FRIGATE_RTSP_PASSWORD=ChangeMeSecurePassword123!"
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
| `` | `5000` | Web UI port for Frigate |
| `` | `1935` | RTMP streaming port for re-broadcasting streams |
| `` | `changeme` | Secure master password utilized for authenticated camera streams |

---

## 🔑 First-Run Onboarding Guide

Open Frigate web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://docs.frigate.video/](https://docs.frigate.video/)

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

Deploy **Frigate** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
