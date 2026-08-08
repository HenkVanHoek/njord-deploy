# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]

### Added
- **Automatic Component Package Auto-Seeding**:
  - Added automatic background seeding (`seed_user_components_if_needed()`) in `src/utils/resource_utils.py` upon initial application startup.
  - Automatically fetches and initializes component templates from remote GitHub (`HenkVanHoek/njord-deploy-components`) when starting on fresh systems.
  - Added graceful offline fallback to built-in resources with user notification on screen (`downloaded` vs `fallback` warning).
- **Automatic System Browser Launcher**:
  - Integrated `webbrowser` launching in `run_editor.py` and `run_configurator.py` after Waitress server startup, opening `http://localhost:5000` / `http://localhost:5001` automatically.
  - Added `NO_BROWSER` environment variable flag for headless server deployments.
- **Post-Deployment AI Log Evaluator & Health Report**:
  - Integrated automated post-deployment log evaluation engine (`src/managers/deployment_evaluator.py`) using `ai_provider_manager` (Gemini, Ollama, HostYourAI, OpenAI) with deterministic rule-based fallback.
  - Added regex log sanitizer (`sanitize_logs()`) to scrub passwords, tokens, API keys, and SSH private keys before AI processing.
  - Categorized health reports into 3 actionable scenarios: `GREEN` (Clean run), `YELLOW` (Parameter tuning with documentation link), and `RED` (Showstopper/Bug with GitHub issue search and pre-filled GitHub issue draft).
  - Added `/api/deployment/<target_task_id>/evaluate` API endpoint and Bootstrap 5 frontend modal (`#deploymentEvalModal`) in `configurator_app` with auto-triggering on session completion and manual `🤖 AI Health Report` button.
  - Created architectural specification document [`docs/DEPLOYMENT_EVALUATION_SPEC.md`](file:///home/hvhoek/PycharmProjects/njord-deploy/docs/DEPLOYMENT_EVALUATION_SPEC.md).
- **Tailscale / Headscale Mesh Discovery**:
  - Integrated native Tailscale CLI daemon inspector (`get_tailscale_status`) and `/tailscale-status` endpoint.
  - Added permanent **Tailscale / Headscale Mesh Discovery** scan option on Step 1 with dynamic status badge (`Active` with online peer count vs `Inactive / Not Found`) and background checking spinner.
  - Enabled 1-click discovery of all online Tailnet mesh nodes without requiring L2 ARP sweeps.
- **SSH Key Authentication Guidance**:
  - Added an interactive SSH key authentication guidance banner on Step 1 providing clear instructions for authorizing public SSH keys (`ssh-copy-id username@target-ip`) on target nodes.
- **Dual-Server Release Build**: Configured PyInstaller and GitHub Release Pipeline (`release.yml`) to build and release two separate executables per platform: `NjordDeployConfigurator` (port 5001) and `NjordDeployEditor` (port 5000).
- **Waitress WSGI Production Web Server**: Replaced Flask Werkzeug development server with production-grade, cross-platform `Waitress` WSGI server (`serve()`) for both Configurator (`run_configurator.py`) and Editor (`run_editor.py`) applications.
- **Component Editor Statistics & QA Dashboard**:
  - Added real-time component, group, and package count badges to the Editor header title and view tabs (`Components (Z)`, `Groups (X)`, `Packages (Y)`).
  - Integrated `test_status` metadata property support across `ComponentReader`, `ComponentWriter`, and `ComponentManager`, automatically synchronizing with `# status:` headers in `docker-compose.template.yml` files.
  - Added interactive **Stats Modal** displaying test coverage statistics (% tested), architecture totals, and metadata quality indicators (missing descriptions, missing UI port variables, missing Traefik ports).
  - Added click-to-filter drill-down list in the Stats modal allowing instant navigation from any stat or QA metric directly to the target component in the Editor.
- **Ansible Host Key Bypass**: Configured `ansible_ssh_common_args` to bypass strict host key verification (`StrictHostKeyChecking=no` and `UserKnownHostsFile=/dev/null`) during deployments, preventing SSH connection failures when dynamic test VMs or reinstalled hosts change their host keys.
- **Proxmox Test Runner Skip List**: Added `gluetun` to the integration test skip list (`SKIPPED_COMPONENTS`) because VPN client containers require valid private credentials to start and cannot be verified automatically in isolated testing environments.

### Changed
- **Spacious Device Credentials Layout**: Refactored Step 2 discovered devices grid from cramped 6-column layout (`row-cols-xxl-6`) to maximum 3 spacious columns per row (`row-cols-1 row-cols-md-2 row-cols-xl-3 g-3`), providing full visibility for long hostnames, IP addresses, MACs, and credential text fields.

### Fixed
- **Actionable `nmap` Missing Error Handling**: Added explicit pre-scan executable check and `nmap.PortScannerError` handling in `NodeScanner`, returning clear package installation guidance (`sudo apt install nmap`) directly to the UI instead of generic error messages.

## [0.6.0] - 2025-10-12

### Added
- **Robust Error Handling**: Implemented a "reactive safety net" in the `SetupManager`. If a template syntax error occurs, the system now produces a detailed error report, including the failing component's name and the raw crashing content.
- **Enhanced UI Feedback**: The frontend (`app.js`) has been updated to correctly parse and display the new, detailed error reports from the backend, ensuring users receive actionable feedback on generation failures.
- **Automatic Traefik Dependency**: The `SetupManager` now automatically injects a `depends_on: [traefik]` directive for any component with `has_traefik_support: true`, resolving the Traefik 404 race condition at an architectural level.

### Changed
- **Architectural Shift to Docker DNS**: Re-architected service discovery to rely exclusively on Docker's built-in DNS. The `extra_hosts` directive has been removed from all component templates, simplifying the design and resolving runtime DNS conflicts.
- **Editor Save Logic**: The `ComponentManager` now uses a "Read-Merge-Write" pattern for saving `variables.json`. This fixes a critical data-loss bug by preserving complex fields (`options`, `depends_on`, `other_files`) that are not managed by the UI.
- **Centralized "Smart" Rendering**: Refactored the generation process to use the `ComponentManager` as a "smart renderer," responsible for injecting all necessary context (`component_id`, `VIRTUAL_HOST`, etc.) before rendering a template.
- **Deployment Script Hardening**: The `DeploymentManager` now uses the more robust `pwd` command instead of `echo $HOME` to determine the remote user's home directory, fixing a deployment failure in non-interactive SSH shells.
- **Editor Hash Generation**: The backend logic for the "Generate Hash" button in the editor has been changed from `argon2id` to the Traefik-compatible `bcrypt` algorithm.

### Fixed
- **Critical File Generation Crash**: Resolved a persistent `yaml.parser.ParserError` by correcting a fundamental indentation error in the `pi-hole` component template.
- **Traefik Login Failure**: Fixed the Traefik login issue by ensuring the correct (`bcrypt`) hash is generated and used.
- **Container Cleanup Logic**: Fixed a bug in `DeploymentManager` where containers could not be found during cleanup due to a name mismatch. Component templates now use `{{ component_id }}` to generate consistent container names.
- **Complete Test Suite Overhaul**:
    - Resolved all failing and hanging tests in `test_setup_manager.py` and `test_deployment_manager.py`.
    - Fixed a critical infinite loop in the dependency resolver that was crashing the test runner and IDE.
    - Corrected the mocking strategy for `SSHManager` to prevent real network connections during tests, resolving hangs and timeouts.

## [0.5.0] - 2025-10-06

### Added
- Traefik configuration validation in DeploymentManager to prevent duplicate internal ports and conflicting derived hostnames. ([296f1cf](https://github.com/HenkVanHoek/njord-deploy/commit/296f1cf))
- New `port_exclude_traefik` variable type in ComponentManager to allow excluding specific ports from Traefik label generation. ([ef0ddaa](https://github.com/HenkVanHoek/njord-deploy/commit/ef0ddaa), [7632f1d](https://github.com/HenkVanHoek/njord-deploy/commit/7632f1d))

### Changed
- Configurator UX/Security hardening: disable SSH credential fields when the "Manage" switch is off and auto-toggle on user input. ([ef0ddaa](https://github.com/HenkVanHoek/njord-deploy/commit/ef0ddaa), [7632f1d](https://github.com/HenkVanHoek/njord-deploy/commit/7632f1d))
- README: add reference to the pi-server-vm repository for Virtual Pi OS test server. ([faf21c4](https://github.com/HenkVanHoek/njord-deploy/commit/faf21c4))

### Fixed
- Editor: resolve "Save All Changes" failure and initialization stability issues in editor UI, adding defensive checks in `editor.v2.js`. ([faf21c4](https://github.com/HenkVanHoek/njord-deploy/commit/faf21c4))
- Deployment: finalize stability fixes and validation before any file transfer or remote execution (including conflict checks and better test harness). ([296f1cf](https://github.com/HenkVanHoek/njord-deploy/commit/296f1cf))
- Testing: explicit mock management in Configurator tests; temporary skip of unstable tests in terminal environment; various test cleanups. ([ef0ddaa](https://github.com/HenkVanHoek/njord-deploy/commit/ef0ddaa), [7632f1d](https://github.com/HenkVanHoek/njord-deploy/commit/7632f1d))

### Chore / Dependencies
- Fix dependency typo: use `argon2-cffi` instead of `argon-cffi`. ([9aaab1c](https://github.com/HenkVanHoek/njord-deploy/commit/9aaab1c))

---

Previous releases are not yet captured in this CHANGELOG. Future entries will continue following Keep a Changelog and SemVer.
