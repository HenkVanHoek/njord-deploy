import os
import shutil
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.resource_utils import (
    get_app_data_dir,
    get_components_paths,
    get_global_template_context,
    get_last_seed_status,
    get_project_root,
    get_project_version,
    get_ssh_key_path,
    is_server_mode,
    resource_path,
    seed_user_components_if_needed,
)


def test_resource_path_in_dev_mode():
    """Tests if resource_path returns the correct path in dev mode."""
    current_test_dir = Path(__file__).resolve().parent
    project_root = current_test_dir.parent
    relative_path_to_test = Path("my_folder") / "my_file.txt"
    expected_path = project_root / relative_path_to_test
    actual_path = resource_path(str(relative_path_to_test))
    assert str(actual_path) == str(expected_path)


def test_resource_path_in_pyinstaller_mode(monkeypatch):
    """Tests resource_path when simulating a PyInstaller bundle."""
    temp_bundle_dir = "/tmp/_MEI12345"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", temp_bundle_dir, raising=False)
    relative = "my_folder/my_file.txt"
    expected_path = str(Path(temp_bundle_dir) / relative)
    actual_path = resource_path(relative)
    assert str(actual_path) == expected_path


def test_get_components_paths_env_override(monkeypatch):
    """Test get_components_paths with environment variable override."""
    fake_dir = "/fake/components/dir"
    monkeypatch.setenv("PI_SELFHOSTING_COMPONENTS_DIR", fake_dir)
    meta_path, temp_path = get_components_paths()
    assert meta_path == Path(fake_dir).resolve() / "components_metadata.json"
    assert temp_path == Path(fake_dir).resolve() / "component_templates"


def test_get_components_paths_user_data_dir(monkeypatch, tmp_path):
    """Test get_components_paths with user data directory."""
    monkeypatch.delenv("PI_SELFHOSTING_COMPONENTS_DIR", raising=False)
    monkeypatch.delenv("NJORD_COMPONENTS_DIR", raising=False)
    monkeypatch.setattr("appdirs.user_data_dir", lambda a, b: str(tmp_path))

    components_dir = tmp_path / "components"
    components_dir.mkdir(parents=True, exist_ok=True)
    (components_dir / "components_metadata.json").touch()
    user_templates_dir = components_dir / "component_templates"
    user_templates_dir.mkdir(parents=True, exist_ok=True)
    (user_templates_dir / "dummy_comp").mkdir(parents=True, exist_ok=True)

    meta_path, temp_path = get_components_paths()
    assert meta_path == components_dir / "components_metadata.json"
    assert temp_path == components_dir / "component_templates"


def test_get_components_paths_fallback(monkeypatch, tmp_path):
    """Test get_components_paths falls back to built-in resources."""
    monkeypatch.delenv("PI_SELFHOSTING_COMPONENTS_DIR", raising=False)
    monkeypatch.delenv("NJORD_COMPONENTS_DIR", raising=False)
    monkeypatch.setattr("appdirs.user_data_dir", lambda a, b: str(tmp_path))

    meta_path, temp_path = get_components_paths()
    expected_meta = resource_path("config/components_metadata.json")
    expected_temp = resource_path("component_templates")
    assert meta_path == expected_meta
    assert temp_path == expected_temp


def test_app_data_and_ssh_key_paths(monkeypatch, tmp_path):
    """Test get_app_data_dir and get_ssh_key_path env overrides and defaults."""
    custom_dir = tmp_path / "custom_data"
    monkeypatch.setenv("NJORD_DATA_DIR", str(custom_dir))
    assert get_app_data_dir() == custom_dir.resolve()

    monkeypatch.delenv("NJORD_DATA_DIR", raising=False)
    monkeypatch.setattr("appdirs.user_data_dir", lambda a, b: str(tmp_path))
    assert get_app_data_dir() == tmp_path

    # SSH key path
    custom_key = tmp_path / "custom_id_rsa"
    monkeypatch.setenv("NJORD_SSH_KEY_PATH", str(custom_key))
    assert get_ssh_key_path() == custom_key.resolve()

    monkeypatch.delenv("NJORD_SSH_KEY_PATH", raising=False)
    expected_default_key = tmp_path / "id_ed25519_njorddeploy"
    assert get_ssh_key_path() == expected_default_key


