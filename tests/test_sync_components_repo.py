"""
tests/test_sync_components_repo.py

Unit tests for scripts/sync_components_repo.py.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.sync_components_repo import (
    commit_and_push,
    get_default_target_dir,
    main,
    run_git_command,
    sync_metadata,
    sync_templates,
    validate_metadata_file,
)


def test_get_default_target_dir() -> None:
    source_root = Path("/fake/path/njord-deploy")
    with patch.dict("os.environ", {}, clear=True):
        target = get_default_target_dir(source_root)
        assert target == (source_root.parent / "njord-deploy-components").resolve()

    with patch.dict("os.environ", {"COMPONENTS_REPO_PATH": "/custom/path"}):
        target = get_default_target_dir(source_root)
        assert target == Path("/custom/path").resolve()


def test_validate_metadata_file(tmp_path: Path) -> None:
    meta_file = tmp_path / "components_metadata.json"
    data: dict[str, Any] = {"components": {"caddy": {}}, "packages": {}}
    meta_file.write_text(json.dumps(data), encoding="utf-8")

    result = validate_metadata_file(meta_file)
    assert result == data

    # Missing file
    non_existent = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        validate_metadata_file(non_existent)

    # Invalid JSON structure (not a dict)
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("['not', 'a', 'dict']", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_metadata_file(invalid_file)


def test_sync_metadata(tmp_path: Path) -> None:
    src_file = tmp_path / "src" / "metadata.json"
    dst_file = tmp_path / "dst" / "metadata.json"
    src_file.parent.mkdir(parents=True)

    src_file.write_text('{"version": 1}', encoding="utf-8")

    # 1. Target doesn't exist -> copies
    updated = sync_metadata(src_file, dst_file, check_only=False)
    assert updated is True
    assert dst_file.exists()
    assert dst_file.read_text(encoding="utf-8") == '{"version": 1}'

    # 2. Both identical -> skips
    updated = sync_metadata(src_file, dst_file, check_only=False)
    assert updated is False

    # 3. Source changed, check_only=True -> reports True but does not overwrite
    src_file.write_text('{"version": 2}', encoding="utf-8")
    updated = sync_metadata(src_file, dst_file, check_only=True)
    assert updated is True
    assert dst_file.read_text(encoding="utf-8") == '{"version": 1}'

    # 4. Actual update
    updated = sync_metadata(src_file, dst_file, check_only=False)
    assert updated is True
    assert dst_file.read_text(encoding="utf-8") == '{"version": 2}'


def test_sync_templates(tmp_path: Path) -> None:
    src_dir = tmp_path / "src_templates"
    dst_dir = tmp_path / "dst_templates"

    # Setup source templates
    (src_dir / "caddy").mkdir(parents=True)
    (src_dir / "caddy" / "docker-compose.template.yml").write_text("caddy_v1")
    (src_dir / "vaultwarden").mkdir(parents=True)
    (src_dir / "vaultwarden" / "docker-compose.template.yml").write_text("vw_v1")

    # Setup obsolete file in dst
    (dst_dir / "obsolete").mkdir(parents=True)
    (dst_dir / "obsolete" / "docker-compose.template.yml").write_text("old")

    # Run check_only
    updated, deleted, unchanged = sync_templates(src_dir, dst_dir, check_only=True)
    assert updated == 2
    assert deleted == 1
    assert unchanged == 0
    assert not (dst_dir / "caddy").exists()

    # Run actual sync
    updated, deleted, unchanged = sync_templates(src_dir, dst_dir, check_only=False)
    assert updated == 2
    assert deleted == 1
    assert unchanged == 0

    assert (dst_dir / "caddy" / "docker-compose.template.yml").read_text() == "caddy_v1"
    assert (
        dst_dir / "vaultwarden" / "docker-compose.template.yml"
    ).read_text() == "vw_v1"
    assert not (dst_dir / "obsolete").exists()

    # Run again without changes
    updated, deleted, unchanged = sync_templates(src_dir, dst_dir, check_only=False)
    assert updated == 0
    assert deleted == 0
    assert unchanged == 2


def test_run_git_command(tmp_path: Path) -> None:
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_run.return_value = mock_res
        res = run_git_command(["status"], cwd=tmp_path)
        assert res == mock_res
        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )


def test_commit_and_push(tmp_path: Path) -> None:
    with patch("scripts.sync_components_repo.run_git_command") as mock_git:
        # 1. No changes detected in status
        status_empty = MagicMock()
        status_empty.stdout = ""
        mock_git.return_value = status_empty

        commit_and_push(tmp_path, commit_msg=None, push=True)
        # Should call git add and git status only
        assert mock_git.call_count == 2

        mock_git.reset_mock()

        # 2. Changes detected, push=True
        status_changes = MagicMock()
        status_changes.stdout = "M components_metadata.json\n"
        branch_res = MagicMock()
        branch_res.stdout = "main\n"

        # Side effects for add, status, commit, rev-parse, push
        mock_git.side_effect = [
            MagicMock(),
            status_changes,
            MagicMock(),
            branch_res,
            MagicMock(),
        ]

        commit_and_push(tmp_path, commit_msg="chore(test): update", push=True)
        assert mock_git.call_count == 5


def test_main_cli_dry_run(tmp_path: Path) -> None:
    source_dir = tmp_path / "njord-deploy"
    target_dir = tmp_path / "njord-deploy-components"
    (source_dir / "config").mkdir(parents=True)
    (source_dir / "component_templates").mkdir(parents=True)
    (target_dir / ".git").mkdir(parents=True)
    (target_dir / "component_templates").mkdir(parents=True)

    meta_file = source_dir / "config" / "components_metadata.json"
    meta_file.write_text(json.dumps({"components": {}}), encoding="utf-8")

    test_args = [
        "sync_components_repo.py",
        "--source",
        str(source_dir),
        "--target",
        str(target_dir),
        "--check",
    ]
    with patch("sys.argv", test_args):
        code = main()
        assert code == 0
