# scripts/common/vault.py
"""Centralized Ansible Vault password resolution and in-memory decryption.

CMMI Level 5 zero-leak standard prevents leaking decrypted vault credentials
to disk or unmanaged child process environments.
"""

import os
from pathlib import Path
from typing import Optional


def resolve_vault_password_file() -> Optional[Path]:
    """Finds the active Ansible Vault password file path if configured."""
    candidate_paths = [
        os.getenv("ANSIBLE_VAULT_PASSWORD_FILE"),
        Path.cwd() / ".vault_password",
        Path.home() / ".vault_password",
    ]
    for cand in candidate_paths:
        if cand:
            path_obj = Path(cand).expanduser().resolve()
            if path_obj.is_file():
                return path_obj
    return None


def get_vault_password() -> Optional[str]:
    """Retrieves Ansible Vault password from env, password file, or secret storage."""
    # 1. Direct env variable
    direct = os.getenv("ANSIBLE_VAULT_PASSWORD")
    if direct:
        return direct.strip()

    # 2. Vault password file
    file_path = resolve_vault_password_file()
    if file_path and file_path.is_file():
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    return None
