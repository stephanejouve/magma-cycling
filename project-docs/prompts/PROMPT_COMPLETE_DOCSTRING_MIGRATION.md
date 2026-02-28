# PROMPT: Compléter Migration Docstrings Google Style

## Contexte Actuel

L'archive `claude-code-context_20251227_142525.tar.gz` montre une migration **PARTIELLE**:

### ✅ Déjà Fait
- `tests/test_docstring_migrator.py` créé (138 lignes) ✅
- `config.py` partiellement migré (format HYBRIDE) ⚠️
- Section Metadata ajoutée dans config.py

### ❌ Manquant (À Compléter)
- `scripts/maintenance/migrate_docstrings.py` **ABSENT** (requis par les tests)
- Dossier `scripts/maintenance/` **INEXISTANT**
- Config Sphinx `docs/conf.py` **ABSENTE**
- Script validation `scripts/maintenance/validate_docstrings.sh` **ABSENT**
- **6 fichiers** encore en ancien format `GARTNER_TIME:`
  1. `weekly_analysis.py`
  2. `stats.py`
  3. `analyzers/daily_aggregator.py`
  4. `core/data_aggregator.py`
  5. `core/timeline_injector.py`
  6. `core/prompt_generator.py`

---

## Objectif

**Compléter la migration vers Google Style** en créant les fichiers manquants et en migrant les 6 fichiers restants.

---

## Étape 1: Créer Dossier Maintenance

```bash
mkdir -p scripts/maintenance
```

---

## Étape 2: Créer Script Migration Complet

**Fichier:** `scripts/maintenance/migrate_docstrings.py`

**Utiliser le code complet du fichier:**
`PROMPT_DOCSTRING_MIGRATION_GOOGLE_STYLE.md` (lignes 90-460)

**Points clés:**
- Classe `DocstringMigrator` avec parsing AST
- Support backup automatique (.bak)
- Mode dry-run pour preview
- Pattern regex pour `GARTNER_TIME:` format
- Génération Google Style avec section Metadata

**IMPORTANT:** Le test `test_docstring_migrator.py` importe déjà ce module:
```python
from migrate_docstrings import (
    DocstringMigrator,
    DocstringMetadata
)
```

Le script DOIT être créé pour que les tests passent.

---

## Étape 3: Créer Configuration Sphinx

**Fichier:** `docs/conf.py`

**Utiliser le code complet du fichier:**
`PROMPT_DOCSTRING_MIGRATION_GOOGLE_STYLE.md` (lignes 580-650)

**Extensions requises:**
```python
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Support Google Style
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

napoleon_google_docstring = True
napoleon_custom_sections = [('Metadata', 'params_style')]
```

---

## Étape 4: Créer Script Validation

**Fichier:** `scripts/maintenance/validate_docstrings.sh`

**Utiliser le code complet du fichier:**
`PROMPT_DOCSTRING_MIGRATION_GOOGLE_STYLE.md` (lignes 670-720)

**Vérifications:**
1. pydocstyle --convention=google
2. darglint (optionnel)
3. Sphinx build test

---

## Étape 5: Exécuter Migration sur 6 Fichiers Restants

**Commande:**
```bash
cd ~/magma-cycling

# Dry-run d'abord (preview)
python scripts/maintenance/migrate_docstrings.py \
    --dry-run \
    --verbose

# Si OK → Migration avec backup
python scripts/maintenance/migrate_docstrings.py \
    --backup \
    --verbose
```

**Fichiers cibles (vérifier migration réussie):**
- `weekly_analysis.py` - Migrer `GARTNER_TIME: E`
- `stats.py` - Migrer `GARTNER_TIME: T`
- `analyzers/daily_aggregator.py`
- `core/data_aggregator.py`
- `core/timeline_injector.py`
- `core/prompt_generator.py`

---

## Étape 6: Nettoyer Format Hybride dans config.py

**Fichier:** `magma_cycling/config.py`

**Problème actuel (lignes 40-50):**
```python
Author: Claude Code                    # ← ANCIEN FORMAT (supprimer)
Created: 2024-12-23                    # ← ANCIEN FORMAT (supprimer)
Updated: 2025-12-26 (Added...)         # ← ANCIEN FORMAT (supprimer)

Metadata:                              # ← NOUVEAU FORMAT (garder)
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P0
    Version: v2
```

**Action:**
Supprimer lignes 40-42 (ancien format Author/Created/Updated) pour ne garder que la section Metadata.

**Résultat attendu:**
```python
"""
Configuration centrale pour séparation code/données.

Module de configuration gérant la séparation entre code et données...

Examples:
    Command-line usage::
        ...

Metadata:
    Created: 2025-12-26
    Author: Cyclisme Training Logs Team
    Category: I
    Status: Production
    Priority: P0
    Version: v2
"""
```

