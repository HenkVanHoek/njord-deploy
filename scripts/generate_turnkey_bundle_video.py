"""High-definition video walkthrough generator for NjordDeploy Turnkey Bundles.

Records a professional, frame-accurate video demonstrating the 1-Click
Turnkey Bundle Presets (The Modern Sovereign Workplace) on a target host
with neural voice-over audio and subtitles.

Features:
- Viewport: 1440x900 (16:10 Full HD canvas)
- Theme: Futuristic Dark initialized before DOM load (zero light flicker)
- Audio: Neural voice-over (en-US-ChristopherNeural) in mathematical lockstep
- Subtitles: Synchronized WebVTT (.vtt) and SubRip (.srt) files
- Visual cursor: Smooth bezier travel, click ripples, and button hover pulses
- Pacing: Audio-driven scene pacing with clean breathing room between transitions
"""

import subprocess  # nosec B404
import sys
import tempfile
import threading
import time
from pathlib import Path

import edge_tts
import imageio_ffmpeg  # type: ignore[import-untyped]
from playwright.sync_api import sync_playwright

# Project Root Setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from configurator_app.app import create_app  # noqa: E402

NARRATION_SCRIPTS: list[tuple[str, str]] = [
    (
        "scene1.mp3",
        "Welcome to NjordDeploy. Let's start an automated discovery "
        "scan to locate nodes on our network.",
    ),
    (
        "scene2.mp3",
        "Target node njord-cloud-01 discovered at 192.168.1.185. Entering SSH "
        "credentials for hardware verification.",
    ),
    (
        "scene3.mp3",
        "Target verified: 8 gigabytes of RAM and 64 gigabytes of storage. "
        "Zero target dependencies required.",
    ),
    (
        "scene4.mp3",
        "In the Turnkey Stacks catalog, selecting The Modern Sovereign "
        "Workplace. With one click, Nextcloud, MariaDB, Redis cache, "
        "push notifications, and Vaultwarden are instantly coordinated.",
    ),
    (
        "scene5.mp3",
        "Deployment complete! All enterprise microservices are "
        "provisioned, isolated, and verified healthy.",
    ),
    (
        "scene6.mp3",
        "Launch Nextcloud and Vaultwarden web dashboards instantly "
        "from your private sovereign cloud harbor.",
    ),
]


def start_flask_server(port: int = 5096) -> None:
    """Starts the Flask Configurator App on a designated local port."""
    app = create_app()

    def run():
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

    server_thread = threading.Thread(target=run, daemon=True)
    server_thread.start()
    time.sleep(1.2)


def wait_seconds(page, seconds: float) -> None:
    """Blocks execution while keeping Playwright event loop active."""
    start = time.time()
    while time.time() - start < seconds:
        page.evaluate("() => new Promise(r => requestAnimationFrame(r))")
        time.sleep(0.04)


def init_custom_cursor(page) -> None:
    """Injects a sleek glowing neon cursor overlay with smooth transitions."""
    page.evaluate(
        """() => {
        let cursor = document.getElementById('njord-animated-cursor');
        if (!cursor) {
            cursor = document.createElement('div');
            cursor.id = 'njord-animated-cursor';
            cursor.style.cssText = (
                'position: fixed; width: 28px; height: 28px; ' +
                'pointer-events: none; z-index: 999999; ' +
                'transition: left 0.75s cubic-bezier(0.22, 1, 0.36, 1), ' +
                'top 0.75s cubic-bezier(0.22, 1, 0.36, 1), ' +
                'transform 0.25s ease; filter: drop-shadow(0 0 10px #00f2fe);'
            );
            cursor.innerHTML = `
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                     xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 3L18 12L11 13L8 20L4 3Z"
                          fill="#00f2fe" stroke="#0f172a" stroke-width="1.5"
                          stroke-linejoin="round"/>
                </svg>
            `;
            document.body.appendChild(cursor);
            cursor.style.left = '200px';
            cursor.style.top = '160px';
        }
    }"""
    )


