#!/usr/bin/env python3
"""Safe D400 fixer using AST parsing to avoid breaking code."""
import ast
import sys
from pathlib import Path


def get_first_line(docstring: str) -> str:
    """Get the first non-empty line of a docstring."""
    lines = docstring.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def needs_period(first_line: str) -> bool:
    """Check if first line needs a period."""
    if not first_line:
        return False

    # Already ends with punctuation
    if first_line.endswith((".", "!", "?")):
        return False

    # Skip if it's just opening quotes (shouldn't happen after strip)
    if first_line in ['"""', "'''"]:
        return False

    return True


def fix_docstring_in_content(content: str, lineno: int) -> str:
    """Fix a docstring at a specific line number."""
    lines = content.split("\n")

    # Find the docstring (lineno is 1-based)
    idx = lineno - 1

    if idx >= len(lines):
        return content

    line = lines[idx]

    # Check if this line contains opening quotes
    if '"""' in line:
        quote = '"""'
    elif "'''" in line:
        quote = "'''"
    else:
        return content

    # Find where the quote starts
    quote_start = line.find(quote)

    # Check if it's a one-line docstring
    quote_end = line.find(quote, quote_start + 3)

    if quote_end != -1:
        # One-line docstring: """text"""
        before_quotes = line[: quote_start + 3]
        docstring_text = line[quote_start + 3 : quote_end]
        after_quotes = line[quote_end:]

        if docstring_text and not docstring_text.rstrip().endswith((".", "!", "?")):
            docstring_text = docstring_text.rstrip() + "."
            lines[idx] = before_quotes + docstring_text + after_quotes
            return "\n".join(lines)
    else:
        # Multi-line docstring - find the first content line
        # The first line might be empty: """
        if line.strip() == quote:
            # Look at next line for content
            if idx + 1 < len(lines):
                next_line = lines[idx + 1]
                stripped_next = next_line.rstrip()

                # Check if this is the first content line (not blank, not closing quotes)
                if stripped_next and not stripped_next.strip().startswith(quote):
                    if not stripped_next.rstrip().endswith((".", "!", "?")):
                        lines[idx + 1] = stripped_next + "."
                        return "\n".join(lines)
        else:
            # First line has content: """Some text
            content_start = quote_start + 3
            first_line_content = line[content_start:].rstrip()

            if first_line_content and not first_line_content.endswith((".", "!", "?")):
                before = line[:content_start]
                lines[idx] = before + first_line_content + "."
                return "\n".join(lines)

    return content


def fix_file(file_path: Path) -> int:
    """Fix D400 errors in a single file using AST."""
    try:
        content = file_path.read_text(encoding="utf-8")

        # Parse AST to find docstrings
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return 0

        # Collect all docstring locations that need fixing
        fixes_needed = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.ClassDef | ast.Module):
                docstring = ast.get_docstring(node)

                if docstring:
                    first_line = get_first_line(docstring)

                    if needs_period(first_line):
                        # Get the line number where this docstring starts
                        if isinstance(node, ast.Module):
                            # Module docstring is at the beginning
                            lineno = 1
                            # Find first """ or '''
                            for i, line in enumerate(content.split("\n"), 1):
                                if '"""' in line or "'''" in line:
                                    lineno = i
                                    break
                        else:
                            # Function/class docstring is after the def/class line
                            lineno = node.lineno + 1
                            # But might have decorators, so find the actual docstring line
                            lines = content.split("\n")
                            for i in range(node.lineno, min(node.lineno + 5, len(lines))):
                                if '"""' in lines[i] or "'''" in lines[i]:
                                    lineno = i + 1  # Convert to 1-based
                                    break

                        fixes_needed.append(lineno)

        # Apply fixes in reverse order to maintain line numbers
        if fixes_needed:
            for lineno in sorted(set(fixes_needed), reverse=True):
                content = fix_docstring_in_content(content, lineno)

            file_path.write_text(content, encoding="utf-8")
            return len(fixes_needed)

        return 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0


def main():
    """Fix D400 errors in all Python files safely."""
    project_root = Path(__file__).parent.parent

    # Directories to process
    dirs = [
        project_root / "magma_cycling",
        project_root / "tests",
        project_root / "scripts",
    ]

    total_fixes = 0
    files_modified = 0

    for directory in dirs:
        if not directory.exists():
            continue

        for py_file in directory.rglob("*.py"):
            # Skip excluded patterns
            if any(p in py_file.parts for p in ["__pycache__", ".venv", "venv", ".pytest_cache"]):
                continue

            fixes = fix_file(py_file)
            if fixes > 0:
                total_fixes += fixes
                files_modified += 1
                print(f"✓ {py_file.relative_to(project_root)}: {fixes} fix(es)")

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total_fixes} fixes in {files_modified} files")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
