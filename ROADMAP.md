# NjordDeploy Project Roadmap

This document outlines the development roadmap for NjordDeploy. It is a living document that details our current priorities, planned features for upcoming releases, and long-term goals. Our aim is to be transparent about our direction and to help contributors understand where they can best apply their efforts.

## Guiding Principles

Our development is guided by the following principles:
1.  **Stability First**: Core features must be robust, reliable, and well-tested before new, complex functionality is added.
2.  **User Experience**: The primary goal is to simplify the self-hosting journey for our users.
3.  **Maintainability**: The codebase and architecture should remain clean, modular, and easy for new contributors to understand.

---

## Phase 1: Foundation & Core Usability (Complete)

This phase focused on creating a rock-solid, feature-rich, and user-friendly installer with a single, well-supported database backend.

*   **[✅] Solidify Core Installer**: Refactored to a full Python application with a seamless web-based UI. The core generation engine has been hardened for stability and now provides robust, detailed error reporting.
*   **[✅] Robust Component System**: Implemented a metadata-driven system (`components_metadata.json`) to easily add and manage new services.
*   **[✅] Comprehensive Testing**: Expanded the `pytest` suite to ensure the reliability of the installer and utility functions. The entire test suite is now stable, passing, and provides a solid foundation for future development.
*   **[✅] Documentation**: Created clear documentation for both end-users and contributors. Core architectural documents (`ARCHITECTURE.md`, `DATA_CONTRACTS.md`, `FUNCTIONAL_SPEC.md`) are now up-to-date with the latest design patterns.
*   **MariaDB as the Primary Database**: Standardized on MariaDB as the sole database option to ensure stability and reduce testing complexity.

---

## Phase 2: Expansion & Flexibility (Current Focus)

With a stable foundation, this phase will focus on expanding the ecosystem, improving the developer experience, and providing more options for advanced users.

*   **[✅] Container Engine Abstraction (Docker & Rootless Podman)**:
    *   **Why?**: To make NjordDeploy engine-agnostic, supporting standard Docker as well as security-hardened rootless Podman environments.
    *   **Implementation**: Introduced `ContainerEngine` class mapping CLI/Compose commands dynamically, with automated target OS provisioning (kernel low-port binding `net.ipv4.ip_unprivileged_port_start=53`, systemd user session lingering via `loginctl`, subuid/subgid mapping), parameterized Ansible playbook execution, and live UI switching.
*   **[✅] Proxmox Automated Testing Suite & Interactive Web GUI**:
    *   **Why?**: To provide automated, rapid end-to-end integration testing and validation of NjordDeploy components in clean virtualized environments without requiring manual Raspberry Pi flashing.
    *   **Implementation**: Built an interactive developer GUI (`run_proxmox_gui.py`) with real-time SSE log streaming, wildcard search, and 4-way cross-validation matrix testing across all target environments (LXC/VM × Docker/Podman).
*   **[✅] Dynamic Components Repository & Air-Gapped Mode**:
    *   **Why?**: To allow custom component repositories (private GitLab/Forgejo/Gitea) and air-gapped offline installations.
    *   **Implementation**: Fully dynamic `SyncManager` supporting `COMPONENTS_REPO_URL`, `COMPONENTS_REPO_BRANCH`, `COMPONENTS_REPO_TOKEN`, with live URL validation endpoint (`/api/validate-repo`) and offline local-only fallback mode.
*   **[In Progress] Component Configuration Tools**: Develop modular, post-installation tools for key services. The core ONVIF camera discovery and configuration tool for Frigate (`frigate_camera_config_tool.py`) has been completed, with dashboard integration being the next step.
*   **[✅] Integrated Backup & Restore Engine & REST API**:
    *   **Why?**: To provide automated, dependable backups and restoration specifically for NjordDeploy-managed services, volumes, and configurations.
    *   **Implementation**: Built `BackupManager` (`src/managers/backup_manager.py`) and REST endpoints (`/api/backup/*`) supporting remote volume discovery, disk footprint inspection, smart large-data flags, transactional container pausing, SHA-256 integrity manifests, single-click downloads, and safe state restoration with permission reconciliation.
*   **[✅] AI-Assisted Component Generation**:
    *   **Why?**: To dramatically accelerate the process of adding new services and lower the barrier for new contributors. As a nod to the powerful AI assistance that has been instrumental in this project's development, this feature brings that same power directly to our developers.
    *   **Implementation**: This has been implemented as an intuitive UI in the Editor where a developer can describe a service or input any Git repository URL (supporting GitHub, GitLab, Gitea, Forgejo, Codeberg, Bitbucket, and self-hosted Git servers). The backend queries an LLM to generate draft versions of the component's metadata, variables, and `docker-compose.template.yml`.
        1.  **[✅] Multi-Provider AI Support**: Fully active support for local models (Ollama RTX 3060) and cloud APIs (Google Gemini, OpenAI, HostYourAI EU), featuring automatic repository analysis, image presence verification across Docker Hub & OCI registries, validation warning flags, and multi-turn self-correction loops.
        2.  **[✅] Multi-Forge Git Support**: Generalized repository parsing and raw content extraction across GitHub, GitLab (including nested namespaces), Codeberg, Gitea, Bitbucket, and self-hosted instances.
