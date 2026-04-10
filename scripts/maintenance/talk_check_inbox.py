#!/usr/bin/env python3
"""Consulte l'inbox Talk pour un agent donné.

Usage:
  poetry run python scripts/maintenance/talk_check_inbox.py
  poetry run python scripts/maintenance/talk_check_inbox.py --agent devleader
  poetry run python scripts/maintenance/talk_check_inbox.py --unread
  poetry run python scripts/maintenance/talk_check_inbox.py --clear
  poetry run python scripts/maintenance/talk_check_inbox.py --last 5
"""

import argparse
import json
import time
from pathlib import Path

INBOX_DIR = Path.home() / ".local/share/magma-cycling/talk_inbox"


def _read_inbox(agent: str | None = None) -> list[dict]:
    """Lit les messages depuis l'inbox."""
    if agent:
        inbox_file = INBOX_DIR / f"{agent}.jsonl"
    else:
        inbox_file = INBOX_DIR / "inbox.jsonl"

    if not inbox_file.exists():
        return []

    messages = []
    for line in inbox_file.read_text().splitlines():
        line = line.strip()
        if line:
            messages.append(json.loads(line))
    return messages


def _last_read_file(agent: str | None) -> Path:
    name = agent or "global"
    return INBOX_DIR / f".last_read_{name}"


def _get_last_read_id(agent: str | None) -> int:
    f = _last_read_file(agent)
    if f.exists():
        return int(f.read_text().strip())
    return 0


def _set_last_read_id(agent: str | None, msg_id: int):
    f = _last_read_file(agent)
    f.write_text(str(msg_id))


def _fmt_message(msg: dict) -> str:
    ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(msg.get("timestamp", 0)))
    actor = msg.get("actor", "?")
    room = msg.get("room", "?")
    text = msg.get("message", "")
    return f"[{ts}] ({room}) {actor}: {text}"


def main():
    """Point d'entree CLI — consulte et gere l'inbox Talk."""
    parser = argparse.ArgumentParser(description="Consulter l'inbox Talk")
    parser.add_argument(
        "--agent",
        choices=["devleader", "admin", "junior"],
        help="Inbox d'un agent specifique (defaut: global)",
    )
    parser.add_argument(
        "--unread",
        action="store_true",
        help="Afficher seulement les messages non lus",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Marquer tous les messages comme lus",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=0,
        help="Afficher les N derniers messages",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sortie JSON (pour consommation programmatique)",
    )
    args = parser.parse_args()

    messages = _read_inbox(args.agent)

    if args.clear:
        if messages:
            max_id = max(m.get("id", 0) for m in messages)
            _set_last_read_id(args.agent, max_id)
            print(f"Marque comme lu jusqu'a id={max_id} ({len(messages)} messages)")
        else:
            print("Inbox vide, rien a marquer")
        return

    if args.unread:
        last_read = _get_last_read_id(args.agent)
        messages = [m for m in messages if m.get("id", 0) > last_read]

    if args.last > 0:
        messages = messages[-args.last :]

    if not messages:
        print("Aucun message" + (" non lu" if args.unread else ""))
        return

    if args.json:
        for msg in messages:
            print(json.dumps(msg, ensure_ascii=False))
    else:
        for msg in messages:
            print(_fmt_message(msg))
        print(f"\n--- {len(messages)} message(s) ---")


if __name__ == "__main__":
    main()
