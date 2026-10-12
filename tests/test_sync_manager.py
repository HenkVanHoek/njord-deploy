# tests/test_sync_manager.py

import io
import json
import shutil
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.managers.sync_manager import SyncManager


class MockResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code


@pytest.fixture
def temp_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.managers.sync_manager.user_data_dir",
        lambda appname, appauthor: str(tmp_path),
    )
    monkeypatch.setattr(
        "appdirs.user_data_dir",
        lambda appname, appauthor: str(tmp_path),
    )

    local_dir = tmp_path / "local"
    local_dir.mkdir()
    local_meta = local_dir / "components_metadata.json"
    local_meta.write_text(
        json.dumps(
            {
                "components": {
                    "test-comp": {
                        "name": "Test Component",
                        "group": "general",
                        "ports": ["80:80"],
                    }
                }
            }
        )
    )

    local_templates = local_dir / "component_templates"
    local_templates.mkdir()
    comp_template_dir = local_templates / "test-comp"
    comp_template_dir.mkdir()
    (comp_template_dir / "docker-compose.template.yml").write_text(
        "services:\n  njorddeploy-test:\n    image: test\n"
    )

    return local_meta, local_templates


def test_sync_manager_init(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)
    assert manager.local_metadata_path == local_meta
    assert manager.local_templates_path == local_templates
    assert manager.cache_dir.name == "remote_components_cache"


def test_compare_component_synced(temp_dirs, monkeypatch):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Mock remote cache to be identical
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    manager.cache_metadata_path.write_text(local_meta.read_text())
    manager.cache_templates_path.mkdir(parents=True, exist_ok=True)
    remote_comp_dir = manager.cache_templates_path / "test-comp"
    remote_comp_dir.mkdir()
    (remote_comp_dir / "docker-compose.template.yml").write_text(
        "services:\n  njorddeploy-test:\n    image: test\n"
    )

    status = manager.compare_component("test-comp")
    assert status == "synced"