*   **[✅] Closed-Loop Self-Healing DevOps & Cross-Matrix AI Failure Diagnosis**:
    *   **Why?**: To automatically diagnose heterogenous environment test failures across 4-way matrices (LXC/VM × Docker/Podman) and generate rapid self-healing patches.
    *   **Implementation**: Built `AIFailureDiagnoser` (`src/utils/ai_failure_diagnoser.py`) with root-cause categorization (`TEMPLATE_CONFIG`, `CORE_PLATFORM_CODE`, `ENVIRONMENT_INFRA`, `MATRIX_CONSTRAINT`) and 1-click Jinja2 compose/matrix patches, detailed in `docs/CASE_STUDY_SELF_HEALING_DEVOPS.md`.
*   **[✅] Standardized Production WSGI Entrypoints & Uniform IDE Integration**:
    *   **Why?**: To provide identical, reliable, multithreaded runtime entrypoints across all apps and eliminate IDE configuration discrepancies.
    *   **Implementation**: Created standardized Waitress WSGI runners (`run_editor.py` on port 5000, `run_configurator.py` on port 5001, `run_proxmox_gui.py` on port 5050) with auto-browser launching, port collision handling, and shared PyCharm `.run/` configurations.
*   **[✅] Headless REST API, Interactive Swagger UI & OpenAPI Specification**:
    *   **Why?**: To enable seamless programmatic deployments for external scripts, CI/CD pipelines, Homelab automation, and AI coding agents (such as Antigravity/Agy), with live in-browser testing and machine-readable schema contracts.
    *   **Implementation**: Fully documented and standardized REST endpoints across discovery, system analysis (`/api/v1/system/analyze`), Proxmox provisioning (`/api/proxmox/*`), deployment execution (`/deploy-configuration`), and real-time SSE streaming (`/stream-deployment/<task_id>`), published in [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md), with an interactive Swagger UI (`/api/docs`) and raw OpenAPI 3.0 specification (`/api/openapi.json`).
*   **[✅] Headless CLI Runner Mode & Zero-Browser Automation**:
    *   **Why?**: To execute automated deployments, volume backups, state restorations, and stack inspections directly from terminal scripts, cron jobs, and CI/CD without starting a web browser or WSGI server.
    *   **Implementation**: Built `NjordCliRunner` (`src/cli/runner.py`) integrated directly into `run_configurator.py` supporting `--deploy <config.json>`, `--backup`, `--restore <archive>`, `--inspect`, `--list-backups`, `--scan-stacks`, and `--example-config`.
*   **[✅] Advanced Installer Options**: Introduced multi-tenant management, customizable port offsets, persistent data directories, and target OS engine parameters.

---

## Phase 3: Milestone 100 Components, Multi-Tenancy & Enterprise Subscriptions (v1.0.0-RC1)

This milestone elevates NjordDeploy into a complete, enterprise-grade, multi-tenant self-hosting and DevOps orchestration platform.

*   **[✅] Milestone 100 Sovereign Components**:
    *   **Why?**: To provide a vast, curated, and rigorously tested library of 100 self-hosted services covering every key homelab and small enterprise domain.
    *   **Implementation**: Curated, templated, and tested 100 modular component stacks across AI/LLMs (Ollama, Open WebUI, LiteLLM, LibreChat), DevOps (Gitea, Woodpecker CI, n8n, Semaphore), Cloud Storage (Immich, Syncthing, MinIO, FileBrowser), Smart Home (Home Assistant, ESPHome, Node-RED, Zigbee2MQTT), Security (Vaultwarden, Authelia, LLDAP), and Observability (Prometheus, Grafana, Uptime Kuma, Netdata).
*   **[✅] Multi-Tenant SaaS Architecture & Tenant Isolation**:
    *   **Why?**: To support managed service providers, teams, and family organizations with isolated workspaces and granular access control.
    *   **Implementation**: Built `TenantManager` and `OrganizationManager` with isolated config caching, user roles (Owner, Admin, Member), and session-based tenant switching.
