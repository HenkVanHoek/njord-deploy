---
name: editor-demo-loop
description: Automatically regenerate the animated demo loop GIF, WebP, and screenshot frames for the NjordDeploy Component Editor AI Generator (featuring HostYourAI / Loes and Immich).
---

# Editor AI Generator Demo Loop

Use this skill whenever the NjordDeploy Component Editor, AI Generator modal, stepper, or styling have been updated and you need to regenerate the animated demo loop GIF, WebP, or documentation screenshots.

## Associated Script
- **Script path:** `scripts/generate_editor_demo_loop.py`
- **Output directory:** `docs/images/`

## Generated Assets
* `docs/images/njorddeploy-editor-demo-loop.gif` (Looping demo GIF for Developer Guide)
* `docs/images/njorddeploy-editor-demo-loop.webp` (Lightweight WebP loop)
* `docs/images/editor_step_1_input.png` (Frame 1: Git URL Ingestion & Loes AI Provider Selection)
* `docs/images/editor_step_2_analyzing.png` (Frame 2: Live Multi-Step AI Stepper & Context Enrichment)
* `docs/images/editor_step_3_preview.png` (Frame 3: Synthesized Compose & Variable Verification)
* `docs/images/editor_step_4_editor.png` (Frame 4: Full Visual Editor Integration)

## Workflow

### 1. Execute the Script
Run the automated Playwright generator script:
```bash
python3 scripts/generate_editor_demo_loop.py
```

### 2. Verify Output & Quality Checks
1. Ensure the script completes with exit code 0.
2. Run flake8 and mypy on the script:
```bash
flake8 scripts/generate_editor_demo_loop.py
mypy scripts/generate_editor_demo_loop.py
```

### 3. Verify Links in Documentation
Ensure the generated assets are referenced in:
* `docs/DEVELOPER_AI_AND_SYNC_GUIDE.md`
* `README.md`
