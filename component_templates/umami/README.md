# 🏗️ NjordDeploy: Umami Analytics

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Utilities-purple.svg)]()

> Umami is an open-source, privacy-focused alternative to Google Analytics. It provides lightweight web analytics without collecting personal data or using tracking cookies.

- **Upstream Project:** [Umami Analytics](https://umami.is/)
- **Source Repository:** [github.com/umami-software/umami](https://github.com/umami-software/umami)
- **Container Image:** `postgres:15-alpine`

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
> Tested on Proxmox LXC: docker (postgresql-latest, 2026-10-05), podman (1.19, 2026-09-14); Proxmox VM: docker (postgresql-latest, 2026-09-14), podman (1.19, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  umami:
    image: "ghcr.io/umami-software/umami:postgresql-latest"
    container_name: njorddeploy-umami
    restart: unless-stopped
    user: "0:0"
    ports:
      - "3000:3000"
    environment:
      - "DATABASE_URL=postgresql://umami:umami_secure_db_pass@njorddeploy-umami-db:5432/umami"
      - "APP_SECRET=random_umami_secret_salt_32_chars_min"
    depends_on:
      njorddeploy-umami-db:
        condition: service_healthy
    networks:
      - njorddeploy_net

  njorddeploy-umami-db:
    image: postgres:15-alpine
    container_name: njorddeploy-umami-db
    restart: unless-stopped
    user: "0:0"
    environment:
      - "POSTGRES_DB=umami"
      - "POSTGRES_USER=umami"
      - "POSTGRES_PASSWORD=umami_secure_db_pass"
    volumes:
      - "./data/umami/db:/var/lib/postgresql/data"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U umami -d umami"]
      interval: 5s
      timeout: 5s
      retries: 5
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
| `UMAMI_WEB_PORT` | `3000` | The external port for accessing the Umami web interface. |
| `POSTGRES_DB` | `umami` | The database name for Umami. |
| `POSTGRES_USER` | `umami` | The database user for Umami. |
| `POSTGRES_PASSWORD` | `umami_secure_db_pass` | The database password for the Umami database user. |
| `UMAMI_APP_SECRET` | `random_umami_secret_salt_32_chars_min` | A random salt string used by Umami for session encryption. |

---

## 🔑 First-Run Onboarding Guide

Open Umami Analytics web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://umami.is/](https://umami.is/)

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

Deploy **Umami Analytics** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
