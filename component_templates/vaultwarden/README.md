# 🏗️ NjordDeploy: Vaultwarden

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Security%20%26%20Utilities-purple.svg)]()

> A lightweight, self-hosted password manager compatible with Bitwarden clients. It provides almost all of the features of the official server without the resource-heavy footprint.

- **Upstream Project:** [Vaultwarden](https://github.com/dani-garcia/vaultwarden)
- **Source Repository:** [github.com/dani-garcia/vaultwarden](https://github.com/dani-garcia/vaultwarden)
- **Container Image:** `vaultwarden/server`

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
> Tested on Proxmox LXC: docker (1.37.4, 2026-10-06), podman (1.37.3, 2026-09-14); Proxmox VM: docker (1.37.3, 2026-09-14), podman (1.37.3, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  vaultwarden:
    image: vaultwarden/server:latest
    container_name: vaultwarden
    restart: unless-stopped
    volumes:
      - './data/vaultwarden:/data'
    ports:
      - '8088:80'
    environment:
      - ADMIN_TOKEN_HASH={{ DOTENV.VAULTWARDEN_ADMIN_TOKEN }}
      - SIGNUPS_ALLOWED=true
      - WEB_VAULT_ENABLED=true
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
| `SIGNUPS_ALLOWED` | `true` | Set to 'true' to allow new users to register, or 'false' to disable registration. |
| `WEB_VAULT_ENABLED` | `true` | Set to 'true' to enable the web-based vault interface. |
| `VAULTWARDEN_WEB_PORT` | `8088` | The external TCP port for the Vaultwarden web interface. |
| `VAULTWARDEN_ADMIN_TOKEN` | `{{ DOTENV.VAULTWARDEN_ADMIN_TOKEN }}` | Secure hashed token for the admin panel. Generate one via `docker exec -it vaultwarden ./vaultwarden hash`. For maximum security, leave this blank in your .env file to disable the admin panel entirely. |

---

## 🔑 First-Run Onboarding Guide

Open the web vault in your browser and click 'Create Account' to establish your master credentials.

- **Upstream Setup Guide:** [https://github.com/dani-garcia/vaultwarden/wiki](https://github.com/dani-garcia/vaultwarden/wiki)

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

Deploy **Vaultwarden** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
