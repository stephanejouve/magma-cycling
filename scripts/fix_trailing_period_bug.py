#!/usr/bin/env python3
"""Fix trailing period bug from D400 fixer."""

import re
from pathlib import Path


def fix_trailing_periods(file_path: Path) -> bool:
    """Remove periods that were incorrectly added after closing triple quotes.

    Args:
        file_path: Path to Python file to fix

    Returns:
        True if file was modified
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # Pattern 1: """. at end of line (period after closing quotes)
    # This is invalid syntax and should be """  (period inside quotes)
    content = re.sub(r'"""\.\s*$', '"""', content, flags=re.MULTILINE)

    # Pattern 2: :. at end of function/method definitions
    # def foo() -> str:. should be def foo() -> str:
    content = re.sub(r":\.\s*$", ":", content, flags=re.MULTILINE)

    # Pattern 3: f.""" or f.''' should be f""" or f'''
    # f-strings with period before quotes
    content = re.sub(r'f\.\"""', 'f"""', content)
    content = re.sub(r"f\.'", "f'", content)

    # Pattern 4: +=. """ or -=. """ should be += """ or -= """
    # Assignment operators with period and optional space before quotes
    content = re.sub(r'([+\-*/]|//|%|&|\||\^|<<|>>)?=\.\s+\"""', r'\1= """', content)
    content = re.sub(r"([+\-*/]|//|%|&|\||\^|<<|>>)?=\.\s+'", r"\1= '", content)

    changed = content != original_content
    if changed:
        file_path.write_text(content, encoding="utf-8")

    return changed


def main():
    """Fix all files in cyclisme_training_logs."""
    base_dir = Path(__file__).parent.parent / "cyclisme_training_logs"

    print(f"🔍 Fixing trailing period bug in {base_dir}...")

    fixed_count = 0
    for py_file in base_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        if fix_trailing_periods(py_file):
            fixed_count += 1
            print(f"  ✅ {py_file.relative_to(base_dir.parent)}")

    print(f"\n📊 Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
