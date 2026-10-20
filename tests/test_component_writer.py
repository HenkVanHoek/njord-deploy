# tests/test_component_writer.py

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from managers.component_writer import ComponentWriter


@pytest.fixture
def writer_fixture(tmp_path):
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(
        json.dumps(
            {
                "components": {
                    "existing-app": {
                        "name": "Existing App",
                        "variables": [],
                        "package_id": "pkg-a",
                        "config_templates": {"sample.conf": "existing-app/sample.conf"},
                        "has_configuration": True,
                    }
                },
                "packages": {
                    "pkg-a": {"name": "Package A"},
                    "pkg-unused": {"name": "Unused Package"},
                },
            }
        ),
        encoding="utf-8",
    )
    templates_path = tmp_path / "templates"
    templates_path.mkdir()

    comp_dir = templates_path / "existing-app"
    comp_dir.mkdir()
    (comp_dir / "template-config").mkdir()
    (comp_dir / "docker-compose.template.yml").write_text(
        '# status: "testing"\n'
        '# last_tested_version: "1.0"\n'
        '# platform_notes: "None"\n'
        '# breaking_changes: "None"\n'
        "services:\n  app:\n    image: app:1.0\n",
        encoding="utf-8",
    )
    (comp_dir / "template-config" / "variables.json").write_text(
        json.dumps({"variables": []}), encoding="utf-8"
    )
    (comp_dir / "template-config" / "sample.conf").write_text(
        "port=8080\n", encoding="utf-8"
    )

    writer = ComponentWriter(metadata_path=meta_path, templates_path=templates_path)
    return writer, meta_path, templates_path


def test_writer_creates_component_skeleton_success(tmp_path):
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(json.dumps({"components": {}}), encoding="utf-8")
    temp_path = tmp_path / "templates"
    temp_path.mkdir()

    writer = ComponentWriter(metadata_path=meta_path, templates_path=temp_path)
    component_id = "new-app"
    meta_data = {"name": "New App", "version": "1.0.0"}
    success = writer.create_component_skeleton(component_id, meta_data)

    assert success is True
    assert (temp_path / component_id).exists()
    assert (temp_path / component_id / "template-config" / "variables.json").exists()
    assert (temp_path / component_id / "docker-compose.template.yml").exists()

    with open(meta_path, "r", encoding="utf-8") as f:
        updated_meta = json.load(f)

    assert component_id in updated_meta["components"]
    assert updated_meta["components"][component_id]["name"] == "New App"


def test_create_component_skeleton_already_exists(writer_fixture):
    writer, _, _ = writer_fixture
    # "existing-app" already exists on disk
    success = writer.create_component_skeleton("existing-app", {"name": "Dup"})
    assert success is False


def test_create_component_skeleton_missing_or_corrupt_metadata(tmp_path):
    # Metadata file does not exist initially
    meta_path = tmp_path / "nonexistent" / "metadata.json"
    temp_path = tmp_path / "templates"
    writer = ComponentWriter(metadata_path=meta_path, templates_path=temp_path)

    success = writer.create_component_skeleton("fresh-app", {"name": "Fresh"})
    assert success is True
    assert meta_path.exists()
    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "fresh-app" in loaded["components"]


def test_save_json_io_error(tmp_path):
    writer = ComponentWriter(
        metadata_path=tmp_path / "m.json", templates_path=tmp_path / "t"
    )
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        result = writer._save_json(tmp_path / "protected.json", {"key": "val"})
        assert result is False


def test_save_metadata(writer_fixture):
    writer, meta_path, _ = writer_fixture
    res = writer.save_metadata({"components": {}, "packages": {}})
    assert res is True
    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    assert loaded == {"components": {}, "packages": {}}


def test_save_component_variables_raw_and_update(writer_fixture):
    writer, _, templates_path = writer_fixture
    res = writer.save_component_variables_raw(
        "existing-app", {"variables": [{"name": "PORT", "default": 80}]}
    )
    assert res is True
    var_file = templates_path / "existing-app" / "template-config" / "variables.json"
    loaded = json.loads(var_file.read_text(encoding="utf-8"))
    first, *_ = loaded["variables"]
    assert first["name"] == "PORT"

    # update_component_variables wraps list in {"variables": data}
    res2 = writer.update_component_variables(
        "existing-app", [{"name": "HOST", "default": "0.0.0.0"}]
    )
    assert res2 is True
    loaded2 = json.loads(var_file.read_text(encoding="utf-8"))
    first2, *_ = loaded2["variables"]
    assert first2["name"] == "HOST"


