# 🏗️ NjordDeploy: LiteLLM AI Gateway

[![Proxmox Tested](https://img.shields.io/badge/Proxmox%20VE-Tested%20Passing-10b981.svg)](/docs/test-reports/LATEST_RUN.md)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()
[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()
[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()
[![Category](https://img.shields.io/badge/Category-AI%20%26%20LLM%20Services-purple.svg)]()

> LiteLLM is an AI gateway and LLM proxy that unifies access to 100+ Large Language Models (OpenAI, Gemini, Anthropic, Ollama, Azure, Bedrock, HostYourAI) behind a single OpenAI-compatible API format.

- **Upstream Project:** [LiteLLM AI Gateway](https://github.com/BerriAI/litellm)
- **Source Repository:** [github.com/BerriAI/litellm](https://github.com/BerriAI/litellm)
- **Container Image:** `postgres:16`

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
> Tested on Proxmox LXC: docker (main-stable, 2026-09-14), podman (1.19, 2026-09-14); Proxmox VM: docker (main-stable, 2026-09-14), podman (16.15-1.pgdg13+2, 2026-09-14).
---

## 🚀 Quick Start (Standalone Docker Compose)

```yaml
services:
  litellm:
    container_name: njorddeploy-litellm
    image: "ghcr.io/berriai/litellm:main-stable"
    ports:
      - "4000:4000"
    volumes:
      - "data_root/litellm/config.yaml:/app/config.yaml:ro"
    command:
      - "--config=/app/config.yaml"
    environment:
      - "DATABASE_URL=postgresql://llmproxy:njorddeploy_db_password_123@njorddeploy-litellm-db:5432/litellm"
      - "STORE_MODEL_IN_DB=True"
      - "OPENAI_API_KEY=openai_api_key"
      - "ANTHROPIC_API_KEY=anthropic_api_key"
      - "COHERE_API_KEY=cohere_api_key"
      - "AZURE_API_KEY=azure_api_key"
      - "AZURE_API_BASE=https://YOUR_RESOURCE_NAME.openai.azure.com/"
      - "AZURE_API_VERSION=2023-07-01-preview"
      - "GEMINI_API_KEY=gemini_api_key"
      - "HOSTYOURAI_API_KEY=hostyourai_api_key"
      - "HOSTYOURAI_API_BASE=https://hostyourai.com/api/v1"
      - "AWS_ACCESS_KEY_ID=aws_access_key_id"
      - "AWS_SECRET_ACCESS_KEY=ChangeMeSecurePassword123!"
      - "AWS_REGION_NAME=us-east-1"
    networks:
      - njorddeploy_net
    depends_on:
      - njorddeploy-litellm-db
    healthcheck:
      test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:4000/health/liveliness')\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.litellm.rule=Host(`litellm.yourdomain.com`)"
      - "traefik.http.routers.litellm.entrypoints=websecure"
      - "traefik.http.routers.litellm.tls.certresolver=default"
      - "traefik.http.services.litellm.loadbalancer.server.port=4000"
    user: "0:0"

  njorddeploy-litellm-db:
    container_name: njorddeploy-litellm-db
    image: postgres:16
    restart: always
    environment:
      - "POSTGRES_DB=litellm"
      - "POSTGRES_USER=llmproxy"
      - "POSTGRES_PASSWORD=njorddeploy_db_password_123"
    volumes:
      - "./data/litellm/postgres_data:/var/lib/postgresql/data"
    networks:
      - njorddeploy_net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -d litellm -U llmproxy"]
      interval: 1s
      timeout: 5s
      retries: 10
    user: "0:0"

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
| `LITELLM_WEB_PORT` | `4000` | The external port for accessing the LiteLLM AI Gateway web interface. |
| `LITELLM_DB_NAME` | `litellm` | The name of the PostgreSQL database for LiteLLM. |
| `LITELLM_DB_USER` | `llmproxy` | The username for accessing the PostgreSQL database. |
| `LITELLM_DB_PASSWORD` | `njorddeploy_db_password_123` | The password for the PostgreSQL database user. |
| `LITELLM_STORE_MODEL_IN_DB` | `True` | Set to 'True' to allow adding models to the proxy via the UI, 'False' otherwise. |
| `OPENAI_API_KEY` | *None* | Your OpenAI API Key. Required for using OpenAI models. This key will be available as an environment variable for LiteLLM. |
| `ANTHROPIC_API_KEY` | *None* | Your Anthropic API Key. Required for using Anthropic models. This key will be available as an environment variable for LiteLLM. |
| `COHERE_API_KEY` | *None* | Your Cohere API Key. Required for using Cohere models. This key will be available as an environment variable for LiteLLM. |
| `AZURE_API_KEY` | *None* | Your Azure OpenAI API Key. Required for using Azure OpenAI models. This key will be available as an environment variable for LiteLLM. |
| `AZURE_API_BASE` | `https://YOUR_RESOURCE_NAME.openai.azure.com/` | Your Azure OpenAI API Base URL (e.g., https://YOUR_RESOURCE_NAME.openai.azure.com/). Required for Azure OpenAI models. |
| `AZURE_API_VERSION` | `2023-07-01-preview` | Your Azure OpenAI API Version (e.g., 2023-07-01-preview). Required for Azure OpenAI models. |
| `GEMINI_API_KEY` | *None* | Your Google Gemini API Key. Required for using Google Gemini models. This key will be available as an environment variable for LiteLLM. |
| `HOSTYOURAI_API_KEY` | *None* | Your HostYourAI API Key for accessing models on HostYourAI. |
| `HOSTYOURAI_API_BASE` | `https://hostyourai.com/api/v1` | The API Base URL for your HostYourAI instance or gateway endpoint. |
| `AWS_ACCESS_KEY_ID` | *None* | Your AWS Access Key ID. Required for using AWS Bedrock/Sagemaker models. This key will be available as an environment variable for LiteLLM. |
| `AWS_SECRET_ACCESS_KEY` | *None* | Your AWS Secret Access Key. Required for using AWS Bedrock/Sagemaker models. This key will be available as an environment variable for LiteLLM. |
| `AWS_REGION_NAME` | `us-east-1` | Your AWS Region Name (e.g., us-east-1). Required for using AWS Bedrock/Sagemaker models. This key will be available as an environment variable for LiteLLM. |
| `TRAEFIK_HOST` | `litellm.yourdomain.com` | The hostname for Traefik to route traffic to LiteLLM (e.g., litellm.yourdomain.com). |

---

## 🔑 First-Run Onboarding Guide

Open LiteLLM AI Gateway web UI and complete the initial onboarding setup.

- **Upstream Setup Guide:** [https://github.com/BerriAI/litellm](https://github.com/BerriAI/litellm)

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

Deploy **LiteLLM AI Gateway** with 1-click using the **[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.
