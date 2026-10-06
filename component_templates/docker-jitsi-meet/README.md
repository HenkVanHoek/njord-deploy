# 🏗️ NjordDeploy: jitsi-meet

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Communication-purple.svg)]()

> Jitsi Meet is a collection of open-source projects that provides a secure, simple, and scalable video conferencing solution. This component sets up a complete Jitsi Meet instance with optional Etherpad collaboration and recording capabilities.

- **Upstream Project:** [jitsi-meet](https://jitsi.org/)
- **Source Repository:** [github.com/jitsi/docker-jitsi-meet](https://github.com/jitsi/docker-jitsi-meet)
- **Container Image:** `jitsi/prosody:stable`

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
  - **RAM Profile:** High
  - **CPU Profile:** High
  - **Storage:** Persistent
> **Platform Verification Notes:**
> Tested on Proxmox LXC: docker (3.3.3, 2026-09-14), podman (3.3.3, 2026-09-14); Proxmox VM: docker (3.3.3, 2026-09-14), podman (3.3.3, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  prosody:
    container_name: njorddeploy-jitsi-prosody
    image: jitsi/prosody:stable
    hostname: xmpp.meet.jitsi
    networks:
      - njorddeploy_net
    volumes:
      - "data_root/jitsi/prosody/config:/config"
      - "data_root/jitsi/prosody/plugins:/prosody-plugins-custom"
    environment:
      - XMPP_SERVER=prosody
      - XMPP_DOMAIN=meet.jitsi
      - XMPP_AUTH_DOMAIN=auth.meet.jitsi
      - XMPP_INTERNAL_MUC_DOMAIN=internal-muc.meet.jitsi
      - JICOFO_AUTH_USER=jicofo
      - JICOFO_AUTH_PASSWORD=changeme
      - JVB_AUTH_USER=jvb
      - JVB_AUTH_PASSWORD=changeme
      - JICOFO_COMPONENT_SECRET=changeme
      - PUBLIC_URL=https://meet.example.com
      - JVB_PORT=10000
      - ENABLE_XMPP_WEBSOCKET=${ENABLE_XMPP_WEBSOCKET}

      - ENABLE_AUTH=1
      - ENABLE_GUEST=1
      - ENABLE_GUESTS=1
      - ENABLE_GUEST_IS_GUEST=1
      - AUTH_TYPE=internal

  jicofo:
    container_name: njorddeploy-jitsi-jicofo
    image: jitsi/jicofo:stable
    networks:
      - njorddeploy_net
    volumes:
      - "data_root/jitsi/jicofo:/config"
    environment:
      - XMPP_SERVER=prosody
      - XMPP_DOMAIN=meet.jitsi
      - XMPP_AUTH_DOMAIN=auth.meet.jitsi
      - XMPP_INTERNAL_MUC_DOMAIN=internal-muc.meet.jitsi
      - JICOFO_AUTH_USER=jicofo
      - JICOFO_AUTH_PASSWORD=changeme
      - JVB_AUTH_USER=jvb
      - JVB_AUTH_PASSWORD=changeme
      - JICOFO_COMPONENT_SECRET=changeme
      - PUBLIC_URL=https://meet.example.com
      - JVB_PORT=10000

      - ENABLE_AUTH=1
      - ENABLE_GUEST=1
      - ENABLE_GUESTS=1
      - ENABLE_GUEST_IS_GUEST=1

  jvb:
    container_name: njorddeploy-jitsi-jvb
    image: jitsi/jvb:stable
    networks:
      - njorddeploy_net
    ports:
      - "10000:10000/udp"
      - "3030:3030/tcp"
    volumes:
      - "data_root/jitsi/jvb:/config"
    environment:
      - XMPP_SERVER=prosody
      - XMPP_DOMAIN=meet.jitsi
      - XMPP_AUTH_DOMAIN=auth.meet.jitsi
      - XMPP_INTERNAL_MUC_DOMAIN=internal-muc.meet.jitsi
      - JICOFO_AUTH_USER=jicofo
      - JICOFO_AUTH_PASSWORD=changeme
      - JVB_AUTH_USER=jvb
      - JVB_AUTH_PASSWORD=changeme
      - JICOFO_COMPONENT_SECRET=changeme
      - PUBLIC_URL=https://meet.example.com
      - JVB_PORT=10000
      - DOCKER_HOST_ADDRESS=${DOCKER_HOST_ADDRESS}
      - ENABLE_COLIBRI_WEBSOCKET=${ENABLE_COLIBRI_WEBSOCKET}

  web:
    container_name: njorddeploy-jitsi-web
    image: jitsi/web:stable
    networks:
      - njorddeploy_net
    ports:
      - "8001:80"
      - "8443:443"
    volumes:
      - "data_root/jitsi/web:/config"
    environment:
      - XMPP_SERVER=prosody
      - XMPP_DOMAIN=meet.jitsi
      - XMPP_AUTH_DOMAIN=auth.meet.jitsi
      - XMPP_INTERNAL_MUC_DOMAIN=internal-muc.meet.jitsi
      - JICOFO_AUTH_USER=jicofo
      - JICOFO_AUTH_PASSWORD=changeme
      - JVB_AUTH_USER=jvb
      - JVB_AUTH_PASSWORD=changeme
      - JICOFO_COMPONENT_SECRET=changeme
      - PUBLIC_URL=https://meet.example.com
      - JVB_PORT=10000

      - ENABLE_AUTH=1
      - ENABLE_GUEST=1
      - ENABLE_GUESTS=1
      - ENABLE_GUEST_IS_GUEST=1
      - AUTH_TYPE=internal

      - ENABLE_XMPP_WEBSOCKET=${ENABLE_XMPP_WEBSOCKET}

      - ETHERPAD_PUBLIC_URL=https://meet.example.com/etherpad

  etherpad:
    container_name: njorddeploy-jitsi-etherpad
    image: etherpad/etherpad:latest
    networks:
      - njorddeploy_net
    volumes:
      - "data_root/jitsi/etherpad:/opt/etherpad-lite/var"

  jibri:
    container_name: njorddeploy-jitsi-jibri
    image: jitsi/jibri:stable
    networks:
      - njorddeploy_net
    volumes:
      - "data_root/jitsi/jibri:/config"
    environment:
      - XMPP_SERVER=prosody
      - XMPP_DOMAIN=meet.jitsi
      - XMPP_AUTH_DOMAIN=auth.meet.jitsi
      - XMPP_INTERNAL_MUC_DOMAIN=internal-muc.meet.jitsi
      - JICOFO_AUTH_USER=jicofo
      - JICOFO_AUTH_PASSWORD=changeme
      - JVB_AUTH_USER=jvb
      - JVB_AUTH_PASSWORD=changeme
      - JICOFO_COMPONENT_SECRET=changeme
      - PUBLIC_URL=https://meet.example.com
      - JVB_PORT=10000

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
| `JITSI_PUBLIC_URL` | `https://meet.example.com` | The public domain or IP address where Jitsi Meet will be accessible. |
| `JITSI_HTTP_PORT` | `8001` | Host port for HTTP traffic. |
| `JITSI_HTTPS_PORT` | `8443` | Host port for HTTPS traffic. |
| `JITSI_JVB_PORT` | `10000` | The UDP port for media streaming routing (essential for audio/video connectivity). |
| `JICOFO_AUTH_PASSWORD` | `changeme` | Secure password for internal signaling. |
| `JVB_AUTH_PASSWORD` | `changeme` | Secure password for internal media bridge authentication. |
| `JICOFO_COMPONENT_SECRET` | `changeme` | Secure component secret for XMPP server authentication. |
| `JITSI_ENABLE_AUTH` | `true` | If enabled, only registered users can create rooms. Guests can join without credentials. |
| `JITSI_ENABLE_ETHERPAD` | `true` | Enables collaborative real-time document editing during meetings. |
| `JITSI_ENABLE_RECORDING` | `true` | Enables call recording and streaming via Jibri. Increases CPU/RAM load. |
| `JITSI_MEET_USER` | `jitsimeet` | The username for the Jitsi Meet moderator account (required to create meetings). |
| `JITSI_MEET_PASSWORD` | `jitsimeetpw` | The password for the Jitsi Meet moderator account. |

---

## 🔑 First-Run Onboarding Guide

Open jitsi-meet web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://jitsi.org/](https://jitsi.org/)

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

Deploy **jitsi-meet** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
