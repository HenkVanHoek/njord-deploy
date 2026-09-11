"""High-definition video walkthrough generator for any NjordDeploy component.

Records a professional, calm, step-by-step video of deploying any component
from the catalog on a Virtual Pi / Proxmox node with frame-accurate neural
voice-over audio and subtitles.

Key capabilities:
- Generic component selection via `--component <id>` (default: immich).
- Dynamic metadata, descriptions, categories, and port resolution from SST.
- Single and multi-UI support: automatically discovers all web endpoints
  (primary UI, admin consoles, secondary interfaces) and presents them cleanly.
- Scene 7 First-Run Web UI transition: clicks launch and reveals the live
  onboarding dashboard / initial user interface.
- Futuristic Dark theme initialized before DOM load (zero light flicker).
- Neural TTS voice-over with Edge-TTS in frame-accurate lockstep.
- Synchronized WebVTT (.vtt) and SubRip (.srt) companion files.
- Dual-format encoding: MP4 (H.264/AAC) and WebM (VP8/Opus).
"""

import argparse
import asyncio
import json
import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import edge_tts
import imageio_ffmpeg  # type: ignore[import-untyped]
from playwright.sync_api import sync_playwright

# Project Root Setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from configurator_app.app import create_app  # noqa: E402

# Hardcoded fallback ports for components with non-standard configs
FALLBACK_PORTS: Dict[str, str] = {
    "nextcloud": "8080",
    "vaultwarden": "8088",
    "nginx-proxy-manager": "81",
    "unifi-controller": "8443",
    "scrypted": "10443",
    "gitlab": "80",
    "octoprint": "5000",
    "heimdall": "80",
    "homer": "8080",
    "organizr": "80",
    "traefik": "8080",
    "minio": "9001",
    "uptime-kuma": "3001",
    "homeassistant": "8123",
    "pi-hole": "80",
    "njorddeploy-service-maintenance": "9999",
}


def load_component_catalog() -> Dict[str, Any]:
    """Loads all components and group rules from components_metadata.json."""
    meta_path = PROJECT_ROOT / "config" / "components_metadata.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def resolve_component_endpoints(
    comp_id: str,
    component_meta: Dict[str, Any],
    host_ip: str = "192.168.1.185",
) -> List[Dict[str, str]]:
    """Resolves all web UI endpoints (ports, names, URLs) for a component."""
    tmpl_dir = PROJECT_ROOT / "component_templates"
    name = component_meta.get("name", comp_id)
    protocol = component_meta.get("protocol", "http")
    ui_var = component_meta.get("ui_port_variable")

    ports: List[Tuple[str, str]] = []

    # 1. Inspect template-config/variables.json
    v_file = tmpl_dir / comp_id / "template-config" / "variables.json"
    if v_file.exists():
        # noinspection PyBroadException
        try:
            with open(v_file, "r", encoding="utf-8") as vf:
                vdata = json.load(vf)
            raw_vars = vdata.get("variables", []) if isinstance(vdata, dict) else vdata
            v_list = raw_vars if isinstance(raw_vars, list) else []
            for v in v_list:
                v_id = v.get("id") or v.get("name")
                vd = str(v.get("default", "")).strip()
                v_label = v.get("label") or str(v_id)
                if vd.isdigit():
                    if ui_var and v_id == ui_var:
                        ports.insert(0, (vd, f"{name} Web UI"))
                    elif "PORT" in str(v_id) and any(
                        k in str(v_id).lower()
                        for k in ["web", "ui", "console", "dashboard", "admin"]
                    ):
                        ports.append((vd, v_label))
        except Exception:  # nosec B110
            pass

    # 2. Inspect docker-compose.template.yml
    c_file = tmpl_dir / comp_id / "docker-compose.template.yml"
    if c_file.exists():
        content = c_file.read_text(encoding="utf-8")
        for m in re.finditer(
            r"([A-Z0-9_]+_PORT)[^}\n]*default\(['\"]?(\d+)['\"]?",
            content,
        ):
            v_name, p_val = m.group(1), m.group(2)
            lbl = v_name.replace("_", " ").title()
            if ui_var and v_name == ui_var:
                ports.insert(0, (p_val, f"{name} Web UI"))
            elif any(
                k in v_name.lower()
                for k in ["web", "ui", "console", "dashboard", "admin", "http"]
            ):
                ports.append((p_val, lbl))

        for m in re.finditer(r"-\s*['\"]?(\d{2,5}):(\d+)['\"]?", content):
            h_port, c_port = m.group(1), m.group(2)
            if c_port in [
                "80",
                "443",
                "8080",
                "3000",
                "5000",
                "8000",
                "9000",
                "9001",
            ]:
                ports.append((h_port, f"{name} (Port {h_port})"))

    # 3. Fallback dictionary check
    if not ports and comp_id in FALLBACK_PORTS:
        ports.append((FALLBACK_PORTS[comp_id], f"{name} Web UI"))

    # De-duplicate ports while preserving first-seen order
    seen_ports = set()
    cleaned_ports: List[Tuple[str, str]] = []
    for p, label in ports:
        if p not in seen_ports and p not in [
            "22",
            "53",
            "5432",
            "6379",
            "3306",
        ]:
            seen_ports.add(p)
            cleaned_ports.append((p, label))

    if not cleaned_ports:
        cleaned_ports.append(("80", f"{name} Web UI"))

    endpoints: List[Dict[str, str]] = []
    for p, label in cleaned_ports:
        proto = "https" if p in ["443", "8443", "9443", "10443"] else protocol
        endpoints.append(
            {
                "name": label,
                "port": p,
                "url": f"{proto}://{host_ip}:{p}",
                "protocol": proto,
            }
        )
    return endpoints


