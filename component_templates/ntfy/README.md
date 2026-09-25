# 🏗️ NjordDeploy: ntfy

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Utilities-purple.svg)]()

> ntfy (pronounced 'notify') is a simple HTTP-based pub-sub notification service. With ntfy, you can send notifications to your phone or desktop via scripts from any computer, without having to sign up or pay any fees. It runs as root (0:0) to manage file permissions on mounted volumes.

- **Source Repository:** [github.com/binwiederhier/ntfy](https://github.com/binwiederhier/ntfy)
- **Container Image:** `binwiederhier/ntfy`

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
> Tested on Proxmox LXC: docker (stable, 2026-09-14), podman (stable, 2026-09-14); Proxmox VM: docker (stable, 2026-09-14), podman (stable, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  ntfy:
    image: "binwiederhier/ntfy:latest"
    container_name: njorddeploy-ntfy
    command:
      - serve
    environment:
      - "TZ=UTC"
      - "NTFY_BASE_URL=http://localhost:8077"
      - "NTFY_CACHE_FILE=/var/cache/ntfy/cache.db"
      - "NTFY_ATTACHMENT_CACHE_DIR=/var/cache/ntfy/attachments"
    user: "0:0"
    volumes:
      - "./data/ntfy/cache:/var/cache/ntfy"
      - "data_root/ntfy/server.yml:/etc/ntfy/server.yml:ro"
    ports:
      - "8077:80"
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
| `NTFY_WEB_PORT` | `8077` | The host port for the ntfy web interface and API. |
| `TZ` | `UTC` | Set the container timezone (e.g., Europe/London, America/New_York). |
| `NTFY_BASE_URL` | `http://localhost:8077` | The base URL for ntfy, used for generating links in notifications. Change 'localhost' to your server's IP address or domain name, and '8077' to the actual host port if different. |
| `NTFY_CACHE_FILE` | `/var/cache/ntfy/cache.db` | Path to the ntfy cache database file within the container. This should typically point inside the mounted cache volume. |
| `NTFY_ATTACHMENT_CACHE_DIR` | `/var/cache/ntfy/attachments` | Path to the directory for storing attachment caches within the container. This should typically point inside the mounted cache volume. |

---

## 🔑 First-Run Onboarding Guide

Open ntfy web UI and complete the initial onboarding setup.

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

Deploy **ntfy** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
