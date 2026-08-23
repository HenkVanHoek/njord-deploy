---
name: editor-feature-slideshow
description: Automatically regenerate the 8-slide feature tour animated GIF, WebP, and screenshot frames for the NjordDeploy Component Editor.
---

# Editor Feature Slideshow Generator

Use this skill whenever the NjordDeploy Component Editor UI, menus, modals, or tabs have been modified, and you need to regenerate the full visual feature slideshow and tour documentation.

## Associated Script
- **Script path:** `scripts/generate_editor_feature_slideshow.py`
- **Output directory:** `docs/images/editor_tour/`

## Generated Assets
* `docs/images/editor_tour/njorddeploy-editor-features.gif` (Animated continuous 8-slide tour)
* `docs/images/editor_tour/njorddeploy-editor-features.webp` (Lightweight WebP slideshow)
* `docs/images/editor_tour/editor_slide_1_workspace.png` (Slide 1: Component Workspace & Sidebar)
* `docs/images/editor_tour/editor_slide_2_variables.png` (Slide 2: User Variables & Dynamic Macros)
* `docs/images/editor_tour/editor_slide_3_compose.png` (Slide 3: Jinja2 Compose Template Editor)
* `docs/images/editor_tour/editor_slide_4_ai_generator.png` (Slide 4: AI Component Generator - Loes)
* `docs/images/editor_tour/editor_slide_5_git_sync.png` (Slide 5: Remote Component Repo Sync & Diff)
* `docs/images/editor_tour/editor_slide_6_stats.png` (Slide 6: Ecosystem Analytics & Stats)
* `docs/images/editor_tour/editor_slide_7_hash.png` (Slide 7: Security Hash Generator)
* `docs/images/editor_tour/editor_slide_8_packages.png` (Slide 8: Curated Packages & Stack Management)

## Workflow

### 1. Execute the Script
Run the automated Playwright slideshow generator:
```bash
python3 scripts/generate_editor_feature_slideshow.py
```

### 2. Verify Output & Quality Checks
1. Ensure the script completes with exit code 0.
2. Run flake8 and mypy on the script:
```bash
flake8 scripts/generate_editor_feature_slideshow.py
mypy scripts/generate_editor_feature_slideshow.py
```

### 3. Verify Links in Documentation
Ensure the generated assets are referenced in:
* `docs/EDITOR_FEATURE_GUIDE.md`
* `docs/DEVELOPER_AI_AND_SYNC_GUIDE.md`
* `README.md`
