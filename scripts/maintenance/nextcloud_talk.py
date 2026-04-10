#!/usr/bin/env python3
"""Nextcloud Talk API utilities for messaging Georges Crespi (beta tester).

Provides CLI sub-commands:
  send <message>             — envoyer un message dans la conversation Georges
  poll [--timeout 30]        — lire les nouveaux messages (long-polling)
  history [--limit 20]       — afficher l'historique récent
  share <nextcloud-path>     — partager un fichier déjà sur Nextcloud
  rooms                      — lister toutes les conversations

Examples:
  python scripts/maintenance/nextcloud_talk.py send "Scénario 01 prêt, ouvre sessions/session-01-diagnostic/"
  python scripts/maintenance/nextcloud_talk.py poll --timeout 30
  python scripts/maintenance/nextcloud_talk.py share /magma-cycling-beta/builds/magma-v0.3.2.zip
  python scripts/maintenance/nextcloud_talk.py history --limit 10

Credentials: app password lu depuis ~/.config/magma/nc_app_pass
"""

import argparse
import sys
import time
from pathlib import Path

import requests

NC_URL = "https://cloud.alliancejr.eu"
NC_USER = "devleader"
GEORGES_ROOM_TOKEN = "mhvjtzkq"
APP_PASS_FILE = Path.home() / ".config" / "magma" / "nc_app_pass"
TALK_BASE = f"{NC_URL}/ocs/v2.php/apps/spreed/api"
HEADERS = {"OCS-APIRequest": "true", "Accept": "application/json"}


def _get_app_pass() -> str:
    if not APP_PASS_FILE.exists():
        print(f"Error: {APP_PASS_FILE} not found — run the onboarding first")
        sys.exit(1)
    return APP_PASS_FILE.read_text().strip()


def _auth() -> tuple[str, str]:
    return (NC_USER, _get_app_pass())


def send_message(message: str, room_token: str = GEORGES_ROOM_TOKEN) -> dict:
    """Envoyer un message texte dans une conversation."""
    resp = requests.post(
        f"{TALK_BASE}/v1/chat/{room_token}",
        auth=_auth(),
        headers=HEADERS,
        data={"message": message},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()["ocs"]["data"]
    return data


def poll_messages(
    room_token: str = GEORGES_ROOM_TOKEN,
    last_known_id: int = 0,
    timeout: int = 30,
) -> list[dict]:
    """Long-polling : bloque jusqu'à timeout secondes ou jusqu'à nouveaux messages."""
    resp = requests.get(
        f"{TALK_BASE}/v1/chat/{room_token}",
        auth=_auth(),
        headers=HEADERS,
        params={
            "lookIntoFuture": 1,
            "lastKnownMessageId": last_known_id,
            "timeout": timeout,
        },
        timeout=timeout + 5,
    )
    if resp.status_code == 304:
        return []
    resp.raise_for_status()
    return resp.json()["ocs"]["data"] or []


def get_history(room_token: str = GEORGES_ROOM_TOKEN, limit: int = 20) -> list[dict]:
    """Récupérer l'historique des messages."""
    resp = requests.get(
        f"{TALK_BASE}/v1/chat/{room_token}",
        auth=_auth(),
        headers=HEADERS,
        params={"lookIntoFuture": 0, "limit": limit},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["ocs"]["data"] or []


def share_file(nextcloud_path: str, room_token: str = GEORGES_ROOM_TOKEN) -> dict:
    """Partager un fichier déjà présent sur Nextcloud comme message riche."""
    resp = requests.post(
        f"{TALK_BASE}/v1/chat/{room_token}/share",
        auth=_auth(),
        headers=HEADERS,
        data={"path": nextcloud_path, "objectType": "file"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["ocs"]["data"]


def list_rooms() -> list[dict]:
    """Lister toutes les conversations accessibles."""
    resp = requests.get(
        f"{TALK_BASE}/v4/room",
        auth=_auth(),
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["ocs"]["data"] or []


def _fmt_message(msg: dict) -> str:
    ts = time.strftime("%H:%M:%S", time.localtime(msg.get("timestamp", 0)))
    actor = msg.get("actorDisplayName", "?")
    text = msg.get("message", "")
    return f"[{ts}] {actor}: {text}"


def main():
    """Point d'entrée CLI — parse les sous-commandes et délègue aux fonctions Talk."""
    parser = argparse.ArgumentParser(description="Nextcloud Talk — Dev Leader CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_send = sub.add_parser("send", help="Envoyer un message à Georges")
    p_send.add_argument("message", help="Texte du message")
    p_send.add_argument("--room", default=GEORGES_ROOM_TOKEN)

    p_poll = sub.add_parser("poll", help="Long-polling nouveaux messages")
    p_poll.add_argument("--timeout", type=int, default=30)
    p_poll.add_argument("--room", default=GEORGES_ROOM_TOKEN)
    p_poll.add_argument("--last-id", type=int, default=0)

    p_hist = sub.add_parser("history", help="Historique récent")
    p_hist.add_argument("--limit", type=int, default=20)
    p_hist.add_argument("--room", default=GEORGES_ROOM_TOKEN)

    p_share = sub.add_parser("share", help="Partager un fichier Nextcloud")
    p_share.add_argument(
        "path", help="Chemin dans Nextcloud (ex: /magma-cycling-beta/builds/x.zip)"
    )
    p_share.add_argument("--room", default=GEORGES_ROOM_TOKEN)

    sub.add_parser("rooms", help="Lister les conversations")

    args = parser.parse_args()

    if args.cmd == "send":
        msg = send_message(args.message, args.room)
        print(f"✅ Envoyé (id={msg.get('id')}): {msg.get('message')}")

    elif args.cmd == "poll":
        print(f"En écoute (timeout={args.timeout}s)…")
        msgs = poll_messages(args.room, args.last_id, args.timeout)
        if not msgs:
            print("(aucun nouveau message)")
        for m in msgs:
            print(_fmt_message(m))

    elif args.cmd == "history":
        msgs = get_history(args.room, args.limit)
        if not msgs:
            print("(aucun message)")
        for m in msgs:
            print(_fmt_message(m))

    elif args.cmd == "share":
        result = share_file(args.path, args.room)
        print(f"✅ Fichier partagé: {result.get('message', args.path)}")

    elif args.cmd == "rooms":
        rooms = list_rooms()
        for r in rooms:
            print(f"  {r['token']}  [{r['type']}]  {r['displayName']}")


if __name__ == "__main__":
    main()
