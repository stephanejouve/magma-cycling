#!/usr/bin/env python3
"""
Migration tool for converting custom GARTNER_TIME docstrings to Google Style.

This script automatically migrates docstrings from the custom GARTNER_TIME format
to industry-standard Google Style docstrings, preserving all metadata in a
dedicated Metadata section.

Metadata:
    Created: 2025-12-27
    Author: Cyclisme Training Logs Team
    Category: MAINTENANCE
    Status: Production
    Priority: P1
    Version: 1.0.0

Examples:
    Migrate entire project with backup::

        python migrate_docstrings.py --backup

    Dry-run to preview changes::

        python migrate_docstrings.py --dry-run

    Migrate specific directory::

        python migrate_docstrings.py --input-dir cyclisme_training_logs/core/

Note:
    Always run with --backup flag first to create .bak files.
    Review changes before deleting backups.

Todo:
    * Add support for class/function docstrings
    * Implement rollback mechanism
"""

import argparse
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class DocstringMetadata:
    """Container for extracted docstring metadata.

    Attributes:
        category: GARTNER_TIME category (e.g., 'I', 'CORE').
        status: Module status (Production, Dev, Test).
        last_review: Last review date (ISO format).
        priority: Priority level (P0, P1, P2).
        version: Docstring version.
        description: Original module description.
    """

    category: str
    status: str
    last_review: str
    priority: str
    version: str
    description: str


class DocstringMigrator:
    """
    Migrates custom GARTNER_TIME docstrings to Google Style format.

    This migrator preserves all custom metadata in a dedicated Metadata section
    while converting to industry-standard Google Style format compatible with
    Sphinx and other documentation tools.

    Attributes:
        GARTNER_PATTERN: Regex pattern for detecting old format.
        project_root: Root directory of the project.
        backup: Whether to create backup files.
        dry_run: Preview changes without writing.

    Examples:
        Basic migration::

            migrator = DocstringMigrator(
                project_root=Path('cyclisme_training_logs'),
                backup=True
            )
            stats = migrator.migrate_all()
            print(f"Migrated {stats['migrated']} files")
    """

    # Pattern pour détecter l'ancien format
    GARTNER_PATTERN = re.compile(
        r'"""[\s\S]*?'
        r"GARTNER_TIME:\s*(?P<category>\w+)\s*\n"
        r"STATUS:\s*(?P<status>\w+)\s*\n"
        r"LAST_REVIEW:\s*(?P<review>[\d-]+)\s*\n"
        r"PRIORITY:\s*(?P<priority>\w+)\s*\n"
        r"DOCSTRING:\s*(?P<version>[\w.]+)\s*\n",
        re.MULTILINE,
    )

    def __init__(self, project_root: Path, backup: bool = True, dry_run: bool = False):
        """
        Initialize the migrator.

        Args:
            project_root: Root directory to scan for Python files.
            backup: If True, create .bak files before modification.
            dry_run: If True, preview changes without writing files.
        """
        self.project_root = project_root
        self.backup = backup
        self.dry_run = dry_run
        self.stats = {"scanned": 0, "migrated": 0, "skipped": 0, "errors": 0}

    def extract_description(self, docstring: str) -> str:
        """
        Extract the description part from old docstring.

        Args:
            docstring: Original docstring text.

        Returns:
            Cleaned description text without metadata lines.
        """
        # Enlever les lignes de métadonnées
        lines = docstring.split("\n")
        description_lines = []

        skip_keywords = {"GARTNER_TIME:", "STATUS:", "LAST_REVIEW:", "PRIORITY:", "DOCSTRING:"}

        for line in lines:
            # Skip metadata lines
            if any(kw in line for kw in skip_keywords):
                continue
            # Skip opening/closing quotes
            if line.strip() in ['"""', "'''"]:
                continue
            description_lines.append(line)

        # Nettoyer et rejoindre
        description = "\n".join(description_lines).strip()
        return description

    def parse_old_docstring(self, content: str) -> DocstringMetadata | None:
        """
        Parse old GARTNER_TIME format docstring.

        Args:
            content: File content containing docstring.

        Returns:
            DocstringMetadata if found, None otherwise.
        """
        match = self.GARTNER_PATTERN.search(content)
        if not match:
            return None

        # Extraire les groupes
        data = match.groupdict()

        # Extraire la description complète
        docstring_start = content.find('"""')
        docstring_end = content.find('"""', docstring_start + 3)
        full_docstring = content[docstring_start : docstring_end + 3]

        description = self.extract_description(full_docstring)

        return DocstringMetadata(
            category=data["category"],
            status=data["status"],
            last_review=data["review"],
            priority=data["priority"],
            version=data["version"],
            description=description,
        )

    def generate_google_style_docstring(self, metadata: DocstringMetadata) -> str:
        """
        Generate Google Style docstring from metadata.

        Args:
            metadata: Extracted metadata from old format.

        Returns:
            Formatted Google Style docstring string.
        """
        # Séparer première ligne du reste
        lines = metadata.description.split("\n")
        brief = lines[0].strip() if lines else "Module description."

        # Description étendue (tout sauf première ligne)
        extended = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        # Construire docstring
        parts = [f'"""\n{brief}']

        if extended:
            parts.append(f"\n{extended}")

        # Metadata section
        parts.append(
            f"""

Metadata:
    Created: {metadata.last_review}
    Author: Cyclisme Training Logs Team
    Category: {metadata.category}
    Status: {metadata.status}
    Priority: {metadata.priority}
    Version: {metadata.version}
"""
        )

        parts.append('"""')

        return "".join(parts)

    def migrate_file(self, file_path: Path) -> bool:
        """
        Migrate a single Python file.

        Args:
            file_path: Path to Python file to migrate.

        Returns:
            True if file was migrated, False if skipped.

        Raises:
            IOError: If file cannot be read or written.
        """
        try:
            content = file_path.read_text(encoding="utf-8")

            # Parser ancien format
            metadata = self.parse_old_docstring(content)

            if not metadata:
                logger.debug(f"No old format found: {file_path}")
                self.stats["skipped"] += 1
                return False

            # Générer nouveau format
            new_docstring = self.generate_google_style_docstring(metadata)

            # Remplacer dans le contenu
            match = self.GARTNER_PATTERN.search(content)
            if not match:
                return False

            # Trouver bornes du docstring complet
            doc_start = content.find('"""')
            doc_end = content.find('"""', doc_start + 3) + 3

            new_content = content[:doc_start] + new_docstring + content[doc_end:]

            # Preview ou écriture
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would migrate: {file_path}")
                logger.debug(f"New docstring:\n{new_docstring}")
            else:
                # Backup si demandé
                if self.backup:
                    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                    backup_path.write_text(content, encoding="utf-8")
                    logger.debug(f"Backup created: {backup_path}")

                # Écrire nouveau contenu
                file_path.write_text(new_content, encoding="utf-8")
                logger.info(f"✅ Migrated: {file_path}")

            self.stats["migrated"] += 1
            return True

        except Exception as e:
            logger.error(f"Error migrating {file_path}: {e}")
            self.stats["errors"] += 1
            return False

    def migrate_all(self) -> dict[str, int]:
        """
        Migrate all Python files in project root.

        Returns:
            Statistics dictionary with counts of scanned/migrated/skipped/errors.
        """
        # Trouver tous les fichiers Python
        python_files = list(self.project_root.rglob("*.py"))

        # Exclure patterns
        exclude_patterns = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            ".pytest_cache",
            "build",
            "dist",
            ".eggs",
            "tests",  # Optionnel: exclure tests
        }

        for py_file in python_files:
            # Vérifier exclusions
            if any(pattern in py_file.parts for pattern in exclude_patterns):
                continue

            self.stats["scanned"] += 1
            self.migrate_file(py_file)

        return self.stats


