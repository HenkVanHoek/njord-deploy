# tests/utils/test_dashy_updater.py

"""
Unit tests for dashy_updater.
"""

import json
from pathlib import Path

import pytest
import yaml

from utils import dashy_updater


def test_get_default_dashy_config():
    config = dashy_updater.get_default_dashy_config()
    assert "pageInfo" in config
    assert "appConfig" in config
    assert "sections" in config
    assert config["sections"][0]["name"] == "My Services"


def test_ensure_config_exists(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "dashy" / "conf.yml"
    monkeypatch.setattr(dashy_updater, "DASHY_CONFIG_PATH", str(cfg_file))

    dashy_updater.ensure_config_exists()

    assert cfg_file.exists()
    content = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert content["pageInfo"]["title"] == "NjordDeploy Dashboard"


def test_load_yaml_and_json(tmp_path: Path):
    yaml_file = tmp_path / "test.yml"
    yaml_file.write_text("hello: world\n", encoding="utf-8")
    assert dashy_updater.load_yaml(str(yaml_file)) == {"hello": "world"}

    json_file = tmp_path / "test.json"
    json_file.write_text('{"num": 42}', encoding="utf-8")
    assert dashy_updater.load_json(str(json_file)) == {"num": 42}

    # Error handling exits
    bad_yaml = tmp_path / "bad.yml"
    bad_yaml.write_text(":\n- invalid", encoding="utf-8")
    with pytest.raises(SystemExit):
        dashy_updater.load_yaml(str(bad_yaml))

    with pytest.raises(SystemExit):
        dashy_updater.load_json(str(tmp_path / "missing.json"))

    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{bad json", encoding="utf-8")
    with pytest.raises(SystemExit):
        dashy_updater.load_json(str(bad_json))


def test_get_selected_components(tmp_path: Path):
    txt_file = tmp_path / "selected.txt"
    txt_file.write_text("adguard-home caddy portainer\n", encoding="utf-8")
    comps = dashy_updater.get_selected_components(str(txt_file))
    assert comps == ["adguard-home", "caddy", "portainer"]

    with pytest.raises(SystemExit):
        dashy_updater.get_selected_components(str(tmp_path / "nonexistent.txt"))


def test_main_workflow(tmp_path: Path, monkeypatch):
    dashy_file = tmp_path / "conf.yml"
    meta_file = tmp_path / "metadata.json"
    selected_file = tmp_path / "selected.txt"

    monkeypatch.setattr(dashy_updater, "DASHY_CONFIG_PATH", str(dashy_file))
    monkeypatch.setattr(dashy_updater, "METADATA_PATH", str(meta_file))
    monkeypatch.setattr(dashy_updater, "SELECTED_COMPONENTS_PATH", str(selected_file))

    meta = {
        "caddy": {
            "name": "Caddy Web Server",
            "has_ui": True,
            "ui_port": 80,
            "protocol": "http",
        },
        "backend-service": {
            "name": "Backend Service",
            "has_ui": False,
        },
    }
    meta_file.write_text(json.dumps(meta), encoding="utf-8")
    selected_file.write_text("caddy backend-service\n", encoding="utf-8")

    dashy_updater.main("192.168.1.100")

    result = yaml.safe_load(dashy_file.read_text(encoding="utf-8"))
    items = result["sections"][0]["items"]
    assert len(items) == 1
    caddy_item, *_ = items
    assert caddy_item["title"] == "Caddy Web Server"
    assert caddy_item["url"] == "http://192.168.1.100:80"

    # Second run does not duplicate
    dashy_updater.main("192.168.1.100")
    result2 = yaml.safe_load(dashy_file.read_text(encoding="utf-8"))
    assert len(result2["sections"][0]["items"]) == 1


def test_main_malformed_config_recovery(tmp_path: Path, monkeypatch):
    dashy_file = tmp_path / "conf.yml"
    meta_file = tmp_path / "metadata.json"
    selected_file = tmp_path / "selected.txt"

    monkeypatch.setattr(dashy_updater, "DASHY_CONFIG_PATH", str(dashy_file))
    monkeypatch.setattr(dashy_updater, "METADATA_PATH", str(meta_file))
    monkeypatch.setattr(dashy_updater, "SELECTED_COMPONENTS_PATH", str(selected_file))

    # Test malformed config: not a dict or missing sections
    dashy_file.write_text("invalid_string_root\n", encoding="utf-8")
    meta_file.write_text("{}", encoding="utf-8")
    selected_file.write_text("", encoding="utf-8")

    dashy_updater.main("192.168.1.100")

    # Test empty sections list
    dashy_file.write_text("sections: []\n", encoding="utf-8")
    dashy_updater.main("192.168.1.100")


def test_main_ioerror_on_save(tmp_path: Path, monkeypatch):
    dashy_file = tmp_path / "conf.yml"
    meta_file = tmp_path / "metadata.json"
    selected_file = tmp_path / "selected.txt"

    monkeypatch.setattr(dashy_updater, "DASHY_CONFIG_PATH", str(dashy_file))
    monkeypatch.setattr(dashy_updater, "METADATA_PATH", str(meta_file))
    monkeypatch.setattr(dashy_updater, "SELECTED_COMPONENTS_PATH", str(selected_file))

    dashy_file.write_text(
        "sections:\n  - name: Default\n    items: []\n", encoding="utf-8"
    )
    meta = {"app": {"name": "App", "has_ui": True, "ui_port": 8080}}
    meta_file.write_text(json.dumps(meta), encoding="utf-8")
    selected_file.write_text("app\n", encoding="utf-8")

    real_open = open

    def _mock_open(file, mode="r", *args, **kwargs):
        if str(file) == str(dashy_file) and "w" in mode:
            raise OSError("disk full")
        return real_open(file, mode, *args, **kwargs)

    with pytest.raises(SystemExit):
        monkeypatch.setattr("builtins.open", _mock_open)
        dashy_updater.main("192.168.1.100")
