# 🏗️ NjordDeploy: AdGuard Home

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-dns_blocker-purple.svg)]()

> AdGuard Home is a free and open-source network-wide software for blocking ads and tracking. It operates as a DNS server that re-routes tracking domains to a “black hole”, thus preventing your devices from connecting to those servers. It provides a web UI for configuration and monitoring. AdGuard Home is capable of running without root privileges, but for persistent volume access, the container is set to run as root (user: 0:0).

- **Upstream Project:** [AdGuard Home](https://adguard.com/en/adguard-home/overview.html)
- **Source Repository:** [github.com/AdguardTeam/AdGuardHome](https://github.com/AdguardTeam/AdGuardHome)
- **Container Image:** `adguard/adguardhome`

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
> Tested on Proxmox LXC: docker (v0.107.79, 2026-09-14), podman (v0.107.79, 2026-09-14); Proxmox VM: docker (v0.107.79, 2026-09-14), podman (v0.107.79, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  adguardhome:
    image: "adguard/adguardhome:latest"
    container_name: njorddeploy-adguardhome
    ports:
      - "80:80/tcp"
      - "3000:3000/tcp"
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - "./data/adguardhome/work:/opt/adguardhome/work"
      - "./data/adguardhome/conf:/opt/adguardhome/conf"
    environment:
      - "TZ=Etc/UTC"
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
| `ADGUARDHOME_WEB_PORT` | `80` | The host port for accessing the AdGuard Home web interface (HTTP). |
| `ADGUARDHOME_DNS_PORT_TCP` | `53` | The host port for AdGuard Home's DNS service (TCP). |
| `ADGUARDHOME_DNS_PORT_UDP` | `53` | The host port for AdGuard Home's DNS service (UDP). |
| `TZ` | `Etc/UTC` | Specify the timezone for the container (e.g., 'America/New_York', 'Europe/London'). |

---

## 🔑 First-Run Onboarding Guide

Access the setup wizard to configure the listening DNS port, web management interface, and create administrator credentials.

- **Default Username / Role:** `admin`
- **Upstream Setup Guide:** [https://github.com/AdguardTeam/AdGuardHome/wiki/Getting-Started](https://github.com/AdguardTeam/AdGuardHome/wiki/Getting-Started)

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

Deploy **AdGuard Home** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
