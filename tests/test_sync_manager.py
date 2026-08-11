# tests/test_sync_manager.py

import io
import json
import zipfile

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
