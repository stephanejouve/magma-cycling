# PROMPT: Réorganisation docs/ + Migration Docstrings

## Contexte

Le projet a un dossier `docs/` avec 65 fichiers de documentation projet (guides, READMEs, workflows).

**Objectif:** Adopter structure standard industrie Python:
- `docs/` → Documentation API Sphinx (standard)
- `project-docs/` → Documentation projet (guides, workflows)

---

## Phase 1: Réorganisation Structure

### Étape 1.1: Renommer docs/ → project-docs/

```bash
cd ~/cyclisme-training-logs

# Checkpoint Git avant changements
git add .
git commit -m "checkpoint: Before docs reorganization"

# Renommer
mv docs/ project-docs/

# Vérifier
ls -la | grep docs
# Attendu: seulement project-docs/ (pas encore docs/)
```

### Étape 1.2: Créer Nouveau docs/ pour Sphinx

```bash
# Créer dossier standard
mkdir -p docs

# Créer sous-dossiers Sphinx
mkdir -p docs/_static
mkdir -p docs/_templates
```

### Étape 1.3: Mettre à Jour Références

#### README.md Principal

```bash
# Chercher références
grep -n "docs/" README.md

# Si trouvé, remplacer
sed -i.bak 's|docs/|project-docs/|g' README.md

# Vérifier changements
diff README.md.bak README.md

# Si OK, supprimer backup
rm README.md.bak
```

#### pyproject.toml

```bash
# Vérifier si référence docs/
grep "docs/" pyproject.toml

# Si présent, éditer manuellement
# [tool.poetry]
# readme = "project-docs/README.md"
```

#### .gitignore

```bash
# Ajouter à .gitignore
cat >> .gitignore << 'EOF'

# Sphinx build artifacts
docs/_build/
docs/_static/
docs/_templates/
EOF
```

#### Liens Internes project-docs/

```bash
cd project-docs

# Trouver liens cassés vers ../docs/
grep -r "\.\./docs/" . 2>/dev/null | head -10

# Fix automatique (si besoin)
# Adapter selon résultats grep
find . -type f -name "*.md" -exec sed -i.bak 's|../docs/README|../project-docs/README|g' {} \;

# Nettoyer backups
find . -name "*.bak" -delete

cd ..
```

### Étape 1.4: Commit Réorganisation

```bash
git add -A
git status

git commit -m "refactor: Reorganize documentation structure

Moved project documentation to project-docs/:
- docs/ → project-docs/ (65 files: guides, workflows, archive)

Created standard docs/ for Sphinx API documentation:
- Follows Python ecosystem conventions
- Compatible with Read the Docs
- GitHub Pages standard

Updated references:
- README.md: docs/ → project-docs/
- pyproject.toml: readme path
- .gitignore: Sphinx build artifacts

Next: Sphinx configuration + docstring migration
"
```

---

## Phase 2: Configuration Sphinx (docs/)

### Étape 2.1: Créer conf.py

**Fichier:** `docs/conf.py`

**Utiliser le code du prompt original:**
`PROMPT_DOCSTRING_MIGRATION_GOOGLE_STYLE.md` (lignes 580-650)

**Adaptations:**

```python
# Configuration project metadata
project = 'Cyclisme Training Logs'
copyright = '2025, Stéphane Jouve'
author = 'Stéphane Jouve'
release = '1.0.0'

# Chemin vers code source (depuis docs/)
import os
import sys
sys.path.insert(0, os.path.abspath('../cyclisme_training_logs'))

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',      # Google Style support
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_custom_sections = [('Metadata', 'params_style')]

# HTML output
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Autodoc settings
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
```

### Étape 2.2: Créer index.rst

**Fichier:** `docs/index.rst`

