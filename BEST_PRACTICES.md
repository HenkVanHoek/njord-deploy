### 📘 Project Best Practices

#### 1. Project Purpose
This project, NjordDeploy, is a Flask-based application designed to simplify the provisioning and management of self-hosted services on a Raspberry Pi. It provides a user-friendly interface for end-users (`configurator_app`) and a dedicated interface for developers (`editor_app`) to manage the underlying service metadata.

#### 2. Project Structure
- **`src/`**: The Python source root.
  - **`configurator_app/`**: The main user-facing Flask application for service configuration.
  - **`editor_app/`**: A separate Flask application for developers to edit component metadata.
  - **`managers/`**: Core logic for handling components, deployments, and system setup.
  - **`utils/`**: Shared utility functions, including SSH, authentication, and resource management.
  - **`config_tools/`**: Tools for managing application configuration.
  - **`pi_scanner.py`**: A script for discovering Raspberry Pi devices on the local network.
- **`config/`**: Contains static configuration files.
  - **`components_metadata.json`**: The Single Source of Truth (SST) for all service component definitions.
- **`component_templates/`**: Holds `docker-compose.template.yml` and other configuration templates for each supported service.
- **`tests/`**: Contains all automated tests. The structure mirrors the `src` directory.
- **`pyproject.toml`**: Defines project dependencies, build configurations, and code style standards.

#### 3. Test Strategy
- **Framework**: We use `pytest` for all backend testing.
- **Organization**: Tests are located in the `tests/` directory and are structured to mirror the application's source code layout.
- **Philosophy**: We adhere to a Test-Driven Development (TDD) methodology for all backend code. The cycle is "Red-Green-Refactor," where the refactor step includes passing all static analysis checks.

#### 4. Code Style
- **Formatting**: Code is automatically formatted using `black` for consistency and `isort` for import ordering. The maximum line length is 88 characters.
- **Linting**: We use `flake8` for general style enforcement and `mypy` for static type checking.
- **Naming Conventions**:
  - **Files**: `snake_case.py`
  - **Variables**: `snake_case`
  - **Functions**: `snake_case()`
  - **Classes**: `PascalCase`
- **Commenting**: All public functions and classes should have clear docstrings.
- **Error Handling**: We practice defensive coding. Always check for potential `None` values or empty lists before access.

#### 5. Common Patterns
- **Application Factory**: Flask applications are created using the `create_app()` factory pattern to ensure consistent and configurable app instances.
- **Single Source of Truth (SST)**: The `config/components_metadata.json` file is the definitive source for all component data. The `editor_app` is the designated tool for modifying this file.
- **Monorepo**: The `configurator_app` and `editor_app` are maintained in a single repository to ensure that changes to shared data contracts are atomic and consistent.

#### 6. Do's and Don'ts
- ✅ **Do** follow the TDD "Red-Green-Refactor" cycle for all backend changes.
- ✅ **Do** ensure all new code passes `flake8` and `mypy` checks before committing.
- ✅ **Do** add or update tests when adding or modifying functionality.
- ❌ **Don't** manually edit `config/components_metadata.json`. Use the `editor_app`.
- ❌ **Don't** introduce business logic into Flask route handlers. Keep routes thin and delegate logic to manager modules.
- ❌ **Don't** commit code that violates the formatting rules enforced by `black` and `isort`.
- ✅ **Do** perform a project-wide usage analysis before modifying any shared module in `src/managers` or `src/utils`. This is a critical safety check to prevent regressions in the `configurator_app`, `editor_app`, and the test suite. The `component_manager` is a frequent source of such errors.

#### 7. Tools & Dependencies
- **Core Framework**: Flask
- **Key Libraries**:
  - `pytest`: For automated testing.
  - `paramiko`: For SSH connectivity.
  - `python-nmap`: For network scanning.
  - `PyYAML` & `jinja2`: For template and configuration management.
- **Development Tools**:
  - `black`, `isort`, `flake8`, `mypy`: For code quality and style.
  - `bandit`: Security scanning for Python, configured via `pyproject.toml` and
    enforced in the pre-commit hooks.
  - `pre-commit`: To automate code quality checks before commits.

#### 8. Other Notes
- This repository is managed with an LLM-driven development workflow. Adhering to the practices outlined here is critical for maintaining code quality and ensuring the LLM can effectively contribute.
- All Python code must be PEP 8 compliant. The project enforces a maximum line length of 88 characters, which is handled automatically by the "black" formatter.
- **Shared Components**: Be aware that some components, like the `component_manager`, are shared between the `configurator_app` and the `editor_app`. Changes in these shared modules must be tested for impact on both applications.