def update_narration_subtitle(page, text: str) -> None:
    """Renders a sleek floating narration banner for voice-over."""
    page.evaluate(
        """(subtitleText) => {
        let bar = document.getElementById('njord-narration-banner');
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'njord-narration-banner';
            bar.style.cssText = (
                'position: fixed; bottom: 20px; left: 50%; ' +
                'transform: translateX(-50%);' +
                'background: rgba(15, 23, 42, 0.94);' +
                'border: 1px solid rgba(0, 242, 254, 0.45);' +
                'color: #f8fafc; padding: 9px 24px; border-radius: 9999px;' +
                'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", ' +
                'Roboto, sans-serif; font-size: 14.5px; font-weight: 500; ' +
                'letter-spacing: 0.2px;' +
                'box-shadow: 0 8px 32px rgba(0, 0, 0, 0.7), ' +
                '0 0 16px rgba(0, 242, 254, 0.25);' +
                'backdrop-filter: blur(12px); ' +
                '-webkit-backdrop-filter: blur(12px);' +
                'z-index: 9999999; display: flex; align-items: center; ' +
                'gap: 10px; transition: opacity 0.3s ease, ' +
                'transform 0.3s ease; max-width: 88%;'
            );
            document.body.appendChild(bar);
        }
        bar.innerHTML = `
            <span style="display:inline-flex;align-items:center;` +
            `justify-content:center;width:24px;height:24px;border-radius:50%;` +
            `background:rgba(0,242,254,0.15);color:#00f2fe;font-size:12px;` +
            `flex-shrink:0;">🎙️</span>
            <span style="color:#38bdf8;font-weight:600;margin-right:4px;">` +
            `Voice-Over:</span>
            <span style="color:#ffffff;">${subtitleText}</span>
        `;
        bar.style.opacity = '1';
    }""",
        text,
    )


def move_cursor_and_click(page, selector: str, wait_after_sec: float = 1.0):
    """Scrolls element into center view, moves cursor to it, and clicks."""
    page.evaluate(
        """(sel) => new Promise(resolve => {
        const el = document.querySelector(sel);
        const cursor = document.getElementById('njord-animated-cursor');
        if (!el) { resolve(); return; }

        el.scrollIntoView({ behavior: 'smooth', block: 'center' });

        setTimeout(() => {
            const rect = el.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top + rect.height / 2;

            if (cursor) {
                cursor.style.left = `${x}px`;
                cursor.style.top = `${y}px`;
            }

            setTimeout(() => {
                if (cursor) {
                    cursor.style.transform = 'scale(0.82)';
                }
                setTimeout(() => {
                    if (cursor) cursor.style.transform = 'scale(1)';
                    el.click();
                    resolve();
                }, 250);
            }, 800);
        }, 400);
    })""",
        selector,
    )
    wait_seconds(page, wait_after_sec)


def move_cursor_to_input_and_type(page, selector: str, text: str, delay_ms: int = 150):
    """Moves the large cursor to an input box and types with natural cadence."""
    page.evaluate(
        """(sel) => new Promise(resolve => {
        const el = document.querySelector(sel);
        const cursor = document.getElementById('njord-animated-cursor');
        if (!el) { resolve(); return; }

        el.scrollIntoView({ behavior: 'smooth', block: 'center' });

        setTimeout(() => {
            const rect = el.getBoundingClientRect();
            const x = rect.left + 30;
            const y = rect.top + rect.height / 2;

            if (cursor) {
                cursor.style.left = `${x}px`;
                cursor.style.top = `${y}px`;
            }

            setTimeout(() => {
                el.focus();
                resolve();
            }, 750);
        }, 350);
    })""",
        selector,
    )
    wait_seconds(page, 0.6)
    page.type(selector, text, delay=delay_ms)
    wait_seconds(page, 1.0)


