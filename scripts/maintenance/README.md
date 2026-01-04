# Maintenance Scripts

Scripts pour maintenir la qualité et l'organisation du projet.

## 🧹 Project Cleaner Bot

Bot automatisé de nettoyage et d'archivage du projet.

### Fonctionnalités

Le bot maintient le projet impeccable en :

1. **Nettoyant les fichiers temporaires**
   - `__pycache__/` directories
   - `*.pyc` fichiers
   - `.DS_Store` (macOS)
   - `*.swp`, `*.swo` (vim)
   - Caches (`.pytest_cache`, `.ruff_cache`, `.mypy_cache`)
   - Coverage HTML (`htmlcov/`)

2. **Détectant les fichiers mal placés**
   - Identifie fichiers à la racine qui ne devraient pas y être
   - Suggère l'emplacement approprié (releases/, archives/, etc.)
   - Liste blanche des fichiers autorisés à la racine

3. **Créant des archives**
   - Archive complète du projet (hors .git, caches, etc.)
   - Sauvegarde **HORS du projet** (dans /tmp/) pour ne pas polluer
   - Génération automatique du checksum SHA256
   - Nommage avec date et version

4. **Vérifiant les standards**
   - Exécute les pre-commit hooks
   - Affiche les statistiques du projet
   - Vérifie l'organisation

### Installation

Le bot est déjà installé avec le projet :

```bash
poetry install
```

### Utilisation

#### 1. Nettoyage Rapide

Nettoie les fichiers temporaires et vérifie l'organisation :

```bash
poetry run project-clean
```

**Exemple de sortie :**
```
======================================================================
                        🧹 Project Cleanup Bot
======================================================================

ℹ️  Cleaning temporary files...
✅ Cleaned 183 temporary files/directories
ℹ️  Checking root directory organization...
✅ Root directory is clean and organized
ℹ️  Verifying code standards...
✅ All pre-commit hooks pass

✅ Cleanup completed!
```

#### 2. Nettoyage Approfondi

Inclut statistiques détaillées du projet :

```bash
poetry run project-clean --deep
```

**Sortie additionnelle :**
```
ℹ️  Gathering project statistics...

Project Statistics:
  Python files: 87
  Test files: 54
  Lines of code: 12,450
```

#### 3. Mode Dry-Run

Affiche ce qui serait fait sans rien modifier :

```bash
poetry run project-clean --dry-run
```

Utile pour vérifier avant de nettoyer.

#### 4. Création d'Archive

Crée une archive complète du projet pour livrable MOA :

```bash
poetry run project-clean --archive --sprint R22
```

**Résultat :**
```
======================================================================
                        📦 Project Archiving Bot
======================================================================

ℹ️  Creating archive: /tmp/sprint-r22/sprint-r22-v2.2.0-20260104.tar.gz
✅ Archive created: /tmp/sprint-r22/sprint-r22-v2.2.0-20260104.tar.gz
  Size: 8.1 MB
  SHA256: e88d0360506975b63ccd32037d96aecb74bf9cabd71db2898f9ae8f6feddce41

Archive saved outside project to keep structure clean!

✅ Archive created successfully!
```

**Fichiers créés** (dans `/tmp/sprint-r22/`) :
- `sprint-r22-v2.2.0-20260104.tar.gz` - Archive complète
- `sprint-r22-v2.2.0-20260104.tar.gz.sha256` - Checksum

### Automatisation Recommandée

#### Workflow Git Hook

Ajouter au `.git/hooks/pre-push` pour nettoyer avant push :

```bash
#!/bin/bash
poetry run project-clean
```

#### Cron Job Hebdomadaire

Nettoyage automatique chaque lundi :

```bash
# Ajouter à crontab (crontab -e)
0 9 * * 1 cd /path/to/project && poetry run project-clean --deep
```

#### Alias Shell

Ajouter à `~/.zshrc` ou `~/.bashrc` :

```bash
alias pclean='poetry run project-clean'
alias pclean-deep='poetry run project-clean --deep'
alias parchive='poetry run project-clean --archive --sprint'
```

Usage :
```bash
pclean                # Nettoyage rapide
pclean-deep           # Nettoyage approfondi
parchive R22          # Créer archive Sprint R22
```

### Configuration

Le bot utilise des listes blanches et patterns configurables dans `project_cleaner.py` :

#### Fichiers Autorisés à la Racine

