#!/usr/bin/env python3
"""Reorganize project documentation structure.

This script reorganizes project-docs/ and docs/ to follow clean architecture:
- Consolidate archive/ and archives/ into archives/
- Move loose .md files to appropriate subdirectories
- Clean up docs/ (Sphinx only)
- Create releases/ directory for binary archives

Usage:
    poetry run python scripts/maintenance/reorganize_docs.py --dry-run
    poetry run python scripts/maintenance/reorganize_docs.py --execute
"""

import argparse
import shutil
import sys
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class DocsReorganizer:
    """Reorganize project documentation structure."""

    def __init__(self, project_root: Path):
        """Initialize reorganizer.

        Args:
            project_root: Path to project root directory.
        """
        self.project_root = project_root
        self.project_docs = project_root / "project-docs"
        self.docs = project_root / "docs"

        # Define target structure
        self.moves = [
            # Root coverage.json
            ("coverage.json", "project-docs/archives/coverage.json"),
            # project-docs/ loose files
            ("project-docs/ARCHITECTURE.md", "project-docs/architecture/ARCHITECTURE.md"),
            (
                "project-docs/ARCHITECTURE_REVIEW_20260104.md",
                "project-docs/archives/ARCHITECTURE_REVIEW_20260104.md",
            ),
            (
                "project-docs/QUICK_REFERENCE_QUALITY.md",
                "project-docs/guides/QUICK_REFERENCE_QUALITY.md",
            ),
            (
                "project-docs/REFACTORING_OPPORTUNITIES.md",
                "project-docs/archives/REFACTORING_OPPORTUNITIES.md",
            ),
            (
                "project-docs/REVIEW_WARNINGS_EXPLAINED.md",
                "project-docs/guides/REVIEW_WARNINGS_EXPLAINED.md",
            ),
            (
                "project-docs/SESSION_SUMMARY_2026-01-03.md",
                "project-docs/sessions/SESSION_SUMMARY_2026-01-03.md",
            ),
            ("project-docs/SPRINT_NAMING.md", "project-docs/guides/SPRINT_NAMING.md"),
            (
                "project-docs/SPRINT_R4_R5_RECAP.md",
                "project-docs/sprints/SPRINT_R4_R5_RECAP.md",
            ),
            # docs/ loose files
            (
                "docs/ARCHITECTURE_EVOLUTION.md",
                "project-docs/architecture/ARCHITECTURE_EVOLUTION.md",
            ),
            (
                "docs/SPRINT_R8_PHASE3_SUMMARY.md",
                "project-docs/sprints/SPRINT_R8_PHASE3_SUMMARY.md",
            ),
            (
                "docs/TESTS_COVERAGE_REPORT.md",
                "project-docs/archives/TESTS_COVERAGE_REPORT.md",
            ),
            # Consolidate ROADMAP.md from archives/ to root level (important doc)
            ("project-docs/archives/ROADMAP.md", "project-docs/ROADMAP.md"),
        ]

    def print_header(self, text: str) -> None:
        """Print formatted header."""
        print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
        print(f"{BOLD}{BLUE}{text:^70}{RESET}")
        print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

    def print_move(self, src: str, dest: str) -> None:
        """Print move operation."""
        print(f"  {BLUE}→{RESET} {src}")
        print(f"    {GREEN}↳{RESET} {dest}")

    def print_success(self, text: str) -> None:
        """Print success message."""
        print(f"{GREEN}✅ {text}{RESET}")

    def print_warning(self, text: str) -> None:
        """Print warning message."""
        print(f"{YELLOW}⚠️  {text}{RESET}")

    def print_error(self, text: str) -> None:
        """Print error message."""
        print(f"{RED}❌ {text}{RESET}")

    def consolidate_archives(self, dry_run: bool = True) -> int:
        """Consolidate archive/ into archives/.

        Args:
            dry_run: If True, only show what would be done.

        Returns:
            Number of files moved.
        """
        old_archive = self.project_docs / "archive"
        new_archive = self.project_docs / "archives"

        if not old_archive.exists():
            return 0

        moved_count = 0
        print(f"\n{BOLD}Consolidating archive/ → archives/{RESET}")

        for item in old_archive.rglob("*"):
            if item.is_file():
                # Compute relative path
                rel_path = item.relative_to(old_archive)
                dest = new_archive / rel_path

                self.print_move(
                    str(item.relative_to(self.project_root)),
                    str(dest.relative_to(self.project_root)),
                )

                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(dest))

                moved_count += 1

        if not dry_run and moved_count > 0:
            # Remove empty old archive directory
            try:
                shutil.rmtree(old_archive)
                self.print_success("Removed empty archive/ directory")
            except Exception as e:
                self.print_warning(f"Could not remove archive/: {e}")

        return moved_count

    def create_releases_dir(self, dry_run: bool = True) -> bool:
        """Create releases/ directory for binary archives.

        Args:
            dry_run: If True, only show what would be done.

        Returns:
            True if directory created/exists.
        """
        releases_dir = self.project_root / "releases"

        if releases_dir.exists():
            self.print_success("releases/ directory already exists")
            return True

        print(f"\n{BOLD}Creating releases/ directory{RESET}")
        print(f"  {BLUE}→{RESET} releases/ (for .tar.gz, .zip, .sha256 files)")

        if not dry_run:
            releases_dir.mkdir(parents=True, exist_ok=True)
            # Create .gitignore to ignore binary files
            gitignore = releases_dir / ".gitignore"
            gitignore.write_text("*.tar.gz\n*.zip\n*.sha256\n")
            self.print_success("Created releases/ with .gitignore")

        return True

    def move_files(self, dry_run: bool = True) -> int:
        """Move files according to target structure.

        Args:
            dry_run: If True, only show what would be done.

        Returns:
            Number of files moved.
        """
        moved_count = 0

        print(f"\n{BOLD}Moving files to target structure{RESET}")

        for src_rel, dest_rel in self.moves:
            src = self.project_root / src_rel
            dest = self.project_root / dest_rel

            if not src.exists():
                self.print_warning(f"Source not found: {src_rel}")
                continue

            self.print_move(src_rel, dest_rel)

            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))

            moved_count += 1

        return moved_count

    def create_index_readme(self, dry_run: bool = True) -> None:
        """Create/update project-docs/README.md index.

        Args:
            dry_run: If True, only show what would be done.
        """
        readme_path = self.project_docs / "README.md"

        content = """# Project Documentation

This directory contains all project documentation organized by category.

## 📁 Directory Structure

- **architecture/** - System design documents and architecture decisions
- **archives/** - Historical documents, old reports, deprecated content
- **audits/** - Code quality audits and analysis reports
- **guides/** - Developer guides and reference documentation
- **logs/** - Session logs and transcripts
- **prompts/** - AI prompts and templates
- **sessions/** - Session summaries and work logs
- **sprints/** - Sprint planning, progress, and summaries
- **workflows/** - Workflow documentation and procedures

## 📋 Key Documents

- **CHANGELOG.md** - Project changelog with all version history
- **ROADMAP.md** - Product roadmap and future sprint planning

## 🗂️ Related Directories

- **docs/** - Sphinx documentation (API reference)
- **releases/** - Binary archives and release packages

---

*Last updated: 2026-01-17*
"""

        print(f"\n{BOLD}Creating/updating project-docs/README.md{RESET}")

        if not dry_run:
            readme_path.write_text(content)
            self.print_success("Created project-docs/README.md index")
        else:
            print(f"  {BLUE}→{RESET} Would create/update project-docs/README.md")

    def run(self, dry_run: bool = True) -> dict:
        """Run full reorganization.

        Args:
            dry_run: If True, only show what would be done.

        Returns:
            Dictionary with reorganization results.
        """
        results = {
            "archives_consolidated": 0,
            "files_moved": 0,
            "releases_created": False,
        }

        self.print_header("📚 Documentation Reorganization Bot")

        if dry_run:
            print(f"{YELLOW}{BOLD}DRY RUN MODE - No changes will be made{RESET}\n")

        # 1. Consolidate archive/ → archives/
        results["archives_consolidated"] = self.consolidate_archives(dry_run)

        # 2. Create releases/ directory
        results["releases_created"] = self.create_releases_dir(dry_run)

        # 3. Move files to target structure
        results["files_moved"] = self.move_files(dry_run)

        # 4. Create README index
        self.create_index_readme(dry_run)

        # Summary
        print(f"\n{BOLD}Summary:{RESET}")
        print(f"  Archive files consolidated: {results['archives_consolidated']}")
        print(f"  Files moved: {results['files_moved']}")
        print(
            f"  Releases directory: {'✅ Created' if results['releases_created'] else '⚠️  Skipped'}"
        )

        if dry_run:
            print(f"\n{YELLOW}Run with --execute to apply these changes{RESET}")
        else:
            print(f"\n{GREEN}{BOLD}✅ Reorganization complete!{RESET}")
            print(f"{YELLOW}Don't forget to run: git add -A && git commit{RESET}")

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reorganize project documentation structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    group.add_argument("--execute", action="store_true", help="Execute the reorganization")

    args = parser.parse_args()

    # Initialize reorganizer
    project_root = Path(__file__).parent.parent.parent
    reorganizer = DocsReorganizer(project_root)

    try:
        results = reorganizer.run(dry_run=args.dry_run)

        if args.execute and (results["archives_consolidated"] > 0 or results["files_moved"] > 0):
            sys.exit(0)
        elif args.dry_run:
            sys.exit(0)

    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
