# 🏗️ NjordDeploy: GeoLens

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Utilities-purple.svg)]()

> Self-hosted geospatial data catalog and interactive web map builder with PostGIS, vector tiles, OGC API support, and semantic spatial search.

- **Upstream Project:** [GeoLens](https://getgeolens.com)
- **Source Repository:** [github.com/geolens-io/geolens](https://github.com/geolens-io/geolens)
- **Container Image:** `ghcr.io/geolens-io/geolens-frontend:latest`

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
> Multi-arch ARM64/AMD64. Runs PostGIS, FastAPI, Vite web client.
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  geolens-web:
    image: ghcr.io/geolens-io/geolens-frontend:latest
    container_name: njorddeploy-geolens-web
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - geolens-api
    networks:
      - njorddeploy_net

  geolens-api:
    image: ghcr.io/geolens-io/geolens-api:latest
    container_name: njorddeploy-geolens-api
    restart: unless-stopped
    ports:
      - "8001:8000"
    depends_on:
      - geolens-db
    environment:
      - "POSTGRES_HOST=geolens-db"
      - "POSTGRES_DB=geolens"
      - "POSTGRES_USER=geolens"
      - "POSTGRES_PASSWORD=ChangeMeSecurePassword123!"
    volumes:
      - "./data/geolens/data/storage:/data/storage"
    networks:
      - njorddeploy_net

  geolens-db:
    image: postgis/postgis:16-3.4-alpine
    container_name: njorddeploy-geolens-db
    restart: unless-stopped
    environment:
      - "POSTGRES_DB=geolens"
      - "POSTGRES_USER=geolens"
      - "POSTGRES_PASSWORD=ChangeMeSecurePassword123!"
    volumes:
      - "./data/geolens/data/db:/var/lib/postgresql/data"
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
| `PORT_GEOLENS` | `8080` | Port to access the GeoLens Web Map interface. |
| `GEOLENS_API_PORT` | `8001` | Port for the GeoLens FastAPI and OGC API endpoints. |
| `GEOLENS_DATA_PATH` | `/opt/njorddeploy/data/geolens/data` | Host path for storing datasets and PostGIS database. |
| `GEOLENS_DB_PASSWORD` | `ChangeMeSecurePassword123!` | Password for internal PostGIS relational store. |

---

## 🔑 First-Run Onboarding Guide

Navigate to http://<server-ip>:8080 and initialize the administrator account to start creating GIS datasets and maps.

- **Default Username / Role:** `admin`
- **Upstream Setup Guide:** [https://docs.getgeolens.com](https://docs.getgeolens.com)

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

Deploy **GeoLens** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
