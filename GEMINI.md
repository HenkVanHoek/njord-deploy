# NjordDeploy Development Context

## System Architecture & Project Layout
- **Framework:** Python Flask-based monorepo containing `configurator_app` (user-facing) and `editor_app` (developer metadata management)[cite: 1, 4].
- **Core Logic:** Delegated to modules inside `src/managers/` and `src/utils/`[cite: 1, 5]. Keep Flask routes thin[cite: 1].
- **Single Source of Truth (SST):** `config/components_metadata.json` defines all service components.
- **Templates:** Service configurations use `docker-compose.template.yml` files located in `component_templates/`.
- **Target OS Policy:** Deployment targets Debian/Docker Engine. Do not depend on or install a system Python interpreter on the target host OS[cite: 4].
- **Domain:** njorddeploy.com

## Critical Safety Check (Shared Components)
- **CRITICAL:** The `component_manager` and other modules in `src/managers` or `src/utils` are shared between `configurator_app`, `editor_app`, and the test suite.
- **Rule:** Before modifying any shared module, perform a project-wide usage analysis to prevent regressions[cite: 1].

## Code Style & Standards (PEP 8 Compliant)
- **Python Line Length:** Max 88 characters (enforced by `black`)[cite: 1].
- **Imports & Linting:** Ordered via `isort`[cite: 1]. General style via `flake8`, static type checking via `mypy`, and security via `bandit`[cite: 1].
- **Naming Conventions:** Files/Variables/Functions use `snake_case`, Classes use `PascalCase`[cite: 1].
- **YAML Rules:** Always enclose YAML passwords in quotes. Use `yamllint` for validation.
- **Formatting:** Use 4 spaces for code blocks inside markdown text.
- **Comments & Docs:** Docstrings are required for public functions/classes[cite: 1]. All comments and documentation files (.md) must be in English.
- **PyCharm IDE Diagnostics:** When verifying code, prefer using the `ide_get_diagnostics` MCP tool to retrieve live warnings directly from PyCharm. If the output is truncated on large files, rely on local checks.
- **Type Narrowing:** Use explicit `isinstance(variable, dict)` or `isinstance(variable, str)` checks to resolve PyCharm `Member 'None'` and `Expected type` warnings.
- **Noinspection Placement:** Place `# noinspection PyBroadException` on the line immediately preceding the `try:` block, not the `except:` block.
- **Variable Casing:** Local function variables must be in lowercase `snake_case` (e.g. `stale_ct_threshold = 10`), not uppercase, to prevent PEP 8 casing warnings inside functions.
- **Protected Access:** Never call a protected member (starting with a single underscore `_`) from an external script or module. Implement a public wrapper method (e.g. `get_ssh_key()`) on the class instead.

## Test-Driven Development (TDD) Workflow
- **Framework:** `pytest`[cite: 1, 4]. Test structure mirrors the `src/` directory layout[cite: 1, 4].
- **Philosophy:** Adhere to "Red-Green-Refactor"[cite: 1]. A requirement is not implemented until a passing automated test explicitly verifies it[cite: 3].
- **Traceability:** When creating commits or writing code, map requirements from `docs/FUNCTIONAL_SPEC.md` to explicit test functions in `tests/`[cite: 3, 4, 5].

## File Modification Workflow
- **Data Protection:** NEVER manually edit or generate overrides for `config/components_metadata.json`. It must only be modified via the `editor_app`[cite: 1, 4, 5].
- **Version Management:** Do not place the version number inside the main application code. It must only be maintained in `version.py`.
- **Markdown Output:** Always output files ending in `.md` in raw text/markdown format.

## Commands Reference
- Run Test Suite: `pytest`[cite: 1, 4]
- Run Linting/Checks: `pre-commit run --all-files` or `flake8` / `mypy .`[cite: 1, 4]
- Run YAML linting: `yamllint`
