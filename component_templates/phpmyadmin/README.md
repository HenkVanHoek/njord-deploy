# 🏗️ NjordDeploy: phpMyAdmin

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-databases-purple.svg)]()

> A comprehensive web-based administration tool for managing MySQL and MariaDB databases, executing SQL queries, and managing user access control.

- **Upstream Project:** [phpMyAdmin](https://www.phpmyadmin.net/)
- **Container Image:** `phpmyadmin`

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
  - **CPU Profile:** Low
  - **Storage:** Persistent
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (5.2.3, 2026-09-14), podman (5.2.3, 2026-09-14); Proxmox VM: docker (5.2.3, 2026-09-14), podman (5.2.3, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  phpmyadmin:
    image: phpmyadmin:latest
    container_name: njorddeploy-phpmyadmin
    restart: unless-stopped
    environment:
      PMA_HOST: ${PMA_HOST:-mariadb}
      PMA_PORT: 3306
      PMA_ARBITRARY: 1
      MYSQL_ROOT_PASSWORD: ${DB_PASS:-}
    ports:
      - "${PHPMYADMIN_WEB_PORT:-8083}:80"
    volumes:
      - "data_root/phpmyadmin/config/config.inc.php:/etc/phpmyadmin/config.inc.php"
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
| `PHPMYADMIN_WEB_PORT` | `8083` | The host port on which phpMyAdmin will be accessible. |
| `PMA_HOST` | `mariadb` | The hostname of the MariaDB database service. |
| `PHPMYADMIN_BLOWFISH_SECRET` | `32_random_secret_string_blowfish` | Blowfish secret passphrase for cookie authentication encryption. |

---

## 🔑 First-Run Onboarding Guide

Open phpMyAdmin web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://www.phpmyadmin.net/](https://www.phpmyadmin.net/)

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

Deploy **phpMyAdmin** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