```rst
Cyclisme Training Logs - API Documentation
===========================================

Documentation auto-générée depuis les docstrings Google Style du code source.

.. toctree::
   :maxdepth: 2
   :caption: Core Modules:

   modules/config
   modules/insert_analysis
   modules/weekly_analysis

.. toctree::
   :maxdepth: 2
   :caption: Analyzers:

   modules/analyzers

.. toctree::
   :maxdepth: 2
   :caption: Core Components:

   modules/core

Documentation Projet
====================

Pour les guides, workflows et architecture, voir le dossier ``project-docs/``.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

### Étape 2.3: Créer Modules RST

```bash
cd docs

# Créer dossier modules
mkdir -p modules

# Auto-générer stubs
poetry run sphinx-apidoc -f -o modules/ ../cyclisme_training_logs

# Vérifier création
ls modules/
# Attendu: cyclisme_training_logs.rst, modules.rst, etc.
```

---

## Phase 3: Migration Docstrings (Identique Prompt Original)

### Étape 3.1: Créer scripts/maintenance/

```bash
mkdir -p scripts/maintenance
```

### Étape 3.2: Créer migrate_docstrings.py

**Fichier:** `scripts/maintenance/migrate_docstrings.py`

**Utiliser code complet:**
`PROMPT_DOCSTRING_MIGRATION_GOOGLE_STYLE.md` (lignes 90-460)

### Étape 3.3: Créer validate_docstrings.sh

**Fichier:** `scripts/maintenance/validate_docstrings.sh`

**Utiliser code complet:**
`PROMPT_DOCSTRING_MIGRATION_GOOGLE_STYLE.md` (lignes 670-720)

### Étape 3.4: Exécuter Migration (6 fichiers)

```bash
cd ~/cyclisme-training-logs

# Dry-run d'abord
python scripts/maintenance/migrate_docstrings.py --dry-run --verbose

# Si OK → Migration avec backup
python scripts/maintenance/migrate_docstrings.py --backup --verbose
```

**Fichiers cibles:**
1. `weekly_analysis.py` (GARTNER_TIME: E)
2. `stats.py` (GARTNER_TIME: T)
3. `analyzers/daily_aggregator.py`
4. `core/data_aggregator.py`
5. `core/timeline_injector.py`
6. `core/prompt_generator.py`

### Étape 3.5: Nettoyer config.py (Format Hybride)

**Fichier:** `cyclisme_training_logs/config.py`

**Supprimer lignes 40-42:**
```python
# AVANT (hybride problématique)
Author: Claude Code              # ← Supprimer
Created: 2024-12-23             # ← Supprimer
Updated: 2025-12-26             # ← Supprimer

Metadata:                        # ← Garder uniquement ça
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    ...
```

---

## Phase 4: Validation

### Étape 4.1: Tests Migration

```bash
cd ~/cyclisme-training-logs

# Tests pytest
poetry run pytest tests/test_docstring_migrator.py -v
# Attendu: 4/4 PASSED

# Validation Google Style
poetry run pydocstyle --convention=google cyclisme_training_logs/
# Attendu: 0 violations

