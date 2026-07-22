---
name: proxmox-lxc
description: Workflows and scripts for automatically creating, provisioning (Docker), and managing LXC containers in Proxmox VE.
---

# Proxmox LXC Container Provisioning Workflow

Use this skill to automatically create LXC containers on your Proxmox VE server specifically provisioned for NjordDeploy (including Docker and necessary network connections).

## 1. Required Environment Variables

Ensure that the following keys are correctly configured in your `.env` file:

```bash
PROXMOX_HOST="https://<your-proxmox-ip>:8006"
PROXMOX_USER="root@pam"
PROXMOX_TOKEN_ID="clone-token"
PROXMOX_TOKEN_SECRET="xxxx-xxxx-xxxx-xxxx"
PROXMOX_NODE="pve"
```

## 2. Creating and Provisioning an LXC Container

The script `scripts/create_proxmox_lxc.py` handles the entire installation. It performs the following steps:
1. Queries Proxmox for the next available VMID.
2. Retrieves NjordDeploy's public SSH key.
3. Searches the storage (`local`) for a usable Debian or Ubuntu LXC template.
4. Creates the container with Nesting and Keyctl enabled (required for Docker inside LXC).
5. Waits for the container to come online and receive an IP address via DHCP.
6. Connects via SSH, automatically installs Docker, and starts the `njorddeploy_net` Docker network.

### Command for 15+ users (Recommended specs):
```bash
python scripts/create_proxmox_lxc.py --cores 4 --memory 8192 --storage-size 40 --storage-name local-lvm
```

### Options:
* `--cores <count>`: Number of CPU cores (default: `4`).
* `--memory <MB>`: RAM in MB (default: `8192` for 8GB).
* `--storage-size <GB>`: Size of the SSD in GB (default: `40`).
* `--storage-name <name>`: Proxmox storage pool (default: `local-lvm`).
* `--node <name>`: Proxmox node name (default: `pve`).
* `--password <password>`: Root password for the container.

## 3. Post-Installation Management

Once the script completes, it displays the container details (ID, IP address, root password).
You can use the container directly as a deployment target in NjordDeploy by specifying the host in the configurator or editor app!
