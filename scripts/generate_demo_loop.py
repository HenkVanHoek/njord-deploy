#!/usr/bin/env python3
"""
scripts/generate_demo_loop.py

Automated Playwright script to generate a crisp, looping demo GIF and WebP
demonstrating the NjordDeploy 4-step wizard workflow for the README and Guide.
"""

import os
import sys
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Add project src to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from playwright.sync_api import sync_playwright  # noqa: E402

from configurator_app.app import create_app  # noqa: E402


def start_flask_server(port: int = 5099):
    """Starts the Flask configurator in a background thread."""
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
    font_title: ImageFont.ImageFont | ImageFont.FreeTypeFont
    font_sub: ImageFont.ImageFont | ImageFont.FreeTypeFont
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
    badge_text = "NjordDeploy Quick Start"
    draw.text((width - 240, 24), badge_text, fill=(0, 212, 255), font=font_title)

    img.save(output_path)
    return output_path


def generate_frames():
    """Drives Playwright through the 5 key states and captures screenshots."""
    images_dir = PROJECT_ROOT / "docs" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = PROJECT_ROOT / "docs" / "images" / "temp_frames"
    temp_dir.mkdir(parents=True, exist_ok=True)

    port = 5099
    print(f"[*] Starting local Flask instance on port {port}...")
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

        # -------------------------------------------------------------
        # Frame 1: Network Discovery (Welcome Screen)
        # -------------------------------------------------------------
        print("[*] Capturing Frame 1: Network Discovery...")
        page.goto(f"http://127.0.0.1:{port}/")
        page.wait_for_selector("#begin-scan-btn", timeout=10000)
        time.sleep(1.0)
        page.evaluate(
            """() => {
            document.querySelectorAll('.modal, .modal-backdrop').forEach(
                e => e.remove()
            );
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
            document.body.style.paddingRight = '0';
        }"""
        )
        time.sleep(0.5)
        f1_raw = temp_dir / "frame1_raw.png"
        page.screenshot(path=str(f1_raw))
        f1 = add_banner(
            f1_raw,
            "Step 1: Network Auto-Discovery",
            "1-Click scanning locates Raspberry Pi & SBC nodes on local network.",
            images_dir / "demo_step_1_discovery.png",
        )

        # -------------------------------------------------------------
        # Frame 2: Device Discovered & Verified
        # -------------------------------------------------------------
        print("[*] Capturing Frame 2: Target Device...")
        page.evaluate(
            """() => {
            document.querySelectorAll('.modal, .modal-backdrop').forEach(
                e => e.remove()
            );
            document.getElementById('begin-scan-btn').click();
        }"""
        )
        page.wait_for_selector(".device-card", timeout=8000)
        time.sleep(0.4)
        page.evaluate(
            """() => {
            document.querySelectorAll('.modal, .modal-backdrop').forEach(
                e => e.remove()
            );
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
        f2_raw = temp_dir / "frame2_raw.png"
        page.screenshot(path=str(f2_raw))
        f2 = add_banner(
            f2_raw,
            "Step 2: Target Device Configuration",
            "Discovered Raspberry Pi 5 (192.168.1.150). SSH & Hardware verified.",
            images_dir / "demo_step_2_target.png",
        )

        # -------------------------------------------------------------
        # Frame 3: Select Software Stack
        # -------------------------------------------------------------
        print("[*] Capturing Frame 3: Software Stack Selection...")
        page.evaluate(
            """() => {
            document.getElementById('proceed-to-step3-btn').click();
        }"""
        )
        page.wait_for_selector("#v-pills-tab", timeout=8000)
        time.sleep(0.8)

        # Select a few popular components
        page.evaluate(
            """() => {
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {
                const text = card.textContent || '';
                if (text.includes('AdGuard') ||
                    text.includes('Home Assistant') ||
                    text.includes('Nextcloud') ||
                    text.includes('Uptime')) {
                    const cb = card.querySelector('input[type="checkbox"]');
                    if (cb) {
                        cb.checked = true;
                        card.classList.add(
                            'border-primary', 'bg-primary-subtle'
                        );
                    }
                }
            });
        }"""
        )
        time.sleep(0.5)
        f3_raw = temp_dir / "frame3_raw.png"
        page.screenshot(path=str(f3_raw))
        f3 = add_banner(
            f3_raw,
            "Step 3: Select Your Applications",
            "Choose from 100+ modular services or curated all-in-one stacks.",
            images_dir / "demo_step_3_selection.png",
        )

        # -------------------------------------------------------------
        # Frame 4: One-Click Deployment & Live Streaming Log
        # -------------------------------------------------------------
        print("[*] Capturing Frame 4: Deployment Streaming...")
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
            const footer = document.getElementById('wizard-footer');
            if (footer) {
                footer.innerHTML = (
                    '<p class="text-muted small mb-0">' +
                    'Provisioning Docker containers and persistent volumes...' +
                    '</p>'
                );
            }

            const body = document.getElementById('wizard-body');
            if (body) {
                body.innerHTML = `
                    <div class="text-start">
                        <div class="d-flex justify-content-between ` +
                        `align-items-center mb-3">
                            <h4 class="mb-0">` +
                            `<i class="fa-solid fa-rocket text-primary me-2">` +
                            `</i>Deploying Software Stacks...</h4>
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
                                `Live Deployment Stream (192.168.1.150)</span>
                                <span class="badge bg-success small">` +
                                `Target Engine: Docker CE</span>
                            </div>
                            <div class="card-body p-3 font-monospace small" ` +
                            `style="background-color: #0f172a; min-height: ` +
                            `240px; color: #38bdf8;">
                                <div><span class="text-success">[OK]</span> ` +
                                `Connected to pi@192.168.1.150 via SSH</div>
                                <div><span class="text-success">[OK]</span> ` +
                                `Verified Docker Engine 27.1.1 active</div>
                                <div><span class="text-success">[OK]</span> ` +
                                `Generated Compose for: adguard, ha, nextcloud</div>
                                <div><span class="text-success">[OK]</span> ` +
                                `Pulling container images from registry...</div>
                                <div><span class="text-success">[OK]</span> ` +
                                `Provisioned persistent volumes</div>
                                <div><span class="text-info">[RUN]</span> ` +
                                `Starting adguard-home (:3000) -> ` +
                                `<span class="text-success">Healthy</span></div>
                                <div><span class="text-info">[RUN]</span> ` +
                                `Starting homeassistant (:8123) -> ` +
                                `<span class="text-success">Healthy</span></div>
                                <div><span class="text-info">[RUN]</span> ` +
                                `Starting nextcloud (:8080) -> ` +
                                `<span class="text-success">Healthy</span></div>
                            </div>
                        </div>
                    </div>
                `;
            }
        }"""
        )
        time.sleep(0.6)
        f4_raw = temp_dir / "frame4_raw.png"
        page.screenshot(path=str(f4_raw))
        f4 = add_banner(
            f4_raw,
            "Step 4: Automated Container Provisioning",
            "Real-time log streaming installs Docker/Podman engines and stacks.",
            images_dir / "demo_step_4_deploying.png",
        )

        # -------------------------------------------------------------
        # Frame 5: Deployment Complete & Instant Web Access
        # -------------------------------------------------------------
        print("[*] Capturing Frame 5: Success & Access URLs...")
        page.evaluate(
            """() => {
            const header = document.getElementById('wizard-header');
            if (header) {
                header.innerHTML = (
                    '<strong>Step 4 of 4: Deployment Complete</strong>'
                );
            }
            const pbar = document.getElementById('wizard-progress-bar');
            if (pbar) pbar.style.width = '100%';
            const footer = document.getElementById('wizard-footer');
            if (footer) {
                footer.innerHTML = (
                    '<p class="text-success small mb-0">' +
                    '<i class="fa-solid fa-check me-1"></i> ' +
                    'All applications deployed successfully and healthy.</p>'
                );
            }

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
                                `shadow-sm">
                                    <div class="card-body p-3">
                                        <div class="d-flex ` +
                                        `align-items-center mb-2">
                                            <i class="fa-solid ` +
                                            `fa-shield-halved text-success ` +
                                            `fs-4 me-2"></i>
                                            <h6 class="fw-bold mb-0">` +
                                            `AdGuard Home</h6>
                                        </div>
                                        <p class="small text-muted mb-2">` +
                                        `Network-wide ad-blocking & DNS</p>
                                        <a href="http://192.168.1.150:3000" ` +
                                        `class="btn btn-sm ` +
                                        `btn-outline-success w-100 ` +
                                        `font-monospace">
                                            <i class="fa-solid ` +
                                            `fa-arrow-up-right-from-square ` +
                                            `me-1"></i> :3000
                                        </a>
                                    </div>
                                </div>
                            </div>
                            <div class="col">
                                <div class="card border-primary h-100 ` +
                                `shadow-sm">
                                    <div class="card-body p-3">
                                        <div class="d-flex ` +
                                        `align-items-center mb-2">
                                            <i class="fa-solid ` +
                                            `fa-house-signal text-primary ` +
                                            `fs-4 me-2"></i>
                                            <h6 class="fw-bold mb-0">` +
                                            `Home Assistant</h6>
                                        </div>
                                        <p class="small text-muted mb-2">` +
                                        `Open source home automation</p>
                                        <a href="http://192.168.1.150:8123" ` +
                                        `class="btn btn-sm ` +
                                        `btn-outline-primary w-100 ` +
                                        `font-monospace">
                                            <i class="fa-solid ` +
                                            `fa-arrow-up-right-from-square ` +
                                            `me-1"></i> :8123
                                        </a>
                                    </div>
                                </div>
                            </div>
                            <div class="col">
                                <div class="card border-info h-100 shadow-sm">
                                    <div class="card-body p-3">
                                        <div class="d-flex ` +
                                        `align-items-center mb-2">
                                            <i class="fa-solid fa-cloud ` +
                                            `text-info fs-4 me-2"></i>
                                            <h6 class="fw-bold mb-0">` +
                                            `Nextcloud</h6>
                                        </div>
                                        <p class="small text-muted mb-2">` +
                                        `Private cloud storage & sync</p>
                                        <a href="http://192.168.1.150:8080" ` +
                                        `class="btn btn-sm ` +
                                        `btn-outline-info w-100 ` +
                                        `font-monospace">
                                            <i class="fa-solid ` +
                                            `fa-arrow-up-right-from-square ` +
                                            `me-1"></i> :8080
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="d-flex justify-content-center gap-3">
                            <span class="badge bg-success-subtle text-success ` +
                            `border border-success p-2 fs-6">
                                <i class="fa-solid fa-heart-pulse me-1"></i> ` +
                                `3/3 Containers Active
                            </span>
                            <span class="badge bg-primary-subtle ` +
                            `text-primary border border-primary p-2 fs-6">
                                <i class="fa-solid fa-lock me-1"></i> ` +
                                `Docker / Podman Ready
                            </span>
                        </div>
                    </div>
                `;
            }
        }"""
        )
        time.sleep(0.6)
        f5_raw = temp_dir / "frame5_raw.png"
        page.screenshot(path=str(f5_raw))
        f5 = add_banner(
            f5_raw,
            "Step 5: Instant Web Access",
            "Direct 1-click links to your live web applications and dashboards.",
            images_dir / "demo_step_5_success.png",
        )

        browser.close()

    # -------------------------------------------------------------
    # Stitch frames into animated GIF and WebP
    # -------------------------------------------------------------
    print("[*] Creating animated GIF and WebP loops...")
    frame_files = [f1, f2, f3, f4, f5]
    pil_images = [Image.open(f).convert("RGB") for f in frame_files]

    duration_ms = 2800  # 2.8s per slide

    # Save Animated GIF using adaptive palette conversion
    gif_path = images_dir / "njorddeploy-demo-loop.gif"
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
    print(f"[+] Saved animated GIF: {gif_path} ({gif_size_kb:.1f} KB)")

    # Save Animated WebP
    webp_path = images_dir / "njorddeploy-demo-loop.webp"
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
    print(f"[+] Saved animated WebP: {webp_path} ({webp_size_kb:.1f} KB)")

    # Clean up temp raw frames
    for temp_f in temp_dir.glob("*.png"):
        temp_f.unlink()
    temp_dir.rmdir()
    print("[+] Done generating demo loop assets!")


if __name__ == "__main__":
    generate_frames()
