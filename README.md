<div align="center" dir="auto"><img width="150" height="150" style="max-width: 100%; height: auto; max-height: 150px;" alt="njorddeploy-icon512x512" src="https://github.com/HenkVanHoek/assets/63ed723a-578f-47f9-b40b-e241c4c5935b" /></div>

# Njord-Deploy

Welcome to Njord-Deploy! This project provides a user-friendly system to deploy and manage a suite of self-hosted services on a Raspberry Pi (or any Linux-based system) using Docker. Our goal is to make self-hosting powerful, accessible, and easy to maintain.

<div align="center">
  <a href="docs/GETTING_STARTED_FOR_BEGINNERS.md">
    <img src="docs/images/njorddeploy-demo-loop.gif" alt="NjordDeploy 5-Step Workflow Demo" width="850" style="border-radius: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.15);" />
  </a>
  <p>
    <strong>🐣 New to self-hosting?</strong> Check out our <strong><a href="docs/GETTING_STARTED_FOR_BEGINNERS.md">Beginner's Guide (Quick Start for Dummies)</a></strong> to get up and running in 5 minutes!
  </p>
</div>

## 🌟 Key Features

- **Milestone 100 Sovereign Components**: Deploy from a curated library of **100 verified self-hosted services** covering AI & LLMs (Ollama, Open WebUI, LiteLLM, LibreChat), DevOps (Gitea, Woodpecker CI, n8n, Semaphore), Cloud Storage (Immich, Syncthing, MinIO, FileBrowser), Smart Home (Home Assistant, ESPHome, Node-RED, Zigbee2MQTT), Privacy Analytics & DBs (Umami, Plausible, MariaDB, PostgreSQL, pgAdmin 4), and Observability (Prometheus, Grafana, Uptime Kuma, Netdata) (see [Supported Services](docs/SUPPORTED_SERVICES.md)).
- **Multi-Tenant SaaS & Organization Workspaces**: Granular tenant isolation with role-based access control (Owner, Admin, Member), isolated configuration caching, and seamless workspace switching.
- **Stripe Billing & Subscription Ecosystem**: Full commercial billing integration with monthly and annual plans, checkout sessions, tier entitlement gating, and self-service Stripe Customer Portal management.
- **24/7 Persistent Self-Hosted Service Daemon**: Run NjordDeploy continuously on your home server, mini-PC, Raspberry Pi, or Proxmox VM (via Docker Compose or native Linux systemd) with automated persistent SSH key management and live healthchecks (see [Self-Hosted Service Guide](docs/SELF_HOSTED_SERVICE_GUIDE.md)).
- **Fully Browser-Based Installer**: A simple, local web application guides you through every step, from device discovery to watching the live installation log.
- **Headless REST API & Agentic DevOps**: Full programmatic control for CI/CD pipelines, Homelab orchestration, and AI coding agents (like Antigravity/Agy). Automate end-to-end deployments, Proxmox LXC provisioning, pre-flight safety analysis, and log evaluation via clean REST endpoints (see [API Reference](docs/API_REFERENCE.md)).
- **Interactive Swagger UI & OpenAPI 3.0**: Explore, test, and inspect all REST API endpoints directly in your browser at `http://localhost:5001/api/docs` or consume the machine-readable OpenAPI schema at `/api/openapi.json`. Supports dark and light theme switching.
- **Dual Container Engine Support (Docker & Rootless Podman)**: Universal container engine abstraction supporting both standard Docker and rootless Podman environments with automated low-port kernel configuration and user lingering.
- **Dynamic Components Repository**: Synchronize component templates from official GitHub, custom GitLab/Forgejo instances, or operate in fully offline/air-gapped mode.
- **Component Editor**: A powerful web-based developer tool for creating, testing, and managing all components in the NjordDeploy ecosystem.
- **AI-Assisted Component Generator**: Bootstrap new services in seconds from any public Git repository (**GitHub, GitLab, Gitea, Forgejo, Codeberg, Bitbucket, or self-hosted Git instances**) powered by **HostYourAI / Loes (EU Sovereign Cloud)**, local Ollama, Google Gemini, or OpenAI with automatic context enrichment, validation checks, and self-correction (see [Developer AI Guide & Demo](docs/DEVELOPER_AI_AND_SYNC_GUIDE.md#2-ai-assisted-component-generator-multi-provider--multi-forge-git-support)).
- **Volume Backup & Disaster Recovery**: Point-in-time state backups for all managed persistent volumes and configurations with transactional pause, SHA-256 verification, single-click restoration, and target filesystem auto-detection.

## 🏛️ How It Works

NjordDeploy provides a **multi-mode architecture**:
1. **Interactive Web Wizard (Standalone Desktop Mode)**: End-users download a standalone release executable and interact with a guided web UI (`http://localhost:5001`) for automatic network scanning, component selection, variable customization, and real-time deployment log streaming.
2. **24/7 Self-Hosted Daemon Mode**: Homelab administrators host NjordDeploy 24/7 in Docker Compose or native systemd on a server/VM with persistent state, continuous SSH key access, and automated health monitoring (`/api/health`).
3. **Multi-Tenant SaaS / Organization Mode**: Multi-user team deployments with tenant isolation, user authentication, and Stripe subscription tiering.
4. **Headless REST Engine & Interactive Swagger UI**: Developers, sysadmins, and AI agents can bypass the UI entirely, communicating directly with the backend API or exploring the interactive Swagger UI (`http://localhost:5001/api/docs`) to provision Proxmox virtual environments, validate conflicts, trigger builds, and monitor deployment health programmatically.

## 📋 System Requirements

**On Your Main Computer (where you run the installer):**
- Windows, macOS, or Linux.
- **Linux Users**: Install the **nmap**, **sshpass**, and **OpenSSH client** packages.
  For Debian/Ubuntu:

      sudo apt install -y nmap sshpass openssh-client

**On Your Target Server (e.g., Raspberry Pi):**
- A Raspberry Pi 4 or newer is recommended.
- Or, use a Debian-based server, such as the one provided by [pi-server-vm](https://github.com/HenkVanHoek/pi-server-vm).
- Container runtime: **Docker Engine** (with Compose plugin) or **Podman (rootless)** (with `podman-compose`). The tool can install and configure either automatically.
- SSH access must be enabled.

## Container Engine Management on Target Device

NjordDeploy provides transparent support for **Docker** and **Podman (Rootless)**:
- **Docker**: Installs official Docker Engine, enables systemd service, adds user to docker group, and provisions network.
- **Podman (Rootless)**: Installs Podman and `podman-compose`, configures unprivileged port binding (`net.ipv4.ip_unprivileged_port_start=53` via `/etc/sysctl.d/99-podman-ports.conf`), enables systemd user session lingering (`loginctl enable-linger`), and sets up subuid/subgid mapping.

For detailed architecture and `.env` parameters, see [`docs/CONTAINER_ENGINE_AND_REPO_ARCHITECTURE.md`](docs/CONTAINER_ENGINE_AND_REPO_ARCHITECTURE.md).

- Compose Spec is used. Compose files do not include a version key.
- Supported runtime: latest stable Docker Engine with the Docker Compose plugin.
- Minimum baseline: Docker Engine 20.10.0 or newer.

Behavior during deployment
1. Detect Docker Engine and Compose plugin.
2. If missing, install the latest Engine via the official installer, enable and
   start the docker service, and ensure the docker-compose-plugin package.
3. If an older Engine is detected, deployment stops with a clear error unless
   upgrade is allowed. To allow upgrade, provide one of the following variables
   in the deployment globals. The tool will remove older packages and install
   the latest Engine and Compose plugin. This upgrade is destructive on Docker
   state and removes local images and containers on the target device.

     ALLOW_DOCKER_UPGRADE=true
     # or
     GLOBAL_ALLOW_DOCKER_UPGRADE=true

4. Permissions: the remote user is added to the docker group for future
   sessions. During the current session, docker commands run with sudo if
   required.

## Host OS runtime policy

- Do not install or depend on a system Python interpreter or compiler on the
  target device for new NjordDeploy functionality.
- If Python is required for new automation or utilities, run it inside
  containers. Deliver it as a Docker image and execute it using Docker, including
  init container patterns when needed.
- Deployment and maintenance operations must not install Python onto the host.
  Remote steps are limited to shell, Docker, and core OS tooling.

## 🚀 Quick Start Guide

### Mode A: Standalone Desktop Application

1. **Download the Release Zip**: Go to the [GitHub Releases page](https://github.com/HenkVanHoek/njord-deploy/releases) and download the release package for your operating system (`NjordDeploy-Linux.zip`, `NjordDeploy-macOS.zip`, or `NjordDeploy-Windows.zip`).
2. **Unzip & Launch**: Unzip the package to a local folder. You will find three standalone executables:
   - **`NjordDeployConfigurator`** (`.exe` on Windows): The end-user application for device discovery, service selection, and deployment (runs on `http://localhost:5001`).
   - **`NjordDeployEditor`** (`.exe` on Windows): The developer tool for creating and modifying component metadata (runs on `http://localhost:5000`).
   - **`NjordDeployProxmoxTest`** (`.exe` on Windows): The developer testing suite for automated Proxmox VE component validation (runs on `http://localhost:5050`).
   - *Linux / macOS:* Make executable if needed (`chmod +x NjordDeployConfigurator`) and launch `./NjordDeployConfigurator`.
3. **Configure & Automate**: Your default web browser will open automatically to `http://localhost:5001`. Follow the on-screen wizard to discover your device, select services, and customize your configuration. Or navigate to `http://localhost:5001/api/docs` to inspect and test the interactive Swagger REST API.
4. **Deploy**: Confirm your selections to generate Docker Compose files and deploy services to your target host with a live browser log.

### Mode B: 24/7 Persistent Self-Hosted Service Daemon

Run NjordDeploy continuously on your home server, mini-PC, or Proxmox VM:

- **Via Docker Compose:**
  ```bash
  docker compose up -d
  curl -s http://localhost:5001/api/health
  ```
- **Via Native Linux Systemd:**
  ```bash
  sudo ./scripts/install_systemd_service.sh install
  sudo ./scripts/install_systemd_service.sh status
  ```

For full persistent SSH key setup, reverse proxy integration, and environment options, see the **[24/7 Self-Hosted Service Guide](docs/SELF_HOSTED_SERVICE_GUIDE.md)**.

### 🔐 Security, First-Run Setup & API Tokens

When deployed as a persistent service on a public or local server (`deploy.njorddeploy.com`), NjordDeploy provides enterprise-grade authentication and token security:

1. **First-Run Setup Wizard (`/setup`)**: On fresh installations in server mode, all non-public requests automatically redirect to an intuitive onboarding wizard to create the primary administrator account (minimum 8-character password hashed with PBKDF2:SHA256 / Argon2).
2. **Session Security (`/login` & `/logout`)**: Protected with secure `HttpOnly`, `SameSite=Lax` cookies, session expiration, and sliding-window brute-force rate limiting (max 5 failed attempts per 5 minutes per IP returning HTTP 429).
3. **Headless REST API Bearer Tokens**: For automation scripts, CI/CD, and external agents, provide your API token via `X-Njord-API-Key: <token>` or `Authorization: Bearer <token>` to bypass browser sessions.
4. **Environment Variables**:
   - `NJORD_SERVER_MODE=true`: Enables production server mode and strict authentication enforcement.
   - `NJORD_AUTH_ENABLED=true`: Force-enables authentication across all endpoints.
   - `NJORD_SECRET_KEY`: Custom Flask session signing key (auto-generated and persisted in `0o600` `.secret_key` if unset).
   - `NJORD_API_KEY`: Custom master headless API key (auto-generated if unset).
   - `NJORD_ADMIN_USER` & `NJORD_ADMIN_PASSWORD` / `NJORD_ADMIN_HASH`: Pre-seed administrator credentials in automated environments without interactive `/setup`.

### One-Time Setup for Linux Desktop Users

If you are running the standalone desktop installer on a `Linux desktop`, grant the scanner permission to perform network discovery:

    echo "your_username ALL=(ALL) NOPASSWD: /usr/bin/nmap" | sudo tee /etc/sudoers.d/99-njorddeploy
    sudo chmod 0440 /etc/sudoers.d/99-njorddeploy

## Project Directory Structure

The following tree represents the current physical layout of the project:
```
.
├── ansible
│   └── playbook.yml
├── component_templates
│   ├── adguard-home
│   ├── homeassistant
│   ├── pi-hole
│   ├── traefik
│   └── [other service templates...]
├── config
│   ├── components_metadata.json
│   └── raspberry_pi_oui.json
├── docs
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   ├── DATA_CONTRACTS.md
│   ├── FUNCTIONAL_SPEC.md
│   └── sovereign_home_server.md
├── linux
│   ├── install.sh
│   └── njorddeploy-Configurator.desktop
├── pyproject.toml
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
├── run_configurator.py
├── run_editor.py
├── run_proxmox_gui.py
├── scripts
│   ├── proxmox_gui.py
│   ├── proxmox_test_runner.py
│   └── update_docs.py
├── src
│   ├── configurator_app
│   │   ├── app.py
│   │   ├── openapi.py (OpenAPI 3.0 specification provider)
│   │   ├── static (base.css, configurator.css, images, js)
│   │   └── templates (base.html, index.html, help.html, swagger.html, etc.)
│   ├── editor_app
│   │   ├── app.py
│   │   ├── static (editor.v2.js, ui_render_utils.js)
│   │   └── templates (editor.html)
│   ├── managers
│   │   ├── component_manager.py
│   │   ├── deployment_evaluator.py
│   │   ├── deployment_manager.py
│   │   ├── setup_manager.py
│   │   ├── ssh_manager.py
│   │   └── sync_manager.py
│   ├── node_scanner.py
│   └── utils
│       ├── ai_failure_diagnoser.py
│       ├── ai_generator_engine.py
│       ├── ai_provider_manager.py
│       ├── auth_utils.py
│       ├── container_engine.py
│       ├── proxmox_client.py
│       └── resource_utils.py
├── tests
│   ├── configurator_app
│   ├── editor_app
│   └── managers
└── windows
    └── start.bat
```
## 📚 Background and Articles

For a detailed case study on running a sovereign stack (including Nextcloud, Euro-Office, and Frigate) on a Raspberry Pi 5 with ZRAM and Google Coral TPU optimizations, please refer to:
- The article on DEV Community: [Building a Sovereign Home Server: Lessons Learned Running Nextcloud, Euro-Office, and Frigate on a Raspberry Pi 5](https://dev.to/henk_van_hoek/building-a-sovereign-home-server-lessons-learned-running-nextcloud-euro-office-and-frigate-on-a-1kbc)
- Our local summary of the lessons learned: [sovereign_home_server.md](file:///home/hvhoek/PycharmProjects/NjordDeploy/docs/sovereign_home_server.md)

## 🤝 Contributing
We welcome contributions! For guidelines on how to get started with development, please see our "CONTRIBUTING.md" file. To understand the core design principles and data contracts of the project, please review the "ARCHITECTURE.md" file. For detailed setup and usage instructions regarding separate components repository synchronization, Gemini AI integration, and the local Ollama LLM setup, see the [Developer AI and Sync Guide](docs/DEVELOPER_AI_AND_SYNC_GUIDE.md).

## 📄 License

This project is licensed under the **[Business Source License 1.1 (BSL-1.1)](LICENSE)**:
- **100% Free for Self-Hosting**: Free of charge for personal use, homelab deployments, non-commercial use, and managing up to two (2) self-hosted target server nodes without a paid subscription.
- **Commercial Protection**: Hosting or offering NjordDeploy as a commercial deployment platform (SaaS) or competing managed service to third parties requires a commercial license agreement from the author.
- **Automatic Open Source Transition**: Transitions to the standard Apache 2.0 open-source license two years after release.

Copyright (c) 2025-2026 Henk van Hoek. All rights reserved.

You can also find more information about this project on my GitHub page: [HenkVanHoek/njord-deploy](https://github.com/HenkVanHoek/njord-deploy).
