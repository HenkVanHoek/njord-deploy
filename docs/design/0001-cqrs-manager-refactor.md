# Design Decision Document: NjordDeploy Architecture Refactor

**Status:** Approved
**Date:** 2026-03-08
**Subject:** Transition to CQRS Managers and Decoupled Deployment Logic

---

## 1. Context and Problem Statement

The original `ComponentManager` was a monolithic class responsible for reading metadata, writing updates, and generating deployment artifacts. This resulted in:
* **High Coupling:** Changes to the metadata structure required modifications to the entire class.
* **Linter/Type Complexity:** Managing diverse data types in one class triggered persistent IDE warnings and type-hinting errors.
* **Deployment Inconsistency:** The Web UI and the CLI Installer utilized different logic to assemble Docker Compose files, leading to "loose ends" in the installation process.

## 2. Decision: CQRS Manager Split

We decided to split the monolithic manager into specialized components following the **Command Query Responsibility Segregation (CQRS)** principle.

### 2.1 The New Manager Suite
* **`ComponentReader` (The Query):** Strictly handles reading `components_metadata.json` and verifying template existence. It is the single source of truth for component status.
* **`ComponentWriter` (The Command):** Handles updates to the metadata file. It ensures atomic writes to prevent file corruption.
* **`ArtifactGenerator` (The Logic):** Encapsulates the Jinja2 templating logic. It takes raw metadata and transforms it into a unified, valid `docker-compose.yml`.



---

## 3. Decision: Role of Ansible vs. Python

We will maintain **Ansible** as the primary orchestration engine for the initial installation while using **Python** as the "Configuration Intelligence" layer.

### 3.1 The Verdict
* **Python Responsibility:** Generates the complete, merged `docker-compose.yml` and handles variable substitution.
* **Ansible Responsibility:** Infrastructure as Code (IaC). It handles directory creation, file transfer, and ensures the target Raspberry Pi is in the correct state (Idempotency).

**Outcome:** The Ansible Playbook is simplified to a "dumb" transport layer, copying pre-generated artifacts rather than trying to re-assemble fragments on the remote node.

---

## 4. Implementation Details

### 4.1 Path Management
All pathing logic has transitioned from `os.path` to `pathlib.Path` to improve cross-platform compatibility (Windows PyCharm host vs. Linux VM target) and code readability.

### 4.2 Security and Formatting
* **SSH:** Transitioned from `sshpass` to `Paramiko` with Ed25519 key-based authentication.
* **Code Quality:** Mandatory pre-commit hooks (Black, Flake8, MyPy, Bandit) are enforced to ensure PEP 8 compliance and security hardening.

## 5. Consequences

### 5.1 Positive
* **Scalability:** New components can be added by simply creating a directory in `component_templates/` and updating the JSON.
* **Testability:** The project now maintains a 100% pass rate on core logic, as verified by the consolidated 35-test suite.
* **Consistency:** The `njorddeploy_installer.py` now produces identical output to the Web UI.

### 5.2 Negative
* **Initial Overhead:** Requires more files and a stricter project structure.
* **Dependency:** Requires `ansible-runner` to be correctly configured in the development environment.

---

## 6. Verification

The success of this decision is measured by the successful execution of the full test suite:
```bash
pytest
```
*Result: 35 passed, 0 failed.*