def test_update_template_content_with_and_without_headers(writer_fixture):
    writer, _, templates_path = writer_fixture
    # Content without headers -> writer should automatically prepend them
    raw_content = "services:\n  web:\n    image: nginx\n"
    res = writer.update_template_content("existing-app", raw_content)
    assert res is True

    template_file = templates_path / "existing-app" / "docker-compose.template.yml"
    saved = template_file.read_text(encoding="utf-8")
    assert '# status: "untested"' in saved
    assert "image: nginx" in saved

    # Content with headers already present
    header_content = (
        '# status: "production"\n'
        '# last_tested_version: "2.0"\n'
        '# platform_notes: "ARM64"\n'
        '# breaking_changes: "None"\n'
        "services:\n  web:\n    image: nginx:2.0\n"
    )
    res2 = writer.update_template_content("existing-app", header_content)
    assert res2 is True
    saved2 = template_file.read_text(encoding="utf-8")
    assert '# status: "production"' in saved2
    # Ensure header wasn't duplicated
    assert saved2.count('# status: "production"') == 1


def test_update_template_content_io_error(writer_fixture):
    writer, _, _ = writer_fixture
    with patch.object(Path, "write_text", side_effect=IOError("Disk full")):
        res = writer.update_template_content("existing-app", "services:\n")
        assert res is False


def test_update_template_status_cases(writer_fixture):
    writer, _, templates_path = writer_fixture
    # When component doesn't exist
    assert writer.update_template_status("nonexistent-app", "verified") is False

    # When component template exists with existing status
    res = writer.update_template_status("existing-app", "production")
    assert res is True
    tpl = (templates_path / "existing-app" / "docker-compose.template.yml").read_text(
        encoding="utf-8"
    )
    assert '# status: "production"' in tpl

    # When component template has no status line -> prepends
    (templates_path / "existing-app" / "docker-compose.template.yml").write_text(
        "services:\n  app:\n    image: app\n", encoding="utf-8"
    )
    res2 = writer.update_template_status("existing-app", "active")
    assert res2 is True
    tpl2 = (templates_path / "existing-app" / "docker-compose.template.yml").read_text(
        encoding="utf-8"
    )
    assert tpl2.startswith('# status: "active"\n')

    # Exception during write
    with patch.object(Path, "write_text", side_effect=OSError("Read-only")):
        assert writer.update_template_status("existing-app", "broken") is False


def test_delete_component_files(writer_fixture):
    writer, _, templates_path = writer_fixture
    # Deleting nonexistent component returns False
    assert writer.delete_component_files("missing-app") is False

    # Deleting existing component
    assert (templates_path / "existing-app").exists()
    deleted = writer.delete_component_files("existing-app")
    assert deleted is True
    assert not (templates_path / "existing-app").exists()

    # Deleting when rmtree fails raises OSError
    with patch("shutil.rmtree", side_effect=OSError("Access denied")):
        (templates_path / "err-app").mkdir()
        with pytest.raises(OSError):
            writer.delete_component_files("err-app")


def test_update_package(writer_fixture):
    writer, meta_path, _ = writer_fixture
    # Package does not exist
    assert writer.update_package("pkg-999", {"name": "Missing"}) is False

    # Package exists
    success = writer.update_package("pkg-a", {"name": "Package Alpha"})
    assert success is True
    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    assert loaded["packages"]["pkg-a"]["name"] == "Package Alpha"

    # Missing metadata file
    writer_ghost = ComponentWriter(
        metadata_path=Path("/tmp/nonexistent_meta_file_test.json"),
        templates_path=Path("/tmp"),
    )
    assert writer_ghost.update_package("pkg-a", {}) is False


def test_delete_package(writer_fixture):
    writer, meta_path, _ = writer_fixture
    # Cannot delete package in use by existing-app
    assert writer.delete_package("pkg-a") is False

    # Cannot delete nonexistent package
    assert writer.delete_package("pkg-unknown") is False

    # Can delete unused package
    assert writer.delete_package("pkg-unused") is True
    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "pkg-unused" not in loaded["packages"]

    # When metadata file does not exist
    writer_ghost = ComponentWriter(
        metadata_path=Path("/tmp/nonexistent_meta_file_test.json"),
        templates_path=Path("/tmp"),
    )
    assert writer_ghost.delete_package("pkg-a") is False


