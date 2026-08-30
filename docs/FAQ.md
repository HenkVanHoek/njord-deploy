# NjordDeploy: Frequently Asked Questions (FAQ)

---

## 1. Concept & Comparison (Orientation Phase)

### 1.1 Why the name "NjordDeploy"?
**Answer:**
In Norse mythology, **Njörðr (Njord)** is the god of the sea, seafaring, navigation, wind, and calm/safe harbors (originating from his mythical harbor realm *Nóatún*, meaning "ships' haven").

In modern DevOps and container orchestration, applications and infrastructure are metaphorically treated as cargo shipping containers and vessels (just like *Docker*, *Kubernetes* [Helmsman], *Helm*, and *Portainer*). Just as Njord calms rough seas and steers seafarers safely into their home port, **NjordDeploy** acts as your sovereign navigator—guiding your container stacks, networking, and persistent data safely into the calm harbor of your own private home server, 100% free from cloud lock-in.

### 1.2 What is NjordDeploy and what problem does it solve?
**Answer:**
NjordDeploy is a lightweight, metadata-driven deployment orchestrator for self-hosting Docker and Rootless Podman services on local or remote Linux servers (such as Raspberry Pi, Orange Pi, Proxmox LXC/VMs, or standard Debian/Ubuntu systems). It removes the friction of manually writing `docker-compose.yml` files, handling reverse proxies, configuring network ports, and managing environment variables, while maintaining total control without heavy background server daemons.

### 1.3 How does NjordDeploy differ from all-in-one platforms like CasaOS, Umbrel, Portainer, or Cosmos Cloud?
**Answer:**
* **No Server-Side Agent or Overhead:** Most platforms require heavy background daemons and web servers running continuously on the target device, consuming precious RAM and CPU. NjordDeploy operates purely as a remote configurator over SSH; once deployed, only standard Docker or Podman containers run on your target server.
* **Non-Invasive & Standardized:** All deployed services use standard Docker Compose stacks. If you ever stop using NjordDeploy, your containers and standard configuration files continue to work normally with standard CLI commands.
* **Modular Metadata Architecture:** Service stacks are rendered on demand using verified templates with built-in port conflict detection and automated reverse-proxy (Traefik/Caddy/NPM) routing.

### 1.4 Which specific self-hosted services are currently supported by NjordDeploy?
**Answer:**
NjordDeploy provides a curated catalog of over 100+ modular services across multiple domains:
* **AI & Voice Studios:** Open WebUI with Ollama, Voicebox (AI voice cloning & TTS/STT), n8n (AI agents & automation).
* **DNS & Privacy:** AdGuard Home, Pi-hole, Unbound DNS.
* **Smart Home & IoT:** Home Assistant, Zigbee2MQTT, Frigate (AI Object Detection NVR), Scrypted, UniFi Controller, OctoPrint, LoRa Letterbox Notifier.
* **Development & DevOps:** GitLab, Semaphore UI (Ansible/Terraform UI).
* **Media & Entertainment:** Jellyfin, Sonarr, Radarr, Prowlarr, qBittorrent, SABnzbd, Gluetun VPN, Audiobookshelf.
* **Dashboards & Monitoring:** Homepage, Homarr, Heimdall, Homer, Organizr, Prometheus & Grafana Stack, Uptime Kuma.
* **Databases & Utilities:** Nextcloud, Vaultwarden, Filebrowser, MariaDB, phpMyAdmin, Adminer, Stirling PDF, Microbin.
* **Communication & Proxies:** Jitsi Meet, Conduit (Matrix), FluffyChat Web, Prosody (XMPP), Traefik, Caddy, Nginx Proxy Manager.
*(See [SUPPORTED_SERVICES.md](SUPPORTED_SERVICES.md) for the full detailed matrix).*

### 1.4 Can I run my own custom AI models using NjordDeploy's AI stack?
**Answer:**
Yes. NjordDeploy includes dedicated AI components such as **Open WebUI bundled with Ollama**, **Voicebox**, and **n8n**. With Ollama, you can download, load, and run any custom open-weight LLM (e.g., Llama 3, Mistral, Gemma, Phi, Qwen, or custom GGUF models) locally and fully offline on your hardware, accessible via a web UI and standard OpenAI-compatible API endpoints.

