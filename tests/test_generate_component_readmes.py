"""
tests/test_generate_component_readmes.py

Unit tests for scripts/generate_component_readmes.py.
"""

from pathlib import Path
from typing import Any

from scripts.generate_component_readmes import (
    extract_image_name,
    format_variables_table,
    generate_catalog_doc,
    generate_component_readme,
    generate_stack_readme,
    parse_compose_header,
    render_standalone_compose,
    write_file_if_changed,
)


def test_parse_compose_header(tmp_path: Path) -> None:
    compose_file = tmp_path / "docker-compose.template.yml"
    compose_file.write_text(
        '# status: "tested"\n'
        '# last_tested_version: "2.5.0"\n'
        '# platform_notes: "ARM64 verified."\n'
        '# breaking_changes: "None"\n'
        "services:\n  app:\n    image: test:latest\n",
        encoding="utf-8",
    )
    headers = parse_compose_header(compose_file)
    assert headers["status"] == "tested"
    assert headers["last_tested_version"] == "2.5.0"
    assert headers["platform_notes"] == "ARM64 verified."


def test_extract_image_name(tmp_path: Path) -> None:
    compose_file = tmp_path / "docker-compose.template.yml"
    compose_file.write_text(
        'services:\n  web:\n    image: "nginx:alpine"\n', encoding="utf-8"
    )
    img = extract_image_name(compose_file, fallback="default/img")
    assert img == "nginx:alpine"

    # Fallback when non-existent
    missing_file = tmp_path / "missing.yml"
    assert extract_image_name(missing_file, fallback="fallback/img") == "fallback/img"


def test_render_standalone_compose(tmp_path: Path) -> None:
    comp_dir = tmp_path / "my-service"
    comp_dir.mkdir()
    compose_file = comp_dir / "docker-compose.template.yml"
    compose_file.write_text(
        '# status: "tested"\n'
        "services:\n"
        "  my-service:\n"
        "    image: test:latest\n"
        '    ports:\n      - "{{ PORT_HTTP }}:80"\n'
        "    environment:\n      - DB_PASS={{ MY_PASSWORD }}\n",
        encoding="utf-8",
    )
    cfg_dir = comp_dir / "template-config"
    cfg_dir.mkdir()
    var_file = cfg_dir / "variables.json"
    var_file.write_text(
        '{"variables": [{"id": "PORT_HTTP", "default": "8080"}]}',
        encoding="utf-8",
    )

    comp_meta: dict[str, Any] = {"image_name": "test:latest"}
    rendered = render_standalone_compose("my-service", comp_dir, comp_meta)
    assert "8080:80" in rendered
    assert "ChangeMeSecurePassword123!" in rendered


def test_format_variables_table(tmp_path: Path) -> None:
    comp_dir = tmp_path / "test-svc"
    cfg_dir = comp_dir / "template-config"
    cfg_dir.mkdir(parents=True)
    var_file = cfg_dir / "variables.json"
    var_file.write_text(
        '{"variables": [{"id": "API_KEY", "default": "xyz", '
        '"description": "API Authentication Token"}]}',
        encoding="utf-8",
    )
    table = format_variables_table(comp_dir)
    assert "`API_KEY`" in table
    assert "`xyz`" in table
    assert "API Authentication Token" in table


def test_generate_component_readme(tmp_path: Path) -> None:
    comp_dir = tmp_path / "adguard-home"
    comp_dir.mkdir()
    (comp_dir / "docker-compose.template.yml").write_text(
        '# status: "tested"\nservices:\n  adguard:\n    image: adguard:latest\n',
        encoding="utf-8",
    )
    comp_meta: dict[str, Any] = {
        "name": "AdGuard Home",
        "description": "Network-wide ad-blocking DNS server.",
        "group": "DNS Blocker",
        "project_url": "https://adguard.com",
        "test_status": "tested",
        "first_run_info": {
            "onboarding_guide": "Visit port 3000 to setup.",
            "doc_url": "https://adguard.com/docs",
        },
    }
    readme = generate_component_readme("adguard-home", comp_dir, comp_meta)
    assert "# 🏗️ NjordDeploy: AdGuard Home" in readme
    assert "Network-wide ad-blocking DNS server." in readme
    assert "https://adguard.com" in readme
    assert "Visit port 3000 to setup." in readme
    assert "Tested%20Passing" in readme


def test_generate_stack_readme(tmp_path: Path) -> None:
    pkg_meta: dict[str, Any] = {
        "name": "Media Stack",
        "badge": "Media Suite",
        "description": "Complete entertainment streaming stack.",
        "components": ["jellyfin", "radarr"],
    }
    components_meta: dict[str, Any] = {
        "jellyfin": {"name": "Jellyfin", "group": "Media", "description": "Streamer"},
        "radarr": {"name": "Radarr", "group": "Media", "description": "Movies"},
    }
    readme = generate_stack_readme("media-stack", pkg_meta, components_meta, tmp_path)
    assert "# 📦 NjordDeploy Turnkey Stack: Media Stack" in readme
    assert "Complete entertainment streaming stack." in readme
    assert "flowchart TD" in readme
    assert "jellyfin" in readme
    assert "radarr" in readme


def test_generate_catalog_doc() -> None:
    components: dict[str, Any] = {
        "caddy": {
            "name": "Caddy",
            "group": "proxy",
            "description": "Reverse proxy",
            "project_url": "https://caddyserver.com",
        }
    }
    packages: dict[str, Any] = {
        "web-stack": {
            "name": "Web Stack",
            "badge": "Core",
            "components": ["caddy"],
            "description": "Web hosting bundle",
        }
    }
    catalog = generate_catalog_doc(
        components, packages, {"proxy": {"name": "Reverse Proxy"}}, ["proxy"]
    )
    assert "# NjordDeploy Component & Stack Catalog" in catalog
    assert "Web Stack" in catalog
    assert "Caddy" in catalog
    assert "Reverse Proxy" in catalog


def test_write_file_if_changed(tmp_path: Path) -> None:
    target = tmp_path / "README.md"

    # 1. New file
    changed = write_file_if_changed(target, "Hello v1", check_only=False)
    assert changed is True
    assert target.read_text(encoding="utf-8") == "Hello v1"

    # 2. Identical content -> False
    changed = write_file_if_changed(target, "Hello v1", check_only=False)
    assert changed is False

    # 3. Dry-run update -> True, but file unchanged
    changed = write_file_if_changed(target, "Hello v2", check_only=True)
    assert changed is True
    assert target.read_text(encoding="utf-8") == "Hello v1"
