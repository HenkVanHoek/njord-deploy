# 🏗️ NjordDeploy: Prosody

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-general-purple.svg)]()

> Prosody is a modern, lightweight XMPP (Jabber) communication server designed for efficiency and extensibility.

Within the NjordDeploy ecosystem, this component provides a private and secure instant messaging platform. It allows users to host their own chat services, including:

One-to-one messaging: Secure, real-time private conversations.

Multi-User Chat (MUC): Group chat capabilities for family or teams.

HTTP File Upload: Seamless sharing of photos and files directly from your own hardware.

Modern Security: Automated TLS encryption using Let's Encrypt certificates via Nginx Proxy Manager.

Note: This service requires port 5222 (client-to-server) and 5269 (server-to-server) to be forwarded in your router for external access.

- **Upstream Project:** [Prosody](https://prosody.im/)
- **Container Image:** `N/A`

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
  prosody:
    image: prosody/prosody:latest
    container_name: prosody
    restart: unless-stopped
    networks:
      - njorddeploy_net
    ports:
      - "5222:5222"
      - "5269:5269"
    volumes:
      - prosody_config:/etc/prosody
      - prosody_data:/var/lib/prosody
    environment:
      - DOMAIN=localhost
      - ADMIN_USER=admin
      - ADMIN_PASS="ChangeMeSecurePassword123!"
      - MUC_PREFIX=conference
      - UPLOAD_PREFIX=upload

volumes:
  prosody_config:
    name: njorddeploy-prosody-config
  prosody_data:
    name: njorddeploy-prosody-data

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
| `XMPP_DOMAIN` | *None* | The main domain name for your Prosody server (e.g., example.com) |
| `XMPP_ADMIN_USER` | `admin` | The JID for the Admin User. |
| `XMPP_ADMIN_PASSWORD` | *None* | The password for the administrator account. This will be securely stored in the configuration. |
| `XMPP_MUC_PREFIX` | `conference` | The subdomain used for group chats. This value needs to be added as an A or CNAME record for your domain. |
| `XMPP_UPLOAD_PREFIX` | `upload` | The subdomain used for file sharing. This value needs to be added as an A or CNAME record for your domain. |

---

## 🔑 First-Run Onboarding Guide

Background service operating without an independent web interface.

- **Upstream Setup Guide:** [https://prosody.im/](https://prosody.im/)

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

Deploy **Prosody** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
