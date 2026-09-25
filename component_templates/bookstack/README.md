# 🏗️ NjordDeploy: BookStack

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Productivity-purple.svg)]()

> Simple, self-hosted, easy-to-use platform for organizing and storing documentation and wikis in book format.

- **Upstream Project:** [BookStack](https://www.bookstackapp.com/)
- **Container Image:** `linuxserver/mariadb:latest`

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
> Tested on Proxmox LXC: docker (v26.05.4-ls283, 2026-09-14), podman (11.8.8-r0-ls230, 2026-09-14); Proxmox VM: docker (v26.05.4-ls283, 2026-09-14), podman (11.8.8-r0-ls230, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  bookstack:
    image: "lscr.io/linuxserver/bookstack:latest"
    container_name: njorddeploy-bookstack
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - "APP_KEY=base64:J8e0Kz+z56fG0B/1Y76LqQ+2n9NqK48x/5H9mH7vV4A="
      - DB_HOST=bookstack_db
      - DB_PORT=3306
      - DB_USERNAME=bookstack
      - DB_PASSWORD=bookstackpassword
      - DB_DATABASE=bookstackapp
    ports:
      - "8115:80"
    volumes:
      - "./data/bookstack/config:/config"
    depends_on:
      - bookstack_db
    networks:
      - njorddeploy_net

  bookstack_db:
    image: linuxserver/mariadb:latest
    container_name: njorddeploy-bookstack-db
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - MYSQL_ROOT_PASSWORD=mariadbrootpassword
      - MYSQL_DATABASE=bookstackapp
      - MYSQL_USER=bookstack
      - MYSQL_PASSWORD=bookstackpassword
    volumes:
      - "./data/bookstack/db:/config"
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
| `BOOKSTACK_WEB_PORT` | `8115` | BookStack web interface port. |

---

## 🔑 First-Run Onboarding Guide

Initial credentials: admin@admin.com with password 'password'. Change immediately upon login.

- **Default Username / Role:** `admin@admin.com`
- **Upstream Setup Guide:** [https://www.bookstackapp.com/docs/](https://www.bookstackapp.com/docs/)

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

Deploy **BookStack** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
