#!/usr/bin/env python3
"""
scripts/add_new_components.py

Programmatically registers new components into NjordDeploy using the
internal editor_app REST API (/api/components/ai).
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from editor_app.app import create_app  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("add_new_components")


NEW_COMPONENTS: list[dict[str, Any]] = [
    {
        "id": "netwatch",
        "metadata": {
            "name": "Netwatch",
            "group": "Security & Utilities",
            "description": (
                "A network presence and device monitoring system featuring active "
                "and passive scanning, timeline analysis, captive portal access "
                "control, and device grouping."
            ),
            "project_url": "https://github.com/emanuele-f/netwatch",
            "image_name": "ghcr.io/emanuele-f/netwatch:latest",
            "has_ui": True,
            "ui_port_variable": "PORT_NETWATCH",
            "protocol": "http",
            "depends_on": [],
            "conflicts_with": [],
            "tags": ["network", "monitoring", "devices", "presence", "security"],
            "resource_profile": {
                "cpu": "low",
                "ram": "low",
                "storage_type": "persistent",
            },
            "upstream": {
                "github_repo": "emanuele-f/netwatch",
                "registry_type": "ghcr",
                "latest_upstream_version": "latest",
            },
            "first_run_info": {
                "auth_type": "none",
                "default_username": None,
                "doc_url": "https://github.com/emanuele-f/netwatch",
                "onboarding_guide": (
                    "Open the Netwatch interface to see discovered network devices. "
                    "Group devices by person or set up passive monitoring filters."
                ),
            },
        },
        "docker_compose": """# status: "tested"
# last_tested_version: "latest"
# platform_notes: "Requires host network mode or NET_ADMIN/NET_RAW capabilities."
# breaking_changes: "None"
services:
  netwatch:
    image: ghcr.io/emanuele-f/netwatch:latest
    container_name: njorddeploy-netwatch
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - "{{ NETWATCH_DATA_PATH }}:/data"
    environment:
      - "TZ={{ TZ }}"
      - "PORT={{ PORT_NETWATCH }}"
""",
        "variables": [
            {
                "id": "PORT_NETWATCH",
                "label": "Netwatch HTTP Port",
                "description": "Port to access the Netwatch web interface.",
                "type": "port",
                "default": "8000",
                "required": "always",
            },
            {
                "id": "NETWATCH_DATA_PATH",
                "label": "Netwatch Data Path",
                "description": (
                    "Host directory for Netwatch database and configuration."
                ),
                "type": "path",
                "default": "{{ CONFIG_BASE_PATH }}/netwatch/data",
                "required": "always",
            },
        ],
    },
    {
        "id": "geolens",
        "metadata": {
            "name": "GeoLens",
            "group": "Utilities",
            "description": (
                "Self-hosted geospatial data catalog and interactive web map "
                "builder with PostGIS, vector tiles, OGC API support, and "
                "semantic spatial search."
            ),
            "project_url": "https://getgeolens.com",
            "image_name": "ghcr.io/geolens-io/geolens-frontend:latest",
            "has_ui": True,
            "ui_port_variable": "PORT_GEOLENS",
            "protocol": "http",
            "depends_on": [],
            "conflicts_with": [],
            "tags": ["gis", "geospatial", "maps", "catalog", "postgis", "analytics"],
            "resource_profile": {
                "cpu": "medium",
                "ram": "medium",
                "storage_type": "persistent",
            },
            "upstream": {
                "github_repo": "geolens-io/geolens",
                "registry_type": "ghcr",
                "latest_upstream_version": "latest",
            },
            "first_run_info": {
                "auth_type": "wizard",
                "default_username": "admin",
                "doc_url": "https://docs.getgeolens.com",
                "onboarding_guide": (
                    "Navigate to http://<server-ip>:8080 and initialize the "
                    "administrator account to start creating GIS datasets and maps."
                ),
            },
        },
        "docker_compose": """# status: "tested"
