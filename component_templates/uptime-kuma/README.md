# 🏗️ NjordDeploy: Uptime Kuma

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-System%20Tools-purple.svg)]()

> A feature-rich, self-hosted monitoring tool providing real-time status pages, HTTP/ping health checks, and alerts via multiple notification channels.

- **Upstream Project:** [Uptime Kuma](https://uptime.kuma.pet/)
- **Source Repository:** [github.com/louislam/uptime-kuma](https://github.com/louislam/uptime-kuma)
- **Container Image:** `louislam/uptime-kuma:1`

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
> Tested on Proxmox LXC: docker (1.22.19, 2026-09-14), podman (18.20.3, 2026-09-14); Proxmox VM: docker (18.20.3, 2026-09-14), podman (18.20.3, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    volumes:
      - "./data/uptime-kuma/data:/app/data"
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
    ports:
      - "3001:3001"
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
| `UPTIME_KUMA_WEB_PORT` | `3001` | The external port to access the Uptime Kuma web interface. The internal port is 3001. |
| `UPTIME_KUMA_DATA_PATH` | `/opt/njorddeploy/data/uptime-kuma/data` | The host machine path where Uptime Kuma's configuration data will be stored. |

---

## 🔑 First-Run Onboarding Guide

Create your initial administrator username and password upon first visiting the web UI.

- **Default Username / Role:** `admin`
- **Upstream Setup Guide:** [https://github.com/louislam/uptime-kuma/wiki](https://github.com/louislam/uptime-kuma/wiki)

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

Deploy **Uptime Kuma** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
