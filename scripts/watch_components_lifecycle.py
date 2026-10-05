#!/usr/bin/env python3
# scripts/watch_components_lifecycle.py
"""NjordDeploy Upstream Lifecycle Watcher & Wachtkamer Manager.

------------------------------------------------------------
Monitors upstream GitHub releases (via RSS Atom feeds) for components in
config/components_metadata.json.

Features:
1. Detects new upstream versions without heavy API rate limits.
2. Prioritizes Security & Critical Gateway Infrastructure (Caddy, Traefik, etc.).
3. Identifies HTTP redirects (repository moves / renames).
4. Identifies stale or deprecated/abandoned repositories (> 365 days without releases).
5. Places newly discovered candidate versions into 'staging' (the Wachtkamer).
6. Sends prioritized notifications via Signal Messenger REST API.
7. Keeps docker-compose template headers synchronized upon promotion.
8. Provides CLI commands to inspect and manage the Wachtkamer:
   - Check:   python scripts/watch_components_lifecycle.py --check
   - Status:  python scripts/watch_components_lifecycle.py --wachtkamer
   - Promote: python scripts/watch_components_lifecycle.py --promote <comp_id>
   - Reject:  python scripts/watch_components_lifecycle.py --reject <comp_id>

Usage:
    python scripts/watch_components_lifecycle.py --check --signal
    python scripts/watch_components_lifecycle.py --wachtkamer
    python scripts/watch_components_lifecycle.py --promote caddy
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CATALOG_METADATA_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "components_metadata.json"
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "component_templates"

# Signal API settings (aligned with audit_supply_chain.py and .env)
SIGNAL_API_URL = os.environ.get(
    "SIGNAL_API_URL", "http://192.168.178.118:8090/v2/send"
)
SIGNAL_SENDER = os.environ.get("SIGNAL_SENDER", "+31651107603")
SIGNAL_RECIPIENT = os.environ.get("SIGNAL_RECIPIENT", "+31651107603")

# Atom namespace
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# Security & Critical Gateway Infrastructure classification
SECURITY_GROUPS = {"reverse_proxy", "dns_blocker", "Security & Utilities"}
SECURITY_TAGS = {
    "security",
    "vpn",
    "ssl",
    "reverse-proxy",
    "dns",
    "firewall",
    "auth",
}
SECURITY_COMPONENTS = {
    "caddy",
    "traefik",
    "nginx-proxy-manager",
    "vaultwarden",
    "wg-easy",
    "pi-hole",
    "adguard-home",
    "unbound",
    "technitium-dns",
    "authentik",
    "authelia",
    "crowdsec",
}


def is_security_component(comp_id: str, comp_data: Dict[str, Any]) -> bool:
    """Identifies if a component is security-critical or network gateway."""
    if comp_id in SECURITY_COMPONENTS:
        return True
    if comp_data.get("group") in SECURITY_GROUPS:
        return True
    tags = set(comp_data.get("tags") or [])
    if tags.intersection(SECURITY_TAGS):
        return True
    return False


def send_signal_message(message: str) -> bool:
    """Sends a notification via Signal REST API."""
    if not (SIGNAL_API_URL and SIGNAL_SENDER and SIGNAL_RECIPIENT):
        return False
    try:
        payload = json.dumps(
            {
                "message": message,
                "number": SIGNAL_SENDER,
                "recipients": [SIGNAL_RECIPIENT],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            SIGNAL_API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status in (200, 201)
    except Exception as exc:
        print(f"Signal notification failed: {exc}", file=sys.stderr)
        return False


def sync_to_sysopswatch() -> None:
    """Syncs components_metadata.json to SysOpsWatch LXC container if reachable."""
    host = os.environ.get("SYSOPSWATCH_HOST", "192.168.178.70")
    dest_dir = os.environ.get("SYSOPSWATCH_DIR", "/opt/njordwatch")
    try:
        import subprocess

        cmd = [
            "scp",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=3",
            "-o",
            "BatchMode=yes",
            str(CATALOG_METADATA_PATH),
            f"root@{host}:{dest_dir}/components_metadata.json",
        ]
        res = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
        )
        if res.returncode == 0:
            print("  Gesynchroniseerd naar SysOpsWatch (192.168.178.70).")
    except Exception:
        pass


PRERELEASE_PATTERN = re.compile(
    r"-(rc|alpha|beta|b\.|dev|preview|canary|pre|nightly)", re.I
)
IGNORED_TAGS = {"stable", "latest", "master", "main", "nightly", "edge"}


def is_prerelease_or_invalid(tag: str) -> bool:
    """Checks whether a tag is a pre-release, alpha, beta, rc, or non-version string."""
    clean = tag.strip().lower()
    if clean in IGNORED_TAGS:
        return True
    if PRERELEASE_PATTERN.search(clean):
        return True
    if not re.search(r"\d", clean):
        return True
    return False


def parse_semver(s: str) -> Optional[Tuple[int, ...]]:
    """Extracts numeric sequence from version string for comparative sorting."""
    clean = clean_tag_version(s)
    parts = re.findall(r"\d+", clean)
    if parts:
        return tuple(int(p) for p in parts[:4])
    return None


def is_newer_version(current: str, candidate: str) -> bool:
    """Determines if candidate is strictly newer than current version."""
    curr_clean = clean_tag_version(current)
    cand_clean = clean_tag_version(candidate)
    if not cand_clean or cand_clean == curr_clean:
        return False
    if is_prerelease_or_invalid(cand_clean):
        return False

    t_curr = parse_semver(curr_clean)
    t_cand = parse_semver(cand_clean)

    if t_curr and t_cand:
        # Strictly greater numeric progression
        return t_cand > t_curr

    return False


def clean_tag_version(tag: str) -> str:
    """Strips leading 'v', release prefixes, or builds from tags."""
    clean = tag.strip()
    match = re.search(r"(\d+(\.\d+)+(-[a-zA-Z0-9\._]+)?)", clean)
    if match:
        return match.group(1)
    return clean.lstrip("vV")


def fetch_atom_feed(
    rss_url: str,
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Fetches the Atom feed, handles redirects, and returns content."""
    req = urllib.request.Request(
        rss_url,
        headers={"User-Agent": "NjordDeploy-LifecycleWatcher/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            final_url = response.geturl()
            content = response.read().decode("utf-8")
            return content, response.status, final_url
    except urllib.error.HTTPError as exc:
        return None, exc.code, None
    except Exception:
        return None, None, None


def parse_latest_release(xml_content: str) -> Optional[Dict[str, Any]]:
    """Parses Atom XML and extracts the latest STABLE GA release entry."""
    try:
        root = ET.fromstring(xml_content)
        entries = root.findall("atom:entry", ATOM_NS)
        if not entries:
            return None

        for entry in entries:
            title_el = entry.find("atom:title", ATOM_NS)
            updated_el = entry.find("atom:updated", ATOM_NS)
            id_el = entry.find("atom:id", ATOM_NS)
            link_el = entry.find("atom:link", ATOM_NS)

            title = title_el.text if title_el is not None and title_el.text else ""
            updated_str = (
                updated_el.text if updated_el is not None and updated_el.text else ""
            )
            link = link_el.attrib.get("href", "") if link_el is not None else ""

            # Extract tag name from id or title
            tag = title.split(":")[0].strip()
            if id_el is not None and id_el.text and "/" in id_el.text:
                tag = id_el.text.split("/")[-1]

            # Filter out pre-releases, alphas, betas, RCs, and branch names
            if is_prerelease_or_invalid(tag):
                continue

            clean_ver = clean_tag_version(tag)
            if not clean_ver or is_prerelease_or_invalid(clean_ver):
                continue

            return {
                "raw_tag": tag,
                "version": clean_ver,
                "title": title,
                "updated": updated_str,
                "url": link,
            }
        return None
    except Exception:
        return None


def run_lifecycle_check(send_signal: bool = False) -> None:
    """Inspects all components, checks Atom feeds, and updates staging."""
    if not CATALOG_METADATA_PATH.exists():
        print(f"Error: Catalog not found at {CATALOG_METADATA_PATH}", file=sys.stderr)
        return

    with open(CATALOG_METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    components = data.get("components", {})
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)

    security_updates: List[Tuple[str, str, str, str]] = []
    standard_updates: List[Tuple[str, str, str, str]] = []
    redirects_found: List[Tuple[str, Optional[str], str]] = []
    stale_found: List[Tuple[str, int]] = []

    print(f"Scanning upstream releases for {len(components)} components...\n")

    for comp_id, comp in components.items():
        upstream = comp.get("upstream", {})
        rss_url = upstream.get("rss_feed")
        if not rss_url:
            continue

        xml_content, status_code, final_url = fetch_atom_feed(rss_url)

        if status_code == 404:
            print(f"⚠️  [{comp_id}] Upstream 404 Not Found: {rss_url}")
            upstream["is_deprecated"] = True
            upstream["deprecation_note"] = (
                "Upstream GitHub repository returned HTTP 404."
            )
            continue

        if not xml_content:
            continue

        # Check for repo rename / redirect
        if final_url and final_url != rss_url and "releases.atom" in final_url:
            new_repo_match = re.search(
                r"github\.com/([^/]+/[^/]+)/releases\.atom", final_url
            )
            if new_repo_match:
                new_repo = new_repo_match.group(1)
                if new_repo != upstream.get("github_repo"):
                    print(
                        f"🔄 [{comp_id}] Repo moved: "
                        f"{upstream.get('github_repo')} -> {new_repo}"
                    )
                    redirects_found.append(
                        (comp_id, upstream.get("github_repo"), new_repo)
                    )
                    upstream["github_repo"] = new_repo
                    upstream["rss_feed"] = final_url

        latest = parse_latest_release(xml_content)
        if not latest:
            continue

        upstream["last_upstream_check"] = now_iso
        upstream["latest_upstream_version"] = latest["version"]

        # Check for stale / unmaintained repository (> 365 days)
        if latest["updated"]:
            try:
                rel_dt = datetime.fromisoformat(
                    latest["updated"].replace("Z", "+00:00")
                )
                days_old = (now_dt - rel_dt).days
                if days_old > 365 and not upstream.get("is_deprecated"):
                    upstream["is_deprecated"] = True
                    upstream["deprecation_note"] = (
                        f"No releases for {days_old} days (stale/unmaintained)."
                    )
                    stale_found.append((comp_id, days_old))
            except Exception:
                pass

        # Compare with last_tested_version or active version
        current_tested = comp.get("last_tested_version") or comp.get(
            "component_version", ""
        )
        current_clean = clean_tag_version(current_tested)
        latest_clean = latest["version"]

        is_sec = is_security_component(comp_id, comp)
        staging = comp.get("staging", {})

        # Self-heal: purge pre-releases or non-progressive ghost candidates
        curr_cand = staging.get("candidate_version")
        if curr_cand:
            if is_prerelease_or_invalid(curr_cand) or not is_newer_version(
                current_clean, curr_cand
            ):
                staging["candidate_version"] = None
                staging["status"] = "idle"
                staging["entered_staging_at"] = None

        # Check if component is pinned or version was explicitly ignored
        if comp.get("pinned", False):
            continue

        ignored = staging.get("ignored_versions", [])
        if latest_clean in ignored:
            continue

        if latest_clean and is_newer_version(current_clean, latest_clean):
            # Is this already in staging?
            if staging.get("candidate_version") != latest_clean:
                staging["candidate_version"] = latest_clean
                staging["status"] = "awaiting_approval"
                staging["entered_staging_at"] = now_iso
                if is_sec:
                    security_updates.append(
                        (comp_id, current_clean, latest_clean, latest["url"])
                    )
                    print(
                        f"🚨 [{comp_id}] SECURITY UPDATE: {current_clean} -> "
                        f"{latest_clean} (moved to wachtkamer)"
                    )
                else:
                    standard_updates.append(
                        (comp_id, current_clean, latest_clean, latest["url"])
                    )
                    print(
                        f"✨ [{comp_id}] New version: {current_clean} -> "
                        f"{latest_clean} (moved to wachtkamer)"
                    )

    # Save updated metadata
    with open(CATALOG_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    sync_to_sysopswatch()

    total_updates = len(security_updates) + len(standard_updates)
    print("\n" + "=" * 60)
    print("Upstream Lifecycle Scan Summary:")
    print(f"  Security & Gateway candidates:            {len(security_updates)}")
    print(f"  Standard candidates placed in wachtkamer: {len(standard_updates)}")
    print(f"  Total update candidates:                  {total_updates}")
    print(f"  Repositories redirected / renamed:        {len(redirects_found)}")
    print(f"  Stale / deprecated components flagged:    {len(stale_found)}")
    print("=" * 60)

    # Signal Alerting
    if send_signal and (total_updates or stale_found or redirects_found):
        msg_lines = ["🛡️ **NjordDeploy Upstream Lifecycle Alert**\n"]

        if security_updates:
            msg_lines.append("🚨 **PRIORITEIT: SECURITY & INFRASTRUCTUUR UPDATES:**")
            for cid, old_v, new_v, _ in security_updates:
                msg_lines.append(
                    f" • `{cid}`: {old_v} ➔ **{new_v}** ⚠️ (Direct verifiëren)"
                )
            msg_lines.append("")

        if standard_updates:
            msg_lines.append(
                f"📦 **Nieuwe releases in Wachtkamer ({len(standard_updates)}):**"
            )
            for cid, old_v, new_v, _ in standard_updates[:8]:
                msg_lines.append(f" • `{cid}`: {old_v} ➔ **{new_v}**")
            if len(standard_updates) > 8:
                rem = len(standard_updates) - 8
                msg_lines.append(f" *(en nog {rem} andere standaard tools...)*")

        msg_lines.append(
            "\nBeheer de wachtkamer met: "
            "`python scripts/watch_components_lifecycle.py --wachtkamer`"
        )

        if stale_found:
            msg_lines.append(f"\n⚠️ **Verouderd / Inactief ({len(stale_found)}):**")
            for cid, days in stale_found[:5]:
                msg_lines.append(f" • `{cid}`: al {days} dagen geen release")

        full_msg = "\n".join(msg_lines)
        if send_signal_message(full_msg):
            print("Signal notification sent successfully.")


def show_wachtkamer() -> None:
    """Lists all candidate versions currently residing in staging (de Wachtkamer)."""
    with open(CATALOG_METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    comps = data.get("components", {})
    candidates = []

    for comp_id, comp in comps.items():
        staging = comp.get("staging", {})
        cand_ver = staging.get("candidate_version")
        status = staging.get("status")
        if cand_ver and status in ("awaiting_approval", "testing"):
            track_info = comp.get("release_track", {}).get("track", "standard")
            curr_ver = comp.get("last_tested_version") or comp.get(
                "component_version", "unknown"
            )
            is_sec = is_security_component(comp_id, comp)
            candidates.append(
                {
                    "id": comp_id,
                    "name": comp.get("name", comp_id),
                    "track": track_info,
                    "current": curr_ver,
                    "candidate": cand_ver,
                    "status": status,
                    "is_security": is_sec,
                    "entered_at": staging.get("entered_staging_at", "unknown"),
                }
            )

    print("=" * 80)
    print(f"🚪 NJORDDEPLOY WACHTKAMER (Staging Candidates: {len(candidates)})")
    print("=" * 80)
    if not candidates:
        print("Geen componenten in de wachtkamer. Alle services zijn up-to-date!")
        print("=" * 80)
        return

    # Sort security infrastructure candidates first, then alphabetical
    candidates.sort(key=lambda x: (not x["is_security"], x["id"]))

    header = (
        f"{'TYPE':<6} {'COMPONENT':<22} {'TRACK':<10} "
        f"{'HUIDIG':<14} {'KANDIDAAT':<14} {'STATUS'}"
    )
    print(header)
    print("-" * 80)
    for c in candidates:
        badge = "🚨 SEC" if c["is_security"] else "📦 STD"
        row = (
            f"{badge:<6} {c['id']:<22} {c['track']:<10} "
            f"{c['current']:<14} {c['candidate']:<14} {c['status']}"
        )
        print(row)
    print("-" * 80)
    print("Acties:")
    print("  Goedkeuren: python scripts/watch_components_lifecycle.py --promote <id>")
    print("  Afwijzen:   python scripts/watch_components_lifecycle.py --reject <id>")
    print("=" * 80)


def promote_candidate(comp_id: str) -> None:
    """Promotes candidate to production version and syncs template."""
    with open(CATALOG_METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    comps = data.get("components", {})
    if comp_id not in comps:
        print(
            f"Fout: Component '{comp_id}' niet gevonden in catalogus.",
            file=sys.stderr,
        )
        return

    comp = comps[comp_id]
    staging = comp.get("staging", {})
    candidate = staging.get("candidate_version")

    if not candidate:
        print(
            f"Component '{comp_id}' heeft geen kandidaat in de wachtkamer.",
            file=sys.stderr,
        )
        return

    old_ver = comp.get("last_tested_version")
    comp["last_tested_version"] = candidate
    comp["last_tested"] = datetime.now(timezone.utc).isoformat()
    comp["test_status"] = "tested"

    # Reset staging
    staging["candidate_version"] = None
    staging["status"] = "idle"
    staging["entered_staging_at"] = None

    with open(CATALOG_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    sync_to_sysopswatch()

    # Sync docker-compose.template.yml header if template exists
    tpl_path = TEMPLATES_DIR / comp_id / "docker-compose.template.yml"
    if tpl_path.exists():
        try:
            content = tpl_path.read_text(encoding="utf-8")
            if "last_tested_version:" in content:
                updated_content = re.sub(
                    r'(#\s*last_tested_version:\s*)["\']?[^"\'\n]+["\']?',
                    f'\\1"{candidate}"',
                    content,
                )
                tpl_path.write_text(updated_content, encoding="utf-8")
                print(f"  Template header bijgewerkt in {tpl_path.name}")
        except Exception as exc:
            print(
                f"Waarschuwing: Kon template header niet bijwerken: {exc}",
                file=sys.stderr,
            )

    print(f"✅ GEPROMOVEERD: '{comp_id}' bijgewerkt van {old_ver} naar {candidate}!")
    print(
        "Tip: Voer nu 'python scripts/sync_components_repo.py --commit' "
        "uit om naar de repo te pushen."
    )


def reject_candidate(comp_id: str) -> None:
    """Rejects a candidate version, remembering it in ignored_versions."""
    with open(CATALOG_METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    comps = data.get("components", {})
    if comp_id not in comps:
        print(
            f"Fout: Component '{comp_id}' niet gevonden in catalogus.",
            file=sys.stderr,
        )
        return

    staging = comps[comp_id].get("staging", {})
    rejected_ver = staging.get("candidate_version")

    staging["candidate_version"] = None
    staging["status"] = "idle"
    staging["test_result"] = f"Rejected candidate {rejected_ver}"
    staging["entered_staging_at"] = None

    # Memory against Groundhog Day loop
    if rejected_ver:
        if "ignored_versions" not in staging or not isinstance(
            staging["ignored_versions"], list
        ):
            staging["ignored_versions"] = []
        if rejected_ver not in staging["ignored_versions"]:
            staging["ignored_versions"].append(rejected_ver)

    with open(CATALOG_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    sync_to_sysopswatch()

    print(
        f"❌ AFGEWEZEN: Kandidaat '{rejected_ver}' voor '{comp_id}' "
        "is verwijderd en toegevoegd aan ignored_versions."
    )


def pin_component(comp_id: str) -> None:
    """Pins a component so it will not enter the wachtkamer for upstream updates."""
    with open(CATALOG_METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    comps = data.get("components", {})
    if comp_id not in comps:
        print(
            f"Fout: Component '{comp_id}' niet gevonden in catalogus.",
            file=sys.stderr,
        )
        return

    comps[comp_id]["pinned"] = True
    staging = comps[comp_id].setdefault("staging", {})
    staging["status"] = "pinned"
    staging["candidate_version"] = None

    with open(CATALOG_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    sync_to_sysopswatch()
    print(f"📌 VASTGEZET: '{comp_id}' is vastgezet (pinned).")


def unpin_component(comp_id: str) -> None:
    """Unpins a component allowing lifecycle updates."""
    with open(CATALOG_METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    comps = data.get("components", {})
    if comp_id not in comps:
        print(
            f"Fout: Component '{comp_id}' niet gevonden in catalogus.",
            file=sys.stderr,
        )
        return

    comps[comp_id]["pinned"] = False
    staging = comps[comp_id].setdefault("staging", {})
    if staging.get("status") == "pinned":
        staging["status"] = "idle"

    with open(CATALOG_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    sync_to_sysopswatch()
    print(f"🔓 VRIJGEGEVEN: '{comp_id}' is niet meer vastgezet (unpinned).")


def main():
    parser = argparse.ArgumentParser(
        description="NjordDeploy Upstream Lifecycle Watcher & Wachtkamer Manager"
    )
    parser.add_argument(
        "--check", action="store_true", help="Scan upstream feeds for new releases."
    )
    parser.add_argument(
        "--signal", action="store_true", help="Send Signal alerts if updates found."
    )
    parser.add_argument(
        "--wachtkamer",
        action="store_true",
        help="Display all candidate versions in staging.",
    )
    parser.add_argument(
        "--promote",
        type=str,
        metavar="COMPONENT_ID",
        help="Promote candidate to production.",
    )
    parser.add_argument(
        "--reject",
        type=str,
        metavar="COMPONENT_ID",
        help="Reject and clear candidate.",
    )
    parser.add_argument(
        "--pin",
        type=str,
        metavar="COMPONENT_ID",
        help="Pin a component to freeze updates.",
    )
    parser.add_argument(
        "--unpin",
        type=str,
        metavar="COMPONENT_ID",
        help="Unpin a component to resume updates.",
    )

    args = parser.parse_args()

    if args.promote:
        promote_candidate(args.promote)
    elif args.reject:
        reject_candidate(args.reject)
    elif args.pin:
        pin_component(args.pin)
    elif args.unpin:
        unpin_component(args.unpin)
    elif args.wachtkamer:
        show_wachtkamer()
    elif args.check:
        run_lifecycle_check(send_signal=args.signal)
    else:
        # Default action: show wachtkamer status
        show_wachtkamer()


if __name__ == "__main__":
    main()
