# 🏗️ NjordDeploy: Nextcloud

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Productivity-purple.svg)]()

> A comprehensive self-hosted productivity and collaboration suite offering secure file storage, online document editing, calendar, and contacts synchronization.

- **Upstream Project:** [Nextcloud](https://nextcloud.com/)
- **Source Repository:** [github.com/nextcloud/server](https://github.com/nextcloud/server)
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
  - **RAM Profile:** Medium
  - **CPU Profile:** Medium
  - **Storage:** Persistent
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (10.11.19, 2026-09-18), podman (10.11.19, 2026-09-14); Proxmox VM: docker (10.11.19, 2026-09-14), podman (10.11.19, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  nextcloud-app:
    image: nextcloud:stable
    container_name: nextcloud-app
    restart: always
    labels:
      - "com.centurylinklabs.watchtower.enable=false"
    depends_on:
      - nextcloud-db
      - nextcloud-redis
    ports:
      - "8080:80"
    networks:
      - njorddeploy_net
      - nextcloud-internal
    volumes:
      - "./data/nextcloud/data:/var/www/html"
    environment:
      TZ: "Europe/Amsterdam"
      MYSQL_PASSWORD: "ChangeMeSecurePassword123!"
      MYSQL_DATABASE: "nextcloud_db"
      MYSQL_USER: "nextcloud_user"
      MYSQL_HOST: "nextcloud-db"
      REDIS_HOST: "nextcloud-redis"
      NEXTCLOUD_TRUSTED_DOMAINS: "nextcloud.home.lan"
      MAIL_FROM_ADDRESS: "nextcloud"
      MAIL_DOMAIN: "example.com"
      SMTP_HOST: "smtp.example.com"
      SMTP_PORT: "587"
      SMTP_SECURE: "tls"
      SMTP_AUTHTYPE: "LOGIN"
      SMTP_AUTH: "true"
      SMTP_NAME: "notifications@example.com"
      SMTP_PASSWORD: "ChangeMeSecurePassword123!"

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

| Variable | Default Value | Description |
|---|---|---|
| `PORT_NEXTCLOUD` | `8080` | Port to access the Nextcloud web interface. |
| `NEXTCLOUD_DATA_PATH` | `/opt/njorddeploy/data/nextcloud/data` | Host path for storing Nextcloud application data and files. |
| `NEXTCLOUD_TRUSTED_DOMAINS` | `nextcloud.home.lan` | Space-separated list of domains Nextcloud will trust. |
| `NEXTCLOUD_MAIL_FROM_ADDRESS` | `nextcloud` | The sender name for system notifications. |
| `NEXTCLOUD_MAIL_DOMAIN` | `example.com` | The email domain for system notifications. |
| `NEXTCLOUD_MAIL_SMTPHOST` | `smtp.example.com` | The SMTP server address for outgoing mails. |
| `NEXTCLOUD_MAIL_SMTPPORT` | `587` | The SMTP port (e.g. 587 or 465). |
| `NEXTCLOUD_MAIL_SMTPSECURE` | `tls` | SMTP security layer (tls or ssl). |
| `NEXTCLOUD_MAIL_SMTPNAME` | `notifications@example.com` | The email address used to log into the SMTP server. |
| `NEXTCLOUD_MAIL_SMTPPASSWORD` | *None* | The password for the SMTP user. |

---

## 🔑 First-Run Onboarding Guide

Enter your desired administrator credentials on the initial setup page to initialize the Nextcloud instance.

- **Default Username / Role:** `admin`
- **Upstream Setup Guide:** [https://docs.nextcloud.com/](https://docs.nextcloud.com/)

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

Deploy **Nextcloud** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
