# Specification: Context Generator for NjordDeploy Expert

## 1. Purpose
The `context_generator.py` script aggregates the NjordDeploy and Sovereign
Stack codebase into a single `llm_context.txt` for local LLM consumption.
It ensures that hardware limits (RTX 3060 12GB) are respected and project
standards are validated before generation [cite: 2025-06-11, 2026-01-20].

## 2. Global Standards & Compliance
* **Licensing**: Every script must contain the full MIT License in English
    [cite: 2026-01-24].
* **Formatting**: Python code must strictly adhere to an 88-character line
    limit [cite: 2025-09-22].
* **Indentation**: 4-space indentation for all code blocks in markdown
    and raw text [cite: 2025-11-04].
* **Language**: All generated documentation and comments must be in English
    for GitHub publication [cite: 2025-06-11].
* **Security**: YAML files must be scanned for secrets/passwords; values
    must be enclosed in double quotes [cite: 2025-11-03].

## 3. Advanced Exclusion Logic
To prevent VRAM "500 errors" (caused by exceeding 90k tokens), the script
implements a multi-layer exclusion strategy [cite: 2026-01-20]:
* **Folders**: `.venv`, `venv`, `env`, `.env`, `.git`, `__pycache__`,
    `node_modules`, `.idea`, `.vscode`, `dist`, `build`, `.pytest_cache`,
    `playwright-report`, `test-results`, `vendor`, `lib`, `fonts`.
* **File Bloat**: Skip any file containing `.min.` (e.g., `bootstrap.min.css`)
    as they lack debuggable logic and consume excessive tokens.
* **Self-Referencing**: The script must never include its own output
    (`llm_context.txt` or `included_files.txt`).

## 4. Hardware Awareness (RTX 3060 12GB)
* **Token Calculation**: Estimated at 4 characters per token.
* **Thresholds**:
    - **Safe**: < 32,768 tokens (Optimized for KV-cache stability).
    - **Warning**: 32,768 - 90,000 tokens (Requires monitoring).
    - **Critical**: > 90,000 tokens (High risk of failure).

## 5. Architectural Intelligence
* **UI Mapping**: If an HTML template from `configurator_app` or `editor_app`
    is processed, the script forces the inclusion of its master JavaScript
    controller (`app.js` or `editor_app.js`) to provide the LLM with the
    dynamic layout logic [cite: 2026-01-20].

## 6. Output Artifacts
* `llm_context.txt`: Full concatenated codebase with Master Instructions.
* `included_files.txt`: Manifest of all files, including VRAM status
    and a "Top 5 Largest Files" bloat analysis.
