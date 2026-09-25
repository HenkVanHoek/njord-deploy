# 🏗️ NjordDeploy: Plausible Analytics

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Utilities-purple.svg)]()

> Plausible is a lightweight, open-source and privacy-friendly Google Analytics alternative without cookies and fully compliant with GDPR, CCPA and PECR.

- **Upstream Project:** [Plausible Analytics](https://plausible.io/)
- **Source Repository:** [github.com/plausible/community-edition](https://github.com/plausible/community-edition)
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
> Tested on Proxmox LXC: docker (v3.2.1, 2026-09-14), podman (1.19, 2026-09-14); Proxmox VM: docker (v3.2.1, 2026-09-14), podman (1.19, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  plausible:
    image: "ghcr.io/plausible/community-edition:v3.2.1"
    container_name: njorddeploy-plausible
    restart: unless-stopped
    command: sh -c "until /entrypoint.sh db createdb; do echo 'Waiting for databases to be ready...'; sleep 3; done && /entrypoint.sh db migrate && /entrypoint.sh run"
    depends_on:
      - njorddeploy-plausible-db
      - njorddeploy-plausible-events-db
    ports:
      - "8000:8000"
    environment:
      - "BASE_URL=http://localhost:8000"
      - "SECRET_KEY_BASE=MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3"
      - "TOTP_VAULT_KEY=MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="
      - "DATABASE_URL=postgres://postgres:plausible_secure_postgres_pass@njorddeploy-plausible-db:5432/plausible_db"
      - "CLICKHOUSE_DATABASE_URL=http://njorddeploy-plausible-events-db:8123/plausible_events_db"
      - "HTTP_PORT=8000"
    networks:
      - njorddeploy_net

  njorddeploy-plausible-db:
    image: postgres:16-alpine
    container_name: njorddeploy-plausible-db
    restart: unless-stopped
    user: "0:0"
    volumes:
      - "./data/plausible/db-data:/var/lib/postgresql/data"
    environment:
      - "POSTGRES_DB=plausible_db"
      - "POSTGRES_USER=postgres"
      - "POSTGRES_PASSWORD=plausible_secure_postgres_pass"
    networks:
      - njorddeploy_net

  njorddeploy-plausible-events-db:
    image: clickhouse/clickhouse-server:24.12-alpine
    container_name: njorddeploy-plausible-events-db
    restart: unless-stopped
    user: "0:0"
    volumes:
      - "./data/plausible/event-data:/var/lib/clickhouse"
      - "./data/plausible/event-logs:/var/log/clickhouse-server"
      - "data_root/plausible/logs.xml:/etc/clickhouse-server/config.d/logs.xml:ro"
      - "data_root/plausible/ipv4-only.xml:/etc/clickhouse-server/config.d/ipv4-only.xml:ro"
      - "data_root/plausible/low-resources.xml:/etc/clickhouse-server/config.d/low-resources.xml:ro"
      - "data_root/plausible/default-profile-low-resources-overrides.xml:/etc/clickhouse-server/users.d/default-profile-low-resources-overrides.xml:ro"
    environment:
      - "CLICKHOUSE_SKIP_USER_SETUP=1"
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
| `PLAUSIBLE_WEB_PORT` | `8000` | The external HTTP port for accessing the Plausible web UI. |
| `PLAUSIBLE_BASE_URL` | `http://localhost:8000` | The domain or URL where Plausible will be accessed (e.g. http://192.168.1.50:8000 or https://analytics.example.com). |
| `PLAUSIBLE_SECRET_KEY_BASE` | `MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3` | A 64+ character random string used for session encryption (generate with V8OoCXdxEwZXASKz5/rGF1TCSIG3Os9Z5/gTA0H8l8gg0OxVJdbqCO+XTxNsu/vM). |
| `PLAUSIBLE_TOTP_VAULT_KEY` | `MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE=` | A 32-byte Base64-encoded key for encrypting 2FA TOTP secrets (generate with mpPzJaVW0iIkfPcqQu2ND2PFVb4RE74ORVdOAqDYUlw=). |
| `POSTGRES_DB` | `plausible_db` | The PostgreSQL database name for Plausible. |
| `POSTGRES_USER` | `postgres` | The PostgreSQL user for Plausible. |
| `POSTGRES_PASSWORD` | `plausible_secure_postgres_pass` | The PostgreSQL password for Plausible. |

---

## 🔑 First-Run Onboarding Guide

Open Plausible Analytics web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://plausible.io/](https://plausible.io/)

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

Deploy **Plausible Analytics** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
