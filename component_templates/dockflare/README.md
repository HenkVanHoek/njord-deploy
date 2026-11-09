# 🏗️ NjordDeploy: DockFlare

[![Status](https://img.shields.io/badge/Status-untested-f59e0b.svg)]()
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-reverse_proxy-purple.svg)]()

> Automate Cloudflare Tunnels and Zero Trust access policies using Docker labels with an intuitive web UI dashboard.

- **Upstream Project:** [DockFlare](https://github.com/ChrispyBacon-dev/DockFlare)
- **Source Repository:** [github.com/ChrispyBacon-dev/DockFlare](https://github.com/ChrispyBacon-dev/DockFlare)
- **Container Image:** `tecnativa/docker-socket-proxy:v0.4.1`

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
  - **RAM Profile:** Low
  - **CPU Profile:** Low
  - **Storage:** Persistent

---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  dockflare:
    image: "alplat/dockflare:stable"
    container_name: njorddeploy-dockflare
    restart: unless-stopped
    ports:
      - "8120:5000"
    volumes:
      - "./data/dockflare/data:/app/data"
    environment:
      - REDIS_URL=redis://dockflare-redis:6379/0
      - REDIS_DB_INDEX=0
      - DOCKER_HOST=tcp://dockflare-socket-proxy:2375
      - INTERNAL_BOOTSTRAP_SECRET=dockflare-secret-token-change-me-32chars!
    depends_on:
      - dockflare-socket-proxy
      - dockflare-redis
    networks:
      - njorddeploy_net

  dockflare-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: njorddeploy-dockflare-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - njorddeploy_net

  dockflare-redis:
    image: redis:7-alpine
    container_name: njorddeploy-dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - "./data/dockflare/redis:/data"
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
| `DOCKFLARE_WEB_PORT` | `8120` | DockFlare web dashboard port. |
| `DOCKFLARE_BOOTSTRAP_SECRET` | `dockflare-secret-token-change-me-32chars!` | Internal secret token used by DockFlare to authenticate internal API communications. |

---

## 🔑 First-Run Onboarding Guide

Open DockFlare and connect your Cloudflare API token or account credentials to begin automating tunnels.

- **Upstream Setup Guide:** [https://github.com/ChrispyBacon-dev/DockFlare](https://github.com/ChrispyBacon-dev/DockFlare)

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

Deploy **DockFlare** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
