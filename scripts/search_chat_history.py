#!/usr/bin/env python3
"""CLI utility to search through local Antigravity chat history transcripts.

Usage:
    python scripts/search_chat_history.py <query>
    python scripts/search_chat_history.py --conv-id <conversation_id>
"""

import argparse
import glob
import json
import os
import sys
from typing import Dict, List, Optional


def find_brain_directory() -> str:
    """Return the absolute path to the Antigravity brain directory."""
    home_dir = os.path.expanduser("~")
    brain_path = os.path.join(home_dir, ".gemini", "antigravity-cli", "brain")
    return brain_path


def search_transcripts(
    query: str,
    conv_id: Optional[str] = None,
    case_sensitive: bool = False,
    max_results: int = 20,
) -> List[Dict[str, str]]:
    """Search transcript JSONL files for a given query string or conv_id."""
    brain_dir = find_brain_directory()
    if not os.path.isdir(brain_dir):
        print(f"Error: Brain directory not found at {brain_dir}")
        return []

    pattern = os.path.join(
        brain_dir, "*", ".system_generated", "logs", "transcript.jsonl"
    )
    files = glob.glob(pattern)

    results = []
    search_term = query if case_sensitive else query.lower()

    for file_path in files:
        current_conv_id = file_path.split(os.sep)[-4]
        if conv_id and current_conv_id != conv_id:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    content = str(data.get("content", ""))
                    source = data.get("source", "")
                    created_at = data.get("created_at", "")

                    target_text = content if case_sensitive else content.lower()

                    if query and search_term in target_text:
                        results.append(
                            {
                                "conv_id": current_conv_id,
                                "created_at": created_at,
                                "source": source,
                                "content": content,
                            }
                        )
                    elif not query and conv_id:
                        results.append(
                            {
                                "conv_id": current_conv_id,
                                "created_at": created_at,
                                "source": source,
                                "content": content,
                            }
                        )
        except Exception:  # nosec B112
            continue

    return results[:max_results]


def main() -> None:
    """Parse CLI arguments and display search results."""
    parser = argparse.ArgumentParser(
        description="Search through Antigravity chat history."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="Search query term (e.g. 'positionering')",
    )
    parser.add_argument(
        "--conv-id",
        type=str,
        default=None,
        help="Filter or display a specific conversation ID",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Perform case-sensitive search",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of result steps to display (default: 20)",
    )

    args = parser.parse_args()

    if not args.query and not args.conv_id:
        parser.print_help()
        sys.exit(1)

    print(f"🔍 Searching chat history for: '{args.query or args.conv_id}'...\n")
    matches = search_transcripts(
        query=args.query,
        conv_id=args.conv_id,
        case_sensitive=args.case_sensitive,
        max_results=args.limit,
    )

    if not matches:
        print("Geen resultaten gevonden.")
        return

    print(f"Totaal {len(matches)} match(es) gevonden:\n" + "=" * 60)
    for idx, match in enumerate(matches, start=1):
        print(
            f"[{idx}] Conversation ID: {match['conv_id']}\n"
            f"    Datum/Tijd     : {match['created_at']}\n"
            f"    Bron           : {match['source']}\n"
        )
        snippet = match["content"].replace("\n", " ")
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."
        print(f"    Inhoud Snippet : {snippet}\n" + "-" * 60)


if __name__ == "__main__":
    main()
