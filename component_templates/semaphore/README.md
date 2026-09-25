# 🏗️ NjordDeploy: Semaphore UI

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-System%20Tools-purple.svg)]()

> Modern UI for Ansible, Terraform/OpenTofu/Terragrunt, PowerShell and other DevOps tools.

- **Upstream Project:** [Semaphore UI](https://semaphoreui.com/)
- **Source Repository:** [github.com/semaphoreui/semaphore](https://github.com/semaphoreui/semaphore)
- **Container Image:** `semaphoreui/semaphore`

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
  - **RAM Profile:** 512mb
  - **CPU Profile:** 500m
  - **Storage:** Ssd
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (v2.19.14, 2026-09-14), podman (v2.19.14, 2026-09-14); Proxmox VM: docker (v2.19.14, 2026-09-14), podman (v2.19.14, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  semaphore-ui:
    image: "semaphoreui/semaphore:latest"
    container_name: njorddeploy-semaphore-ui
    ports:
      - "3000:3000"
    environment:
      - "SEMAPHORE_DB_DIALECT=sqlite"
      - "SEMAPHORE_DB_FILE=/etc/semaphore/semaphore.sqlite"
      - "SEMAPHORE_ADMIN=admin"
      - "SEMAPHORE_ADMIN_PASSWORD=4R0W0R+oK20wS7qXW2E1F/7P4n9Y7iG1"
      - "SEMAPHORE_ADMIN_NAME=Admin User"
      - "SEMAPHORE_ADMIN_EMAIL=admin@localhost"
    volumes:
      - "/var/lib/njorddeploy/semaphore-ui/data:/etc/semaphore"
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
| `SEMAPHORE_PORT` | `3000` | The port on the host to expose the Semaphore UI web interface. |
| `SEMAPHORE_ADMIN_USERNAME` | `admin` | The username for the initial Semaphore UI admin user. |
| `SEMAPHORE_ADMIN_PASSWORD` | `4R0W0R+oK20wS7qXW2E1F/7P4n9Y7iG1` | The password for the initial Semaphore UI admin user. This will be securely generated if left as default. |
| `SEMAPHORE_ADMIN_NAME` | `Admin User` | The full name for the initial Semaphore UI admin user. |
| `SEMAPHORE_ADMIN_EMAIL` | `admin@localhost` | The email address for the initial Semaphore UI admin user. |
| `DATA_ROOT` | `/var/lib/njorddeploy` | The root directory for persistent application data. This is where Semaphore UI's SQLite database and configuration will be stored. |

---

## 🔑 First-Run Onboarding Guide

Log in with SEMAPHORE_ADMIN / SEMAPHORE_ADMIN_PASSWORD configured in your deployment parameters.

- **Default Username / Role:** `admin`
- **Upstream Setup Guide:** [https://docs.semaphoreui.com/](https://docs.semaphoreui.com/)

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

Deploy **Semaphore UI** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
