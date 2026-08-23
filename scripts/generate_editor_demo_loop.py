#!/usr/bin/env python3
"""
scripts/generate_editor_demo_loop.py

Automated Playwright script to generate a crisp, looping demo GIF and WebP
demonstrating the NjordDeploy Component Editor AI Generator workflow
powered by HostYourAI / Loes (EU Sovereign Cloud) using immich-app/immich.
"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# Add project src to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from playwright.sync_api import sync_playwright  # noqa: E402

from editor_app.app import create_app  # noqa: E402


def start_flask_editor_server(port: int = 5098):
    """Starts the Flask Editor app in a background thread."""
    from waitress import serve

    app = create_app({"TESTING": True})
    server_thread = threading.Thread(
        target=serve,
        kwargs={"app": app, "host": "127.0.0.1", "port": port, "threads": 4},
        daemon=True,
    )
    server_thread.start()
    time.sleep(1.0)
    return app


def add_banner(
    image_path: Path, step_text: str, subtitle_text: str, output_path: Path
) -> Path:
    """Draws a clean, professional banner overlay on the frame."""
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    banner_height = 68
    width, _ = img.size

    # Draw dark translucent banner at the top
    overlay = Image.new("RGBA", (width, banner_height), (15, 23, 42, 245))
    img.paste(overlay, (0, 0), overlay)

    # Draw separator line (accent purple)
    draw.line(
        [(0, banner_height - 1), (width, banner_height - 1)],
        fill=(168, 85, 247),
        width=2,
    )

    # Text rendering with fallback fonts
    font_title: Any
    font_sub: Any
    try:
        font_title = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20
        )
        font_sub = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14
        )
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((24, 12), step_text, fill=(255, 255, 255), font=font_title)
    draw.text((24, 38), subtitle_text, fill=(148, 163, 184), font=font_sub)

    # Add NjordDeploy badge on the right
    badge_text = "Loes AI Generator"
    draw.text((width - 230, 24), badge_text, fill=(168, 85, 247), font=font_title)

    img.save(output_path)
    return output_path


def generate_frames():
    """Drives Playwright through the 4 key states of the AI Generator."""
    images_dir = PROJECT_ROOT / "docs" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = PROJECT_ROOT / "docs" / "images" / "temp_editor_frames"
    temp_dir.mkdir(parents=True, exist_ok=True)

    port = 5098
    print(f"[*] Starting local Flask Editor instance on port {port}...")
    start_flask_editor_server(port)

    print("[*] Launching headless browser with Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 780})
        # Set Loes / HostYourAI as the selected provider
        context.add_init_script(
            """
            localStorage.setItem('njord_tour_completed', 'true');
            localStorage.setItem('njord_guide_hidden', 'true');
            localStorage.setItem('njord_ai_provider', 'hostyourai');
        """
        )
        page = context.new_page()

        # Intercept AI providers registry
        def handle_providers(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body="""{
                    "providers": {
                        "hostyourai": {
                            "name": "HostYourAI / Loes (EU)",
                            "requires_api_key": true,
                            "env_var": "HOSTYOURAI_API_KEY",
                            "models": ["loes-instruct", "loes-coder"]
                        },
                        "gemini": {
                            "name": "Google Gemini",
                            "requires_api_key": true,
                            "models": ["gemini-2.5-flash", "gemini-1.5-pro"]
                        },
                        "ollama": {
                            "name": "Ollama Local (RTX 3060)",
                            "requires_api_key": false,
                            "allow_custom_base_url": true,
                            "models": ["qwen2.5-coder:14b", "deepseek-coder-v2"]
                        }
                    }
                }""",
            )

        page.route("**/api/ai/providers", handle_providers)

        # Intercept AI status
        def handle_status(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body="""{
                    "status": "ready",
                    "provider": "hostyourai",
                    "details": "Ready (HostYourAI / Loes connected)"
                }""",
            )

        page.route("**/api/ai/status", handle_status)

        # Intercept AI generate
        def handle_generate(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body="""{
                    "status": "success",
                    "component_id": "immich-custom",
                    "name": "Immich (Self-Hosted Photos)",
                    "group": "media_servers",
                    "package_id": "immich-stack",
                    "description": "High performance self-hosted photo & "
                                   "video management with ML.",
                    "docker_compose": "services:\\n  immich-server:\\n"
                                     "    image: ghcr.io/immich-app/immich"
                                     "-server:release\\n"
                                     "    container_name: immich_server\\n"
                                     "    volumes:\\n      - "
                                     "${IMMICH_UPLOAD_LOCATION}:"
                                     "/usr/src/app/upload\\n"
                                     "    ports:\\n      - "
                                     "\\"${IMMICH_WEB_PORT}:2283\\"\\n"
                                     "    restart: always\\n",
                    "variables": {
                        "IMMICH_WEB_PORT": {
                            "default": "2283",
                            "description": "Immich Web UI and API Port",
                            "type": "port"
                        },
                        "IMMICH_UPLOAD_LOCATION": {
                            "default": "/srv/immich/upload",
                            "description": "Persistent media storage dir",
                            "type": "directory"
                        }
                    },
                    "conflicts": [],
                    "warnings": []
                }""",
            )

        page.route("**/api/ai/generate", handle_generate)

        # -------------------------------------------------------------
        # Frame 1: AI Generator Input Modal (immich-app/immich + Loes)
        # -------------------------------------------------------------
        print("[*] Capturing Frame 1: AI Generator Input (Loes)...")
        page.goto(f"http://127.0.0.1:{port}/")
        time.sleep(0.8)
        page.evaluate(
            """() => {
            document.querySelectorAll(
                '.introjs-overlay, .introjs-helperLayer, ' +
                '.introjs-tooltipReferenceLayer, .modal-backdrop'
            ).forEach(e => e.remove());
            const guide = document.getElementById('welcome-detailed-guide');
            if (guide) guide.classList.add('d-none');
            const minimal = document.getElementById('welcome-minimal');
            if (minimal) minimal.classList.remove('d-none');
        }"""
        )
        page.wait_for_selector("#create-new-ai-btn", timeout=10000)
        time.sleep(0.4)

        # Open AI Modal
        page.evaluate("document.getElementById('create-new-ai-btn').click();")
        page.wait_for_selector("#ai-component-modal.show, #ai-repo-url", timeout=5000)
        time.sleep(0.4)

        # Populate form fields
        page.fill("#ai-repo-url", "https://github.com/immich-app/immich")
        page.fill("#ai-component-id", "immich-custom")
        page.fill(
            "#ai-instructions",
            "Optimized for Raspberry Pi 5 with hardware transcoding "
            "& persistent media volumes.",
        )
        page.evaluate(
            """() => {
            const providerSelect = document.getElementById('ai-provider');
            if (providerSelect) providerSelect.value = 'hostyourai';
            const statusContainer = document.getElementById(
                'ai-status-container'
            );
            const statusBadge = document.getElementById('ai-status-badge');
            const statusDetails = document.getElementById('ai-status-details');
            if (statusContainer) statusContainer.classList.remove('d-none');
            if (statusBadge) {
                statusBadge.className = 'badge bg-success';
                statusBadge.innerHTML = (
                    '<i class="bi bi-shield-check me-1"></i> ' +
                    'Ready (HostYourAI / Loes)'
                );
            }
            if (statusDetails) {
                statusDetails.textContent = (
                    'EU Sovereign Private Cloud (Loes) connected'
                );
            }
        }"""
        )
        time.sleep(0.5)
        f1_raw = temp_dir / "frame1_editor_raw.png"
        page.screenshot(path=str(f1_raw))
        f1 = add_banner(
            f1_raw,
            "Step 1: Ingest Git Repository & Select AI Provider",
            "Enter public Git URL and select HostYourAI / Loes (EU Private Cloud).",
            images_dir / "editor_step_1_input.png",
        )

        # -------------------------------------------------------------
        # Frame 2: Multi-Step AI Analysis & Stepper (Loes)
        # -------------------------------------------------------------
        print("[*] Capturing Frame 2: Multi-Step AI Analysis (Loes)...")
        page.evaluate(
            """() => {
            const inputStep = document.getElementById('ai-input-step');
            const loadingStep = document.getElementById('ai-loading-step');
            if (inputStep) inputStep.classList.add('d-none');
            if (loadingStep) {
                loadingStep.classList.remove('d-none');
                loadingStep.innerHTML = `
                    <div class="text-center mb-4">
                        <div class="spinner-border text-primary mb-2" ` +
                        `role="status" style="width: 2.5rem; height: 2.5rem;">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <h5 class="fw-bold mb-1">` +
                        `Synthesizing Immich with Loes AI</h5>
                        <p class="text-muted small mb-0">` +
                        `HostYourAI / Loes is analyzing repo context and Compose...</p>
                    </div>
                    <div class="card border-0 bg-light shadow-sm mx-auto" ` +
                    `style="max-width: 540px; border-radius: 12px;">
                        <div class="card-body p-3">
                            <div class="d-flex flex-column gap-3">
                                <div class="d-flex align-items-start gap-3">
                                    <div class="badge rounded-circle p-2 ` +
                                    `bg-success d-flex align-items-center ` +
                                    `justify-content-center" ` +
                                    `style="width: 32px; height: 32px;">
                                        <i class="bi bi-check-lg text-white"></i>
                                    </div>
                                    <div class="flex-grow-1">
                                        <div class="fw-bold small text-dark">` +
                                        `1. Fetching Repository Docs</div>
                                        <div class="text-success extra-small">` +
                                        `Retrieved README and compose</div>
                                    </div>
                                </div>
                                <div class="d-flex align-items-start gap-3">
                                    <div class="badge rounded-circle p-2 ` +
                                    `bg-success d-flex align-items-center ` +
                                    `justify-content-center" ` +
                                    `style="width: 32px; height: 32px;">
                                        <i class="bi bi-check-lg text-white"></i>
                                    </div>
                                    <div class="flex-grow-1">
                                        <div class="fw-bold small text-dark">` +
                                        `2. Connecting to Loes AI</div>
                                        <div class="text-success extra-small">` +
                                        `EU Sovereign Cloud initialized</div>
                                    </div>
                                </div>
                                <div class="d-flex align-items-start gap-3">
                                    <div class="badge rounded-circle p-2 ` +
                                    `bg-primary d-flex align-items-center ` +
                                    `justify-content-center" ` +
                                    `style="width: 32px; height: 32px;">
                                        <i class="bi bi-arrow-repeat ` +
                                        `spin text-white"></i>
                                    </div>
                                    <div class="flex-grow-1">
                                        <div class="fw-bold small text-dark">` +
                                        `3. Drafting Architecture</div>
                                        <div class="text-muted extra-small">` +
                                        `Loes is generating template...</div>
                                    </div>
                                </div>
                                <div class="d-flex align-items-start ` +
                                `gap-3 opacity-50">
                                    <div class="badge rounded-circle p-2 ` +
                                    `bg-secondary d-flex align-items-center ` +
                                    `justify-content-center" ` +
                                    `style="width: 32px; height: 32px;">
                                        <i class="bi bi-circle"></i>
                                    </div>
                                    <div class="flex-grow-1">
                                        <div class="fw-bold small text-dark">` +
                                        `4. Validating Security</div>
                                        <div class="text-muted extra-small">` +
                                        `Verifying volumes & ports</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
        }"""
        )
        time.sleep(0.6)
        f2_raw = temp_dir / "frame2_editor_raw.png"
        page.screenshot(path=str(f2_raw))
        f2 = add_banner(
            f2_raw,
            "Step 2: Multi-Step AI Analysis & Stepper",
            "HostYourAI / Loes analyzes repo context, parameters, and volumes.",
            images_dir / "editor_step_2_analyzing.png",
        )

        # -------------------------------------------------------------
        # Frame 3: AI Preview & Verification
        # -------------------------------------------------------------
        print("[*] Capturing Frame 3: AI Preview & Verification...")
        page.evaluate(
            """() => {
            const loadingStep = document.getElementById('ai-loading-step');
            const previewStep = document.getElementById('ai-preview-step');
            if (loadingStep) loadingStep.classList.add('d-none');
            if (previewStep) {
                previewStep.classList.remove('d-none');
                previewStep.innerHTML = `
                    <div class="alert alert-success py-2 px-3 mb-3 d-flex ` +
                    `align-items-center gap-2 small">
                        <i class="bi bi-shield-check text-success fs-5 ` +
                        `flex-shrink-0"></i>
                        <div>
                            <strong>Loes AI Synthesis Verified:</strong> ` +
                            `Component <code>immich-custom</code> ` +
                            `successfully drafted via HostYourAI / Loes.
                        </div>
                    </div>
                    <div class="row g-3 text-start">
                        <div class="col-md-6">
                            <div class="card h-100 border-0 bg-light p-3">
                                <h6 class="fw-bold text-primary mb-2">` +
                                `<i class="bi bi-info-circle me-1"></i> ` +
                                `Generated Metadata</h6>
                                <div class="small mb-1"><strong>ID:</strong> ` +
                                `<code>immich-custom</code></div>
                                <div class="small mb-1"><strong>Name:</strong> ` +
                                `Immich (Self-Hosted Photos)</div>
                                <div class="small mb-1"><strong>Group:</strong> ` +
                                `Media Servers</div>
                                <div class="small mb-2"><strong>Image:</strong> ` +
                                `<code>ghcr.io/immich-app/immich-server:release` +
                                `</code></div>
                                <div class="small text-muted">High ` +
                                `performance photo & video management with ML.</div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card h-100 border-0 bg-light p-3">
                                <h6 class="fw-bold text-primary mb-2">` +
                                `<i class="bi bi-sliders me-1"></i> ` +
                                `Extracted Variables (2)</h6>
                                <div class="d-flex justify-content-between ` +
                                `border-bottom py-1 small">
                                    <code>IMMICH_WEB_PORT</code>
                                    <span class="badge bg-secondary">` +
                                    `Port :2283</span>
                                </div>
                                <div class="d-flex justify-content-between ` +
                                `border-bottom py-1 small">
                                    <code>IMMICH_UPLOAD_LOCATION</code>
                                    <span class="badge bg-secondary">` +
                                    `/srv/immich/upload</span>
                                </div>
                                <div class="mt-2 text-success small">
                                    <i class="bi bi-check-circle me-1"></i> ` +
                                    `0 Port/Volume Conflicts Detected
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-3 p-2 bg-dark rounded text-light ` +
                    `font-monospace small text-start" style="font-size: ` +
                    `0.8rem; max-height: 140px; overflow-y: hidden;">
                        <span class="text-muted"># docker-compose.template.yml` +
                        ` (Synthesized by HostYourAI / Loes)</span><br>
                        <span class="text-info">services:</span><br>
                        &nbsp;&nbsp;<span class="text-warning">` +
                        `immich-server:</span><br>
                        &nbsp;&nbsp;&nbsp;&nbsp;image: ` +
                        `ghcr.io/immich-app/immich-server:release<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;ports:<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- ` +
                        `<span class="text-success">"` +
                        '${IMMICH_WEB_PORT}:2283"' +
                        `</span><br>
                        &nbsp;&nbsp;&nbsp;&nbsp;volumes:<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- ` +
                        `<span class="text-success">"` +
                        '${IMMICH_UPLOAD_LOCATION}:/usr/src/app/upload"' +
                        `</span>
                    </div>
                    <div class="modal-footer px-0 pb-0 mt-3 d-flex ` +
                    `justify-content-between">
                        <button type="button" class="btn ` +
                        `btn-outline-secondary btn-sm"><i class="bi ` +
                        `bi-arrow-left"></i> Back</button>
                        <button type="button" class="btn btn-primary ` +
                        `btn-sm" id="ai-confirm-load-btn"><i class="bi ` +
                        `bi-box-arrow-in-down-right me-1"></i> Load into Editor` +
                        `</button>
                    </div>
                `;
            }
        }"""
        )
        time.sleep(0.6)
        f3_raw = temp_dir / "frame3_editor_raw.png"
        page.screenshot(path=str(f3_raw))
        f3 = add_banner(
            f3_raw,
            "Step 3: Preview & Security Verification",
            "Review generated Compose template, extracted variables, and port rules.",
            images_dir / "editor_step_3_preview.png",
        )

        # -------------------------------------------------------------
        # Frame 4: Loaded in Component Editor UI
        # -------------------------------------------------------------
        print("[*] Capturing Frame 4: Loaded in Component Editor...")
        page.evaluate(
            """() => {
            const modal = document.getElementById('ai-component-modal');
            if (modal) {
                document.querySelectorAll(
                    '.modal, .modal-backdrop'
                ).forEach(e => e.remove());
                document.body.classList.remove('modal-open');
            }
            const placeholder = document.getElementById('placeholder-text');
            const editorContent = document.getElementById('editor-content');
            if (placeholder) placeholder.classList.add('d-none');
            if (editorContent) {
                editorContent.classList.remove('d-none');
                editorContent.classList.add('d-flex');
            }
            const title = document.getElementById('editor-title');
            if (title) {
                title.innerHTML = (
                    '<i class="bi bi-cpu text-primary me-2"></i>' +
                    'Immich (Self-Hosted Photos) ' +
                    '<span class="badge bg-secondary fs-6 ms-2">' +
                    'immich-custom</span>'
                );
            }

            // Add to sidebar list
            const list = document.getElementById('component-list');
            if (list) {
                list.innerHTML = `
                    <a href="#" class="list-group-item ` +
                    `list-group-item-action active d-flex ` +
                    `justify-content-between align-items-center">
                        <div>
                            <strong>Immich (Self-Hosted Photos)</strong>
                            <div class="small text-light opacity-75">` +
                            `immich-custom</div>
                        </div>
                        <span class="badge bg-primary rounded-pill">Loes AI</span>
                    </a>
                    <a href="#" class="list-group-item ` +
                    `list-group-item-action d-flex ` +
                    `justify-content-between align-items-center">
                        <div>
                            <strong>AdGuard Home</strong>
                            <div class="small text-muted">adguard-home</div>
                        </div>
                    </a>
                    <a href="#" class="list-group-item ` +
                    `list-group-item-action d-flex ` +
                    `justify-content-between align-items-center">
                        <div>
                            <strong>Home Assistant</strong>
                            <div class="small text-muted">homeassistant</div>
                        </div>
                    </a>
                `;
            }

            // Fill editor metadata tab
            const metaTab = document.getElementById('metadata-pane');
            if (metaTab) {
                metaTab.innerHTML = `
                    <div class="row g-3 text-start p-3">
                        <div class="col-md-6">
                            <label class="form-label fw-bold small">` +
                            `Component Name</label>
                            <input class="form-control" ` +
                            `value="Immich (Self-Hosted Photos)">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold small">` +
                            `Component ID</label>
                            <input class="form-control font-monospace" ` +
                            `value="immich-custom" readonly>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold small">` +
                            `Category / Group</label>
                            <input class="form-control" ` +
                            `value="Media Servers">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold small">` +
                            `Docker Image</label>
                            <input class="form-control font-monospace" ` +
                            `value="ghcr.io/immich-app/immich-server:release">
                        </div>
                        <div class="col-12">
                            <label class="form-label fw-bold small">` +
                            `Description</label>
                            <textarea class="form-control" rows="2">` +
                            `High performance self-hosted photo & video ` +
                            `management with local ML and mobile backup.` +
                            `</textarea>
                        </div>
                    </div>
                `;
            }
        }"""
        )
        time.sleep(0.6)
        f4_raw = temp_dir / "frame4_editor_raw.png"
        page.screenshot(path=str(f4_raw))
        f4 = add_banner(
            f4_raw,
            "Step 4: Full Visual Editor Integration",
            "The generated component is loaded with Compose, Variables, & Configs.",
            images_dir / "editor_step_4_editor.png",
        )

        browser.close()

    # -------------------------------------------------------------
    # Stitch frames into animated GIF and WebP
    # -------------------------------------------------------------
    print("[*] Creating animated GIF and WebP loops for Editor...")
    frame_files = [f1, f2, f3, f4]
    pil_images = [Image.open(f).convert("RGB") for f in frame_files]

    duration_ms = 3000  # 3.0s per slide

    # Save Animated GIF using adaptive palette conversion
    gif_path = images_dir / "njorddeploy-editor-demo-loop.gif"
    p_images = [
        img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
        for img in pil_images
    ]
    first_p = p_images[0]
    rest_p = p_images[1:]
    first_p.save(
        gif_path,
        save_all=True,
        append_images=rest_p,
        duration=duration_ms,
        loop=0,
        optimize=True,
    )
    gif_size_kb = os.path.getsize(gif_path) / 1024
    print(f"[+] Saved Editor animated GIF: {gif_path} ({gif_size_kb:.1f} KB)")

    # Save Animated WebP
    webp_path = images_dir / "njorddeploy-editor-demo-loop.webp"
    first_img = pil_images[0]
    rest_imgs = pil_images[1:]
    first_img.save(
        webp_path,
        save_all=True,
        append_images=rest_imgs,
        duration=duration_ms,
        loop=0,
        lossless=False,
        quality=90,
        method=6,
    )
    webp_size_kb = os.path.getsize(webp_path) / 1024
    print(f"[+] Saved Editor animated WebP: {webp_path} ({webp_size_kb:.1f} KB)")

    # Clean up temp raw frames
    for temp_f in temp_dir.glob("*.png"):
        temp_f.unlink()
    temp_dir.rmdir()
    print("[+] Done generating Editor demo loop assets!")


if __name__ == "__main__":
    generate_frames()
