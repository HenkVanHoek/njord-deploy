# 🏗️ NjordDeploy: Speaches Speech-to-Text & Audio

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-AI%20%26%20LLM%20Services-purple.svg)]()

> Speaches is an open-source, OpenAI-compatible Speech-to-Text (faster-whisper) and Text-to-Speech (Kokoro/Piper) server supporting GPU acceleration.

- **Upstream Project:** [Speaches Speech-to-Text & Audio](https://github.com/speaches-ai/speaches)
- **Source Repository:** [github.com/speaches-ai/speaches](https://github.com/speaches-ai/speaches)
- **Container Image:** `ghcr.io/speaches-ai/speaches`

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
> Tested on Proxmox LXC: docker (24.04, 2026-10-20), podman (24.04, 2026-10-20); Proxmox VM: docker (24.04, 2026-10-20), podman (24.04, 2026-10-20).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  speaches:
    container_name: njorddeploy-speaches
    image: "ghcr.io/speaches-ai/speaches:latest-cpu"
    volumes:
      - "./data/speaches/cache:/home/ubuntu/.cache/huggingface/hub"
    ports:
      - "8008:8000"
    environment:
      - "WHISPER__COMPUTE_TYPE=default"
      - 'PRELOAD_MODELS=["Systran/faster-whisper-small"]'
      - "API_KEY=speaches"
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
| `SPEACHES_PORT` | `8008` | The host port to expose the Speaches STT/TTS API. |
| `SPEACHES_MODEL` | `Systran/faster-whisper-small` | Whisper spraakmodel voor transcriptie. 'Systran/faster-whisper-small' is de aanbevolen standaard voor uitstekend Nederlands op standaard CPU (~1 GB RAM). |
| `SPEACHES_COMPUTE_TYPE` | `default` | Whisper compute type (e.g. default, int8, float16, int8_float16). |

---

## 🔑 First-Run Onboarding Guide

Speaches REST API and OpenAPI docs are available at /docs. Configure Open WebUI audio transcription settings to point to http://speaches:8000/v1.

- **Upstream Setup Guide:** [https://github.com/speaches-ai/speaches](https://github.com/speaches-ai/speaches)

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

Deploy **Speaches Speech-to-Text & Audio** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