def test_compare_component_modified_meta(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Mock remote cache with modified metadata
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    manager.cache_metadata_path.write_text(
        json.dumps(
            {
                "components": {
                    "test-comp": {
                        "name": "Test Component Changed",
                        "group": "general",
                    }
                }
            }
        )
    )
    manager.cache_templates_path.mkdir(parents=True, exist_ok=True)
    remote_comp_dir = manager.cache_templates_path / "test-comp"
    remote_comp_dir.mkdir()
    (remote_comp_dir / "docker-compose.template.yml").write_text(
        "services:\n  njorddeploy-test:\n    image: test\n"
    )

    status = manager.compare_component("test-comp")
    assert status == "modified"


def test_compare_component_modified_template(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Mock remote cache with modified template
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    manager.cache_metadata_path.write_text(local_meta.read_text())
    manager.cache_templates_path.mkdir(parents=True, exist_ok=True)
    remote_comp_dir = manager.cache_templates_path / "test-comp"
    remote_comp_dir.mkdir()
    (remote_comp_dir / "docker-compose.template.yml").write_text(
        "services:\n  njorddeploy-test:\n    image: test-changed\n"
    )

    status = manager.compare_component("test-comp")
    assert status == "modified"


def test_compare_component_local_only(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Mock remote cache without the component
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    manager.cache_metadata_path.write_text(json.dumps({"components": {}}))
    manager.cache_templates_path.mkdir(parents=True, exist_ok=True)

    status = manager.compare_component("test-comp")
    assert status == "local_only"


def test_compare_component_remote_only(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Mock remote cache with a new component
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    manager.cache_metadata_path.write_text(
        json.dumps(
            {
                "components": {
                    "remote-comp": {
                        "name": "Remote Only",
                        "group": "general",
                    }
                }
            }
        )
    )
    manager.cache_templates_path.mkdir(parents=True, exist_ok=True)
    remote_comp_dir = manager.cache_templates_path / "remote-comp"
    remote_comp_dir.mkdir()
    (remote_comp_dir / "docker-compose.template.yml").write_text("...")

    status = manager.compare_component("remote-comp")
    assert status == "remote_only"


def test_sync_component(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Setup remote cache with modified metadata and template
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    manager.cache_metadata_path.write_text(
        json.dumps(
            {
                "components": {
                    "test-comp": {
                        "name": "Updated Name",
                        "group": "general",
                    }
                }
            }
        )
    )
    manager.cache_templates_path.mkdir(parents=True, exist_ok=True)
    remote_comp_dir = manager.cache_templates_path / "test-comp"
    remote_comp_dir.mkdir()
    (remote_comp_dir / "docker-compose.template.yml").write_text(
        "services:\n  njorddeploy-test:\n    image: updated-image\n"
    )

    # Act
    success = manager.sync_component("test-comp")

    # Assert
    assert success is True
    # Verify local metadata updated
    local_data = json.loads(local_meta.read_text())
    assert local_data["components"]["test-comp"]["name"] == "Updated Name"

    # Verify local template updated
    local_tpl = (
        local_templates / "test-comp" / "docker-compose.template.yml"
    ).read_text()
    assert "updated-image" in local_tpl


def test_fetch_from_remote(temp_dirs, monkeypatch):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # 1. Prepare in-memory mock zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # GitHub ZIP wraps in repo-name-branch/
        zip_file.writestr(
            "njord-deploy-components-main/components_metadata.json",
            json.dumps({"components": {"fetched-comp": {"name": "Fetched"}}}),
        )
        zip_file.writestr(
            "njord-deploy-components-main/component_templates/"
            "fetched-comp/docker-compose.template.yml",
            "services:\n  fetched:\n    image: fetched\n",
        )

    zip_buffer.seek(0)
    mock_zip_content = zip_buffer.getvalue()

    # 2. Mock requests.get to return this mock ZIP
    def mock_get(url, *args, **kwargs):
        return MockResponse(mock_zip_content, 200)

    import requests  # type: ignore

    monkeypatch.setattr(requests, "get", mock_get)

    # Act
    success = manager.fetch_from_remote()

    # Assert
    assert success is True
    assert manager.cache_metadata_path.exists()
    assert (
        manager.cache_templates_path / "fetched-comp" / "docker-compose.template.yml"
    ).exists()


def test_validate_metadata_header_valid(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Write a template with a valid header
    comp_dir = local_templates / "test-comp"
    comp_dir.mkdir(parents=True, exist_ok=True)
    header = (
        '# status: "untested"\n'
        '# last_tested_version: "none"\n'
        '# platform_notes: "None"\n'
        '# breaking_changes: "None"\n'
    )
    (comp_dir / "docker-compose.template.yml").write_text(
        header + "services:\n  test:\n    image: test\n"
    )

    assert manager.validate_metadata_header("test-comp") is True


def test_validate_metadata_header_invalid(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Write a template with an invalid/incomplete header
    comp_dir = local_templates / "test-comp"
    comp_dir.mkdir(parents=True, exist_ok=True)
    header = '# status: "untested"\n' '# last_tested_version: "none"\n'
    (comp_dir / "docker-compose.template.yml").write_text(
        header + "services:\n  test:\n    image: test\n"
    )

    assert manager.validate_metadata_header("test-comp") is False


def test_check_write_access_success(temp_dirs, monkeypatch):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    import subprocess

    class MockCompletedProcess:
        def __init__(self, returncode, stderr):
            self.returncode = returncode
            self.stderr = stderr
            self.stdout = ""

    def mock_run(*_args, **_kwargs):
        # Simulate successful push dry run (return code 1 with rejected
        # non-permission error is success)
        return MockCompletedProcess(1, "To github.com:...\n ! [rejected] main -> main")

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert manager.check_write_access() is True


def test_check_write_access_fail(temp_dirs, monkeypatch):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    import subprocess

    class MockCompletedProcess:
        def __init__(self, returncode, stderr):
            self.returncode = returncode
            self.stderr = stderr
            self.stdout = ""

    def mock_run(*_args, **_kwargs):
        # Simulate failed push dry run due to permission denied
        return MockCompletedProcess(128, "Permission denied (publickey)")

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert manager.check_write_access() is False


def test_fetch_from_remote_offline_graceful(temp_dirs, monkeypatch):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    import requests

    def mock_get(*_args, **_kwargs):
        raise requests.exceptions.ConnectionError("Failed to connect")

    monkeypatch.setattr("requests.get", mock_get)
    result = manager.fetch_from_remote(timeout=3)
    assert result is False
    assert manager.is_offline is True


def test_mark_component_tested_and_timestamp(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Test mark_component_tested
    success = manager.mark_component_tested("test-comp", test_status="stable")
    assert success is True

    meta = manager.get_local_component_meta("test-comp")
    assert "last_tested" in meta
    assert meta["test_status"] == "stable"

    # Test update_component_timestamp
    success_ts = manager.update_component_timestamp("test-comp")
    assert success_ts is True

    meta_updated = manager.get_local_component_meta("test-comp")
    assert "last_updated" in meta_updated

    # Verify status report includes timestamps
    status = manager.get_sync_status()
    assert "component_timestamps" in status
    assert "test-comp" in status["component_timestamps"]
    assert status["component_timestamps"]["test-comp"]["test_status"] == "stable"


def test_repo_config_and_urls(monkeypatch):
    monkeypatch.delenv("COMPONENTS_REPO_URL", raising=False)
    monkeypatch.delenv("PI_SELFHOSTING_COMPONENTS_REPO", raising=False)
    config = SyncManager.get_repo_config()
    assert config["url"] == "HenkVanHoek/njord-deploy-components"
    assert config["is_enabled"] is True
    assert SyncManager.is_remote_sync_enabled() is True

    ssh_url, https_url = SyncManager.get_repo_urls()
    assert "git@github.com:HenkVanHoek/njord-deploy-components.git" in ssh_url
    assert "https://github.com/HenkVanHoek/njord-deploy-components.git" in https_url

    # Disabled / local mode
    monkeypatch.setenv("COMPONENTS_REPO_URL", "none")
    assert SyncManager.is_remote_sync_enabled() is False

    monkeypatch.setenv("COMPONENTS_REPO_URL", "local")
    assert SyncManager.is_remote_sync_enabled() is False

    # Custom GitLab URL
    monkeypatch.setenv(
        "COMPONENTS_REPO_URL", "https://gitlab.example.com/org/custom-repo"
    )
    ssh_u, https_u = SyncManager.get_repo_urls()
    assert https_u == "https://gitlab.example.com/org/custom-repo.git"


def test_validate_remote_repo_local():
    valid, msg = SyncManager.validate_remote_repo("none")
    assert valid is True
    assert "Local-only" in msg

    valid, msg = SyncManager.validate_remote_repo("local")
    assert valid is True


def test_validate_remote_repo_mock(monkeypatch):
    import requests

    class MockHead:
        def __init__(self, status_code):
            self.status_code = status_code

    monkeypatch.setattr(requests, "head", lambda *args, **kwargs: MockHead(200))
    valid, msg = SyncManager.validate_remote_repo("HenkVanHoek/njord-deploy-components")
    assert valid is True
    assert "reachable" in msg

    # Direct zip url and gitlab url
    valid_zip, _ = SyncManager.validate_remote_repo("https://example.com/archive.zip")
    assert valid_zip is True

    valid_gl, _ = SyncManager.validate_remote_repo(
        "https://gitlab.com/test/repo", token="secret"
    )
    assert valid_gl is True

    # Fallback to GET when HEAD returns 405
    monkeypatch.setattr(requests, "head", lambda *args, **kwargs: MockHead(405))
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockHead(206))
    valid_fallback, _ = SyncManager.validate_remote_repo(
        "HenkVanHoek/njord-deploy-components"
    )
    assert valid_fallback is True

    # When request fails or raises Exception
    monkeypatch.setattr(requests, "head", lambda *args, **kwargs: MockHead(404))
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockHead(404))
    valid_404, _ = SyncManager.validate_remote_repo(
        "HenkVanHoek/njord-deploy-components"
    )
    assert valid_404 is False

    def mock_err(*args, **kwargs):
        raise ConnectionError("DNS resolution failed")

    monkeypatch.setattr(requests, "head", mock_err)
    valid_err, err_msg = SyncManager.validate_remote_repo(
        "HenkVanHoek/njord-deploy-components"
    )
    assert valid_err is False
    assert "Connection failed" in err_msg


def test_sync_all_and_cache(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # When remote cache doesn't exist -> False
    assert manager.sync_all() is False

    # Create remote cache
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    manager.cache_metadata_path.write_text(json.dumps({"components": {}}))
    manager.cache_templates_path.mkdir(parents=True, exist_ok=True)

    success = manager.sync_all(force=True)
    assert success is True
    assert local_meta.read_text() == json.dumps({"components": {}})


def test_validate_metadata_header_cases(temp_dirs):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # 1. Nonexistent component
    assert manager.validate_metadata_header("ghost-comp") is False

    # 2. Existing component missing one header
    comp_dir = local_templates / "test-comp"
    tpl = comp_dir / "docker-compose.template.yml"
    tpl.write_text(
        '# status: "testing"\n'
        '# last_tested_version: "1.0"\n'
        '# platform_notes: "None"\n'
        "services:\n",
        encoding="utf-8",
    )
    assert manager.validate_metadata_header("test-comp") is False

    # 3. Existing component with all 4 headers
    tpl.write_text(
        '# status: "testing"\n'
        '# last_tested_version: "1.0"\n'
        '# platform_notes: "None"\n'
        '# breaking_changes: "None"\n'
        "services:\n",
        encoding="utf-8",
    )
    assert manager.validate_metadata_header("test-comp") is True


def test_check_write_access_details_and_git(temp_dirs, monkeypatch):
    import subprocess

    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Mock subprocess.run for dry run SSH
    mock_res_ssh = MagicMock()
    mock_res_ssh.returncode = 0
    mock_res_ssh.stderr = ""

    with patch.object(manager, "_prepare_git_repo", return_value="existing"):
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_res_ssh)
        has_write, msg = manager.check_write_access_details()
        assert has_write is True
        assert "SSH" in msg
        assert manager.check_write_access() is True

        # When SSH fails and HTTPS succeeds
        def fake_run(cmd, *args, **kwargs):
            first, *rest = cmd
            target = rest[-1] if rest else ""
            res = MagicMock()
            if "git@" in target:
                res.returncode = 128
                res.stderr = "Permission denied (publickey)"
            else:
                res.returncode = 0
                res.stderr = ""
            return res

        monkeypatch.setattr(subprocess, "run", fake_run)
        has_write_https, msg_https = manager.check_write_access_details()
        assert has_write_https is True
        assert "HTTPS" in msg_https


def test_upload_component_and_bulk_cases(temp_dirs, monkeypatch):
    import subprocess

    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # Initialize mock remote git repo directory
    manager.git_repo_dir.mkdir(parents=True, exist_ok=True)
    (manager.git_repo_dir / "components_metadata.json").write_text(
        json.dumps({"components": {}}), encoding="utf-8"
    )
    (manager.git_repo_dir / "component_templates").mkdir(parents=True, exist_ok=True)

    with patch.object(manager, "_prepare_git_repo", return_value="existing"):
        # 1. upload_component when no git changes
        mock_status = MagicMock()
        mock_status.stdout = ""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda cmd, *args, **kwargs: (
                mock_status if "status" in cmd else MagicMock(returncode=0)
            ),
        )
        assert manager.upload_component("test-comp") is True

        # 2. upload_component when local dir missing
        with pytest.raises(FileNotFoundError):
            manager.upload_component("missing-comp")

        # 3. upload_all_components with invalid header raises ValueError
        tpl = local_templates / "test-comp" / "docker-compose.template.yml"
        tpl.write_text("no headers\nservices:\n", encoding="utf-8")
        with pytest.raises(ValueError) as exc:
            manager.upload_all_components()
        assert "malformed metadata headers" in str(exc.value)

        # 4. upload_component with changes -> commits and pushes
        tpl.write_text(
            '# status: "testing"\n'
            '# last_tested_version: "1.0"\n'
            '# platform_notes: "None"\n'
            '# breaking_changes: "None"\n'
            "services:\n",
            encoding="utf-8",
        )
        mock_changed_status = MagicMock()
        mock_changed_status.stdout = " M components_metadata.json\n"
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda cmd, *args, **kwargs: (
                mock_changed_status if "status" in cmd else MagicMock(returncode=0)
            ),
        )
        assert manager.upload_component("test-comp") is True

        # 5. upload_all_components with changes -> bulk commits and pushes
        assert manager.upload_all_components() is True


def test_fetch_from_remote_git_and_zip(temp_dirs, monkeypatch):
    import subprocess

    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # 1. Disabled remote sync returns False
    monkeypatch.setenv("COMPONENTS_REPO_URL", "none")
    assert manager.fetch_from_remote() is False

    # 2. Git pull succeeds when git repo cache exists
    monkeypatch.delenv("COMPONENTS_REPO_URL", raising=False)
    manager.git_repo_dir.mkdir(parents=True, exist_ok=True)
    (manager.git_repo_dir / ".git").mkdir(parents=True, exist_ok=True)
    (manager.git_repo_dir / "components_metadata.json").write_text(
        json.dumps({"components": {}}), encoding="utf-8"
    )
    (manager.git_repo_dir / "component_templates").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: MagicMock(returncode=0)
    )
    assert manager.fetch_from_remote() is True
    assert manager.is_offline is False


def test_sync_manager_extended_edge_cases(temp_dirs, monkeypatch, tmp_path):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # 1. URL parsing branches in fetch_from_remote
    # 1a. .zip url
    monkeypatch.setenv("COMPONENTS_REPO_URL", "https://example.com/repo.zip")
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=404)
        assert manager.fetch_from_remote() is False

    # 1b. gitlab url
    monkeypatch.setenv("COMPONENTS_REPO_URL", "https://gitlab.com/org/repo.git")
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=500)
        assert manager.fetch_from_remote() is False

    # 1c. git pull exception fallback to zip
    monkeypatch.delenv("COMPONENTS_REPO_URL", raising=False)
    manager.git_repo_dir.mkdir(parents=True, exist_ok=True)
    (manager.git_repo_dir / ".git").mkdir(parents=True, exist_ok=True)
    with (
        patch("subprocess.run", side_effect=Exception("Git pull boom")),
        patch("requests.get") as mock_get,
    ):
        mock_get.return_value = MagicMock(status_code=403)
        assert manager.fetch_from_remote() is False

    # 1d. ZIP archive with no subdirectories
    empty_zip_bytes = io.BytesIO()
    with zipfile.ZipFile(empty_zip_bytes, "w") as zf:
        zf.writestr("some_file.txt", "content")
    empty_zip_data = empty_zip_bytes.getvalue()

    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, content=empty_zip_data)
        # Remove git repo dir to avoid git pull
        import shutil

        shutil.rmtree(manager.git_repo_dir)
        assert manager.fetch_from_remote() is False

    # 2. get_sync_status global out of sync branches
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    local_meta.write_text(
        json.dumps(
            {
                "components": {"comp-1": {}},
                "packages": {"pkg-1": {"name": "Package One"}},
                "_njorddeploy": {
                    "group_rules": {"rule-1": {}},
                    "group_order": ["grp-1"],
                },
            }
        ),
        encoding="utf-8",
    )
    manager.cache_metadata_path.write_text(
        json.dumps(
            {
                "components": {"comp-1": {}},
                "packages": {"pkg-1": {"name": "Changed Pkg"}},
                "_njorddeploy": {
                    "group_rules": {"rule-1": {}},
                    "group_order": ["grp-1"],
                },
            }
        ),
        encoding="utf-8",
    )
    status_pkg = manager.get_sync_status()
    assert status_pkg["global_metadata_out_of_sync"] is True

    # Rule mismatch
    manager.cache_metadata_path.write_text(
        json.dumps(
            {
                "components": {"comp-1": {}},
                "packages": {"pkg-1": {"name": "Package One"}},
                "_njorddeploy": {
                    "group_rules": {"rule-changed": {}},
                    "group_order": ["grp-1"],
                },
            }
        ),
        encoding="utf-8",
    )
    status_rule = manager.get_sync_status()
    assert status_rule["global_metadata_out_of_sync"] is True

    # Order mismatch
    manager.cache_metadata_path.write_text(
        json.dumps(
            {
                "components": {"comp-1": {}},
                "packages": {"pkg-1": {"name": "Package One"}},
                "_njorddeploy": {
                    "group_rules": {"rule-1": {}},
                    "group_order": ["grp-different"],
                },
            }
        ),
        encoding="utf-8",
    )
    status_order = manager.get_sync_status()
    assert status_order["global_metadata_out_of_sync"] is True

    # 3. mark_component_tested and update_component_timestamp
    assert manager.mark_component_tested("missing-comp") is False
    assert manager.update_component_timestamp("missing-comp") is False

    with patch("builtins.open", side_effect=OSError("Write permission denied")):
        assert manager.mark_component_tested("comp-1") is False
        assert manager.update_component_timestamp("comp-1") is False

    # 4. sync_component missing remote component or missing cache
    import shutil

    if manager.cache_metadata_path.exists():
        manager.cache_metadata_path.unlink()
    assert manager.sync_component("comp-1") is False

    manager.cache_metadata_path.write_text(
        json.dumps({"components": {}}), encoding="utf-8"
    )
    assert manager.sync_component("comp-1") is False

    # 5. upload_all_components: no changes vs push failure
    manager.git_repo_dir.mkdir(parents=True, exist_ok=True)
    with (
        patch.object(manager, "validate_metadata_header", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        # No changes
        mock_status = MagicMock(returncode=0, stdout="")
        mock_run.return_value = mock_status
        assert manager.upload_all_components() is True

        # Push failure
        mock_status_changed = MagicMock(returncode=0, stdout="M meta.json\n")

        def side_effect_run(cmd, *args, **kwargs):
            if "status" in cmd:
                return mock_status_changed
            if "push" in cmd:
                return MagicMock(returncode=1, stderr="Auth rejected")
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect_run
        with pytest.raises(RuntimeError, match="Git push failed"):
            manager.upload_all_components()

    # 6. Cache update exception handling
    with patch("builtins.open", side_effect=Exception("Cache disk full")):
        manager._update_cache_for_component("comp-1")

    with patch("shutil.copy2", side_effect=Exception("Disk error")):
        manager._update_cache_all()
        manager._update_cache_from_git_repo()


def test_sync_manager_additional_coverage(tmp_path, monkeypatch):
    """Verify edge-cases, error handling, and branches in SyncManager."""
    # 1. NJORD_DATA_DIR initialization
    custom_data = tmp_path / "custom_data"
    monkeypatch.setenv("NJORD_DATA_DIR", str(custom_data))
    local_meta = tmp_path / "meta.json"
    local_meta.write_text(
        json.dumps({"components": {"comp-1": {"name": "C1"}}}), encoding="utf-8"
    )
    local_tmpl = tmp_path / "templates"
    local_tmpl.mkdir()
    (local_tmpl / "comp-1").mkdir()
    (local_tmpl / "comp-1" / "docker-compose.template.yml").write_text(
        "# header", encoding="utf-8"
    )

    mgr = SyncManager(local_meta, local_tmpl)
    assert custom_data in mgr.cache_dir.parents or custom_data == mgr.cache_dir.parent

    # 2. get_repo_urls git@ branch
    monkeypatch.setenv("COMPONENTS_REPO_URL", "git@github.com:owner/repo.git")
    assert SyncManager.get_repo_urls() == (
        "git@github.com:owner/repo.git",
        "git@github.com:owner/repo.git",
    )

    # 3. validate_remote_repo https branch
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        ok, msg = SyncManager.validate_remote_repo("https://github.com/owner/repo.git")
        assert ok is True

    # 4. fetch_remote_components with token & existing cache_dir & generic exception
    mgr.cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("COMPONENTS_REPO_URL", "https://github.com/owner/repo")
    monkeypatch.setenv("COMPONENTS_REPO_TOKEN", "test-token")

    # Generic exception branch
    with patch("requests.get", side_effect=Exception("Unexpected crash")):
        assert mgr.fetch_from_remote(timeout=1) is False
        assert mgr.is_offline is True

    # 5. get_remote_component_meta & compare_component "not_found"
    mgr.cache_metadata_path.parent.mkdir(parents=True, exist_ok=True)
    mgr.cache_metadata_path.write_text(
        json.dumps({"components": {"comp-1": {"name": "Remote C1"}}}),
        encoding="utf-8",
    )
    assert mgr.get_remote_component_meta("comp-1") == {"name": "Remote C1"}
    assert mgr.compare_component("nonexistent") == "not_found"

    # 6. _compare_directories: differing file count & differing binary files
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()
    (d1 / "file1.txt").write_text("hello", encoding="utf-8")
    assert mgr._compare_directories(d1, d2) is False

    (d2 / "file1.txt").write_text("hello", encoding="utf-8")
    (d1 / "image.png").write_bytes(b"\x00\x01")
    (d2 / "image.png").write_bytes(b"\x00\x02")
    assert mgr._compare_directories(d1, d2) is False

    # 7. File write failure branches: mark_component_tested, update_component_timestamp
    local_meta.write_text(
        json.dumps({"components": {"comp-1": {"name": "C1"}}}), encoding="utf-8"
    )
    with patch("json.dump", side_effect=OSError("Disk full")):
        assert mgr.mark_component_tested("comp-1", "passed") is False
        assert mgr.update_component_timestamp("comp-1") is False

    # 8. sync_component & sync_all copy exceptions and missing "components" key in local
    mgr.cache_metadata_path.write_text(
        json.dumps({"components": {"comp-1": {"name": "Remote C1"}}}),
        encoding="utf-8",
    )
    (mgr.cache_templates_path / "comp-1").mkdir(parents=True, exist_ok=True)
    local_meta.write_text(json.dumps({}), encoding="utf-8")
    with patch("json.dump", side_effect=OSError("Disk write error")):
        assert mgr.sync_component("comp-1") is False

    with patch("shutil.copytree", side_effect=OSError("Copy failed")):
        assert mgr.sync_component("comp-1") is False
        assert mgr.sync_all() is False

    # 9. check_write_access_details exception in SSH and HTTPS subprocess
    with patch.object(mgr, "_prepare_git_repo"):
        with patch("subprocess.run", side_effect=OSError("Subprocess error")):
            has_w, msg_w = mgr.check_write_access_details()
            assert has_w is False
            assert "Subprocess error" in msg_w

    # 10. _prepare_git_repo: git pull success, git pull fail (re-clone),
    # https clone success
    mgr.git_repo_dir.mkdir(parents=True, exist_ok=True)
    (mgr.git_repo_dir / ".git").mkdir()

    # Git pull success
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        assert mgr._prepare_git_repo() == "existing"

    # Git pull fails, triggers re-clone; SSH clone fails, HTTPS clone succeeds
    with patch("subprocess.run") as mock_sub:
        mock_sub.side_effect = [
            MagicMock(returncode=1, stderr="Merge conflict"),  # git pull
            MagicMock(returncode=1, stderr="SSH rejected"),  # git clone ssh
            MagicMock(returncode=0),  # git clone https
        ]
        res_prep = mgr._prepare_git_repo()
        assert "https://" in res_prep

    # 11. validate_metadata_header empty lines and read exception
    (local_tmpl / "comp-1").mkdir(parents=True, exist_ok=True)
    header_content = (
        "\n\n# status: tested\n# last_tested_version: 1.0\n"
        "# platform_notes: debian\n# breaking_changes: none\n\nservices:\n"
    )
    (local_tmpl / "comp-1" / "docker-compose.template.yml").write_text(
        header_content, encoding="utf-8"
    )
    assert mgr.validate_metadata_header("comp-1") is True

    with patch.object(Path, "read_text", side_effect=OSError("Read error")):
        assert mgr.validate_metadata_header("comp-1") is False

    # 12. upload_all_components validation failure, and upload_component push failure
    local_meta.write_text(
        json.dumps({"components": {"comp-1": {"name": "C1"}}}), encoding="utf-8"
    )
    with patch.object(mgr, "_prepare_git_repo"):
        with patch.object(mgr, "validate_metadata_header", return_value=False):
            with pytest.raises(ValueError, match="Upload aborted"):
                mgr.upload_all_components()

    with (
        patch.object(mgr, "_prepare_git_repo"),
        patch("subprocess.run") as mock_git,
    ):
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout=" M file.txt"),  # git status
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0),  # git commit
            MagicMock(returncode=1, stderr="Push error"),  # git push
        ]
        with pytest.raises(RuntimeError, match="Git push failed"):
            mgr.upload_component("comp-1")

    # 13. _update_cache_for_component metadata exception and template copy exception
    mgr.cache_metadata_path.write_text(json.dumps({"components": {}}), encoding="utf-8")
    local_meta.write_text(
        json.dumps({"components": {"comp-1": {"meta": "val"}}}), encoding="utf-8"
    )
    with patch("json.dump", side_effect=OSError("Write cache error")):
        mgr._update_cache_for_component("comp-1")

    with patch("shutil.copytree", side_effect=OSError("Copy cache error")):
        mgr._update_cache_for_component("comp-1")

    # 14. _update_cache_all success & failure
    mgr._update_cache_all()
    with patch("shutil.copy2", side_effect=OSError("Copy2 error")):
        mgr._update_cache_all()

    # 15. _update_cache_from_git_repo copying git_meta and git_templates & failure
    git_meta = mgr.git_repo_dir / "components_metadata.json"
    git_meta.write_text("{}", encoding="utf-8")
    git_tmpl = mgr.git_repo_dir / "component_templates"
    git_tmpl.mkdir(parents=True, exist_ok=True)
    mgr.cache_templates_path.mkdir(parents=True, exist_ok=True)
    mgr._update_cache_from_git_repo()
    assert mgr.cache_metadata_path.exists()

    with patch("shutil.copy2", side_effect=OSError("Git copy2 error")):
        mgr._update_cache_from_git_repo()


