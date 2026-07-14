# Contributing to NjordDeploy

Thank you for considering contributing to NjordDeploy! We welcome contributions
from everyone.

This document provides guidelines for our development process, setting up
your environment, and contributing effectively to the project.

## ✅ Code of Conduct

Please read and follow our [Code of Conduct](https://github.com/HenkVanHoek/njord-deploy/blob/main/CODE_OF_CONDUCT.md).

## 🏛️ Architectural Doctrine

Before making changes, it is essential to understand the core principles that
guide our development. All contributions must adhere to the architectural
standards for the project to ensure the system remains stable, maintainable,
and testable.

**Please read the [ARCHITECTURE.md](https://github.com/HenkVanHoek/njord-deploy/blob/main/ARCHITECTURE.md)
file to review these principles.**

## 📋 Development Workflow & Traceability

We follow a lightweight, test-driven process to ensure that every
functional requirement is implemented, verified, and easily traceable from
the specification to the code.

A requirement is not considered "implemented" until there is a passing
automated test that explicitly verifies its behavior.

### How to Verify a Requirement's Implementation

To check if a requirement from the functional specification is complete,
follow these three steps:

#### 1. Find the Requirement in the Specification

Start with the `docs/FUNCTIONAL_SPEC.md` file. This is the single source
of truth for what the system is expected to do from a user's perspective.
Locate the User Story and the specific Acceptance Criterion you want to
verify.

#### 2. Find the Proof in the Tests

The proof of implementation is not the application code itself, but the
**automated test** that verifies it. Look in the `tests/` directory for a
test file and function that corresponds to the requirement.

-   **Spec Story:** "Enforcing Mutually Exclusive Choices"
-   **Test File:** `tests/configurator_app/test_selection_logic.py`
-   **Test Function:** `test_deselecting_item_in_exclusive_group()`

If a test that clearly describes the behavior **exists and is passing**,
the requirement is considered implemented and verified.

#### 3. Find the Implementation in the Git History

The `git commit` message is the link that connects the specification to
the code. We use a convention in our commit messages to make this link
explicit. The body of the commit message should reference the story it
implements.

**Example Commit Message:**

```
feat(configurator): Allow deselecting items in exclusive groups

This implements the user-facing requirement for opting out of an
exclusive group choice.

Implements: FUNCTIONAL_SPEC.md - "Enforcing Mutually Exclusive Choices"
```

You can use this convention to find the exact code changes for any
requirement with a single `git` command:

```bash
git log --grep="Enforcing Mutually Exclusive Choices"
```

This command provides a complete audit trail of the implementation.

## 🚀 Getting Started: The GitHub Workflow

1.  **Fork the repository**.
2.  **Clone your fork** to your local machine.
3.  Make your changes.
4.  **Push** your changes to your fork.
5.  Open a **Pull Request** to the main project repository.

## 👨‍💻 Development Setup

### 1. Environment

- **OS:** An Ubuntu environment is strongly recommended.
- **Virtualization:** For other OSes, use VirtualBox with the network
  adapter in **Bridged Mode**.
- **Do not use WSL:** Avoid Windows Subsystem for Linux for development and
  testing of the Configurator. Raw socket and privilege boundaries inside WSL
  make network scanning unreliable and often break nmap based discovery and the
  sudoers configuration. Prefer native Linux or a Linux VM with bridged
  networking. macOS is also a valid option.
- **Side note:** The related project named "pi-server-vm" is best developed on
  a Windows host. This is shared as context only and does not affect
  NjordDeploy.

### 2. System Dependencies

Ensure **git**, **python3.11+**, **ansible**, **nmap**, and **sshpass** are
installed on your system.

### 3. Project Installation

1.  Clone your forked repository.
2.  Navigate to the project root directory.
3.  Create and activate a Python virtual environment.
4.  Install all dependencies:

    ```bash
    pip install -e .[dev,test]
    ```

### 4. Nmap Permissions (Critical)

The Pi Scanner requires elevated permissions. This setup is OS-specific.

#### For Linux (Recommended)

You must add a **sudoers** rule to allow **nmap** to run without a
password. Replace the placeholder **your_username** with your actual Linux username.

```bash
echo "your_username ALL=(ALL) NOPASSWD: /usr/bin/nmap" | sudo tee /etc/sudoers.d/99-njorddeploy
sudo chmod 0440 /etc/sudoers.d/99-njorddeploy
```

#### For Windows & macOS

Please refer to the main **README.md** for the project for detailed
instructions on configuring Nmap and the firewall on these systems.

## 🧪 Running the Apps and Tests

### Run the Configurator App

```bash
flask --app src.configurator_app.app:create_app run
```

### Run the Editor App

```bash
flask --app src.editor_app.app:create_app run
```

### Run the Test Suite

From the project root directory:

```bash
pytest
```

## Linting and Security Checks

We enforce code quality and security via formatters, linters, type checks, and a
security scanner. All tools are wired into pre-commit, and can also be run
manually.

Run all checks with pre-commit:

```
pre-commit run --all-files
```

Run individual tools:

-   Black

```
black .
```

-   Isort

```
isort .
```

-   Flake8

```
flake8
```

-   MyPy

```
mypy .
```

-   Bandit (security scanning, configured via pyproject.toml)

```
bandit -c pyproject.toml -r src
```

## Creating a New Release

1. **Run Pytest**: `pytest`
2. **Run Pre-Commit Checks**: `pre-commit run --all-files`
3. **Run Pytest again, sometimes Pre-Commit changes files**: `pytest`
4. **Bump the Version**: `bump-my-version patch` (or `minor`/`major`)
5. **Push to GitHub**: `git push && git push --tags`

GitHub performs the building of the artifacts.
Although your development is done on a Linux PC,
the workflow in GitHub performs building of
the software depending on macOS or Windows.
