# 🏗️ NjordDeploy: Gluetun

[![Status](https://img.shields.io/badge/Status-beta-f59e0b.svg)]()
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Media%20Stack-purple.svg)]()

> A lightweight, multi-provider VPN client container supporting OpenVPN and WireGuard protocols to route Docker service traffic securely.

- **Upstream Project:** [Gluetun](https://github.com/qdm12/gluetun)
- **Source Repository:** [github.com/qdm12/gluetun](https://github.com/qdm12/gluetun)
- **Container Image:** `ghcr.io/qdm12/gluetun`

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
> Requires NET_ADMIN capability and /dev/net/tun device.
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  gluetun:
    image: "ghcr.io/qdm12/gluetun:latest"
    container_name: njorddeploy-gluetun
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun:/dev/net/tun
    ports:
      - "8000:8000/tcp" # Gluetun control server API
      - "8888:8888/tcp" # HTTP proxy
      - "8388:8388/tcp" # Shadowsocks TCP
      - "8388:8388/udp" # Shadowsocks UDP
    volumes:
      - "./data/gluetun:/gluetun"
    environment:
      - "VPN_SERVICE_PROVIDER=custom"
      - "VPN_TYPE=wireguard"
      - "WIREGUARD_PRIVATE_KEY=wireguard_private_key"
      - "WIREGUARD_ADDRESSES=wireguard_addresses"
      - "VPN_ENDPOINT_IP=vpn_endpoint_ip"
      - "VPN_ENDPOINT_PORT=51820"
      - "TZ=Etc/UTC"
      - "PUID=1000"
      - "PGID=1000"
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
| `GLUETUN_CONTROL_PORT` | `8000` | The port for Gluetun's internal control server API. |
| `GLUETUN_HTTP_PROXY_PORT` | `8888` | The port for the built-in HTTP proxy server. |
| `GLUETUN_SHADOWSOCKS_PORT` | `8388` | The port for the built-in Shadowsocks proxy server (TCP and UDP). |
| `VPN_SERVICE_PROVIDER` | `custom` | Your VPN service provider (e.g., ivpn, nordvpn, private internet access, custom). |
| `VPN_TYPE` | `wireguard` | The VPN protocol type (e.g., openvpn, wireguard). |
| `WIREGUARD_PRIVATE_KEY` | *None* | Your Wireguard private key, if using Wireguard. |
| `WIREGUARD_ADDRESSES` | *None* | Your Wireguard IP addresses (e.g., 10.64.222.21/32), if using Wireguard. |
| `VPN_ENDPOINT_IP` | *None* | The IP address of your VPN server endpoint. Required for 'custom' provider. |
| `VPN_ENDPOINT_PORT` | `51820` | The port of your VPN server endpoint. Required for 'custom' provider. |
| `TZ` | `Etc/UTC` | Container timezone (e.g., Europe/London, America/New_York). |
| `PUID` | `1000` | User ID for permissions. Set to 0 for root if experiencing permission issues. |
| `PGID` | `1000` | Group ID for permissions. Set to 0 for root if experiencing permission issues. |

---

## 🔑 First-Run Onboarding Guide

Open Gluetun web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://github.com/qdm12/gluetun](https://github.com/qdm12/gluetun)

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

Deploy **Gluetun** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
