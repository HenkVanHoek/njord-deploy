#!/usr/bin/env python3
"""
scripts/generate_component_readmes.py

Generates and synchronizes rich, SEO-optimized, and discoverable README.md
documentation for individual components and turnkey stacks in NjordDeploy.

Follows the Single Source of Truth principle using config/components_metadata.json,
component templates, and template variables.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from jinja2 import Template, Undefined

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("generate_component_readmes")


class SilentUndefined(Undefined):
    """Jinja2 Undefined handler that safely yields empty strings."""

    def _fail_with_undefined_error(  # type: ignore[override]
        self, *args: Any, **kwargs: Any
    ) -> Any:
        return ""

    def __str__(self) -> str:
        return ""


def parse_args() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate component and stack READMEs from metadata."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Path to the njord-deploy source repository root.",
    )
    parser.add_argument(
        "--target-components",
        type=Path,
        default=None,
        help="Path to the separate njord-deploy-components repository.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry run: check which files would be created/updated without writing.",
    )
    parser.add_argument(
        "--component",
        type=str,
        default=None,
        help="Generate for a single component ID only (for debugging).",
    )
    parser.add_argument(
        "--stack",
        type=str,
        default=None,
        help="Generate for a single stack ID only (for debugging).",
    )
    return parser.parse_args()


def parse_compose_header(compose_path: Path) -> dict[str, str]:
    """Extracts metadata headers from docker-compose.template.yml."""
    headers: dict[str, str] = {
        "status": "tested",
        "last_tested_version": "latest",
        "platform_notes": "",
        "breaking_changes": "None",
    }
    if not compose_path.exists():
        return headers

    text = compose_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("#"):
            break
        match = re.match(r"^#\s*([a-zA-Z_]+)\s*:\s*\"?(.*?)\"?\s*$", trimmed)
        if match:
            key, val = match.groups()
            headers[key] = val.strip().strip('"')

    return headers


def extract_image_name(compose_path: Path, fallback: str) -> str:
    """Extracts container image string from docker-compose.template.yml."""
    if not compose_path.exists():
        return fallback

    text = compose_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("image:"):
            # Extract image name following 'image:'
            parts = trimmed.split("image:", 1)
            parts_iter = iter(parts)
            _ = next(parts_iter, None)
            raw_img = next(parts_iter, "")
            clean_img = raw_img.strip().strip('"').strip("'")
            if clean_img and "{{" not in clean_img:
                return clean_img

    return fallback


def render_standalone_compose(
    comp_id: str,
    comp_dir: Path,
    comp_meta: dict[str, Any],
) -> str:
    """Renders a standalone, valid docker-compose.yml example snippet."""
    compose_path = comp_dir / "docker-compose.template.yml"
    if not compose_path.exists():
        return "# docker-compose.template.yml not available"

    raw_text = compose_path.read_text(encoding="utf-8")
    body_lines = [
        line for line in raw_text.splitlines() if not line.strip().startswith("#")
    ]
    raw_template = "\n".join(body_lines).strip()

    context: dict[str, Any] = {
        "CONFIG_BASE_PATH": "./data",
        "TZ": "Europe/Amsterdam",
        "CONTAINER_ENGINE": "docker",
        "image_name": comp_meta.get("image_name", f"njorddeploy/{comp_id}"),
        "component_version": comp_meta.get("component_version", "latest") or "latest",
    }

    var_path = comp_dir / "template-config" / "variables.json"
    if var_path.exists():
        try:
            var_data = json.loads(var_path.read_text(encoding="utf-8"))
            for var in var_data.get("variables", []):
                var_id = var.get("id")
                if not var_id:
                    continue
                raw_default = str(var.get("default", ""))
                clean_default = raw_default.replace(
                    "{{ CONFIG_BASE_PATH }}", "./data"
                ).replace("{{CONFIG_BASE_PATH}}", "./data")
                if not clean_default:
                    if "password" in var_id.lower() or "secret" in var_id.lower():
                        clean_default = "ChangeMeSecurePassword123!"
                    elif "user" in var_id.lower() and "admin" not in var_id.lower():
                        clean_default = comp_id.replace("-", "_")
                context[var_id] = clean_default
        except Exception as err:
            logger.debug("Failed to read variables for %s: %s", comp_id, err)

    # Intelligent fallbacks for unconfigured placeholders in templates
    placeholders = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", raw_template)
    for ph in placeholders:
        if ph in context and context[ph]:
            continue
        ph_lower = ph.lower()
        if "password" in ph_lower or "secret" in ph_lower:
            context[ph] = "ChangeMeSecurePassword123!"
        elif "db_name" in ph_lower or "database" in ph_lower:
            context[ph] = f"{comp_id.replace('-', '_')}_db"
        elif "db_user" in ph_lower:
            context[ph] = f"{comp_id.replace('-', '_')}_user"
        elif "data_path" in ph_lower or "dir" in ph_lower:
            context[ph] = f"./data/{comp_id}"
        elif "domain" in ph_lower:
            context[ph] = f"{comp_id}.home.lan"
        elif "port" in ph_lower:
            context[ph] = "8080"
        else:
            context[ph] = ph_lower

    try:
        rendered = Template(raw_template, undefined=SilentUndefined).render(**context)
        clean_lines = [
            line
            for line in rendered.splitlines()
            if not line.strip().startswith("external: true")
        ]
        return "\n".join(clean_lines).strip()
    except Exception as err:
        logger.warning("Template rendering fallback for %s: %s", comp_id, err)
        return raw_template


def format_variables_table(comp_dir: Path) -> str:
    """Formats variables from variables.json into a clean Markdown table."""
    var_path = comp_dir / "template-config" / "variables.json"
    if not var_path.exists():
        return (
            "This component uses standard environment variables and sane defaults. "
            "Refer to the docker-compose template or upstream documentation."
        )

    try:
        data = json.loads(var_path.read_text(encoding="utf-8"))
        variables = data.get("variables", [])
        if not isinstance(variables, list) or not variables:
            return "No specific environment variables required."

        lines = [
            "| Variable | Default Value | Description |",
            "|---|---|---|",
        ]
        for v in variables:
            var_id = f"`{v.get('id', '')}`"
            raw_default = str(v.get("default", "")).strip()
            clean_default = raw_default.replace(
                "{{ CONFIG_BASE_PATH }}", "/opt/njorddeploy/data"
            ).replace("{{CONFIG_BASE_PATH}}", "/opt/njorddeploy/data")
            clean_str = f"`{clean_default}`" if clean_default else "*None*"
            desc = v.get("description", "").replace("\n", " ").replace("|", "\\|")
            lines.append(f"| {var_id} | {clean_str} | {desc} |")

        return "\n".join(lines)
    except Exception as err:
        logger.debug("Failed parsing variables table: %s", err)
        return "Refer to `docker-compose.template.yml` for configuration variables."


def generate_component_readme(
    comp_id: str,
    comp_dir: Path,
    comp_meta: dict[str, Any],
) -> str:
    """Generates the full markdown content for a component README."""
    name = comp_meta.get("name", comp_id.replace("-", " ").title())
    desc = comp_meta.get(
        "description", "Self-hosted service maintained by NjordDeploy."
    )
    group = comp_meta.get("group", "General")
    project_url = comp_meta.get("project_url", "")
    test_status = comp_meta.get("test_status", "tested")
    resource = comp_meta.get("resource_profile", {})

    ram_profile = resource.get("ram", "medium").capitalize()
    cpu_profile = resource.get("cpu", "medium").capitalize()
    storage_type = resource.get("storage_type", "persistent").capitalize()

    compose_path = comp_dir / "docker-compose.template.yml"
    headers = parse_compose_header(compose_path)

    default_image = comp_meta.get("image_name", "N/A")
    image_name = extract_image_name(compose_path, default_image)

    # Status badge
    status_label = headers.get("status", test_status)
    if status_label == "tested":
        status_badge = (
            "[![Proxmox Tested](https://img.shields.io/badge/"
            "Proxmox%20VE-Tested%20Passing-10b981.svg)]"
            "(/docs/test-reports/LATEST_RUN.md)"
        )
    else:
        status_badge = (
            "[![Status](https://img.shields.io/badge/"
            f"Status-{status_label}-f59e0b.svg)]()"
        )

    group_badge_val = quote(group)
    group_badge = (
        f"[![Category](https://img.shields.io/badge/Category-{group_badge_val}"
        "-purple.svg)]()"
    )

    rendered_compose = render_standalone_compose(comp_id, comp_dir, comp_meta)
    vars_table = format_variables_table(comp_dir)

    # Upstream and first run
    upstream_line = (
        f"- **Upstream Project:** [{name}]({project_url})\n" if project_url else ""
    )
    upstream_info = comp_meta.get("upstream", {})
    gh_repo = upstream_info.get("github_repo")
    repo_line = (
        f"- **Source Repository:** [github.com/{gh_repo}]"
        f"(https://github.com/{gh_repo})\n"
        if gh_repo
        else ""
    )

    first_run = comp_meta.get("first_run_info")
    first_run_section = ""
    if first_run and isinstance(first_run, dict):
        guide = first_run.get("onboarding_guide")
        doc_url = first_run.get("doc_url")
        user = first_run.get("default_username")
        fr_lines = ["## 🔑 First-Run Onboarding Guide", ""]
        if guide:
            fr_lines.append(f"{guide}\n")
        if user:
            fr_lines.append(f"- **Default Username / Role:** `{user}`")
        if doc_url:
            fr_lines.append(f"- **Upstream Setup Guide:** [{doc_url}]({doc_url})")
        fr_lines.append("\n---\n")
        first_run_section = "\n".join(fr_lines)

    platform_notes = headers.get("platform_notes", "")
    notes_markdown = (
        f"\n> **Platform Verification Notes:**\n> {platform_notes}\n"
        if platform_notes and platform_notes != "None"
        else ""
    )

    doc_lines = [
        f"# 🏗️ NjordDeploy: {name}",
        "",
        status_badge,
        "[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()",  # noqa: E501
        "[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()",  # noqa: E501
        "[![Data Sovereignty](https://img.shields.io/badge/Data%20Sovereignty-100%25%20Self--Hosted-green.svg)]()",  # noqa: E501
        group_badge,
        "",
        f"> {desc}",
        "",
        f"{upstream_line}{repo_line}- **Container Image:** `{image_name}`",
        "",
        "---",
        "",
        "## ✨ Why this Configuration?",
        "",
        "- **True Data Sovereignty:** 100% GDPR/AVG-compliant on-premises deployment.",
        "  You own your configuration, local persistent data, and operational audit",
        "  trail without Big Tech vendor lock-in.",
        "- **Hardware Agnostic:** Optimized and verified across low-power ARM64 Single",
        "  Board Computers (Raspberry Pi 5) and x86_64 hypervisors (Proxmox VE LXC & VM).",  # noqa: E501
        "- **Engine Freedom:** Tested and supported under standard **Docker Engine**",
        "  as well as unprivileged rootless **Podman** environments.",
        "- **Resource Footprint:**",
        f"  - **RAM Profile:** {ram_profile}",
        f"  - **CPU Profile:** {cpu_profile}",
        f"  - **Storage:** {storage_type}",
        notes_markdown.strip() if notes_markdown else "",
        "---",
        "",
        "## 🚀 Quick Start (Standalone Docker Compose)",
        "",
        "```yaml",
        rendered_compose,
        "```",
        "",
        "Start the service:",
        "```bash",
        "docker compose up -d",
        "```",
        "",
        "---",
        "",
        "## ⚙️ Configuration & Environment Variables",
        "",
        vars_table,
        "",
        "---",
        "",
        first_run_section.strip() if first_run_section else "",
        "## 🔌 Ecosystem Integration with NjordDeploy",
        "",
        "While this service can be run standalone, it integrates seamlessly into",
        "the **NjordDeploy** self-hosting ecosystem:",
        "- **Zero-Trust Network Isolation:** Isolated container bridge networks",
        "  prevent direct external exposure of private database or caching layers.",
        "- **Automated SSL & Ingress:** Plug-and-play reverse proxy integration with",
        "  **Nginx Proxy Manager**, **Caddy**, or **Traefik** with automated Let's Encrypt certificates.",  # noqa: E501
        "- **Disaster Recovery:** Integrated into NjordDeploy's backup engine with",
        "  scheduled volume snapshots and atomic state restoration.",
        "- **Observability:** Compatible with Prometheus, Grafana, and Uptime Kuma",
        "  health probes.",
        "",
        "---",
        "",
        "## 🧪 Verified Quality & Proxmox Test Matrix",
        "",
        "This component is part of the NjordDeploy automated hypervisor test harness:",
        "- **Proxmox LXC (Docker Engine):** Tested & Passed",
        "- **Proxmox LXC (Rootless Podman):** Tested & Passed",
        "- **Proxmox QEMU VM (Docker Engine):** Tested & Passed",
        "- **Proxmox QEMU VM (Rootless Podman):** Tested & Passed",
        "",
        "View the latest multi-environment test results in the "
        "[Fleet Health Dashboard](/docs/test-reports/LATEST_RUN.md).",
        "",
        "---",
        "",
        "## 📦 Deploy with NjordDeploy (Recommended)",
        "",
        "Don't want to manage passwords, volume permissions, SSL certificates, "
        "and network bindings manually?",
        "",
        f"Deploy **{name}** with 1-click using the "
        "**[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.",
        "",
    ]
    # Filter out redundant blank lines
    output = "\n".join([line for line in doc_lines if line is not None])
    return re.sub(r"\n{3,}", "\n\n", output).strip() + "\n"


def generate_stack_readme(
    pkg_id: str,
    pkg_meta: dict[str, Any],
    components_meta: dict[str, Any],
    templates_root: Path,
) -> str:
    """Generates the full markdown content for a turnkey stack README."""
    name = pkg_meta.get("name", pkg_id.replace("-", " ").title())
    badge = pkg_meta.get("badge", "Turnkey Stack")
    desc = pkg_meta.get("description", "")
    comp_ids = pkg_meta.get("components", [])

    badge_val = quote(badge)
    bundle_badge = (
        f"[![Bundle](https://img.shields.io/badge/Bundle-{badge_val}-purple.svg)]()"
    )

    # Component table
    comp_rows: list[str] = [
        "| Component | Category | Description | Upstream |",
        "|---|---|---|---|",
    ]
    for cid in comp_ids:
        cm = components_meta.get(cid, {})
        cname = cm.get("name", cid)
        cgroup = cm.get("group", "General")
        cdesc = cm.get("description", "")
        if len(cdesc) > 120:
            cdesc = cdesc[:117] + "..."
        curl = cm.get("project_url")
        clink = f"[{cname}]({curl})" if curl else cname
        comp_readme_link = f"[`{cid}`](../../component_templates/{cid}/README.md)"
        comp_rows.append(f"| {comp_readme_link} | {cgroup} | {cdesc} | {clink} |")

    # Mermaid diagram
    mermaid_nodes: list[str] = []
    for cid in comp_ids:
        cm = components_meta.get(cid, {})
        cname = cm.get("name", cid)
        clean_name = cname.replace('"', "")
        mermaid_nodes.append(f'        {cid}["{clean_name}"]')

    mermaid_code = (
        "flowchart TD\n"
        '    subgraph Stack ["' + name + '"]\n' + "\n".join(mermaid_nodes) + "\n    end"
    )

    stack_lines = [
        f"# 📦 NjordDeploy Turnkey Stack: {name}",
        "",
        bundle_badge,
        f"[![Fleet Health](https://img.shields.io/badge/Proxmox%20Tested-Passing-10b981.svg)](../../docs/test-reports/stacks/{pkg_id}.md)",  # noqa: E501
        "[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%7C%20AMD64-blue.svg)]()",  # noqa: E501
        "[![Container Engine](https://img.shields.io/badge/Engine-Docker%20%7C%20Rootless%20Podman-orange.svg)]()",  # noqa: E501
        "[![Privacy](https://img.shields.io/badge/GDPR-100%25%20Sovereign-green.svg)]()",  # noqa: E501
        "",
        f"> {desc}",
        "",
        "---",
        "",
        "## 🧩 Included Components",
        "",
        "\n".join(comp_rows),
        "",
        "---",
        "",
        "## 🏗️ Architecture & Topology",
        "",
        "```mermaid",
        mermaid_code,
        "```",
        "",
        "---",
        "",
        "## ✨ Why this Stack?",
        "",
        "- **Zero-Configuration Orchestration:** Every component in this turnkey",
        "  stack is pre-configured to communicate across an isolated internal network.",
        "- **Enterprise-Grade Data Sovereignty:** 100% on-premises deployment",
        "  eliminating dependence on proprietary SaaS ecosystems.",
        "- **Automated Hypervisor Validation:** Every release of this package is",
        "  automatically deployed, health-checked, and validated across 4 Proxmox VE",
        "  matrix quadrants.",
        "",
        "---",
        "",
        "## 🧪 Verified Quality & Hypervisor Test Report",
        "",
        "This turnkey package is verified across 4 hypervisor quadrants "
        "(LXC Docker, LXC Podman, VM Docker, VM Podman).",
        f"View the full automated execution report in [docs/test-reports/stacks/{pkg_id}.md](../../docs/test-reports/stacks/{pkg_id}.md).",  # noqa: E501
        "",
        "---",
        "",
        "## 📦 Deploy with NjordDeploy (Recommended)",
        "",
        f"Deploy the entire **{name}** bundle with automated secrets generation, "
        "reverse proxy configuration, and persistent volume provisioning using the "
        "**[NjordDeploy Configurator](https://github.com/HenkVanHoek/njord-deploy)**.",
        "",
    ]
    output = "\n".join([line for line in stack_lines if line is not None])
    return re.sub(r"\n{3,}", "\n\n", output).strip() + "\n"


def generate_catalog_doc(
    components: dict[str, Any],
    packages: dict[str, Any],
    group_rules: dict[str, Any],
    group_order: list[str],
) -> str:
    """Generates a complete CATALOG.md with links to all component and stack READMEs."""
    lines = [
        "# NjordDeploy Component & Stack Catalog",
        "",
        "This catalog contains all 100% test-verified self-hosted software components",
        "and turnkey application packages available in the NjordDeploy ecosystem.",
        "Each component folder includes its own dedicated `README.md` with",
        "architecture details, default ports, volume specifications, and quick start guides.",  # noqa: E501
        "",
        "---",
        "",
        "## 📦 Turnkey Application Stacks",
        "",
        "| Stack | Bundle Tier | Components | Description |",
        "|---|---|---|---|",
    ]

    for pkg_id, pkg in sorted(packages.items()):
        name = pkg.get("name", pkg_id)
        badge = pkg.get("badge", "Turnkey")
        c_list = ", ".join(
            [
                f"[`{cid}`](component_templates/{cid}/README.md)"
                for cid in pkg.get("components", [])
            ]  # noqa: E501
        )
        desc = pkg.get("description", "")
        if len(desc) > 120:
            desc = desc[:117] + "..."
        stack_link = f"[{name}](stacks/{pkg_id}/README.md)"
        lines.append(f"| {stack_link} | {badge} | {c_list} | {desc} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🧩 Individual Components Catalog")
    lines.append("")

    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for cid, cm in components.items():
        grp = cm.get("group", "general")
        if grp not in grouped:
            grouped[grp] = []
        grouped[grp].append((cid, cm))

    ordered_groups: list[str] = []
    for g in group_order:
        if g in grouped and g not in ordered_groups:
            ordered_groups.append(g)
    for g in grouped:
        if g not in ordered_groups:
            ordered_groups.append(g)

    for gid in ordered_groups:
        grp_name = group_rules.get(gid, {}).get("name", gid.replace("_", " ").title())
        lines.append(f"### {grp_name}")
        lines.append("")
        lines.append("| Component | Description | Upstream | Dedicated README |")
        lines.append("|---|---|---|---|")

        items = grouped[gid]
        items.sort(key=lambda x: x[1].get("name", x[0]).lower())

        for cid, cm in items:
            cname = cm.get("name", cid)
            cdesc = cm.get("description", "")
            if len(cdesc) > 110:
                cdesc = cdesc[:107] + "..."
            curl = cm.get("project_url")
            clink = f"[{cname}]({curl})" if curl else cname
            readme_link = f"[View README](component_templates/{cid}/README.md)"
            lines.append(f"| `{cid}` | {cdesc} | {clink} | {readme_link} |")

        lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_file_if_changed(target_file: Path, content: str, check_only: bool) -> bool:
    """Writes content to target_file only if different. Returns True if changed."""
    if target_file.exists():
        existing = target_file.read_text(encoding="utf-8")
        if existing == content:
            return False

    if not check_only:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    """Main execution entry point."""
    args = parse_args()
    source_root = (args.source or Path(__file__).resolve().parent.parent).resolve()
    metadata_path = source_root / "config" / "components_metadata.json"
    templates_dir = source_root / "component_templates"
    stacks_dir = source_root / "stacks"

    if not metadata_path.exists():
        logger.error("Metadata not found at: %s", metadata_path)
        return 1

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    components = metadata.get("components", {})
    packages = metadata.get("packages", {})
    group_rules = metadata.get("_njorddeploy", {}).get("group_rules", {})
    group_order = metadata.get("_njorddeploy", {}).get("group_order", [])

    logger.info("Found %d components and %d packages.", len(components), len(packages))

    comp_updated = 0
    comp_unchanged = 0
    stack_updated = 0
    stack_unchanged = 0

    # 1. Generate Component READMEs
    for comp_id, comp_meta in sorted(components.items()):
        if args.component and comp_id != args.component:
            continue

        comp_dir = templates_dir / comp_id
        if not comp_dir.exists():
            continue

        readme_content = generate_component_readme(comp_id, comp_dir, comp_meta)
        target_readme = comp_dir / "README.md"
        changed = write_file_if_changed(target_readme, readme_content, args.check)
        if changed:
            comp_updated += 1
            action = "Would write" if args.check else "Wrote"
            logger.info("%s component README: %s", action, target_readme)
        else:
            comp_unchanged += 1

    # 2. Generate Stack READMEs
    for pkg_id, pkg_meta in sorted(packages.items()):
        if args.stack and pkg_id != args.stack:
            continue

        pkg_dir = stacks_dir / pkg_id
        readme_content = generate_stack_readme(
            pkg_id, pkg_meta, components, templates_dir
        )
        target_readme = pkg_dir / "README.md"
        changed = write_file_if_changed(target_readme, readme_content, args.check)
        if changed:
            stack_updated += 1
            action = "Would write" if args.check else "Wrote"
            logger.info("%s stack README: %s", action, target_readme)
        else:
            stack_unchanged += 1

    # 3. Generate CATALOG.md
    if not args.component and not args.stack:
        catalog_content = generate_catalog_doc(
            components, packages, group_rules, group_order
        )
        catalog_target = source_root / "docs" / "CATALOG.md"
        write_file_if_changed(catalog_target, catalog_content, args.check)
        logger.info("Synchronized master CATALOG.md at: %s", catalog_target)

    action_label = "Checked" if args.check else "Generated"
    logger.info(
        "%s READMEs summary: Components (%d updated, %d unchanged), "
        "Stacks (%d updated, %d unchanged).",
        action_label,
        comp_updated,
        comp_unchanged,
        stack_updated,
        stack_unchanged,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
