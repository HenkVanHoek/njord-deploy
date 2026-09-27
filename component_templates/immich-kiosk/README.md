# 🏗️ NjordDeploy: Immich Kiosk

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Media%20Servers-purple.svg)]()

> Immich Kiosk is an ambient digital photo frame and slideshow client designed for smart TVs, tablets, and wall displays powered by your Immich server.

- **Upstream Project:** [Immich Kiosk](https://github.com/damongolding/immich-kiosk)
- **Source Repository:** [github.com/damongolding/immich-kiosk](https://github.com/damongolding/immich-kiosk)
- **Container Image:** `ghcr.io/damongolding/immich-kiosk`

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
  - **Storage:** Ephemeral
> **Platform Verification Notes:**
> Tested on Proxmox VM: docker (v3.2.2, 2026-09-27).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  immich-kiosk:
    container_name: njorddeploy-immich-kiosk
    image: ghcr.io/damongolding/immich-kiosk:0.44.1
    tty: true
    restart: unless-stopped
    ports:
      - "2284:3000"
    environment:
      - "KIOSK_IMMICH_URL=http://njorddeploy-immich-server:2283"
      - "KIOSK_IMMICH_API_KEY=initial_setup_token"
      - "KIOSK_DURATION=60"
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
| `IMMICH_KIOSK_PORT` | `2284` | Port to access the Immich Kiosk web interface. |
| `KIOSK_IMMICH_URL` | `http://njorddeploy-immich-server:2283` | Internal or external URL to the Immich server (e.g. http://njorddeploy-immich-server:2283). |
| `KIOSK_IMMICH_API_KEY` | `initial_setup_token` | API Key generated in Immich (Account Settings -> API Keys). |
| `KIOSK_DURATION` | `60` | Duration in seconds each photo remains on screen. |

---

## 🔑 First-Run Onboarding Guide

Generate an API key in Immich (Account Settings -> API Keys) and provide it via KIOSK_IMMICH_API_KEY or in config/config.yaml to start displaying your albums.

- **Upstream Setup Guide:** [https://docs.immichkiosk.app/](https://docs.immichkiosk.app/)

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

Deploy **Immich Kiosk** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
