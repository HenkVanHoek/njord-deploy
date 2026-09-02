#!/usr/bin/env python3
"""
scripts/generate_configurator_feature_slideshow.py

Automated Playwright script to capture a comprehensive visual slideshow of all
major menus, dialogs, and panels in the NjordDeploy Configurator.
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

from configurator_app.app import create_app  # noqa: E402


def start_flask_server(port: int = 5096):
    """Starts the Flask Configurator app in a background thread."""
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

    # Draw separator line (accent cyan)
    draw.line(
        [(0, banner_height - 1), (width, banner_height - 1)],
        fill=(0, 212, 255),
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
    badge_text = "Configurator Feature Tour"
    draw.text((width - 290, 24), badge_text, fill=(0, 212, 255), font=font_title)

    img.save(output_path)
    return output_path


def generate_slideshow():
    """Captures the key menu options, modals, and wizard views in Configurator."""
    images_dir = PROJECT_ROOT / "docs" / "images" / "configurator_tour"
    images_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = images_dir / "temp_frames"
    temp_dir.mkdir(parents=True, exist_ok=True)

    port = 5096
    print(f"[*] Starting local Flask Configurator instance on port {port}...")
    start_flask_server(port)

    print("[*] Launching headless browser with Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 780})
        page = context.new_page()

        # Intercept network scan
        def handle_scan(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body="""{
                    "hosts": [
                        {
                            "ip": "192.168.1.150",
                            "hostname": "raspberrypi5",
                            "vendor": "Raspberry Pi Foundation",
                            "mac": "D8:3A:DD:4A:8B:1C"
                        }
                    ],
                    "unresolved_hosts": []
                }""",
            )

        page.route("**/scan-pis", handle_scan)

        # Intercept get-device-details
        def handle_device_details(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body="""{
                    "details": {
                        "model": "Raspberry Pi 5 Model B (8GB RAM)",
                        "serial": "10000000a1b2c3d4",
                        "ram": "8.0 GB",
                        "disks": [
                            {
                                "mounted_on": "/",
                                "size": "128 GB",
                                "pcent": "12%"
                            }
                        ]
                    }
                }""",
            )

        page.route("**/get-device-details", handle_device_details)

        # Base clean page loader
        def load_clean_configurator():
            page.goto(f"http://127.0.0.1:{port}/")
            time.sleep(0.8)
            page.evaluate(
                """() => {
                document.querySelectorAll(
                    '.modal-backdrop, .introjs-overlay, .introjs-helperLayer'
                ).forEach(e => e.remove());
                document.querySelectorAll('.modal.show').forEach(e => {
                    e.classList.remove('show');
                    e.style.display = 'none';
                });
                document.body.classList.remove('modal-open');
                document.body.style.overflow = 'auto';
            }"""
            )
            time.sleep(0.3)

        # -------------------------------------------------------------
        # Slide 1: Welcome & Multi-Mode Network Discovery
        # -------------------------------------------------------------
        print("[*] Capturing Slide 1: Welcome & Network Discovery...")
        load_clean_configurator()
        page.wait_for_selector("#begin-scan-btn", timeout=10000)
        time.sleep(0.5)
        s1_raw = temp_dir / "slide1_raw.png"
        page.screenshot(path=str(s1_raw))
        s1 = add_banner(
            s1_raw,
            "1. Multi-Mode Network Discovery Wizard",
            "Auto-scan local subnet, connect via direct IP, Tailscale, or Proxmox.",
            images_dir / "config_slide_1_discovery.png",
        )

        # -------------------------------------------------------------
        # Slide 2: Dual Container Engine Switcher (Docker / Podman)
        # -------------------------------------------------------------
        print("[*] Capturing Slide 2: Dual Engine Selector...")
        load_clean_configurator()
        page.evaluate(
            """() => {
            const dropdown = document.getElementById('engineDropdown');
            if (dropdown) dropdown.click();
        }"""
        )
        time.sleep(0.5)
        s2_raw = temp_dir / "slide2_raw.png"
        page.screenshot(path=str(s2_raw))
        s2 = add_banner(
            s2_raw,
            "2. Dual Container Engine Support (Docker & Podman)",
            "Seamlessly toggle between Docker CE and Rootless Podman runtime engines.",
            images_dir / "config_slide_2_engine.png",
        )

        # -------------------------------------------------------------
        # Slide 3: Target Hardware & SSH Configuration
        # -------------------------------------------------------------
        print("[*] Capturing Slide 3: Target Hardware Configuration...")
        load_clean_configurator()
        page.evaluate(
            """() => {
            document.getElementById('begin-scan-btn').click();
        }"""
        )
        page.wait_for_selector(".device-card", timeout=8000)
        time.sleep(0.4)
        page.evaluate(
            """() => {
            const card = document.querySelector('.device-card');
            if (card) {
                const sw = card.querySelector('.form-check-input');
                if (sw) sw.checked = true;
                const user = card.querySelector('.device-username');
                if (user) user.value = 'pi';
                const pw = card.querySelector('.device-password');
                if (pw) pw.value = '••••••••';
            }
            const getBtn = document.getElementById('get-details-btn');
            if (getBtn) getBtn.click();
        }"""
        )
        page.wait_for_selector("#proceed-to-step3-btn", timeout=8000)
        time.sleep(0.6)
        s3_raw = temp_dir / "slide3_raw.png"
        page.screenshot(path=str(s3_raw))
        s3 = add_banner(
            s3_raw,
            "3. Discovered Node & SSH Hardware Verification",
            "Inspect detected Raspberry Pi / Debian nodes, RAM, and disk capacity.",
            images_dir / "config_slide_3_target.png",
        )

        # -------------------------------------------------------------
        # Slide 4: Software Stack Selection (100+ Modular Apps)
        # -------------------------------------------------------------
        print("[*] Capturing Slide 4: Software Stack Selection...")
        page.evaluate(
            """() => {
            const step3Btn = document.getElementById('proceed-to-step3-btn');
            if (step3Btn) step3Btn.click();
        }"""
        )
        page.wait_for_selector("#v-pills-tab", timeout=8000)
        time.sleep(0.6)
        s4_raw = temp_dir / "slide4_raw.png"
        page.screenshot(path=str(s4_raw))
        s4 = add_banner(
            s4_raw,
            "4. Software Selection & Curated Bundles",
            "Select from 100+ modular services, media suites, and all-in-one packages.",
            images_dir / "config_slide_4_selection.png",
        )

        # -------------------------------------------------------------
        # Slide 5: Live Streaming Deployment Terminal
        # -------------------------------------------------------------
        print("[*] Capturing Slide 5: Live Streaming Deployment...")
        page.evaluate(
            """() => {
            const header = document.getElementById('wizard-header');
            if (header) {
                header.innerHTML = (
                    '<strong>Step 4 of 4: Deploying Services</strong>'
                );
            }
            const pbar = document.getElementById('wizard-progress-bar');
            if (pbar) pbar.style.width = '85%';
            const body = document.getElementById('wizard-body');
            if (body) {
                body.innerHTML = `
                    <div class="text-start">
                        <div class="d-flex justify-content-between ` +
                        `align-items-center mb-3">
                            <h4 class="mb-0"><i class="fa-solid fa-rocket ` +
                            `text-primary me-2"></i>Deploying Services</h4>
                            <span class="badge bg-primary fs-6">` +
                            `<i class="fa-solid fa-spinner fa-spin me-1"></i> ` +
                            `Installing 3 Services</span>
                        </div>
                        <div class="progress mb-4" style="height: 10px;">
                            <div class="progress-bar progress-bar-striped ` +
                            `progress-bar-animated bg-success" ` +
                            `style="width: 85%;"></div>
                        </div>
                        <div class="card bg-dark text-light border-0 ` +
                        `shadow-sm mb-3">
                            <div class="card-header bg-black py-2 d-flex ` +
                            `justify-content-between">
                                <span class="small text-muted ` +
                                `font-monospace"><i class="fa-solid ` +
                                `fa-terminal me-2 text-success"></i>` +
                                `Live Terminal Stream (192.168.1.150)</span>
                                <span class="badge bg-success small">` +
                                `Docker Engine CE</span>
                            </div>
                            <div class="card-body p-3 font-monospace small" ` +
                            `style="background-color: #0f172a; min-height: ` +
                            `220px; color: #38bdf8;">
                                <div><span class="text-success">[OK]</span> ` +
                                `Connected to pi@192.168.1.150 via SSH</div>
                                <div><span class="text-success">[OK]</span> ` +
                                `Docker Engine active & verified</div>
                                <div><span class="text-success">[OK]</span> ` +
                                `Pulling images & provisioning volumes...</div>
                                <div><span class="text-info">[RUN]</span> ` +
                                `adguard-home (:3000) -> ` +
                                `<span class="text-success">Healthy</span></div>
                                <div><span class="text-info">[RUN]</span> ` +
                                `homeassistant (:8123) -> ` +
                                `<span class="text-success">Healthy</span></div>
                            </div>
                        </div>
                    </div>
                `;
            }
        }"""
        )
        time.sleep(0.6)
        s5_raw = temp_dir / "slide5_raw.png"
        page.screenshot(path=str(s5_raw))
        s5 = add_banner(
            s5_raw,
            "5. Real-Time Deployment Log Streaming",
            "Watch real-time container provisioning, volume setup, and health checks.",
            images_dir / "config_slide_5_deploying.png",
        )

        # -------------------------------------------------------------
        # Slide 6: Instant Web Access & Live Dashboards
        # -------------------------------------------------------------
        print("[*] Capturing Slide 6: Instant Web Access...")
        page.evaluate(
            """() => {
            const body = document.getElementById('wizard-body');
            if (body) {
                body.innerHTML = `
                    <div class="text-center py-2">
                        <div class="display-5 text-success mb-2">` +
                        `<i class="fa-solid fa-circle-check"></i></div>
                        <h3 class="fw-bold mb-2">Deployment Complete!</h3>
                        <p class="text-muted mb-4">` +
                        `Your self-hosted services are live and ready.</p>
                        <div class="row row-cols-1 row-cols-md-3 g-3 mb-4 ` +
                        `text-start justify-content-center">
                            <div class="col">
                                <div class="card border-success h-100 ` +
                                `shadow-sm p-3">
                                    <h6 class="fw-bold text-success mb-2">` +
                                    `<i class="fa-solid fa-shield-halved me-1">` +
                                    `</i> AdGuard Home</h6>
                                    <p class="small text-muted mb-2">` +
                                    `Network-wide ad-blocking</p>
                                    <a class="btn btn-sm btn-outline-success ` +
                                    `font-monospace w-100">:3000</a>
                                </div>
                            </div>
                            <div class="col">
                                <div class="card border-primary h-100 ` +
                                `shadow-sm p-3">
                                    <h6 class="fw-bold text-primary mb-2">` +
                                    `<i class="fa-solid fa-house-signal me-1">` +
                                    `</i> Home Assistant</h6>
                                    <p class="small text-muted mb-2">` +
                                    `Open home automation</p>
                                    <a class="btn btn-sm btn-outline-primary ` +
                                    `font-monospace w-100">:8123</a>
                                </div>
                            </div>
                            <div class="col">
                                <div class="card border-info h-100 ` +
                                `shadow-sm p-3">
                                    <h6 class="fw-bold text-info mb-2">` +
                                    `<i class="fa-solid fa-cloud me-1"></i> ` +
                                    `Nextcloud</h6>
                                    <p class="small text-muted mb-2">` +
                                    `Private cloud storage</p>
                                    <a class="btn btn-sm btn-outline-info ` +
                                    `font-monospace w-100">:8080</a>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
        }"""
        )
        time.sleep(0.6)
        s6_raw = temp_dir / "slide6_raw.png"
        page.screenshot(path=str(s6_raw))
        s6 = add_banner(
            s6_raw,
            "6. Instant Service Web Links & Dashboards",
            "1-click launch links to all newly deployed applications and dashboards.",
            images_dir / "config_slide_6_success.png",
        )

        # -------------------------------------------------------------
        # Slide 7: Backup & Disaster Recovery Center
        # -------------------------------------------------------------
        print("[*] Capturing Slide 7: Backup & Disaster Recovery...")
        load_clean_configurator()
        page.evaluate(
            """() => {
            const modalEl = document.getElementById('backupRestoreModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            }
        }"""
        )
        page.wait_for_selector("#backupRestoreModal.show", timeout=5000)
        time.sleep(0.6)
        s7_raw = temp_dir / "slide7_raw.png"
        page.screenshot(path=str(s7_raw))
        s7 = add_banner(
            s7_raw,
            "7. Volume Backup & Disaster Recovery Center",
            "Snapshot persistent volumes, verify SHA-256 hashes, and 1-click restore.",
            images_dir / "config_slide_7_backup.png",
        )

        # -------------------------------------------------------------
        # Slide 8: Interactive Swagger REST API (OpenAPI 3.0)
        # -------------------------------------------------------------
        print("[*] Capturing Slide 8: Swagger REST API...")
        page.goto(f"http://127.0.0.1:{port}/api/docs")
        page.wait_for_selector(".swagger-ui", timeout=8000)
        time.sleep(0.8)
        s8_raw = temp_dir / "slide8_raw.png"
        page.screenshot(path=str(s8_raw))
        s8 = add_banner(
            s8_raw,
            "8. Interactive Swagger REST API & OpenAPI 3.0",
            "Full programmatic REST API for Homelab CI/CD, Proxmox, and AI agents.",
            images_dir / "config_slide_8_swagger.png",
        )

        browser.close()

    # -------------------------------------------------------------
    # Stitch frames into animated slideshow GIF and WebP
    # -------------------------------------------------------------
    print("[*] Stitching Configurator feature slideshow loop...")
    slides = [s1, s2, s3, s4, s5, s6, s7, s8]
    pil_images = [Image.open(f).convert("RGB") for f in slides]

    duration_ms = 3500  # 3.5s per slide

    gif_path = images_dir / "njorddeploy-configurator-features.gif"
    p_images = [
        img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
        for img in pil_images
    ]
    p_first = p_images[0]
    p_rest = p_images[1:]
    p_first.save(
        gif_path,
        save_all=True,
        append_images=p_rest,
        duration=duration_ms,
        loop=0,
        optimize=True,
    )
    gif_size_kb = os.path.getsize(gif_path) / 1024
    print(f"[+] Saved Configurator Slideshow GIF: {gif_path} ({gif_size_kb:.1f} KB)")

    webp_path = images_dir / "njorddeploy-configurator-features.webp"
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
    print(f"[+] Saved Configurator Slideshow WebP: {webp_path} ({webp_size_kb:.1f} KB)")

    for temp_f in temp_dir.glob("*.png"):
        temp_f.unlink()
    temp_dir.rmdir()
    print("[+] Done generating Configurator feature slideshow!")


if __name__ == "__main__":
    generate_slideshow()
