#!/usr/bin/env python3
"""Project cleanup and archiving automation bot.

This script maintains project structure cleanliness by:
- Removing temporary files and caches
- Identifying misplaced files at root
- Creating archives outside project
- Enforcing organization standards

Usage:
    poetry run project-clean          # Quick cleanup
    poetry run project-clean --deep   # Deep cleanup with report
    poetry run project-clean --archive # Create deliverable archive

Examples:
    Quick cleanup::

        poetry run project-clean

    Full cleanup with detailed report::

        poetry run project-clean --deep

    Create deliverable archive::

        poetry run project-clean --archive --sprint "R22"
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

# ANSI colors for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class ProjectCleaner:
    """Automated project cleanup and archiving bot."""

    def __init__(self, project_root: Path):
        """Initialize the cleaner.

        Args:
            project_root: Path to project root directory.
        """
        self.project_root = project_root

        # Files that MUST be at root (whitelist)
        self.allowed_root_files = {
            "README.md",
            "CODING_STANDARDS.md",
            "pyproject.toml",
            "poetry.lock",
            ".gitignore",
            ".pre-commit-config.yaml",
            ".pycodestyle",
            ".env",
            ".env.example",
            ".workflow_state.json",
            ".workflow_state.json.backup",
            ".coverage",
        }

        # Directories that MUST exist at root
        self.required_directories = {
            "cyclisme_training_logs",
            "tests",
            "docs",
            "scripts",
            "project-docs",
            "data",
            "logs",
        }

        # Patterns for temporary files to clean
        self.temp_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/.DS_Store",
            "**/*.swp",
            "**/*.swo",
            "**/*~",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            "htmlcov",
        ]

        # Patterns to exclude from archives
        self.archive_excludes = [
            ".git",
            "__pycache__",
            ".venv",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            "htmlcov",
            "docs/_build",
            "*.pyc",
            ".DS_Store",
            ".coverage",
        ]

    def print_header(self, text: str) -> None:
        """Print formatted header.

        Args:
            text: Header text to print.
        """
        print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
        print(f"{BOLD}{BLUE}{text:^70}{RESET}")
        print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

    def print_success(self, text: str) -> None:
        """Print success message.

        Args:
            text: Success message to print.
        """
        print(f"{GREEN}✅ {text}{RESET}")

    def print_warning(self, text: str) -> None:
        """Print warning message.

        Args:
            text: Warning message to print.
        """
        print(f"{YELLOW}⚠️  {text}{RESET}")

    def print_error(self, text: str) -> None:
        """Print error message.

        Args:
            text: Error message to print.
        """
        print(f"{RED}❌ {text}{RESET}")

    def print_info(self, text: str) -> None:
        """Print info message.

        Args:
            text: Info message to print.
        """
        print(f"{BLUE}ℹ️  {text}{RESET}")

    def clean_temp_files(self, dry_run: bool = False) -> tuple[int, list[Path]]:
        """Remove temporary files and caches.

        Args:
            dry_run: If True, only report what would be deleted.

        Returns:
            Tuple of (count of items removed, list of removed paths).
        """
        removed = []

        for pattern in self.temp_patterns:
            for path in self.project_root.glob(pattern):
                if path.exists():
                    try:
                        if not dry_run:
                            if path.is_dir():
                                shutil.rmtree(path)
                            else:
                                path.unlink()
                        removed.append(path)
                    except Exception as e:
                        self.print_warning(f"Could not remove {path}: {e}")

        return len(removed), removed

    def check_root_files(self) -> list[Path]:
        """Check for files at root that shouldn't be there.

        Returns:
            List of misplaced files at root.
        """
        misplaced = []

        for item in self.project_root.iterdir():
            # Skip hidden files/directories (except whitelisted ones)
            if item.name.startswith(".") and item.name not in self.allowed_root_files:
                continue

            # Skip directories
            if item.is_dir():
                continue

            # Check if file is allowed at root
            if item.name not in self.allowed_root_files:
                misplaced.append(item)

        return misplaced

    def suggest_organization(self, misplaced: list[Path]) -> dict:
        """Suggest where misplaced files should go.

        Args:
            misplaced: List of misplaced files.

        Returns:
            Dictionary mapping file paths to suggested destinations.
        """
        suggestions = {}

        for file_path in misplaced:
            name = file_path.name.lower()

            # Suggest destination based on file pattern
            if name.endswith((".tar.gz", ".zip", ".tar", ".sha256")):
                suggestions[file_path] = "releases/"
            elif "moa" in name or "livraison" in name or "sprint" in name:
                suggestions[file_path] = "project-docs/archives/"
            elif name.endswith(".py") and ("fix_" in name or "test_" in name):
                if "fix_" in name:
                    suggestions[file_path] = "scripts/maintenance/"
                else:
                    suggestions[file_path] = "scripts/debug/"
            elif name.endswith((".txt", ".md")) and name not in self.allowed_root_files:
                suggestions[file_path] = "project-docs/archives/"
            else:
                suggestions[file_path] = "project-docs/archives/"

        return suggestions

    def create_archive(
        self, sprint_name: str, output_dir: Path, dry_run: bool = False
    ) -> tuple[Path | None, str | None]:
        """Create project archive in releases/ and copy to iCloud.

        Args:
            sprint_name: Sprint identifier (e.g., "R22").
            output_dir: Directory to save archive (releases/).
            dry_run: If True, only show what would be done.

        Returns:
            Tuple of (archive path, SHA256 checksum) or (None, None) if dry_run.
        """
        # Archive filename with date
        date_str = datetime.now().strftime("%Y%m%d")
        archive_name = f"sprint-{sprint_name.lower()}-v2.2.0-{date_str}.tar.gz"

        if dry_run:
            self.print_info(f"Would create archive: {output_dir}/{archive_name}")
            self.print_info(
                f"Would copy to: ~/Documents/cyclisme-training-logs-archives/{archive_name}"
            )
            return None, None

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        archive_path = output_dir / archive_name

        # Create tar.gz archive
        self.print_info(f"Creating archive: {archive_path}")

        with tarfile.open(archive_path, "w:gz") as tar:
            for item in self.project_root.iterdir():
                # Check if should be excluded
                should_exclude = False
                for exclude in self.archive_excludes:
                    if exclude in str(item):
                        should_exclude = True
                        break

                if not should_exclude:
                    tar.add(item, arcname=item.name, recursive=True)

        # Calculate SHA256 checksum
        sha256_hash = hashlib.sha256()
        with open(archive_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        checksum = sha256_hash.hexdigest()

        # Save checksum file
        checksum_path = output_dir / f"{archive_name}.sha256"
        with open(checksum_path, "w") as f:
            f.write(f"{checksum}  {archive_name}\n")

        # Copy to iCloud Documents for easy sharing from iPhone
        icloud_dir = Path.home() / "Documents" / "cyclisme-training-logs-archives"
        icloud_dir.mkdir(parents=True, exist_ok=True)

        icloud_archive_path = icloud_dir / archive_name
        icloud_checksum_path = icloud_dir / f"{archive_name}.sha256"

        self.print_info(f"Copying to iCloud: {icloud_archive_path}")
        shutil.copy2(archive_path, icloud_archive_path)
        shutil.copy2(checksum_path, icloud_checksum_path)

        return archive_path, checksum

    def get_project_stats(self) -> dict:
        """Get current project statistics.

        Returns:
            Dictionary with project statistics.
        """
        stats = {
            "python_files": 0,
            "test_files": 0,
            "lines_of_code": 0,
            "docstring_coverage": 0,
        }

        # Count Python files
        for py_file in self.project_root.glob("cyclisme_training_logs/**/*.py"):
            stats["python_files"] += 1
            try:
                stats["lines_of_code"] += len(py_file.read_text().splitlines())
            except Exception:
                pass

        # Count test files
        stats["test_files"] = len(list(self.project_root.glob("tests/**/*.py")))

        return stats

    def run_cleanup(self, deep: bool = False, dry_run: bool = False) -> dict:
        """Run cleanup process.

        Args:
            deep: If True, perform deep cleanup with full report.
            dry_run: If True, only report what would be done.

        Returns:
            Dictionary with cleanup results.
        """
        results = {
            "temp_cleaned": 0,
            "misplaced_found": 0,
            "suggestions": {},
        }

        self.print_header("🧹 Project Cleanup Bot")

        # 1. Clean temporary files
        self.print_info("Cleaning temporary files...")
        count, removed = self.clean_temp_files(dry_run=dry_run)
        results["temp_cleaned"] = count

        if count > 0:
            self.print_success(f"Cleaned {count} temporary files/directories")
            if deep:
                for path in removed[:5]:  # Show first 5
                    print(f"  - {path.relative_to(self.project_root)}")
                if len(removed) > 5:
                    print(f"  ... and {len(removed) - 5} more")
        else:
            self.print_success("No temporary files to clean")

        # 2. Check root directory
        self.print_info("Checking root directory organization...")
        misplaced = self.check_root_files()
        results["misplaced_found"] = len(misplaced)

        if misplaced:
            self.print_warning(f"Found {len(misplaced)} misplaced files at root:")
            suggestions = self.suggest_organization(misplaced)
            results["suggestions"] = suggestions

            for file_path, destination in suggestions.items():
                print(f"  {YELLOW}→{RESET} {file_path.name} → {destination}")

            print(f"\n{YELLOW}Run 'git mv <file> <destination>' to organize these files{RESET}")
        else:
            self.print_success("Root directory is clean and organized")

        # 3. Project statistics (if deep)
        if deep:
            self.print_info("Gathering project statistics...")
            stats = self.get_project_stats()
            print(f"\n{BOLD}Project Statistics:{RESET}")
            print(f"  Python files: {stats['python_files']}")
            print(f"  Test files: {stats['test_files']}")
            print(f"  Lines of code: {stats['lines_of_code']:,}")

        # 4. Verify standards
        self.print_info("Verifying code standards...")
        try:
            # Check if pre-commit hooks pass
            result = subprocess.run(
                ["pre-commit", "run", "--all-files"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self.print_success("All pre-commit hooks pass")
            else:
                self.print_warning("Some pre-commit hooks need attention")
        except Exception:
            self.print_warning("Could not run pre-commit hooks")

        return results

    def run_archive(self, sprint_name: str, dry_run: bool = False) -> dict:
        """Run archiving process.

        Args:
            sprint_name: Sprint identifier.
            dry_run: If True, only report what would be done.

        Returns:
            Dictionary with archive results.
        """
        results = {
            "archive_created": False,
            "archive_path": None,
            "icloud_path": None,
            "checksum": None,
        }

        self.print_header("📦 Project Archiving Bot")

        # Output directory in releases/ (local, gitignored)
        output_dir = self.project_root / "releases"

        # Create archive (also copies to iCloud)
        archive_path, checksum = self.create_archive(sprint_name, output_dir, dry_run)

        if not dry_run and archive_path:
            results["archive_created"] = True
            results["archive_path"] = archive_path
            results["checksum"] = checksum

            # iCloud path
            icloud_path = (
                Path.home() / "Documents" / "cyclisme-training-logs-archives" / archive_path.name
            )
            results["icloud_path"] = icloud_path

            # Print results
            size_mb = archive_path.stat().st_size / (1024 * 1024)
            self.print_success(f"Archive created: {archive_path}")
            print(f"  Size: {size_mb:.1f} MB")
            print(f"  SHA256: {checksum}")
            print(f"\n{GREEN}✅ Archive saved in 2 locations:{RESET}")
            print(f"  1. Local (gitignored): {archive_path}")
            print(f"  2. iCloud (shareable):  {icloud_path}")
            print(
                f"\n{BLUE}📱 Access from iPhone: Files → Documents → cyclisme-training-logs-archives{RESET}"
            )

        return results


def main():
    """Main entry point for the cleanup bot."""
    parser = argparse.ArgumentParser(
        description="Project cleanup and archiving automation bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Quick cleanup
  %(prog)s --deep             # Deep cleanup with report
  %(prog)s --archive --sprint R22  # Create archive
  %(prog)s --dry-run          # Show what would be done
        """,
    )

    parser.add_argument("--deep", action="store_true", help="Perform deep cleanup with full report")

    parser.add_argument("--archive", action="store_true", help="Create deliverable archive")

    parser.add_argument("--sprint", type=str, help="Sprint identifier for archive (e.g., R22)")

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.archive and not args.sprint:
        print(f"{RED}Error: --sprint required when using --archive{RESET}")
        sys.exit(1)

    # Initialize cleaner
    project_root = Path(__file__).parent.parent.parent
    cleaner = ProjectCleaner(project_root)

    try:
        if args.archive:
            # Run archiving
            results = cleaner.run_archive(args.sprint, dry_run=args.dry_run)
            if results["archive_created"]:
                print(f"\n{GREEN}{BOLD}✅ Archive created successfully!{RESET}")
        else:
            # Run cleanup
            results = cleaner.run_cleanup(deep=args.deep, dry_run=args.dry_run)
            if results["misplaced_found"] == 0 and results["temp_cleaned"] == 0:
                print(f"\n{GREEN}{BOLD}✅ Project is perfectly clean!{RESET}")
            elif results["misplaced_found"] > 0:
                print(
                    f"\n{YELLOW}{BOLD}⚠️  Found {results['misplaced_found']} "
                    f"files to organize{RESET}"
                )
            else:
                print(f"\n{GREEN}{BOLD}✅ Cleanup completed!{RESET}")

    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
