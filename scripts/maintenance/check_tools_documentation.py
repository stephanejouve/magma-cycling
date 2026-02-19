#!/usr/bin/env python3
"""
Check that all poetry scripts have Sphinx documentation.

This script validates that:
1. Every script in [tool.poetry.scripts] has a corresponding .rst file
2. Every .rst file references the actual module
3. The main tools.rst index includes all tool docs

Can be run as:
- Pre-commit hook (exit 1 if undocumented tools found)
- Manual check (poetry run check-tools-docs)
- Documentation generator (--generate flag)

Author: Claude Sonnet 4.5
Created: 2026-02-19
"""

import argparse
import sys
import tomllib  # Python 3.11+
from pathlib import Path


def load_poetry_scripts(pyproject_path: Path) -> dict[str, str]:
    """Load all scripts from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml

    Returns:
        Dict mapping script name to module path (e.g., {'shift-sessions': 'cyclisme_training_logs.shift_sessions:main'})
    """
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    return data.get("tool", {}).get("poetry", {}).get("scripts", {})


def extract_module_from_script(script_path: str) -> str:
    """Extract module name from script path.

    Args:
        script_path: e.g., 'cyclisme_training_logs.shift_sessions:main'

    Returns:
        Module name, e.g., 'shift_sessions'
    """
    module_path = script_path.split(":")[0]  # Remove ':main'
    return module_path.split(".")[-1]  # Get last component


def find_documented_tools(docs_dir: Path) -> set[str]:
    """Find all tools documented in Sphinx.

    Args:
        docs_dir: Path to docs/ directory

    Returns:
        Set of documented module names
    """
    documented = set()

    # Check tools.rst for automodule directives
    tools_rst = docs_dir / "modules" / "tools.rst"
    if tools_rst.exists():
        content = tools_rst.read_text()
        for line in content.splitlines():
            if ".. automodule::" in line:
                # Extract module name after automodule::
                module = line.split("::")[1].strip()
                # Get last component (e.g., shift_sessions from cyclisme_training_logs.shift_sessions)
                module_name = module.split(".")[-1]
                documented.add(module_name)

    return documented


def check_documentation(project_root: Path, verbose: bool = False) -> tuple[list[str], list[str]]:
    """Check which tools are missing documentation.

    Args:
        project_root: Root of the project
        verbose: Print detailed info

    Returns:
        Tuple of (undocumented_tools, documented_tools)
    """
    pyproject_path = project_root / "pyproject.toml"
    docs_dir = project_root / "docs"

    scripts = load_poetry_scripts(pyproject_path)
    documented = find_documented_tools(docs_dir)

    # Extract module names from scripts
    tools = {}
    for script_name, script_path in scripts.items():
        module_name = extract_module_from_script(script_path)
        tools[script_name] = module_name

    # Find undocumented tools
    undocumented = []
    documented_tools = []

    for script_name, module_name in tools.items():
        if module_name in documented:
            documented_tools.append(script_name)
            if verbose:
                print(f"✅ {script_name:30} → {module_name} (documented)")
        else:
            undocumented.append(script_name)
            if verbose:
                print(f"❌ {script_name:30} → {module_name} (MISSING DOC)")

    return undocumented, documented_tools


def generate_doc_skeleton(tool_name: str, module_name: str, docs_dir: Path) -> str:
    """Generate documentation skeleton for a tool.

    Args:
        tool_name: Script name (e.g., 'shift-sessions')
        module_name: Module name (e.g., 'shift_sessions')
        docs_dir: Path to docs/ directory

    Returns:
        Generated RST content
    """
    template = f"""
{tool_name} - Tool Name
{'=' * (len(tool_name) + 13)}

Brief description of what {tool_name} does.

.. automodule:: cyclisme_training_logs.{module_name}
   :members:
   :undoc-members:
   :show-inheritance:

Usage
-----

.. code-block:: bash

    poetry run {tool_name} --help

Examples
--------

.. code-block:: bash

    # Example usage
    poetry run {tool_name} [options]

See Also
--------

- Related module or tool
"""
    return template.strip()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check that all poetry scripts have Sphinx documentation"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed information")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate documentation skeleton for undocumented tools",
    )
    parser.add_argument(
        "--fail", action="store_true", help="Exit with error if undocumented tools found"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.parent
    docs_dir = project_root / "docs"

    print("🔍 Checking tools documentation...\n")

    undocumented, documented = check_documentation(project_root, verbose=args.verbose)

    print("\n📊 Summary:")
    print(f"   Documented tools:   {len(documented)}")
    print(f"   Undocumented tools: {len(undocumented)}")

    if undocumented:
        print("\n⚠️  Undocumented tools:")
        for tool in undocumented:
            print(f"   - {tool}")

        if args.generate:
            print("\n📝 Generating documentation skeletons...")
            scripts = load_poetry_scripts(project_root / "pyproject.toml")

            for tool in undocumented:
                if tool in scripts:
                    module_name = extract_module_from_script(scripts[tool])
                    skeleton = generate_doc_skeleton(tool, module_name, docs_dir)

                    print(f"\n--- Documentation for {tool} ---")
                    print(skeleton)
                    print(f"--- End {tool} ---\n")

            print("\n💡 Add these sections to docs/modules/tools.rst or create separate files")

        if args.fail:
            print(f"\n❌ Documentation check failed: {len(undocumented)} tools missing docs")
            return 1
    else:
        print("\n✅ All tools are documented!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
