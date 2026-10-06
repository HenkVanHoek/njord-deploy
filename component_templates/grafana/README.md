# 🏗️ NjordDeploy: Grafana Stack

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-System%20Tools-purple.svg)]()

> An open-source visualization and analytics platform that turns metrics and logs into dynamic, interactive dashboards for comprehensive system observability.

- **Upstream Project:** [Grafana Stack](https://grafana.com/)
- **Source Repository:** [github.com/grafana/grafana](https://github.com/grafana/grafana)
- **Container Image:** `grafana/grafana-oss`

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
> Tested on Proxmox LXC: docker (11.1.3, 2026-10-06), podman (11.1.3, 2026-09-14); Proxmox VM: docker (11.1.3, 2026-09-14), podman (11.1.3, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  grafana:
    container_name: njorddeploy-grafana
    user: "0:0"
    image: "grafana/grafana-oss:11.1.3"
    ports:
      - "3000:3000"
    volumes:
      - "./data/grafana/data:/var/lib/grafana"
      - "data_root/grafana/provisioning:/etc/grafana/provisioning:ro"
    environment:
      - "GF_SECURITY_ADMIN_PASSWORD=NjB4N2E1YjQzYjU2Y2QxMjM0NTY3ODkwYQ=="
    restart: unless-stopped
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
| `GRAFANA_WEB_PORT` | `3000` | External port for the Grafana UI |
| `GRAFANA_DATA_PATH` | `/opt/njorddeploy/data/grafana/data` | Host path for Grafana persistent data |
| `GRAFANA_ADMIN_PASSWORD` | `NjB4N2E1YjQzYjU2Y2QxMjM0NTY3ODkwYQ==` | Admin password for the Grafana UI |

---

## 🔑 First-Run Onboarding Guide

Sign in as 'admin' using the password configured in GRAFANA_ADMIN_PASSWORD.

- **Default Username / Role:** `admin`
- **Upstream Setup Guide:** [https://grafana.com/docs/grafana/latest/getting-started/](https://grafana.com/docs/grafana/latest/getting-started/)

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

Deploy **Grafana Stack** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