def build_narration_scripts(
    comp_id: str,
    meta: Dict[str, Any],
    endpoints: List[Dict[str, str]],
) -> List[Tuple[str, str]]:
    """Builds an audio-driven narration script for all 7 scenes."""
    name = meta.get("name", comp_id)
    group = meta.get("group", "Utilities")
    first_ep, *rest_eps = endpoints
    primary_port = first_ep["port"]

    is_multi_ui = len(endpoints) > 1

    scene1_text = (
        "Welcome to NjordDeploy. Let's start an automated discovery "
        "scan to locate nodes on our network."
    )
    scene2_text = (
        "Virtual Pi 5 discovered at 192.168.1.185. Entering SSH "
        "credentials for verification."
    )
    scene3_text = (
        "Hardware verified: 8 gigabytes of RAM and 64 gigabytes of "
        "storage. Ready for the software catalog."
    )
    desc_sample = meta.get("description", "")[:95].strip()
    scene4_text = f"In category {group}, selecting {name}: {desc_sample}."
    scene5_text = (
        f"Deployment complete! All containers for {name} are deployed "
        "via Docker and verified healthy."
    )

    if is_multi_ui:
        ep_summary = ", and ".join(
            [f"{ep['name']} on port {ep['port']}" for ep in endpoints[:2]]
        )
        scene6_text = (
            f"Instant access unlocked! {name} provides multiple web "
            f"interfaces, including {ep_summary}."
        )
        scene7_text = (
            f"Launching the {name} dashboard now to complete the first-run "
            "configuration and experience the active service."
        )
    else:
        scene6_text = (
            f"Launch the {name} Web UI instantly with one click on "
            f"port {primary_port}."
        )
        scene7_text = (
            f"Here is the live {name} web interface, ready for instant "
            "use directly on your local network."
        )

    return [
        ("scene1.mp3", scene1_text),
        ("scene2.mp3", scene2_text),
        ("scene3.mp3", scene3_text),
        ("scene4.mp3", scene4_text),
        ("scene5.mp3", scene5_text),
        ("scene6.mp3", scene6_text),
        ("scene7.mp3", scene7_text),
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
                'position: fixed; bottom: 24px; left: 50%; ' +
                'transform: translateX(-50%); ' +
                'background: rgba(15, 23, 42, 0.95); ' +
                'border: 1px solid rgba(0, 242, 254, 0.5); ' +
                'color: #f8fafc; padding: 10px 24px; border-radius: 9999px; ' +
                'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", ' +
                'Roboto, sans-serif; font-size: 15px; font-weight: 500; ' +
                'letter-spacing: 0.2px; ' +
                'box-shadow: 0 8px 32px rgba(0, 0, 0, 0.7), ' +
                '0 0 16px rgba(0, 242, 254, 0.3); ' +
                'backdrop-filter: blur(12px); ' +
                '-webkit-backdrop-filter: blur(12px); ' +
                'z-index: 9999999; display: flex; align-items: center; ' +
                'gap: 10px; max-width: 90%; transition: all 0.3s ease; ' +
                'pointer-events: none;'
            );
            document.body.appendChild(bar);
        }
        bar.innerHTML = `
            <span style="display:inline-block;width:10px;height:10px;' +
            'background:#00f2fe;border-radius:50%;box-shadow:0 0 8px #00f2fe;' +
            'margin-right:2px;animation:pulse 1.5s infinite;"></span>
            <span style="color:#38bdf8;font-weight:600;margin-right:4px;">' +
            'Voice-Over:</span>
            <span style="color:#ffffff;">${subtitleText}</span>
        `;
        bar.style.opacity = '1';
    }""",
        text,
    )


def move_cursor_and_click(page, selector: str, wait_after_sec: float = 1.0) -> None:
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


def move_cursor_to_input_and_type(
    page, selector: str, text: str, delay_ms: int = 150
) -> None:
    """Moves the cursor to an input box and types with natural cadence."""
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
    scripts: List[Tuple[str, str]],
    temp_dir: Path,
    voice: str = "en-US-ChristopherNeural",
) -> Dict[str, float]:
    """Pre-synthesizes all voice-over clips and calculates exact durations."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    durations: Dict[str, float] = {}

    async def generate():
        for filename, text in scripts:
            out_file = temp_dir / filename
            comm = edge_tts.Communicate(text, voice, rate="+6%")
            await comm.save(str(out_file))

    print(f"[*] Pre-synthesizing {len(scripts)} voice-over clips...")
    asyncio.run(generate())

    for filename, _ in scripts:
        clip_path = temp_dir / filename
        cmd = [ffmpeg, "-i", str(clip_path)]
        res = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )  # nosec B603
        duration = 5.0
        for line in res.stderr.splitlines():
            if "Duration:" in line:
                part = line.split("Duration:")[1].split(",")[0].strip()
                hh, mm, ss = part.split(":")
                duration = float(hh) * 3600 + float(mm) * 60 + float(ss)
                break
        durations[filename] = round(duration, 3)
        print(f"    - {filename}: {duration:.2f}s")

    return durations


