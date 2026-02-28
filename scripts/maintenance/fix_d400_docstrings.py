#!/usr/bin/env python3
"""Fix D400 docstring errors by adding periods to first lines."""
import re
import sys
from pathlib import Path


def fix_d400_in_file(file_path: Path) -> tuple[bool, int]:
    """Fix D400 errors in a single file.

    Args:
        file_path: Path to Python file to fix

    Returns:
        Tuple of (changed, count) where changed is True if file was modified
    """
    content = file_path.read_text(encoding="utf-8")

    original_content = content
    fixes_count = 0

    # Pattern for docstrings - matches triple quotes with content
    # This matches: """Some text""" or '''Some text'''
    # where the first line doesn't end with period, !, or ?

    # Pattern 1: Single-line docstrings without period
    # """Text"""  -> """Text."""
    pattern1 = r'(""")([^"]+[^.!?"\s])(\s*""")'

    def replace_single_line(match):
        nonlocal fixes_count
        fixes_count += 1
        return f"{match.group(1)}{match.group(2)}.{match.group(3)}"

    content = re.sub(pattern1, replace_single_line, content)

    # Pattern 2: Multi-line docstrings where first line doesn't end with period
    # """Text
    # More text
    # """
    pattern2 = r'("""[ \t]*)([^\n]+[^.!?\s])([ \t]*\n)'

    def replace_multi_line(match):
        # Only fix if this looks like the start of a docstring (not code)
        first_line = match.group(2).strip()
        # Skip if first line is empty or starts with common code patterns
        if not first_line or first_line.startswith(
            ("Args:", "Returns:", "Raises:", "Example", "Note:")
        ):
            return match.group(0)
        nonlocal fixes_count
        fixes_count += 1
        return f"{match.group(1)}{match.group(2)}.{match.group(3)}"

    content = re.sub(pattern2, replace_multi_line, content)

    changed = content != original_content
    if changed:
        file_path.write_text(content, encoding="utf-8")

    return changed, fixes_count


def main():
    """Run D400 fixer on magma_cycling directory."""
    base_dir = Path(__file__).parent.parent / "magma_cycling"

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

        changed, fixes = fix_d400_in_file(py_file)
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
