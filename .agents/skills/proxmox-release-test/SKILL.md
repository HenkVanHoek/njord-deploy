---
name: proxmox-release-test
description: Workflows and scripts for automatically testing the compiled NjordDeploy release binaries in clean Proxmox VMs.
---

# Proxmox Release Installation Testing Workflow

Use this skill to validate that packaged NjordDeploy release binaries (e.g., PyInstaller standalone executables) compile, install, and execute correctly in isolated virtual machine environments on a Proxmox VE server.

## 1. Required Configuration (.env)

Ensure the Proxmox credentials and target VM templates are configured in your `.env` file:

```bash
# Proxmox VE Server API credentials
PROXMOX_HOST="https://<your-proxmox-ip>:8006"
PROXMOX_USER="root@pam"
PROXMOX_TOKEN_ID="clone-token"
PROXMOX_TOKEN_SECRET="xxxx-xxxx-xxxx-xxxx"
PROXMOX_NODE="pve"

# Release Test Target VMs
# Template IDs for clean OS installations (must have OpenSSH/QEMU Guest Agent)
RELEASE_TEST_LINUX_TEMPLATE="900"
RELEASE_TEST_WINDOWS_TEMPLATE="910"

# Target OS credentials
RELEASE_TEST_VM_USER="testuser"
RELEASE_TEST_VM_PASSWORD="your-secure-test-password"
```

## 2. Running the Release Test Suite

The test suite clones the master VM templates, uploads the target release binary, executes the installation, and verifies the web server.

### A. Test Local Build (Default / Recommended before pushing tag)
First, compile the application locally:
```bash
pyinstaller NjordDeployInstaller.spec
```

Then run the release test runner:
```bash
python scripts/proxmox_release_test_runner.py --binary-path dist/NjordDeployInstaller
```

### B. Test a GitHub Tagged Release
You can test an official release by downloading its assets directly to the VM:
```bash
python scripts/proxmox_release_test_runner.py --github-tag v0.4.46-Alpha
```

### C. Skip Windows/Linux Testing
If you only want to test a specific platform:
```bash
# Test Linux only
python scripts/proxmox_release_test_runner.py --skip-windows

# Test Windows only
python scripts/proxmox_release_test_runner.py --skip-linux
```

## 3. How Verification Works

1. **Clone & Boot:** The script queries Proxmox for the next unused VMID, clones the template, configures SSH keys/credentials via cloud-init, and boots the VM.
2. **Transfer:** The binary is SCP'd to the guest OS.
3. **Execution:**
   - **Linux:** Runs `sudo ./install.sh` to place the binary in `/usr/local/bin/NjordDeploy-Configurator` and registers/starts the service, checking that it responds on port `5001`.
   - **Windows:** Runs the packaged `.exe` binary in the background and verifies port connectivity.
4. **Cleanup:** Once tests finish (pass or fail), the cloned VMs are stopped and deleted from the Proxmox server.
