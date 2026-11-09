# 🏗️ NjordDeploy: Karakeep

[![Status](https://img.shields.io/badge/Status-untested-f59e0b.svg)]()
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-News%20%26%20Bookmarks-purple.svg)]()

> Self-hostable bookmark-everything app (links, notes, and images) with AI-based automatic tagging and full-text search.

- **Upstream Project:** [Karakeep](https://github.com/karakeep-app/karakeep)
- **Source Repository:** [github.com/karakeep-app/karakeep](https://github.com/karakeep-app/karakeep)
- **Container Image:** `ghcr.io/karakeep-app/karakeep-chrome:release`

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

---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  karakeep:
    image: "ghcr.io/karakeep-app/karakeep:release"
    container_name: njorddeploy-karakeep
    restart: unless-stopped
    ports:
      - "8121:3000"
    environment:
      - MEILI_ADDR=http://karakeep-meilisearch:7700
      - MEILI_MASTER_KEY=ChangeMeMeiliSearchMasterKeyKarakeep2026!
      - BROWSER_WEB_URL=http://karakeep-chrome:9222
      - NEXTAUTH_SECRET=ChangeMeNextAuthSecretKeyKarakeep32CharsLong!
      - NEXTAUTH_URL=http://localhost:8121
      - DATA_DIR=/data
    volumes:
      - "./data/karakeep/data:/data"
    depends_on:
      - karakeep-meilisearch
      - karakeep-chrome
    networks:
      - njorddeploy_net

  karakeep-chrome:
    image: ghcr.io/karakeep-app/karakeep-chrome:release
    container_name: njorddeploy-karakeep-chrome
    restart: unless-stopped
    networks:
      - njorddeploy_net

  karakeep-meilisearch:
    image: getmeili/meilisearch:v1.12.0
    container_name: njorddeploy-karakeep-meilisearch
    restart: unless-stopped
    environment:
      - MEILI_MASTER_KEY=ChangeMeMeiliSearchMasterKeyKarakeep2026!
      - MEILI_NO_ANALYTICS=true
    volumes:
      - "./data/karakeep/meili_data:/meili_data"
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
| `KARAKEEP_WEB_PORT` | `8121` | Karakeep web interface port. |
| `KARAKEEP_NEXTAUTH_SECRET` | `ChangeMeNextAuthSecretKeyKarakeep32CharsLong!` | Random secret key used by NextAuth to sign and encrypt session tokens. |
| `KARAKEEP_MEILI_MASTER_KEY` | `ChangeMeMeiliSearchMasterKeyKarakeep2026!` | Master API key used to secure the Meilisearch search engine instance. |

---

## 🔑 First-Run Onboarding Guide

Open Karakeep web UI to register your administrator account and start saving bookmarks.

- **Upstream Setup Guide:** [https://docs.karakeep.com](https://docs.karakeep.com)

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

Deploy **Karakeep** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