# last_tested_version: "latest"
# platform_notes: "Multi-arch ARM64/AMD64. Runs PostGIS, FastAPI, Vite web client."
# breaking_changes: "None"
services:
  geolens-web:
    image: ghcr.io/geolens-io/geolens-frontend:latest
    container_name: njorddeploy-geolens-web
    restart: unless-stopped
    ports:
      - "{{ PORT_GEOLENS }}:80"
    depends_on:
      - geolens-api
    networks:
      - njorddeploy_net

  geolens-api:
    image: ghcr.io/geolens-io/geolens-api:latest
    container_name: njorddeploy-geolens-api
    restart: unless-stopped
    ports:
      - "{{ GEOLENS_API_PORT }}:8000"
    depends_on:
      - geolens-db
    environment:
      - "POSTGRES_HOST=geolens-db"
      - "POSTGRES_DB=geolens"
      - "POSTGRES_USER=geolens"
      - "POSTGRES_PASSWORD={{ GEOLENS_DB_PASSWORD }}"
    volumes:
      - "{{ GEOLENS_DATA_PATH }}/storage:/data/storage"
    networks:
      - njorddeploy_net

  geolens-db:
    image: postgis/postgis:16-3.4-alpine
    container_name: njorddeploy-geolens-db
    restart: unless-stopped
    environment:
      - "POSTGRES_DB=geolens"
      - "POSTGRES_USER=geolens"
      - "POSTGRES_PASSWORD={{ GEOLENS_DB_PASSWORD }}"
    volumes:
      - "{{ GEOLENS_DATA_PATH }}/db:/var/lib/postgresql/data"
    networks:
      - njorddeploy_net

networks:
  njorddeploy_net:
    external: true
""",
        "variables": [
            {
                "id": "PORT_GEOLENS",
                "label": "GeoLens Web Port",
                "description": "Port to access the GeoLens Web Map interface.",
                "type": "port",
                "default": "8080",
                "required": "always",
            },
            {
                "id": "GEOLENS_API_PORT",
                "label": "GeoLens API Port",
                "description": "Port for the GeoLens FastAPI and OGC API endpoints.",
                "type": "port",
                "default": "8001",
                "required": "always",
            },
            {
                "id": "GEOLENS_DATA_PATH",
                "label": "GeoLens Storage Path",
                "description": "Host path for storing datasets and PostGIS database.",
                "type": "path",
                "default": "{{ CONFIG_BASE_PATH }}/geolens/data",
                "required": "always",
            },
            {
                "id": "GEOLENS_DB_PASSWORD",
                "label": "GeoLens Database Password",
                "description": "Password for internal PostGIS relational store.",
                "type": "password",
                "default": "ChangeMeSecurePassword123!",
                "required": "always",
            },
        ],
    },
    {
        "id": "hatchdoor",
        "metadata": {
            "name": "Hatchdoor",
            "group": "Productivity",
            "description": (
                "Agent-native web app and Model Context Protocol (MCP) server "
                "for Obsidian-style Markdown vaults with semantic search, "
                "wikilinks, and graph views."
            ),
            "project_url": "https://github.com/BattermanZ/Hatchdoor",
            "image_name": "battermanz/hatchdoor:latest",
            "has_ui": True,
            "ui_port_variable": "PORT_HATCHDOOR",
            "protocol": "http",
            "depends_on": [],
            "conflicts_with": [],
            "tags": ["markdown", "vault", "notes", "mcp", "ai", "obsidian", "pwa"],
            "resource_profile": {
                "cpu": "low",
                "ram": "low",
                "storage_type": "persistent",
            },
            "upstream": {
                "github_repo": "BattermanZ/Hatchdoor",
                "registry_type": "dockerhub",
                "latest_upstream_version": "latest",
            },
            "first_run_info": {
                "auth_type": "none",
                "default_username": None,
                "doc_url": "https://docs-hatchdoor.battercloud.cc",
                "onboarding_guide": (
                    "Open http://<server-ip>:42824 to browse your notes. Point "
                    "your MCP client (Claude Code, Cursor, Codex) to the MCP "
                    "endpoint to enable AI agent note navigation."
                ),
            },
        },
        "docker_compose": """# status: "tested"
# last_tested_version: "latest"
# platform_notes: "Rootless and distroless. Provides web UI and MCP server."
# breaking_changes: "None"
services:
  hatchdoor:
    image: battermanz/hatchdoor:latest
    container_name: njorddeploy-hatchdoor
    restart: unless-stopped
    ports:
      - "{{ PORT_HATCHDOOR }}:42824"
    environment:
      - "HOST=0.0.0.0"
      - "PORT=42824"
      - "VAULT_PATH=/data/vault"
      - "HATCHDOOR_CACHE_DB=/data/cache/hatchdoor-cache.sqlite3"
    volumes:
      - "{{ HATCHDOOR_VAULT_PATH }}:/data/vault"
      - "{{ HATCHDOOR_CACHE_PATH }}:/data/cache"
    networks:
      - njorddeploy_net

networks:
  njorddeploy_net:
    external: true
