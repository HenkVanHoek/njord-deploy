---
name: configurator-feature-slideshow
description: Automatically regenerate the 8-slide feature tour animated GIF, WebP, and screenshot frames for the NjordDeploy Configurator application.
---

# Configurator Feature Slideshow Generator

Use this skill whenever the NjordDeploy Configurator application, navbar menus, engine selectors, modals, or views have been modified, and you need to regenerate the full visual feature slideshow and tour documentation.

## Associated Script
- **Script path:** `scripts/generate_configurator_feature_slideshow.py`
- **Output directory:** `docs/images/configurator_tour/`

## Generated Assets
* `docs/images/configurator_tour/njorddeploy-configurator-features.gif` (Animated continuous 8-slide tour)
* `docs/images/configurator_tour/njorddeploy-configurator-features.webp` (Lightweight WebP slideshow)
* `docs/images/configurator_tour/config_slide_1_discovery.png` (Slide 1: Multi-Mode Network Discovery)
* `docs/images/configurator_tour/config_slide_2_engine.png` (Slide 2: Dual Container Engine Support)
* `docs/images/configurator_tour/config_slide_3_target.png` (Slide 3: Discovered Node & SSH Verification)
* `docs/images/configurator_tour/config_slide_4_selection.png` (Slide 4: Software Selection & Curated Bundles)
* `docs/images/configurator_tour/config_slide_5_deploying.png` (Slide 5: Real-Time Deployment Log Stream)
* `docs/images/configurator_tour/config_slide_6_success.png` (Slide 6: Instant Service Web Links & Dashboards)
* `docs/images/configurator_tour/config_slide_7_backup.png` (Slide 7: Volume Backup & Disaster Recovery)
* `docs/images/configurator_tour/config_slide_8_swagger.png` (Slide 8: Interactive Swagger REST API - OpenAPI 3.0)

## Workflow

### 1. Execute the Script
Run the automated Playwright slideshow generator:
```bash
python3 scripts/generate_configurator_feature_slideshow.py
```

### 2. Verify Output & Quality Checks
1. Ensure the script completes with exit code 0.
2. Run flake8 and mypy on the script:
```bash
flake8 scripts/generate_configurator_feature_slideshow.py
mypy scripts/generate_configurator_feature_slideshow.py
```

### 3. Verify Links in Documentation
Ensure the generated assets are referenced in:
* `docs/CONFIGURATOR_FEATURE_GUIDE.md`
* `docs/USER_GUIDE.md`
* `README.md`
