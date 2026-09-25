# 🏗️ NjordDeploy: n8n

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Productivity-purple.svg)]()

> Fair-code platform to build and deploy AI agents and workflows. Combine a visual canvas with custom code, run it self-hosted, and connect to 1500+ integrations.

- **Upstream Project:** [n8n](https://n8n.io/)
- **Source Repository:** [github.com/n8n-io/n8n](https://github.com/n8n-io/n8n)
- **Container Image:** `n8nio/n8n`

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
> Tested on Proxmox LXC: docker (2.38.7, 2026-09-14), podman (2.38.7, 2026-09-14); Proxmox VM: docker (2.38.7, 2026-09-14), podman (2.38.7, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  n8n:
    image: "n8nio/n8n:latest"
    container_name: njorddeploy-n8n
    ports:
      - "5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n
    environment:
      - "N8N_BASIC_AUTH_ACTIVE=true"
      - "N8N_BASIC_AUTH_USER=njorduser"
      - "N8N_BASIC_AUTH_PASSWORD=CHANGEMEPASSWORD123"
      - "WEBHOOK_URL=http://your-n8n-domain.com"
      - "GENERIC_TIMEZONE=UTC"
      - "N8N_SECURE_COOKIE=false"
    networks:
      - njorddeploy_net

volumes:
  n8n_data:
    name: njorddeploy-n8n-data

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
| `N8N_WEB_PORT` | `5678` | The host port for accessing the n8n web interface. |
| `N8N_BASIC_AUTH_USER` | `njorduser` | Username for n8n basic authentication. |
| `N8N_BASIC_AUTH_PASSWORD` | `CHANGEMEPASSWORD123` | Password for n8n basic authentication. CHANGE THIS IMMEDIATELY! |
| `N8N_WEBHOOK_URL` | `http://your-n8n-domain.com` | The external URL that n8n uses to generate webhook endpoints. This must be accessible from outside the container. For example: http://your-n8n-domain.com or https://your-n8n-domain.com. You can also use a local IP and port (e.g. http://192.168.1.100:5678) if you only use webhooks internally on your local network (LAN) and do not need external triggers from public internet services. |
| `N8N_TIMEZONE` | `UTC` | Set the timezone for n8n. Example: Europe/Berlin or America/New_York. |

---

## 🔑 First-Run Onboarding Guide

Open n8n web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://n8n.io/](https://n8n.io/)

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

Deploy **n8n** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