def test_is_server_mode(monkeypatch):
    """Test server mode detection for various string values."""
    for val in ("true", "1", "yes", "service", "daemon"):
        monkeypatch.setenv("NJORD_SERVER_MODE", val)
        assert is_server_mode() is True

    for val in ("false", "0", "no", ""):
        monkeypatch.setenv("NJORD_SERVER_MODE", val)
        assert is_server_mode() is False


def test_project_root_and_version(tmp_path):
    """Test get_project_root, get_project_version, and fallback."""
    root = get_project_root()
    assert root.exists()
    assert (root / "pyproject.toml").exists()

    version = get_project_version()
    assert version != "latest"
    assert "." in version

    with patch("utils.resource_utils.get_project_root", return_value=tmp_path):
        fallback_ver = get_project_version()
        assert fallback_ver == "latest"


def test_global_template_context_and_seed_status():
    """Test global template context and last seed status getters."""
    ctx = get_global_template_context()
    assert "DOTENV" in ctx
    assert "CONFIG_BASE_PATH" in ctx

    status = get_last_seed_status()
    assert isinstance(status, dict)
    assert "status" in status


def test_seed_user_components_scenarios(monkeypatch, tmp_path):
    """Test seed_user_components_if_needed across multiple conditions."""
    # 1. Environment variable override
    monkeypatch.setenv("PI_SELFHOSTING_COMPONENTS_DIR", str(tmp_path))
    status_env = seed_user_components_if_needed()
    assert status_env["status"] == "already_seeded"

    monkeypatch.delenv("PI_SELFHOSTING_COMPONENTS_DIR", raising=False)
    monkeypatch.setattr("appdirs.user_data_dir", lambda a, b: str(tmp_path))

    # 2. Pytest mode seeding
    status_pytest = seed_user_components_if_needed()
    assert status_pytest["status"] == "already_seeded"

    # 3. Already seeded when files exist
    status_existing = seed_user_components_if_needed()
    assert status_existing["status"] == "already_seeded"

    # 4. Remote sync download scenario (simulating frozen binary runtime)
    import shutil

    user_components_dir = tmp_path / "components"
    if user_components_dir.exists():
        shutil.rmtree(user_components_dir)

    monkeypatch.setattr(sys, "frozen", True, raising=False)

    mock_sync = MagicMock()
    mock_sync.is_remote_sync_enabled.return_value = True
    mock_sync.fetch_from_remote.return_value = True
    mock_sync.sync_all.return_value = True

    # Temporarily hide pytest from sys.modules
    modules_copy = sys.modules.copy()
    modules_copy.pop("pytest", None)

    with (
        patch.dict(sys.modules, modules_copy, clear=True),
        patch("managers.sync_manager.SyncManager", return_value=mock_sync),
    ):
        status_download = seed_user_components_if_needed()
        assert status_download["status"] == "downloaded"

    # 5. Remote sync fails fallback scenario
    if user_components_dir.exists():
        shutil.rmtree(user_components_dir)

    mock_sync_fail = MagicMock()
    mock_sync_fail.is_remote_sync_enabled.return_value = False

    with (
        patch.dict(sys.modules, modules_copy, clear=True),
        patch("managers.sync_manager.SyncManager", return_value=mock_sync_fail),
    ):
        status_fallback = seed_user_components_if_needed()
        assert status_fallback["status"] == "fallback"


