#!/usr/bin/env python3
"""Component Trend Radar for NjordDeploy.

Measures Docker Hub adoption, maintenance freshness, and momentum to rank
self-hosted server components and identify trending services.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

CANDIDATES_FILE = "data/trend_radar_candidates.json"
HISTORY_FILE = "data/trend_radar_history.json"
METADATA_FILE = "config/components_metadata.json"
COMPONENTS_REPO_METADATA = (
    "/home/hvhoek/PycharmProjects/njord-deploy-components/components_metadata.json"
)


def load_candidates() -> List[Dict[str, Any]]:
    """Load candidates list."""
    if not os.path.exists(CANDIDATES_FILE):
        print(f"Error: {CANDIDATES_FILE} not found.", file=sys.stderr)
        return []
    with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history() -> Dict[str, Any]:
    """Load historical tracking data."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_history(history: Dict[str, Any]) -> None:
    """Save history database."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_existing_components() -> set[str]:
    """Get set of components already implemented in NjordDeploy."""
    existing: set[str] = set()
    for path in [COMPONENTS_REPO_METADATA, METADATA_FILE]:
        if os.path.exists(path):
            # noinspection PyBroadException
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    comps = data.get("components", {})
                    existing.update(comps.keys())
            except Exception:  # nosec B110
                pass
    return existing


DOCKER_HUB_REPO_REGEX = re.compile(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+$")


async def fetch_docker_hub_stats(
    session: aiohttp.ClientSession, docker_repo: str
) -> Dict[str, Any]:
    """Fetch pull count, star count, and last updated timestamp from Docker Hub."""
    if not docker_repo or not DOCKER_HUB_REPO_REGEX.match(docker_repo):
        return {"pulls": 0, "stars": 0, "last_updated": None, "source": "external"}

    parts = docker_repo.split("/")
    repo_first, repo_second = parts[0], parts[1]
    if repo_first == "library":
        url = f"https://hub.docker.com/v2/repositories/library/{repo_second}/"
    else:
        url = f"https://hub.docker.com/v2/repositories/{repo_first}/{repo_second}/"

    headers = {
        "User-Agent": "NjordDeploy-TrendRadar/1.0",
        "Accept": "application/json",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "pulls": data.get("pull_count", 0),
                    "stars": data.get("star_count", 0),
                    "last_updated": data.get("last_updated"),
                    "source": "dockerhub",
                }
            if resp.status == 404:
                return {
                    "pulls": 0,
                    "stars": 0,
                    "last_updated": None,
                    "source": "not_found",
                }
    # noinspection PyBroadException
    except Exception:  # nosec B110
        pass
    return {"pulls": 0, "stars": 0, "last_updated": None, "source": "error"}


def calculate_maintenance_factor(last_updated_iso: Optional[str]) -> float:
    """Calculate maintenance factor (1.0 to 0.1) based on days since last update."""
    if not last_updated_iso:
        return 0.8

    try:
        clean_date = last_updated_iso.replace("Z", "+00:00")
        updated_dt = datetime.fromisoformat(clean_date)
        now_dt = datetime.now(timezone.utc)
        days_diff = (now_dt - updated_dt).days

        if days_diff <= 90:
            return 1.0
        if days_diff <= 180:
            return 0.8
        if days_diff <= 365:
            return 0.5
        return 0.2
    except Exception:
        return 0.8


def calculate_wams_score(
    pulls: int,
    maintenance_factor: float,
    previous_pulls: Optional[int],
) -> float:
    """Calculate Weighted Adoption & Momentum Score (WAMS)."""
    if pulls <= 0:
        return 0.0
    effective_pulls = max(pulls, 1000)
    adoption_scale = math.log10(effective_pulls)

    momentum = 1.0
    if previous_pulls and previous_pulls > 0 and pulls >= previous_pulls:
        growth_rate = (pulls - previous_pulls) / float(previous_pulls)
        momentum = max(0.8, min(2.0, 1.0 + growth_rate))

    score = adoption_scale * momentum * maintenance_factor
    return round(score, 2)


async def run_radar(limit: int = 125, update_history: bool = True) -> None:
    """Run full radar scan across candidates."""
    candidates = load_candidates()
    if not candidates:
        print("No candidates configured.")
        return

    history = load_history()
    existing_comps = get_existing_components()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[*] Scanning {len(candidates)} candidates for trending server metrics...")

    results = []
    connector = aiohttp.TCPConnector(limit_per_host=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_docker_hub_stats(session, c.get("docker_repo", ""))
            for c in candidates
        ]
        stats_list = await asyncio.gather(*tasks)

    for cand, stats in zip(candidates, stats_list):
        cid = cand["id"]
        pulls = stats["pulls"]
        stars = stats["stars"]
        last_updated = stats["last_updated"]

        cand_history = history.get(cid, {})
        snapshots = cand_history.get("snapshots", [])
        prev_pulls = None
        if snapshots:
            last_snap = snapshots[-1]
            prev_pulls = last_snap.get("pulls")

        m_factor = calculate_maintenance_factor(last_updated)
        score = calculate_wams_score(pulls, m_factor, prev_pulls)
        in_njord = cid in existing_comps

        item = {
            "id": cid,
            "name": cand["name"],
            "category": cand.get("category", "General"),
            "pulls": pulls,
            "stars": stars,
            "last_updated": last_updated,
            "score": score,
            "in_njord": in_njord,
            "docker_repo": cand.get("docker_repo", ""),
        }
        results.append(item)

        if update_history and pulls > 0:
            if cid not in history:
                history[cid] = {"name": cand["name"], "snapshots": []}
            current_snaps = history[cid]["snapshots"]
            if not any(s.get("date") == today_str for s in current_snaps):
                current_snaps.append(
                    {"date": today_str, "pulls": pulls, "stars": stars, "score": score}
                )
                if len(current_snaps) > 24:
                    history[cid]["snapshots"] = current_snaps[-24:]

    if update_history:
        save_history(history)

    results.sort(key=lambda x: (x["score"], x["pulls"]), reverse=True)
    display_results = results[:limit]

    hdr_line = "=" * 90
    sep_line = "-" * 90
    print("\n" + hdr_line)
    print(f"  NJORDDEPLOY COMPONENT TREND RADAR (TOP {len(display_results)})")
    print(hdr_line)
    print(
        f"{'#':<4} {'Component':<22} {'Categorie':<20} "
        f"{'Pulls':<12} {'Score':<8} {'Status':<10}"
    )
    print(sep_line)

    missing_top: List[Dict[str, Any]] = []

    for idx, r in enumerate(display_results, 1):
        status = "✅ In repo" if r["in_njord"] else "❌ Ontbreekt"
        pulls_fmt = f"{r['pulls']:,}" if r["pulls"] > 0 else "GHCR / Ext"
        print(
            f"{idx:<4} {r['name']:<22} {r['category']:<20} "
            f"{pulls_fmt:<12} {r['score']:<8.2f} {status:<10}"
        )

        if not r["in_njord"]:
            missing_top.append(r)

    print(sep_line)
    in_repo_count = len(display_results) - len(missing_top)
    print(
        f"Totaal in lijst: {len(display_results)} | "
        f"Reeds in NjordDeploy: {in_repo_count} | "
        f"Ontbreekt: {len(missing_top)}"
    )

    if missing_top:
        print("\n[*] Aanbevolen stijgers / ontbrekende trending kandidaten:")
        for m in missing_top[:15]:
            p_info = f"({m['pulls']:,} pulls)" if m["pulls"] > 0 else ""
            print(f"  - [{m['name']}] ({m['category']}) {p_info} -> ID: {m['id']}")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="NjordDeploy Component Trend Radar")
    parser.add_argument(
        "--limit",
        type=int,
        default=125,
        help="Number of items to display (default: 125)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not update history database",
    )
    args = parser.parse_args()

    asyncio.run(run_radar(limit=args.limit, update_history=not args.no_save))


if __name__ == "__main__":
    main()
