# 🏗️ NjordDeploy: Conduit (Matrix Server)

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-general-purple.svg)]()

> A high-performance, lightweight Matrix chat homeserver written in Rust, specifically optimized for low-resource environments like the Raspberry Pi.

- **Upstream Project:** [Conduit (Matrix Server)](https://conduit.rs/)
- **Source Repository:** [github.com/famedly/conduit](https://github.com/famedly/conduit)
- **Container Image:** `matrixconduit/matrix-conduit`

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
> Tested on Proxmox LXC: docker (latest, 2026-09-14), podman (latest, 2026-09-14); Proxmox VM: docker (latest, 2026-09-14), podman (latest, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  matrix-conduit:
    container_name: njorddeploy-conduit
    image: matrixconduit/matrix-conduit:latest
    restart: unless-stopped
    ports:
      - "6167:6167"
    volumes:
      - "./data/conduit:/var/lib/matrix-conduit"
    environment:
      - "CONDUIT_CONFIG="
      - "CONDUIT_DATABASE_PATH=/var/lib/matrix-conduit"
      - "CONDUIT_SERVER_NAME=conduit.local"
      - "CONDUIT_DATABASE_BACKEND=rocksdb"
      - "CONDUIT_PORT=6167"
      - "CONDUIT_ALLOW_REGISTRATION=true"
      - "CONDUIT_ALLOW_FEDERATION=true"
      - "CONDUIT_MAX_REQUEST_SIZE=20000000"
      - "CONDUIT_TRUSTED_SERVERS=[\"matrix.org\"]"
      - "PUID=1000"
      - "PGID=1000"
      - "TZ=Europe/Amsterdam"
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
| `` | `6167` | The port to access the Conduit Matrix homeserver. |
| `` | `conduit.local` | The server name/domain name for the Matrix homeserver (e.g. yourdomain.com). |

---

## 🔑 First-Run Onboarding Guide

Background service operating without an independent web interface.

- **Upstream Setup Guide:** [https://conduit.rs/](https://conduit.rs/)

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

Deploy **Conduit (Matrix Server)** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
