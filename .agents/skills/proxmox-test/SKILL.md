---
name: proxmox-test
description: Workflows for automatically testing NjordDeploy components in a cloned Proxmox VM.
---

# Proxmox Component Integration Testing Workflow

Use this skill to validate NjordDeploy components by automatically deploying and testing them on a temporarily cloned VM within a Proxmox VE server.

## 1. Required Environment Variables

Configure the following keys in the project's `.env` file:

```bash
# Proxmox VE Cluster credentials
PROXMOX_HOST="https://<your-proxmox-ip>:8006"
PROXMOX_USER="root@pam"
PROXMOX_TOKEN_ID="clone-token"
PROXMOX_TOKEN_SECRET="xxxx-xxxx-xxxx-xxxx"
PROXMOX_NODE="pve"
PROXMOX_TEMPLATE_ID="902"

# Target VM credentials
PROXMOX_VM_USER="<your-vm-user>"
PROXMOX_VM_PASSWORD="your-ssh-and-sudo-password"

# Optional resources
PROXMOX_VM_RAM="2048"
PROXMOX_VM_CORES="2"
```

## 2. Running Tests

### A. Interactive Web UI (with live wildcard search & log streamer):
```bash
python run_proxmox_gui.py
# or: python scripts/proxmox_gui.py
```

### B. 4-Way Cross-Validation Matrix Test (LXC + VM × Docker + Podman):
```bash
python scripts/proxmox_test_runner.py --components web-notepad --mode both --engine both
```

### C. Test all components (single environment):
```bash
python scripts/proxmox_test_runner.py --mode lxc --engine docker
```

### D. Test specific components with Podman or Docker:
```bash
python scripts/proxmox_test_runner.py --components adguard-home,pi-hole --engine podman --mode lxc
```

### E. Exclude certain components:
```bash
python scripts/proxmox_test_runner.py --exclude homeassistant,frigate
```

### F. Specify a different template or Proxmox node via CLI:
```bash
python scripts/proxmox_test_runner.py --template-id 901 --node pve-node2 --engine podman
```

## 3. Reporting & Results

* **JSON Report**: The raw test results are saved in `tests/proxmox_results.json`.
* **Markdown Report**: A human-readable overview of the test run with error details is saved in `docs/PROXMOX_TESTS.md`.

## 4. Troubleshooting

### A. QEMU Guest Agent is not active
If the test runner times out while retrieving the IP address of the VM:
* Ensure that the `qemu-guest-agent` daemon is installed and enabled in the operating system of your master template VM:
  ```bash
  sudo apt-get update && sudo apt-get install -y qemu-guest-agent
  sudo systemctl enable --now qemu-guest-agent
  ```
* The test runner automatically configures the cloned VM with `agent: enabled=1` and attaches a network card (`net0`) and Cloud-Init drive (`ide2`), but the daemon inside the VM must be active to respond to API queries.

### B. No support for Linked Clones
If your storage pool (e.g., `local-lvm`) does not support snapshots/linked clones, Proxmox will throw an API error. The test runner has an automatic fallback built-in and will automatically switch to a **Full Clone**. This takes slightly longer but prevents the test from failing.

### C. Master Template VMID
On the `pve` node, the master template VMID defaults to `902` (`debian-clean-template`). If you want to use a different template, specify it using the `--template-id <id>` CLI option.

## 5. Multi-Environment Compose Templating (Jinja2)

When components behave differently across environments (e.g. Docker vs Podman, or LXC vs VM):

* **Jinja2 Environment Variables**:
  All compose templates are rendered with:
  * `CONTAINER_ENGINE`: `'docker'` or `'podman'`
  * `TARGET_MODE`: `'lxc'` or `'vm'`
  * `DATA_ROOT`: `/opt/njorddeploy/data`
  * `CONFIG_BASE_PATH`: `../njorddeploy_data`

* **Conditional Networking & Permissions**:
  Use Jinja2 conditionals in `docker-compose.template.yml` to support both engines without creating separate components:
  ```jinja2
  {%- if CONTAINER_ENGINE == 'podman' %}
      ports:
        - "{{ HA_WEB_PORT | default('8123') }}:8123"
      networks:
        - njorddeploy_net
  {%- else %}
      network_mode: host
  {%- endif %}
  ```

* **Matrix Constraints**:
  If a service fundamentally cannot run under a mode/engine (e.g. requires raw Docker socket `/var/run/docker.sock` not present in Podman, or requires `/dev/net/tun` not passed into LXC), restrict its `supported_matrix` in `config/components_metadata.json`:
  ```json
  "supported_matrix": {
    "engines": ["docker"],
    "modes": ["vm"],
    "notes": "Requires VM mode and Docker daemon socket"
  }
  ```
