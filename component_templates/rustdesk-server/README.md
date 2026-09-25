# 🏗️ NjordDeploy: RustDesk Server

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-System%20%26%20Tools-purple.svg)]()

> Self-hosted rendezvous and relay server for RustDesk remote desktop clients.

- **Upstream Project:** [RustDesk Server](https://rustdesk.com/)
- **Source Repository:** [github.com/rustdesk/rustdesk-server](https://github.com/rustdesk/rustdesk-server)
- **Container Image:** `rustdesk/rustdesk-server`

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
> Tested on Proxmox LXC: docker (1.1.16, 2026-09-14), podman (1.1.16, 2026-09-14); Proxmox VM: docker (1.1.16, 2026-09-14), podman (1.1.16, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  hbbs:
    image: "rustdesk/rustdesk-server:latest"
    container_name: njorddeploy-rustdesk-hbbs
    command: hbbs
    restart: unless-stopped
    ports:
      - "21115:21115"
      - "21116:21116"
      - "21116:21116/udp"
      - "21118:21118"
    volumes:
      - "./data/rustdesk:/root"
    networks:
      - njorddeploy_net

  hbbr:
    image: "rustdesk/rustdesk-server:latest"
    container_name: njorddeploy-rustdesk-hbbr
    command: hbbr
    restart: unless-stopped
    ports:
      - "21117:21117"
      - "21119:21119"
    volumes:
      - "./data/rustdesk:/root"
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
| `RUSTDESK_HBBS_PORT` | `21116` | RustDesk Server web interface port. |

---

## 🔑 First-Run Onboarding Guide

RustDesk server is active. Obtain your public key from /root/id_ed25519.pub in container.

- **Upstream Setup Guide:** [https://rustdesk.com/docs/en/self-host/](https://rustdesk.com/docs/en/self-host/)

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

Deploy **RustDesk Server** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
