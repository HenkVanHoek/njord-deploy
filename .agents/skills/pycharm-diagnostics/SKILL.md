---
name: pycharm-diagnostics
description: Diagnostic guidelines, workflows, and inspection resolution patterns for PyCharm IDE diagnostics and JetBrains Companion MCP tools.
---

# PyCharm Diagnostics & Inspection Resolution Skill

Use this skill to diagnose, inspect, and systematically resolve all PyCharm IDE inspections, warnings, and type errors across Python and JavaScript files in NjordDeploy.

---

## 1. Automated Self-Verification Mandate

Whenever code changes or fixes are applied, this skill must **automatically re-verify itself in a self-healing loop**:
1. Apply the code change.
2. Query `ide_get_diagnostics` (JetBrains Companion MCP) or inspect live warnings on the modified file.
3. Check for any secondary warnings or regressions introduced by the fix.
4. If warnings remain, immediately apply targeted fixes and re-verify until **0 warnings/problems remain**.
5. Run `pre-commit run --all-files` and `pytest`.

---

## 2. PyCharm Inspection Patterns & Solutions (Reference Guide)

### A. Type Narrowing Across `try:` Boundaries (CRITICAL)
* **Problem**: PyCharm resets flow-based type narrowing across `try:` boundaries when a variable is typed as `Optional[T]` in function parameters or outer scope. Inside the `try:` block, PyCharm flags `Expected type 'int', got 'int | None' instead`.
* **Resolution**: Assign to a strongly-annotated local variable inside the `isinstance` guard before entering the `try:` block.
```python
# Correct
def _force_kill(p: subprocess.Popen, kill_pgid: Optional[int]):
    time.sleep(1.5)
    if isinstance(kill_pgid, int) and kill_pgid > 1:
        target_pgid: int = kill_pgid
        # noinspection PyBroadException
        try:
            if target_pgid != os.getpgrp():
                os.killpg(target_pgid, signal.SIGKILL)
        except Exception:  # nosec B110
            pass
```

### B. Subprocess `Popen` Nullability & Attribute Access
* **Problem**: `Member 'None' of 'Popen[Any] | None' does not have attribute 'stdout'` / `'wait'`.
* **Resolution**: Assign `subprocess.Popen(...)` to a direct local variable (e.g. `running_proc = subprocess.Popen(...)`) before storing on `self.process`, and guard attribute access with `if running_proc.stdout is not None:`.
```python
# Correct
running_proc = subprocess.Popen(...)
self.process = running_proc
if running_proc.stdout is not None:
    for line in iter(running_proc.stdout.readline, ""):
        ...
running_proc.wait()
```

### C. String & Path Nullability (`Any | None` / `str | PathLike[str]`)
* **Problem**: `Type 'None' doesn't define '__str__' or '__repr__'` or `Expected type 'str | PathLike[str]', got 'Any | None' instead`.
* **Resolution**: Explicitly narrow the string variable with `isinstance(raw_id, str)` before using it in path concatenations. Avoid calling `str(val)` on a value that might be inferred as `None`.
```python
# Correct
raw_comp_id = payload.get("component_id")
if not isinstance(raw_comp_id, str) or not raw_comp_id.strip():
    return jsonify({"error": "component_id is required"}), 400
comp_id = raw_comp_id.strip()
tmpl_file = project_root / "component_templates" / comp_id / "docker-compose.template.yml"
```

### D. Unused Parameter in Callbacks
* **Problem**: `Parameter 'x' value is not used`.
* **Resolution**: Prefix unused arguments with an underscore (e.g., `_engine: str = ""`).

### E. Broad Exception Clauses (`PyBroadException`)
* **Problem**: `Too broad exception clause`.
* **Resolution**: Place `# noinspection PyBroadException` on the line **immediately preceding the `try:` block**.

### F. Spell Checking & Grammar Inspections
* **Problem**: `Typo: In word 'PYTHONUNBUFFERED'` or `Did you mean the formatting language?` for 'markdown'.
* **Resolution**:
  - For environment variables, add `# noinspection SpellCheckingInspection`.
  - For docstrings referring to Markdown, use capital `Markdown`.

---

## 3. Verification Workflow

1. Query PyCharm live diagnostics via `ide_get_diagnostics`.
2. Run Flake8: `flake8 <modified_files>`
3. Run Pre-commit: `pre-commit run --all-files`
4. Run Pytest: `pytest <related_test_files>`
5. Confirm 0 problems in PyCharm.
