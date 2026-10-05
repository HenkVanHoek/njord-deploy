# 🏗️ NjordDeploy: Pi-hole

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-dns_blocker-purple.svg)]()

> A network-wide ad and tracker blocker that functions as a DNS sinkhole, protecting all local network devices without requiring client-side software.

- **Upstream Project:** [Pi-hole](https://pi-hole.net/)
- **Source Repository:** [github.com/pi-hole/docker-pi-hole](https://github.com/pi-hole/docker-pi-hole)
- **Container Image:** `pihole/pihole:latest`

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
> Tested on Proxmox LXC: docker (2026.09.0, 2026-10-05), podman (2026.07.2, 2026-09-14); Proxmox VM: docker (2026.07.2, 2026-09-14), podman (2026.07.2, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  pi-hole:
    container_name: njorddeploy-component_id
    image: pihole/pihole:latest
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8088:80/tcp"
    environment:
      TZ: 'Etc/UTC'
      FTLCONF_webserver_api_password: "pi"
      FTLCONF_dns_listeningMode: "all"
      VIRTUAL_HOST: "pi-hole.pi-hole.home.lan"
    volumes:
      - "pihole_etc:/etc/pihole"
      - "pihole_dnsmasq:/etc/dnsmasq.d"
    cap_add:
      - NET_ADMIN
    networks:
      - njorddeploy_net
volumes:
  pihole_etc:
    name: "njorddeploy-pihole-etc"
  pihole_dnsmasq:
    name: "njorddeploy-pihole-dnsmasq"

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
| `PIHOLE_WEB_PASSWORD` | `pi` | A strong password for the web UI. Required for a clean installation. |
| `PIHOLE_WEB_PORT` | `8088` | The external HTTP port to access the Pi-hole web UI. |
| `PIHOLE_DNS_PORT` | `53` | The external port for DNS queries. Must be 53 for most use cases. |

---

## 🔑 First-Run Onboarding Guide

Log in to the web administration console using the password configured in service variables (PIHOLE_WEB_PASSWORD).

- **Upstream Setup Guide:** [https://docs.pi-hole.net/](https://docs.pi-hole.net/)

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

Deploy **Pi-hole** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
