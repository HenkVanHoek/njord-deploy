#!/usr/bin/env python3
"""scripts/check_upstream_updates.py

Autonomous control system for monitoring upstream GitHub repositories of
NjordDeploy components. Tracks new releases/tags, detects upstream breaking changes,
and evaluates if changes affect template configuration, ports, volumes, or
first_run_info onboarding instructions using AI analysis.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from managers.component_manager import ComponentManager  # noqa: E402
from utils.ai_generator_engine import AIGeneratorEngine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("check_upstream_updates")

BASE_GITHUB_API = "https://api.github.com"


def get_auth_token() -> Optional[str]:
    """Retrieves GitHub token from environment variables or .env file."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and token.strip():
        return token.strip()

    env_file = project_root / ".env"
    if env_file.exists():
        # noinspection PyBroadException
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("GITHUB_TOKEN=") or stripped.startswith(
                    "GH_TOKEN="
                ):
                    parts = stripped.split("=", 1)
                    if len(parts) == 2:
                        _, val = parts
                        cleaned_val = val.strip("\"' ")
                        if cleaned_val:
                            return cleaned_val
        except Exception:
            pass  # nosec B110
    return None


# Known upstream repository overrides for popular service images
KNOWN_UPSTREAM_REPOS = {
    "immich": "immich-app/immich",
    "pi-hole": "pi-hole/docker-pi-hole",
    "octoprint": "octoprint/octoprint",
    "adguard-home": "AdguardTeam/AdGuardHome",
    "homeassistant": "home-assistant/core",
    "portainer": "portainer/portainer",
    "vaultwarden": "dani-garcia/vaultwarden",
    "nextcloud": "nextcloud/server",
    "uptime-kuma": "louislam/uptime-kuma",
    "wireguard-easy": "wg-easy/wg-easy",
    "wg-easy": "wg-easy/wg-easy",
}


def resolve_component_repository(
    component_id: str,
    component_data: Dict[str, Any],
    template_path: Path,
) -> Optional[str]:
    """Infers the upstream GitHub repository (owner/repo) for a component."""
    # 0. Check explicit known mapping
    if component_id in KNOWN_UPSTREAM_REPOS:
        return KNOWN_UPSTREAM_REPOS[component_id]

    urls_to_check: List[str] = []
    p_url = component_data.get("project_url")
    if isinstance(p_url, str):
        urls_to_check.append(p_url)

    fri = component_data.get("first_run_info")
    if isinstance(fri, dict):
        d_url = fri.get("doc_url")
        if isinstance(d_url, str):
            urls_to_check.append(d_url)

    for url in urls_to_check:
        match = re.search(r"github\.com/([a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+)", url)
        if match:
            repo_slug = match.group(1).rstrip("/")
            if not repo_slug.endswith(".git"):
                return repo_slug

    img = component_data.get("image_name")
    if not img and template_path.exists():
        tpl_content = template_path.read_text(encoding="utf-8")
        im = re.search(r"image:\s*([^\s:]+)", tpl_content)
        if im:
            img = im.group(1)

    if isinstance(img, str) and img:
        cleaned = img.replace("lscr.io/", "").replace("ghcr.io/", "")
        parts = cleaned.split("/")
        if len(parts) == 2:
            owner, repo = parts
            if owner not in ("library", "docker"):
                return f"{owner}/{repo}"

    return None


