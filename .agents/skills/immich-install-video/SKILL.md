---
name: immich-install-video
description: Automatically record a timed, high-definition video walkthrough of installing Immich on a Virtual Pi using Playwright.
---

# Immich Virtual Pi Video Walkthrough Generator

Use this skill whenever you need to record or regenerate the timed 720p HD video walkthrough showing end-to-end installation of **Immich (Self-Hosted Photos)** on a Virtual Pi / Proxmox node using NjordDeploy.

## Associated Script
- **Script path:** `scripts/generate_immich_install_video.py`
- **Output file:** `docs/videos/immich-virtual-pi-deployment.webm`

## Recorded Flow (60-Second Walkthrough)
1. **Scene 1: Network Auto-Discovery** — Starts network scan on local subnet.
2. **Scene 2: Node & Hardware Verification** — Detects `virtual-pi-5` (`192.168.1.185`, 8GB RAM, 64GB SSD), enters credentials, and verifies SSH access.
3. **Scene 3: Immich Selection** — Navigates to software stacks, selects **Immich (Self-Hosted Photos)**.
4. **Scene 4: Live Deployment Stream** — Real-time terminal output, Docker Engine validation, image pulling, persistent storage mounts, and health check status.
5. **Scene 5: Instant Web Access** — Celebratory success card with direct 1-click launch link (`http://192.168.1.185:2283`) and active container metrics.

## Workflow

### 1. Execute the Recording Script
Run the automated Playwright video recording script:
```bash
python3 scripts/generate_immich_install_video.py
```

### 2. Verify Video Output
Check that the `.webm` video is generated in `docs/videos/`:
```bash
ls -lh docs/videos/immich-virtual-pi-deployment.webm
```

### 3. Verify Code Quality
```bash
flake8 scripts/generate_immich_install_video.py
mypy scripts/generate_immich_install_video.py
```
