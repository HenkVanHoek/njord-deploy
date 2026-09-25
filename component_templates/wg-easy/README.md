# 🏗️ NjordDeploy: WireGuard Easy

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Network-purple.svg)]()

> All-in-one WireGuard VPN server with a web UI for managing clients and configuration. Requires root privileges with NET_ADMIN and SYS_MODULE capabilities for managing kernel network devices.

- **Source Repository:** [github.com/wg-easy/wg-easy](https://github.com/wg-easy/wg-easy)
- **Container Image:** `ghcr.io/wg-easy/wg-easy`

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
> Tested on Proxmox LXC: docker (22.16.0, 2026-09-14), podman (22.16.0, 2026-09-14); Proxmox VM: docker (22.16.0, 2026-09-14), podman (22.16.0, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  wg-easy:
    image: ghcr.io/wg-easy/wg-easy:latest
    container_name: njorddeploy-wg-easy
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
      - NET_RAW
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
    environment:
      - "WG_HOST=vpn.example.com"
      - "PASSWORD_HASH=$2b$12$U5DIA2y39QuBN0Cv4iZNxu9bb7NROm.gs2Kq.KbIi4uOzjJ3ST5u2"
      - "PORT=51821"
      - "WG_PORT=51820"
      - "WG_DEFAULT_DNS=1.1.1.1"
    volumes:
      - "./data/wg-easy/wireguard:/etc/wireguard"
      - "/lib/modules:/lib/modules:ro"
    ports:
      - "51820:51820/udp"
      - "51821:51821/tcp"
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
| `WG_EASY_WEB_PORT` | `51821` | Host port used to access the WireGuard Easy administration web interface. |
| `WG_EASY_PORT` | `51820` | Public UDP port on which WireGuard VPN traffic will be received. |
| `WG_HOST` | `vpn.example.com` | Public domain name or external IP address that WireGuard clients will use to connect. |
| `WG_PASSWORD_HASH` | `$2b$12$U5DIA2y39QuBN0Cv4iZNxu9bb7NROm.gs2Kq.KbIi4uOzjJ3ST5u2` | Bcrypt password hash used to log in to the WireGuard Easy web management interface (default: change_me). |
| `WG_DEFAULT_DNS` | `1.1.1.1` | DNS server provided to connecting WireGuard clients. |

---

## 🔑 First-Run Onboarding Guide

Open WireGuard Easy web UI and complete the initial onboarding setup.

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

Deploy **WireGuard Easy** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
