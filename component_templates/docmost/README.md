# 🏗️ NjordDeploy: Docmost

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Productivity-purple.svg)]()

> Modern open-source collaborative wiki and knowledge-base alternative to Notion and Confluence.

- **Upstream Project:** [Docmost](https://docmost.com/)
- **Source Repository:** [github.com/docmost/docmost](https://github.com/docmost/docmost)
- **Container Image:** `postgres:16-alpine`

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
> Tested on Proxmox LXC: docker (1.19, 2026-09-14), podman (16.15, 2026-09-14); Proxmox VM: docker (16.15, 2026-09-14), podman (1.19, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  docmost:
    image: "docmost/docmost:latest"
    container_name: njorddeploy-docmost
    restart: unless-stopped
    environment:
      - APP_URL=http://localhost:8116
      - APP_SECRET=ChangeMeToSuperSecretString64BytesLong1234567890abcdefghijklm
      - DATABASE_URL=postgresql://docmost:docmostpw@docmost_db:5432/docmost?sslmode=disable
      - REDIS_URL=redis://docmost_redis:6379
    ports:
      - "8116:3000"
    volumes:
      - "./data/docmost/data:/app/data/storage"
    depends_on:
      - docmost_db
      - docmost_redis
    networks:
      - njorddeploy_net

  docmost_db:
    image: postgres:16-alpine
    container_name: njorddeploy-docmost-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=docmost
      - POSTGRES_PASSWORD=docmostpw
      - POSTGRES_DB=docmost
    volumes:
      - "./data/docmost/db:/var/lib/postgresql/data"
    networks:
      - njorddeploy_net

  docmost_redis:
    image: redis:7-alpine
    container_name: njorddeploy-docmost-redis
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
| `DOCMOST_WEB_PORT` | `8116` | Docmost web interface port. |

---

## 🔑 First-Run Onboarding Guide

Create your initial administrative account and setup workspace spaces.

- **Upstream Setup Guide:** [https://docmost.com/docs](https://docmost.com/docs)

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

Deploy **Docmost** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
