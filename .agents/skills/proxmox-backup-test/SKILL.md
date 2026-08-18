---
name: proxmox-backup-test
description: End-to-end automated disaster recovery test suite in clean Proxmox LXC containers (provision, backup, mutate data, restore, verify convergence, and cleanup).
---

# Proxmox Backup & Disaster Recovery Test Skill

Use this skill to automatically execute an end-to-end disaster recovery and volume restoration validation test on a clean Proxmox VE LXC container.

## 🎯 Test Workflow & Steps

The test runner script `scripts/test_backup_restore_lxc.py` automates the entire regression cycle:

1. **LXC Container Provisioning**: Queries Proxmox for the next available VMID, deploys a clean Debian 12 LXC container with Docker capabilities (`nesting=1,keyctl=1`), and retrieves its DHCP IP.
2. **Container Engine Setup**: Automatically connects via SSH and provisions Docker Engine and the `njorddeploy_net` bridge network.
3. **Stack Deployment**: Launches an initial service stack (Uptime Kuma) and initializes persistent volume mount data under `/opt/uptime-kuma/data`.
4. **Volume Inspection**: Executes `BackupManager.inspect_target()` to verify volume parsing, container mapping, and byte calculation.
5. **Snapshot Creation**: Triggers `BackupManager.create_backup()` with transactional container pause, producing an archive with SHA-256 verification.
6. **Disaster Simulation (Data Mutation)**: Injects simulated data corruption / file modifications into the persistent volume.
7. **Volume Restoration**: Triggers `BackupManager.restore_backup()` from the generated archive, restores configuration and permissions (`chmod 777`), and restarts the container stack.
8. **State Verification**: Asserts that volume state reverted 100% to the initial snapshot and containers are running and healthy.
9. **Automated Cleanup**: Stops and destroys the temporary test LXC container on Proxmox VE.

---

## 🚀 Running the Automated Test

Run the test suite directly from the workspace terminal:

```bash
python3 scripts/test_backup_restore_lxc.py
```

### CLI Options:

* `--cores <count>`: Number of CPU cores (default: `2`).
* `--memory <MB>`: RAM in MB (default: `4096`).
* `--storage-size <GB>`: Rootfs disk in GB (default: `20`).
* `--storage-name <name>`: Proxmox storage pool (default: `local-lvm`).
* `--node <name>`: Proxmox node name (default: `pve`).
* `--password <password>`: Root password for the test container.
* `--keep`: Keep the container online after testing (prevents automated deletion for manual inspection).