def render_first_run_ui(
    page,
    comp_id: str,
    meta: Dict[str, Any],
    endpoints: List[Dict[str, str]],
) -> None:
    """Renders a realistic in-frame browser window showing the first-run UI."""
    first_endpoint, *rest_endpoints = endpoints
    name = meta.get("name", comp_id)
    primary_url = first_endpoint["url"]

    tabs_html = ""
    for idx, ep in enumerate(endpoints):
        active_cls = "bg-primary text-white" if idx == 0 else "bg-dark text-muted"
        tabs_html += (
            f'<button class="btn btn-sm {active_cls} me-2 font-monospace '
            f'px-3 py-1" id="ui-tab-{idx}">'
            f'<i class="fa-solid fa-globe me-1"></i>{ep["name"]} (:{ep["port"]})'
            f"</button>"
        )

    desc_text = meta.get("description", "Service running on your sovereign cloud.")[
        :160
    ]

    js_code = f"""() => {{
        const header = document.getElementById('wizard-header');
        if (header) {{
            header.innerHTML = (
                '<strong>Application Live: {name} First-Run Web UI</strong>'
            );
        }}
        const body = document.getElementById('wizard-body');
        if (body) {{
            body.innerHTML = `
                <div class="card shadow-lg border-0 mb-3" ` +
                `style="background:#0b1120; border-radius:12px; ` +
                `overflow:hidden;">
                    <div class="card-header bg-black py-2 px-3 d-flex ` +
                    `align-items-center justify-content-between ` +
                    `border-bottom border-secondary">
                        <div class="d-flex align-items-center gap-2">
                            <span style="width:12px; height:12px; ` +
                            `background:#ef4444; border-radius:50%; ` +
                            `display:inline-block;"></span>
                            <span style="width:12px; height:12px; ` +
                            `background:#f59e0b; border-radius:50%; ` +
                            `display:inline-block;"></span>
                            <span style="width:12px; height:12px; ` +
                            `background:#10b981; border-radius:50%; ` +
                            `display:inline-block;"></span>
                            <span class="badge bg-secondary font-monospace ` +
                            `ms-3 px-3 py-1 text-light" id="active-url-bar">
                                <i class="fa-solid fa-lock text-success me-1"></i>` +
                                `{primary_url}
                            </span>
                        </div>
                        <div class="d-flex align-items-center">
                            {tabs_html}
                            <span class="badge bg-success-subtle text-success ` +
                            `border border-success-subtle px-2 py-1 small">
                                <i class="fa-solid fa-circle-check me-1"></i>Live OK
                            </span>
                        </div>
                    </div>
                    <div class="card-body p-4 text-light" ` +
                    `style="background:#0f172a; min-height:460px;" ` +
                    `id="web-ui-viewport">
                        <div class="row align-items-center ` +
                        `justify-content-center py-4">
                            <div class="col-md-9 text-center">
                                <div class="mb-4">
                                    <div class="d-inline-flex p-3 ` +
                                    `rounded-circle mb-3" ` +
                                    `style="background:rgba(0,242,254,0.15); ` +
                                    `border:1px solid #00f2fe;">
                                        <i class="fa-solid fa-layer-group ` +
                                        `text-info fs-1"></i>
                                    </div>
                                    <h2 class="fw-bold text-white mb-2">` +
                                    `Welcome to {name}</h2>
                                    <p class="text-muted fs-6 mb-4">{desc_text}</p>
                                </div>
                                <div class="card p-4 mx-auto text-start shadow" ` +
                                `style="max-width: 520px; background:#1e293b; ` +
                                `border:1px solid rgba(255,255,255,0.1);">
                                    <h5 class="fw-bold text-white mb-3">` +
                                    `<i class="fa-solid fa-user-plus ` +
                                    `text-primary me-2"></i>Initial Setup</h5>
                                    <div class="mb-3">
                                        <label class="form-label small ` +
                                        `text-muted">Admin Account</label>
                                        <input type="text" class="form-control ` +
                                        `form-control-sm bg-dark text-white ` +
                                        `border-secondary" ` +
                                        `value="admin@{comp_id}.local" readonly>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label small ` +
                                        `text-muted">Cluster Node</label>
                                        <input type="text" class="form-control ` +
                                        `form-control-sm bg-dark text-white ` +
                                        `border-secondary" ` +
                                        `value="virtual-pi-5 (192.168.1.185)" readonly>
                                    </div>
                                    <div class="d-grid mt-4">
                                        <button class="btn btn-primary fw-bold" ` +
                                        `id="app-get-started-btn">
                                            <i class="fa-solid ` +
                                            `fa-arrow-right-to-bracket me-2"></i>` +
                                            `Enter {name} Dashboard
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }}
        window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}"""
    page.evaluate(js_code)