def fetch_latest_release(
    repo: str,
    token: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fetches the latest GitHub release or tag information for a repository."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "NjordDeploy-Upstream-Watcher",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # noinspection PyBroadException
    try:
        url = f"{BASE_GITHUB_API}/repos/{repo}/releases?per_page=1"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            releases = res.json()
            if isinstance(releases, list) and releases:
                rel = next(iter(releases))
                return {
                    "tag_name": rel.get("tag_name"),
                    "name": rel.get("name") or rel.get("tag_name"),
                    "published_at": rel.get("published_at"),
                    "body": rel.get("body", ""),
                    "html_url": rel.get("html_url"),
                }
        elif res.status_code == 404:
            tag_url = f"{BASE_GITHUB_API}/repos/{repo}/tags?per_page=1"
            tag_res = requests.get(tag_url, headers=headers, timeout=10)
            if tag_res.status_code == 200:
                tags = tag_res.json()
                if isinstance(tags, list) and tags:
                    tag = next(iter(tags))
                    tag_name = tag.get("name")
                    return {
                        "tag_name": tag_name,
                        "name": tag_name,
                        "published_at": None,
                        "body": "",
                        "html_url": (
                            f"https://github.com/{repo}/releases/tag/{tag_name}"
                        ),
                    }
    except Exception as err:
        logger.debug(f"Failed to fetch release for {repo}: {err}")

    return None


def analyze_release_impact_with_ai(
    component_id: str,
    component_data: Dict[str, Any],
    template_content: str,
    release_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Uses AIGeneratorEngine to evaluate whether upstream release impacts metadata."""
    tag = release_info.get("tag_name", "unknown")
    notes = (release_info.get("body") or "")[:4000]

    system_prompt = (
        "You are an expert DevOps AI assistant specializing in Docker service "
        "compatibility and NjordDeploy component maintenance.\n"
        "Analyze the upstream release notes for a self-hosted software service.\n"
        "Determine if this release contains breaking changes or updates affecting:\n"
        "1. Docker Compose environment variables (deprecated, renamed, added)\n"
        "2. Exposed network ports or protocols\n"
        "3. Volume mount paths or file permissions\n"
        "4. First-run onboarding flow, credentials, or setup wizards "
        "(first_run_info)\n\n"
        "Output strictly valid JSON with keys:\n"
        '{"has_impact": true|false, "impact_level": "none|low|medium|high", '
        '"breaking_changes": "...", "recommended_actions": "...", "summary": "..."}'
    )

    user_prompt = (
        f"Component: {component_id}\n"
        f"New Upstream Version: {tag}\n"
        f"Current Metadata: {json.dumps(component_data, indent=2)}\n\n"
        f"Current Docker Compose Template:\n```yaml\n{template_content}\n```\n\n"
        f"Upstream Release Notes:\n{notes}"
    )

    # noinspection PyBroadException
    try:
        engine = AIGeneratorEngine()
        raw_res = engine.generate(prompt=user_prompt, system_context=system_prompt)
        cleaned = raw_res.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 2:
                cleaned = "\n".join(lines[1:-1])
        data = json.loads(cleaned)
        return {
            "has_impact": bool(data.get("has_impact", False)),
            "impact_level": str(data.get("impact_level", "low")),
            "breaking_changes": str(data.get("breaking_changes", "None")),
            "recommended_actions": str(data.get("recommended_actions", "")),
            "summary": str(data.get("summary", "")),
        }
    except Exception as e:
        logger.warning(f"AI analysis failed for {component_id}: {e}")
        return {
            "has_impact": False,
            "impact_level": "unknown",
            "breaking_changes": "AI Analysis unavailable",
            "recommended_actions": "Review upstream release manually",
            "summary": str(e),
        }


def run_upstream_check(
    components_filter: Optional[List[str]] = None,
    use_ai: bool = False,
    output_report: Optional[Path] = None,
) -> int:
    """Checks upstream releases across configured components and generates report."""
    load_dotenv(project_root / ".env", override=True)
    token = get_auth_token()

    metadata_path = project_root / "config" / "components_metadata.json"
    templates_dir = project_root / "component_templates"

    comp_mgr = ComponentManager(
        metadata_file_path=str(metadata_path), templates_path=str(templates_dir)
    )
    all_components = comp_mgr.get_all_components()

    targets: List[Dict[str, Any]] = []
    if components_filter:
        c_set = {c.strip().lower() for c in components_filter}
        targets = [c for c in all_components if c.get("id") in c_set]
    else:
        targets = all_components

    logger.info(f"Checking upstream updates for {len(targets)} component(s)...")

    results: List[Dict[str, Any]] = []

    for comp in targets:
        cid = comp.get("id", "")
        tpl_path = templates_dir / cid / "docker-compose.template.yml"
        repo = resolve_component_repository(cid, comp, tpl_path)

        if not repo:
            logger.debug(f"Could not infer upstream GitHub repo for {cid}.")
            continue

        rel_info = fetch_latest_release(repo, token=token)
        if not rel_info:
            continue

        tag = rel_info.get("tag_name")
        curr_ver = comp.get("component_version") or "latest"

        clean_tag = str(tag).lstrip("vV")
        clean_curr = str(curr_ver).lstrip("vV")

        is_newer = False
        if clean_curr in ("latest", "master", "main"):
            last_tested = comp.get("last_tested")
            pub_at = rel_info.get("published_at")
            if pub_at and last_tested:
                is_newer = pub_at > last_tested
            elif pub_at:
                is_newer = True
        elif clean_tag != clean_curr:
            is_newer = True

        rec: Dict[str, Any] = {
            "component_id": cid,
            "name": comp.get("name", cid),
            "repo": repo,
            "current_version": curr_ver,
            "latest_version": tag,
            "published_at": rel_info.get("published_at"),
            "release_url": rel_info.get("html_url"),
            "is_newer": is_newer,
            "ai_impact": None,
        }

        if is_newer:
            logger.info(
                f"🔔 [{cid}] Update detected: {curr_ver} -> {tag} "
                f"(Repo: https://github.com/{repo})"
            )
            if use_ai and tpl_path.exists():
                logger.info(f"🤖 Analyzing upstream release impact for {cid}...")
                tpl_txt = tpl_path.read_text(encoding="utf-8")
                ai_res = analyze_release_impact_with_ai(cid, comp, tpl_txt, rel_info)
                rec["ai_impact"] = ai_res
                logger.info(
                    f"   Impact: {ai_res.get('impact_level', '').upper()} | "
                    f"Breaking: {ai_res.get('breaking_changes')}"
                )

        results.append(rec)
        time.sleep(0.3)

    newer_records = [r for r in results if r["is_newer"]]
    logger.info(
        f"Finished check. {len(newer_records)} component(s) have new upstream releases."
    )

    if output_report:
        _generate_markdown_report(output_report, results, newer_records)
        logger.info(f"Saved upstream update report to: {output_report}")

    return 0


def _generate_markdown_report(
    report_path: Path,
    all_results: List[Dict[str, Any]],
    newer_records: List[Dict[str, Any]],
) -> None:
    """Writes a GitHub Markdown report detailing upstream releases and impact."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    md_lines: List[str] = [
        "# 🛰️ Upstream Component Release & Metadata Drift Report",
        "",
        f"**Generated:** `{ts}`  ",
        f"**Components Checked:** {len(all_results)} | "
        f"**New Releases Detected:** {len(newer_records)}",
        "",
    ]

    if newer_records:
        md_lines.append("## 🔔 Components with Upstream Updates")
        md_lines.append("")
        md_lines.append(
            "| Component ID | Current Ver | Upstream Ver | Repository | "
            "AI Impact | Action |"
        )
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        for r in newer_records:
            cid = r["component_id"]
            cver = r["current_version"]
            uver = f"[{r['latest_version']}]({r['release_url']})"
            repo_link = f"[{r['repo']}](https://github.com/{r['repo']})"
            ai = r.get("ai_impact")
            if ai:
                imp = ai.get("impact_level", "low").upper()
                imp_badge = f"**{imp}**" if imp in ("HIGH", "MEDIUM") else imp
                action = ai.get("recommended_actions", "Review")
            else:
                imp_badge = "—"
                action = "Re-test"

            md_lines.append(
                f"| `{cid}` | `{cver}` | {uver} | {repo_link} | "
                f"{imp_badge} | {action} |"
            )
        md_lines.append("")

        impacted = [r for r in newer_records if r.get("ai_impact")]
        if impacted:
            md_lines.append("## 🧠 AI Impact & Breaking Changes Analysis")
            md_lines.append("")
            for r in impacted:
                cid = r["component_id"]
                ai = r["ai_impact"]
                md_lines.append(f"### `{cid}` ({r['latest_version']})")
                md_lines.append(f"- **Summary:** {ai.get('summary')}")
                md_lines.append(f"- **Breaking Changes:** {ai.get('breaking_changes')}")
                md_lines.append(
                    f"- **Recommendations:** {ai.get('recommended_actions')}"
                )
                md_lines.append("")
    else:
        md_lines.append("## ✅ All Components Up to Date")
        md_lines.append("")
        md_lines.append(
            "No upstream releases or metadata drift detected across monitored "
            "components."
        )
        md_lines.append("")

    report_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check upstream GitHub releases and analyze impact on NjordDeploy."
    )
    parser.add_argument(
        "--components",
        type=str,
        help="Comma-separated component IDs to check (defaults to all).",
    )
    parser.add_argument(
        "--ai-analyze",
        action="store_true",
        help="Invoke AI engine to analyze release notes for breaking changes.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Path to output markdown report (defaults to docs/UPSTREAM_UPDATES.md).",
    )

    args = parser.parse_args()
    comps = (
        [c.strip() for c in args.components.split(",") if c.strip()]
        if args.components
        else None
    )
    rep_path = args.report or (project_root / "docs" / "UPSTREAM_UPDATES.md")

    return run_upstream_check(
        components_filter=comps,
        use_ai=args.ai_analyze,
        output_report=rep_path,
    )


if __name__ == "__main__":
    sys.exit(main())