*   **[✅] 24/7 Persistent Self-Hosted Service Daemon (`run_service.py`)**:
    *   **Why?**: To allow homelab operators to run NjordDeploy continuously in background mode with automated SSH key persistence and continuous health checks.
    *   **Implementation**: Implemented `run_service.py` daemon entrypoint, systemd service unit (`services/systemd/njorddeploy.service`), Docker Compose deployment (`docker-compose.service.yml`), and unified `/api/health` diagnostics.
*   **[✅] Stripe Billing & Subscription Ecosystem**:
    *   **Why?**: To establish a sustainable commercial model supporting monthly and annual subscriptions with tier gating.
    *   **Implementation**: Integrated Stripe SDK (`stripe>=15.6.0`), monthly and annual pricing plans, secure Stripe Checkout sessions, self-service Stripe Customer Portal integration, and automated entitlement enforcement.
*   **[✅] Universal Multi-OS & Automated Disaster Recovery Suite**:
    *   **Why?**: To ensure 100% dependable deployment and state recovery across Debian 12, Ubuntu 24.04, Windows, and macOS.
    *   **Implementation**: Automated Proxmox backup/restore testrunners with clean VM/LXC provisioning, state mutation, restore validation, and universal Debian 12 standalone binary compilation.
*   **[✅] Generative Engine Optimization (GEO) & Machine-Readable AI Standards**:
    *   **Why?**: To enable accurate, hallucination-free indexing and retrieval by AI search engines (Perplexity, ChatGPT Search, Claude, Gemini) and AI coding agents.
    *   **Implementation**: Authored RFC-compliant `llms.txt` and `llms-full.txt` (conforming to [llmstxt.org](https://llmstxt.org/)), fine-tuned AI bot crawler directives in `robots.txt`, integrated Schema.org JSON-LD (`SoftwareApplication`, `WebSite`, `FAQPage`), and implemented root Flask routes for server daemon and website deployments.
*   **[✅] Enterprise Matrix Reporting & Playwright Vector PDF Export**:
    *   **Why?**: To provide self-contained, audit-grade documentation and visual verification proofs of 4-way hypervisor matrix tests that can be shared with enterprise clients and compliance teams offline.
    *   **Implementation**: Implemented headless Playwright Chromium A4 vector PDF engine (`GET /api/report/pdf`), isolated per-matrix markdown reporting (`PROXMOX_PACKAGE_TESTS_{pkg}_{mode}_{engine}_{ts}.md`), Base64 screenshot embedding, and local Docker Registry pull-through caching (`setup_test_gateway.py`).
*   **[✅] 100% Package Integration Matrix & Autonomous Proxmox Autopilot**:
    *   **Why?**: To validate all 11 curated Turnkey Application Packages with zero failures across all 4 target quadrants (44 total test executions) under zero-token autonomous supervision.
    *   **Implementation**: Built `scripts/proxmox_autopilot.py` watchdog daemon with fail-fast abort, automated SSH root-cause diagnostics, and Signal mobile notifications. Solved the unprivileged LXC Podman DNS limitation via a `/usr/bin/systemd-run` wrapper, achieving 44/44 passing tests (100% score) across LXC Docker, LXC Podman, VM Docker, and VM Podman.
*   **[✅] Zero-Vulnerability Security Baseline & Pre-Release Readiness Gates (v1.0.0-RC4)**:
    *   **Why?**: To achieve and maintain zero open security alerts across GitHub CodeQL (Code Scanning), Dependabot, and Secret Scanning, guaranteeing that releases and production environments are strictly verified.
    *   **Implementation**: Remediated all 16 CodeQL alerts (strict dictionary whitelist for path containment in `proxmox_gui.py`, origin validation for client/server open redirects, and credential redaction eliminating CodeQL AST heuristic false-positives). Built automated pre-release verification gates (`scripts/verify_release_readiness.py`) enforcing clean git working trees, zero open GitHub security alerts, linter and unit test suite passes, and GitHub Actions QC polling awareness before releasing.

---

## Phase 4: Long-Term Vision (Future)

This is a collection of ideas that are being considered for future minor/major iterations.

*   **[✅] PostgreSQL Support**: Fully integrated PostgreSQL and pgAdmin 4 components with automated volume persistence and database administration.
*   **Provider-Agnostic Off-site Backups**: Enhance the Backup & Restore tool with an automated off-site capability using a generic tool like `rclone`. This will allow users to send encrypted backups to any of the 70+ cloud storage providers `rclone` supports.
*   **Plugin Marketplace**: An interface where the community can submit new component templates for easy inclusion.
*   **Multi-Node/Clustering Support**: The ability to deploy services across multiple Raspberry Pi devices and distributed nodes.
*   **Enhanced Security Auditing**: Tools to scan configurations for common security misconfigurations.

We welcome discussion on this roadmap! Please open an issue to discuss any of the points above or to propose new features.
