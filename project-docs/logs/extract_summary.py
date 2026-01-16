#!/usr/bin/env python3
"""
Extract readable summary from Claude Code transcript (JSONL format).

Usage:
    python3 extract_summary.py session_20260112-20260116_transcript.jsonl > summary.txt
    python3 extract_summary.py session_20260112-20260116_transcript.jsonl --messages-only > messages.txt
"""

import json
import sys
from datetime import datetime


def parse_timestamp(ts_str: str) -> str:
    """Parse ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return ts_str


def extract_text_from_content(content) -> str:
    """Extract text from content array."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif item.get("type") == "tool_use":
                    tool_name = item.get("name", "unknown")
                    text_parts.append(f"[Tool: {tool_name}]")
            elif isinstance(item, str):
                text_parts.append(item)
        return "\n".join(text_parts)

    return str(content)


def extract_messages(jsonl_file: str, messages_only: bool = False) -> list[dict]:
    """Extract messages from JSONL transcript."""
    messages = []
    stats = {"user": 0, "assistant": 0, "system": 0, "snapshots": 0, "queue": 0, "other": 0}

    with open(jsonl_file) as f:
        for line_num, line in enumerate(f, 1):
            try:
                event = json.loads(line)
                event_type = event.get("type", "unknown")

                # Update stats
                if event_type == "user":
                    stats["user"] += 1
                elif event_type == "assistant":
                    stats["assistant"] += 1
                elif event_type == "system":
                    stats["system"] += 1
                elif event_type == "file-history-snapshot":
                    stats["snapshots"] += 1
                elif event_type == "queue-operation":
                    stats["queue"] += 1
                else:
                    stats["other"] += 1

                # Extract messages
                if event_type in ["user", "assistant", "system"]:
                    timestamp = parse_timestamp(event.get("timestamp", "unknown"))
                    content = event.get("content", event.get("text", ""))
                    text = extract_text_from_content(content)

                    if text.strip() or not messages_only:
                        messages.append(
                            {
                                "line": line_num,
                                "timestamp": timestamp,
                                "role": event_type,
                                "content": text,
                            }
                        )

            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Error processing line {line_num}: {e}", file=sys.stderr)

    return messages, stats


def print_summary(messages: list[dict], stats: dict, messages_only: bool = False):
    """Print readable summary."""
    if not messages_only:
        print("=" * 80)
        print("CLAUDE CODE SESSION TRANSCRIPT SUMMARY")
        print("=" * 80)
        print()
        print("STATISTICS:")
        print(f"  User messages:      {stats['user']:,}")
        print(f"  Assistant messages: {stats['assistant']:,}")
        print(f"  System messages:    {stats['system']:,}")
        print(f"  File snapshots:     {stats['snapshots']:,}")
        print(f"  Queue operations:   {stats['queue']:,}")
        print(f"  Other events:       {stats['other']:,}")
        print(f"  TOTAL EVENTS:       {sum(stats.values()):,}")
        print()
        print("=" * 80)
        print("MESSAGES")
        print("=" * 80)
        print()

    for msg in messages:
        role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(msg["role"], "❓")

        print(f"{role_emoji} [{msg['timestamp']}] {msg['role'].upper()}")
        print("-" * 80)

        # Truncate very long messages
        content = msg["content"]
        if len(content) > 2000 and not messages_only:
            content = content[:2000] + f"\n... (truncated, {len(msg['content']) - 2000} more chars)"

        print(content)
        print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    jsonl_file = sys.argv[1]
    messages_only = "--messages-only" in sys.argv

    try:
        messages, stats = extract_messages(jsonl_file, messages_only)
        print_summary(messages, stats, messages_only)
    except FileNotFoundError:
        print(f"Error: File not found: {jsonl_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
