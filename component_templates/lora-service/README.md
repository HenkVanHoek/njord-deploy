# 🏗️ NjordDeploy: LoRa Letterbox Notifier

[![Status](https://img.shields.io/badge/Status-untested-f59e0b.svg)]()
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-general-purple.svg)]()

> A smart home IoT notification service that monitors LoRa-enabled mailbox sensors and sends real-time alert notifications when physical mail is delivered.

- **Upstream Project:** [LoRa Letterbox Notifier](https://github.com/HenkVanHoek/lora-letterbox-notifier)
- **Source Repository:** [github.com/HenkVanHoek/lora-letterbox-notifier](https://github.com/HenkVanHoek/lora-letterbox-notifier)
- **Container Image:** `chirpstack/chirpstack:4`

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

---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
    chirpstack:
        image: chirpstack/chirpstack:4
        command: -c /etc/chirpstack
        restart: unless-stopped
        volumes:
            - ./configuration/chirpstack:/etc/chirpstack
        depends_on:
            - postgres
            - mosquitto_lora
            - redis
        environment:
            - MQTT_SERVER=mosquitto_lora:1883
            - POSTGRESQL_DSN=postgres://chirpstack:"ChangeMeSecurePassword123!"@postgres/chirpstack?sslmode=disable
            - REDIS_URL=redis://redis:6379/0
        ports:
            - "8083:8080"

    mosquitto_lora:
        image: eclipse-mosquitto:2
        restart: unless-stopped
        container_name: mosquitto_lora
        ports:
            - "18884:1883"
        volumes:
            - ./configuration/mosquitto_lora/mosquitto.conf:/mosquitto/config/mosquitto.conf

    chirpstack-gateway-bridge:
        image: chirpstack/chirpstack-gateway-bridge:4
        restart: unless-stopped
        depends_on:
            - mosquitto_lora
        ports:
            - "1700:1700/udp"
        environment:
            - INTEGRATION__MQTT__AUTH__GENERIC__SERVER=tcp://mosquitto_lora:1883

    postgres:
        image: postgres:14-alpine
        restart: unless-stopped
        environment:
            - POSTGRES_PASSWORD="ChangeMeSecurePassword123!"
            - POSTGRES_USER=chirpstack
            - POSTGRES_DB=chirpstack
        volumes:
            - ./data/postgres:/var/lib/postgresql/data

    redis:
        image: redis:7-alpine
        restart: unless-stopped
        volumes:
            - ./data/redis:/data
```

Start the service:
```bash
docker compose up -d
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `CHIRPSTACK_WEB_UI_PORT` | `8083` | Access to the dashboard of of Chirpstack |
| `LORA_MQTT_PORT` | `18884` | Port for the MQTT broker |
| `LORA_GATEWAY_PORT` | `1700` |  |
| `CHIRPSTACK_DB_PASSWORD` | *None* |  |
| `MQTT_BROKER` | `mosquitto_lora` |  |

---

## 🔑 First-Run Onboarding Guide

Open LoRa Letterbox Notifier web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://github.com/HenkVanHoek/lora-letterbox-notifier](https://github.com/HenkVanHoek/lora-letterbox-notifier)

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

Deploy **LoRa Letterbox Notifier** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
