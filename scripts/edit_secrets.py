#!/usr/bin/env python3
# File: scripts/edit_secrets.py
# Part of the NjordDeploy project.
"""NjordDeploy Environment Secrets Manager.

Hiermee open je in vi (of je ingestelde $EDITOR) veilig het .env bestand
van NjordDeploy met alle gegroepeerde configuratiewaarden en geheimen.

Bij het opslaan worden permissies direct strikt op 0600 gezet en wordt de
syntaxis gevalideerd. Geheimen worden NOOIT in de chat of logs geprint.

Gebruik:
  python3 scripts/edit_secrets.py          # Interactief bewerken in $EDITOR
  python3 scripts/edit_secrets.py --check  # Toon gemaskeerde statuscontrole
  python3 scripts/edit_secrets.py --set KEY=VALUE # Stel variabele in via CLI
"""

import argparse
import os
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Schema van bekende variabelen met beschrijving en groep
CONFIG_SCHEMA = [
    # --- Groep 1: Proxmox VE Hypervisor API (De Proeftuin) ---
    (
        "PROXMOX_HOST",
        "Proxmox VE API URL (bijv. https://192.168.178.51:8006)",
        "https://192.168.178.51:8006",
        True,
        "Proxmox VE API",
    ),
    (
        "PROXMOX_NODE",
        "Proxmox Hypervisor node naam (bijv. pve)",
        "pve",
        True,
        "Proxmox VE API",
    ),
    (
        "PROXMOX_USER",
        "Proxmox API gebruikersnaam (bijv. root@pam)",
        "root@pam",
        True,
        "Proxmox VE API",
    ),
    (
        "PROXMOX_TOKEN_ID",
        "Proxmox API Token ID (bijv. root@pam!clone-token)",
        "",
        True,
        "Proxmox VE API",
    ),
    (
        "PROXMOX_TOKEN_SECRET",
        "Proxmox API Token Secret (UUID)",
        "",
        True,
        "Proxmox VE API",
    ),
    (
        "PROXMOX_VERIFY_SSL",
        "SSL-certificaatvalidatie voor Proxmox API (true/false)",
        "false",
        False,
        "Proxmox VE API",
    ),
    # --- Groep 2: Guest LXC / VM SSH Credentials ---
    (
        "PROXMOX_VM_USER",
        "SSH/Admin gebruikersnaam testcontainer (root voor LXC, pivm voor VM)",
        "root",
        True,
        "Proxmox Guest Credentials",
    ),
    (
        "PROXMOX_VM_PASSWORD",
        "SSH/Admin wachtwoord voor De Proeftuin testcontainer/VM",
        "",
        True,
        "Proxmox Guest Credentials",
    ),
    (
        "PROXMOX_TEMPLATE_ID",
        "Master template VMID (912 voor Docker LXC, 902 voor VM)",
        "912",
        False,
        "Proxmox Guest Credentials",
    ),
    (
        "PROXMOX_BRIDGE",
        "Proxmox netwerk bridge (bijv. vmbr0)",
        "vmbr0",
        False,
        "Proxmox Guest Credentials",
    ),
    # --- Groep 3: Signal REST API Notificaties ---
    (
        "SIGNAL_API_URL",
        "Signal REST API URL voor autopilot escalaties",
        "http://192.168.178.118:8090/v2/send",
        False,
        "Signal Notificaties",
    ),
    (
        "SIGNAL_SENDER",
        "Afzender telefoonnummer voor Signal alerts",
        "+31651107603",
        False,
        "Signal Notificaties",
    ),
    (
        "SIGNAL_RECIPIENT",
        "Ontvanger telefoonnummer voor Signal escalaties",
        "+31651107603",
        False,
        "Signal Notificaties",
    ),
    # --- Groep 4: Container Engine & AI Modellen ---
    (
        "CONTAINER_ENGINE",
        "Standaard container engine (docker of podman)",
        "docker",
        False,
        "Container & AI Engine",
    ),
    (
        "AI_PROVIDER",
        "Standaard AI Provider (gemini, ollama, openai)",
        "gemini",
        False,
        "Container & AI Engine",
    ),
    (
        "GEMINI_API_KEY",
        "Google Gemini API Key (voor AI generator / diagnoser)",
        "",
        False,
        "Container & AI Engine",
    ),
    (
        "GITHUB_TOKEN",
        "GitHub Personal Access Token (voor rate limits & security alerts)",
        "",
        False,
        "GitHub API",
    ),
]


def load_env_dict(path: Path) -> Dict[str, str]:
    """Leest een .env bestand in als dictionary (met behoud van lege waarden)."""
    env_vars: Dict[str, str] = {}
    if not path.exists():
        return env_vars
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            k, v = stripped.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            env_vars[k] = v
    return env_vars


def save_env_file(path: Path, env_vars: Dict[str, str]) -> None:
    """Schrijft het .env bestand gestructureerd weg met permissies 0600."""
    lines: List[str] = [
        "# =====================================================================",
        "# NJORDDEPLOY OMGEVINGSVARIABELEN & GEHEIMEN (.env)",
        "# Automatisch beheerd via: scripts/edit_secrets.py",
        "# Permissies: 0600 (strikt vertrouwelijk)",
        "# =====================================================================\n",
    ]

    handled_keys = set()
    current_group: Optional[str] = None

    for key, desc, default_val, _, group in CONFIG_SCHEMA:
        if group != current_group:
            current_group = group
            lines.append(f"\n# --- {group} ---")
        val = env_vars.get(key, default_val)
        escaped_val = val.replace('"', '\\"')
        lines.append(f"# {desc}")
        lines.append(f'{key}="{escaped_val}"')
        handled_keys.add(key)

    # Schrijf eventuele overige/aangepaste variabelen weg
    remaining = [k for k in env_vars.keys() if k not in handled_keys]
    if remaining:
        lines.append("\n# --- Overige & Maatwerk Variabelen ---")
        for k in sorted(remaining):
            v = env_vars[k].replace('"', '\\"')
            lines.append(f'{k}="{v}"')

    content = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    os.chmod(path, 0o600)


