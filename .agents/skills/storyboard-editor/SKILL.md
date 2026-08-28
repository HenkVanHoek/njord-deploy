---
name: storyboard-editor
description: Review, direct, edit, and polish video walkthrough storyboards, scene timings, voice-over scripts, subtitles, visual hierarchy, and automated Playwright recording scripts.
---

# Video Storyboard & Walkthrough Editor (Director & Polish Skill)

Use this skill whenever you need to act as a **professional video director and editor** for NjordDeploy visual walkthroughs, demo loops, tutorials, and feature showcases.

---

## 🎯 Core Objectives
1. **Pacing & Timing Polish:** Balance scene durations, mouse transit speeds, typing cadences, and reading pauses to ensure comfortable viewing and natural narration fit.
2. **Theme & Visual Integrity:** Guarantee that the target theme (`futuristic-dark`, `light`, etc.) is fully initialized before the first frame renders, preventing light-theme flash or layout jump. Suppress intrusive popups, welcome modals, and overlays during recordings.
3. **Voice-Over & Subtitle Direction:** Craft concise, punchy voice-over scripts in English and Dutch. Embed on-screen floating narration banners and generate companion `.en.vtt` / `.en.srt` files.
4. **Storyboard Documentation:** Maintain structured, visual storyboard documents (e.g. `docs/IMMICH_VIDEO_STORYBOARD.md`) complete with Mermaid Gantt charts, high-definition scene screenshots, and interactive preview carousels.

---

## 📐 Production Standards & Timing Rules

| Element | Standard / Target | Rationale |
| :--- | :--- | :--- |
| **Viewport Canvas** | `1440x900` (Expanded) or `1280x780` | Ensures bottom action buttons, topbars, and sticky controls are visible without clipping. |
| **Theme Initialization** | `localStorage` + `color_scheme="dark"` + DOM init | Eliminates white flicker on page load (`accessibility.js` compatibility). |
| **Cursor Motion** | `0.75s` cubic-bezier transition + click press | Mimics natural human mouse guidance without jerky robotic jumps. |
| **Typing Cadence** | `120ms` to `150ms` per character | Allows viewers to comfortably read credentials or search inputs as they are typed. |
| **Scene Pauses** | 3.5s (Start) / 8–10s (Specs/Catalog) / 12–15s (Deploy) / 8–10s (Outro) | Provides 1.2x headroom over spoken voice-over length. |
| **Voice-Over Banner** | Floating glassmorphic pill at `bottom: 20px` | Gives instant clarity on muted players, social media, and documentation. |

---

## 🎬 Standard Walkthrough Workflow

### 1. Pre-Flight Script Audit
Before recording, inspect the Python generator script (e.g. `scripts/generate_immich_install_video.py`):
- Ensure `user-theme-preference` is preloaded in `context.add_init_script`.
- Ensure all startup popups (`#quickStartModal`, `#onboardingModal`) are suppressed.
- Check that all line lengths satisfy PEP 8 (<= 88 characters).

### 2. Voice-Over & Narration Synchronization
Map each scene to an explicit voice-over subtitle line:
```python
update_narration_subtitle(
    page,
    "Welcome to NjordDeploy. We start with an automated discovery "
    "scan to locate nodes.",
)
```

### 3. Capture High-Resolution Scene Frames
Save screenshots for every scene during the recording run into `docs/images/<walkthrough_name>/`:
```python
page.screenshot(path=str(screenshot_dir / "scene_1_discovery_start.png"))
```

### 4. Companion Subtitle Generation
Emit synchronized WebVTT (`.vtt`) and SubRip (`.srt`) files in `docs/videos/`.

### 5. Storyboard & Artifact Documentation
- Update or create `docs/<NAME>_STORYBOARD.md` with:
  - Mermaid Gantt timeline
  - Screenshots embedded per scene
  - Bilingual Voice-Over script tables (NL / EN)
  - Visual focus & pacing breakdown
- Create an interactive Artifact in the agent conversation containing a 6-slide carousel for instant review.

---

## 🛠️ Verification & Quality Assurance Commands

```bash
# 1. Run generator script
python3 scripts/generate_immich_install_video.py

# 2. Verify code quality (PEP 8 & Type checking)
flake8 scripts/generate_immich_install_video.py
mypy scripts/generate_immich_install_video.py

# 3. Verify video and subtitle files
ls -lh docs/videos/immich-virtual-pi-deployment*
ls -lh docs/images/immich_walkthrough/
```
