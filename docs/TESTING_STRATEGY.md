
# NjordDeploy Testing Strategy

This document outlines the testing procedures for the NjordDeploy project, covering both the Python backend and the JavaScript frontend.

## 1. Backend Testing (Pytest)

The backend, written in Python with Flask, is tested using the `pytest` framework.

### Running Backend Tests

All backend unit and integration tests can be executed with a single command from the project root:

```bash
pytest
```

Pytest will automatically discover and run all test files (matching `test_*.py`) located in the `tests/` directory. Configuration for `pytest` is managed in the `pyproject.toml` file.

The suite currently contains **103 test functions** across the following test modules:

| Test Module                              | Scope                                                         |
|------------------------------------------|---------------------------------------------------------------|
| `tests/configurator_app/`               | Configurator App Flask routes and API responses               |
| `tests/editor_app/test_editor_app_api.py`| Editor App API endpoints (sync, components, metadata)        |
| `tests/test_ai_generator.py`            | AIGenerator Gemini API integration (mocked)                   |
| `tests/test_artifact_generator.py`      | Docker Compose artifact rendering                             |
| `tests/test_auth_utils.py`             | Authentication utility functions                              |
| `tests/test_component_manager.py`       | ComponentManager CRUD and validation logic                    |
| `tests/test_component_reader.py`        | ComponentReader file-reading contracts                        |
| `tests/test_component_writer.py`        | ComponentWriter file-writing contracts                        |
| `tests/test_deployment_manager.py`      | DeploymentManager conflict detection and task logic           |
| `tests/test_installer.py`              | Installer bootstrap logic                                     |
| `tests/test_node_scanner.py`           | NodeScanner network discovery (mocked)                        |
| `tests/test_proxmox_client.py`         | ProxmoxClient REST API adapter (mocked)                       |
| `tests/test_resource_utils.py`         | Resource utility functions                                    |
| `tests/test_scanner.py`               | Legacy scanner compatibility                                  |
| `tests/test_setup_manager.py`          | SetupManager deployment package preparation                   |
| `tests/test_ssh_manager.py`            | SSHManager connection, upload, and command execution (mocked) |
| `tests/test_sync_manager.py`           | SyncManager fetch, diff, pull, push, and validation (mocked) |

## 2. Frontend Testing (Playwright)

The JavaScript frontend for the `editor_app` is tested using the Playwright framework. This approach allows for both isolated UI component unit tests and full end-to-end (E2E) integration tests in a real browser environment.

### 2.1. One-Time Environment Setup

Before running the frontend tests for the first time, you must prepare your development environment by installing the necessary Node.js dependencies and browser binaries.

1.  **Install Node.js Dependencies:**
    This command reads the `package.json` file and installs Playwright and its dependencies into a `node_modules` directory.

    ```bash
    npm install
    ```

2.  **Install Playwright Browsers:**
    This command downloads the browser binaries (Chromium, Firefox, WebKit) that Playwright uses to run the tests.

    ```bash
    npx playwright install
    ```

### 2.2. Standard Procedure: Running the Full Frontend Suite

To run the entire suite of frontend tests, execute the following command from the project root:

```bash
npx playwright test
```

This command will automatically:
1.  Find the `playwright.config.js` configuration file.
2.  Start a local web server (`http-server`) and a local Flask instance to serve the application files.
3.  Discover and run all test files (matching `*.spec.js`) in the `tests/editor_app/playwright/` directory.
4.  Execute the tests in a headless Chromium browser by default.
5.  Generate an HTML report in the `playwright-report/` directory upon completion.

The following Playwright spec files are currently active:

| Spec File                                               | Scope                                            |
|---------------------------------------------------------|--------------------------------------------------|
| `tests/editor_app/playwright/editor_v2.spec.js`        | Editor App end-to-end UI interactions            |
| `tests/editor_app/playwright/ui_render_utils.spec.js`  | Unit tests for JavaScript UI rendering utilities |

### 2.3. Manual Testing and Debugging

During development, it is often more efficient to run a single test or to visually inspect the browser as the test runs.

*   **To run a single test file:**

    ```bash
    npx playwright test tests/editor_app/playwright/editor_v2.spec.js
    ```

*   **To run tests in a headed browser (UI visible):**

    ```bash
    npx playwright test --headed
    ```

*   **To debug a test with the Playwright Inspector:**
    This is the most powerful debugging tool. It pauses the test execution and opens a browser with the Playwright Inspector, allowing you to step through commands and inspect the DOM.

    ```bash
    PWDEBUG=1 npx playwright test
    ```

## 3. Post-Deployment UI Verification (Playwright via Pytest)

A third testing layer exists in `tests/ui_verification/`. These tests use Playwright's Python bindings via `pytest-playwright` and run **after** a component has been deployed to a real environment (e.g., via the Proxmox test runner). They verify that the deployed service's web interface is actually reachable and renders correctly.

These tests are automatically skipped by `pytest` if:
- Playwright is not installed (`playwright` Python package missing).
- The component was not found in `tests/proxmox_results.json` (i.e., the Proxmox runner has not been executed).
- The target port is unreachable.

| Test File                                         | Component Tested |
|---------------------------------------------------|------------------|
| `tests/ui_verification/uptime_kuma_ui_test.py`   | Uptime Kuma      |

## 4. Unified Testing Workflow

While backend and frontend tests are run with separate commands, they can be orchestrated by a simple build tool or script for a unified development experience.

The `Makefile` in the project root provides the following targets:

```makefile
.PHONY: test test-backend test-frontend

# Run all tests for the entire project
test: test-backend test-frontend

# Run only the Python backend tests
test-backend:
	pytest

# Run only the JavaScript frontend tests
test-frontend:
	npx playwright test
```