def pregenerate_audio_clips(
    temp_dir: Path, voice: str = "en-US-ChristopherNeural"
) -> dict[str, float]:
    """Pre-synthesizes all narration clips and returns their exact durations."""
    import asyncio

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    durations: dict[str, float] = {}

    async def generate():
        for filename, text in NARRATION_SCRIPTS:
            out_file = temp_dir / filename
            comm = edge_tts.Communicate(text, voice, rate="+6%")
            await comm.save(str(out_file))

    print(f"[*] Pre-synthesizing {len(NARRATION_SCRIPTS)} voice-over clips...")
    asyncio.run(generate())

    for filename, _ in NARRATION_SCRIPTS:
        clip_path = temp_dir / filename
        cmd = [ffmpeg, "-i", str(clip_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603
        dur = 6.0
        for line in res.stderr.splitlines():
            if "Duration:" in line:
                part = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = part.split(":")
                dur = float(h) * 3600 + float(m) * 60 + float(s)
                break
        durations[filename] = dur
        print(f"    - {filename}: {dur:.2f}s")

    return durations


def record_walkthrough_video():
    """Drives Playwright through the guided flow and records the video."""
    video_dir = PROJECT_ROOT / "docs" / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = PROJECT_ROOT / "docs" / "images" / "turnkey_bundle_walkthrough"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    temp_audio_dir = Path(tempfile.mkdtemp(prefix="njord_bundle_audio_"))
    clip_durations = pregenerate_audio_clips(temp_audio_dir)

    port = 5096
    print(f"[*] Starting local Flask Configurator on port {port}...")
    start_flask_server(port)

    recorded_cues: list[tuple[float, str, str]] = []
    view_w, view_h = 1440, 900
    print(f"[*] Launching Chromium at {view_w}x{view_h} Full HD...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": view_w, "height": view_h},
            color_scheme="dark",
            record_video_dir=str(video_dir),
            record_video_size={"width": view_w, "height": view_h},
        )
        context.add_init_script(
            """
            localStorage.setItem('user-theme-preference', 'futuristic-dark');
            localStorage.setItem('configurator_hide_quickstart_guide', 'true');
            localStorage.setItem('configurator_quickstart_shown', 'true');
            document.documentElement.setAttribute('data-theme', 'futuristic-dark');
        """
        )
        page = context.new_page()

        # Intercept network scan
        def handle_scan(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body="""{
                    "hosts": [
                        {
                            "ip": "192.168.1.185",
                            "hostname": "njord-cloud-01",
                            "vendor": "Debian 12 Sovereign Server (Proxmox)",
                            "mac": "BC:24:11:9A:88:2E"
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
                        "model": "Debian GNU/Linux 12 (Bookworm) x86_64",
                        "serial": "njord-srv-node-101",
                        "ram": "8.0 GB",
                        "disks": [
                            {
                                "mounted_on": "/",
                                "size": "64 GB",
                                "pcent": "12%"
                            }
                        ]
                    }
                }""",
            )

        page.route("**/get-device-details", handle_device_details)

        # -------------------------------------------------------------
        # Scene 1: Welcome & Network Auto-Discovery (Futuristic Dark)
        # -------------------------------------------------------------
        print("[*] Scene 1: Welcome & Discovery Scan in Futuristic Dark...")
        page.goto(f"http://127.0.0.1:{port}/")
        time.sleep(0.8)
        page.evaluate(
            """() => {
            document.documentElement.setAttribute('data-theme', 'futuristic-dark');
            document.body.classList.remove('bg-light');
            document.querySelectorAll(
                '#quickStartModal, #onboardingModal, .modal-backdrop, .modal, ' +
                '.introjs-overlay, .introjs-helperLayer, .introjs-tooltipReferenceLayer'
            ).forEach(e => e.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
        }"""
        )
        init_custom_cursor(page)

        video_start_time = time.time()

        def record_cue(scene_idx: int, offset_sec: float = 0.2) -> float:
            fname, text = NARRATION_SCRIPTS[scene_idx]
            elapsed = round(max(0.0, time.time() - video_start_time + offset_sec), 2)
            recorded_cues.append((elapsed, text, fname))
            update_narration_subtitle(page, text)
            print(f"    [Cue {scene_idx+1}] @ {elapsed:.2f}s: {text[:45]}...")
            return clip_durations[fname]

        # Trigger Cue 1
        d1 = record_cue(0, offset_sec=0.2)

        # Capture Scene 1 Screenshot
        page.screenshot(path=str(screenshot_dir / "scene_1_discovery_start.png"))

        # Display welcome screen for full speech duration + buffer
        wait_seconds(page, d1 + 1.2)

        # Move cursor to Begin Scan button and click
        print("[*] Moving cursor to Begin Discovery button...")
        move_cursor_and_click(page, "#begin-scan-btn", wait_after_sec=2.5)

        # -------------------------------------------------------------
        # Scene 2: Target Node Found & Credentials Entry
        # -------------------------------------------------------------
        print("[*] Scene 2: Target Node Found & Credentials Entry...")
        page.wait_for_selector(".device-card", timeout=8000)

        # Smoothly center device card
        page.evaluate(
            """() => {
            const card = document.querySelector('.device-card');
            if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }"""
        )
        wait_seconds(page, 0.8)

        # Trigger Cue 2 ONLY AFTER node card is visible
        d2 = record_cue(1, offset_sec=0.2)
        scene2_start = time.time()

        # Move cursor to device checkbox and enable it
        print("[*] Clicking device checkbox...")
        move_cursor_and_click(
            page, ".device-card .form-check-input", wait_after_sec=1.0
        )
        page.evaluate(
            """() => {
            const card = document.querySelector('.device-card');
            if (card) card.classList.add('border-primary', 'shadow');
        }"""
        )

        # Move cursor to username input and type 'admin'
        print("[*] Entering username 'admin'...")
        move_cursor_to_input_and_type(page, ".device-username", "admin", delay_ms=120)

        # Move cursor to password input and type password
        print("[*] Entering password...")
        move_cursor_to_input_and_type(
            page, ".device-password", "sovereign-cloud", delay_ms=120
        )

        # Capture Scene 2 Screenshot
        page.screenshot(path=str(screenshot_dir / "scene_2_node_found_credentials.png"))

        # Wait until voice-over 2 has finished + pause
        s2_elapsed = time.time() - scene2_start
        s2_remaining = max(1.5, (d2 + 1.5) - s2_elapsed)
        wait_seconds(page, s2_remaining)

        # -------------------------------------------------------------
        # Scene 3: Inspect Hardware & Verify SSH Specs
        # -------------------------------------------------------------
        print("[*] Scene 3: Inspect Hardware & Verify SSH...")
        move_cursor_and_click(page, "#get-details-btn", wait_after_sec=2.5)
        page.wait_for_selector("#proceed-to-step3-btn", timeout=8000)

        # Scroll to show complete hardware specs card
        page.evaluate(
            """() => {
            const btn = document.getElementById('proceed-to-step3-btn');
            if (btn) btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }"""
        )
        wait_seconds(page, 0.8)

        d3 = record_cue(2, offset_sec=0.2)
        scene3_start = time.time()

        # Capture Scene 3 Screenshot (Hardware specs verified)
        page.screenshot(path=str(screenshot_dir / "scene_3_hardware_verified.png"))

        s3_elapsed = time.time() - scene3_start
        s3_remaining = max(1.5, (d3 + 1.5) - s3_elapsed)
        wait_seconds(page, s3_remaining)

        # Move cursor to Proceed button and click
        print("[*] Moving to Step 3: Software Catalog & Stacks...")
        move_cursor_and_click(page, "#proceed-to-step3-btn", wait_after_sec=2.0)

        # -------------------------------------------------------------
        # Scene 4: 1-Click Turnkey Bundle Selection (Modern Sovereign Workplace)
        # -------------------------------------------------------------
        print("[*] Scene 4: 1-Click Turnkey Bundle Selection...")
        page.wait_for_selector(".package-card", timeout=8000)

        # Scroll down smoothly to show Turnkey Stacks
        page.evaluate(
            """() => {
            const pkgTab = document.getElementById('v-pills-packages-tab');
            if (pkgTab) pkgTab.click();
            const card = document.querySelector(
                '.package-card[data-package-id="modern-workplace"]'
            );
            if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }"""
        )
        wait_seconds(page, 1.0)

        d4 = record_cue(3, offset_sec=0.2)
        scene4_start = time.time()

        # Click The Modern Sovereign Workplace Bundle Card!
        print("[*] Selecting The Modern Sovereign Workplace 1-Click Bundle...")
        move_cursor_and_click(
            page,
            '.package-card[data-package-id="modern-workplace"]',
            wait_after_sec=2.0,
        )

        # Capture Scene 4 Screenshot (Bundle selected with pills)
        page.screenshot(
            path=str(screenshot_dir / "scene_4_turnkey_bundle_selected.png")
        )

        s4_elapsed = time.time() - scene4_start
        s4_remaining = max(2.0, (d4 + 2.0) - s4_elapsed)
        wait_seconds(page, s4_remaining)

        # Click Proceed to Step 4 (Configuration)
        print("[*] Clicking Proceed to Step 4...")
        page.evaluate(
            """() => {
            const proceedBtn = document.getElementById('proceed-to-step4-btn');
            if (proceedBtn) {
                proceedBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }"""
        )
        wait_seconds(page, 0.8)
        move_cursor_and_click(page, "#proceed-to-step4-btn", wait_after_sec=2.0)

        # -------------------------------------------------------------
        # Scene 5: Automated Live Deployment Stream
        # -------------------------------------------------------------
        print("[*] Scene 5: Automated Live Deployment Stream...")

        # Stream real-time simulated progress log
        log_lines = [
            ("[1/5] Initializing agentless SSH session to 192.168.1.185...", 10),
            ("[2/5] Target OS verified: Debian 12 Bookworm (Linux 6.1.0)", 25),
            ("[2/5] Validating Docker Engine & Compose plugin...", 40),
            (
                "[3/5] Pulling official images: nextcloud, mariadb, redis, vaultwarden",
                60,
            ),
            (
                "[4/5] Creating isolated persistent volumes with SHA-256 integrity...",
                75,
            ),
            ("[4/5] Injecting dynamic secrets and environment parameters...", 88),
            ("[5/5] Orchestrating stack containers via docker compose up -d...", 95),
            ("[5/5] Health checks verified: All 6 microservices ONLINE!", 100),
        ]

        page.evaluate(
            """() => {
            const body = document.getElementById('wizard-body');
            if (body) {
                body.innerHTML = `
                    <div class="p-4 text-start">
                        <div class="d-flex justify-content-between ` +
                        `align-items-center mb-3">
                            <h4 class="fw-bold mb-0">
                                <i class="fa-solid fa-layer-group ` +
                                `text-primary me-2"></i>
                                Deploying Sovereign Workplace Bundle...
                            </h4>
                            <span class="badge bg-primary px-3 py-2" ` +
                            `id="demo-pct-badge">10%</span>
                        </div>
                        <div class="progress mb-4" style="height: 12px; ` +
                        `border-radius: 6px;">
                            <div id="demo-progress-bar" class="progress-bar ` +
                            `progress-bar-striped progress-bar-animated ` +
                            `bg-primary" style="width: 10%;"></div>
                        </div>
                        <div id="demo-terminal" class="p-3 rounded font-monospace ` +
                        `small" style="background:#090d16; border:1px solid ` +
                        `rgba(0,242,254,0.3); color:#38bdf8; height:240px; ` +
                        `overflow-y:auto; line-height:1.6;"></div>
                    </div>
                `;
            }
        }"""
        )

        for line, pct in log_lines:
            page.evaluate(
                f"""() => {{
                const term = document.getElementById('demo-terminal');
                const bar = document.getElementById('demo-progress-bar');
                const badge = document.getElementById('demo-pct-badge');
                if (term) {{
                    term.innerHTML += '<div><span style="color:#00f2fe;">❯</span> ' +
                        '{line}</div>';
                    term.scrollTop = term.scrollHeight;
                }}
                if (bar) bar.style.width = '{pct}%';
                if (badge) badge.innerText = '{pct}%';
            }}"""
            )
            wait_seconds(page, 0.45)

        # -------------------------------------------------------------
        # Scene 6: Celebratory Deployment Complete & Instant Web Access
        # -------------------------------------------------------------
        print("[*] Scene 6: Celebratory Success & Instant Web Access...")
        page.evaluate(
            """() => {
            const body = document.getElementById('wizard-body');
            if (body) {
                body.innerHTML = `
                    <div class="p-4 text-center">
                        <div class="mb-3 p-3 bg-success-subtle text-success ` +
                        `rounded-circle d-inline-flex align-items-center ` +
                        `justify-content-center shadow-lg" ` +
                        `style="width: 80px; height: 80px;">
                            <i class="fa-solid fa-circle-check fa-3x"></i>
                        </div>
                        <h3 class="fw-bold text-white mb-2">` +
                        `Sovereign Cloud Deployment Complete!</h3>
                        <p class="text-muted mb-4">All 6 microservices in ` +
                        `The Modern Sovereign Workplace are active, isolated, ` +
                        `and healthy.</p>

                        <div class="row row-cols-1 row-cols-md-2 g-3 ` +
                        `max-width-700 mx-auto text-start">
                            <div class="col">
                                <div class="card p-3 border-primary shadow-sm ` +
                                `h-100" style="background:rgba(15,23,42,0.8);">
                                    <div class="d-flex align-items-center ` +
                                    `justify-content-between mb-2">
                                        <div class="d-flex align-items-center">
                                            <i class="fa-solid fa-cloud ` +
                                            `text-primary me-2 fa-lg"></i>
                                            <strong class="text-white">` +
                                            `Nextcloud Hub</strong>
                                        </div>
                                        <span class="badge bg-success-subtle ` +
                                        `text-success border ` +
                                        `border-success-subtle">Online</span>
                                    </div>
                                    <p class="small text-muted mb-3">Enterprise ` +
                                    `file sync, calendars, and real-time ` +
                                    `document collaboration.</p>
                                    <a href="http://192.168.1.185:8080" ` +
                                    `target="_blank" class="btn btn-sm ` +
                                    `btn-primary w-100">
                                        <i class="fa-solid ` +
                                        `fa-arrow-up-right-from-square me-1"></i> ` +
                                        `Open Nextcloud (:8080)
                                    </a>
                                </div>
                            </div>
                            <div class="col">
                                <div class="card p-3 border-primary shadow-sm ` +
                                `h-100" style="background:rgba(15,23,42,0.8);">
                                    <div class="d-flex align-items-center ` +
                                    `justify-content-between mb-2">
                                        <div class="d-flex align-items-center">
                                            <i class="fa-solid fa-shield-halved ` +
                                            `text-info me-2 fa-lg"></i>
                                            <strong class="text-white">` +
                                            `Vaultwarden</strong>
                                        </div>
                                        <span class="badge bg-success-subtle ` +
                                        `text-success border ` +
                                        `border-success-subtle">Online</span>
                                    </div>
                                    <p class="small text-muted mb-3">Secure ` +
                                    `encrypted password manager for ` +
                                    `organizations and teams.</p>
                                    <a href="http://192.168.1.185:8088" ` +
                                    `target="_blank" class="btn btn-sm ` +
                                    `btn-info text-dark w-100">
                                        <i class="fa-solid ` +
                                        `fa-arrow-up-right-from-square me-1"></i> ` +
                                        `Open Vaultwarden (:8088)
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
        }"""
        )

        d5 = record_cue(4, offset_sec=0.2)
        wait_seconds(page, d5 + 1.2)

        # Trigger Cue 6 (Instant Web Access & Outro)
        d6 = record_cue(5, offset_sec=0.2)

        # Move cursor to Open Nextcloud button
        print("[*] Moving cursor to Open Nextcloud launch button...")
        page.evaluate(
            """() => {
            const btn = document.querySelector('a[href="http://192.168.1.185:8080"]');
            const cursor = document.getElementById('njord-animated-cursor');
            if (btn && cursor) {
                const rect = btn.getBoundingClientRect();
                cursor.style.left = `${rect.left + rect.width / 2}px`;
                cursor.style.top = `${rect.top + rect.height / 2}px`;
            }
        }"""
        )

        # Capture Scene 6 Screenshot (Celebratory launch screen)
        page.screenshot(
            path=str(screenshot_dir / "scene_6_turnkey_deployment_complete.png")
        )

        wait_seconds(page, d6 + 2.5)

        # Close page and context to finalize raw video recording
        print("[*] Closing browser session to flush video buffer...")
        page.close()
        context.close()
        browser.close()

    # Find the recorded raw webm file
    recorded_raw_files = list(video_dir.glob("*.webm"))
    if not recorded_raw_files:
        print("[!] No raw video file found in video_dir!")
        return

    # Sort by mtime descending
    recorded_raw_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    raw_video_path = recorded_raw_files[0]

    # Combine video and audio
    postprocess_video(
        raw_video_path,
        video_dir / "turnkey-bundle-deployment.mp4",
        video_dir / "turnkey-bundle-deployment.webm",
        temp_audio_dir,
        recorded_cues,
    )


def postprocess_video(
    raw_video: Path,
    out_mp4: Path,
    out_webm: Path,
    temp_audio_dir: Path,
    recorded_cues: list[tuple[float, str, str]],
):
    """Muxes audio tracks at exact recorded timestamps and generates subtitles."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    print("[*] Generating synchronized WebVTT and SubRip subtitle files...")
    srt_path = out_mp4.with_suffix(".en.srt")
    vtt_path = out_mp4.with_suffix(".en.vtt")

    srt_lines = []
    vtt_lines = ["WEBVTT", ""]

    def format_ts(seconds: float, srt_format: bool = True) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        sep = "," if srt_format else "."
        return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

    for idx, (start_t, text, fname) in enumerate(recorded_cues):
        clip_path = temp_audio_dir / fname
        cmd = [ffmpeg, "-i", str(clip_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603
        clip_len = 5.0
        for line in res.stderr.splitlines():
            if "Duration:" in line:
                part = line.split("Duration:")[1].split(",")[0].strip()
                hh, mm, ss = part.split(":")
                clip_len = float(hh) * 3600 + float(mm) * 60 + float(ss)
                break

        end_t = start_t + clip_len + 0.4
        srt_lines.extend(
            [
                str(idx + 1),
                f"{format_ts(start_t, True)} --> {format_ts(end_t, True)}",
                text,
                "",
            ]
        )
        vtt_lines.extend(
            [
                f"{format_ts(start_t, False)} --> {format_ts(end_t, False)}",
                text,
                "",
            ]
        )

    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")
    print(f"    - Subtitles written to {srt_path.name} & {vtt_path.name}")

    # Build FFmpeg complex filter to delay each narration clip to its recorded cue
    inputs = ["-i", str(raw_video)]
    filter_parts = []
    for idx, (start_t, _, fname) in enumerate(recorded_cues):
        inputs.extend(["-i", str(temp_audio_dir / fname)])
        delay_ms = int(start_t * 1000)
        filter_parts.append(
            f"[{idx+1}:a]adelay={delay_ms}|{delay_ms}," f"volume=1.0[a{idx+1}];"
        )

    mix_inputs = "".join(f"[a{i+1}]" for i in range(len(recorded_cues)))
    filter_complex = (
        "".join(filter_parts)
        + f"{mix_inputs}amix=inputs={len(recorded_cues)}:normalize=0[aout]"
    )

    print("[*] Encoding final MP4 with synchronized audio track...")
    ffmpeg_mp4_cmd = (
        [ffmpeg, "-y"]
        + inputs
        + [
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(out_mp4),
        ]
    )
    subprocess.run(ffmpeg_mp4_cmd, check=True)  # nosec B603
    print(f"✅ High-Definition MP4 created: {out_mp4} ({out_mp4.stat().st_size} bytes)")

    print("[*] Encoding webm with Opus audio...")
    ffmpeg_webm_cmd = (
        [ffmpeg, "-y"]
        + inputs
        + [
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "libvpx-vp9",
            "-crf",
            "30",
            "-b:v",
            "0",
            "-c:a",
            "libopus",
            "-b:a",
            "128k",
            "-shortest",
            str(out_webm),
        ]
    )
    subprocess.run(ffmpeg_webm_cmd, check=True)  # nosec B603
    print(
        f"✅ High-Definition WebM created: {out_webm} ({out_webm.stat().st_size} bytes)"
    )


if __name__ == "__main__":
    record_walkthrough_video()