def main():
    """
    Command-line entry point for docstring migration.

    Examples:
        Migrate with backup::

            python migrate_docstrings.py --backup

        Dry-run preview::

            python migrate_docstrings.py --dry-run
    """
    parser = argparse.ArgumentParser(
        description="Migrate GARTNER_TIME docstrings to Google Style",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate entire project with backup
  python migrate_docstrings.py --backup

  # Preview changes without writing
  python migrate_docstrings.py --dry-run

  # Migrate specific directory
  python migrate_docstrings.py --input-dir cyclisme_training_logs/core/

  # Verbose output
  python migrate_docstrings.py --backup --verbose
        """,
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path.cwd() / "cyclisme_training_logs",
        help="Root directory to scan (default: ./cyclisme_training_logs)",
    )
    parser.add_argument(
        "--backup", action="store_true", help="Create .bak files before modification"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing files"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Vérifier que le répertoire existe
    if not args.input_dir.exists():
        logger.error(f"Directory not found: {args.input_dir}")
        return 1

    # Créer migrator
    migrator = DocstringMigrator(
        project_root=args.input_dir, backup=args.backup, dry_run=args.dry_run
    )

    # Exécuter migration
    logger.info(f"Starting migration in: {args.input_dir}")
    logger.info(f"Backup: {args.backup}, Dry-run: {args.dry_run}")

    stats = migrator.migrate_all()

    # Afficher résumé
    print("\n" + "=" * 50)
    print("MIGRATION SUMMARY")
    print("=" * 50)
    print(f"Files scanned:  {stats['scanned']}")
    print(f"Files migrated: {stats['migrated']}")
    print(f"Files skipped:  {stats['skipped']}")
    print(f"Errors:         {stats['errors']}")
    print("=" * 50)

    if args.dry_run:
        print("\n⚠️  DRY-RUN MODE - No files were modified")
        print("Remove --dry-run to apply changes")
    elif stats["migrated"] > 0:
        print(f"\n✅ Successfully migrated {stats['migrated']} file(s)")
        if args.backup:
            print("📦 Backup files created with .bak extension")

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    exit(main())
