# 🏗️ NjordDeploy: Chatwoot

[![Status](https://img.shields.io/badge/Status-testing-f59e0b.svg)]()
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Communication-purple.svg)]()

> Customer engagement suite, omnichannel support and live chat platform.

- **Upstream Project:** [Chatwoot](https://www.chatwoot.com)
- **Container Image:** `pgvector/pgvector:pg16`

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
> Tested on Proxmox LXC: docker (v4.17.1, 2026-09-16).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  chatwoot-web:
    image: chatwoot/chatwoot:v4.17.1
    container_name: njorddeploy-chatwoot-web
    restart: always
    depends_on:
      chatwoot-postgres:
        condition: service_healthy
      chatwoot-redis:
        condition: service_healthy
    ports:
      - "3044:3000"
    environment:
      - "NODE_ENV=production"
      - "RAILS_ENV=production"
      - "INSTALLATION_ENV=docker"
      - "FRONTEND_URL=https://chat.njorddeploy.com"
      - "SECRET_KEY_BASE=generate_secret_token_placeholder"
      - "POSTGRES_HOST=chatwoot-postgres"
      - "POSTGRES_PORT=5432"
      - "POSTGRES_DATABASE=chatwoot_production"
      - "POSTGRES_USERNAME=chatwoot"
      - "POSTGRES_PASSWORD=chatwoot_secure_pw_2026"
      - "REDIS_URL=redis://:chatwoot_redis_pw_2026@chatwoot-redis:6379"
      - "ACTIVE_STORAGE_SERVICE=local"
      - "SMTP_ADDRESS=smtp.soverin.net"
      - "SMTP_PORT=587"
      - "SMTP_USERNAME=info@njorddeploy.com"
      - "SMTP_PASSWORD=ChangeMeSecurePassword123!"
      - "SMTP_DOMAIN=njorddeploy.com"
      - "SMTP_ENABLE_STARTTLS_AUTO=true"
      - "SMTP_AUTHENTICATION=plain"
      - "MAILER_SENDER_EMAIL=info@njorddeploy.com"
      - "SMTP_OPENSSL_VERIFY_MODE=peer"
      - "ENABLE_ACCOUNT_SIGNUP=false"
      - "ENABLE_RACK_ATTACK_WIDGET_API=true"
    volumes:
      - "/opt/njorddeploy/data/chatwoot/storage:/app/storage"
    entrypoint: docker/entrypoints/rails.sh
    command: ["bundle", "exec", "rails", "s", "-p", "3000", "-b", "0.0.0.0"]
    networks:
      - njorddeploy_net

  chatwoot-worker:
    image: chatwoot/chatwoot:v4.17.1
    container_name: njorddeploy-chatwoot-worker
    restart: always
    depends_on:
      chatwoot-postgres:
        condition: service_healthy
      chatwoot-redis:
        condition: service_healthy
    environment:
      - "NODE_ENV=production"
      - "RAILS_ENV=production"
      - "INSTALLATION_ENV=docker"
      - "FRONTEND_URL=https://chat.njorddeploy.com"
      - "SECRET_KEY_BASE=generate_secret_token_placeholder"
      - "POSTGRES_HOST=chatwoot-postgres"
      - "POSTGRES_PORT=5432"
      - "POSTGRES_DATABASE=chatwoot_production"
      - "POSTGRES_USERNAME=chatwoot"
      - "POSTGRES_PASSWORD=chatwoot_secure_pw_2026"
      - "REDIS_URL=redis://:chatwoot_redis_pw_2026@chatwoot-redis:6379"
      - "ACTIVE_STORAGE_SERVICE=local"
      - "SMTP_ADDRESS=smtp.soverin.net"
      - "SMTP_PORT=587"
      - "SMTP_USERNAME=info@njorddeploy.com"
      - "SMTP_PASSWORD=ChangeMeSecurePassword123!"
      - "SMTP_DOMAIN=njorddeploy.com"
      - "SMTP_ENABLE_STARTTLS_AUTO=true"
      - "SMTP_AUTHENTICATION=plain"
      - "MAILER_SENDER_EMAIL=info@njorddeploy.com"
      - "SMTP_OPENSSL_VERIFY_MODE=peer"
      - "ENABLE_ACCOUNT_SIGNUP=false"
      - "ENABLE_RACK_ATTACK_WIDGET_API=true"
    volumes:
      - "/opt/njorddeploy/data/chatwoot/storage:/app/storage"
    entrypoint: docker/entrypoints/rails.sh
    command: ["bundle", "exec", "sidekiq", "-C", "config/sidekiq.yml"]
    networks:
      - njorddeploy_net

  chatwoot-postgres:
    image: pgvector/pgvector:pg16
    container_name: njorddeploy-chatwoot-postgres
    restart: always
    environment:
      - "POSTGRES_DB=chatwoot_production"
      - "POSTGRES_USER=chatwoot"
      - "POSTGRES_PASSWORD=chatwoot_secure_pw_2026"
    volumes:
      - "/opt/njorddeploy/data/chatwoot/postgres:/var/lib/postgresql/data"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chatwoot -d chatwoot_production"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - njorddeploy_net

  chatwoot-redis:
    image: redis:7-alpine
    container_name: njorddeploy-chatwoot-redis
    restart: always
    command: ["redis-server", "--requirepass", "chatwoot_redis_pw_2026"]
    volumes:
      - "/opt/njorddeploy/data/chatwoot/redis:/data"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "chatwoot_redis_pw_2026", "ping"]
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
| `CHATWOOT_WEB_PORT` | `3044` | The external TCP port on the host for Chatwoot web interface. |
| `FRONTEND_URL` | `https://chat.njorddeploy.com` | Public URL where Chatwoot will be reachable. |
| `SECRET_KEY_BASE` | `generate_secret_token_placeholder` | Secret key used for Rails session encryption. |
| `POSTGRES_PASSWORD` | `chatwoot_secure_pw_2026` | Password for the dedicated Chatwoot PostgreSQL database. |
| `REDIS_PASSWORD` | `chatwoot_redis_pw_2026` | Password for the dedicated Chatwoot Redis cache and worker queue. |

---

## 🔑 First-Run Onboarding Guide

Open the web interface to create your super admin account and configure your inbox channel.

- **Upstream Setup Guide:** [https://www.chatwoot.com/docs](https://www.chatwoot.com/docs)

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

Deploy **Chatwoot** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
