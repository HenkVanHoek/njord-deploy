# NjordDeploy REST API Reference

NjordDeploy provides a comprehensive, headless REST API that enables automated and programmatic deployments of self-hosted container stacks. This API can be consumed by external automation tools, CI/CD pipelines, DevOps scripts, and AI coding agents (such as Antigravity/Agy).

The Configurator backend runs by default at `http://localhost:5001`.

> [!TIP]
> **Interactive Swagger UI**: Explore and execute requests interactively in your browser at [`http://localhost:5001/api/docs`](http://localhost:5001/api/docs).
>
> **OpenAPI 3.0 Specification**: Raw schema JSON is available at [`http://localhost:5001/api/openapi.json`](http://localhost:5001/api/openapi.json).

---

## Table of Contents
- [Interactive Swagger UI & OpenAPI Spec](#interactive-swagger-ui--openapi-spec)
1. [Component Discovery & Metadata](#1-component-discovery--metadata)
2. [Target Discovery & Node Inspection](#2-target-discovery--node-inspection)
3. [Pre-Flight Conflict Analysis](#3-pre-flight-conflict-analysis)
4. [Deployment Execution & Streaming](#4-deployment-execution--streaming)
5. [Deployment Evaluation & Diagnostics](#5-deployment-evaluation--diagnostics)
6. [Proxmox VE Orchestration](#6-proxmox-ve-orchestration)
7. [Engine & Repository Settings](#7-engine--repository-settings)
8. [Backup & Restore Management](#8-backup--restore-management)
9. [Headless CLI Runner Mode](#9-headless-cli-runner-mode)

---

## Interactive Swagger UI, OpenAPI Spec & AI Endpoints

### `GET /api/docs`
Renders the full, interactive Swagger UI with live request execution and dynamic accessibility theming (Futuristic Dark, Standard Light, High Contrast).

### `GET /api/openapi.json`
Returns the complete OpenAPI 3.0.3 machine-readable specification formatted for automated tooling and agent ingestion.

### `GET /robots.txt`
Returns the search and generative AI crawler accessibility rules, enabling bots like `PerplexityBot`, `GPTBot`, and `ClaudeBot` while protecting sensitive endpoints.

### `GET /llms.txt`
Returns the machine-readable architecture and documentation index structured according to the [llmstxt.org](https://llmstxt.org/) standard.

### `GET /llms-full.txt`
Returns the consolidated full technical specification and documentation text for LLM context windows and RAG systems.

---

## 1. Component Discovery & Metadata

### `GET /api/components`
Retrieves all registered services and templates from the single source of truth (`config/components_metadata.json` / remote repo).

- **Method:** `GET`
- **Response `200 OK`:**
```json
{
  "adguard-home": {
    "id": "adguard-home",
    "name": "AdGuard Home",
    "description": "Network-wide ads & trackers blocking DNS server.",
    "category": "Network & DNS",
    "ports": ["53:53/udp", "3000:3000/tcp", "80:80/tcp"],
    "volumes": ["/opt/adguard-home/work:/opt/adguardhome/work"],
    "variables": []
  },
  "grafana": {
    "id": "grafana",
    "name": "Grafana",
    "description": "Operational dashboards and data visualization platform.",
    "category": "Monitoring",
    "ports": ["3000:3000/tcp"],
    "volumes": ["/opt/grafana/data:/var/lib/grafana"]
  }
}
```

---

### `POST /get-available-software`
Returns both available software components and pre-bundled software packages.

- **Method:** `POST`
- **Response `200 OK`:**
```json
{
  "available_software": [
    { "id": "adguard-home", "name": "AdGuard Home", "category": "Network & DNS" }
  ],
  "available_packages": [
    {
      "id": "monitoring-stack",
      "name": "Monitoring Stack",
      "components": ["prometheus", "grafana", "node-exporter"]
    }
  ]
}
```

---

### `GET /get-software-groups`
Retrieves category grouping rules, exclusivity constraints, and display order for software components.

- **Method:** `GET`
- **Response `200 OK`:**
```json
{
  "groups": {
    "DNS & Adblocking": {
      "is_exclusive": true,
      "components": ["adguard-home", "pi-hole"]
    },
    "Monitoring & Observability": {
      "is_exclusive": false,
      "components": ["grafana", "prometheus", "uptime-kuma"]
    }
  }
}
```

---

### `POST /get-required-variables`
Returns the list of configurable environment variables for a given set of selected component IDs.

- **Method:** `POST`
- **Request Body:**
```json
{
  "selected_components": ["grafana", "nextcloud"]
}
```
- **Response `200 OK`:**
```json
{
  "components": {
    "grafana": {
      "name": "Grafana",
      "variables": [
        {
          "name": "GF_SECURITY_ADMIN_PASSWORD",
          "label": "Admin Password",
          "type": "password",
          "default": "admin",
          "required": true
        }
      ]
    }
  }
}
```

---

### `POST /validate-selection`
Validates that template folders and `variables.json` configuration definitions exist on disk.

- **Method:** `POST`
- **Request Body:**
```json
{
  "selected_components": ["adguard-home", "grafana"]
}
```
- **Response `200 OK`:**
```json
{
  "message": "Selection is valid."
}
```

---

## 2. Target Discovery & Node Inspection

### `POST /scan-pis`
Discovers target hosts on the local network via Subnet Nmap scan, Tailscale mesh, or direct IP.

- **Method:** `POST`
- **Request Body:**
```json
{
  "discovery_method": "direct_ip",
  "direct_target_ip": "192.168.1.150"
}
```
*(Or `{"discovery_method": "tailscale"}` / `{"discovery_method": "network_scan"}`)*

- **Response `200 OK`:**
```json
{
  "hosts": [
    {
      "ip": "192.168.1.150",
      "hostname": "raspberrypi",
      "status": "online",
      "os_type": "Debian Linux"
    }
  ],
  "messages": ["✅ Found 1 target host."],
  "error": null
}
```

---

### `POST /get-device-details`
Connects via SSH to inspect hardware resources, OS version, disk mounts, and active container engine status.

- **Method:** `POST`
- **Request Body:**
```json
{
  "ip": "192.168.1.150",
  "username": "root",
  "password": "TargetPassword123"
}
```
- **Response `200 OK`:**
```json
{
  "model": "Raspberry Pi 4 Model B",
  "serial": "10000000abcde123",
  "os_version": "Debian GNU/Linux 12 (bookworm)",
  "docker_is_active": true,
  "ram": "7812 MB",
  "disks": [
    {
      "mounted_on": "/",
      "size": "58G",
      "pcent": "18%"
    }
  ]
}
```

---

## 3. Pre-Flight Conflict Analysis

### `POST /api/v1/system/analyze`
Performs an automated pre-deployment safety analysis by checking port collisions (native OS and Docker/Podman processes), volume mount collisions, and system resource requirements.

- **Method:** `POST`
- **Request Body:**
```json
{
  "is_reinstallation": false,
  "devices": [
    {
      "ip": "192.168.1.150",
      "username": "root",
      "password": "TargetPassword123"
    }
  ],
  "components": [
    {
      "id": "grafana",
      "name": "Grafana",
      "ports": ["3000:3000/tcp"],
      "volumes": ["/opt/grafana/data:/var/lib/grafana"]
    }
  ]
}
```
- **Response `200 OK`:**
```json
{
  "status": "success",
  "internal_conflicts": [],
  "external_conflicts": {
    "ports": [],
    "volumes": []
  },
  "resource_warnings": []
}
```

---

## 4. Deployment Execution & Streaming

### `POST /start-installation`
Generates deployment files (`docker-compose.yml`, `.env`, and configuration directories) locally in the staging area.

- **Method:** `POST`
- **Request Body:**
```json
{
  "selected_components": ["grafana"],
  "devices": [
    {
      "ip": "192.168.1.150",
      "username": "root",
      "password": "TargetPassword123"
    }
  ],
  "env_vars": {
    "GF_SECURITY_ADMIN_PASSWORD": "SecretAdminPassword"
  }
}
```
- **Response `200 OK`:**
```json
{
  "message": "Configuration files generated.",
  "output_path": "/home/user/.local/share/NjordDeploy/output/session_123"
}
```

---

### `POST /deploy-configuration`
Initiates the asynchronous deployment over SSH to the remote target host (transferring files, running pre-flight provisioning, and launching containers).

- **Method:** `POST`
- **Request Body:**
```json
{
  "output_path": "/home/user/.local/share/NjordDeploy/output/session_123",
  "devices": [
    {
      "ip": "192.168.1.150",
      "username": "root",
      "password": "TargetPassword123"
    }
  ],
  "selected_components_data": [
    { "id": "grafana", "name": "Grafana" }
  ],
  "global_vars": {
    "GF_SECURITY_ADMIN_PASSWORD": "SecretAdminPassword"
  },
  "components_to_clean": [],
  "components_to_restart": [],
  "analysis_results": {}
}
```
- **Response `202 Accepted`:**
```json
{
  "task_id": "a1b2c3d4e5f67890"
}
```

---

### `GET /stream-deployment/<task_id>`
Server-Sent Events (SSE) stream providing real-time deployment logs.

- **Method:** `GET`
- **Response Stream (`text/event-stream`):**
```
data: Starting deployment process...
data: Connecting to 192.168.1.150 via SSH...
data: Syncing deployment artifacts to target...
data: Executing container engine compose up...
data: [grafana] Container started successfully.
```

---

### `GET /task-status/<task_id>`
Polls the current status, collected logs, and non-blocking warnings of an ongoing or completed deployment task.

- **Method:** `GET`
- **Response `200 OK`:**
```json
{
  "status": "completed",
  "logs": [
    "Starting deployment process...",
    "Container started successfully."
  ],
  "errors": []
}
```

---

## 5. Deployment Evaluation & Diagnostics

### `POST /api/deployment/<task_id>/evaluate`
Evaluates the execution logs and container state, returning a structured health assessment (with AI diagnosis if enabled).

- **Method:** `POST`
- **Request Body:**
```json
{
  "component_name": "grafana",
  "use_ai": true
}
```
- **Response `200 OK`:**
```json
{
  "status": "healthy",
  "verdict": "success",
  "summary": "Grafana deployed and running with exit code 0.",
  "errors_found": [],
  "remediation": []
}
```

---

### `POST /get-container-logs`
Fetches the latest live logs directly from a running container on the remote host via SSH.

- **Method:** `POST`
- **Request Body:**
```json
{
  "ip": "192.168.1.150",
  "username": "root",
  "password": "TargetPassword123",
  "container_name": "njorddeploy-grafana"
}
```
- **Response `200 OK`:**
```json
{
  "container_name": "njorddeploy-grafana",
  "logs": "HTTP Server Listen :3000 ... initialized database schema"
}
```

---

## 6. Proxmox VE Orchestration

### `POST /api/proxmox/create-lxc`
Creates, boots, and provisions a fresh unprivileged LXC container with Docker/Podman pre-installed.

- **Method:** `POST`
- **Request Body:**
```json
{
  "hostname": "ct-grafana",
  "cores": 4,
  "memory": 4096,
  "storage_name": "local-lvm",
  "storage_size": "20",
  "node": "pve",
  "password": "SecureContainerPassword123!"
}
```
- **Response `201 Created`:**
```json
{
  "status": "success",
  "ip": "192.168.1.185",
  "vmid": 120,
  "hostname": "ct-grafana",
  "username": "root",
  "password": "SecureContainerPassword123!"
}
```

---

### `POST /api/proxmox/list-targets`
Lists all available LXC containers and QEMU VMs running on the Proxmox node.

- **Method:** `POST`
- **Response `200 OK`:**
```json
{
  "targets": [
    { "vmid": 100, "name": "debian-master", "type": "qemu", "status": "running", "node": "pve" },
    { "vmid": 120, "name": "ct-grafana", "type": "lxc", "status": "running", "node": "pve" }
  ]
}
```

---

### `POST /api/proxmox/start-target`
Starts a stopped VM or LXC container and waits until it obtains an IPv4 address.

- **Method:** `POST`
- **Request Body:**
```json
{
  "vmid": 120,
  "type": "lxc",
  "node": "pve"
}
```
- **Response `200 OK`:**
```json
{
  "ip": "192.168.1.185"
}
```

---

## 7. Engine & Repository Settings

### `GET /api/engine-status`
Returns the currently active container runtime (`docker` or `podman`) and remote component repository synchronization status.

- **Method:** `GET`
- **Response `200 OK`:**
```json
{
  "engine": "docker",
  "is_docker": true,
  "is_podman": false,
  "supported_engines": ["docker", "podman"],
  "repo_url": "https://github.com/HenkVanHoek/njorddeploy-components.git",
  "repo_branch": "main",
  "is_remote_sync_enabled": true
}
```

---

### `POST /api/engine-switch`
Switches the active container runtime dynamically (`docker` or `podman`) and persists the preference.

- **Method:** `POST`
- **Request Body:**
```json
{
  "engine": "podman"
}
```
- **Response `200 OK`:**
```json
{
  "status": "success",
  "engine": "podman",
  "message": "Container engine successfully switched to PODMAN."
}
```

---

### `POST /api/validate-repo`
Validates connectivity, authentication, and branch existence for a remote component repository.

- **Method:** `POST`
- **Request Body:**
```json
{
  "url": "https://github.com/HenkVanHoek/njorddeploy-components.git",
  "branch": "main",
  "token": "optional_git_pat_token"
}
```
- **Response `200 OK`:**
```json
{
  "valid": true,
  "message": "Repository connection validated successfully."
}
```

---

## 8. Backup & Restore Management

> [!IMPORTANT]
> **Scope Boundary:** NjordDeploy's backup and restore engine exclusively archives and restores services, persistent volumes, and configuration files managed under `/opt/njorddeploy`. Foreign host directories and unmanaged containers are never altered or included.

### `POST /api/backup/discover-compose`
Scans target host common filesystem locations (`$HOME`, `/opt`, `/srv`, `/etc/docker`) for existing `docker-compose.yml` or `compose.yaml` files.

- **Method:** `POST`
- **Request Body:**
```json
{
  "ip": "192.168.1.150",
  "username": "root",
  "password": "TargetPassword123"
}
```
- **Response `200 OK`:**
```json
{
  "status": "success",
  "discovered_paths": [
    {
      "directory": "/home/pi/docker",
      "compose_file": "/home/pi/docker/docker-compose.yml",
      "filename": "docker-compose.yml"
    }
  ],
  "suggested_path": "/home/pi/docker"
}
```

---

### `POST /api/backup/inspect`
Inspects the target host's Docker Compose stack configuration and calculates disk space consumed by each service's persistent volume mounts. Supports custom stack locations (e.g., `~/docker`).

- **Method:** `POST`
- **Request Body:**
```json
{
  "ip": "192.168.1.150",
  "username": "root",
  "password": "TargetPassword123",
  "project_config_dir": "~/docker",
  "port": 22
}
```
- **Response `200 OK`:**
```json
{
  "status": "success",
  "managed_scope": "/opt/njorddeploy",
  "disclaimer": "This backup tool exclusively detects, archives, and restores services, configurations, and persistent volumes managed by NjordDeploy under /opt/njorddeploy.",
  "components": [
    {
      "id": "grafana",
      "name": "Grafana",
      "container_name": "njorddeploy-grafana",
      "volumes": [
        {
          "type": "bind",
          "host_path": "/opt/grafana/data",
          "container_path": "/var/lib/grafana",
          "size_bytes": 10485760,
          "size_human": "10.0 MB"
        }
      ],
      "total_size_bytes": 10485760,
      "total_size_human": "10.0 MB",
      "is_heavy": false
    }
  ],
  "total_managed_size_bytes": 10485760,
  "total_managed_size_human": "10.0 MB"
}
```

---

### `POST /api/backup/create`
Creates a timestamped `.tar.gz` archive on the target host containing the stack configuration (`.env`, `docker-compose.yml`), a JSON manifest, and compressed volume datasets.

- **Method:** `POST`
- **Request Body:**
```json
{
  "ip": "192.168.1.150",
  "username": "root",
  "password": "TargetPassword123",
  "selected_components": ["grafana", "uptime-kuma"],
  "pause_containers": true
}
```
- **Response `200 OK`:**
```json
{
  "status": "success",
  "filename": "njorddeploy_backup_20260818_120000.tar.gz",
  "remote_path": "/opt/njorddeploy/backups/njorddeploy_backup_20260818_120000.tar.gz",
  "size_bytes": 5242880,
  "size_human": "5.0 MB",
  "sha256": "3a8c5f90...",
  "components": ["grafana", "uptime-kuma"]
}
```

---

### `POST /api/backup/list`
Lists all available NjordDeploy backup archives located on the target host.

- **Method:** `POST`
- **Response `200 OK`:**
```json
{
  "status": "success",
  "backups": [
    {
      "filename": "njorddeploy_backup_20260818_120000.tar.gz",
      "remote_path": "/opt/njorddeploy/backups/njorddeploy_backup_20260818_120000.tar.gz",
      "size_bytes": 5242880,
      "size_human": "5.0 MB",
      "created_at": "2026-08-18 12:00:00"
    }
  ]
}
```

---

### `POST /api/backup/restore`
Restores services and volumes from a selected backup tarball, applies correct permissions (`chmod 777`), and restarts the container stack.

- **Method:** `POST`
- **Request Body:**
```json
{
  "ip": "192.168.1.150",
  "username": "root",
  "password": "TargetPassword123",
  "backup_filename": "njorddeploy_backup_20260818_120000.tar.gz",
  "restart_after": true
}
```
- **Response `200 OK`:**
```json
{
  "status": "success",
  "restored_archive": "njorddeploy_backup_20260818_120000.tar.gz",
  "restored_components": ["grafana", "uptime-kuma"],
  "restarted": true
}
```

---

### `GET /api/backup/download/<filename>`
Streams the `.tar.gz` archive from remote host via SFTP / local staging to the user's browser.

- **Method:** `GET`
- **Query Parameters:** `ip`, `username`, `password` (optional if in session)
- **Response `200 OK`:** Binary file stream (`application/gzip`).

---

## 9. Headless CLI Runner Mode

NjordDeploy includes a built-in headless CLI runner (`run_configurator.py` / `src/cli/runner.py`) designed for zero-browser CI/CD automation, scheduled tasks, and autonomous AI agents.

### Example Configuration Export
```bash
python3 run_configurator.py --example-config > deployment.json
```

### Headless Deployment via JSON Specification
```bash
python3 run_configurator.py --deploy deployment.json
```

### Direct CLI Deployment via Flags
```bash
python3 run_configurator.py --deploy --ip 192.168.1.31 --user root --components uptime-kuma,homarr --engine docker
```

### Stack Inspection & Diagnostics
```bash
python3 run_configurator.py --inspect --ip 192.168.1.31 --user root
```

### Disaster Recovery Backup via CLI
```bash
python3 run_configurator.py --backup --ip 192.168.1.31 --user root --components uptime-kuma --pause-containers
```

### Snapshot Restoration via CLI
```bash
python3 run_configurator.py --restore njorddeploy_backup_20260818_134348.tar.gz --ip 192.168.1.31 --user root
```

### Stack Auto-Discovery
```bash
python3 run_configurator.py --scan-stacks --ip 192.168.1.31 --user root
```
