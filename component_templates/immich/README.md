# 🏗️ NjordDeploy: Immich

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Media%20Servers-purple.svg)]()

> Immich is a high-performance self-hosted photo and video management solution. It consists of multiple services (server, microservices, machine learning, proxy) and requires a PostgreSQL database and Redis for operation. It is recommended to follow a 3-2-1 backup plan for your precious photos and videos. The Immich services are configured to run as root (`user: "0:0"`) to prevent common permission issues with mounted volumes.

- **Source Repository:** [github.com/immich-app/immich](https://github.com/immich-app/immich)
- **Container Image:** `ghcr.io/immich-app/postgres:14-vectorchord0.4.3-pgvectors0.2.0`

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
> Tested on Proxmox LXC: docker (v3.2.0, 2026-09-14), podman (v3.2.0, 2026-09-14); Proxmox VM: docker (v3.2.0, 2026-09-27), podman (v3.2.0, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  immich-server:
    container_name: njorddeploy-immich-server
    image: ghcr.io/immich-app/immich-server:release
    volumes:
      - "./data/immich/library:/data"
      - "/etc/localtime:/etc/localtime:ro"
    environment:
      - "DB_HOSTNAME=immich-postgres"
      - "DB_USERNAME=postgres"
      - "DB_PASSWORD=ImmichDbPassword123"
      - "DB_DATABASE_NAME=immich"
      - "DB_PORT=5432"
      - "REDIS_HOSTNAME=immich-redis"
      - "REDIS_PORT=6379"
      - "TZ=Etc/UTC"
    ports:
      - "2283:2283"
    networks:
      - njorddeploy_net
    restart: always
    depends_on:
      - immich-postgres
      - immich-redis

  immich-machine-learning:
    container_name: njorddeploy-immich-machine-learning
    image: ghcr.io/immich-app/immich-machine-learning:release
    volumes:
      - "./data/immich/model-cache:/cache"
    environment:
      - "TZ=Etc/UTC"
    networks:
      - njorddeploy_net
    restart: always

  immich-postgres:
    container_name: njorddeploy-immich-postgres
    image: ghcr.io/immich-app/postgres:14-vectorchord0.4.3-pgvectors0.2.0
    environment:
      - "POSTGRES_USER=postgres"
      - "POSTGRES_PASSWORD=ImmichDbPassword123"
      - "POSTGRES_DB=immich"
      - "POSTGRES_INITDB_ARGS=--data-checksums"
      - "PGDATA=/var/lib/postgresql/data"
    volumes:
      - "./data/immich/database:/var/lib/postgresql/data"
    shm_size: 128mb
    networks:
      - njorddeploy_net
    restart: always

  immich-redis:
    container_name: njorddeploy-immich-redis
    image: redis:6.2-alpine
    volumes:
      - "./data/immich/redis:/data"
    networks:
      - njorddeploy_net
    restart: always

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
| `IMMICH_WEB_PORT` | `2283` | The external port for accessing the Immich web interface. |
| `IMMICH_SECRET_KEY` | `dG9wU2VjcmV0S2V5Rm9ySW1taWNoQXBwQWJjMTIzNDU2Nzg5MA==` | A strong secret key for Immich. Keep this secure and do not change it after initial setup. |
| `IMMICH_JWT_SECRET` | `c2Vjb25kU2VjcmV0S2V5Rm9ySW1taWNoQXBwRGVmMTIzNDU2Nzg5MA==` | A strong JWT secret for Immich. Keep this secure and do not change it after initial setup. |
| `IMMICH_API_KEY` | `dGhpcmRTZWNyZXRLZXlGb3JJbW1pY2hBcHBHaGk1Njc4OTA1NDMyMQ==` | A strong API key for Immich. Keep this secure and do not change it after initial setup. |
| `DB_HOSTNAME` | `immich-postgres` | Hostname for the PostgreSQL database service. |
| `DB_USERNAME` | `postgres` | Username for the PostgreSQL database. |
| `DB_PASSWORD` | `ImmichDbPassword123` | Password for the PostgreSQL database user. |
| `DB_DATABASE` | `immich` | Name of the PostgreSQL database. |
| `DB_PORT` | `5432` | Port for the PostgreSQL database service. |
| `REDIS_HOSTNAME` | `immich-redis` | Hostname for the Redis service. |
| `REDIS_PORT` | `6379` | Port for the Redis service. |
| `TZ` | `Etc/UTC` | Specify the timezone for the Immich services (e.g., 'America/New_York', 'Europe/London'). |
| `IMMICH_LOG_LEVEL` | `info` | Set the logging level for Immich services (e.g., 'debug', 'info', 'warn', 'error'). |
| `IMMICH_MACHINE_LEARNING_ENABLED` | `true` | Set to 'true' to enable machine learning features (object detection, facial recognition). Set to 'false' to disable. |
| `IMMICH_MACHINE_LEARNING_URL` | `http://immich-machine-learning:3003` | Internal URL for the Immich machine learning service. |
| `TRAEFIK_HOST` | `immich.henkenyvonne.com` | The hostname to use for Traefik routing to Immich's web UI. E.g., 'immich.yourdomain.com'. |

---

## 🔑 First-Run Onboarding Guide

Navigate to the web interface and click 'Getting Started' to create the root administrator account.

- **Upstream Setup Guide:** [https://immich.app/docs/overview/quick-start](https://immich.app/docs/overview/quick-start)

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

Deploy **Immich** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
