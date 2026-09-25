# 🏗️ NjordDeploy: Audiobookshelf

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Media%20Servers-purple.svg)]()

> A self-hosted audiobook and podcast server for organizing, streaming, and tracking playback progress across your personal audio media library.

- **Upstream Project:** [Audiobookshelf](https://www.audiobookshelf.org/)
- **Source Repository:** [github.com/advplyr/audiobookshelf](https://github.com/advplyr/audiobookshelf)
- **Container Image:** `ghcr.io/advplyr/audiobookshelf`

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
  - **RAM Profile:** 256mi
  - **CPU Profile:** 100m
  - **Storage:** Hdd
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (2.36.0, 2026-09-14), podman (2.36.0, 2026-09-14); Proxmox VM: docker (2.36.0, 2026-09-14), podman (2.36.0, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  audiobookshelf:
    image: ghcr.io/advplyr/audiobookshelf:latest
    container_name: njorddeploy-audiobookshelf
    ports:
      - "13378:80"
    volumes:
      - "./data/audiobookshelf/audiobooks:/audiobooks"
      - "./data/audiobookshelf/podcasts:/podcasts"
      - "./data/audiobookshelf/metadata:/metadata"
      - "./data/audiobookshelf/config:/config"
    environment:
      - "PUID=1000"
      - "PGID=1000"
      - "TZ=Europe/Amsterdam"
    restart: unless-stopped
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
| `AUDIOBOOKSHELF_PORT` | `13378` | The host port for the Audiobookshelf web interface. |
| `AUDIOBOOKSHELF_PUID` | `1000` | The User ID (PUID) for the container process. Set to 0 for root or match your host user's PUID for file permissions. |
| `AUDIOBOOKSHELF_PGID` | `1000` | The Group ID (PGID) for the container process. Set to 0 for root or match your host user's PGID for file permissions. |
| `AUDIOBOOKSHELF_AUDIOBOOKS_DIR` | `/opt/njorddeploy/data/audiobookshelf/audiobooks` | Host path where your audiobook files are stored and accessible by Audiobookshelf. |
| `AUDIOBOOKSHELF_PODCASTS_DIR` | `/opt/njorddeploy/data/audiobookshelf/podcasts` | Host path where your podcast files are stored and accessible by Audiobookshelf. |
| `AUDIOBOOKSHELF_METADATA_DIR` | `/opt/njorddeploy/data/audiobookshelf/metadata` | Host path to store Audiobookshelf's metadata. |
| `AUDIOBOOKSHELF_CONFIG_DIR` | `/opt/njorddeploy/data/audiobookshelf/config` | Host path to store Audiobookshelf's configuration files. |

---

## 🔑 First-Run Onboarding Guide

Open Audiobookshelf web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://www.audiobookshelf.org/](https://www.audiobookshelf.org/)

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

Deploy **Audiobookshelf** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
