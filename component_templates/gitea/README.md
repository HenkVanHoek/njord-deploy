# 🏗️ NjordDeploy: Gitea

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Developer-purple.svg)]()

> A painless, self-hosted Git service written in Go with repository management, code review, issues, and wikis.

- **Source Repository:** [github.com/go-gitea/gitea](https://github.com/go-gitea/gitea)
- **Container Image:** `gitea/gitea`

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
> Tested on Proxmox LXC: docker (stable, 2026-09-14), podman (stable, 2026-09-14); Proxmox VM: docker (stable, 2026-09-14), podman (stable, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  gitea:
    image: "gitea/gitea:latest"
    container_name: njorddeploy-gitea
    restart: unless-stopped
    environment:
      - "USER_UID=1000"
      - "USER_GID=1000"
      - "GITEA__database__DB_TYPE=sqlite3"
      - "GITEA__database__PATH=/data/gitea/gitea.db"
      - "GITEA__server__DOMAIN=127.0.0.1"
      - "GITEA__server__SSH_PORT=2222"
      - "GITEA__server__ROOT_URL=http://127.0.0.1:3000/"
      - "GITEA__server__HTTP_PORT=3000"
    volumes:
      - "./data/gitea/data:/data"
      - "/etc/timezone:/etc/timezone:ro"
      - "/etc/localtime:/etc/localtime:ro"
    ports:
      - "3000:3000"
      - "2222:22"
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
| `GITEA_WEB_PORT` | `3000` | Port for the Gitea web interface. |
| `GITEA_SSH_PORT` | `2222` | Port for Git operations over SSH. |
| `HOST_IP` | `127.0.0.1` | IP address or domain name of the host. |

---

## 🔑 First-Run Onboarding Guide

Review database settings and register the initial administrator account at the bottom of the installation page.

- **Default Username / Role:** `admin`
- **Upstream Setup Guide:** [https://docs.gitea.com/installation/install-with-docker](https://docs.gitea.com/installation/install-with-docker)

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

Deploy **Gitea** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