def mask_secret(key: str, val: str) -> str:
    """Maskeert gevoelige waarden voor veilige weergave in de terminal."""
    if not val:
        return "[LEEG]"
    sensitive_keywords = ("PASS", "SECRET", "KEY", "TOKEN")
    if any(k in key.upper() for k in sensitive_keywords):
        if len(val) <= 4:
            return "****"
        return f"{val[:2]}****{val[-2:]}"
    return val


def check_status() -> int:
    """Toont een gemaskeerd overzicht van de geconfigureerde geheimen."""
    print("=" * 72)
    print("NJORDDEPLOY CREDENTIALS PRE-FLIGHT CONTROLE")
    print(f"Configuratiebestand: {ENV_FILE}")
    print("=" * 72)

    env_vars = load_env_dict(ENV_FILE)
    missing_required = 0

    current_group = None
    for key, desc, _, required, group in CONFIG_SCHEMA:
        if group != current_group:
            current_group = group
            print(f"\n📂 {group}:")

        val = env_vars.get(key, "")
        masked = mask_secret(key, val)

        if required and not val:
            status = "❌ ONTBREEKT (Vereist)"
            missing_required += 1
        elif val:
            status = "✅ INGESTELD"
        else:
            status = "⚪ Optioneel"

        print(f"  • {key:22} : {status:22} ({masked})")

    # Extra keys
    known_keys = {item[0] for item in CONFIG_SCHEMA}
    custom_keys = [k for k in env_vars if k not in known_keys]
    if custom_keys:
        print("\n📂 Overige variabelen:")
        for k in sorted(custom_keys):
            masked = mask_secret(k, env_vars[k])
            print(f"  • {k:22} : ✅ INGESTELD            ({masked})")

    print("\n" + "=" * 72)
    if missing_required == 0:
        print("🎉 Alle vereiste credentials voor Proxmox & Autopilot zijn aanwezig!")
        return 0
    else:
        print(f"⚠️ Er ontbreken {missing_required} vereiste variabele(n)!")
        print("Tip: Voer 'python3 scripts/edit_secrets.py' uit om ze aan te vullen.")
        return 1


def interactive_edit() -> int:
    """Opent het .env bestand in $EDITOR met strikte permissies."""
    current_vars = load_env_dict(ENV_FILE)

    # Maak een tijdelijk bestand aan met permissie 0600
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".env", delete=False
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)
        save_env_file(tmp_path, current_vars)

    os.chmod(tmp_path, 0o600)

    editor = os.environ.get("EDITOR") or "/usr/bin/vi"
    if not os.path.exists(editor) and editor.startswith("/"):
        editor = "vi"

    mtime_before = os.path.getmtime(tmp_path)
    print(f"[*] Openen van geheimen in {editor} (permissies: 0600)...")
    # noinspection PyBroadException
    try:
        subprocess.run([editor, str(tmp_path)], check=True)  # nosec B603
    except Exception as exc:
        print(f"[-] Fout bij starten van editor: {exc}")
        if tmp_path.exists():
            tmp_path.unlink()
        return 1

    mtime_after = os.path.getmtime(tmp_path)
    if mtime_after == mtime_before:
        print("[*] Geen wijzigingen opgeslagen. Afgesloten.")
        if tmp_path.exists():
            tmp_path.unlink()
        return 0

    # Lees en valideer gewijzigde waarden
    try:
        new_vars = load_env_dict(tmp_path)
        save_env_file(ENV_FILE, new_vars)
        print(
            f"[+] Succesvol bijgewerkt: {ENV_FILE} "
            f"({len(new_vars)} variabelen, permissies: 0600)"
        )
    except Exception as exc:
        print(f"[-] Fout bij verwerken van bewerkt bestand: {exc}")
        print(f"[-] Tijdelijk bestand bewaard voor herstel: {tmp_path}")
        return 1
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return 0


def set_variable(kv_pair: str) -> int:
    """Stelt direct een sleutel/waarde-paar in via de CLI."""
    if "=" not in kv_pair:
        print("[-] Fout: Geef op in formaat: KEY=WAARDE")
        return 1
    key, val = kv_pair.split("=", 1)
    key = key.strip()
    val = val.strip().strip("'\"")

    env_vars = load_env_dict(ENV_FILE)
    env_vars[key] = val
    save_env_file(ENV_FILE, env_vars)
    masked = mask_secret(key, val)
    print(f"[+] Variabele '{key}' succesvol ingesteld op: {masked}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NjordDeploy Veilige Secrets & .env Manager"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Toon gemaskeerde pre-flight status van alle credentials.",
    )
    parser.add_argument(
        "--set",
        type=str,
        metavar="KEY=VALUE",
        help="Stel direct een sleutel/waarde-paar in zonder de editor te openen.",
    )

    args = parser.parse_args()

    if args.check:
        return check_status()
    elif args.set:
        return set_variable(args.set)
    else:
        return interactive_edit()


if __name__ == "__main__":
    sys.exit(main())
