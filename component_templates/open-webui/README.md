# 🏗️ NjordDeploy: Open WebUI

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-AI%20%26%20LLM%20Services-purple.svg)]()

> Open WebUI is an extensible, feature-rich, and user-friendly web interface for AI models and LLMs, supporting Ollama and OpenAI-compatible APIs with chat, voice, and RAG capabilities.

- **Upstream Project:** [Open WebUI](https://openwebui.com/)
- **Source Repository:** [github.com/open-webui/open-webui](https://github.com/open-webui/open-webui)
- **Container Image:** `ghcr.io/open-webui/open-webui`

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
> Tested on Proxmox LXC: docker (main, 2026-09-14), podman (main, 2026-09-14); Proxmox VM: docker (main, 2026-09-14), podman (main, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  open-webui:
    container_name: njorddeploy-open-webui
    image: "ghcr.io/open-webui/open-webui:main"
    volumes:
      - "./data/open-webui/data:/app/backend/data"
    ports:
      - "3000:8080"
    environment:
      - "OLLAMA_BASE_URL=http://ollama:11434"
      - "WEBUI_SECRET_KEY=njorddeploy_secret_key_openwebui_2026"
      - "OPENAI_API_KEY="
    networks:
      - njorddeploy_net
    restart: unless-stopped

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
| `OPEN_WEBUI_PORT` | `3000` | The port on the host to access the Open WebUI interface. |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | URL of the Ollama server (e.g. http://ollama:11434 for local Ollama, or http://<IP>:11434 for remote). |
| `WEBUI_SECRET_KEY` | `njorddeploy_secret_key_openwebui_2026` | A secret key for Open WebUI sessions. Generate a strong, random string. |
| `OPENAI_API_KEY` | *None* | Optional: Your OpenAI API key for OpenAI API usage. Leave empty if not using OpenAI. |

---

## 🔑 First-Run Onboarding Guide

Open Open WebUI web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://openwebui.com/](https://openwebui.com/)

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

Deploy **Open WebUI** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