def test_sync_manager_missing_lines_coverage(temp_dirs, tmp_path):
    local_meta, local_tmpl = temp_dirs
    mgr = SyncManager(local_meta, local_tmpl)

    # 1. Line 232: cache_dir exists during _download_and_extract_cache
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("repo-main/components_metadata.json", "{}")
    zip_bytes = zip_buffer.getvalue()

    mgr.cache_dir.mkdir(parents=True, exist_ok=True)
    with patch("requests.get", return_value=MockResponse(zip_bytes, 200)):
        assert mgr.fetch_from_remote() is True

    # 2. Line 228: next(iter(subdirs), None) returns None
    with (
        patch("requests.get", return_value=MockResponse(zip_bytes, 200)),
        patch("src.managers.sync_manager.next", return_value=None),
    ):
        assert mgr.fetch_from_remote() is False

    # 3. Lines 330-331: Exception in _compare_directories
    d1 = tmp_path / "dir1"
    d2 = tmp_path / "dir2"
    d1.mkdir(parents=True, exist_ok=True)
    d2.mkdir(parents=True, exist_ok=True)
    (d1 / "test.txt").write_text("a", encoding="utf-8")
    (d2 / "test.txt").write_text("a", encoding="utf-8")
    with patch.object(Path, "read_text", side_effect=OSError("Read error")):
        assert mgr._compare_directories(d1, d2) is False

    # 4. Lines 455-457: Exception during update_component_timestamp
    local_meta.write_text(
        json.dumps({"components": {"test-comp": {"name": "Test"}}}),
        encoding="utf-8",
    )
    with patch("src.managers.sync_manager.json.dump", side_effect=OSError("File lock")):
        assert mgr.update_component_timestamp("test-comp") is False

    # 5. Lines 541-542: .git parent directory discovery in verify_github_push_access
    git_parent = tmp_path / "git_root"
    (git_parent / ".git").mkdir(parents=True, exist_ok=True)
    fake_meta = git_parent / "sub1" / "sub2" / "metadata.json"
    fake_meta.parent.mkdir(parents=True, exist_ok=True)
    fake_meta.write_text("{}", encoding="utf-8")
    mgr.local_metadata_path = fake_meta

    with (
        patch.object(mgr, "_prepare_git_repo", side_effect=RuntimeError("no git")),
        patch("subprocess.run", return_value=MagicMock(returncode=0)),
    ):
        success, _ = mgr.check_write_access_details()
        assert success is True


