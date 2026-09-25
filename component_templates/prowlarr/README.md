# 🏗️ NjordDeploy: Prowlarr

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Media%20Stack-purple.svg)]()

> Prowlarr is an indexer manager/proxy built on the popular *arr .net/reactjs base stack to integrate with your various PVR apps. Prowlarr supports management of both Torrent Trackers and Usenet Indexers.

- **Upstream Project:** [Prowlarr](https://prowlarr.com/)
- **Source Repository:** [github.com/Prowlarr/Prowlarr](https://github.com/Prowlarr/Prowlarr)
- **Container Image:** `lscr.io/linuxserver/prowlarr`

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
> Tested on Proxmox LXC: docker (2.5.2.5491-ls159, 2026-09-14), podman (2.5.2.5491-ls159, 2026-09-14); Proxmox VM: docker (2.5.2.5491-ls159, 2026-09-14), podman (2.5.2.5491-ls159, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  prowlarr:
    container_name: njorddeploy-prowlarr
    image: "lscr.io/linuxserver/prowlarr:latest"
    environment:
      - "PUID=1000"
      - "PGID=1000"
      - "TZ=Europe/Amsterdam"
      - "UMASK_SET=022"
    volumes:
      - "./data/prowlarr/config:/config"
    ports:
      - "9696:9696"
    networks:
      - njorddeploy_net
    restart: unless-stopped
    user: "0:0"

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
| `PROWLARR_WEB_PORT` | `9696` | The port Prowlarr's web interface will be accessible on. |
| `PUID` | `1000` | The User ID (PUID) for the container. Set to your user id for file access. |
| `PGID` | `1000` | The Group ID (PGID) for the container. Set to your group id for file access. |
| `TZ` | `Europe/Amsterdam` | Specify the timezone for the container, e.g., Europe/London, America/New_York. |

---

## 🔑 First-Run Onboarding Guide

Open Prowlarr web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://prowlarr.com/](https://prowlarr.com/)

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

Deploy **Prowlarr** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
