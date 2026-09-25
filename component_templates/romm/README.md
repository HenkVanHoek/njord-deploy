# 🏗️ NjordDeploy: RomM

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Media-purple.svg)]()

> A web-based retro ROMs manager and player for managing your game library.

- **Source Repository:** [github.com/zurdi15/romm](https://github.com/zurdi15/romm)
- **Container Image:** `mariadb:11`

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
> Tested on Proxmox LXC: docker (11.8.9, 2026-09-14), podman (11.8.9, 2026-09-14); Proxmox VM: docker (11.8.9, 2026-09-14), podman (11.8.9, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  romm:
    image: "ghcr.io/zurdi15/romm:latest"
    container_name: njorddeploy-romm
    restart: unless-stopped
    environment:
      - "ROMM_AUTH_SECRET_KEY=f47ac10b58cc4372a5670e02b2c3d4e5"
      - "DB_HOST=njorddeploy-romm-db"
      - "DB_NAME=romm"
      - "DB_USER=romm_user"
      - "DB_PASSWD=romm_db_secure_pass_123"
    volumes:
      - "./data/romm/resources:/romm/resources"
      - "./data/romm/library:/romm/library"
      - "./data/romm/assets:/romm/assets"
      - "./data/romm/config:/romm/config"
    ports:
      - "8090:8080"
    depends_on:
      - romm-db
    user: "0:0"
    networks:
      - njorddeploy_net

  romm-db:
    image: mariadb:11
    container_name: njorddeploy-romm-db
    restart: unless-stopped
    environment:
      - "MARIADB_ROOT_PASSWORD=romm_db_secure_pass_123"
      - "MARIADB_DATABASE=romm"
      - "MARIADB_USER=romm_user"
      - "MARIADB_PASSWORD=romm_db_secure_pass_123"
    volumes:
      - "./data/romm/mysql:/var/lib/mysql"
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
| `ROMM_WEB_PORT` | `8090` | Port for the RomM web interface. |
| `ROMM_AUTH_SECRET_KEY` | `f47ac10b58cc4372a5670e02b2c3d4e5` | Secret key for authentication (32-character string). |
| `ROMM_DB_PASSWORD` | `romm_db_secure_pass_123` | Password for MariaDB romm database. |

---

## 🔑 First-Run Onboarding Guide

Open RomM web UI and complete the initial onboarding setup.

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

Deploy **RomM** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
