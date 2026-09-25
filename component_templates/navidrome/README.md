# 🏗️ NjordDeploy: Navidrome Music Server

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Media%20Servers-purple.svg)]()

> Navidrome is an open source web-based music collection server and streamer. It gives you freedom to listen to your music collection from any browser or mobile device. It's like your personal Spotify! The container runs as root (user: 0:0) to ensure proper file permissions for mounted volumes.

- **Source Repository:** [github.com/deluan/navidrome](https://github.com/deluan/navidrome)
- **Container Image:** `deluan/navidrome`

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
> Tested on Proxmox LXC: docker (0.64.0, 2026-09-14), podman (0.64.0, 2026-09-14); Proxmox VM: docker (0.64.0, 2026-09-14), podman (0.64.0, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  navidrome:
    container_name: njorddeploy-navidrome
    image: "deluan/navidrome:latest"
    ports:
      - "4533:4533"
    environment:
      - "ND_SCANSCHEDULE=1h"
      - "ND_LOGLEVEL=info"
      - "ND_SESSIONTIMEOUT=24h"
      - "ND_BASEURL=nd_baseurl"
    volumes:
      - "./data/navidrome/data:/data"
      - "./data/navidrome/music:/music:ro"
    user: "0:0"
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
| `NAVIDROME_WEB_PORT` | `4533` | The port to access the Navidrome web interface. |
| `ND_SCANSCHEDULE` | `1h` | How often Navidrome should scan your music library for changes (e.g., 1h, 24h, 1m). |
| `ND_LOGLEVEL` | `info` | The logging level for Navidrome (e.g., debug, info, warn, error). |
| `ND_SESSIONTIMEOUT` | `24h` | How long a user session remains active (e.g., 24h, 7d). |
| `ND_BASEURL` | *None* | If Navidrome is behind a reverse proxy, set the base URL (e.g., /navidrome). Leave empty if not using a subpath. |

---

## 🔑 First-Run Onboarding Guide

Open Navidrome Music Server web UI and complete the initial onboarding setup.

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

Deploy **Navidrome Music Server** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
