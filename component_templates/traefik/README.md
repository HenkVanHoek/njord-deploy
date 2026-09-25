# 🏗️ NjordDeploy: Traefik

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-reverse_proxy-purple.svg)]()

> A modern, cloud-native reverse proxy and load balancer that automatically discovers services.

- **Upstream Project:** [Traefik](https://traefik.io/traefik/)
- **Source Repository:** [github.com/traefik/traefik](https://github.com/traefik/traefik)
- **Container Image:** `busybox:1.36`

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
> Tested on Proxmox LXC: docker (v3.7.10, 2026-08-16), podman (v3.7.10, 2026-08-16); Proxmox VM: docker (v3.7.13, 2026-09-14), podman (v3.7.10, 2026-08-16).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  traefik-init:
    image: busybox:1.36
    container_name: njorddeploy-traefik-init
    restart: "no"
    volumes:
      - "./data/traefik/acme-storage:/etc/traefik/acme"
    command:
      - "sh"
      - "-c"
      - "touch /etc/traefik/acme/acme.json && chmod 600 /etc/traefik/acme/acme.json"

  traefik:
    image: traefik:latest
    container_name: njorddeploy-traefik
    restart: unless-stopped
    depends_on:
      traefik-init:
        condition: service_completed_successfully
    security_opt:
      - "no-new-privileges:true"

    command:
      - "--api.dashboard=true"
      - "--log.level=INFO"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--entrypoints.dashboard.address=:8080"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"

    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"

    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./data/traefik/acme-storage:/etc/traefik/acme"
      - "./data/traefik/config:/etc/traefik/dynamic/"
      - "./traefik/certs:/etc/traefik/certs:ro"

    networks:
      - njorddeploy_net

    labels:
      - "traefik.enable=true"
      - "traefik.http.middlewares.traefik-auth.basicauth.users=admin:$$apr1$$526B9557$$sKx5.cVfgrd3n2V3bV0S9/"
      - "traefik.http.routers.traefik-dashboard-direct.entrypoints=dashboard"
      - "traefik.http.routers.traefik-dashboard-direct.service=api@internal"
      - "traefik.http.routers.traefik-dashboard-direct.rule=PathPrefix(`/`)"
      - "traefik.http.routers.traefik-dashboard-direct.middlewares=traefik-auth"
      - "traefik.http.routers.traefik-dashboard-secure.rule=Host(`component_id.njorddeploy.com`)"
      - "traefik.http.routers.traefik-dashboard-secure.entrypoints=websecure"
      - "traefik.http.routers.traefik-dashboard-secure.service=api@internal"
      - "traefik.http.routers.traefik-dashboard-secure.tls=true"
      - "traefik.http.routers.traefik-dashboard-secure.middlewares=traefik-auth"
      - "traefik.http.routers.traefik-dashboard-http.rule=Host(`component_id.njorddeploy.com`)"
      - "traefik.http.routers.traefik-dashboard-http.entrypoints=web"

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
| `TRAEFIK_CERTIFICATE_METHOD` | `self-signed` | Select the method for handling SSL certificates. 'self-signed' is the recommended default for local networks and requires no extra setup. 'lets-encrypt' provides a trusted certificate but requires you to own a domain name and forward port 80 from your router to this device. |
| `TRAEFIK_ADMIN_EMAIL` | `{{ DOTENV.LETS_ENCRYPT_REGISTRATION_EMAIL }}` | Your email address, used for Let's Encrypt registration and recovery. |
| `TRAEFIK_WEB_PORT` | `8080` | The external port to access the Traefik dashboard (e.g., 8080). |
| `TRAEFIK_LOG_LEVEL` | `INFO` | Logging verbosity. Options: DEBUG, INFO, WARN, ERROR. |
| `TRAEFIK_ACME_STORAGE_PATH` | `/opt/njorddeploy/data/traefik/acme-storage` | Host directory for storing Let's Encrypt SSL certificates. |
| `TRAEFIK_CONFIG_PATH` | `/opt/njorddeploy/data/traefik/config` | Host directory for Traefik's dynamic configuration files. |
| `DOMAIN_NAME` | `njorddeploy.com` | Your public domain name for dashboard access (e.g., traefik.your.domain). Required for Let's Encrypt. |
| `TRAEFIK_DASHBOARD_USERS` | `admin:$apr1$526B9557$sKx5.cVfgrd3n2V3bV0S9/` | SECURITY CRITICAL: A 'user:hashed_password' pair for dashboard access. You MUST use a tool like 'htpasswd' to generate a compatible md5 hash (apr1 format). The default value is 'admin:password'. For production, generate a new hash, store it in your .env file (e.g., TRAEFIK_USERS_HASH=...), and reference it here using the macro: {{ DOTENV.TRAEFIK_USERS_HASH }}. |

---

## 🔑 First-Run Onboarding Guide

Open Traefik web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://traefik.io/traefik/](https://traefik.io/traefik/)

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

Deploy **Traefik** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