""",
        "variables": [
            {
                "id": "PORT_HATCHDOOR",
                "label": "Hatchdoor Port",
                "description": "Port to access the Hatchdoor Web UI and MCP endpoint.",
                "type": "port",
                "default": "42824",
                "required": "always",
            },
            {
                "id": "HATCHDOOR_VAULT_PATH",
                "label": "Markdown Vault Path",
                "description": "Host path containing Markdown notes and documents.",
                "type": "path",
                "default": "{{ CONFIG_BASE_PATH }}/hatchdoor/vault",
                "required": "always",
            },
            {
                "id": "HATCHDOOR_CACHE_PATH",
                "label": "Hatchdoor Cache Path",
                "description": "Host path for storing generated SQLite search cache.",
                "type": "path",
                "default": "{{ CONFIG_BASE_PATH }}/hatchdoor/cache",
                "required": "always",
            },
        ],
    },
    {
        "id": "dynacat",
        "metadata": {
            "name": "Dynacat",
            "group": "Dashboards",
            "description": (
                "A modern, real-time homelab dashboard and Glance fork "
                "featuring WebSockets, dynamic widgets, live feed aggregators, "
                "and minimal resource usage."
            ),
            "project_url": "https://github.com/Panonim/dynacat",
            "image_name": "panonim/dynacat:latest",
            "has_ui": True,
            "ui_port_variable": "PORT_DYNACAT",
            "protocol": "http",
            "depends_on": [],
            "conflicts_with": [],
            "tags": [
                "dashboard",
                "homepage",
                "feeds",
                "widgets",
                "glance",
                "realtime",
            ],
            "resource_profile": {
                "cpu": "low",
                "ram": "low",
                "storage_type": "persistent",
            },
            "upstream": {
                "github_repo": "Panonim/dynacat",
                "registry_type": "dockerhub",
                "latest_upstream_version": "latest",
            },
            "first_run_info": {
                "auth_type": "none",
                "default_username": None,
                "doc_url": "https://dynacat.artur.zone",
                "onboarding_guide": (
                    "Open http://<server-ip>:8092 to view your dashboard. "
                    "Configure widgets, feeds, and layouts via the web UI "
                    "or YAML configuration."
                ),
            },
        },
        "docker_compose": """# status: "tested"
# last_tested_version: "latest"
# platform_notes: "Fast Go binary. Real-time WebSocket homelab dashboard."
# breaking_changes: "None"
services:
  dynacat:
    image: panonim/dynacat:latest
    container_name: njorddeploy-dynacat
    restart: unless-stopped
    ports:
      - "{{ PORT_DYNACAT }}:8080"
    volumes:
      - "{{ DYNACAT_CONFIG_PATH }}:/app/config"
      - "{{ DYNACAT_ASSETS_PATH }}:/app/assets"
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - njorddeploy_net

networks:
  njorddeploy_net:
    external: true
""",
        "variables": [
            {
                "id": "PORT_DYNACAT",
                "label": "Dynacat Web Port",
                "description": "Port to access the Dynacat dashboard.",
                "type": "port",
                "default": "8092",
                "required": "always",
            },
            {
                "id": "DYNACAT_CONFIG_PATH",
                "label": "Dynacat Config Path",
                "description": "Host path for Dynacat YAML configuration.",
                "type": "path",
                "default": "{{ CONFIG_BASE_PATH }}/dynacat/config",
                "required": "always",
            },
            {
                "id": "DYNACAT_ASSETS_PATH",
                "label": "Dynacat Assets Path",
                "description": "Host path for custom dashboard icons and assets.",
                "type": "path",
                "default": "{{ CONFIG_BASE_PATH }}/dynacat/assets",
                "required": "always",
            },
        ],
    },
]


def main() -> int:
    app = create_app({"TESTING": True})
    client = app.test_client()

    success_count = 0
    for comp in NEW_COMPONENTS:
        cid = comp["id"]
        logger.info("Registering component '%s' via /api/components/ai...", cid)
        payload = {
            "id": cid,
            "metadata": comp["metadata"],
            "docker_compose": comp["docker_compose"],
            "variables": comp["variables"],
            "overwrite": True,
        }

        response = client.post("/api/components/ai", json=payload)
        if response.status_code in (200, 201):
            logger.info("Successfully registered component '%s' via API!", cid)
            success_count += 1
        else:
            logger.error(
                "Failed to register component '%s': status=%d, body=%s",
                cid,
                response.status_code,
                response.get_data(as_text=True),
            )

    logger.info(
        "Registration finished: %d/%d components added.",
        success_count,
        len(NEW_COMPONENTS),
    )
    return 0 if success_count == len(NEW_COMPONENTS) else 1


if __name__ == "__main__":
    sys.exit(main())
