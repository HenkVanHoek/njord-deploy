---
name: code-quality
description: Guidelines and commands for code quality, linting, and unit testing with pytest, flake8, mypy, and pre-commit specifically for NjordDeploy.
---

# Code Quality & Unit Testing (NjordDeploy)

Use this skill to guarantee code quality and run tests within the NjordDeploy project.

### All-in-One Code Quality Check (Python & JavaScript)
You can run the complete check locally and token-free using the provided script:
```bash
./scripts/check_code_quality.sh
```
This script runs all Python checks (via pre-commit) and then checks all JavaScript files with ESLint. This is the fastest and most token-efficient method to verify that all code is clean.

## Python & File Modification Guidelines:
* **PEP 8 Compliance**: Python code must follow PEP 8 standards.
* **Maximum Line Length**: Keep Python lines under 88 characters.
* **Code Validation**: Python code must pass all `flake8` and `mypy` checks.
* **Trailing Empty Line (CRITICAL)**: All edited or newly created files (Python, HTML, JS, CSS, YAML, JSON, Markdown, etc.) MUST end with a single trailing empty line (newline). This is enforced by the `end-of-file-fixer` hook in `pre-commit`. Always ensure your edits and file writes include this trailing newline so that `pre-commit` passes on the very first run.

## JavaScript Code Guidelines:
* No inline JavaScript. Logic must always be placed in external `.js` files.
* JavaScript must be linter-clean.

## Commands for Verification:

### 1. Run Tests (Pytest):
```bash
.venv/bin/pytest
```

### 2. Linting (Flake8):
```bash
.venv/bin/flake8
```

### 3. Static Analysis (Mypy):
```bash
.venv/bin/mypy .
```

### 4. Pre-commit Checks:
```bash
.venv/bin/pre-commit run --all-files
```

### 5. PyCharm IDE Diagnostics (JetBrains Companion):
If the agent is using the JetBrains Companion MCP server, it can retrieve live diagnostic warnings, type errors, and inspections directly from the IDE using the tool:
* Tool: `ide_get_diagnostics` (MCP server: `jetbrains-companion-py-dbb56c69`)
* Parameter: `file_path` (optional, absolute path to the file to inspect. If omitted, the active editor is used)

This enables the agent to query and immediately resolve live IDE warnings.

*Important note for large files:* The output of `ide_get_diagnostics` is capped at a maximum of 100 messages. If a file contains a lot of syntax highlighting or JSDoc type information (`INFO`), warnings/errors further down in the file might not be reported because the limit has been reached. In that case, use additional local tools (such as ESLint).

### 6. Common PyCharm Warnings & Solutions:
When resolving type and inspection warnings from PyCharm, apply the following guidelines:

#### Python-specific:
1. **Access to a protected member (e.g., `_get_or_create_key`):**
   * *Solution:* Expose the method as a public wrapper on the class (e.g., `get_ssh_key()`) instead of calling the private `_` method directly from an external script.
2. **Member 'None' of 'Any | None' does not have attribute 'get':**
   * *Solution:* Use `isinstance(variable, dict)` as a guard to narrow the type to a dictionary for PyCharm's analyzer.
3. **Expected type 'str', got 'Any | None' instead:**
   * *Solution:* Use `isinstance(variable, str)` as a guard to specify the type to PyCharm and guarantee it is a string.
4. **Too broad exception clause:**
   * *Solution:* Place `# noinspection PyBroadException` directly **above the corresponding `try:` block** (not above the `except:` block).
5. **Shadows name '...' from outer scope:**
   * *Solution:* Rename the local variable to prevent it from shadowing a function name or variable from an outer scope (e.g., the `create_app` factory scope).
6. **Expected type 'str | PathLike[str]', got 'str | bytes' instead (e.g., with `os.path.realpath`):**
   * *Solution:* Use `pathlib` methods such as `Path.resolve()` and convert them to strings with `str(path)` or `str(path.resolve())` if necessary instead of `os.path.realpath`. This prevents PyCharm's type checker from suspecting that `bytes` might be returned.
7. **Redundant parentheses (e.g., around string concatenation):**
   * *Solution:* Parentheses around consecutive string literals that are automatically concatenated by Python (e.g., `("a" "b")`) are redundant for the IDE and should be omitted.

#### JavaScript & JSDoc-specific:
1. **Redundant CSS unit in style attributes (e.g., `0%` or `0px`):**
   * *Solution:* The CSS inspection warns that `0` does not need a unit. For example, change `style="width: 0%;"` to `style="width: 0;"`.
2. **Argument type number is not assignable to parameter type string (e.g., with `setAttribute`):**
   * *Solution:* `element.setAttribute(name, value)` requires the value to be a string. Explicitly convert numbers to strings with `String(value)` or via string interpolation (e.g., `'100'`).
3. **Assigned expression type { ... } is not assignable to type X (JSDoc type mismatch):**
   * *Solution:* If an object is initialized without certain properties defined in the `@typedef` of type `X`, PyCharm flags a type error. Make optional properties in the `@typedef` optional using square brackets (e.g., `* @property {string} [mac]` or `* @property {DiskInfo[]} [disks]`).
4. **Ignored promise returned from async function:**
   * *Solution:* Make the event listeners or callbacks asynchronous (`async () => { ... }`) and call the method with `await` (e.g., `await showDiffForComponent(...)` or `await setupGitSyncFeatures()`).

### 7. Manual JavaScript Linting (ESLint):
If JavaScript pre-commit hooks are not activated, ESLint can be run manually using a temporary `.eslintrc.json` file in the root:
```bash
# Run eslint on all js files
eslint src/editor_app/static/*.js src/configurator_app/static/js/*.js
```
