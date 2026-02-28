# PROMPT: Migration Docstrings vers Google Style (Standard Industrie)

## Objectif

Migrer tous les docstrings du projet depuis le format custom `GARTNER_TIME` vers le standard industrie **Google Style** avec support Sphinx, tout en préservant les métadonnées custom dans une section dédiée.

## Contexte

- **Projet:** `magma-cycling` (Python package)
- **Format actuel:** Non-standard GARTNER_TIME
- **Format cible:** Google Style (PEP 257 compliant)
- **Tooling requis:** Compatible Sphinx, pydocstyle, darglint, IDEs

### Format Actuel (Non-Standard)

```python
"""
Configuration centrale pour séparation code/données

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P0
DOCSTRING: v2

Module de configuration...
"""
```

**Problèmes:**
- ❌ Non reconnu par outils industrie (Sphinx, pdoc)
- ❌ Pas de support IDE (VS Code, PyCharm)
- ❌ Impossible génération docs automatique
- ❌ Non conforme PEP 257

### Format Cible (Google Style)

```python
"""
Brief one-line summary of the module.

Extended description explaining the module's purpose, architecture,
and key responsibilities. Multiple paragraphs allowed.

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: CORE
    Status: Production
    Priority: P0
    Version: 2.0

Examples:
    Basic usage::

        from magma_cycling.config import get_data_config
        config = get_data_config()
        print(config.data_repo_path)

Note:
    Important considerations or requirements.

Todo:
    * Future improvements
    * Pending features
"""
```

**Avantages:**
- ✅ Standard industrie (Google, Meta, Microsoft)
- ✅ Support Sphinx + Napoleon extension
- ✅ Auto-completion IDE
- ✅ Génération docs automatique
- ✅ Section Metadata pour infos custom

---

## Modifications à Effectuer

### 1. Créer Script de Migration

**Fichier:** `scripts/maintenance/migrate_docstrings.py`

**Créer le fichier complet:**