def test_sync_all_non_destructive_and_preflight(temp_dirs, tmp_path):
    local_meta, local_templates = temp_dirs
    manager = SyncManager(local_meta, local_templates)

    # 1. Setup local data with a local-only component (e.g. clamav)
    local_meta_content = {
        "components": {
            "clamav": {"name": "ClamAV Local", "group": "Security"},
            "existing-comp": {"name": "Existing Local"},
        },
        "packages": {"modern-workplace": {"components": ["existing-comp", "clamav"]}},
        "_njorddeploy": {
            "group_rules": {"Security": {"name": "Security"}},
            "group_order": ["Security"],
        },
    }
    if local_templates.exists():
        shutil.rmtree(local_templates)
    local_templates.mkdir(parents=True, exist_ok=True)
    local_meta.write_text(json.dumps(local_meta_content), encoding="utf-8")

    clamav_local_dir = local_templates / "clamav"
    clamav_local_dir.mkdir(parents=True, exist_ok=True)
    (clamav_local_dir / "docker-compose.template.yml").write_text(
        "services:\n  clamav:\n    image: clamav:latest\n", encoding="utf-8"
    )

    # 2. Setup remote cache without clamav
    manager.cache_dir.mkdir(parents=True, exist_ok=True)
    remote_meta_content = {
        "components": {
            "existing-comp": {"name": "Existing Remote Updated"},
            "remote-new": {"name": "Remote New"},
        },
        "packages": {"modern-workplace": {"components": ["existing-comp"]}},
        "_njorddeploy": {
            "group_rules": {"General": {"name": "General"}},
            "group_order": ["General"],
        },
    }
    manager.cache_metadata_path.write_text(
        json.dumps(remote_meta_content), encoding="utf-8"
    )
    manager.cache_templates_path.mkdir(parents=True, exist_ok=True)
    rem_exist_dir = manager.cache_templates_path / "existing-comp"
    rem_exist_dir.mkdir(parents=True, exist_ok=True)
    (rem_exist_dir / "docker-compose.template.yml").write_text(
        "services:\n  existing:\n    image: existing:v2\n", encoding="utf-8"
    )

    # 3. Verify get_local_only_components
    local_only = manager.get_local_only_components()
    assert local_only == ["clamav"]

    # 4. Verify check_preflight_sync
    preflight = manager.check_preflight_sync()
    assert preflight["is_synced"] is False
    assert "clamav" in preflight["local_only"]

    # 5. sync_all with preserve_local=False & force=False -> raises ValueError
    with pytest.raises(ValueError) as excinfo:
        manager.sync_all(force=False, preserve_local=False)
    assert "local-only component(s) detected: clamav" in str(excinfo.value)

    # 6. Safe sync_all (default preserve_local=True)
    success = manager.sync_all(force=False, preserve_local=True)
    assert success is True

    # Verify that clamav was preserved in both metadata and templates!
    saved_local = json.loads(local_meta.read_text(encoding="utf-8"))
    assert "clamav" in saved_local["components"]
    assert "remote-new" in saved_local["components"]
    assert saved_local["components"]["existing-comp"]["name"] == (
        "Existing Remote Updated"
    )
    # Package modern-workplace still contains clamav
    assert "clamav" in saved_local["packages"]["modern-workplace"]["components"]
    # Group rule Security preserved
    assert "Security" in saved_local["_njorddeploy"]["group_rules"]

    # Template for clamav is still intact
    assert (clamav_local_dir / "docker-compose.template.yml").exists()
    assert (local_templates / "existing-comp").exists()
