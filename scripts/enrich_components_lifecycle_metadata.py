#!/usr/bin/env python3
# scripts/enrich_components_lifecycle_metadata.py
"""
Enriches catalog components with lifecycle, release track (LTS/Feature/Standard),
upstream sources (GitHub/RSS/Registry), and staging/wachtkamer metadata.

Safely outputs to a test/staging file by default to allow side-by-side comparison
before applying to the production metadata file.

Usage:
    # Run test run writing to config/components_metadata_lifecycle_preview.json:
    python scripts/enrich_components_lifecycle_metadata.py --preview

    # Run dry-run without writing any files:
    python scripts/enrich_components_lifecycle_metadata.py --dry-run

    # Apply directly to config/components_metadata.json (creates .bak backup):
    python scripts/enrich_components_lifecycle_metadata.py --apply
"""

import argparse
import json
import shutil
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

CATALOG_METADATA_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "components_metadata.json"
)
PREVIEW_OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "components_metadata_lifecycle_preview.json"
)

# Known LTS software patterns or identifiers
KNOWN_LTS_PATTERNS = {
    "postgres": {"track": "lts", "otap_role": "production", "lts_identifier": "16"},
    "mariadb": {"track": "lts", "otap_role": "production", "lts_identifier": "10.11"},
    "nodejs": {"track": "lts", "otap_role": "production", "lts_identifier": "20"},
    "ubuntu": {"track": "lts", "otap_role": "production", "lts_identifier": "24.04"},
    "redis": {"track": "lts", "otap_role": "production", "lts_identifier": "7"},
}

# Known upstream mappings where image name or docs don't match GitHub repo directly
KNOWN_UPSTREAM_REPOS = {
    "actual-budget": "actualbudget/actual-server",
    "adguard-home": "AdguardTeam/AdGuardHome",
    "audiobookshelf": "advplyr/audiobookshelf",
    "caddy": "caddyserver/caddy",
    "conduit": "famedly/conduit",
    "filebrowser": "filebrowser/filebrowser",
    "frigate": "blakeblackshear/frigate",
    "gluetun": "qdm12/gluetun",
    "grafana": "grafana/grafana",
    "heimdall": "linuxserver/docker-heimdall",
    "homarr": "ajnart/homarr",
    "homeassistant": "home-assistant/core",
    "homepage": "gethomepage/homepage",
    "homer": "bastienwirtz/homer",
    "immich": "immich-app/immich",
    "jellyfin": "jellyfin/jellyfin",
    "litellm": "BerriAI/litellm",
    "microbin": "szabodanika/microbin",
    "n8n": "n8n-io/n8n",
    "nextcloud": "nextcloud/server",
    "nginx-proxy-manager": "NginxProxyManager/nginx-proxy-manager",
    "octoprint": "OctoPrint/OctoPrint",
    "ollama": "ollama/ollama",
    "open-webui": "open-webui/open-webui",
    "pi-hole": "pi-hole/pi-hole",
    "portainer": "portainer/portainer",
    "prowlarr": "Prowlarr/Prowlarr",
    "qbittorrent": "linuxserver/docker-qbittorrent",
    "radarr": "Radarr/Radarr",
    "sabnzbd": "sabnzbd/sabnzbd",
    "scrypted": "koush/scrypted",
    "semaphore": "semaphoreui/semaphore",
    "sonarr": "Sonarr/Sonarr",
    "stirling-pdf": "Stirling-Tools/Stirling-PDF",
    "traefik": "traefik/traefik",
    "umami": "umami-software/umami",
    "uptime-kuma": "louislam/uptime-kuma",
    "vaultwarden": "dani-garcia/vaultwarden",
    "zigbee2mqtt": "Koenkk/zigbee2mqtt",
}


def detect_github_repo(comp_id: str, comp_data: Dict[str, Any]) -> Optional[str]:
    """Detects GitHub repository slug using known mappings or heuristics."""
    if comp_id in KNOWN_UPSTREAM_REPOS:
        return KNOWN_UPSTREAM_REPOS[comp_id]

    # Check project_url or doc_url
    for url_key in ["project_url", "doc_url"]:
        val = comp_data.get(url_key)
        if isinstance(val, str) and val.strip():
            parsed = urllib.parse.urlparse(val)
            if parsed.netloc in ("github.com", "www.github.com"):
                path_parts = [p for p in parsed.path.strip("/").split("/") if p]
                if len(path_parts) >= 2:
                    owner, repo = path_parts[0], path_parts[1].rstrip(".git")
                    return f"{owner}/{repo}"

    # Check first_run_info doc_url
    first_run = comp_data.get("first_run_info", {})
    if isinstance(first_run, dict):
        doc_url = first_run.get("doc_url")
        if isinstance(doc_url, str) and doc_url.strip():
            parsed = urllib.parse.urlparse(doc_url)
            if parsed.netloc in ("github.com", "www.github.com"):
                path_parts = [p for p in parsed.path.strip("/").split("/") if p]
                if len(path_parts) >= 2:
                    owner, repo = path_parts[0], path_parts[1].rstrip(".git")
                    return f"{owner}/{repo}"

    # Check image_name
    img = comp_data.get("image_name", "")
    if isinstance(img, str) and img:
        img_clean = img.split(":")[0]
        if "/" in img_clean:
            parts = img_clean.split("/")
            if (
                len(parts) == 2
                and not parts[0].endswith(".io")
                and not parts[0].endswith(".com")
            ):
                # Docker Hub standard owner/image
                return f"{parts[0]}/{parts[1]}"
            elif len(parts) >= 3 and parts[0] == "ghcr.io":
                return f"{parts[1]}/{parts[2]}"

    return None


