# 🏗️ NjordDeploy: TeslaMate

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Smart%20Home%20%26%20IoT-purple.svg)]()

> Self-hosted data logger for your Tesla vehicle with detailed driving, battery, and charging analytics.

- **Upstream Project:** [TeslaMate](https://docs.teslamate.org/)
- **Source Repository:** [github.com/teslamate-org/teslamate](https://github.com/teslamate-org/teslamate)
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
> Tested on Proxmox LXC: docker (v4.2.0, 2026-09-14), podman (1.19, 2026-09-14); Proxmox VM: docker (v4.2.0, 2026-09-14), podman (16.15, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  teslamate:
    image: "teslamate/teslamate:latest"
    container_name: njorddeploy-teslamate
    restart: unless-stopped
    environment:
      - ENCRYPTION_KEY=supersecretencryptionkey123456789
      - DATABASE_USER=teslamate
      - DATABASE_PASS=secretpassword
      - DATABASE_NAME=teslamate
      - DATABASE_HOST=teslamate_db
      - MQTT_HOST=mosquitto
    ports:
      - "4000:4000"
    depends_on:
      - teslamate_db
    networks:
      - njorddeploy_net

  teslamate_db:
    image: postgres:16-alpine
    container_name: njorddeploy-teslamate-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=teslamate
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=teslamate
    volumes:
      - "./data/teslamate/db:/var/lib/postgresql/data"
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
| `TESLAMATE_WEB_PORT` | `4000` | TeslaMate web interface port. |

---

## 🔑 First-Run Onboarding Guide

Generate and paste your Tesla API tokens in TeslaMate to begin telemetry collection.

- **Upstream Setup Guide:** [https://docs.teslamate.org/](https://docs.teslamate.org/)

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

Deploy **TeslaMate** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
