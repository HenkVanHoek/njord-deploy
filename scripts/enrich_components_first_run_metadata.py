#!/usr/bin/env python3
# scripts/enrich_components_first_run_metadata.py
"""
Enriches existing catalog components in config/components_metadata.json with
first_run_info metadata (auth_type, log_token_regex, token_label,
default_username, onboarding_guide, doc_url).

Usage:
    python scripts/enrich_components_first_run_metadata.py --dry-run
    python scripts/enrich_components_first_run_metadata.py --apply
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

CATALOG_METADATA_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "components_metadata.json"
)

# Known standard first_run_info specifications for popular catalog services
KNOWN_FIRST_RUN_CATALOG: Dict[str, Dict[str, Any]] = {
    "octoprint": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": None,
        "onboarding_guide": (
            "Complete the initial OctoPrint setup wizard in your browser to "
            "configure access control, printer profile, and server settings."
        ),
        "doc_url": "https://docs.octoprint.org/",
    },
    "portainer": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin",
        "onboarding_guide": (
            "Create your initial administrator account within 5 minutes of "
            "container startup to secure the management portal."
        ),
        "doc_url": "https://docs.portainer.io/start/install-ce",
    },
    "pi-hole": {
        "auth_type": "preconfigured",
        "log_token_regex": None,
        "token_label": None,
        "default_username": None,
        "onboarding_guide": (
            "Log in to the web administration console using the password "
            "configured in service variables (PIHOLE_WEB_PASSWORD)."
        ),
        "doc_url": "https://docs.pi-hole.net/",
    },
    "adguard-home": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin",
        "onboarding_guide": (
            "Access the setup wizard to configure the listening DNS port, "
            "web management interface, and create administrator credentials."
        ),
        "doc_url": "https://github.com/AdguardTeam/AdGuardHome/wiki/Getting-Started",
    },
    "vaultwarden": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": None,
        "onboarding_guide": (
            "Open the web vault in your browser and click 'Create Account' "
            "to establish your master credentials."
        ),
        "doc_url": "https://github.com/dani-garcia/vaultwarden/wiki",
    },
    "nextcloud": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin",
        "onboarding_guide": (
            "Enter your desired administrator credentials on the initial "
            "setup page to initialize the Nextcloud instance."
        ),
        "doc_url": "https://docs.nextcloud.com/",
    },
    "homeassistant": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": None,
        "onboarding_guide": (
            "Follow the onboarding flow to name your home, set location, "
            "and create your owner account."
        ),
        "doc_url": "https://www.home-assistant.io/getting-started/onboarding/",
    },
    "semaphore": {
        "auth_type": "preconfigured",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin",
        "onboarding_guide": (
            "Log in with SEMAPHORE_ADMIN / SEMAPHORE_ADMIN_PASSWORD configured "
            "in your deployment parameters."
        ),
        "doc_url": "https://docs.semaphoreui.com/",
    },
    "grafana": {
        "auth_type": "preconfigured",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin",
        "onboarding_guide": (
            "Sign in as 'admin' using the password configured in "
            "GRAFANA_ADMIN_PASSWORD."
        ),
        "doc_url": "https://grafana.com/docs/grafana/latest/getting-started/",
    },
    "filebrowser": {
        "auth_type": "preconfigured",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin",
        "onboarding_guide": (
            "Sign in with initial credentials 'admin' / 'admin' and change "
            "the password immediately under Settings."
        ),
        "doc_url": "https://filebrowser.org/quick-start",
    },
    "nginx-proxy-manager": {
        "auth_type": "preconfigured",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin@example.com",
        "onboarding_guide": (
            "Default email: admin@example.com, default password: changeme. "
            "You will be prompted to change these on first login."
        ),
        "doc_url": "https://nginxproxymanager.com/guide/#initial-run",
    },
    "uptime-kuma": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin",
        "onboarding_guide": (
            "Create your initial administrator username and password upon "
            "first visiting the web UI."
        ),
        "doc_url": "https://github.com/louislam/uptime-kuma/wiki",
    },
    "immich": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": None,
        "onboarding_guide": (
            "Navigate to the web interface and click 'Getting Started' to "
            "create the root administrator account."
        ),
        "doc_url": "https://immich.app/docs/overview/quick-start",
    },
    "syncthing": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": None,
        "onboarding_guide": (
            "Access the web GUI. Syncthing will advise you to configure a "
            "GUI username and password under Actions -> Settings -> GUI."
        ),
        "doc_url": "https://docs.syncthing.net/intro/getting-started.html",
    },
    "gitea": {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": "admin",
        "onboarding_guide": (
            "Review database settings and register the initial administrator "
            "account at the bottom of the installation page."
        ),
        "doc_url": "https://docs.gitea.com/installation/install-with-docker",
    },
}


def build_default_first_run_info(
    component_id: str, comp_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Infers sensible first_run_info for services not explicitly hardcoded.
    """
    has_ui = bool(comp_data.get("has_ui", False))
    if not has_ui:
        return {
            "auth_type": "none",
            "log_token_regex": None,
            "token_label": None,
            "default_username": None,
            "onboarding_guide": (
                "Background service operating without an independent web interface."
            ),
            "doc_url": comp_data.get("project_url"),
        }

    # If it has a UI but isn't explicitly listed, default to wizard
    return {
        "auth_type": "wizard",
        "log_token_regex": None,
        "token_label": None,
        "default_username": None,
        "onboarding_guide": (
            f"Open {comp_data.get('name', component_id)} web UI and complete "
            "the initial onboarding setup."
        ),
        "doc_url": comp_data.get("project_url"),
    }


