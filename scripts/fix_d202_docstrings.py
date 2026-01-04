#!/usr/bin/env python3
"""
Fix D202 docstring errors - remove blank lines after function docstrings.

Removes blank lines that appear immediately after a function/method/class docstring.
D202: No blank lines allowed after function docstring (found 1)

Examples:
    Before::

        def foo():
            \"\"\"Docstring.\"\"\"

            return 42

    After::

        def foo():
            \"\"\"Docstring.\"\"\"
            return 42

Usage:
    python scripts/fix_d202_docstrings.py
"""
from pathlib import Path


def fix_d202_blank_lines(content: str) -> tuple[str, int]:
    """
    Remove blank lines after docstrings.

    Args:
        content: File content as string

    Returns:
        Tuple of (fixed_content, number_of_fixes)
    """
    lines = content.split("\n")
    fixes = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this line ends with a docstring closer
        if stripped.endswith('"""') or stripped.endswith("'''"):
            # Check if next line(s) are blank
            blank_count = 0
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                blank_count += 1
                j += 1

            # If we found blank lines after docstring, remove them
            if blank_count > 0 and j < len(lines):
                # Keep only the docstring line and the next non-blank line
                lines = lines[: i + 1] + lines[j:]
                fixes += 1

        i += 1

    return "\n".join(lines), fixes


def main():
    """Command-line entry point for fixing D202 docstring errors."""
    # Find all Python files
    python_files = []
    for directory in ["cyclisme_training_logs", "tests", "scripts"]:
        path = Path(directory)
        if path.exists():
            python_files.extend(path.rglob("*.py"))

    total_fixes = 0
    files_modified = 0

    print("=" * 70)
    print("FIX D202 - BLANK LINES AFTER DOCSTRING")
    print("=" * 70)
    print()

    for file_path in sorted(python_files):
        try:
            content = file_path.read_text(encoding="utf-8")
            fixed_content, fixes = fix_d202_blank_lines(content)

            if fixes > 0:
                file_path.write_text(fixed_content, encoding="utf-8")
                total_fixes += fixes
                files_modified += 1
                print(f"✓ {file_path}: {fixes} fix(es)")
        except Exception as e:
            print(f"✗ {file_path}: ERROR - {e}")

    print()
    print("=" * 70)
    print(f"TOTAL: {total_fixes} fixes in {files_modified} files")
    print("=" * 70)


if __name__ == "__main__":
    main()