def test_seed_user_components_dev_sync(monkeypatch, tmp_path):
    """Test seed_user_components dev mode auto-sync copying files."""
    fake_app_dir = tmp_path / "app_data"
    monkeypatch.setattr("appdirs.user_data_dir", lambda a, b: str(fake_app_dir))
    monkeypatch.delenv("PI_SELFHOSTING_COMPONENTS_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    fake_repo = tmp_path / "repo"
    meta_dir = fake_repo / "config"
    meta_dir.mkdir(parents=True)
    (meta_dir / "components_metadata.json").write_text("{}", encoding="utf-8")

    templates_dir = fake_repo / "component_templates"
    templates_dir.mkdir(parents=True)
    comp_a = templates_dir / "comp_a"
    comp_a.mkdir()
    (comp_a / "docker-compose.template.yml").write_text("services:\n", encoding="utf-8")
    (templates_dir / "root_file.txt").write_text("hello", encoding="utf-8")

    def mock_resource_path(relative=""):
        return fake_repo / relative

    modules_copy = sys.modules.copy()
    modules_copy.pop("pytest", None)

    with (
        patch.dict(sys.modules, modules_copy, clear=True),
        patch("utils.resource_utils.resource_path", side_effect=mock_resource_path),
    ):
        status = seed_user_components_if_needed()
        assert status["status"] in ("already_seeded", "downloaded", "fallback")


def test_resource_utils_exceptions_and_edge_cases(monkeypatch, tmp_path):
    """Test exceptions in iterdir, sync failure, copy fallback failure,
    and dev mtime update."""
    fake_app_dir = tmp_path / "app_data2"
    monkeypatch.setattr("appdirs.user_data_dir", lambda a, b: str(fake_app_dir))
    monkeypatch.delenv("PI_SELFHOSTING_COMPONENTS_DIR", raising=False)
    monkeypatch.delenv("NJORD_COMPONENTS_DIR", raising=False)

    # 1. Exception during iterdir in get_components_paths
    components_dir = fake_app_dir / "components"
    components_dir.mkdir(parents=True, exist_ok=True)
    (components_dir / "components_metadata.json").touch()
    user_templates_dir = components_dir / "component_templates"
    user_templates_dir.mkdir(parents=True, exist_ok=True)

    with patch.object(Path, "iterdir", side_effect=PermissionError("no access")):
        meta, tmpl = get_components_paths()
        # Falls back to built-in resources because has_templates becomes False
        assert meta == resource_path("config/components_metadata.json")

    # 2. Auto-fetch throws exception in seed_user_components_if_needed
    if fake_app_dir.exists():
        shutil.rmtree(fake_app_dir)
    modules_copy = sys.modules.copy()
    modules_copy.pop("pytest", None)

    with patch.dict(sys.modules, modules_copy, clear=True):
        with patch(
            "managers.sync_manager.SyncManager", side_effect=RuntimeError("sync crash")
        ):
            st = seed_user_components_if_needed()
            assert st["status"] == "fallback"

    # 3. Fallback copy throws exception
    if fake_app_dir.exists():
        shutil.rmtree(fake_app_dir)
    with patch.dict(sys.modules, modules_copy, clear=True):
        with patch("shutil.copy2", side_effect=IOError("disk fail")):
            with patch("shutil.copytree", side_effect=IOError("disk fail")):
                st2 = seed_user_components_if_needed()
                assert st2["status"] == "fallback"

    # 4. Exception in iterdir during seed_user_components_if_needed (lines 86-87)
    (fake_app_dir / "components" / "component_templates").mkdir(
        parents=True, exist_ok=True
    )
    real_iterdir = Path.iterdir

    def _mock_iterdir_fail(self):
        if self.name == "component_templates":
            raise PermissionError("Denied")
        return real_iterdir(self)

    with patch.dict(sys.modules, modules_copy, clear=True):
        with patch.object(Path, "iterdir", _mock_iterdir_fail):
            seed_user_components_if_needed()

    # 5. Dev auto-sync with newer source template directory (lines 108-110)
    fake_source = tmp_path / "mock_repo"
    fake_source_tpl = fake_source / "component_templates" / "service_a"
    fake_source_tpl.mkdir(parents=True, exist_ok=True)
    (fake_source / "config").mkdir(parents=True, exist_ok=True)
    meta_file = fake_source / "config" / "components_metadata.json"
    meta_file.write_text("{}", encoding="utf-8")

    user_dest_tpl = fake_app_dir / "components" / "component_templates" / "service_a"
    user_dest_tpl.mkdir(parents=True, exist_ok=True)

    # Set destination mtime to the past
    past_time = time.time() - 1000
    os.utime(user_dest_tpl, (past_time, past_time))

    def _mock_res_path(rel_p):
        return fake_source / rel_p

    with patch.dict(sys.modules, modules_copy, clear=True):
        with patch("utils.resource_utils.resource_path", side_effect=_mock_res_path):
            st3 = seed_user_components_if_needed()
            assert st3["status"] in ("already_seeded", "downloaded", "fallback")
