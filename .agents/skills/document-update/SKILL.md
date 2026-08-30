---
name: document-update
description: Workflows for updating project documentation and roadmaps before committing or pushing changes to Git.
---

# Document and Road Map Update Workflow

This skill guides the agent (and developers) on how to verify and update all project documentation, specifications, and the project road map after making updates and before committing or pushing changes to Git/GitHub.

## Why Update Documents?

Keeping documentation synchronized with the codebase ensures that:
1. Contributors and developers always have an up-to-date mental map of the project.
2. The project's automated tools (like the local `njorddeploy-expert` model) have accurate codebase context (`llm_context.txt`).
3. The road map and changelog remain true sources of truth for release cycles.

---

## Workflow Steps

Whenever you complete a feature, bug fix, or component update, perform the following steps:

### 1. Run Automated Document Regeneration
We use a unified script to regenerate all dynamically generated documentation and context files:

```bash
python scripts/update_docs.py
```

This script automatically runs:
*   [generate_services_doc.py](file:///home/hvhoek/PycharmProjects/njord-deploy/scripts/generate_services_doc.py): Rebuilds [docs/SUPPORTED_SERVICES.md](file:///home/hvhoek/PycharmProjects/njord-deploy/docs/SUPPORTED_SERVICES.md) based on the latest [config/components_metadata.json](file:///home/hvhoek/PycharmProjects/njord-deploy/config/components_metadata.json).
*   [context_generator.py](file:///home/hvhoek/PycharmProjects/njord-deploy/context_generator.py): Rebuilds the AI codebase context file `llm_context.txt` and its manifest `included_files.txt`.

### 2. Manual Checklist: Review and Update Documents

Review the following files and make manual edits if they are impacted by your changes:

*   **[ROADMAP.md](file:///home/hvhoek/PycharmProjects/njord-deploy/ROADMAP.md)**:
    *   Locate the active development Phase (e.g., *Phase 2: Expansion & Flexibility*).
    *   Mark completed features with `[✅]`.
    *   Update the status of in-progress features with `[In Progress]`.
    *   Add brief technical notes or implementation summaries under the items if needed.
*   **[CHANGELOG.md](file:///home/hvhoek/PycharmProjects/njord-deploy/CHANGELOG.md)**:
    *   Verify that your changes are documented under the current development version section.
    *   Ensure they are categorised correctly under `### Added`, `### Changed`, or `### Fixed`.
    *   Adhere strictly to the *Keep a Changelog* format and Semantic Versioning.
*   **[README.md](file:///home/hvhoek/PycharmProjects/njord-deploy/README.md)**:
    *   If you introduced a new major feature or CLI option, document its description, parameters, or environment variables.
*   **Architectural Specifications** (`docs/`):
    *   [docs/ARCHITECTURE.md](file:///home/hvhoek/PycharmProjects/njord-deploy/docs/ARCHITECTURE.md): Update if the project architecture, module structure, or component-sync mechanisms have changed.
    *   [docs/DATA_CONTRACTS.md](file:///home/hvhoek/PycharmProjects/njord-deploy/docs/DATA_CONTRACTS.md): Update if metadata schemas, variables configurations, or API payload contracts are modified.
    *   [docs/FUNCTIONAL_SPEC.md](file:///home/hvhoek/PycharmProjects/njord-deploy/docs/FUNCTIONAL_SPEC.md): Update if new functional behaviors or user-facing requirements are established.

### 3. Verify Code Quality, PII Sanitization and Format
After completing documentation edits:

1.  **Security, PII & IP Sanitization Audit (MANDATORY)**:
    Ensure no private production IP addresses (`192.168.178.x`, real VPS IPs) or personal email addresses (e.g. `@almereautomatisering.nl`) exist in any documentation files. Always use generic placeholders (e.g. `<server-ip>`, `192.168.1.100`, `<test_username>`, `testuser@example.com`).
    This is automatically enforced on all files via the `check-secrets` hook in `pre-commit`.
2.  **Format and Validate Files**:
    Run `pre-commit` to verify secrets/PII checks, Markdown formatting, JSON schemas, YAML variables, and code syntax:
    ```bash
    pre-commit run --all-files
    ```
3.  **Verify Test Suite**:
    Always execute the test suite to ensure that documentation or configuration updates didn't break parsing tests:
    ```bash
    pytest
    ```

### 4. Git Commit and Push
Once all tests and linters pass, proceed with committing and pushing your changes to GitHub:

```bash
git add .
git commit -m "docs: update roadmap and project documentation for <feature-name>"
git push
```
