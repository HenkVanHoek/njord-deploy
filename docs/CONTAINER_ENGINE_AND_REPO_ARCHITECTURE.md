# Container Engine & Dynamic Components Repository Architecture

## 1. Overview & Objective

NjordDeploy operates as an **engine-agnostic, universal deployment kernel** designed for enterprise, home-lab, and advanced self-hosted environments.

This architecture introduces two fundamental decoupling layers:
1. **Container Engine Abstraction Layer**: Transparent support for standard **Docker** as well as **Podman (Rootless)** across all orchestration, provisioning, and pre-flight routines.
2. **Dynamic Components Repository Source**: Dynamic synchronization of component metadata (`components_metadata.json`) and compose templates (`component_templates/`) from any remote repository (GitHub, GitLab, Forgejo, custom servers) or local air-gapped storage.

All service definitions (`component_templates/**/docker-compose.template.yml`) and metadata contracts remain 100% OCI- and Compose-compliant.

---

## 2. Environment Configuration (`.env`)

The system configuration is controlled via environment variables, modifiable through the UI (Settings / Onboarding Wizard) or directly in `.env`:

| Variable | Type / Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `CONTAINER_ENGINE` | `docker` \| `podman` | `docker` | Target container engine on managed nodes and local provisioning. |
| `COMPONENTS_REPO_URL` | String / URL / `none` / `local` | `HenkVanHoek/njord-deploy-components` | Upstream components repository. Accepts GitHub slug, HTTPS/SSH git URL, direct `.zip` URL, or `none`/`local` for offline air-gapped operation. |
| `COMPONENTS_REPO_BRANCH` | String | `main` | Target branch to pull component updates and definitions from. |
| `COMPONENTS_REPO_TOKEN` | String | `""` | Optional personal access token (PAT) for private repositories (GitHub, GitLab, Forgejo). |

---

## 3. Container Engine Abstraction Layer

The engine abstraction is implemented in [`src/utils/container_engine.py`](file:///home/hvhoek/PycharmProjects/njord-deploy/src/utils/container_engine.py) via the `ContainerEngine` class.

### CLI & Compose Mapping

| Operation | Docker Mode | Podman Mode (Rootless) |
| :--- | :--- | :--- |
| **CLI Binary** | `docker` | `podman` |
| **Compose Command** | `docker compose` | `podman-compose` |
| **Pull Images** | `docker compose pull --ignore-buildable` | `podman-compose pull` |
| **Start Services** | `docker compose up -d` | `podman-compose up -d` |
| **Stop Services** | `docker compose down [-v]` | `podman-compose down [-v]` |
| **Remove Service** | `docker compose rm -f -s -v <service>` | `podman-compose rm -f -s -v <service>` |
| **Container Exec** | `docker exec <container> <cmd>` | `podman exec <container> <cmd>` |
| **Network Creation** | `docker network create njorddeploy_net` | `podman network create njorddeploy_net` |
| **Log Streaming** | `docker logs --tail 200 <container>` | `podman logs --tail 200 <container>` |

---

## 4. Rootless Podman: Technical Prerequisites & Provisioning

Running OCI containers without root privileges improves security posture but introduces three specific host OS constraints that NjordDeploy automatically configures during provisioning:

### A. Low-Port Binding ($< 1024$) for DNS & Web Services
By default, the Linux kernel restricts unprivileged users from binding ports below 1024. Services like AdGuard Home / Pi-hole require port `53` (DNS), and reverse proxies require `80` (HTTP) and `443` (HTTPS).

**Automated Configuration**:
NjordDeploy creates `/etc/sysctl.d/99-podman-ports.conf`:
```ini
net.ipv4.ip_unprivileged_port_start=53
```
Applied immediately with `sysctl --system`.

### B. Systemd User Session Lingering
In rootless mode, container processes run under the user's systemd user session (`dbus-user-session`). If lingering is not enabled, systemd terminates user processes upon SSH session logout.

**Automated Configuration**:
```bash
loginctl enable-linger <username>
```
This guarantees that background containers continue running uninterrupted across logouts, reboots, and SSH disconnects.

### C. SubUID & SubGID User Namespace Mapping
Rootless Podman maps internal container UIDs (like root UID 0 inside the container) to a designated range of unprivileged subordinate UIDs on the host.

**Automated Configuration**:
NjordDeploy verifies and ensures `/etc/subuid` and `/etc/subgid` allocations:
```bash
usermod --add-subuids 100000-165535 <username>
usermod --add-subgids 100000-165535 <username>
```

### D. Ansible Integration
The main deployment playbook ([`ansible/playbook.yml`](file:///home/hvhoek/PycharmProjects/njord-deploy/ansible/playbook.yml)) receives `container_engine: "{{ container_engine }}"` via Ansible extravars and dynamically adapts provisioning tasks and service execution without code divergence.

---

## 5. Dynamic Components Repository & Air-Gapped Mode

The dynamic synchronization is managed by [`src/managers/sync_manager.py`](file:///home/hvhoek/PycharmProjects/njord-deploy/src/managers/sync_manager.py):

1. **Remote Sync Enabled**: Downloads and extracts upstream templates and metadata into the local user cache directory (`user_data_dir/NjordDeploy/cache`).
2. **Offline / Air-Gapped Mode (`COMPONENTS_REPO_URL="none"` or `"local"`)**: Remote network sync is disabled. The system exclusively uses locally seeded component templates from the application package, preventing network timeouts.
3. **Repository Validation Endpoint (`/api/validate-repo`)**: Validates candidate repository URLs and credentials live before persisting settings.

---

## 6. User Interface & Experience

### A. Topbar Status Badge & Engine Switcher
- **Visual Status**: Real-time badge in the top navigation bar indicating the active engine:
  - 🐳 **Docker** (Blue Badge)
  - 🦭 **Podman** (Amber Badge)
- **Live Switcher**: Quick dropdown allows instant switching between Docker and Podman modes without application restarts.

### B. First-Run Onboarding Setup Modal
When launching NjordDeploy on a clean system (no prior `.env` configuration):
- An interactive onboarding wizard automatically welcomes the user.
- Allows immediate choice of Default Container Engine (Docker vs Podman).
- Allows selection of Components Repository source (Official GitHub, Air-Gapped Local, or Custom GitLab/Forgejo repository with instant connection testing).

### C. Settings Page Cards
- Dedicated configuration cards in the Settings tab for **Container Engine** and **Components Repository**, featuring URL input, branch selection, optional auth tokens, and a live "Test Connection" button.