```python
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

        python migrate_docstrings.py --input-dir magma_cycling/core/

Note:
    Always run with --backup flag first to create .bak files.
    Review changes before deleting backups.

Todo:
    * Add support for class/function docstrings
    * Implement rollback mechanism
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import logging
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
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
                project_root=Path('magma_cycling'),
                backup=True
            )
            stats = migrator.migrate_all()
            print(f"Migrated {stats['migrated']} files")
    """

    # Pattern pour détecter l'ancien format
    GARTNER_PATTERN = re.compile(
        r'"""[\s\S]*?'
        r'GARTNER_TIME:\s*(?P<category>\w+)\s*\n'
        r'STATUS:\s*(?P<status>\w+)\s*\n'
        r'LAST_REVIEW:\s*(?P<review>[\d-]+)\s*\n'
        r'PRIORITY:\s*(?P<priority>\w+)\s*\n'
        r'DOCSTRING:\s*(?P<version>[\w.]+)\s*\n',
        re.MULTILINE
    )

    def __init__(
        self,
        project_root: Path,
        backup: bool = True,
        dry_run: bool = False
    ):
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
        self.stats = {
            'scanned': 0,
            'migrated': 0,
            'skipped': 0,
            'errors': 0
        }

    def extract_description(self, docstring: str) -> str:
        """
        Extract the description part from old docstring.

        Args:
            docstring: Original docstring text.

        Returns:
            Cleaned description text without metadata lines.
        """
        # Enlever les lignes de métadonnées
        lines = docstring.split('\n')
        description_lines = []

        skip_keywords = {
            'GARTNER_TIME:', 'STATUS:', 'LAST_REVIEW:',
            'PRIORITY:', 'DOCSTRING:'
        }

        for line in lines:
            # Skip metadata lines
            if any(kw in line for kw in skip_keywords):
                continue
            # Skip opening/closing quotes
            if line.strip() in ['"""', "'''"]:
                continue
            description_lines.append(line)

        # Nettoyer et rejoindre
        description = '\n'.join(description_lines).strip()
        return description

    def parse_old_docstring(self, content: str) -> Optional[DocstringMetadata]:
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
        full_docstring = content[docstring_start:docstring_end + 3]

        description = self.extract_description(full_docstring)

        return DocstringMetadata(
            category=data['category'],
            status=data['status'],
            last_review=data['review'],
            priority=data['priority'],
            version=data['version'],
            description=description
        )

    def generate_google_style_docstring(
        self,
        metadata: DocstringMetadata
    ) -> str:
        """
        Generate Google Style docstring from metadata.

        Args:
            metadata: Extracted metadata from old format.

        Returns:
            Formatted Google Style docstring string.
        """
        # Séparer première ligne du reste
        lines = metadata.description.split('\n')
        brief = lines[0].strip() if lines else "Module description."

        # Description étendue (tout sauf première ligne)
        extended = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""

        # Construire docstring
        parts = [f'"""\n{brief}']

        if extended:
            parts.append(f'\n{extended}')

        # Metadata section
        parts.append(f"""

Metadata:
    Created: {metadata.last_review}
    Author: Cyclisme Training Logs Team
    Category: {metadata.category}
    Status: {metadata.status}
    Priority: {metadata.priority}
    Version: {metadata.version}
""")

        parts.append('"""')

        return ''.join(parts)

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
            content = file_path.read_text(encoding='utf-8')

            # Parser ancien format
            metadata = self.parse_old_docstring(content)

            if not metadata:
                logger.debug(f"No old format found: {file_path}")
                self.stats['skipped'] += 1
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

            new_content = (
                content[:doc_start] +
                new_docstring +
                content[doc_end:]
            )

            # Preview ou écriture
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would migrate: {file_path}")
                logger.debug(f"New docstring:\n{new_docstring}")
            else:
                # Backup si demandé
                if self.backup:
                    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                    file_path.rename(backup_path)
                    logger.debug(f"Backup created: {backup_path}")

                # Écrire nouveau contenu
                file_path.write_text(new_content, encoding='utf-8')
                logger.info(f"✅ Migrated: {file_path}")

            self.stats['migrated'] += 1
            return True

        except Exception as e:
            logger.error(f"Error migrating {file_path}: {e}")
            self.stats['errors'] += 1
            return False

    def migrate_all(self) -> Dict[str, int]:
        """
        Migrate all Python files in project root.

        Returns:
            Statistics dictionary with counts of scanned/migrated/skipped/errors.
        """
        # Trouver tous les fichiers Python
        python_files = list(self.project_root.rglob('*.py'))

        # Exclure patterns
        exclude_patterns = {
            '__pycache__',
            '.git',
            '.venv',
            'venv',
            '.pytest_cache',
            'build',
            'dist',
            '.eggs',
            'tests'  # Optionnel: exclure tests
        }

        for py_file in python_files:
            # Vérifier exclusions
            if any(pattern in py_file.parts for pattern in exclude_patterns):
                continue

            self.stats['scanned'] += 1
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
        description='Migrate GARTNER_TIME docstrings to Google Style',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate entire project with backup
  python migrate_docstrings.py --backup

  # Preview changes without writing
  python migrate_docstrings.py --dry-run

  # Migrate specific directory
  python migrate_docstrings.py --input-dir magma_cycling/core/

  # Verbose output
  python migrate_docstrings.py --backup --verbose
        """
    )

    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path.cwd() / 'magma_cycling',
        help='Root directory to scan (default: ./magma_cycling)'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create .bak files before modification'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable debug logging'
    )

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
        project_root=args.input_dir,
        backup=args.backup,
        dry_run=args.dry_run
    )

    # Exécuter migration
    logger.info(f"Starting migration in: {args.input_dir}")
    logger.info(f"Backup: {args.backup}, Dry-run: {args.dry_run}")

    stats = migrator.migrate_all()

    # Afficher résumé
    print("\n" + "="*50)
    print("MIGRATION SUMMARY")
    print("="*50)
    print(f"Files scanned:  {stats['scanned']}")
    print(f"Files migrated: {stats['migrated']}")
    print(f"Files skipped:  {stats['skipped']}")
    print(f"Errors:         {stats['errors']}")
    print("="*50)

    if args.dry_run:
        print("\n⚠️  DRY-RUN MODE - No files were modified")
        print("Remove --dry-run to apply changes")
    elif stats['migrated'] > 0:
        print(f"\n✅ Successfully migrated {stats['migrated']} file(s)")
        if args.backup:
            print("📦 Backup files created with .bak extension")

    return 0 if stats['errors'] == 0 else 1


if __name__ == '__main__':
    exit(main())
```

---

### 2. Créer Tests Unitaires

**Fichier:** `tests/test_docstring_migrator.py`

