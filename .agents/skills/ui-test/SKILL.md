---
name: ui-test
description: Workflows and instructions for automatically testing all untested components that have a web UI.
---

# Generic Testing of Components with a Web UI

Use this skill to test all components in a single run that have a web interface (`has_ui` is true) and whose status in the docker-compose template is not yet marked as `"tested"`.

---

## 1. How It Works (The Workflow)

The test runner (`proxmox_test_runner.py`) features an `--untested-ui` parameter. When executed:

1. **Detection**: The script scans all components in `config/components_metadata.json` and filters for components with `"has_ui": true`.
2. **Status Check**: For each UI component, the script reads the status header `# status:` from its corresponding `docker-compose.template.yml` file.
3. **Selection**: Only components with a status that is **not** `"tested"` (such as `"untested"` or `"testing"`) are selected for the test run.
4. **Provisioning & Run**: The selected components are deployed sequentially on a temporary Proxmox LXC container (or VM).
5. **Health Verification**: The test runner performs an HTTP health check (with automatic retries) on the external UI port.
6. **Result & Teardown**: Upon success, the status in the docker-compose template is automatically updated to `"tested"`, and the container is cleaned up immediately to save Proxmox resources.

---

## 2. Execution

### A. Test all untested UI components (LXC mode, recommended):
```bash
.venv/bin/python scripts/proxmox_test_runner.py --untested-ui --mode lxc
```
*This sequentially spins up temporary containers for all untested UI services, validates their web interfaces, and cleans them up immediately.*

### B. Test all untested UI components via VM mode:
```bash
.venv/bin/python scripts/proxmox_test_runner.py --untested-ui --mode vm --template-id 105
```

---

## 3. Playwright E2E UI Verification (Optional)

In addition to the standard HTTP port check performed by the test runner, you can test more complex interactions for components using Playwright (such as logging in or verifying form actions).

* UI test scripts are located in `tests/ui_verification/` and use the active IP address retrieved from `tests/proxmox_results.json`.
* **Run Playwright test for a specific component**:
  ```bash
  .venv/bin/pytest tests/ui_verification/ -k <component_id>
  ```