### 1.5 Is NjordDeploy a cloud service or is it 100% private and local?
**Answer:**
NjordDeploy is **100% local, self-contained, and privacy-first**. All discovery scans, credential handling, template rendering, and deployments execute directly from your control machine to your target device over local network or encrypted SSH/WireGuard/Tailscale tunnels. No telemetry, metadata, or user credentials ever leave your infrastructure.

### 1.6 Is NjordDeploy free for self-hosters?
**Answer:**
**Yes, absolutely!**
* **Free Community Tier:** Every self-hoster and homelab user can use NjordDeploy **100% free forever** for up to **2 connected servers / SBC devices** (e.g. 1 Raspberry Pi + 1 Homelab server/mini-PC). It includes access to all 100 components, unlimited container deployments, local volume backups, and full multi-tenant workspace isolation without requiring a credit card.
* **Pro Tier (€5/month or €50/year):** For power users, organizations, and homelabbers managing more than 2 server nodes, NjordDeploy Pro unlocks unlimited connected servers, automated cloud off-site backups, and priority CVE security advisory alerts.
* **Standalone Desktop Mode:** If running the standalone offline desktop executable locally, there are no node limits.

### 1.7 Can I run NjordDeploy as a 24/7 persistent background daemon/service on my home server?
**Answer:**
Yes! While NjordDeploy provides standalone desktop executables for workstations, it can also run as a **24/7 persistent daemon** on your Raspberry Pi, server, or Proxmox VM. You can deploy it using **Docker Compose** (`docker compose up -d`) or as a native Linux **systemd service** (`sudo ./scripts/install_systemd_service.sh install`). In service mode, it exposes the Web UI on port `5001`, provides a live healthcheck endpoint (`/api/health`), automatically persists SSH keys in `/var/lib/njorddeploy`, and exposes the full Headless OpenAPI REST API for continuous homelab automation. See the **[Self-Hosted Service Guide](SELF_HOSTED_SERVICE_GUIDE.md)** for detailed instructions.

---

## 2. Hardware & System Requirements (Preparation Phase)

### 2.1 Which devices and operating systems are supported?
**Answer:**
* **Target Hardware:** Raspberry Pi (3, 4, 5, Compute Modules), alternative SBCs (ODROID, Orange Pi), x86_64 mini-PCs, Intel NUCs, and Proxmox VE hypervisors.
* **Target Architectures:** `x86_64` (amd64) and `aarch64` (arm64).
* **Target Operating Systems:** Debian 11/12/13, Ubuntu (22.04 LTS, 24.04 LTS, 26.04 LTS), and Raspberry Pi OS (64-bit recommended).
* **Control Machine:** Linux or Windows running the NjordDeploy configurator.

### 2.2 Do I need to install Docker or Python on the target server beforehand?
**Answer:**
* **Docker:** No. NjordDeploy automatically detects whether a modern Docker Engine (>= 20.10.0) and the Docker Compose plugin are installed. If missing, it automates the official installation and service enablement.
* **Python:** **Strictly No.** Under NjordDeploy’s core architectural policy (*No Python on Target*), target servers remain clean and lightweight. NjordDeploy orchestrates deployments using native shell commands and Docker APIs over SSH. All Python-based services run exclusively inside isolated container images.

### 2.3 Can I deploy to Proxmox VE (LXC Containers or QEMU VMs)?
**Answer:**
Yes. NjordDeploy has dedicated Proxmox VE integration. It can automatically provision fresh Debian LXC containers (or clone Cloud-Init QEMU VMs), initialize the Docker runtime, and deploy your chosen services in a single workflow.

### 2.4 What are the minimum system requirements?
**Answer:**
* **Control Machine:** 512 MB RAM, Python 3.11+, and optional `nmap` (for local L2 subnet discovery).
* **Target Node:** 1 CPU core, 1 GB RAM (2 GB+ recommended depending on the services selected), 8 GB storage, and an open SSH port (default port 22).

---

## 3. Network, Security & Authentication (Onboarding Phase)

