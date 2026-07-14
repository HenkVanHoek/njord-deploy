feat: Configure and stabilize development environment

This commit introduces comprehensive configuration for the development environment,
ensuring code quality, security, and consistent version management.

Key changes include:

- **Pre-commit Hooks:**
  - Re-enabled and configured `black`, `isort`, `flake8`, `mypy`, and `bandit` for automated code quality checks.
  - Resolved all reported `flake8` (line length) and `mypy` (type annotation, type incompatibility) errors.
  - Addressed `bandit` security warnings by implementing timeouts for requests, making host binding configurable, using secure temporary file handling, enabling Jinja2 autoescaping,
improving SSH host key verification, and sanitizing subprocess calls. Hardcoded credentials in test files are now loaded from environment variables.

- **Version Management:**
  - Consolidated version bumping to `bump-my-version` by transferring `bump2version`'s custom release part configuration to `pyproject.toml`.
  - Removed the deprecated `.bumpversion.cfg` file.

- **Environment Configuration:**
  - Created a `.env` file in the project root to centralize environment variables.
  - Updated application code (`src/configurator_app/app.py`, `test_scanner.py`) to load sensitive information (credentials, host binding) from environment variables.
  - Improved local IP detection in `src/utils/frigate_camera_config_tool.py` by leveraging `PiScanner.get_primary_ip()`, reducing reliance on `subprocess` calls.

These changes significantly enhance the project's maintainability, security, and development workflow.
