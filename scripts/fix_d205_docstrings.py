#!/usr/bin/env python3
"""Fix D205 docstring errors by adding blank lines."""
import re
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

    # Pattern 1: """First line.\nSecond line
    pattern1 = r'(""")([^\n]+\.)(\n)([ \t]*)([^\n"]+)'

    def add_blank_line1(match):
        nonlocal fixes_count
        next_line = match.group(5).strip()
        if next_line and not next_line.startswith('"""'):
            fixes_count += 1
            return f"{match.group(1)}{match.group(2)}{match.group(3)}{match.group(3)}{match.group(4)}{match.group(5)}"
        return match.group(0)

    content = re.sub(pattern1, add_blank_line1, content)

    # Pattern 2: """\nFirst line\nSecond line (for module docstrings)
    # Match: opening quotes, newline, first line (with or without period), newline, text (not closing quotes)
    # This pattern handles summaries that may not end with a period
    pattern2 = r'(""")\n([ \t]*)([^\n]+)\n([ \t]*)([^\n"]+)'

    def add_blank_line2(match):
        nonlocal fixes_count
        first_line = match.group(3).strip()
        next_line = match.group(5).strip()
        # Check if next line is not empty and not closing quotes
        # Also check that first line looks like a summary (not too long, typically < 100 chars)
        if next_line and not next_line.startswith('"""') and len(first_line) < 100:
            fixes_count += 1
            # Add blank line after the first line
            return f"{match.group(1)}\n{match.group(2)}{match.group(3)}\n\n{match.group(4)}{match.group(5)}"
        return match.group(0)

    content = re.sub(pattern2, add_blank_line2, content)

    changed = content != original_content
    if changed:
        file_path.write_text(content, encoding="utf-8")

    return changed, fixes_count


def main():
    """Run D205 fixer on all Python directories."""
    root_dir = Path(__file__).parent.parent

    directories = ["cyclisme_training_logs", "tests", "scripts"]

    total_files = 0
    total_fixes = 0
    changed_files = []

    for dir_name in directories:
        base_dir = root_dir / dir_name
        if not base_dir.exists():
            continue

        print(f"🔍 Scanning {dir_name}...")

        for py_file in base_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            changed, fixes = fix_d205_in_file(py_file)
            if changed:
                total_files += 1
                total_fixes += fixes
                changed_files.append((py_file.relative_to(root_dir), fixes))
                print(f"  ✅ {py_file.relative_to(root_dir)} ({fixes} fixes)")

    print("\n📊 Summary:")
    print(f"  Files modified: {total_files}")
    print(f"  Total fixes: {total_fixes}")

    if changed_files:
        print("\n📝 Modified files:")
        for file_path, count in changed_files:
            print(f"  - {file_path} ({count} fixes)")


if __name__ == "__main__":
    main()
