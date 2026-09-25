# 🏗️ NjordDeploy: Hatchdoor

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-Productivity-purple.svg)]()

> Agent-native web app and Model Context Protocol (MCP) server for Obsidian-style Markdown vaults with semantic search, wikilinks, and graph views.

- **Upstream Project:** [Hatchdoor](https://github.com/BattermanZ/Hatchdoor)
- **Source Repository:** [github.com/BattermanZ/Hatchdoor](https://github.com/BattermanZ/Hatchdoor)
- **Container Image:** `battermanz/hatchdoor:latest`

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
> Rootless and distroless. Provides web UI and MCP server.
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  hatchdoor:
    image: battermanz/hatchdoor:latest
    container_name: njorddeploy-hatchdoor
    restart: unless-stopped
    ports:
      - "42824:42824"
    environment:
      - "HOST=0.0.0.0"
      - "PORT=42824"
      - "VAULT_PATH=/data/vault"
      - "HATCHDOOR_CACHE_DB=/data/cache/hatchdoor-cache.sqlite3"
    volumes:
      - "./data/hatchdoor/vault:/data/vault"
      - "./data/hatchdoor/cache:/data/cache"
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
| `PORT_HATCHDOOR` | `42824` | Port to access the Hatchdoor Web UI and MCP endpoint. |
| `HATCHDOOR_VAULT_PATH` | `/opt/njorddeploy/data/hatchdoor/vault` | Host path containing Markdown notes and documents. |
| `HATCHDOOR_CACHE_PATH` | `/opt/njorddeploy/data/hatchdoor/cache` | Host path for storing generated SQLite search cache. |

---

## 🔑 First-Run Onboarding Guide

Open http://<server-ip>:42824 to browse your notes. Point your MCP client (Claude Code, Cursor, Codex) to the MCP endpoint to enable AI agent note navigation.

- **Upstream Setup Guide:** [https://docs-hatchdoor.battercloud.cc](https://docs-hatchdoor.battercloud.cc)

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

Deploy **Hatchdoor** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
