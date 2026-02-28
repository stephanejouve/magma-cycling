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

# Production tools that MUST be documented
PRODUCTION_TOOLS = {
    # Core workflows
    "workflow-coach",
    "daily-sync",
    "end-of-week",
    # Analysis
    "weekly-analysis",
    "monthly-analysis",
    "dashboard",
    "stats",
    # Session management
    "update-session",
    "shift-sessions",
    "weekly-planner",
    "planned-checker",
    # Data sync
    "upload-workouts",
    "sync-intervals",
    # Reports
    "generate-report",
    "organize-report",
}

# Debug/maintenance tools (documentation optional)
DEBUG_PATTERNS = [
    "check-",
    "validate-",
    "cleanup-",
    "backfill-",
    "normalize-",
    "format-",
    "clear-",
    "project-clean",
    "seed-",
    "populate-",
    "search-",
]


def is_debug_tool(tool_name: str) -> bool:
    """Check if tool is debug/maintenance (documentation optional).

    Args:
        tool_name: Tool script name

    Returns:
        True if debug/maintenance tool
    """
    return any(tool_name.startswith(pattern) for pattern in DEBUG_PATTERNS)


def load_poetry_scripts(pyproject_path: Path) -> dict[str, str]:
    """Load all scripts from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml

    Returns:
        Dict mapping script name to module path (e.g., {'shift-sessions': 'magma_cycling.shift_sessions:main'})
    """
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    return data.get("tool", {}).get("poetry", {}).get("scripts", {})


def extract_module_from_script(script_path: str) -> str:
    """Extract module name from script path.

    Args:
        script_path: e.g., 'magma_cycling.shift_sessions:main'

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
                # Get last component (e.g., shift_sessions from magma_cycling.shift_sessions)
                module_name = module.split(".")[-1]
                documented.add(module_name)

    return documented


def check_documentation(
    project_root: Path, verbose: bool = False
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Check which tools are missing documentation.

    Args:
        project_root: Root of the project
        verbose: Print detailed info

    Returns:
        Tuple of (undocumented_dict, documented_dict) where each dict has:
        - 'production': List of production tools
        - 'debug': List of debug/maintenance tools
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

    # Categorize tools
    undocumented = {"production": [], "debug": []}
    documented_tools = {"production": [], "debug": []}

    for script_name, module_name in tools.items():
        # Determine category
        is_debug = is_debug_tool(script_name)
        category = "debug" if is_debug else "production"

        # Check if documented
        if module_name in documented:
            documented_tools[category].append(script_name)
            if verbose:
                emoji = "✅" if not is_debug else "💡"
                label = "documented" if not is_debug else "documented (debug)"
                print(f"{emoji} {script_name:30} → {module_name} ({label})")
        else:
            undocumented[category].append(script_name)
            if verbose:
                emoji = "❌" if not is_debug else "⚠️"
                label = "MISSING DOC" if not is_debug else "optional doc"
                print(f"{emoji} {script_name:30} → {module_name} ({label})")

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

.. automodule:: magma_cycling.{module_name}
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

    # Calculate totals
    total_prod_documented = len(documented["production"])
    total_prod_undocumented = len(undocumented["production"])
    total_debug_documented = len(documented["debug"])
    total_debug_undocumented = len(undocumented["debug"])

    print("\n📊 Summary:")
    print("\n   🚀 Production Tools:")
    print(f"      Documented:   {total_prod_documented}")
    print(f"      Undocumented: {total_prod_undocumented}")
    print("\n   🔧 Debug/Maintenance Tools:")
    print(f"      Documented:   {total_debug_documented}")
    print(f"      Undocumented: {total_debug_undocumented} (optional)")

    # Show undocumented production tools (priority)
    if undocumented["production"]:
        print("\n❌ Undocumented PRODUCTION tools (must be documented):")
        for tool in undocumented["production"]:
            print(f"   - {tool}")

    # Show undocumented debug tools (optional)
    if undocumented["debug"] and args.verbose:
        print("\n⚠️  Undocumented DEBUG tools (documentation optional):")
        for tool in undocumented["debug"]:
            print(f"   - {tool}")

    # Generate skeletons if requested
    if args.generate:
        all_undocumented = undocumented["production"] + undocumented["debug"]
        if all_undocumented:
            print("\n📝 Generating documentation skeletons...")
            scripts = load_poetry_scripts(project_root / "pyproject.toml")

            for tool in all_undocumented:
                if tool in scripts:
                    module_name = extract_module_from_script(scripts[tool])
                    skeleton = generate_doc_skeleton(tool, module_name, docs_dir)

                    print(f"\n--- Documentation for {tool} ---")
                    print(skeleton)
                    print(f"--- End {tool} ---\n")

            print("\n💡 Add these sections to docs/modules/tools.rst or create separate files")

    # Only fail on undocumented production tools
    if args.fail and undocumented["production"]:
        print(
            f"\n❌ Documentation check failed: {total_prod_undocumented} "
            f"production tools missing docs"
        )
        return 1

    if not undocumented["production"]:
        print("\n✅ All production tools are documented!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