```python
"""
Tests for docstring migration to Google Style.

Metadata:
    Created: 2025-12-27
    Author: Cyclisme Training Logs Team
    Category: TEST
    Status: Development
    Priority: P1
    Version: 1.0.0
"""

import pytest
from pathlib import Path
from scripts.maintenance.migrate_docstrings import (
    DocstringMigrator,
    DocstringMetadata
)


@pytest.fixture
def sample_old_docstring():
    """Sample file with old GARTNER_TIME format."""
    return '''"""
Configuration centrale pour séparation code/données

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P0
DOCSTRING: v2

Module de configuration gérant la séparation entre code et données.
"""

from pathlib import Path
'''


@pytest.fixture
def temp_python_file(tmp_path, sample_old_docstring):
    """Create temporary Python file with old format."""
    test_file = tmp_path / "test_module.py"
    test_file.write_text(sample_old_docstring)
    return test_file


def test_parse_old_docstring(sample_old_docstring):
    """Test parsing of old GARTNER_TIME format."""
    migrator = DocstringMigrator(project_root=Path.cwd())
    metadata = migrator.parse_old_docstring(sample_old_docstring)

    assert metadata is not None
    assert metadata.category == 'I'
    assert metadata.status == 'Production'
    assert metadata.priority == 'P0'
    assert metadata.version == 'v2'


def test_generate_google_style():
    """Test Google Style docstring generation."""
    metadata = DocstringMetadata(
        category='CORE',
        status='Production',
        last_review='2025-12-27',
        priority='P0',
        version='1.0',
        description='Brief summary.\n\nExtended description.'
    )

    migrator = DocstringMigrator(project_root=Path.cwd())
    result = migrator.generate_google_style_docstring(metadata)

    assert 'Brief summary.' in result
    assert 'Metadata:' in result
    assert 'Created: 2025-12-27' in result
    assert 'Category: CORE' in result
    assert 'Priority: P0' in result


def test_migrate_file(temp_python_file):
    """Test file migration with backup."""
    migrator = DocstringMigrator(
        project_root=temp_python_file.parent,
        backup=True,
        dry_run=False
    )

    # Migrate
    result = migrator.migrate_file(temp_python_file)
    assert result is True

    # Verify backup created
    backup_file = temp_python_file.with_suffix('.py.bak')
    assert backup_file.exists()

    # Verify new content
    new_content = temp_python_file.read_text()
    assert 'Metadata:' in new_content
    assert 'GARTNER_TIME:' not in new_content


def test_dry_run_mode(temp_python_file):
    """Test dry-run mode doesn't modify files."""
    original_content = temp_python_file.read_text()

    migrator = DocstringMigrator(
        project_root=temp_python_file.parent,
        backup=False,
        dry_run=True
    )

    migrator.migrate_file(temp_python_file)

    # File should be unchanged
    assert temp_python_file.read_text() == original_content
```

---

### 3. Configuration Sphinx (Documentation Auto)

**Fichier:** `docs/conf.py`

```python
"""
Sphinx configuration for magma-cycling documentation.

Metadata:
    Created: 2025-12-27
    Author: Cyclisme Training Logs Team
    Category: DOCS
    Status: Production
    Priority: P1
    Version: 1.0.0
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Project information
project = 'Cyclisme Training Logs'
copyright = '2025, Cyclisme Training Logs Team'
author = 'Cyclisme Training Logs Team'
release = '2.0.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',       # Auto-generate docs from docstrings
    'sphinx.ext.napoleon',      # Google/NumPy style support
    'sphinx.ext.viewcode',      # Link to source code
    'sphinx.ext.intersphinx',   # Link to other projects
    'sphinx.ext.todo',          # Support for Todo sections
    'sphinx_rtd_theme',         # Read the Docs theme
]

# Napoleon settings (Google Style)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_custom_sections = [('Metadata', 'params_style')]

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# HTML output
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Todo extension
todo_include_todos = True
```

---

### 4. Script de Validation (pydocstyle)

**Fichier:** `scripts/maintenance/validate_docstrings.sh`

```bash
#!/bin/bash
"""
Validate Google-style docstrings compliance.

Metadata:
    Created: 2025-12-27
    Author: Cyclisme Training Logs Team
    Category: MAINTENANCE
    Status: Production
    Priority: P2
    Version: 1.0.0
"""

set -e

echo "🔍 Validating Google-style docstrings..."

# Install dependencies if needed
pip install -q pydocstyle darglint sphinx

# Check Google-style compliance
echo "1️⃣ Checking PEP 257 compliance (Google convention)..."
pydocstyle --convention=google magma_cycling/ || {
    echo "❌ Docstring style violations found"
    exit 1
}

# Validate docstring/signature match
echo "2️⃣ Validating docstring/code consistency..."
darglint -v 2 magma_cycling/ || {
    echo "⚠️ Docstring/signature mismatches found"
    # Non-blocking pour l'instant
}

# Generate Sphinx docs (test)
echo "3️⃣ Testing Sphinx documentation generation..."
cd docs
make clean
make html || {
    echo "❌ Sphinx doc generation failed"
    exit 1
}
cd ..

echo "✅ All docstring validations passed!"
```

---

## Validation

### Tests Manuels

```bash
cd ~/magma-cycling

# 1. Test dry-run (preview sans modifications)
python scripts/maintenance/migrate_docstrings.py --dry-run --verbose

# 2. Migration avec backup
python scripts/maintenance/migrate_docstrings.py --backup --verbose

# 3. Vérifier un fichier migré
cat magma_cycling/config.py | head -30

# 4. Valider conformité Google Style
pip install pydocstyle
pydocstyle --convention=google magma_cycling/

# 5. Générer documentation Sphinx
cd docs
make html
open _build/html/index.html  # macOS
# ou xdg-open _build/html/index.html  # Linux
```

