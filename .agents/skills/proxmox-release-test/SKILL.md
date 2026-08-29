---
name: proxmox-release-test
description: Workflows and scripts for automatically testing the NjordDeploy release installer across Multi-OS environments (Debian, Ubuntu, Windows, macOS) in clean Proxmox VMs and LXC containers.
---

# Proxmox Multi-OS Release Installer Testing Workflow

Use this skill to validate that packaged NjordDeploy release binaries (e.g., PyInstaller standalone executables, installer scripts, and archive packages) compile, install, and execute correctly in isolated virtual machine (VM) and Linux container (LXC) environments on a Proxmox VE server.

## 1. Required Configuration (.env)

Ensure the Proxmox credentials and target templates are configured in your `.env` file:

```bash
# Proxmox VE Server API credentials
PROXMOX_HOST="https://<your-proxmox-ip>:8006"
PROXMOX_USER="root@pam"
PROXMOX_TOKEN_ID="clone-token"
PROXMOX_TOKEN_SECRET="xxxx-xxxx-xxxx-xxxx"
PROXMOX_NODE="pve"

# Target Linux VM / LXC Templates
RELEASE_TEST_DEBIAN_TEMPLATE="902"
RELEASE_TEST_UBUNTU_TEMPLATE=""  # Optional: Ubuntu Cloud-Init VMID
RELEASE_TEST_DEBIAN_LXC="local:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst"
RELEASE_TEST_UBUNTU_LXC="storage-backups-iso:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst"

# Target Windows & macOS VM Templates
RELEASE_TEST_WINDOWS_TEMPLATE="910"
RELEASE_TEST_MACOS_TEMPLATE=""  # Optional: OSX-KVM VMID

# Target OS credentials
RELEASE_TEST_VM_USER="testuser"
RELEASE_TEST_VM_PASSWORD="your-secure-test-password"

# Optional Signal Notifications
SIGNAL_API_URL="http://<signal-host>:8080"
SIGNAL_SENDER="+31600000000"
SIGNAL_RECIPIENT="+31611111111"
```

## 2. Running the Multi-OS Test Suite

The test runner provisions clean VM and LXC environments on Proxmox, transfers the installer/binary, executes the installation, and verifies the web configurator on port `5001`.

### A. Run Full Multi-OS Matrix (Debian, Ubuntu, Windows, macOS)
```bash
python scripts/proxmox_release_test_runner.py --os all --mode both
```

### B. Test a Specific Operating System
```bash
# Test Debian only (both VM and LXC)
python scripts/proxmox_release_test_runner.py --os debian

# Test Ubuntu only (LXC or VM)
python scripts/proxmox_release_test_runner.py --os ubuntu

# Test Windows VM only
python scripts/proxmox_release_test_runner.py --os windows

# Test macOS (via OSX-KVM VM or CI status check)
python scripts/proxmox_release_test_runner.py --os macos
```

### C. Test an Official GitHub Release Tag
```bash
python scripts/proxmox_release_test_runner.py --github-tag v0.4.46-Alpha --os all
```

### D. Test a Local Custom Binary Path
```bash
python scripts/proxmox_release_test_runner.py --binary-path dist/NjordDeployConfigurator --os linux
```

## 3. How Multi-OS Verification Works

1. **Provisioning:**
   - **Linux VMs:** Clones clean master template (e.g. Debian 902), attaches Cloud-Init disk, configures dynamic DHCP network, and boots.
   - **Linux LXC Containers:** Creates clean unprivileged LXC container with nested Docker/Podman support from appliance template (Debian 12 / Ubuntu 24.04).
   - **Windows VMs:** Clones Windows 10/11 template with OpenSSH and QEMU Guest Agent.
   - **macOS VMs:** Clones OSX-KVM OpenCore VM template with OpenSSH (or verifies via GitHub Actions runner).
2. **File Transfer:** Copies installer package (`install.sh` / `NjordDeploy-Linux` / `NjordDeployInstaller.exe`) via SCP.
3. **Execution & Service Launch:**
   - **Linux:** Executes `./install.sh` to place the binary in `/usr/local/bin/NjordDeploy-Configurator` and starts the daemon.
   - **Windows:** Launches the executable in background via PowerShell.
4. **Health Check:** Probes `http://<guest-ip>:5001/` (fallback `5000`) for HTTP `200 OK`.
5. **Automatic Reporting & Cleanup:**
   - Detailed Markdown test report generated in `docs/RELEASE_INSTALLER_TESTS_<timestamp>.md`.
   - Results recorded in `tests/release_installer_results.json`.
   - Signal notification sent if configured.
   - Cloned VMs and LXC containers automatically stopped and destroyed.
