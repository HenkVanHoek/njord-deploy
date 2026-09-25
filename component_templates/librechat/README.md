# 🏗️ NjordDeploy: LibreChat

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-AI%20%26%20LLM%20Services-purple.svg)]()

> LibreChat is a self-hosted AI chat platform that unifies all major AI providers in a single, privacy-focused interface. It features AI Agents, Code Interpreter, custom actions, conversation search, and enterprise-ready multi-user authentication. The service runs as root (user: 0:0) to manage volume permissions.

- **Source Repository:** [github.com/danny-avila/librechat](https://github.com/danny-avila/librechat)
- **Container Image:** `mongo:6.0`

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
> Tested on Proxmox LXC: docker (22.04, 2026-09-14), podman (22.04, 2026-09-14); Proxmox VM: docker (22.04, 2026-09-14), podman (22.04, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  librechat:
    container_name: njorddeploy-librechat
    image: "ghcr.io/danny-avila/librechat:latest"
    restart: always
    user: "0:0"
    ports:
      - "3080:3080"
    environment:
      - "HOST=0.0.0.0"
      - "PORT=3080"
      - "MONGO_URI=mongodb://njorddeploy-librechat-mongodb:27017/LibreChat"
      - "JWT_SECRET=q8g+R6s5t7v9w0x1y2z3a4b5c6d7e8f9g0h1i2j3k4l5m6n7o8p="
      - "JWT_REFRESH_TOKEN_SECRET=r9h+S7t6u8v0w1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m7n8q="
      - "CREDS_KEY=f34be427ebb29de8d88c107a71546019685ed8b241d8f2ed00c3f39708323511"
      - "CREDS_IV=e28e9323f46fbf8dc61f6305a4ecb38b"
      - "OPENAI_API_KEY=openai_api_key"
      - "ANTHROPIC_API_KEY=anthropic_api_key"
      - "GOOGLE_API_KEY=google_api_key"
      - "AZURE_OPENAI_API_KEY=azure_openai_api_key"
      - "AZURE_OPENAI_ENDPOINT=azure_openai_endpoint"
      - "AZURE_OPENAI_API_VERSION=2023-12-01-preview"
      - "CUSTOM_ENDPOINTS=custom_endpoints"
    volumes:
      - "./data/librechat/data:/app/data"
      - "./data/librechat/images:/app/client/public/images"
      - "./data/librechat/uploads:/app/uploads"
      - "./data/librechat/logs:/app/logs"
      - "./data/librechat/skill:/app/skill"
    depends_on:
      - librechat-mongodb
    networks:
      - njorddeploy_net

  librechat-mongodb:
    container_name: njorddeploy-librechat-mongodb
    image: mongo:6.0
    restart: always
    user: "0:0"
    volumes:
      - "./data/librechat/mongodb:/data/db"
    command: mongod --noauth
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
| `LIBRECHAT_WEB_PORT` | `3080` | Port for the LibreChat web interface. |
| `JWT_SECRET` | `q8g+R6s5t7v9w0x1y2z3a4b5c6d7e8f9g0h1i2j3k4l5m6n7o8p=` | Secret key for JSON Web Token (JWT) authentication. |
| `JWT_REFRESH_TOKEN_SECRET` | `r9h+S7t6u8v0w1x2y3z4a5b6c7d8e9f0g1h2i3j4k5l6m7n8q=` | Secret key for JSON Web Token (JWT) refresh tokens. |
| `CREDS_KEY` | `f34be427ebb29de8d88c107a71546019685ed8b241d8f2ed00c3f39708323511` | Key for encrypting user credentials (64 hex chars). |
| `CREDS_IV` | `e28e9323f46fbf8dc61f6305a4ecb38b` | Initialization Vector for encrypting user credentials (32 hex chars). |
| `OPENAI_API_KEY` | *None* | Your OpenAI API key for accessing OpenAI models. |
| `ANTHROPIC_API_KEY` | *None* | Your Anthropic API key for accessing Claude models. |
| `GOOGLE_API_KEY` | *None* | Your Google API key for accessing Google models (e.g., Gemini). |
| `AZURE_OPENAI_API_KEY` | *None* | Your Azure OpenAI API key. |
| `AZURE_OPENAI_ENDPOINT` | *None* | Your Azure OpenAI endpoint URL. |
| `AZURE_OPENAI_API_VERSION` | `2023-12-01-preview` | API version for Azure OpenAI. |
| `CUSTOM_ENDPOINTS` | *None* | JSON string for custom OpenAI-compatible API endpoints. Example: '[{"baseURL":"http://localhost:11434/v1","name":"Ollama","apiKey":""}]' |

---

## 🔑 First-Run Onboarding Guide

Open LibreChat web UI and complete the initial onboarding setup.

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

Deploy **LibreChat** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
