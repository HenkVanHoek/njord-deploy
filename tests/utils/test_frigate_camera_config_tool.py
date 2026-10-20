# tests/utils/test_frigate_camera_config_tool.py

"""
Unit tests for frigate_camera_config_tool.
"""

import asyncio
import concurrent.futures
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from utils import frigate_camera_config_tool


def _run_async(coro):
    """Executes a coroutine inside an isolated thread to avoid event loop conflicts."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


def test_check_ip_port_open():
    mock_writer = AsyncMock()
    mock_writer.close = MagicMock()
    mock_writer.wait_closed = AsyncMock()

    with patch("asyncio.open_connection", return_value=(AsyncMock(), mock_writer)):
        result = _run_async(
            frigate_camera_config_tool.check_ip_port("192.168.1.50", 80)
        )
        assert result == "192.168.1.50"


def test_check_ip_port_closed():
    with patch("asyncio.open_connection", side_effect=OSError("Connection refused")):
        result = _run_async(
            frigate_camera_config_tool.check_ip_port("192.168.1.50", 80)
        )
        assert result is None


def test_discover_onvif_cameras_loopback():
    with patch(
        "utils.frigate_camera_config_tool.NodeScanner.get_primary_ip",
        return_value="127.0.0.1",
    ):
        cameras = _run_async(frigate_camera_config_tool.discover_onvif_cameras())
        assert cameras == []


def test_discover_onvif_cameras_with_hosts():
    with (
        patch(
            "utils.frigate_camera_config_tool.NodeScanner.get_primary_ip",
            return_value="192.168.1.10",
        ),
        patch(
            "utils.frigate_camera_config_tool.check_ip_port",
            side_effect=lambda ip, port: ip if ip == "192.168.1.55" else None,
        ),
    ):
        mock_cam = MagicMock()
        mock_cam.create_media_service = AsyncMock()
        dev_info = MagicMock()
        dev_info.Model = "Driveway Cam"
        mock_cam.devicemgmt.GetDeviceInformation = AsyncMock(return_value=dev_info)

        profile = MagicMock()
        profile.token = "token1"
        mock_cam.media.GetProfiles = AsyncMock(return_value=[profile])

        uri_resp = MagicMock()
        uri_resp.Uri = "rtsp://192.168.1.55:554/live"
        mock_cam.media.GetStreamUri = AsyncMock(return_value=uri_resp)

        with patch(
            "utils.frigate_camera_config_tool.ONVIFCamera",
            return_value=mock_cam,
        ):
            cameras = _run_async(frigate_camera_config_tool.discover_onvif_cameras())
            assert len(cameras) >= 1
            cam, *_ = cameras
            assert cam["name"] == "Driveway Cam"
            assert cam["ip_address"] == "192.168.1.55"
            assert "rtsp://192.168.1.55:554/live" in cam["rtsp_urls"]


def test_main_generates_placeholder_when_no_cameras(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "config.yml"
    monkeypatch.setattr(
        frigate_camera_config_tool, "FRIGATE_CONFIG_PATH", str(cfg_file)
    )

    with patch(
        "utils.frigate_camera_config_tool.discover_onvif_cameras",
        AsyncMock(return_value=[]),
    ):
        _run_async(frigate_camera_config_tool.main())

    assert cfg_file.exists()
    data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert "placeholder_camera_127_0_0_1" in data["cameras"]


def test_main_merges_discovered_camera(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "config.yml"
    monkeypatch.setattr(
        frigate_camera_config_tool, "FRIGATE_CONFIG_PATH", str(cfg_file)
    )

    mock_discovered = [
        {
            "name": "Garden Cam",
            "ip_address": "192.168.1.60",
            "rtsp_urls": ["rtsp://192.168.1.60/main"],
        }
    ]

    with patch(
        "utils.frigate_camera_config_tool.discover_onvif_cameras",
        AsyncMock(return_value=mock_discovered),
    ):
        _run_async(frigate_camera_config_tool.main())

    assert cfg_file.exists()
    data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert "garden_cam_192_168_1_60" in data["cameras"]


def test_frigate_no_potential_ips_and_existing_config(tmp_path: Path, monkeypatch):
    """Test empty potential IPs, corrupt config yaml, existing camera skip, and write
    failure."""
    cfg_file = tmp_path / "config.yml"
    monkeypatch.setattr(
        frigate_camera_config_tool, "FRIGATE_CONFIG_PATH", str(cfg_file)
    )

    # 1. No potential IPs found
    with (
        patch(
            "utils.frigate_camera_config_tool.NodeScanner.get_primary_ip",
            return_value="192.168.1.10",
        ),
        patch(
            "utils.frigate_camera_config_tool.check_ip_port",
            return_value=None,
        ),
    ):
        res = _run_async(frigate_camera_config_tool.discover_onvif_cameras())
        assert res == []

    # 2. Corrupt YAML config handled
    cfg_file.write_text("invalid:\n  - : bad", encoding="utf-8")
    with patch(
        "utils.frigate_camera_config_tool.discover_onvif_cameras",
        AsyncMock(return_value=[]),
    ):
        _run_async(frigate_camera_config_tool.main())
    loaded_data = yaml.safe_load(cfg_file.read_text())
    assert "placeholder_camera_127_0_0_1" in loaded_data["cameras"]

    # 3. Already up to date (no changes made)
    with patch(
        "utils.frigate_camera_config_tool.discover_onvif_cameras",
        AsyncMock(return_value=[]),
    ):
        _run_async(frigate_camera_config_tool.main())

    # 4. Write error handled with sys.exit(0)
    fake_cam = [{"name": "c", "ip_address": "1.1.1.1", "rtsp_urls": ["rtsp://1"]}]
    real_open = open

    def _mock_open(file, mode="r", *args, **kwargs):
        if str(file) == str(cfg_file) and "w" in mode:
            raise OSError("write fail")
        return real_open(file, mode, *args, **kwargs)

    with patch("builtins.open", side_effect=_mock_open):
        with patch(
            "utils.frigate_camera_config_tool.discover_onvif_cameras",
            AsyncMock(return_value=fake_cam),
        ):
            with pytest.raises(SystemExit) as exc_info:
                _run_async(frigate_camera_config_tool.main())
            assert exc_info.value.code == 0


def test_frigate_camera_already_exists(tmp_path: Path, monkeypatch):
    """Test skipping when discovered camera already exists in configuration."""
    cfg_file = tmp_path / "config.yml"
    monkeypatch.setattr(
        frigate_camera_config_tool, "FRIGATE_CONFIG_PATH", str(cfg_file)
    )

    initial_config = {
        "cameras": {
            "driveway_cam_192_168_1_55": {
                "ffmpeg": {
                    "inputs": [
                        {
                            "path": "rtsp://192.168.1.55/stream",
                            "roles": ["detect"],
                        }
                    ]
                },
                "detect": {"width": 1280, "height": 720, "fps": 5},
            }
        }
    }
    cfg_file.write_text(yaml.dump(initial_config), encoding="utf-8")

    discovered_cam = [
        {
            "name": "Driveway Cam",
            "ip_address": "192.168.1.55",
            "rtsp_urls": ["rtsp://192.168.1.55/stream"],
        }
    ]

    with patch(
        "utils.frigate_camera_config_tool.discover_onvif_cameras",
        AsyncMock(return_value=discovered_cam),
    ):
        _run_async(frigate_camera_config_tool.main())

    loaded = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert "driveway_cam_192_168_1_55" in loaded["cameras"]


def test_frigate_container_path_resolution():
    """Verify FRIGATE_CONFIG_PATH resolution inside container environment."""
    import importlib
    import os

    real_exists = os.path.exists

    def _mock_exists(p):
        if str(p) == "/app/config":
            return True
        return real_exists(p)

    with patch("os.path.exists", side_effect=_mock_exists):
        reloaded = importlib.reload(frigate_camera_config_tool)
        assert reloaded.FRIGATE_CONFIG_PATH == "/app/config/config.yml"
    importlib.reload(frigate_camera_config_tool)


def test_discover_onvif_exceptions():
    """Verify exception handling during ONVIF discovery and stream URI extraction."""
    with (
        patch(
            "utils.frigate_camera_config_tool.NodeScanner.get_primary_ip",
            return_value="192.168.1.10",
        ),
        patch(
            "utils.frigate_camera_config_tool.check_ip_port",
            side_effect=lambda ip, port: ip if ip == "192.168.1.55" else None,
        ),
    ):
        mock_cam = MagicMock()
        mock_cam.create_media_service = AsyncMock()
        mock_cam.devicemgmt.GetDeviceInformation = AsyncMock(
            return_value=MagicMock(Model="Cam1")
        )
        mock_cam.media.GetProfiles = AsyncMock(return_value=[MagicMock(token="t1")])
        mock_cam.media.GetStreamUri = AsyncMock(side_effect=Exception("URI Fail"))

        calls = [0]

        def _onvif_factory(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise frigate_camera_config_tool.ONVIFError("Auth fail")
            return mock_cam

        with patch(
            "utils.frigate_camera_config_tool.ONVIFCamera",
            side_effect=_onvif_factory,
        ):
            cams = _run_async(frigate_camera_config_tool.discover_onvif_cameras())
            assert cams == []
