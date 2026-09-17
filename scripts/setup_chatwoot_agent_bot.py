#!/usr/bin/env python3
"""NjordDeploy Chatwoot AI Agent Bot Setup Utility.

Connects to self-hosted Chatwoot (e.g. https://chat.njorddeploy.com), registers
an autonomous Agent Bot, links it to web widget inboxes, and validates end-to-end
AI responses via NjordDeploy's sovereign knowledge base.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from managers.chatwoot_bot_manager import ChatwootBotManager  # noqa: E402


def list_inboxes(
    base_url: str, account_id: int, api_token: str
) -> List[Dict[str, Any]]:
    """Fetches all inboxes associated with the account."""
    url = f"{base_url.rstrip('/')}/api/v1/accounts/{account_id}/inboxes"
    headers = {"api_access_token": api_token}
    resp = requests.get(url, headers=headers, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    return data.get("payload", []) if isinstance(data, dict) else []


def register_agent_bot(
    base_url: str,
    account_id: int,
    api_token: str,
    bot_name: str,
    outgoing_url: str,
) -> Optional[Dict[str, Any]]:
    """Registers an Agent Bot in Chatwoot."""
    url = f"{base_url.rstrip('/')}/api/v1/accounts/{account_id}/agent_bots"
    headers = {
        "Content-Type": "application/json",
        "api_access_token": api_token,
    }
    payload = {
        "name": bot_name,
        "description": ("NjordDeploy Sovereign AI Assistant & Knowledge Base Bot"),
        "outgoing_url": outgoing_url,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=10.0)
    if resp.status_code in (200, 201):
        return resp.json()
    print(f"Error registering agent bot: {resp.status_code} - {resp.text}")
    return None


def assign_bot_to_inbox(
    base_url: str,
    account_id: int,
    inbox_id: int,
    bot_id: int,
    api_token: str,
) -> bool:
    """Assigns an Agent Bot to a specific inbox."""
    url = (
        f"{base_url.rstrip('/')}/api/v1/accounts/{account_id}/"
        f"inboxes/{inbox_id}/set_agent_bot"
    )
    headers = {
        "Content-Type": "application/json",
        "api_access_token": api_token,
    }
    payload = {"agent_bot": bot_id}
    resp = requests.post(url, json=payload, headers=headers, timeout=10.0)
    return resp.status_code in (200, 201)


def main() -> None:
    """Main CLI entrypoint for Chatwoot AI Bot setup."""
    parser = argparse.ArgumentParser(
        description="Configure NjordDeploy AI Agent Bot in Chatwoot"
    )
    parser.add_argument(
        "--url",
        default=os.getenv("CHATWOOT_BASE_URL", "https://chat.njorddeploy.com"),
        help="Chatwoot base URL",
    )
    parser.add_argument(
        "--account-id",
        type=int,
        default=int(os.getenv("CHATWOOT_ACCOUNT_ID", "1")),
        help="Chatwoot Account ID (default: 1)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("CHATWOOT_ADMIN_API_TOKEN", ""),
        help="Chatwoot User or Platform API Access Token",
    )
    parser.add_argument(
        "--webhook-url",
        default="https://deploy.njorddeploy.com/api/v1/chatwoot/webhook",
        help="Inbound webhook URL for NjordDeploy",
    )
    parser.add_argument(
        "--test-query",
        default=None,
        help="Test prompt to verify AI engine knowledge retrieval directly",
    )

    args = parser.parse_args()

    if args.test_query:
        print(f"\n[?] Testing NjordDeploy AI Engine with query: '{args.test_query}'")
        bot = ChatwootBotManager()
        is_esc = bot.is_escalation_request(args.test_query)
        print(f"[i] Escalation detected: {is_esc}")
        sys_context = bot.get_knowledge_context()
        prompt = (
            f"Bezoeker vraagt via de NjordDeploy live chat widget:\n"
            f'"{args.test_query}"\n\nGeef een behulpzaam antwoord:'
        )
        try:
            answer = bot.ai_engine.generate(prompt=prompt, system_context=sys_context)
            print("\n[✓] Generated Answer:\n" + "=" * 40)
            print(answer)
            print("=" * 40)
        except Exception as exc:
            print(f"[!] AI Generator error: {exc}")
        return

    print("=" * 60)
    print("🤖 NjordDeploy Chatwoot AI Agent Bot Setup")
    print("=" * 60)
    print(f"Chatwoot URL: {args.url}")
    print(f"Account ID  : {args.account_id}")
    print(f"Webhook URL : {args.webhook_url}\n")

    if not args.token:
        print(
            "[i] Geen API token meegegeven. Je kunt de Agent Bot handmatig of "
            "geautomatiseerd instellen:\n"
        )
        print("Optie A: Automatisch via CLI:")
        print(
            "  python3 scripts/setup_chatwoot_agent_bot.py "
            "--token <JOUW_CHATWOOT_API_TOKEN>\n"
        )
        print("Optie B: Handmatig via het Chatwoot Dashboard:")
        print(
            f"  1. Ga naar {args.url}/app/accounts/{args.account_id}/settings/inboxes"
        )
        print("  2. Klik op 'Instellingen' van je Live Chat Website Inbox.")
        print("  3. Ga naar 'Samenwerkers' of 'Integraties' -> 'Webhooks'.")
        print(f"  4. Voeg een webhook toe met URL: {args.webhook_url}")
        print("     en selecteer het event: 'message_created'.")
        print("  5. Sla de wijzigingen op.\n")
        return

    try:
        inboxes = list_inboxes(args.url, args.account_id, args.token)
        print(f"[✓] Gevonden inboxes ({len(inboxes)}):")
        for ibox in inboxes:
            ch_type = ibox.get("channel_type")
            print(f"  - [{ibox.get('id')}] {ibox.get('name')} ({ch_type})")

        print("\n[+] Registreren van Agent Bot 'Njord Assistant'...")
        bot_res = register_agent_bot(
            args.url,
            args.account_id,
            args.token,
            "Njord Assistant",
            args.webhook_url,
        )
        if bot_res and isinstance(bot_res.get("id"), int):
            bot_id = int(bot_res["id"])
            print(f"[✓] Agent Bot succesvol geregistreerd met ID: {bot_id}")
            if inboxes:
                first_inbox, *_ = inboxes
                raw_inbox_id = first_inbox.get("id")
                if isinstance(raw_inbox_id, int):
                    target_inbox_id = raw_inbox_id
                    print(f"[+] Koppelen van bot aan inbox ID {target_inbox_id}...")
                    success = assign_bot_to_inbox(
                        args.url,
                        args.account_id,
                        target_inbox_id,
                        bot_id,
                        args.token,
                    )
                    if success:
                        print("[✓] Bot succesvol gekoppeld aan inbox!")
                    else:
                        print("[!] Koppelen aan inbox mislukt.")
    except Exception as exc:
        print(f"[!] Fout tijdens communicatie met Chatwoot: {exc}")


if __name__ == "__main__":
    main()
