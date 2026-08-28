"""
High-definition video walkthrough generator for NjordDeploy.

Records a professional, calm, step-by-step video of deploying Immich on a
Virtual Pi / Proxmox node with frame-accurate neural voice-over audio and subtitles.

Features:
- Viewport: 1440x900 (16:10 Full HD canvas)
- Theme: Futuristic Dark initialized before DOM load (zero light flicker)
- Audio: Neural voice-over (en-US-ChristopherNeural) in mathematical lockstep
- Subtitles: Synchronized WebVTT (.vtt) and SubRip (.srt) files
- Visual cursor: Smooth bezier travel, click ripples, and button hover pulses
- Pacing: Audio-driven scene pacing ensuring every voice line finishes with
  calm breathing room before any screen transition occurs.
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
        "Virtual Pi 5 discovered at 192.168.1.185. Entering SSH "
        "credentials for verification.",
    ),
    (
        "scene3.mp3",
        "Hardware verified: 8 gigabytes of RAM and 64 gigabytes of "
        "storage. Ready for the software catalog.",
    ),
    (
        "scene4.mp3",
        "Under Media Servers, selecting Immich: complete photo "
        "suite with AI recognition and PostgreSQL.",
    ),
    (
        "scene5.mp3",
        "Deployment complete! All four microservices are deployed "
        "via Docker and verified healthy.",
    ),
    (
        "scene6.mp3",
        "Launch the Immich Web UI instantly with one click on " "port 2283.",
    ),
]


def start_flask_server(port: int = 5095) -> None:
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
    screenshot_dir = PROJECT_ROOT / "docs" / "images" / "immich_walkthrough"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    temp_audio_dir = Path(tempfile.mkdtemp(prefix="njord_preaudio_"))
    clip_durations = pregenerate_audio_clips(temp_audio_dir)

    port = 5095
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
                            "hostname": "virtual-pi-5",
                            "vendor": "Raspberry Pi (Proxmox KVM)",
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
                        "model": "Raspberry Pi 5 Model B (8GB RAM - Proxmox KVM)",
                        "serial": "10000000e4b8c9d2",
                        "ram": "8.0 GB",
                        "disks": [
                            {
                                "mounted_on": "/",
                                "size": "64 GB",
                                "pcent": "14%"
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
        # Scene 2: Virtual Pi Node Found & SSH Credentials Entry
        # -------------------------------------------------------------
        print("[*] Scene 2: Virtual Pi Node Found & Credentials Entry...")
        page.wait_for_selector(".device-card", timeout=8000)

        # Smoothly center device card
        page.evaluate(
            """() => {
            const card = document.querySelector('.device-card');
            if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }"""
        )
        wait_seconds(page, 0.8)

        # Trigger Cue 2 ONLY AFTER Pi card is visible on screen!
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

        # Move cursor to username input and type 'pi'
        print("[*] Entering username 'pi'...")
        move_cursor_to_input_and_type(page, ".device-username", "pi", delay_ms=120)

        # Move cursor to password input and type 'raspberry'
        print("[*] Entering password 'raspberry'...")
        move_cursor_to_input_and_type(
            page, ".device-password", "raspberry", delay_ms=120
        )

        # Capture Scene 2 Screenshot (Credentials entered)
        page.screenshot(path=str(screenshot_dir / "scene_2_node_found_credentials.png"))

        # Wait until voice-over 2 has finished + 1.5s pause
        s2_elapsed = time.time() - scene2_start
        s2_remaining = max(1.5, (d2 + 1.5) - s2_elapsed)
        wait_seconds(page, s2_remaining)

        # -------------------------------------------------------------
        # Scene 3: Inspect Hardware & Verify SSH Specs (8GB RAM & 64GB SSD)
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

        # Trigger Cue 3 ONLY AFTER hardware details card (8 GB RAM) is visible!
        d3 = record_cue(2, offset_sec=0.2)

        # Capture Scene 3 Screenshot (Hardware specs verified)
        page.screenshot(path=str(screenshot_dir / "scene_3_hardware_verified.png"))
        # Generous pause for the complete voice-over 3 + 2.0s reading time
        wait_seconds(page, d3 + 2.0)

        # -------------------------------------------------------------
        # Scene 4: Select Software Stack (Media Servers -> Immich)
        # -------------------------------------------------------------
        print("[*] Scene 4: Moving to Software Selection & Immich...")
        move_cursor_and_click(page, "#proceed-to-step3-btn", wait_after_sec=2.0)
        page.wait_for_selector("#v-pills-tab", timeout=8000)

        # Trigger Cue 4 when software catalog is visible
        d4 = record_cue(3, offset_sec=0.2)
        scene4_start = time.time()

        # Click the 'Media Servers' tab pill on the left
        print("[*] Clicking 'Media Servers' category tab...")
        page.evaluate(
            """() => {
            const tabBtn = Array.from(
                document.querySelectorAll('#v-pills-tab button')
            ).find(b => b.textContent.includes('Media'));
            if (tabBtn) {
                tabBtn.click();
            }
        }"""
        )
        init_custom_cursor(page)
        page.evaluate(
            """() => {
            const tabBtn = Array.from(
                document.querySelectorAll('#v-pills-tab button')
            ).find(b => b.textContent.includes('Media'));
            const cursor = document.getElementById('njord-animated-cursor');
            if (tabBtn && cursor) {
                const rect = tabBtn.getBoundingClientRect();
                cursor.style.left = `${rect.left + rect.width / 2}px`;
                cursor.style.top = `${rect.top + rect.height / 2}px`;
            }
        }"""
        )
        wait_seconds(page, 1.2)

        # Scroll to Immich card and move cursor to its Select button
        print("[*] Scrolling to and selecting Immich...")
        page.evaluate(
            """() => {
            const cards = Array.from(document.querySelectorAll('.component-card'));
            const immichCard = cards.find(c => c.textContent.includes('Immich'));
            if (immichCard) {
                immichCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }"""
        )
        wait_seconds(page, 1.0)

        # Click Immich Select button
        page.evaluate(
            """() => {
            const cards = Array.from(document.querySelectorAll('.component-card'));
            const immichCard = cards.find(c => c.textContent.includes('Immich'));
            const cursor = document.getElementById('njord-animated-cursor');
            if (immichCard) {
                const btn = immichCard.querySelector('.btn-select-software');
                if (btn) {
                    const rect = btn.getBoundingClientRect();
                    if (cursor) {
                        cursor.style.left = `${rect.left + rect.width / 2}px`;
                        cursor.style.top = `${rect.top + rect.height / 2}px`;
                        cursor.style.transform = 'scale(0.85)';
                    }
                    btn.click();
                    setTimeout(() => {
                        if (cursor) cursor.style.transform = 'scale(1)';
                    }, 250);
                }
            }
        }"""
        )
        wait_seconds(page, 1.0)

        # Capture Scene 4 Screenshot (Immich selected)
        page.screenshot(path=str(screenshot_dir / "scene_4_immich_selected.png"))

        # Wait until voice-over 4 has finished + 2.0s pause to see selected state
        s4_elapsed = time.time() - scene4_start
        s4_remaining = max(1.5, (d4 + 2.0) - s4_elapsed)
        wait_seconds(page, s4_remaining)

        # Move cursor to 'Proceed to Deployment' button and click
        print("[*] Moving cursor to proceed to Step 4 Deployment...")
        page.evaluate(
            """() => {
            const btn = document.getElementById('proceed-to-step4-btn');
            if (btn) {
                btn.innerHTML = (
                    '<i class="fa-solid fa-rocket me-2"></i>Deploy Immich Stack'
                );
            }
        }"""
        )
        move_cursor_and_click(page, "#proceed-to-step4-btn", wait_after_sec=2.0)

        # -------------------------------------------------------------
        # Scene 5: Live Terminal Stream Deployment
        # -------------------------------------------------------------
        print("[*] Scene 5: Live Deployment Streaming...")
        page.evaluate(
            """() => {
            const header = document.getElementById('wizard-header');
            if (header) {
                header.innerHTML = (
                    '<strong>Step 4 of 4: Deploying Immich Stack</strong>'
                );
            }
            const pbar = document.getElementById('wizard-progress-bar');
            if (pbar) pbar.style.width = '15%';

            const body = document.getElementById('wizard-body');
            if (body) {
                body.innerHTML = `
                    <div class="text-start">
                        <div class="d-flex justify-content-between ` +
                        `align-items-center mb-3">
                            <h4 class="mb-0"><i class="fa-solid fa-rocket ` +
                            `text-primary me-2"></i>` +
                            `Deploying Immich Stack...</h4>
                            <span class="badge bg-primary fs-6" id="dep-badge">` +
                            `<i class="fa-solid fa-spinner fa-spin me-1"></i> ` +
                            `Installing 4 Containers</span>
                        </div>
                        <div class="progress mb-4" style="height: 14px;">
                            <div class="progress-bar progress-bar-striped ` +
                            `progress-bar-animated bg-primary" id="prog-bar" ` +
                            `style="width: 20%; transition: width 0.6s ease;">` +
                            `</div>
                        </div>
                        <div class="card bg-dark text-light border-0 ` +
                        `shadow mb-3">
                            <div class="card-header bg-black py-2 d-flex ` +
                            `justify-content-between align-items-center">
                                <span class="small text-muted ` +
                                `font-monospace"><i class="fa-solid ` +
                                `fa-terminal me-2 text-success"></i>` +
                                `Deployment Log: pi@192.168.1.185 ` +
                                `(Virtual Pi 5)</span>
                                <span class="badge bg-success small">` +
                                `Engine: Docker CE 27.1.1</span>
                            </div>
                            <div class="card-body p-3 font-monospace small" ` +
                            `id="stream-term" style="background-color: ` +
                            `#0f172a; min-height: 270px; color: #38bdf8;">
                                <div><span class="text-success">[OK]</span> ` +
                                `SSH connection established ` +
                                `(pi@192.168.1.185)</div>
                            </div>
                        </div>
                    </div>
                `;
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }"""
        )
        init_custom_cursor(page)
        wait_seconds(page, 1.2)

        # Feed progressive log lines calmly
        log_steps = [
            (
                35,
                '<span class="text-success">[OK]</span> Verified Docker '
                "Engine & Docker Compose plugin active",
            ),
            (
                50,
                '<span class="text-success">[OK]</span> Synthesized Jinja2 '
                "Compose template for Immich Stack",
            ),
            (
                68,
                '<span class="text-info">[PULL]</span> Pulling container '
                "images (server, ML, postgres, redis)...",
            ),
            (
                80,
                '<span class="text-success">[OK]</span> Created persistent '
                "volume mounts: /srv/immich/upload",
            ),
            (
                88,
                '<span class="text-info">[RUN]</span> Starting '
                'immich_postgres (5432) -> <span class="text-success">'
                "Healthy</span>",
            ),
            (
                93,
                '<span class="text-info">[RUN]</span> Starting '
                'immich_redis (6379) -> <span class="text-success">'
                "Healthy</span>",
            ),
            (
                97,
                '<span class="text-info">[RUN]</span> Starting '
                'immich_machine_learning -> <span class="text-success">'
                "Healthy</span>",
            ),
            (
                100,
                '<span class="text-info">[RUN]</span> Starting '
                'immich_server (:2283) -> <span class="text-success">'
                "Healthy</span>",
            ),
        ]

        for percent, log_line in log_steps:
            page.evaluate(
                f"""() => {{
                const bar = document.getElementById('prog-bar');
                if (bar) {{
                    bar.style.width = '{percent}%';
                    if ({percent} === 100) {{
                        bar.classList.remove('bg-primary');
                        bar.classList.add('bg-success');
                    }}
                }}
                const term = document.getElementById('stream-term');
                if (term) {{
                    const div = document.createElement('div');
                    div.innerHTML = '{log_line}';
                    term.appendChild(div);
                }}
            }}"""
            )
            wait_seconds(page, 1.2)

        # Capture Scene 5 Screenshot (Deployment terminal completed)
        page.screenshot(path=str(screenshot_dir / "scene_5_live_deployment_stream.png"))

        # Trigger Cue 5 ONLY AFTER all 4 containers are 100% healthy and deployed!
        d5 = record_cue(4, offset_sec=0.2)

        # Calm pause on the completed terminal for voice-over 5 + buffer
        wait_seconds(page, d5 + 2.0)

        # -------------------------------------------------------------
        # Scene 6: Instant Access & Success Screen
        # -------------------------------------------------------------
        print("[*] Scene 6: Instant Web Access & Success Screen...")
        page.evaluate(
            """() => {
            const header = document.getElementById('wizard-header');
            if (header) {
                header.innerHTML = (
                    '<strong>Step 4 of 4: Deployment Complete</strong>'
                );
            }
            const body = document.getElementById('wizard-body');
            if (body) {
                body.innerHTML = `
                    <div class="text-center py-3">
                        <div class="display-4 text-success mb-2">` +
                        `<i class="fa-solid fa-circle-check"></i></div>
                        <h2 class="fw-bold mb-2">` +
                        `Immich Deployed Successfully!</h2>
                        <p class="text-muted mb-4 fs-5">` +
                        `Your self-hosted photo & video suite is live on ` +
                        `your Virtual Pi.</p>

                        <div class="row justify-content-center mb-4">
                            <div class="col-md-7">
                                <div class="card border-primary shadow p-4">
                                    <div class="d-flex align-items-center ` +
                                     `justify-content-between mb-3">
                                        <div class="d-flex align-items-center">
                                            <i class="fa-solid ` +
                                            `fa-images text-primary fs-2 ` +
                                            `me-3"></i>
                                            <div class="text-start">
                                                <h5 class="fw-bold mb-0">` +
                                                `Immich Web UI</h5>
                                                <small class="text-muted">` +
                                                `Photo management & ` +
                                                `backup</small>
                                            </div>
                                        </div>
                                        <span class="badge bg-success ` +
                                        `px-3 py-2 fs-6">Active</span>
                                    </div>
                                    <a href="http://192.168.1.185:2283" ` +
                                    `class="btn btn-primary btn-lg ` +
                                    `font-monospace w-100 shadow-sm" ` +
                                    `id="launch-btn">
                                        <i class="fa-solid ` +
                                        `fa-arrow-up-right-from-square me-2">` +
                                        `</i> Open http://192.168.1.185:2283
                                    </a>
                                </div>
                            </div>
                        </div>

                        <div class="d-flex justify-content-center gap-3">
                            <span class="badge bg-success-subtle text-success ` +
                            `border border-success p-2 fs-6">
                                <i class="fa-solid fa-heart-pulse me-1"></i> ` +
                                `4/4 Containers Healthy
                            </span>
                            <span class="badge bg-primary-subtle ` +
                            `text-primary border border-primary p-2 fs-6">
                                <i class="fa-solid fa-microchip me-1"></i> ` +
                                `Machine Learning Enabled
                            </span>
                            <span class="badge bg-info-subtle text-info ` +
                            `border border-info p-2 fs-6">
                                <i class="fa-solid fa-hard-drive me-1"></i> ` +
                                `/srv/immich/upload Mounted
                            </span>
                        </div>
                    </div>
                `;
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }"""
        )
        init_custom_cursor(page)

        # Trigger Cue 6 when success screen displays
        d6 = record_cue(5, offset_sec=0.2)

        # Capture Scene 6 Screenshot (Success card & launch button)
        page.screenshot(path=str(screenshot_dir / "scene_6_success_web_access.png"))
        wait_seconds(page, 2.0)

        # Move large cursor over the launch button and pulse
        print("[*] Moving cursor over launch button...")
        page.evaluate(
            """() => {
            const btn = document.getElementById('launch-btn');
            const cursor = document.getElementById('njord-animated-cursor');
            if (btn && cursor) {
                const rect = btn.getBoundingClientRect();
                cursor.style.left = `${rect.left + rect.width / 2}px`;
                cursor.style.top = `${rect.top + rect.height / 2}px`;
                btn.classList.add('btn-success', 'shadow-lg');
                btn.classList.remove('btn-primary');
                btn.style.transform = 'scale(1.03)';
                btn.style.transition = 'all 0.4s ease';
            }
        }"""
        )
        # Generous holding pause at the end for voice-over 6 + outro
        wait_seconds(page, d6 + 3.0)

        # Close page & context to finalize video
        raw_video_path = Path(page.video.path())
        page.close()
        context.close()
        browser.close()

    # Mux pregenerated audio with the recorded video at exact measured timestamps
    mux_audio_tracks(
        raw_video_path,
        video_dir,
        temp_audio_dir,
        recorded_cues,
        clip_durations,
    )
    print("[+] Done recording calm Immich deployment walkthrough video!")


def mux_audio_tracks(
    raw_video_path: Path,
    video_dir: Path,
    temp_audio_dir: Path,
    recorded_cues: list[tuple[float, str, str]],
    clip_durations: dict[str, float],
) -> None:
    """Muxes the pre-synthesized audio clips at exact recorded timestamps."""
    import shutil

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    def fmt_vtt(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"00:{m:02d}:{s:02d}.{ms:03d}"

    def fmt_srt(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"00:{m:02d}:{s:02d},{ms:03d}"

    vtt_lines = ["WEBVTT - Immich Deployment Walkthrough\n"]
    srt_lines = []
    for idx, (start_sec, text, filename) in enumerate(recorded_cues, 1):
        end_sec = start_sec + clip_durations.get(filename, 6.0) + 0.3
        vtt_lines.append(
            f"{idx}\n{fmt_vtt(start_sec)} --> {fmt_vtt(end_sec)}\n{text}\n"
        )
        srt_lines.append(
            f"{idx}\n{fmt_srt(start_sec)} --> {fmt_srt(end_sec)}\n{text}\n"
        )

    (video_dir / "immich-virtual-pi-deployment.en.vtt").write_text(
        "\n".join(vtt_lines), encoding="utf-8"
    )
    (video_dir / "immich-virtual-pi-deployment.en.srt").write_text(
        "\n".join(srt_lines), encoding="utf-8"
    )
    print("[+] Generated synchronized companion subtitles (.en.vtt, .en.srt)")

    # Build audio mix filter with exact frame-accurate delays
    inputs = []
    filter_parts = []
    mix_labels = []
    for i, (delay, _, filename) in enumerate(recorded_cues):
        inputs.extend(["-i", str(temp_audio_dir / filename)])
        ms = int(delay * 1000)
        filter_parts.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
        mix_labels.append(f"[a{i}]")

    filter_complex = (
        ";".join(filter_parts)
        + ";"
        + "".join(mix_labels)
        + f"amix=inputs={len(recorded_cues)}:dropout_transition=0:normalize=0[aout]"
    )
    mixed_audio = temp_audio_dir / "full_voiceover.mp3"

    cmd_mix = (
        [ffmpeg, "-y"]
        + inputs
        + ["-filter_complex", filter_complex, "-map", "[aout]", str(mixed_audio)]
    )
    subprocess.run(cmd_mix, check=True, capture_output=True)  # nosec B603

    # 1. Output MP4 with AAC audio (Broadest universal compatibility)
    mp4_target = video_dir / "immich-virtual-pi-deployment.mp4"
    cmd_mp4 = [
        ffmpeg,
        "-y",
        "-i",
        str(raw_video_path),
        "-i",
        str(mixed_audio),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(mp4_target),
    ]
    subprocess.run(cmd_mp4, check=True, capture_output=True)  # nosec B603
    mp4_size_mb = mp4_target.stat().st_size / (1024 * 1024)
    print(f"[+] Saved Audio-Muxed MP4: {mp4_target} ({mp4_size_mb:.2f} MB)")

    # 2. Output WebM with Opus audio
    webm_target = video_dir / "immich-virtual-pi-deployment.webm"
    temp_webm = temp_audio_dir / "out.webm"
    cmd_webm = [
        ffmpeg,
        "-y",
        "-i",
        str(raw_video_path),
        "-i",
        str(mixed_audio),
        "-c:v",
        "copy",
        "-c:a",
        "libopus",
        "-b:a",
        "128k",
        "-shortest",
        str(temp_webm),
    ]
    subprocess.run(cmd_webm, check=True, capture_output=True)  # nosec B603
    shutil.move(str(temp_webm), str(webm_target))
    webm_size_mb = webm_target.stat().st_size / (1024 * 1024)
    print(f"[+] Saved Audio-Muxed WebM: {webm_target} ({webm_size_mb:.2f} MB)")

    # Cleanup temp directory and raw video
    shutil.rmtree(temp_audio_dir, ignore_errors=True)
    if raw_video_path.exists() and raw_video_path != webm_target:
        try:
            raw_video_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    record_walkthrough_video()