With this in place, you can run `make test` to validate the entire application.

## 5. Proxmox Hypervisor Matrix Testing

NjordDeploy features a high-fidelity automated test matrix suite that validates individual components and multi-app turnkey packages across real virtualized environments on a Proxmox VE server.

### 5.1 The 4-Way Cross-Validation Matrix

To ensure unconditional reliability in both homelab and production enterprise environments, components and stacks are verified across a 4-way matrix (2 targets × 2 engines):

| Environment Combination | Target Hypervisor Mode | Container Runtime Engine | Template ID |
|:---|:---|:---|:---|
| **LXC + Docker** | Unprivileged Debian 12 LXC Container | Docker Engine (CE) | `912` |
| **LXC + Podman** | Unprivileged Debian 12 LXC Container | Rootless Podman | `914` |
| **VM + Docker** | Debian 12 KVM Virtual Machine (Cloud-Init) | Docker Engine (CE) | `911` |
| **VM + Podman** | Debian 12 KVM Virtual Machine (Cloud-Init) | Rootless Podman | `913` |

### 5.2 Test Runners & Interactive GUI

Two dedicated runners orchestrate testing over agentless SSH on an isolated test subnet (`10.99.0.0/24` on `vmbr1`):
1. **Single Component Runner (`scripts/proxmox_test_runner.py`)**:
   Tests individual components from `component_templates/` in isolation.
2. **Turnkey Package Runner (`scripts/proxmox_package_test_runner.py`)**:
   Tests multi-service bundles (e.g. `agile-ops`, `media-stack`, `smarthome-stack`) with full dependency wiring and zero-collision port validation.
3. **Interactive Test GUI (`run_proxmox_gui.py` on port `5050`)**:
   Real-time SSE log streaming, dynamic package/component selection, environment filtering, live result tracking, and AI-assisted root cause diagnosis.

### 5.3 Local Docker Registry Pull-Through Cache Mirror

Multi-environment matrix runs pull dozens of container images. To eliminate WAN bandwidth overhead and Docker Hub rate limiting:
- LXC container `920` runs a dedicated Docker Registry pull-through mirror at `10.99.0.2:5000` with 30GB storage on `vmbr1`.
- Provisioned via [`scripts/setup_test_gateway.py`](../scripts/setup_test_gateway.py).
- Runners configure test instances to route all Docker and Podman image pulls through this local cache.
- Networking follows a strict KISS policy: standard upstream DNS is provided directly by the Proxmox host NAT gateway (`10.99.0.1`), avoiding container-level DNS interception.

### 5.4 Isolated Matrix Reports & Visual Proofs

Test results and visual verification proofs are recorded with full isolation:
- **JSON Manifests**: `tests/proxmox_results.json` and `tests/proxmox_package_results.json`.
- **Global Reports**: `docs/PROXMOX_TESTS.md` and `docs/PROXMOX_PACKAGE_TESTS.md`.
- **Per-Matrix Isolated Reports**: `docs/PROXMOX_PACKAGE_TESTS_{pkg}_{mode}_{engine}_{ts}.md`.
- **Automated Screenshots**: Headless Playwright captures live web interfaces at runtime, stored in `docs/images/test_screenshots/`.

### 5.5 Playwright Vector PDF Export

For audit compliance, client deliverables, and offline documentation, the Proxmox GUI provides single-click export to A4 vector PDF (`GET /api/report/pdf`):
- Rendered via headless Playwright Chromium with `@media print` styling.
- Local screenshot images are converted and embedded as Base64 data URIs for 100% self-contained, offline viewing.
- Features automatic running headers/footers with dynamic page numbering.

### 5.6 Autonomous Test Autopilot & Signal Alerting

To enable zero-touch, overnight, and long-running hypervisor testing, NjordDeploy includes an autonomous watchdog daemon:
- **Zero Token Overhead**: [`scripts/proxmox_autopilot.py`](../scripts/proxmox_autopilot.py) runs locally in background mode (`--watch`), continuously supervising the active test runner process without generating continuous LLM token consumption.
- **Fail-Fast Early Abort**: Halts the test runner immediately on package health check probe failure (`POST /api/stop`), preserving hypervisor CPU and disk I/O.
- **Automated Root-Cause SSH Diagnosis**: Before instances are destroyed, the autopilot connects via SSH to the target, collects container exit codes, tails the last 50 lines of logs, inspects network DNS settings, and produces structured markdown diagnosis reports (`docs/AUTOPILOT_DIAG_*.md`).
- **Real-Time Signal Mobile Alerts**: Delivers immediate failure notifications with extracted stack traces and milestone completion celebrations directly to the operator's phone via the Signal REST API.

### 5.7 100% Package Matrix Milestone & LXC Podman DNS Hardening

On September 5, 2026, the complete 4-way matrix achieved a **100% pass rate (44/44 tests passed)** across all 11 curated Turnkey Application Packages:
- **LXC / Docker**: 11 / 11 Passed (100%)
- **LXC / Podman**: 11 / 11 Passed (100%)
- **VM / Docker**: 11 / 11 Passed (100%)
- **VM / Podman**: 11 / 11 Passed (100%)

Key to this milestone was resolving the unprivileged LXC Podman DNS limitation:
- Netavark's mistaken assumption that root inside an unprivileged user namespace is rootless was resolved via a `/usr/bin/systemd-run` wrapper that strips `--user` for UID 0.
- `aardvark-dns` attaches directly to the container's systemd system scope, enabling sub-millisecond container-to-container DNS resolution with 0% packet loss across all complex multi-container stacks.
- Permanently baked into Proxmox Golden Template `914` (`njorddeploy-podman-lxc-template`), Ansible playbook, and automated test runners.
