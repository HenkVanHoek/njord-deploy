---
name: configurator-demo-loop
description: Automatically regenerate the animated demo loop GIF and WebP and screenshot frames for the NjordDeploy Configurator application.
---

# Configurator Demo Loop Generator

Use this skill whenever the NjordDeploy Configurator UI, themes, or wizard flow have been updated and you need to regenerate the animated demo GIF, WebP, or documentation screenshots.

## Associated Script
- **Script path:** `scripts/generate_demo_loop.py`
- **Output directory:** `docs/images/`

## Generated Assets
* `docs/images/njorddeploy-demo-loop.gif` (Lightweight looping GIF for README & Guide)
* `docs/images/njorddeploy-demo-loop.webp` (Lightweight WebP loop)
* `docs/images/demo_step_1_discovery.png` (Frame 1: Network Auto-Discovery)
* `docs/images/demo_step_2_target.png` (Frame 2: Target Device Configuration)
* `docs/images/demo_step_3_selection.png` (Frame 3: Software Stack Selection)
* `docs/images/demo_step_4_deploying.png` (Frame 4: Automated Container Provisioning)
* `docs/images/demo_step_5_success.png` (Frame 5: Instant Web Access)

## Workflow

### 1. Execute the Script
Run the automated Playwright generator script:
```bash
python3 scripts/generate_demo_loop.py
```

### 2. Verify Output & Quality Checks
1. Ensure the script completes with exit code 0.
2. Run flake8 and mypy on the script:
```bash
flake8 scripts/generate_demo_loop.py
mypy scripts/generate_demo_loop.py
```

### 3. Verify Links in Documentation
Ensure the generated assets are referenced in:
* `README.md`
* `docs/GETTING_STARTED_FOR_BEGINNERS.md`
* `docs/USER_GUIDE.md`