def detect_registry_type(image_name: Optional[str]) -> str:
    """Determines registry type (dockerhub, ghcr, quay, etc.)."""
    if not image_name:
        return "dockerhub"
    parts = image_name.lower().strip().split("/")
    domain = parts[0] if len(parts) > 1 else ""
    if domain == "ghcr.io":
        return "ghcr"
    if domain == "quay.io":
        return "quay"
    if domain == "gcr.io" or domain.endswith(".pkg.dev"):
        return "gcr"
    return "dockerhub"


def detect_release_track(comp_id: str, comp_data: Dict[str, Any]) -> Dict[str, Any]:
    """Determines if the component fits an LTS, feature, or standard rolling track."""
    for pattern, cfg in KNOWN_LTS_PATTERNS.items():
        if pattern in comp_id:
            return {
                "track": cfg["track"],
                "otap_role": cfg["otap_role"],
                "lts_identifier": cfg["lts_identifier"],
            }

    # Default to standard track
    return {
        "track": "standard",
        "otap_role": "production",
        "lts_identifier": None,
    }


def build_lifecycle_metadata(comp_id: str, comp_data: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs release_track, upstream, and staging dictionaries."""
    img_name = comp_data.get("image_name")
    gh_repo = detect_github_repo(comp_id, comp_data)
    rss_feed = f"https://github.com/{gh_repo}/releases.atom" if gh_repo else None
    registry = detect_registry_type(img_name)
    last_version = comp_data.get("last_tested_version")

    release_track = comp_data.get("release_track") or detect_release_track(
        comp_id, comp_data
    )

    upstream = comp_data.get("upstream") or {
        "github_repo": gh_repo,
        "rss_feed": rss_feed,
        "registry_type": registry,
        "latest_upstream_version": last_version,
        "last_upstream_check": None,
        "is_deprecated": False,
        "deprecation_note": None,
    }

    staging = comp_data.get("staging") or {
        "candidate_version": None,
        "status": "idle",
        "test_result": None,
        "entered_staging_at": None,
        "grace_days": 14,
    }

    return {
        "release_track": release_track,
        "upstream": upstream,
        "staging": staging,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Enrich component metadata with release_track, upstream, and staging."
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--preview",
        action="store_true",
        default=True,
        help="Generate preview file without touching production.",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect changes in console only without writing any files.",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes directly to production metadata with backup.",
    )
    args = parser.parse_args()

    if not CATALOG_METADATA_PATH.exists():
        print(
            f"Error: Catalog metadata file not found at {CATALOG_METADATA_PATH}",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(CATALOG_METADATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    components = data.get("components", {})
    enriched_count = 0
    repo_found_count = 0
    lts_count = 0

    enriched_components = {}
    for comp_id, comp_data in components.items():
        new_data = dict(comp_data)
        lifecycle = build_lifecycle_metadata(comp_id, comp_data)
        new_data["release_track"] = lifecycle["release_track"]
        new_data["upstream"] = lifecycle["upstream"]
        new_data["staging"] = lifecycle["staging"]

        if lifecycle["upstream"]["github_repo"]:
            repo_found_count += 1
        if lifecycle["release_track"]["track"] == "lts":
            lts_count += 1

        enriched_components[comp_id] = new_data
        enriched_count += 1

    result_data = dict(data)
    result_data["components"] = enriched_components

    print("=" * 60)
    print("NjordDeploy Component Metadata Enrichment Summary:")
    print(f"  Total components processed:  {enriched_count}")
    print(f"  GitHub upstream repos mapped:{repo_found_count}")
    print(f"  LTS track components tagged: {lts_count}")
    print("=" * 60)

    if args.dry_run:
        print("[DRY-RUN] No files written.")
        return

    if args.apply:
        backup_path = CATALOG_METADATA_PATH.with_suffix(".json.bak")
        shutil.copyfile(CATALOG_METADATA_PATH, backup_path)
        print(f"[BACKUP] Created backup at {backup_path}")
        with open(CATALOG_METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=4, ensure_ascii=False)
        print(f"[SUCCESS] Updated production catalog at {CATALOG_METADATA_PATH}")
    else:
        # Default: preview mode
        with open(PREVIEW_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=4, ensure_ascii=False)
        print(f"[PREVIEW] Created preview file at {PREVIEW_OUTPUT_PATH}")
        print("You can compare this preview with the original metadata safely.")


if __name__ == "__main__":
    main()