### 3.1 How does NjordDeploy discover devices on the local network?
**Answer:**
NjordDeploy supports multiple discovery mechanisms:
1. **L2 Subnet Scan & OUI Matching:** Performs an ARP broadcast scan (`nmap -sn -PR`) on your local subnet and matches MAC address OUIs against the official Raspberry Pi foundation registry.
2. **Custom CIDR Sweep:** Allows scanning custom IP ranges or VLANs (e.g., `10.0.10.0/24`).
3. **Tailscale / Headscale Mesh Discovery:** Queries your local Tailscale daemon to discover remote peer nodes with 1-click connection.
4. **Direct Target Input:** Connect directly using an IP address, mDNS hostname (`hostname.local`), or fully qualified domain name.

### 3.2 How does NjordDeploy handle passwords and SSH keys?
**Answer:**
* **SSH Key Authentication:** NjordDeploy natively supports modern SSH key pairs (`ed25519` and `rsa`) for passwordless, secure deployments.
* **Credential Storage:** When credentials or passphrase tokens are saved, NjordDeploy leverages the operating system’s native secure storage (via Python `keyring`), preventing sensitive information from being stored in plaintext.

### 3.3 Do I need to forward ports in my home router?
**Answer:**
No. In a local home network or when using an overlay mesh network like Tailscale or WireGuard, all services and management traffic remain private. No router port forwarding is required unless you intentionally choose to expose specific web services to the public internet.

---

## 4. Deployment, Storage & Operations (Operational Phase)

### 4.1 Where are service data, configurations, and Docker volumes stored on the target?
**Answer:**
NjordDeploy deploys each service into its own isolated directory structure on the target machine (under standard paths such as `/opt/njorddeploy/<component>` or `/home/<user>/njorddeploy/<component>`). Persistent volumes and environment definitions are isolated per service to ensure clean separation, easy backups, and simple migrations.

### 4.2 How can I configure automated backups for my GitLab instance or other service configurations?
**Answer:**
Because NjordDeploy isolates all state, volumes, and configurations into dedicated per-service directories on the target host:
1. **Native Container Backup Tools:** For complex applications like GitLab, you can trigger native backup tasks directly inside the running container (e.g., scheduling `docker exec -t gitlab gitlab-backup create` via host cron).
2. **Automated Database & Directory Dumps:** Components like the built-in `Nextcloud DB Dumper` provide automatic periodic SQL dumps. For full system backups, companion backup tools (such as Restic, BorgBackup, or Duplicati) can be pointed to the persistent `/opt/njorddeploy/` directories.

### 4.3 How does NjordDeploy prevent port conflicts between different services?
**Answer:**
Before launching a deployment, NjordDeploy performs a live pre-flight check:
1. It parses the component metadata to inspect all default host ports (e.g., port 80, 443, 53, 8080).
2. It queries active listening ports and running Docker containers on the target machine over SSH.
3. If a conflict is detected, the UI alerts you and allows remapping the external port before deployment begins.

### 4.4 How do I update running containers to newer versions?
**Answer:**
NjordDeploy uses standard Docker Compose stacks. You can trigger an update through the configurator interface, or run standard commands directly on the target:
```bash
docker compose pull && docker compose up -d
```

### 4.5 How is atomic file deployment guaranteed?
**Answer:**
NjordDeploy employs the **Tarball Deployment Pattern**: all rendered templates, configuration files, and scripts are bundled into a single compressed archive on the control machine, transferred via SSH, and extracted atomically in one operation on the target. This eliminates partial deployments caused by SFTP transfer interruptions.

---

## 5. Troubleshooting & Error Recovery

### 5.1 What happens if the network or SSH connection drops during deployment?
**Answer:**
NjordDeploy’s provisioning steps are designed to be **idempotent**. If a connection is interrupted, running the deployment again safely detects existing files and Docker states, resumes the process, and finishes bringing up the containers without corrupting configuration files.

### 5.2 Where can I view deployment logs and diagnostic output?
**Answer:**
* **In the Configurator UI:** The deployment modal displays real-time streaming logs of the SSH execution, package installation, and Docker container startup.
* **On the Target Node:** You can inspect real-time container logs at any time using:
  ```bash
  docker compose logs -f <service-name>
  ```

