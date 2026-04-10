#!/usr/bin/env python3
"""Nextcloud Talk polling daemon — LaunchAgent compatible.

Polls all Talk rooms, writes new messages to inbox files for each agent.
Designed to be called periodically by a LaunchAgent (every 10 min).

State: ~/.local/share/magma-cycling/talk_poll_state.json
Inbox: ~/.local/share/magma-cycling/talk_inbox/
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

# Reuse auth/config from nextcloud_talk.py (same directory)
sys.path.insert(0, str(Path(__file__).parent))
from nextcloud_talk import HEADERS, TALK_BASE, _auth, list_rooms  # noqa: E402

STATE_FILE = Path.home() / ".local/share/magma-cycling/talk_poll_state.json"
INBOX_DIR = Path.home() / ".local/share/magma-cycling/talk_inbox"
AGENTS = ["devleader", "admin", "junior"]


def load_state() -> dict:
    """Charge le lastKnownMessageId par room."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    """Persiste le state entre exécutions."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_recent_messages(room_token: str, last_id: int) -> tuple[list[dict], int]:
    """Récupère les messages récents (sans long-polling).

    Returns:
        (filtered_messages, max_id_seen) — max_id_seen avance le curseur
        même si aucun message ne passe le filtre.
    """
    params = {"lookIntoFuture": 0, "limit": 50}
    if last_id:
        params["lastKnownMessageId"] = last_id
    resp = requests.get(
        f"{TALK_BASE}/v1/chat/{room_token}",
        auth=_auth(),
        headers=HEADERS,
        params=params,
        timeout=10,
    )
    if resp.status_code == 304:
        return [], last_id
    resp.raise_for_status()
    all_messages = resp.json()["ocs"]["data"] or []
    if not all_messages:
        return [], last_id

    # Curseur global : avance même pour les messages filtrés
    max_id_seen = max(m["id"] for m in all_messages)

    # Filtrer : après last_id, utilisateurs uniquement, pas nos propres messages
    filtered = [
        m
        for m in all_messages
        if m["id"] > last_id and m.get("actorType") == "users" and m.get("actorId") != "devleader"
    ]
    return filtered, max_id_seen


def append_to_inbox(messages: list[dict], room_name: str):
    """Append messages au inbox global + par agent."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    global_inbox = INBOX_DIR / "inbox.jsonl"

    with open(global_inbox, "a") as f:
        for msg in messages:
            entry = {
                "id": msg["id"],
                "room": room_name,
                "actor": msg.get("actorDisplayName", "?"),
                "actor_id": msg.get("actorId", "?"),
                "message": msg.get("message", ""),
                "timestamp": msg.get("timestamp", 0),
                "received_at": datetime.now().isoformat(),
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Copie vers chaque agent (routage futur — pour l'instant identique)
    for agent in AGENTS:
        agent_inbox = INBOX_DIR / f"{agent}.jsonl"
        with open(agent_inbox, "a") as f:
            for msg in messages:
                entry = {
                    "id": msg["id"],
                    "room": room_name,
                    "actor": msg.get("actorDisplayName", "?"),
                    "message": msg.get("message", ""),
                    "timestamp": msg.get("timestamp", 0),
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def poll_all_rooms():
    """Poll tous les rooms et enregistre les nouveaux messages."""
    state = load_state()
    rooms = list_rooms()
    total_new = 0

    for room in rooms:
        token = room["token"]
        name = room.get("displayName", token)
        last_id = state.get(token, 0)

        try:
            messages, max_id_seen = get_recent_messages(token, last_id)
        except requests.RequestException as exc:
            print(f"[{name}] Erreur: {exc}")
            continue

        # Toujours avancer le curseur (même sans messages filtrés)
        if max_id_seen > last_id:
            state[token] = max_id_seen

        if messages:
            append_to_inbox(messages, name)
            total_new += len(messages)
            print(f"[{name}] {len(messages)} nouveau(x) message(s)")

    save_state(state)

    if total_new > 0:
        print(f"Total: {total_new} nouveau(x) message(s)")
    else:
        print("Aucun nouveau message")

    return total_new


if __name__ == "__main__":
    poll_all_rooms()