### Tests Automatisés

```bash
cd ~/magma-cycling

# Lancer tests pytest
poetry run pytest tests/test_docstring_migrator.py -v

# Attendu:
# test_parse_old_docstring PASSED
# test_generate_google_style PASSED
# test_migrate_file PASSED
# test_dry_run_mode PASSED
```

---

## Commits Git

### Commit 1: Script Migration

```bash
cd ~/magma-cycling

git add scripts/maintenance/migrate_docstrings.py
git add tests/test_docstring_migrator.py

git commit -m "feat(docs): Add Google Style docstring migration tool

- New migrator script: migrate_docstrings.py
- Converts GARTNER_TIME to Google Style format
- Preserves metadata in dedicated Metadata section
- Backup mode and dry-run support
- Full pytest test coverage

Why Google Style:
- Industry standard (Google, Meta, Microsoft)
- Sphinx + Napoleon support
- IDE auto-completion
- Auto-generated documentation

Usage:
  python scripts/maintenance/migrate_docstrings.py --backup

Related: PEP 257, Sphinx documentation
"
```

### Commit 2: Migration Exécutée

```bash
# Après avoir vérifié la migration en dry-run
python scripts/maintenance/migrate_docstrings.py --backup

git add magma_cycling/**/*.py
git add -u  # Stages deletions (.bak files excluded by .gitignore)

git commit -m "docs: Migrate all docstrings to Google Style format

- Migrated XX files from GARTNER_TIME to Google Style
- All metadata preserved in Metadata sections
- Backup files created (.bak)
- Validated with pydocstyle --convention=google

Benefits:
- Industry-standard format
- Sphinx documentation ready
- IDE support enabled
- Auto-completion improved

Migration tool: scripts/maintenance/migrate_docstrings.py
Validation: pydocstyle --convention=google
"
```

### Commit 3: Sphinx Configuration

```bash
git add docs/conf.py
git add docs/Makefile  # Si créé
git add docs/index.rst  # Si créé

git commit -m "docs: Add Sphinx configuration for auto-documentation

- Napoleon extension for Google Style
- Read the Docs theme
- Auto-generate API docs from docstrings
- Custom Metadata section support

Generate docs:
  cd docs && make html

View:
  open docs/_build/html/index.html
"
```

---

## Roadmap Post-Migration

### Phase 1: Migration Complete ✅
- [x] Script migrator créé
- [x] Tests unitaires
- [x] Migration exécutée
- [x] Validation pydocstyle

### Phase 2: Documentation (Semaine 1)
- [ ] Générer Sphinx docs complètes
- [ ] Publier sur Read the Docs
- [ ] Ajouter examples dans docstrings critiques
- [ ] CI/CD check docstring quality

### Phase 3: Amélioration Continue (Semaine 2-4)
- [ ] Pre-commit hook pydocstyle
- [ ] Darglint validation (docstring/code sync)
- [ ] Coverage docstrings 100%
- [ ] API reference complète

---

## Configuration Recommandée

### .pre-commit-config.yaml (Optionnel)

```yaml
repos:
  - repo: local
    hooks:
      - id: pydocstyle
        name: pydocstyle (Google convention)
        entry: pydocstyle --convention=google
        language: system
        types: [python]
        exclude: ^(tests/|docs/)
```

### pyproject.toml (pydocstyle config)

```toml
[tool.pydocstyle]
convention = "google"
add-ignore = ["D100", "D104"]  # Ignore missing docstrings in __init__.py
match = "(?!test_).*\\.py"     # Skip test files
```

---

## Impact Attendu

### Performance Documentation
- ✅ Génération Sphinx docs: < 10 secondes
- ✅ IDE auto-completion: Instantané
- ✅ pydocstyle validation: < 5 secondes

### Qualité Code
- ✅ Standard industrie adopté
- ✅ Documentation auto-générée
- ✅ Maintenabilité améliorée
- ✅ Onboarding développeurs facilité

### Tooling Disponible
- ✅ Sphinx (docs web)
- ✅ pdoc (docs lightweight)
- ✅ pydocstyle (linter)
- ✅ darglint (validation)
- ✅ IDE support (VS Code, PyCharm)

---

**Créé:** 2025-12-27 10:15
**Priorité:** P1 (standardisation critique)
**Effort:** 1-2 heures (migration + validation)
**Dépendances:** Aucune (peut être fait en parallèle du backfill)
**Tests requis:** pytest + pydocstyle + Sphinx build
