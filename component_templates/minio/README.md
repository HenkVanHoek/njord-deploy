# 🏗️ NjordDeploy: MinIO S3 Storage

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Storage-purple.svg)]()

> High-performance, S3-compatible enterprise object storage system.

- **Container Image:** `quay.io/minio/minio`

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
> Tested on Proxmox LXC: docker (RELEASE.2025-09-07T16-13-09Z, 2026-09-14), podman (RELEASE.2025-09-07T16-13-09Z, 2026-09-14); Proxmox VM: docker (RELEASE.2025-09-07T16-13-09Z, 2026-09-14), podman (RELEASE.2025-09-07T16-13-09Z, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  minio:
    image: "quay.io/minio/minio:latest"
    container_name: njorddeploy-minio
    restart: unless-stopped
    command: "server /data --console-address ':9001'"
    environment:
      - "MINIO_ROOT_USER=minioadmin"
      - "MINIO_ROOT_PASSWORD=minioadmin_secure_123"
    volumes:
      - "./data/minio/data:/data"
    ports:
      - "9000:9000"
      - "9001:9001"
    user: "0:0"
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
| `MINIO_API_PORT` | `9000` | S3 API communication port. |
| `MINIO_CONSOLE_PORT` | `9001` | Web administration console port. |
| `MINIO_ROOT_USER` | `minioadmin` | Root admin username. |
| `MINIO_ROOT_PASSWORD` | `minioadmin_secure_123` | Root admin password (minimum 8 characters). |

---

## 🔑 First-Run Onboarding Guide

Open MinIO S3 Storage web UI and complete the initial onboarding setup.

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

Deploy **MinIO S3 Storage** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
