# 🏗️ NjordDeploy: Homepage

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-dashboard%20%26%20Homepages-purple.svg)]()

> A modern, fully static, fast, secure fully proxied, highly customizable application dashboard with integrations for over 100 services and translations into multiple languages. Easily configured via YAML files or through docker label discovery. Homepage does not include an authentication layer itself; it is recommended to place it behind a reverse proxy with authentication if exposed to untrusted networks. For optimal file permissions on mounted volumes, the container is configured to run as root (user: 0:0) by default, overriding the PUID/PGID environment variables if set. Note: Docker integration requiring access to /var/run/docker.sock is not enabled by default for security reasons. Users can manually add this volume mount if needed.

- **Upstream Project:** [Homepage](https://gethomepage.dev/)
- **Source Repository:** [github.com/gethomepage/homepage](https://github.com/gethomepage/homepage)
- **Container Image:** `ghcr.io/gethomepage/homepage`

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
> Tested on Proxmox LXC: docker (v2.4.0, 2026-10-05), podman (v2.3.0, 2026-09-14); Proxmox VM: docker (v2.3.0, 2026-09-14), podman (v2.3.0, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  homepage:
    image: "ghcr.io/gethomepage/homepage:latest"
    container_name: njorddeploy-homepage
    environment:
      - "HOMEPAGE_ALLOWED_HOSTS=*"
      - "PUID=1000"
      - "PGID=1000"
    ports:
      - "3000:3000"
    volumes:
      - "./data/homepage/config:/app/config"
    restart: unless-stopped
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
| `HOMEPAGE_WEB_PORT` | `3000` | The port on the host that Homepage's web interface will be accessible on. |
| `HOMEPAGE_ALLOWED_HOSTS` | `*` | Comma-separated list of allowed hostnames/IPs. Required for security. See Homepage documentation for details. Example: 'yourdomain.com,192.168.1.100:3000' or '*' for all. |
| `PUID` | `1000` | User ID for the container. Set to 0 for root. Note: The container is configured to run as root (0:0) by default to prevent permission issues with mounted volumes, but this variable is provided for advanced customization. |
| `PGID` | `1000` | Group ID for the container. Set to 0 for root. Note: The container is configured to run as root (0:0) by default to prevent permission issues with mounted volumes, but this variable is provided for advanced customization. |

---

## 🔑 First-Run Onboarding Guide

Open Homepage web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://gethomepage.dev/](https://gethomepage.dev/)

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

Deploy **Homepage** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
