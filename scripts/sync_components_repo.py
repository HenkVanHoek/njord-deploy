#!/usr/bin/env python3
"""
scripts/sync_components_repo.py

Synchronizes verified component definitions, templates, and metadata
from the njord-deploy source repository to the separate
njord-deploy-components repository.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("sync_components_repo")


def parse_args() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="Sync components metadata and templates to njord-deploy-components."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Path to the source njord-deploy repository (defaults to auto-detect).",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Path to the njord-deploy-components repository.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check and report differences without copying files.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Create a git commit in the target repository after syncing.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the commit to remote origin in the target repository.",
    )
    parser.add_argument(
        "--message",
        type=str,
        default=None,
        help="Custom commit message.",
    )
    parser.add_argument(
        "--sync-site",
        action="store_true",
        help="Also sync metadata and SUPPORTED_SERVICES.md to njord-deploy-site.",
    )
    parser.add_argument(
        "--site-dir",
        type=Path,
        default=None,
        help="Path to the njord-deploy-site repository.",
    )
    return parser.parse_args()


def get_default_target_dir(source_root: Path) -> Path:
    """Resolves the default target directory for njord-deploy-components."""
    env_path = os.environ.get("COMPONENTS_REPO_PATH")
    if env_path:
        return Path(env_path).resolve()
    return (source_root.parent / "njord-deploy-components").resolve()


def get_default_site_dir(source_root: Path) -> Path:
    """Resolves the default directory for njord-deploy-site."""
    env_path = os.environ.get("SITE_REPO_PATH")
    if env_path:
        return Path(env_path).resolve()
    return (source_root.parent / "njord-deploy-site").resolve()


def validate_metadata_file(metadata_path: Path) -> dict:
    """Validates that the metadata file exists and contains valid JSON."""
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid metadata structure in {metadata_path}, expected a JSON object."
        )
    return data


def _files_differ(file_a: Path, file_b: Path) -> bool:
    """Checks if two files differ in content, avoiding mtime cache artifacts."""
    if file_a.stat().st_size != file_b.stat().st_size:
        return True
    return file_a.read_bytes() != file_b.read_bytes()


def sync_templates(
    src_dir: Path, dst_dir: Path, check_only: bool = False
) -> tuple[int, int, int]:
    """
    Synchronizes files from src_dir to dst_dir.
    Removes files and directories in dst_dir that do not exist in src_dir.
    Returns (updated_count, deleted_count, unchanged_count).
    """
    updated_count = 0
    deleted_count = 0
    unchanged_count = 0

    if not src_dir.exists():
        raise FileNotFoundError(f"Source templates directory not found: {src_dir}")

    # 1. Copy new / modified files from src to dst
    for root, _, files in os.walk(src_dir):
        rel_root = Path(root).relative_to(src_dir)
        target_root = dst_dir / rel_root

        for filename in files:
            src_file = Path(root) / filename
            dst_file = target_root / filename

            needs_copy = False
            if not dst_file.exists():
                needs_copy = True
            elif _files_differ(src_file, dst_file):
                needs_copy = True

            if needs_copy:
                updated_count += 1
                if not check_only:
                    target_root.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
            else:
                unchanged_count += 1

    # 2. Prune obsolete files in dst that no longer exist in src
    if dst_dir.exists():
        for root, _, files in os.walk(dst_dir):
            rel_root = Path(root).relative_to(dst_dir)
            source_root_check = src_dir / rel_root

            for filename in files:
                dst_file = Path(root) / filename
                src_file_check = source_root_check / filename

                if not src_file_check.exists():
                    deleted_count += 1
                    if not check_only:
                        dst_file.unlink()

        # Remove empty directories in dst (bottom-up)
        if not check_only:
            for root, dirs, _ in os.walk(dst_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    # next(iter(...), None) for safe defensive check
                    first_entry = next(iter(dir_path.iterdir()), None)
                    if first_entry is None:
                        dir_path.rmdir()

    return updated_count, deleted_count, unchanged_count


def sync_metadata(src_file: Path, dst_file: Path, check_only: bool = False) -> bool:
    """
    Synchronizes the metadata JSON file if different.
    Returns True if updated, False if unchanged.
    """
    needs_copy = False
    if not dst_file.exists():
        needs_copy = True
    elif _files_differ(src_file, dst_file):
        needs_copy = True

    if needs_copy and not check_only:
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)

    return needs_copy


def run_git_command(
    args: list[str], cwd: Path, check: bool = True
) -> subprocess.CompletedProcess:
    """Executes a git command in the target directory."""
    logger.info("Running git in %s: %s", cwd, " ".join(args))
    return subprocess.run(  # nosec B603
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def commit_and_push(
    target_repo: Path, commit_msg: Optional[str], push: bool = False
) -> None:
    """Stages, commits, and optionally pushes changes in the target repository."""
    # Stage synced artifacts
    run_git_command(
        ["add", "components_metadata.json", "component_templates"],
        cwd=target_repo,
    )

    # Check status
    status_res = run_git_command(["status", "--porcelain"], cwd=target_repo)
    if not status_res.stdout.strip():
        logger.info("No changes to commit in target repository.")
        return

    msg = (
        commit_msg
        or "chore(components): sync verified templates and metadata from njord-deploy"
    )
    run_git_command(["commit", "-m", msg], cwd=target_repo)
    logger.info("Committed changes with message: %s", msg)

    if push:
        branch_res = run_git_command(
            ["rev-parse", "--abbrev-ref", "HEAD"], cwd=target_repo
        )
        active_branch = branch_res.stdout.strip() or "main"
        logger.info("Pushing to origin/%s...", active_branch)
        run_git_command(["push", "origin", active_branch], cwd=target_repo)
        logger.info("Successfully pushed to origin/%s.", active_branch)


def sync_site_repo(
    source_root: Path,
    site_repo: Path,
    check_only: bool = False,
    commit: bool = False,
    push: bool = False,
    custom_msg: Optional[str] = None,
) -> None:
    """Synchronizes metadata and documentation to the njord-deploy-site repository."""
    if not site_repo.exists() or not (site_repo / ".git").exists():
        logger.warning(
            "Site repository does not exist or is not a git repo: %s", site_repo
        )
        return

    logger.info("Synchronizing with site repository: %s", site_repo)
    source_metadata = source_root / "config" / "components_metadata.json"
    target_metadata = (
        site_repo / "src" / "site_app" / "static" / "components_metadata.json"
    )

    metadata_updated = sync_metadata(
        source_metadata, target_metadata, check_only=check_only
    )
    if metadata_updated:
        action = "Would update" if check_only else "Updated"
        logger.info("%s site components_metadata.json", action)

    # Sync docs/SUPPORTED_SERVICES.md if present
    source_supported = source_root / "docs" / "SUPPORTED_SERVICES.md"
    target_supported = (
        site_repo / "src" / "site_app" / "static" / "docs" / "SUPPORTED_SERVICES.md"
    )
    if source_supported.exists():
        doc_updated = sync_metadata(
            source_supported, target_supported, check_only=check_only
        )
        if doc_updated:
            action = "Would update" if check_only else "Updated"
            logger.info("%s site SUPPORTED_SERVICES.md", action)

    if check_only:
        return

    if commit or push:
        rel_files = [
            str(target_metadata.relative_to(site_repo)),
            str(target_supported.relative_to(site_repo)),
        ]
        run_git_command(["add"] + rel_files, cwd=site_repo)
        status_res = run_git_command(["status", "--porcelain"], cwd=site_repo)
        if not status_res.stdout.strip():
            logger.info("No changes to commit in site repository.")
            return

        msg = (
            custom_msg
            or "chore(site): sync verified metadata and docs from njord-deploy"
        )
        run_git_command(["commit", "-m", msg], cwd=site_repo)
        logger.info("Committed changes in site repository: %s", msg)

        if push:
            branch_res = run_git_command(
                ["rev-parse", "--abbrev-ref", "HEAD"], cwd=site_repo
            )
            branch = branch_res.stdout.strip() or "master"
            logger.info("Pushing to site remote origin/%s...", branch)
            run_git_command(["push", "origin", branch], cwd=site_repo)
            logger.info("Successfully pushed site repository.")


def main() -> int:
    """Main execution entry point."""
    args = parse_args()
    source_root = (args.source or Path(__file__).resolve().parent.parent).resolve()
    source_metadata = source_root / "config" / "components_metadata.json"
    source_templates = source_root / "component_templates"

    target_repo = args.target or get_default_target_dir(source_root)
    target_metadata = target_repo / "components_metadata.json"
    target_templates = target_repo / "component_templates"

    logger.info("Source repository: %s", source_root)
    logger.info("Target repository: %s", target_repo)

    if not target_repo.exists() or not (target_repo / ".git").exists():
        logger.error(
            "Target repository does not exist or is not a valid git repo: %s",
            target_repo,
        )
        return 1

    # Validate source metadata
    logger.info("Validating source metadata: %s", source_metadata)
    metadata_data = validate_metadata_file(source_metadata)
    comp_count = len(metadata_data.get("components", {}))
    pkg_count = len(metadata_data.get("packages", {}))
    logger.info(
        "Source metadata is valid JSON with %d components and %d packages.",
        comp_count,
        pkg_count,
    )

    # Sync metadata
    metadata_changed = sync_metadata(
        source_metadata, target_metadata, check_only=args.check
    )
    if metadata_changed:
        action = "Would update" if args.check else "Updated"
        logger.info("%s components_metadata.json.", action)
    else:
        logger.info("components_metadata.json is already up-to-date.")

    # Sync templates
    updated, deleted, unchanged = sync_templates(
        source_templates, target_templates, check_only=args.check
    )
    logger.info(
        "Templates summary: %d updated/added, %d deleted, %d unchanged.",
        updated,
        deleted,
        unchanged,
    )

    # Commit and push components repo if requested
    if not args.check and (args.commit or args.push):
        commit_and_push(
            target_repo=target_repo,
            commit_msg=args.message,
            push=args.push,
        )

    # Optionally sync site repository
    if args.sync_site:
        site_repo = args.site_dir or get_default_site_dir(source_root)
        sync_site_repo(
            source_root=source_root,
            site_repo=site_repo,
            check_only=args.check,
            commit=args.commit,
            push=args.push,
            custom_msg=args.message,
        )

    if args.check:
        logger.info("Check complete (dry-run mode). No files were modified.")
        return 0

    logger.info("Components synchronization finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
