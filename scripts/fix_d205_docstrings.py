#!/usr/bin/env python3
"""Fix D205 docstring errors by adding blank lines."""
import re
import sys
from pathlib import Path


def fix_d205_in_file(file_path: Path) -> tuple[bool, int]:
    """Fix D205 errors in a single file.

    Args:
        file_path: Path to Python file to fix

    Returns:
        Tuple of (changed, count) where changed is True if file was modified
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    fixes_count = 0

    # Pattern for multi-line docstrings where first line (ending with period)
    # is immediately followed by another line without a blank line
    # """First line.
    # Second line
    # """
    # Should become:
    # """First line.
    #
    # Second line
    # """
    # Match: opening quotes, first line ending with period, newline, text (not closing quotes)
    pattern = r'(""")([^\n]+\.)(\n)([ \t]*)([^\n"]+)'

    def add_blank_line(match):
        nonlocal fixes_count
        # Check if the next line after period is not just whitespace or closing quotes
        next_line = match.group(5).strip()
        if next_line and not next_line.startswith('"""'):
            fixes_count += 1
            # Add blank line after the first line
            return f"{match.group(1)}{match.group(2)}{match.group(3)}{match.group(3)}{match.group(4)}{match.group(5)}"
        return match.group(0)

    content = re.sub(pattern, add_blank_line, content)

    changed = content != original_content
    if changed:
        file_path.write_text(content, encoding="utf-8")

    return changed, fixes_count


def main():
    """Run D205 fixer on cyclisme_training_logs directory."""
    base_dir = Path(__file__).parent.parent / "cyclisme_training_logs"

    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}")
        sys.exit(1)

    print(f"🔍 Scanning {base_dir}...")

    total_files = 0
    total_fixes = 0
    changed_files = []

    for py_file in base_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        changed, fixes = fix_d205_in_file(py_file)
        if changed:
            total_files += 1
            total_fixes += fixes
            changed_files.append((py_file.relative_to(base_dir.parent), fixes))
            print(f"  ✅ {py_file.relative_to(base_dir.parent)} ({fixes} fixes)")

    print("\n📊 Summary:")
    print(f"  Files modified: {total_files}")
    print(f"  Total fixes: {total_fixes}")

    if changed_files:
        print("\n📝 Modified files:")
        for file_path, count in changed_files:
            print(f"  - {file_path} ({count} fixes)")


if __name__ == "__main__":
    main()