def enrich_components(dry_run: bool = True) -> int:
    """Enriches all components in the metadata file."""
    if not CATALOG_METADATA_PATH.exists():
        print(f"Error: {CATALOG_METADATA_PATH} not found.")
        return 1

    with open(CATALOG_METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    components = metadata.get("components", {})
    updated_count = 0

    for comp_id, comp_data in sorted(components.items()):
        current_fri = comp_data.get("first_run_info")
        new_fri: Dict[str, Any]

        if comp_id in KNOWN_FIRST_RUN_CATALOG:
            preset = KNOWN_FIRST_RUN_CATALOG[comp_id]
            new_fri = {
                "auth_type": preset.get("auth_type", "wizard"),
                "log_token_regex": preset.get("log_token_regex"),
                "token_label": preset.get("token_label"),
                "default_username": preset.get("default_username"),
                "onboarding_guide": preset.get("onboarding_guide", ""),
                "doc_url": preset.get("doc_url") or comp_data.get("project_url"),
            }
        elif current_fri is None:
            new_fri = build_default_first_run_info(comp_id, comp_data)
        else:
            continue

        if current_fri != new_fri:
            updated_count += 1
            action_label = "WOULD UPDATE" if dry_run else "UPDATED"
            print(
                f"[{action_label}] {comp_id}: auth_type={new_fri['auth_type']} "
                f"guide='{new_fri['onboarding_guide'][:50]}...'"
            )
            if not dry_run:
                comp_data["first_run_info"] = new_fri

    if dry_run:
        print(
            f"\n[DRY-RUN] Processed {len(components)} components. "
            f"{updated_count} components would be enriched."
        )
        print("Run with --apply to commit changes to config/components_metadata.json.")
    else:
        with open(CATALOG_METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)
        print(
            f"\n[SUCCESS] Successfully enriched {updated_count} "
            f"components in {CATALOG_METADATA_PATH}."
        )

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich catalog components with first_run_info metadata."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate metadata enrichment without writing to disk.",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Apply first_run_info updates to config/components_metadata.json.",
    )

    args = parser.parse_args()
    status_code = enrich_components(dry_run=not args.apply)
    sys.exit(status_code)


if __name__ == "__main__":
    main()