def test_save_and_delete_component_config(writer_fixture):
    writer, meta_path, templates_path = writer_fixture
    # Save a config file
    success = writer.save_component_config(
        "existing-app", "custom.conf", "server=localhost\n"
    )
    assert success is True
    conf_file = templates_path / "existing-app" / "template-config" / "custom.conf"
    assert conf_file.exists()
    assert conf_file.read_text(encoding="utf-8") == "server=localhost\n"

    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    comp_meta = loaded["components"]["existing-app"]
    assert "custom.conf" in comp_meta["config_templates"]
    assert comp_meta["has_configuration"] is True

    # Save config write error
    with patch.object(Path, "write_text", side_effect=IOError("Permission denied")):
        assert writer.save_component_config("existing-app", "err.conf", "data") is False

    # Delete config file
    del_res = writer.delete_component_config("existing-app", "custom.conf")
    assert del_res is True
    assert not conf_file.exists()
    loaded_after = json.loads(meta_path.read_text(encoding="utf-8"))
    existing_meta = loaded_after["components"]["existing-app"]
    assert "custom.conf" not in existing_meta["config_templates"]

    # Delete original sample.conf so config_templates becomes empty
    del_res2 = writer.delete_component_config("existing-app", "sample.conf")
    assert del_res2 is True
    loaded_after2 = json.loads(meta_path.read_text(encoding="utf-8"))
    assert loaded_after2["components"]["existing-app"]["has_configuration"] is False

    with patch("json.load", side_effect=json.JSONDecodeError("err", "doc", 0)):
        assert writer.update_package("pkg-a", {}) is False
        assert writer.delete_package("pkg-unused") is False

    # Re-add a config template to test deletion failure handling
    writer.save_component_config("existing-app", "temp.conf", "x=1")
    with patch.object(
        writer, "_save_json", side_effect=Exception("Metadata DB corrupt")
    ):
        assert writer.save_component_config("existing-app", "err2.conf", "x") is False
        assert writer.delete_component_config("existing-app", "temp.conf") is False


def test_writer_additional_edge_cases(writer_fixture, tmp_path):
    writer, meta_path, templates_path = writer_fixture

    # _save_json IOError
    with patch("builtins.open", side_effect=IOError("Disk full")):
        assert writer._save_json(meta_path, {}) is False

    # update_template_content IOError
    with patch.object(Path, "write_text", side_effect=IOError("Write failed")):
        assert writer.update_template_content("existing-app", "services:") is False

    # update_template_status nonexistent & exception
    assert writer.update_template_status("nonexistent-app", "tested") is False
    with patch.object(Path, "write_text", side_effect=RuntimeError("fail")):
        assert writer.update_template_status("existing-app", "tested") is False

    # delete_component_files nonexistent & OSError
    assert writer.delete_component_files("nonexistent-app") is False
    with patch("shutil.rmtree", side_effect=OSError("Access denied")):
        with pytest.raises(OSError):
            writer.delete_component_files("existing-app")

    # Missing metadata file for package and config deletion
    missing_meta_writer = ComponentWriter(
        tmp_path / "missing_meta.json", templates_path
    )
    assert missing_meta_writer.update_package("pkg-a", {}) is False
    assert missing_meta_writer.delete_package("pkg-a") is False
    assert (
        missing_meta_writer.delete_component_config("existing-app", "sample.conf")
        is True
    )

    # Empty lines in template headers & exception fallback (lines 72, 81-82)
    content_with_empty_lines = "\n# status: untested\n\n# last_tested_version: 1.0\n"
    assert (
        writer.update_template_content("existing-app", content_with_empty_lines) is True
    )

    class BadStr(str):
        def splitlines(self, *args, **kwargs):
            raise RuntimeError("split error")

    assert writer.update_template_content("existing-app", BadStr("services:\n")) is True

    # Corrupt metadata file during create_component_skeleton (lines 159-160)
    corrupt_meta = tmp_path / "corrupt_meta.json"
    corrupt_meta.write_text("{ corrupt", encoding="utf-8")
    corrupt_writer = ComponentWriter(corrupt_meta, templates_path)
    assert corrupt_writer.create_component_skeleton("new_comp", {"name": "New"}) is True

    # save_component_config when metadata_file does not exist (line 241)
    assert (
        missing_meta_writer.save_component_config("new_comp", "conf.yml", "key: val")
        is True
    )

    # delete_component_config with unlink IOError & missing from meta
    # (lines 262-263, 279)
    locked_file = templates_path / "existing-app" / "template-config" / "locked.conf"
    locked_file.write_text("lock", encoding="utf-8")
    with patch.object(Path, "unlink", side_effect=IOError("Lock error")):
        assert writer.delete_component_config("existing-app", "locked.conf") is True
    assert writer.delete_component_config("existing-app", "not_in_meta.conf") is True
