
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
2.  Start a local web server to serve the application files.
3.  Discover and run all test files (matching `*.spec.js`) in the `tests/editor_app/playwright/` directory.
4.  Execute the tests in a headless Chromium browser by default.
5.  Generate an HTML report in the `playwright-report/` directory upon completion.

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

## 3. Unified Testing Workflow

While backend and frontend tests are run with separate commands, they can be orchestrated by a simple build tool or script for a unified development experience.

For example, you can add the following scripts to a `Makefile` in the project root:

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

## 4. Proxmox Component Integration Testing

NjordDeploy features a high-fidelity automated test runner that validates components by deploying them on dynamically cloned VMs within a Proxmox VE server.

This test runner performs the following steps:
1. Clones a master template VM on the Proxmox host.
2. Injects SSH keys and boots the VM using Cloud-Init.
3. Retrieves the dynamic IP address of the booted VM.
4. Generates deployment configurations and runs the Ansible deployment playbook.
5. Performs HTTP and docker health verification checks.
6. Automatically cleans up by destroying the temporary VM.

For credentials, setup instructions, and advanced parameters, refer to the [.agents/skills/proxmox-test/SKILL.md](file:///home/hvhoek/PycharmProjects/njord-deploy/.agents/skills/proxmox-test/SKILL.md) skill file.
```

With this in place, you can run `make test` to validate the entire application.
