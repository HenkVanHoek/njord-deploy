# 🏗️ NjordDeploy: Rybbit

[![Status](https://img.shields.io/badge/Status-untested-f59e0b.svg)]()
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Utilities-purple.svg)]()

> Open-source, cookie-free, and privacy-friendly web analytics platform designed as an intuitive alternative to Google Analytics.

- **Upstream Project:** [Rybbit](https://github.com/rybbit-io/rybbit)
- **Source Repository:** [github.com/rybbit-io/rybbit](https://github.com/rybbit-io/rybbit)
- **Container Image:** `caddy:2-alpine`

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

---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  rybbit:
    image: caddy:2-alpine
    container_name: njorddeploy-rybbit
    restart: unless-stopped
    ports:
      - "8122:80"
    command:
      - /bin/sh
      - -c
      - |
        cat << 'EOF' > /etc/caddy/Caddyfile
        :80 {
            encode zstd gzip
            handle /api/* {
                reverse_proxy rybbit-backend:3001
            }
            handle /.well-known/* {
                reverse_proxy rybbit-backend:3001
            }
            handle {
                reverse_proxy rybbit-client:3002
            }
        }
        EOF
        exec caddy run --config /etc/caddy/Caddyfile
    depends_on:
      - rybbit-client
      - rybbit-backend
    networks:
      - njorddeploy_net

  rybbit-backend:
    image: ghcr.io/rybbit-io/rybbit-backend:latest
    container_name: njorddeploy-rybbit-backend
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - CLICKHOUSE_HOST=http://rybbit-clickhouse:8123
      - CLICKHOUSE_DB=analytics
      - CLICKHOUSE_USER=default
      - CLICKHOUSE_PASSWORD=ChangeMeDatabasePasswordRybbit2026!
      - CLICKHOUSE_QUERY_PASSWORD=ChangeMeDatabasePasswordRybbit2026!
      - POSTGRES_HOST=rybbit-postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=analytics
      - POSTGRES_USER=frog
      - POSTGRES_PASSWORD=ChangeMeDatabasePasswordRybbit2026!
      - REDIS_HOST=rybbit-redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=ChangeMeDatabasePasswordRybbit2026!
      - BETTER_AUTH_SECRET=ChangeMeAuthSecretKeyRybbit32CharsLong2026!
      - BASE_URL=http://localhost:8122
      - DISABLE_SIGNUP=false
      - DISABLE_TELEMETRY=true
      - CLUSTER_WORKERS=2
    depends_on:
      - rybbit-clickhouse
      - rybbit-postgres
      - rybbit-redis
    networks:
      - njorddeploy_net

  rybbit-client:
    image: ghcr.io/rybbit-io/rybbit-client:latest
    container_name: njorddeploy-rybbit-client
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_BACKEND_URL=http://localhost:8122
      - NEXT_PUBLIC_DISABLE_SIGNUP=false
    depends_on:
      - rybbit-backend
    networks:
      - njorddeploy_net

  rybbit-postgres:
    image: postgres:17-alpine
    container_name: njorddeploy-rybbit-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=frog
      - POSTGRES_PASSWORD=ChangeMeDatabasePasswordRybbit2026!
      - POSTGRES_DB=analytics
    volumes:
      - "./data/rybbit/postgres:/var/lib/postgresql/data"
    networks:
      - njorddeploy_net

  rybbit-clickhouse:
    image: clickhouse/clickhouse-server:24-alpine
    container_name: njorddeploy-rybbit-clickhouse
    restart: unless-stopped
    environment:
      - CLICKHOUSE_DB=analytics
      - CLICKHOUSE_USER=default
      - CLICKHOUSE_PASSWORD=ChangeMeDatabasePasswordRybbit2026!
      - CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1
    volumes:
      - "./data/rybbit/clickhouse:/var/lib/clickhouse"
    networks:
      - njorddeploy_net

  rybbit-redis:
    image: redis:7-alpine
    container_name: njorddeploy-rybbit-redis
    restart: unless-stopped
    command: ["redis-server", "--requirepass", "ChangeMeDatabasePasswordRybbit2026!", "--appendonly", "yes"]
    volumes:
      - "./data/rybbit/redis:/data"
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
| `RYBBIT_WEB_PORT` | `8122` | Rybbit web analytics dashboard port. |
| `RYBBIT_AUTH_SECRET` | `ChangeMeAuthSecretKeyRybbit32CharsLong2026!` | Secret key (32+ characters) used for securing authentication tokens. |
| `RYBBIT_DB_PASSWORD` | `ChangeMeDatabasePasswordRybbit2026!` | Password used for internal Postgres, Redis, and ClickHouse databases. |

---

## 🔑 First-Run Onboarding Guide

Open Rybbit web UI and navigate to /signup to create your initial administrator account and register your websites.

- **Upstream Setup Guide:** [https://rybbit.com/docs](https://rybbit.com/docs)

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

Deploy **Rybbit** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
