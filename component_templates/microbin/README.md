# 🏗️ NjordDeploy: Microbin

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Utilities-purple.svg)]()

> Ultra-lightweight, configurable, feature-rich, self-hosted pastebin service.

- **Upstream Project:** [Microbin](https://microbin.eu/)
- **Source Repository:** [github.com/szabodanika/microbin](https://github.com/szabodanika/microbin)
- **Container Image:** `danielszabo99/microbin:latest`

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
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (2.1.4, 2026-09-14), podman (2.1.4, 2026-09-14); Proxmox VM: docker (2.1.4, 2026-09-14), podman (2.1.4, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  microbin:
    image: danielszabo99/microbin:latest
    container_name: njorddeploy-microbin
    ports:
      - "8080:8080"
    volumes:
      - "data_root/microbin/data:/data"
    environment:
      - PORT=8080
      - DATA_DIR=/data
      - BASE_URL=microbin_base_url
      - ADMIN_PASSWORD=ChangeMeSecurePassword123!
      - MAX_CONTENT_LENGTH_KB=1024
      - DEFAULT_EXPIRATION_SECONDS=0
      - SALT=CHANGEME_SECURELY
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
| `MICROBIN_PORT` | `8080` | The port on the host to access the Microbin web interface. |
| `MICROBIN_BASE_URL` | *None* | The base URL for the Microbin instance (e.g., https://paste.example.com). Leave empty for relative paths. |
| `MICROBIN_ADMIN_PASSWORD` | *None* | The password for the Microbin administration interface. Leave empty for no admin password. |
| `MICROBIN_MAX_CONTENT_LENGTH_KB` | `1024` | Maximum content length for a paste in kilobytes. |
| `MICROBIN_DEFAULT_EXPIRATION_SECONDS` | `0` | Default expiration time for pastes in seconds. 0 means no expiration. |
| `MICROBIN_SALT` | `CHANGEME_SECURELY` | A random salt string for secure hashes. It is HIGHLY RECOMMENDED to change this from the default value. |
| `MICROBIN_HIGHLIGHT_SYNTAX` | `1` |  |
| `MICROBIN_EDITABLE` | `1` |  |

---

## 🔑 First-Run Onboarding Guide

Open Microbin web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://microbin.eu/](https://microbin.eu/)

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

Deploy **Microbin** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
