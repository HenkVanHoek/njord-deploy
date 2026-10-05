# 🏗️ NjordDeploy: Mealie

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Productivity-purple.svg)]()

> A self-hosted recipe manager, meal planner, and shopping list with a RestAPI backend and a reactive frontend built in Vue for a pleasant user experience for the whole family. Easily add recipes into your database by providing the URL and Mealie will automatically import the relevant data, or add a family recipe with the UI editor. The Mealie Docker image often supports PUID/PGID environment variables for file ownership within the container, even if the container runs as root.

- **Source Repository:** [github.com/mealie-recipes/mealie](https://github.com/mealie-recipes/mealie)
- **Container Image:** `ghcr.io/mealie-recipes/mealie`

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
> Tested on Proxmox LXC: docker (v3.28.0, 2026-10-05), podman (v3.26.0, 2026-09-14); Proxmox VM: docker (v3.26.0, 2026-09-14), podman (v3.26.0, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  mealie:
    container_name: njorddeploy-mealie
    image: "ghcr.io/mealie-recipes/mealie:latest"
    ports:
      - "9925:9000"
    environment:
      - "TZ=Etc/UTC"
      - "PUID=1000"
      - "PGID=1000"
      - "MEALIE_DATA_DIR=/app/data"
      - "MEALIE_PORT=9000"
    volumes:
      - "./data/mealie/data:/app/data"
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
| `MEALIE_WEB_PORT` | `9925` | The external port for accessing the Mealie web interface. |
| `PUID` | `1000` | User ID for the Mealie container. Used by the application internally for file ownership. Set to match the owner of the mounted volume for best permissions. |
| `PGID` | `1000` | Group ID for the Mealie container. Used by the application internally for file ownership. Set to match the group of the mounted volume for best permissions. |
| `TZ` | `Etc/UTC` | Specify the timezone for the Mealie container (e.g., 'America/New_York', 'Etc/UTC'). |

---

## 🔑 First-Run Onboarding Guide

Open Mealie web UI and complete the initial onboarding setup.

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

Deploy **Mealie** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
