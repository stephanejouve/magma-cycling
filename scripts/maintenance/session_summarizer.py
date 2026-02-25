#!/usr/bin/env python3
"""
Automatic session summary generator from JSONL logs.

Purpose:
- Parse Claude Code session JSONL files
- Extract key events (commits, file changes, decisions, errors)
- Generate human-readable markdown summary

Usage:
    python session_summarizer.py <session.jsonl> [--output summary.md]
    python session_summarizer.py project-docs/sessions/SESSION_R9E_*.jsonl

Output:
    - Markdown summary with sections:
      * Session overview (date, duration, objective)
      * Key accomplishments (commits, files modified)
      * Decisions made (user questions answered)
      * Errors/warnings encountered
      * Metrics extracted (coverage, tests, etc.)
      * References (files created, commits)
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


class SessionSummary:
    """Extracted summary data from a session."""

    def __init__(self):
        """Initialize empty summary."""
        self.session_id = None
        self.start_time = None
        self.end_time = None
        self.user_messages = []
        self.assistant_messages = []
        self.commits = []
        self.files_created = []
        self.files_modified = []
        self.tool_calls = defaultdict(int)
        self.questions_asked = []
        self.errors = []
        self.todos = []
        self.metrics = {}


class SessionParser:
    """Parse JSONL session files and extract summary data."""

    def __init__(self, jsonl_path: Path):
        """Initialize parser.

        Args:
            jsonl_path: Path to JSONL file (original or chunk)
        """
        self.jsonl_path = jsonl_path
        self.summary = SessionSummary()

    def parse_entry(self, entry: dict[str, Any]) -> None:
        """Parse a single JSONL entry and update summary.

        Args:
            entry: Parsed JSON object from JSONL line
        """
        # Extract session ID
        if not self.summary.session_id and "sessionId" in entry:
            self.summary.session_id = entry["sessionId"]

        # Extract timestamps
        timestamp = entry.get("timestamp")
        if timestamp:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if not self.summary.start_time:
                self.summary.start_time = ts
            self.summary.end_time = ts

        entry_type = entry.get("type")

        # User messages
        if entry_type == "user":
            msg = entry.get("message", {}).get("content", "")
            if msg and len(msg) < 200:  # Skip very long messages
                self.summary.user_messages.append({"timestamp": timestamp, "content": msg})

        # Assistant messages and tool calls
        elif entry_type == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])

            # Extract tool calls
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_name = item.get("name", "unknown")
                    self.summary.tool_calls[tool_name] += 1

                    # Extract specific tool details
                    tool_input = item.get("input", {})

                    # Bash commands (look for git commits)
                    if tool_name == "Bash":
                        command = tool_input.get("command", "")
                        self._extract_git_commits(command)

                    # Files written
                    elif tool_name == "Write":
                        file_path = tool_input.get("file_path", "")
                        if file_path:
                            self.summary.files_created.append(file_path)

                    # Files edited
                    elif tool_name == "Edit":
                        file_path = tool_input.get("file_path", "")
                        if file_path:
                            self.summary.files_modified.append(file_path)

                    # Questions asked
                    elif tool_name == "AskUserQuestion":
                        questions = tool_input.get("questions", [])
                        for q in questions:
                            self.summary.questions_asked.append(
                                {
                                    "question": q.get("question", ""),
                                    "timestamp": timestamp,
                                }
                            )

                    # Todos
                    elif tool_name == "TodoWrite":
                        todos = tool_input.get("todos", [])
                        if todos:
                            self.summary.todos.append({"timestamp": timestamp, "todos": todos})

        # Errors in function results
        elif entry_type == "function_results":
            results = entry.get("content", [])
            for result in results:
                if isinstance(result, dict):
                    error = result.get("error")
                    if error and "error" in str(error).lower():
                        self.summary.errors.append(
                            {"timestamp": timestamp, "error": str(error)[:200]}
                        )

    def _extract_git_commits(self, command: str) -> None:
        """Extract git commit from bash command.

        Args:
            command: Bash command string
        """
        # Look for git commit commands
        if "git commit" not in command:
            return

        # Try different patterns in order
        # Pattern 1: Simple quotes
        match = re.search(r'git commit.*?-m\s*"([^"]+)"', command, re.DOTALL)
        if not match:
            match = re.search(r"git commit.*?-m\s*'([^']+)'", command, re.DOTALL)

        # Pattern 2: HEREDOC with EOF
        if not match:
            match = re.search(
                r'git commit.*?-m\s*"\$\(cat\s*<<\'?EOF\'?\s+(.*?)\s+EOF', command, re.DOTALL
            )

        # Pattern 3: Multiline with newlines
        if not match:
            match = re.search(r'git commit.*?-m\s*"([^"]+)', command.replace("\n", " "), re.DOTALL)

        if match:
            commit_msg = match.group(1).strip()
            # Clean up the message
            commit_msg = commit_msg.replace("\n", " ")
            commit_msg = re.sub(r"\s+", " ", commit_msg)
            # Extract first line/sentence (up to first period or newline)
            first_line = commit_msg.split("\n")[0].split(".")[0].strip()
            if first_line and len(first_line) > 10:  # Ignore very short matches
                self.summary.commits.append(first_line)

    def parse_file(self) -> SessionSummary:
        """Parse JSONL file and return summary.

        Returns:
            SessionSummary object with extracted data
        """
        with open(self.jsonl_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    self.parse_entry(entry)
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON at line {line_num}: {e}")
                    continue

        return self.summary


class SummaryGenerator:
    """Generate markdown summary from parsed session data."""

    def __init__(self, summary: SessionSummary, session_name: str):
        """Initialize generator.

        Args:
            summary: Parsed session summary data
            session_name: Name of the session (from filename)
        """
        self.summary = summary
        self.session_name = session_name

    def generate_markdown(self) -> str:
        """Generate markdown summary.

        Returns:
            Markdown-formatted summary string
        """
        lines = []

        # Header
        lines.append(f"# Session Summary: {self.session_name}\n")

        # Metadata
        if self.summary.start_time:
            date_str = self.summary.start_time.strftime("%Y-%m-%d")
            start_str = self.summary.start_time.strftime("%H:%M")
            end_str = self.summary.end_time.strftime("%H:%M") if self.summary.end_time else "?"
            duration = self._calculate_duration()

            lines.append(f"**Date:** {date_str}")
            lines.append(f"**Time:** {start_str} - {end_str} ({duration})")
            if self.summary.session_id:
                lines.append(f"**Session ID:** `{self.summary.session_id}`")
            lines.append("")

        lines.append("---\n")

        # Overview
        lines.append("## 📋 Session Overview\n")
        if self.summary.user_messages:
            first_msg = self.summary.user_messages[0]["content"]
            lines.append(f"**Initial request:** {first_msg}\n")
        lines.append(f"**Total interactions:** {len(self.summary.user_messages)} user messages\n")
        lines.append("---\n")

        # Key accomplishments (commits)
        if self.summary.commits:
            lines.append("## 🎯 Commits Created\n")
            for i, commit in enumerate(self.summary.commits, 1):
                lines.append(f"{i}. {commit}")
            lines.append("\n---\n")

        # Files created/modified
        if self.summary.files_created or self.summary.files_modified:
            lines.append("## 📁 Files Changed\n")

            if self.summary.files_created:
                lines.append(f"**Created ({len(self.summary.files_created)}):**\n")
                for f in sorted(set(self.summary.files_created))[:10]:
                    # Shorten path
                    short_path = self._shorten_path(f)
                    lines.append(f"- `{short_path}`")
                if len(self.summary.files_created) > 10:
                    lines.append(f"- ... and {len(self.summary.files_created) - 10} more")
                lines.append("")

            if self.summary.files_modified:
                lines.append(f"**Modified ({len(self.summary.files_modified)}):**\n")
                for f in sorted(set(self.summary.files_modified))[:10]:
                    short_path = self._shorten_path(f)
                    lines.append(f"- `{short_path}`")
                if len(self.summary.files_modified) > 10:
                    lines.append(f"- ... and {len(self.summary.files_modified) - 10} more")
                lines.append("")

            lines.append("---\n")

        # Decisions (questions)
        if self.summary.questions_asked:
            lines.append("## 🤔 Decisions Made\n")
            for q in self.summary.questions_asked:
                question = q["question"]
                lines.append(f"- {question}")
            lines.append("\n---\n")

        # Todos
        if self.summary.todos:
            lines.append("## ✅ Tasks Tracked\n")
            # Get final todo state
            final_todos = self.summary.todos[-1]["todos"]
            completed = [t for t in final_todos if t["status"] == "completed"]
            pending = [t for t in final_todos if t["status"] == "pending"]
            in_progress = [t for t in final_todos if t["status"] == "in_progress"]

            if completed:
                lines.append(f"**Completed ({len(completed)}):**\n")
                for t in completed:
                    lines.append(f"- ✅ {t['content']}")
                lines.append("")

            if in_progress:
                lines.append(f"**In Progress ({len(in_progress)}):**\n")
                for t in in_progress:
                    lines.append(f"- 🔄 {t['content']}")
                lines.append("")

            if pending:
                lines.append(f"**Pending ({len(pending)}):**\n")
                for t in pending:
                    lines.append(f"- ⏳ {t['content']}")
                lines.append("")

            lines.append("---\n")

        # Tool usage stats
        if self.summary.tool_calls:
            lines.append("## 🔧 Tools Used\n")
            sorted_tools = sorted(self.summary.tool_calls.items(), key=lambda x: x[1], reverse=True)
            for tool, count in sorted_tools[:10]:
                lines.append(f"- **{tool}:** {count} times")
            lines.append("\n---\n")

        # Errors (if any)
        if self.summary.errors:
            lines.append("## ⚠️ Errors Encountered\n")
            for err in self.summary.errors[:5]:  # Show first 5
                error_msg = err["error"]
                lines.append(f"- {error_msg}")
            if len(self.summary.errors) > 5:
                lines.append(f"- ... and {len(self.summary.errors) - 5} more errors")
            lines.append("\n---\n")

        # Footer
        lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("**Tool:** session_summarizer.py")

        return "\n".join(lines)

    def _calculate_duration(self) -> str:
        """Calculate session duration.

        Returns:
            Human-readable duration string
        """
        if not self.summary.start_time or not self.summary.end_time:
            return "?"

        delta = self.summary.end_time - self.summary.start_time
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h{minutes:02d}m"
        return f"{minutes}m"

    def _shorten_path(self, path: str) -> str:
        """Shorten file path for readability.

        Args:
            path: Full file path

        Returns:
            Shortened path
        """
        # Remove common prefixes
        path = path.replace("", "")
        path = path.replace("", "")
        return path


def summarize_session(jsonl_path: Path, output_path: Path | None = None) -> tuple[str, Path]:
    """Summarize a session JSONL file.

    Args:
        jsonl_path: Path to JSONL session file
        output_path: Optional output path for summary

    Returns:
        Tuple of (summary_text, output_path)
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Session file not found: {jsonl_path}")

    # Parse session
    parser = SessionParser(jsonl_path)
    summary = parser.parse_file()

    # Generate summary
    session_name = jsonl_path.stem
    generator = SummaryGenerator(summary, session_name)
    summary_text = generator.generate_markdown()

    # Determine output path
    if output_path is None:
        output_path = jsonl_path.parent / f"{session_name}_SUMMARY.md"

    # Write summary
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    return summary_text, output_path


def main():
    """Main entry point for session summarizer CLI."""
    parser = argparse.ArgumentParser(
        description="Generate automatic summary from Claude Code session JSONL"
    )
    parser.add_argument("input", type=Path, help="Input JSONL session file")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output markdown file (default: <session>_SUMMARY.md)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print summary to stdout instead of file",
    )

    args = parser.parse_args()

    try:
        summary_text, output_path = summarize_session(args.input, args.output)

        if args.stdout:
            print(summary_text)
        else:
            print(f"✅ Summary generated: {output_path}")
            print(f"📊 Size: {len(summary_text)} characters")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