def record_walkthrough_video(
    component_id: str = "immich",
    voice: str = "en-US-ChristopherNeural",
    output_dir: Optional[Path] = None,
) -> None:
    """Orchestrates the entire 7-scene video walkthrough recording."""
    catalog = load_component_catalog()
    comps = catalog.get("components", {})
    if component_id not in comps:
        raise ValueError(
            f"Component '{component_id}' not found in components_metadata.json."
        )

    meta = comps[component_id]
    endpoints = resolve_component_endpoints(component_id, meta)
    narration_scripts = build_narration_scripts(component_id, meta, endpoints)

    video_dir = output_dir or (PROJECT_ROOT / "docs" / "videos")
    video_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = PROJECT_ROOT / "docs" / "images" / f"{component_id}_walkthrough"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    temp_audio_dir = Path(tempfile.mkdtemp(prefix="njord_video_tts_"))
    clip_durations = pregenerate_audio_clips(
        narration_scripts, temp_audio_dir, voice=voice
    )

    port = 5097
    print(f"[*] Starting background Configurator Flask server on port {port}...")
    start_flask_server(port=port)

    recorded_cues: List[Tuple[float, str, str]] = []
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

        # Intercept network scanner
        page.route(
            "**/scan-pis",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "hosts": [
                            {
                                "ip": "192.168.1.185",
                                "hostname": "virtual-pi-5",
                                "vendor": "Raspberry Pi (Proxmox KVM)",
                                "mac": "BC:24:11:9A:88:2E",
                            }
                        ],
                        "unresolved_hosts": [],
                    }
                ),
            ),
        )

        # Intercept device inspection
        page.route(
            "**/get-device-details",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "details": {
                            "model": ("Raspberry Pi 5 Model B (8GB RAM - Proxmox KVM)"),
                            "serial": "10000000e4b8c9d2",
                            "ram": "8.0 GB",
                            "disks": [
                                {
                                    "mounted_on": "/",
                                    "size": "64 GB",
                                    "pcent": "14%",
                                }
                            ],
                        }
                    }
                ),
            ),
        )

        # -------------------------------------------------------------
        # Scene 1: Network Auto-Discovery
        # -------------------------------------------------------------
        print("[*] Scene 1: Discovery Scan in Futuristic Dark...")
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
            pair = narration_scripts[scene_idx]
            fname, text = pair
            elapsed = round(max(0.0, time.time() - video_start_time + offset_sec), 2)
            recorded_cues.append((elapsed, text, fname))
            update_narration_subtitle(page, text)
            print(f"    [Cue {scene_idx+1}] @ {elapsed:.2f}s: {text[:45]}...")
            return clip_durations[fname]

        d1 = record_cue(0, offset_sec=0.2)
        page.screenshot(path=str(screenshot_dir / "scene_1_discovery_start.png"))
        wait_seconds(page, d1 + 1.2)

        move_cursor_and_click(page, "#begin-scan-btn", wait_after_sec=2.5)

        # -------------------------------------------------------------
        # Scene 2: Target Selection & Credentials
        # -------------------------------------------------------------
        print("[*] Scene 2: Target Node Found & Credentials Entry...")
        page.wait_for_selector(".device-card", timeout=8000)
        page.evaluate(
            """() => {
            const card = document.querySelector('.device-card');
            if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }"""
        )
        wait_seconds(page, 0.8)

        d2 = record_cue(1, offset_sec=0.2)
        scene2_start = time.time()

        move_cursor_and_click(
            page, ".device-card .form-check-input", wait_after_sec=1.0
        )
        page.evaluate(
            """() => {
            const card = document.querySelector('.device-card');
            if (card) card.classList.add('border-primary', 'shadow');
        }"""
        )
        move_cursor_to_input_and_type(page, ".device-username", "pi", delay_ms=120)
        move_cursor_to_input_and_type(
            page, ".device-password", "raspberry", delay_ms=120
        )

        page.screenshot(path=str(screenshot_dir / "scene_2_node_found_credentials.png"))
        s2_elapsed = time.time() - scene2_start
        s2_remaining = max(1.5, (d2 + 1.5) - s2_elapsed)
        wait_seconds(page, s2_remaining)

        # -------------------------------------------------------------
        # Scene 3: Hardware Verification
        # -------------------------------------------------------------
        print("[*] Scene 3: Inspect Hardware & Verify SSH...")
        move_cursor_and_click(page, "#get-details-btn", wait_after_sec=2.5)
        page.wait_for_selector("#proceed-to-step3-btn", timeout=8000)

        page.evaluate(
            """() => {
            const btn = document.getElementById('proceed-to-step3-btn');
            if (btn) btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }"""
        )
        wait_seconds(page, 0.8)

        d3 = record_cue(2, offset_sec=0.2)
        page.screenshot(path=str(screenshot_dir / "scene_3_hardware_verified.png"))
        wait_seconds(page, d3 + 2.0)

        # -------------------------------------------------------------
        # Scene 4: Catalog Navigation & Component Selection
        # -------------------------------------------------------------
        comp_name = str(meta.get("name", component_id))
        print(f"[*] Scene 4: Selecting {comp_name}...")
        move_cursor_and_click(page, "#proceed-to-step3-btn", wait_after_sec=2.0)
        page.wait_for_selector("#v-pills-tab", timeout=8000)

        d4 = record_cue(3, offset_sec=0.2)
        scene4_start = time.time()

        # Switch to component category if tab exists
        group_name = meta.get("group", "Utilities")
        grp_slug = group_name.lower()
        page.evaluate(
            f"""() => {{
            const tabs = Array.from(
                document.querySelectorAll('#v-pills-tab button')
            );
            const matchTab = tabs.find(
                b => b.textContent.toLowerCase().includes('{grp_slug}')
            );
            if (matchTab) matchTab.click();
        }}"""
        )
        wait_seconds(page, 1.2)

        # Select target component card
        comp_slug = comp_name.lower()
        page.evaluate(
            f"""() => {{
            const cards = Array.from(
                document.querySelectorAll('.component-card')
            );
            const targetCard = cards.find(
                c => c.textContent.toLowerCase().includes('{comp_slug}')
            ) || cards[0];
            const cursor = document.getElementById('njord-animated-cursor');
            if (targetCard) {{
                targetCard.scrollIntoView({{
                    behavior: 'smooth',
                    block: 'center'
                }});
                const btn = (
                    targetCard.querySelector('.btn-select-software') ||
                    targetCard.querySelector('button')
                );
                if (btn) {{
                    const rect = btn.getBoundingClientRect();
                    if (cursor) {{
                        cursor.style.left = `${{rect.left + rect.width / 2}}px`;
                        cursor.style.top = `${{rect.top + rect.height / 2}}px`;
                    }}
                    btn.click();
                }}
            }}
        }}"""
        )
        wait_seconds(page, 1.5)

        page.screenshot(
            path=str(screenshot_dir / f"scene_4_{component_id}_selected.png")
        )
        s4_elapsed = time.time() - scene4_start
        s4_remaining = max(1.5, (d4 + 2.0) - s4_elapsed)
        wait_seconds(page, s4_remaining)

        page.evaluate(
            f"""() => {{
            const btn = document.getElementById('proceed-to-step4-btn');
            if (btn) {{
                btn.innerHTML = (
                    '<i class="fa-solid fa-rocket me-2"></i>Deploy {comp_name}'
                );
            }}
        }}"""
        )
        move_cursor_and_click(page, "#proceed-to-step4-btn", wait_after_sec=2.0)

        # -------------------------------------------------------------
        # Scene 5: Live Streaming Deployment & Container Health
        # -------------------------------------------------------------
        print(f"[*] Scene 5: Live Deployment Streaming for {comp_name}...")
        page.evaluate(
            f"""() => {{
            const header = document.getElementById('wizard-header');
            if (header) {{
                header.innerHTML = (
                    '<strong>Step 4 of 4: Deploying {comp_name}</strong>'
                );
            }}
            const body = document.getElementById('wizard-body');
            if (body) {{
                body.innerHTML = `
                    <div class="text-start">
                        <div class="d-flex justify-content-between ` +
                        `align-items-center mb-3">
                            <h4 class="mb-0"><i class="fa-solid fa-rocket ` +
                            `text-primary me-2"></i>` +
                            `Deploying {comp_name}...</h4>
                            <span class="badge bg-primary fs-6" id="dep-badge">` +
                            `<i class="fa-solid fa-spinner fa-spin me-1"></i> ` +
                            `Provisioning Containers</span>
                        </div>
                        <div class="progress mb-4" style="height: 14px;">
                            <div class="progress-bar progress-bar-striped ` +
                            `progress-bar-animated bg-primary" id="prog-bar" ` +
                            `style="width: 25%;"></div>
                        </div>
                        <div class="card bg-dark text-light border-0 shadow mb-3">
                            <div class="card-header bg-black py-2 d-flex ` +
                            `justify-content-between align-items-center">
                                <span class="small text-muted ` +
                                `font-monospace">` +
                                `<i class="fa-solid fa-terminal ` +
                                `me-2 text-success"></i>` +
                                `Deployment Log: pi@192.168.1.185 ` +
                                `(Virtual Pi 5)</span>
                                <span class="badge bg-success small">` +
                                `Engine: Docker CE 27.1.1</span>
                            </div>
                            <div class="card-body p-3 font-monospace small" ` +
                            `id="stream-term" style="background-color: #0f172a; ` +
                            `min-height: 270px; color: #38bdf8;">
                                <div><span class="text-success">[OK]</span> ` +
                                `SSH connection established (pi@192.168.1.185)</div>
                            </div>
                        </div>
                    </div>
                `;
            }}
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}"""
        )
        init_custom_cursor(page)
        wait_seconds(page, 1.0)

        log_steps = [
            (
                45,
                '<span class="text-success">[OK]</span> '
                "Verified Docker Engine & Compose plugin active",
            ),
            (
                65,
                f'<span class="text-success">[OK]</span> '
                f"Synthesized Jinja2 Compose template for {comp_name}",
            ),
            (
                85,
                f'<span class="text-info">[PULL]</span> '
                f"Pulling container images for {comp_name}...",
            ),
            (
                95,
                '<span class="text-info">[RUN]</span> Starting '
                'container service -> <span class="text-success">Healthy</span>',
            ),
            (
                100,
                f'<span class="text-success">[OK]</span> '
                f"Healthchecks passed for {comp_name}",
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

        page.screenshot(path=str(screenshot_dir / "scene_5_live_deployment_stream.png"))
        d5 = record_cue(4, offset_sec=0.2)
        wait_seconds(page, d5 + 2.0)

        # -------------------------------------------------------------
        # Scene 6: Deployment Success & Web Access Cards
        # -------------------------------------------------------------
        print(f"[*] Scene 6: Success Screen & Web Access for {comp_name}...")
        cards_html = ""
        for idx, ep in enumerate(endpoints):
            btn_id = f"launch-btn-{idx}"
            cards_html += f"""
                <div class="col-md-6 mb-3">
                    <div class="card border-primary shadow p-3 text-start ` +
                    `h-100" style="background:#0f172a;">
                        <div class="d-flex align-items-center ` +
                        `justify-content-between mb-2">
                            <strong class="text-white"><i class="fa-solid ` +
                            `fa-globe text-primary me-2"></i>` +
                            `{ep['name']}</strong>
                            <span class="badge bg-success px-2 py-1">` +
                            `Active</span>
                        </div>
                        <p class="small text-muted mb-3 font-monospace">` +
                        `{ep['url']}</p>
                        <a href="{ep['url']}" class="btn btn-primary btn-sm ` +
                        `font-monospace w-100 launch-action-btn" ` +
                        `id="{btn_id}" onclick="return false;">
                            <i class="fa-solid fa-arrow-up-right-from-square ` +
                            `me-1"></i> Open {ep['name']}
                        </a>
                    </div>
                </div>
            """

        page.evaluate(
            f"""() => {{
            const header = document.getElementById('wizard-header');
            if (header) {{
                header.innerHTML = (
                    '<strong>Step 4 of 4: Deployment Complete</strong>'
                );
            }}
            const body = document.getElementById('wizard-body');
            if (body) {{
                body.innerHTML = `
                    <div class="text-center py-3">
                        <div class="display-4 text-success mb-2">` +
                        `<i class="fa-solid fa-circle-check"></i></div>
                        <h2 class="fw-bold mb-2">` +
                        `{comp_name} Deployed Successfully!</h2>
                        <p class="text-muted mb-4 fs-5">` +
                        `Your sovereign application is verified and running ` +
                        `on your Virtual Pi.</p>
                        <div class="row justify-content-center mb-4">
                            {cards_html}
                        </div>
                        <div class="d-flex justify-content-center gap-3">
                            <span class="badge bg-success-subtle text-success ` +
                            `border border-success p-2 fs-6">
                                <i class="fa-solid fa-heart-pulse me-1"></i> ` +
                                `Containers Healthy
                            </span>
                            <span class="badge bg-primary-subtle text-primary ` +
                            `border border-primary p-2 fs-6">
                                <i class="fa-solid fa-shield-halved me-1"></i> ` +
                                `Zero Target Dependencies
                            </span>
                        </div>
                    </div>
                `;
            }}
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}"""
        )
        init_custom_cursor(page)

        d6 = record_cue(5, offset_sec=0.2)
        page.screenshot(path=str(screenshot_dir / "scene_6_success_web_access.png"))

        # Move cursor over primary launch button and pulse
        page.evaluate(
            """() => {
            const btn = document.querySelector('.launch-action-btn');
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
        wait_seconds(page, d6 + 1.5)

        # -------------------------------------------------------------
        # Scene 7: First-Run Web UI Onboarding & Verification
        # -------------------------------------------------------------
        print(f"[*] Scene 7: First-Run Web UI for {comp_name}...")
        render_first_run_ui(page, component_id, meta, endpoints)
        init_custom_cursor(page)

        d7 = record_cue(6, offset_sec=0.2)
        page.screenshot(path=str(screenshot_dir / "scene_7_first_run_web_ui.png"))

        # If multi-UI, demonstrate clicking secondary tab
        if len(endpoints) > 1:
            first_ep, second_ep, *remaining_eps = endpoints
            wait_seconds(page, 2.0)
            page.evaluate(
                f"""() => {{
                const secTab = document.getElementById('ui-tab-1');
                const cursor = document.getElementById('njord-animated-cursor');
                if (secTab && cursor) {{
                    const rect = secTab.getBoundingClientRect();
                    cursor.style.left = `${{rect.left + rect.width / 2}}px`;
                    cursor.style.top = `${{rect.top + rect.height / 2}}px`;
                    secTab.classList.remove('bg-dark', 'text-muted');
                    secTab.classList.add('bg-info', 'text-dark');
                    const urlBar = document.getElementById('active-url-bar');
                    if (urlBar) {{
                        urlBar.innerHTML = (
                            '<i class="fa-solid fa-lock text-success me-1"></i>' +
                            '{second_ep["url"]}'
                        );
                    }}
                }}
            }}"""
            )

        # Hold on first-run UI for remainder of speech + outro
        wait_seconds(page, d7 + 3.0)

        # Finalize video capture
        if page.video is None:
            raise RuntimeError("Playwright video recording was not initialized.")
        raw_video_path = Path(page.video.path())
        page.close()
        context.close()
        browser.close()

    # Mux audio and generate subtitles
    mux_audio_tracks(
        component_id,
        raw_video_path,
        video_dir,
        temp_audio_dir,
        recorded_cues,
        clip_durations,
    )
    print(
        f"[+] Done recording calm 7-scene deployment walkthrough for "
        f"{component_id}!"
    )


def mux_audio_tracks(
    comp_id: str,
    raw_video_path: Path,
    video_dir: Path,
    temp_audio_dir: Path,
    recorded_cues: List[Tuple[float, str, str]],
    clip_durations: Dict[str, float],
) -> None:
    """Muxes audio tracks at exact recorded timestamps and generates subtitles."""
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

    vtt_lines = [f"WEBVTT - {comp_id.title()} Deployment Walkthrough\n"]
    srt_lines = []
    for idx, (start_sec, text, filename) in enumerate(recorded_cues, 1):
        end_sec = start_sec + clip_durations.get(filename, 6.0) + 0.3
        vtt_lines.append(
            f"{idx}\n{fmt_vtt(start_sec)} --> {fmt_vtt(end_sec)}\n{text}\n"
        )
        srt_lines.append(
            f"{idx}\n{fmt_srt(start_sec)} --> {fmt_srt(end_sec)}\n{text}\n"
        )

    base_name = f"{comp_id}-virtual-pi-deployment"
    (video_dir / f"{base_name}.en.vtt").write_text(
        "\n".join(vtt_lines), encoding="utf-8"
    )
    (video_dir / f"{base_name}.en.srt").write_text(
        "\n".join(srt_lines), encoding="utf-8"
    )
    print(f"[+] Generated subtitles: {base_name}.en.vtt & {base_name}.en.srt")

    # Build audio filter
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

    # Output MP4
    mp4_target = video_dir / f"{base_name}.mp4"
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
    print(f"[+] Saved MP4: {mp4_target} ({mp4_size_mb:.2f} MB)")

    # Output WebM
    webm_target = video_dir / f"{base_name}.webm"
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
    print(f"[+] Saved WebM: {webm_target} ({webm_size_mb:.2f} MB)")

    # Cleanup temp resources
    shutil.rmtree(temp_audio_dir, ignore_errors=True)
    if raw_video_path.exists() and raw_video_path != webm_target:
        # noinspection PyBroadException
        try:
            raw_video_path.unlink()
        except OSError:
            pass


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generic Video Walkthrough Generator for NjordDeploy Components"
    )
    parser.add_argument(
        "--component",
        default="immich",
        help=(
            "Component ID from components_metadata.json "
            "(e.g. immich, nextcloud, adguard-home)"
        ),
    )
    parser.add_argument(
        "--voice",
        default="en-US-ChristopherNeural",
        help="Edge-TTS voice name (default: en-US-ChristopherNeural)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom output directory for generated video and subtitles",
    )
    args = parser.parse_args()

    out_p = Path(args.output_dir) if args.output_dir else None
    record_walkthrough_video(
        component_id=args.component,
        voice=args.voice,
        output_dir=out_p,
    )


if __name__ == "__main__":
    main()