# Vérifier aucun ancien format
grep -r "GARTNER_TIME:" cyclisme_training_logs/*.py
# Attendu: exit code 1 (rien trouvé)
```

### Étape 4.2: Build Sphinx

```bash
cd docs

# Build HTML
poetry run sphinx-build -b html . _build/html

# Vérifier erreurs
# Attendu: Build succeeded (ou warnings mineurs)

# Voir résultat
open _build/html/index.html  # macOS
# ou xdg-open _build/html/index.html  # Linux
```

---

## Phase 5: Commits Git

### Commit 1: Infrastructure Migration

```bash
git add scripts/maintenance/migrate_docstrings.py
git add scripts/maintenance/validate_docstrings.sh
git add docs/conf.py
git add docs/index.rst
git add docs/modules/

git commit -m "feat(docs): Add Sphinx infrastructure + migration tools

Created Sphinx API documentation in docs/:
- conf.py: Napoleon + Read the Docs theme
- index.rst: API documentation home
- modules/: Auto-generated module stubs

Created migration tooling:
- scripts/maintenance/migrate_docstrings.py (full migrator)
- scripts/maintenance/validate_docstrings.sh (validation)

Enables Google Style docstring standard enforcement.
Fixes test imports in test_docstring_migrator.py.
"
```

### Commit 2: Docstrings Migrés

```bash
git add cyclisme_training_logs/weekly_analysis.py
git add cyclisme_training_logs/stats.py
git add cyclisme_training_logs/analyzers/daily_aggregator.py
git add cyclisme_training_logs/core/data_aggregator.py
git add cyclisme_training_logs/core/timeline_injector.py
git add cyclisme_training_logs/core/prompt_generator.py
git add cyclisme_training_logs/config.py

git commit -m "docs: Complete migration to Google Style docstrings

Migrated final 6 files to Google Style:
- weekly_analysis.py (GARTNER_TIME: E → Metadata)
- stats.py (GARTNER_TIME: T → Metadata)
- analyzers/daily_aggregator.py
- core/data_aggregator.py
- core/timeline_injector.py
- core/prompt_generator.py

Cleaned hybrid format in config.py (removed duplicate metadata).

All Python files now use industry-standard Google Style.
Validated with: pydocstyle --convention=google

API docs: http://localhost:8000 (sphinx-build)
"
```

---

## Structure Finale

```
cyclisme-training-logs/
│
├── docs/                        # ✅ Documentation API Sphinx (STANDARD)
│   ├── conf.py                  # Napoleon + RTD theme
│   ├── index.rst                # API home
│   ├── modules/                 # Auto-generated
│   │   ├── cyclisme_training_logs.rst
│   │   └── modules.rst
│   ├── _static/
│   ├── _templates/
│   └── _build/                  # HTML généré
│       └── html/
│           └── index.html
│
├── project-docs/                # ✅ Documentation projet (ancien docs/)
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── guides/
│   ├── workflows/
│   └── archive/
│
├── cyclisme_training_logs/      # Code source
│   ├── config.py                # ✅ Google Style
│   ├── weekly_analysis.py       # ✅ Google Style
│   ├── stats.py                 # ✅ Google Style
│   └── core/
│       ├── data_aggregator.py   # ✅ Google Style
│       └── timeline_injector.py # ✅ Google Style
│
└── scripts/
    └── maintenance/
        ├── migrate_docstrings.py
        └── validate_docstrings.sh
```

---

## Checklist Validation Finale

- [ ] `docs/` renommé en `project-docs/` ✅
- [ ] Nouveau `docs/` créé pour Sphinx ✅
- [ ] Références mises à jour (README, pyproject.toml) ✅
- [ ] `.gitignore` mis à jour (Sphinx artifacts) ✅
- [ ] `docs/conf.py` créé avec Napoleon ✅
- [ ] `docs/index.rst` créé ✅
- [ ] Scripts migration créés ✅
- [ ] 6 fichiers migrés Google Style ✅
- [ ] Format hybride config.py nettoyé ✅
- [ ] Tests pytest 4/4 PASSED ✅
- [ ] pydocstyle validation PASSED ✅
- [ ] Sphinx build réussi ✅
- [ ] 2 commits Git propres ✅
- [ ] grep "GARTNER_TIME:" → 0 résultats ✅

---

## Timeline Estimée

| Phase | Durée | Cumulé |
|-------|-------|--------|
| Réorganisation docs/ | 10 min | 10 min |
| Config Sphinx | 8 min | 18 min |
| Scripts migration | 10 min | 28 min |
| Exécution migration | 5 min | 33 min |
| Validation complète | 7 min | 40 min |
| Commits Git | 3 min | **43 min** |

---

**Créé:** 2025-12-27 15:15
**Priorité:** P0 (réorganisation + migration complète)
**Standard:** Python ecosystem best practices
**Compatible:** Read the Docs, GitHub Pages
