# 🏗️ NjordDeploy: Nextcloud DB Dumper

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-databases-purple.svg)]()

> An automated backup utility container that periodically exports SQL dumps of the Nextcloud MariaDB database for disaster recovery.

- **Container Image:** `N/A`

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
  - **RAM Profile:** Low
  - **CPU Profile:** Low
  - **Storage:** Persistent
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (10.11.19, 2026-09-14), podman (10.11.19, 2026-09-14); Proxmox VM: docker (10.11.19, 2026-09-14), podman (10.11.19, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  nextcloud-db-dumper:
    image: databack/mysql-backup:latest
    container_name: nextcloud-db-dumper
    restart: always
    command: dump
    labels:
      - "com.centurylinklabs.watchtower.enable=false"
    environment:
      TZ: "Europe/Amsterdam"
      DB_SERVER: "nextcloud-db"
      DB_USER: "nextcloud"
      DB_PASS: "nextcloudpass"
      DB_NAMES: "nextcloud"
      DB_DUMP_CRON: "0 2 * * *"
      DB_DUMP_TARGET: "/backups"
      CLEANUP_OLDER_THAN: "3"
    networks:
      - njorddeploy_net
      - nextcloud-internal
    depends_on:
      - nextcloud-db
    volumes:
      - "./data/nextcloud/db_dumps:/backups"

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
| `NEXTCLOUD_DB_DUMP_PATH` | `/opt/njorddeploy/data/nextcloud/db_dumps` | Host path for storing Nextcloud DB backups. |

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

Deploy **Nextcloud DB Dumper** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
