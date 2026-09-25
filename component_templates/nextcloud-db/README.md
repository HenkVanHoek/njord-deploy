# 🏗️ NjordDeploy: Nextcloud MariaDB

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-databases-purple.svg)]()

> A dedicated, pre-configured MariaDB relational database server optimized for Nextcloud persistent data storage and high query performance.

- **Container Image:** `mariadb:10.11`

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
  - **RAM Profile:** High
  - **CPU Profile:** Medium
  - **Storage:** Persistent
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (10.11.19, 2026-09-14), podman (10.11.19, 2026-09-14); Proxmox VM: docker (10.11.19, 2026-09-14), podman (10.11.19, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  nextcloud-db:
    image: mariadb:10.11
    container_name: nextcloud-db
    restart: always
    command: >
      --transaction-isolation=READ-COMMITTED
      --log-bin=binlog
      --binlog-format=ROW
    labels:
      - "com.centurylinklabs.watchtower.enable=false"
    networks:
      - njorddeploy_net
      - nextcloud-internal
    volumes:
      - "./data/nextcloud/db:/var/lib/mysql"
    environment:
      TZ: "Europe/Amsterdam"
      MYSQL_ROOT_PASSWORD: "ChangeMeSecurePassword123!"
      MYSQL_PASSWORD: "ChangeMeSecurePassword123!"
      MYSQL_DATABASE: "nextcloud"
      MYSQL_USER: "nextcloud"

networks:
  njorddeploy_net:
  nextcloud-internal:
    name: nextcloud-internal
```

Start the service:
```bash
docker compose up -d
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `NEXTCLOUD_DB_PATH` | `/opt/njorddeploy/data/nextcloud/db` | Host path for storing Nextcloud DB files. |
| `NEXTCLOUD_DB_ROOT_PASSWORD` | *None* | Root password for MariaDB database engine. |
| `NEXTCLOUD_DB_NAME` | `nextcloud` | Name of the Nextcloud database schema. |
| `NEXTCLOUD_DB_USER` | `nextcloud` | Username for Nextcloud DB connection. |
| `NEXTCLOUD_DB_PASSWORD` | *None* | Database user connection password. |

---

## 🔑 First-Run Onboarding Guide

Background service operating without an independent web interface.

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

Deploy **Nextcloud MariaDB** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
