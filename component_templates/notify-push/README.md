# 🏗️ NjordDeploy: Nextcloud High-Performance Push

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-utilities-purple.svg)]()

> Realtime notification and file-sync daemon for Nextcloud written in Rust.

- **Container Image:** `nextcloud:stable`

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
> Tested on Proxmox LXC: docker (10.11.19, 2026-09-14), podman (10.11.19, 2026-09-14); Proxmox VM: docker (10.11.19, 2026-09-14), podman (10.11.19, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  notify-push:
    image: nextcloud:stable
    container_name: notify-push
    restart: unless-stopped
    depends_on:
      - nextcloud-app
      - nextcloud-db
      - nextcloud-redis
    environment:
      TZ: "Europe/Amsterdam"
      PORT: "7867"
      NEXTCLOUD_URL: "https://nextcloud.notify-push.home.lan"
    volumes:
      - "./data/notify-push:/var/www/html"
    entrypoint:
      - /bin/sh
      - -c
      - |
        ARCH=$$(uname -m)
        if [ "$$ARCH" = "arm64" ] || [ "$$ARCH" = "aarch64" ]; then
            BINARY_ARCH="aarch64"
        elif [ "$$ARCH" = "x86_64" ] || [ "$$ARCH" = "amd64" ]; then
            BINARY_ARCH="x86_64"
        elif [ "$$ARCH" = "armv7l" ] || [ "$$ARCH" = "armv7" ]; then
            BINARY_ARCH="armv7"
        else
            BINARY_ARCH="$$ARCH"
        fi

        BINARY="/var/www/html/custom_apps/notify_push/bin/$$BINARY_ARCH/notify_push"

        if [ -f "$$BINARY" ] && [ -f /var/www/html/config/config.php ]; then
            echo "Starting notify_push for architecture $$BINARY_ARCH..."
            exec "$$BINARY" /var/www/html/config/config.php
        else
            echo "Warning: notify_push binary ($$BINARY) or config.php not found."
            echo "Standby mode active. Waiting for Nextcloud installation and Client Push app activation..."
            while true; do
                sleep 3600
            done
        fi
    networks:
      - njorddeploy_net
      - nextcloud-internal

networks:
  njorddeploy_net:
  nextcloud-internal:
    name: nextcloud-internal
```

Start the service:
```bash
docker compose up -d
```

---

## ⚙️ Configuration & Environment Variables

No specific environment variables required.

---

## 🔑 First-Run Onboarding Guide

Background service operating without an independent web interface.

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

Deploy **Nextcloud High-Performance Push** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