---

## 6. For Developers & Power-Users (Architecture & Templates)

### 6.1 What is the difference between `configurator_app` and `editor_app`?
**Answer:**
NjordDeploy is structured as a monorepo containing two dedicated Flask applications:
* **`configurator_app`:** The end-user application used to discover hardware, configure parameters, and deploy service stacks.
* **`editor_app`:** The developer tool used to author, validate, and manage component templates, metadata schemas, and dependencies.

### 6.2 Can I deploy custom service versions (e.g., GitLab with a specific Ruby or container version)?
**Answer:**
Yes. In NjordDeploy's container-first architecture, runtimes and language versions (like Ruby for GitLab) are encapsulated within Docker images. You can:
* Pin or customize the container image tag in the service's `variables.json` configuration.
* Use the `editor_app` to customize the `docker-compose.template.yml` to reference a custom image build or specific release tag without modifying the host OS.

### 6.3 What is the Single Source of Truth (SST) for component metadata?
**Answer:**
* **`config/components_metadata.json`** is the authoritative Single Source of Truth for component identity, categorization, default ports, and requirements.
* **`component_templates/<component>/variables.json`** defines the configurable environment variables and user-facing schema for that specific service.

### 6.4 How does component synchronization work (`SyncManager`)?
**Answer:**
NjordDeploy includes a `SyncManager` that bridges local component templates with the upstream `HenkVanHoek/njord-deploy-components` GitHub repository. It allows developers to diff local templates against remote upstream versions, pull updates in bulk, and commit/push validated changes.

### 6.5 How do service templates work?
**Answer:**
Each service stack resides in `component_templates/<component_id>/` and contains a Jinja2-compatible `docker-compose.template.yml`. When a deployment is initiated, the expert `ComponentManager` renders the template, injecting user-configured variables, Traefik/reverse proxy routing labels, and system dependencies automatically.

---

## 7. Local AI & Data Sovereignty (Component Generation)

### 7.1 Can I generate component metadata completely offline without third-party cloud APIs?
**Answer:**
Yes, 100%. NjordDeploy natively supports local LLMs via **Ollama** or **Open-WebUI**. When you connect the AI Component Builder to a local model (such as Llama 3, Mistral, Gemma, or Qwen running on your own PC or GPU), the entire repository scanning, documentation parsing, and template generation executes completely within your local network. No prompts, server paths, internal IPs, or secrets ever leave your environment.

### 7.2 How does NjordDeploy prevent local AI models from hallucinating ports or volume permissions?
**Answer:**
Local models are bound by strict **Air Traffic Control (ATC) Validation Rules** defined in `ai_generator_rules.json` and strict JSON schemas. NjordDeploy enforces:
* **Mathematical schema constraints** for variable keys, port types, and Jinja2 conditionals.
* **Volume permissions isolation** (`user: "0:0"` safeguards where required).
* **Automatic OCI registry validation** against Docker Hub, GHCR, and Quay to confirm that referenced container tags actually exist.
* **Autonomous correction loop**: If a generated template contains syntax flaws or conflicting bindings, the engine corrects them prior to saving.

### 7.3 Why did 3 different local AI models produce the exact same deployment metadata?
**Answer:**
In empirical testing with 3 distinct open-weight models (Llama 3, Mistral, and Qwen), all three yielded **identical, deterministic metadata** for complex GitHub repositories. This occurs because NjordDeploy's ATC prompt engineering and schema contracts are formulated so unambiguously that model variance and hallucinations are eliminated. The AI acts as a deterministic compiler rather than a probabilistic guessing tool.

### 7.4 What hardware is required to run the local AI Component Generator?
**Answer:**
Any standard modern consumer workstation or laptop with a modern multi-core CPU (such as an Intel Core i7/i9, AMD Ryzen 7/9, or Apple Silicon M-series) or an entry-level GPU (such as an NVIDIA RTX 3060/4060) can comfortably run quantized 7B/8B models in Ollama with near-instantaneous metadata generation times.
