# tests/utils/test_ssh_utils.py

"""
Unit tests for ssh_utils.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from utils.ssh_utils import set_key


def test_set_key_appends_to_file(tmp_path: Path):
    target_file = tmp_path / ".env"
    set_key(str(target_file), "TEST_KEY", "test_value")

    assert target_file.exists()
    content = target_file.read_text(encoding="utf-8")
    assert "TEST_KEY=test_value\n" in content


def test_set_key_raises_io_error_on_failure():
    with patch("builtins.open", side_effect=IOError("Permission denied")):
        with pytest.raises(IOError):
            set_key("/unauthorized/path/.env", "KEY", "VAL")