```python
self.allowed_root_files = {
    "README.md",
    "CODING_STANDARDS.md",
    "pyproject.toml",
    "poetry.lock",
    # ... etc
}
```

#### Patterns de Fichiers Temporaires

```python
self.temp_patterns = [
    "**/__pycache__",
    "**/*.pyc",
    "**/.DS_Store",
    # ... etc
]
```

#### Exclusions d'Archive

```python
self.archive_excludes = [
    ".git",
    "__pycache__",
    ".venv",
    # ... etc
]
```

### Comportement

#### Détection de Fichiers Mal Placés

Le bot suggère automatiquement où déplacer les fichiers :

| Type de Fichier | Destination Suggérée |
|-----------------|---------------------|
| `*.tar.gz`, `*.zip` | `releases/` |
| `*moa*`, `*livraison*`, `*sprint*` | `project-docs/archives/` |
| `fix_*.py` | `scripts/maintenance/` |
| `test_*.py` | `scripts/debug/` |
| Autres `*.txt`, `*.md` | `project-docs/archives/` |

**Exemple :**
```
⚠️  Found 3 misplaced files at root:
  → ANALYSE_MOA.md → project-docs/archives/
  → sprint-r21.tar.gz → releases/
  → fix_something.py → scripts/maintenance/

Run 'git mv <file> <destination>' to organize these files
```

#### Archives Hors Projet

Les archives sont **toujours créées en dehors du projet** dans `/tmp/sprint-XX/` pour :
- ✅ Garder le projet propre
- ✅ Éviter pollution de la structure
- ✅ Faciliter transfert/upload
- ✅ Ne pas tracker dans Git

### Intégration CI/CD

Ajouter à `.github/workflows/cleanup.yml` :

```yaml
name: Project Cleanup Check

on: [push, pull_request]

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Check project cleanliness
        run: poetry run project-clean --dry-run
```

### Autres Scripts de Maintenance

#### Scripts de Fix Docstrings (Historique)

Ces scripts ont été utilisés pour migrer le projet vers PEP 257 + Google Style :

- `fix_d202_docstrings.py` - Supprime lignes blanches après docstrings
- `fix_d205_docstrings.py` - Ajoute lignes blanches dans docstrings
- `fix_d400_docstrings.py` - Ajoute points finaux
- `fix_d400_safe.py` - Version AST-safe du fix D400
- `fix_d401_docstrings.py` - Convertit en mode impératif
- `fix_trailing_period_bug.py` - Corrige bug `:. ` introduit par scripts

**Note :** Ces scripts sont conservés pour référence historique.
Ils ne devraient plus être nécessaires grâce aux pre-commit hooks.

#### Validation Scripts

- `validate_gartner_tags.py` - Valide tags Gartner TIME dans docstrings
- `migrate_docstrings.py` - Script principal de migration docstrings

### Dépannage

#### Le script ne trouve pas le module

```bash
# Réinstaller le projet
poetry install
```

#### Permission denied

```bash
# Rendre le script exécutable
chmod +x scripts/maintenance/project_cleaner.py
```

#### Import errors

Vérifier que `scripts/__init__.py` et `scripts/maintenance/__init__.py` existent.

### Exemples d'Usage

#### Workflow Fin de Sprint

```bash
# 1. Nettoyer le projet
poetry run project-clean --deep

# 2. Vérifier qu'il n'y a rien à organiser
# (le bot affichera warnings si fichiers mal placés)

# 3. Créer l'archive livrable
poetry run project-clean --archive --sprint R22

# 4. Archive disponible dans /tmp/sprint-r22/
ls /tmp/sprint-r22/
```

#### Maintenance Hebdomadaire

```bash
# Lundi matin : nettoyage approfondi
poetry run project-clean --deep

# Vérifier statistiques projet
# Observer nombre de fichiers Python, tests, LOC
```

#### Avant Push Important

```bash
# Dry-run pour voir ce qui serait nettoyé
poetry run project-clean --dry-run

# Si OK, nettoyer pour de vrai
poetry run project-clean

# Puis commit et push
git add -A
git commit -m "chore: cleanup project"
git push
```

---

## 📚 Références

- **PEP 8** : https://peps.python.org/pep-0008/
- **PEP 257** : https://peps.python.org/pep-0257/
- **Pre-commit Hooks** : https://pre-commit.com/

---

**Auteur :** Claude Code (Anthropic)
**Date :** 2026-01-04
**Version :** 1.0.0