---

## Étape 7: Valider Migration Complète

**Tests à exécuter:**

```bash
cd ~/magma-cycling

# 1. Vérifier que tous les tests passent
poetry run pytest tests/test_docstring_migrator.py -v

# Attendu:
# test_parse_old_docstring PASSED
# test_generate_google_style PASSED
# test_migrate_file PASSED
# test_dry_run_mode PASSED

# 2. Valider conformité Google Style
pip install pydocstyle
pydocstyle --convention=google magma_cycling/

# Attendu: 0 violations (ou très peu)

# 3. Vérifier qu'aucun fichier n'a l'ancien format
grep -r "GARTNER_TIME:" magma_cycling/*.py

# Attendu: Aucun résultat (exit code 1)

# 4. Test génération Sphinx (optionnel)
cd docs
make html
```

---

## Étape 8: Commits Git

### Commit 1: Fichiers Infrastructure

```bash
git add scripts/maintenance/migrate_docstrings.py
git add scripts/maintenance/validate_docstrings.sh
git add docs/conf.py

git commit -m "feat(docs): Complete docstring migration infrastructure

Created missing files:
- scripts/maintenance/migrate_docstrings.py (full migrator)
- scripts/maintenance/validate_docstrings.sh (validation)
- docs/conf.py (Sphinx config with Napoleon)

Fixes test imports in test_docstring_migrator.py
Enables Google Style validation with pydocstyle
"
```

### Commit 2: Migration Exécutée

```bash
# Après migration réussie des 6 fichiers
git add magma_cycling/weekly_analysis.py
git add magma_cycling/stats.py
git add magma_cycling/analyzers/daily_aggregator.py
git add magma_cycling/core/data_aggregator.py
git add magma_cycling/core/timeline_injector.py
git add magma_cycling/core/prompt_generator.py
git add magma_cycling/config.py  # Format hybride nettoyé

git commit -m "docs: Complete migration to Google Style docstrings

Migrated final 6 files to Google Style format:
- weekly_analysis.py (GARTNER_TIME: E → Metadata)
- stats.py (GARTNER_TIME: T → Metadata)
- analyzers/daily_aggregator.py
- core/data_aggregator.py
- core/timeline_injector.py
- core/prompt_generator.py

Cleaned hybrid format in config.py (removed duplicate Author/Created)

All 59 Python files now use Google Style standard.
Validated with: pydocstyle --convention=google

Migration tool: scripts/maintenance/migrate_docstrings.py
"
```

---

## Validation Finale

### Checklist Complétude

- [ ] `scripts/maintenance/migrate_docstrings.py` créé et fonctionnel
- [ ] `scripts/maintenance/validate_docstrings.sh` créé
- [ ] `docs/conf.py` créé (Sphinx + Napoleon)
- [ ] 6 fichiers migrés avec backup (.bak créés)
- [ ] Format hybride config.py nettoyé
- [ ] Tests pytest 4/4 PASSED
- [ ] pydocstyle validation PASSED
- [ ] grep "GARTNER_TIME:" → 0 résultats
- [ ] 2 commits Git propres

### Statistiques Attendues

**Avant:**
- Fichiers ancien format: 6
- Format hybride: 1 (config.py)
- Format standard: 0

**Après:**
- Fichiers ancien format: 0 ✅
- Format hybride: 0 ✅
- Format Google Style: 7 minimum (6 migrés + config.py nettoyé) ✅

---

## Notes Importantes

1. **Backup automatique:** Le script crée des fichiers .bak avant modification
2. **Dry-run recommandé:** Toujours tester avec --dry-run d'abord
3. **Tests existants:** Le test `test_docstring_migrator.py` attend le script
4. **Format hybride:** Nettoyer config.py est CRITIQUE pour cohérence

---

## Dépendances à Installer

```bash
pip install pydocstyle sphinx sphinx-rtd-theme
```

---

## Timeline Estimée

| Étape | Durée | Cumulé |
|-------|-------|--------|
| Créer migrate_docstrings.py | 10 min | 10 min |
| Créer docs/conf.py | 5 min | 15 min |
| Créer validate_docstrings.sh | 3 min | 18 min |
| Exécuter migration (6 fichiers) | 5 min | 23 min |
| Nettoyer config.py | 2 min | 25 min |
| Validation complète | 7 min | 32 min |
| Commits Git | 3 min | **35 min** |

**Total:** ~35 minutes pour migration 100% complète

---

**Créé:** 2025-12-27 14:45
**Priorité:** P0 (compléter travail commencé)
**Dépend de:** PROMPT_DOCSTRING_MIGRATION_GOOGLE_STYLE.md
**Bloquant:** tests/test_docstring_migrator.py (importe module absent)
