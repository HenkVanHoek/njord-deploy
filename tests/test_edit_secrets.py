# tests/test_edit_secrets.py
"""Unit tests for scripts/edit_secrets.py."""

import os
from pathlib import Path
from unittest.mock import patch

from scripts.edit_secrets import (
    check_status,
    load_env_dict,
    mask_secret,
    save_env_file,
    set_variable,
)


def test_mask_secret() -> None:
    assert mask_secret("FOO_BAR", "plaintext") == "plaintext"
    assert mask_secret("PROXMOX_PASSWORD", "secret123") == "se****23"
    assert mask_secret("API_KEY", "123") == "****"
    assert mask_secret("EMPTY_PASS", "") == "[LEEG]"


def test_load_and_save_env(tmp_path: Path) -> None:
    test_env = tmp_path / ".env"
    initial_vars = {
        "PROXMOX_HOST": "https://192.168.178.51:8006",
        "PROXMOX_VM_PASSWORD": "dummy_password",
        "CUSTOM_KEY": "custom_val",
    }
    save_env_file(test_env, initial_vars)

    assert test_env.exists()
    if os.name != "nt":
        assert oct(os.stat(test_env).st_mode & 0o777) == "0o600"

    loaded = load_env_dict(test_env)
    assert loaded["PROXMOX_HOST"] == "https://192.168.178.51:8006"
    assert loaded["PROXMOX_VM_PASSWORD"] == "dummy_password"
    assert loaded["CUSTOM_KEY"] == "custom_val"


def test_check_status_and_set_variable(tmp_path: Path) -> None:
    test_env = tmp_path / ".env"
    with patch("scripts.edit_secrets.ENV_FILE", test_env):
        # 1. Missing file / required
        res = check_status()
        assert res == 1

        # 2. Set variables via set_variable
        assert set_variable("PROXMOX_HOST=https://1.2.3.4") == 0
        assert set_variable("PROXMOX_NODE=pve") == 0
        assert set_variable("PROXMOX_USER=root@pam") == 0
        assert set_variable("PROXMOX_TOKEN_ID=mytoken") == 0
        assert set_variable("PROXMOX_TOKEN_SECRET=mysecret") == 0
        assert set_variable("PROXMOX_VM_USER=root") == 0
        assert set_variable("PROXMOX_VM_PASSWORD=mypassword") == 0

        # Invalid format
        assert set_variable("INVALID_NO_EQUALS") == 1

        # 3. Check status when all required are present
        res_ok = check_status()
        assert res_ok == 0


def test_get_secrets_data_and_batch_set(tmp_path: Path) -> None:
    from scripts.edit_secrets import get_secrets_data, set_variables

    test_env = tmp_path / ".env"
    with patch("scripts.edit_secrets.ENV_FILE", test_env):
        # Batch set variables
        res = set_variables(
            {
                "PROXMOX_HOST": "https://10.0.0.1:8006",
                "CUSTOM_VAR": "secret_abc",
            }
        )
        assert res["success"] is True
        assert res["updated_count"] == 2

        # Dump structured data
        data = get_secrets_data()
        assert data["project"] == "njord-deploy"
        assert data["type"] == "dotenv"
        keys = [item["key"] for item in data["secrets"]]
        assert "PROXMOX_HOST" in keys
        assert "CUSTOM_VAR" in keys

        # No changes when re-setting same values
        res_noop = set_variables({"PROXMOX_HOST": "https://10.0.0.1:8006"})
        assert res_noop["updated_count"] == 0
