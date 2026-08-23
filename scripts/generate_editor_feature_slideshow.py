#!/usr/bin/env python3
"""
scripts/generate_editor_feature_slideshow.py

Automated Playwright script to capture a comprehensive visual slideshow of all
major menus, dialogs, and panels in the NjordDeploy Component Editor.
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


def start_flask_editor_server(port: int = 5097):
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
    badge_text = "Editor Feature Tour"
    draw.text((width - 240, 24), badge_text, fill=(168, 85, 247), font=font_title)

    img.save(output_path)
    return output_path


def generate_slideshow():
    """Captures the key menu options, modals, and tabs in the Editor."""
    images_dir = PROJECT_ROOT / "docs" / "images" / "editor_tour"
    images_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = images_dir / "temp_frames"
    temp_dir.mkdir(parents=True, exist_ok=True)

    port = 5097
    print(f"[*] Starting local Flask Editor instance on port {port}...")
    start_flask_editor_server(port)

    print("[*] Launching headless browser with Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 780})
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
                            "models": ["loes-instruct"]
                        }
                    }
                }""",
            )

        page.route("**/api/ai/providers", handle_providers)

        # Base clean page loader
        def load_clean_editor():
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
            time.sleep(0.3)

        # -------------------------------------------------------------
        # Slide 1: Main Component Workspace & Sidebar
        # -------------------------------------------------------------
        print("[*] Capturing Slide 1: Main Workspace & Sidebar...")
        load_clean_editor()
        # Select first component if available
        page.evaluate(
            """() => {
            const firstItem = document.querySelector(
                '#component-list .list-group-item'
            );
            if (firstItem) firstItem.click();
        }"""
        )
        time.sleep(0.6)
        s1_raw = temp_dir / "slide1_raw.png"
        page.screenshot(path=str(s1_raw))
        s1 = add_banner(
            s1_raw,
            "1. Component Workspace & Sidebar Navigation",
            "Browse 50+ services by category or package with instant search.",
            images_dir / "editor_slide_1_workspace.png",
        )

        # -------------------------------------------------------------
        # Slide 2: User Variables Tab & Macro System
        # -------------------------------------------------------------
        print("[*] Capturing Slide 2: Variables Tab...")
        page.evaluate(
            """() => {
            const varTab = document.querySelector(
                'button[data-bs-target="#variables-pane"]'
            );
            if (varTab) varTab.click();
        }"""
        )
        time.sleep(0.6)
        s2_raw = temp_dir / "slide2_raw.png"
        page.screenshot(path=str(s2_raw))
        s2 = add_banner(
            s2_raw,
            "2. User Variables & Dynamic Macros",
            "Define configurable ports, storage paths, and global .env bindings.",
            images_dir / "editor_slide_2_variables.png",
        )

        # -------------------------------------------------------------
        # Slide 3: Docker Compose Template Editor (Jinja2)
        # -------------------------------------------------------------
        print("[*] Capturing Slide 3: Compose Template Editor...")
        page.evaluate(
            """() => {
            const tplTab = document.querySelector(
                'button[data-bs-target="#template-pane"]'
            );
            if (tplTab) tplTab.click();
        }"""
        )
        time.sleep(0.6)
        s3_raw = temp_dir / "slide3_raw.png"
        page.screenshot(path=str(s3_raw))
        s3 = add_banner(
            s3_raw,
            "3. Jinja2 Compose Template Editor & Validator",
            "Syntax highlighting with Jinja badges, conditionals, and syntax checks.",
            images_dir / "editor_slide_3_compose.png",
        )

        # -------------------------------------------------------------
        # Slide 4: AI Component Generator (HostYourAI / Loes)
        # -------------------------------------------------------------
        print("[*] Capturing Slide 4: AI Component Generator...")
        load_clean_editor()
        page.evaluate(
            """() => {
            const btn = document.getElementById('create-new-ai-btn');
            if (btn) btn.click();
            const input = document.getElementById('ai-repo-url');
            if (input) input.value = 'https://github.com/immich-app/immich';
            const idInput = document.getElementById('ai-component-id');
            if (idInput) idInput.value = 'immich-custom';
        }"""
        )
        page.wait_for_selector("#ai-component-modal.show", timeout=5000)
        time.sleep(0.6)
        s4_raw = temp_dir / "slide4_raw.png"
        page.screenshot(path=str(s4_raw))
        s4 = add_banner(
            s4_raw,
            "4. AI Component Generator (HostYourAI / Loes)",
            "Bootstrap complete service stacks from any public Git repository.",
            images_dir / "editor_slide_4_ai_generator.png",
        )

        # -------------------------------------------------------------
        # Slide 5: Git Sync & Remote Diff Modal
        # -------------------------------------------------------------
        print("[*] Capturing Slide 5: Git Sync & Diff...")
        load_clean_editor()
        page.evaluate(
            """() => {
            const syncBtn = document.getElementById('git-sync-btn');
            if (syncBtn) syncBtn.click();
        }"""
        )
        time.sleep(0.8)
        s5_raw = temp_dir / "slide5_raw.png"
        page.screenshot(path=str(s5_raw))
        s5 = add_banner(
            s5_raw,
            "5. Remote Component Repository Sync & Diff",
            "Bi-directional git synchronization with conflict detection and pull/push.",
            images_dir / "editor_slide_5_git_sync.png",
        )

        # -------------------------------------------------------------
        # Slide 6: Statistics & Ecosystem Analytics
        # -------------------------------------------------------------
        print("[*] Capturing Slide 6: Ecosystem Stats...")
        load_clean_editor()
        page.evaluate(
            """() => {
            const statsBtn = document.getElementById('stats-btn');
            if (statsBtn) statsBtn.click();
        }"""
        )
        page.wait_for_selector("#statsModal.show", timeout=5000)
        time.sleep(0.6)
        s6_raw = temp_dir / "slide6_raw.png"
        page.screenshot(path=str(s6_raw))
        s6 = add_banner(
            s6_raw,
            "6. Ecosystem Analytics & Component Stats",
            "Live overview of total services, category distributions, and test status.",
            images_dir / "editor_slide_6_stats.png",
        )

        # -------------------------------------------------------------
        # Slide 7: Security Hash Generator (Basic Auth)
        # -------------------------------------------------------------
        print("[*] Capturing Slide 7: Hash Generator...")
        load_clean_editor()
        page.evaluate(
            """() => {
            const firstItem = document.querySelector(
                '#component-list .list-group-item'
            );
            if (firstItem) firstItem.click();
            const hashBtn = document.getElementById('generate-hash-btn');
            if (hashBtn) hashBtn.click();
        }"""
        )
        page.wait_for_selector("#hashGeneratorModal.show", timeout=5000)
        time.sleep(0.6)
        s7_raw = temp_dir / "slide7_raw.png"
        page.screenshot(path=str(s7_raw))
        s7 = add_banner(
            s7_raw,
            "7. Security Hash Generator (Argon2 / bcrypt)",
            "Password hashing for reverse proxy and web basic authentication.",
            images_dir / "editor_slide_7_hash.png",
        )

        # -------------------------------------------------------------
        # Slide 8: Manage Groups & Packages
        # -------------------------------------------------------------
        print("[*] Capturing Slide 8: Manage Packages...")
        load_clean_editor()
        page.evaluate(
            """() => {
            const pkgBtn = document.getElementById('manage-packages-btn');
            if (pkgBtn) pkgBtn.click();
        }"""
        )
        page.wait_for_selector("#manage-packages-modal.show", timeout=5000)
        time.sleep(0.6)
        s8_raw = temp_dir / "slide8_raw.png"
        page.screenshot(path=str(s8_raw))
        s8 = add_banner(
            s8_raw,
            "8. Curated Packages & Stack Management",
            "Group individual components into bundled all-in-one software suites.",
            images_dir / "editor_slide_8_packages.png",
        )

        browser.close()

    # -------------------------------------------------------------
    # Stitch frames into animated slideshow GIF and WebP
    # -------------------------------------------------------------
    print("[*] Stitching Editor feature slideshow loop...")
    slides = [s1, s2, s3, s4, s5, s6, s7, s8]
    pil_images = [Image.open(f).convert("RGB") for f in slides]

    duration_ms = 3500  # 3.5s per slide

    gif_path = images_dir / "njorddeploy-editor-features.gif"
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
    print(f"[+] Saved Editor Slideshow GIF: {gif_path} ({gif_size_kb:.1f} KB)")

    webp_path = images_dir / "njorddeploy-editor-features.webp"
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
    print(f"[+] Saved Editor Slideshow WebP: {webp_path} ({webp_size_kb:.1f} KB)")

    for temp_f in temp_dir.glob("*.png"):
        temp_f.unlink()
    temp_dir.rmdir()
    print("[+] Done generating Editor feature slideshow!")


if __name__ == "__main__":
    generate_slideshow()
