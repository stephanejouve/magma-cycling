# Maintenance Scripts

Scripts pour maintenir la qualité et l'organisation du projet.

## 📦 Code Review Package Generator

Script automatisé de génération de package de revue architecturale complet.

### Fonctionnalités

Génère un package professionnel pour revue de code externe contenant :

1. **Métriques qualité complètes**
   - Tests (497 passing, 100%)
   - PEP 8/257 compliance (0 violations)
   - MyPy type safety (0 errors)
   - Ruff linting (0 warnings)
   - Pre-commit hooks status

2. **Structure et analyse**
   - Arborescence complète du projet
   - Statistiques lignes de code (cloc)
   - Taille de chaque module
   - Graphe de dépendances (optionnel)

3. **Documentation complète**
   - CODING_STANDARDS.md
   - LIVRAISON_MOA documents
   - Sessions de développement
   - Explications warnings

4. **Code source**
   - Tous les fichiers Python (~87 fichiers)
   - Tests complets (~54 fichiers)
   - Configurations (pyproject.toml, hooks, CI/CD)

5. **Guides de revue**
   - README avec instructions claires
   - Guide de revue approfondi
   - Template de rapport
   - FAQ et explications

### Utilisation

```bash
# Depuis n'importe où
bash ~/cyclisme-training-logs/scripts/maintenance/generate_code_review_package.sh

# Ou depuis le projet
cd ~/cyclisme-training-logs
bash scripts/maintenance/generate_code_review_package.sh
```

### Résultat

**Fichiers générés dans `~/Downloads/` :**
- `review_package_v2.2.0_[TIMESTAMP]/` - Dossier complet
- `review_package_v2.2.0_[TIMESTAMP].zip` - Archive (~2-5 MB)
- `review_package_v2.2.0_[TIMESTAMP].zip.sha256` - Checksum

**Contenu du package :**
- Métriques à jour (tests exécutés lors génération)
- Documentation complète
- Code source pour consultation
- Guide de revue (express 15min ou approfondi 1h30)
- Template de rapport

### Quand l'utiliser

- **Fin de sprint** : Créer livrable MOA
- **Revue externe** : Package prêt à envoyer
- **Audit qualité** : Métriques complètes
- **Documentation** : Snapshot complet du projet

### Alias Recommandé

Ajouter à `~/.zshrc` :
```bash
alias review-package='bash ~/cyclisme-training-logs/scripts/maintenance/generate_code_review_package.sh'
```

Usage :
```bash
review-package  # Génère le package instantanément
```

---

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
  → sprint-r5.tar.gz → releases/
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

## 🗑️ Clear Week Planning

Script de maintenance pour supprimer les workouts planifiés erronés d'une semaine sur Intervals.icu.

### Fonctionnalités

- **Suppression sécurisée** : Ne supprime QUE les événements WORKOUT (workouts planifiés)
- **Préservation** : Ne touche PAS aux activités réalisées ni aux notes de calendrier
- **Mode dry-run** : Simulation pour voir ce qui serait supprimé sans rien toucher
- **Mode interactif** : Demande confirmation avant suppression réelle
- **Mode automatique** : Option `--yes` pour scripting sans confirmation
- **Verbose** : Option `--verbose` pour afficher détails et erreurs

### Cas d'Usage

Utilisez ce script quand vous avez besoin de :
- Effacer un planning de semaine complètement erroné
- Régénérer une semaine avec nouveaux paramètres
- Nettoyer les workouts planifiés avant réupload
- Corriger une erreur de planification

### Utilisation

#### 1. Mode Dry-Run (Simulation)

**Recommandé en premier** pour vérifier ce qui serait supprimé :

```bash
python scripts/maintenance/clear_week_planning.py \
  --week-id S075 \
  --start-date 2026-01-05 \
  --dry-run
```

**Exemple de sortie :**
```
======================================================================
🗑️  CLEAR WEEK PLANNING - S075
======================================================================

📅 Période: 05/01/2026 → 11/01/2026
🔍 Mode: DRY-RUN (simulation)

✅ Connecté à Intervals.icu (athlete: i151223)

📥 Récupération des événements de la semaine...
   ✅ 7 événements trouvés

🎯 7 workouts planifiés trouvés:

  1. [05/01/2026] S075-01-END-EnduranceBase-V001
  2. [06/01/2026] S075-02-INT-SweetSpotProgressif-V001
  3. [07/01/2026] S075-03-TEC-CadenceVariable-V001
  4. [08/01/2026] S075-04-FOR-ForceEndurance-V001
  5. [09/01/2026] S075-05-INT-ActivationSweetSpot-V001
  6. [10/01/2026] S075-06-END-EnduranceLongue-V001
  7. [11/01/2026] S075-07-REC-Recuperation-V001

======================================================================

🔍 DRY-RUN: Les événements ci-dessus SERAIENT supprimés
   Relancez sans --dry-run pour suppression réelle
```

#### 2. Mode Interactif (Avec Confirmation)

Demande confirmation avant de supprimer :

```bash
python scripts/maintenance/clear_week_planning.py \
  --week-id S075 \
  --start-date 2026-01-05
```

**Exemple de sortie :**
```
🎯 7 workouts planifiés trouvés:
  ...

======================================================================

⚠️  Vous allez supprimer 7 workouts planifiés
   Cette action est IRRÉVERSIBLE

Confirmer la suppression ? (oui/non): oui

🗑️  Suppression en cours...

  ✅ [1/7] Supprimé: S075-01-END-EnduranceBase-V001
  ✅ [2/7] Supprimé: S075-02-INT-SweetSpotProgressif-V001
  ...

======================================================================
📊 RÉSUMÉ
======================================================================

✅ Supprimés : 7/7

✅ Planning S075 complètement effacé !

💡 Prochaines étapes:
   1. Générer nouveau planning: wp --week-id S075 --start-date 2026-01-05
   2. Uploader workouts: wu --week-id S075 --start-date 2026-01-05
```

#### 3. Mode Automatique (Sans Confirmation)

Pour scripting ou usage en ligne de commande sans interaction :

```bash
python scripts/maintenance/clear_week_planning.py \
  --week-id S075 \
  --start-date 2026-01-05 \
  --yes
```

Supprime directement sans demander confirmation.

#### 4. Mode Verbose

Affiche détails supplémentaires (IDs, descriptions, erreurs) :

```bash
python scripts/maintenance/clear_week_planning.py \
  --week-id S075 \
  --start-date 2026-01-05 \
  --verbose
```

### Workflow Complet : Régénération de Semaine

Quand vous avez besoin de régénérer complètement une semaine :

```bash
# 1. Voir ce qui serait supprimé (dry-run)
python scripts/maintenance/clear_week_planning.py \
  --week-id S075 --start-date 2026-01-05 --dry-run

# 2. Si OK, supprimer les workouts
python scripts/maintenance/clear_week_planning.py \
  --week-id S075 --start-date 2026-01-05 --yes

# 3. Régénérer le planning
wp --week-id S075 --start-date 2026-01-05

# 4. Uploader les nouveaux workouts
wu --week-id S075 --start-date 2026-01-05
```

### Options Complètes

```
usage: clear_week_planning.py [-h] --week-id WEEK_ID --start-date START_DATE
                              [--dry-run] [--yes] [--verbose]

options:
  --week-id WEEK_ID     ID de la semaine (format SXXX, ex: S075)
  --start-date START_DATE
                        Date de début de semaine (format YYYY-MM-DD)
  --dry-run             Mode simulation (affiche ce qui serait supprimé sans supprimer)
  --yes, -y             Mode automatique (pas de confirmation)
  --verbose, -v         Mode verbose (affiche détails)
```

### Sécurité

Le script implémente plusieurs mesures de sécurité :

- ✅ **Filtre strict** : Supprime UNIQUEMENT les événements de catégorie "WORKOUT"
- ✅ **Préservation activités** : Ne touche JAMAIS aux activités réalisées (catégorie "ACTIVITY")
- ✅ **Préservation notes** : Ne touche JAMAIS aux notes de calendrier (catégorie "NOTE")
- ✅ **Dry-run par défaut** : Recommandation explicite de tester avant suppression
- ✅ **Confirmation requise** : Mode interactif demande validation explicite
- ✅ **Scope limité** : Opère uniquement sur la semaine spécifiée (7 jours)

### API Intervals.icu

Le script utilise l'API Intervals.icu via `IntervalsClient` :

- **Endpoint** : `DELETE /api/v1/athlete/{id}/events/{event_id}`
- **Authentification** : API key configurée dans `.env` ou config
- **Rate limiting** : Respecte les limites Intervals.icu
- **Gestion erreurs** : Affiche échecs et continue avec les autres événements

### Configuration

Le script utilise automatiquement la configuration Intervals.icu du projet :

```python
from cyclisme_training_logs.config import get_intervals_config

config = get_intervals_config()
# Lit INTERVALS_ATHLETE_ID et INTERVALS_API_KEY depuis .env
```

Assurez-vous que votre fichier `.env` contient :
```bash
INTERVALS_ATHLETE_ID=i151223
INTERVALS_API_KEY=your_api_key_here
```

### Alias Recommandé

Ajouter à `~/.zshrc` :
```bash
alias clear-week='python ~/cyclisme-training-logs/scripts/maintenance/clear_week_planning.py'
```

Usage :
```bash
clear-week --week-id S075 --start-date 2026-01-05 --dry-run
clear-week --week-id S075 --start-date 2026-01-05 --yes
```

### Logs et Debug

Le script utilise le logger standard du projet :

```python
from cyclisme_training_logs.api.intervals_client import IntervalsClient
# Logs dans stdout + fichiers selon configuration logging
```

Mode verbose pour debug :
```bash
python scripts/maintenance/clear_week_planning.py \
  --week-id S075 --start-date 2026-01-05 --verbose
```

### Exemples d'Erreurs

#### Aucun workout trouvé
```
✅ Aucun workout planifié trouvé pour cette semaine
   La semaine est déjà vide ou n'a jamais été planifiée
```

#### Échec de suppression
```
🗑️  Suppression en cours...

  ✅ [1/7] Supprimé: S075-01-END-EnduranceBase-V001
  ❌ [2/7] Échec: S075-02-INT-SweetSpotProgressif-V001
  ...

⚠️  Certaines suppressions ont échoué
   Relancez le script pour nettoyer les événements restants
```

#### Configuration manquante
```
❌ Erreur configuration Intervals.icu: INTERVALS_API_KEY not found
```

### Dépannage

#### Le script ne trouve aucun événement

Vérifiez :
1. La date de début est-elle correcte ? (format YYYY-MM-DD)
2. Les workouts ont-ils été uploadés sur Intervals.icu ?
3. L'API key est-elle valide ?

```bash
# Vérifier les événements manuellement
curl -u "API_i151223:your_api_key" \
  "https://intervals.icu/api/v1/athlete/i151223/events?oldest=2026-01-05&newest=2026-01-11"
```

#### Erreur d'authentification

```bash
# Vérifier config
python -c "from cyclisme_training_logs.config import get_intervals_config; print(get_intervals_config())"
```

#### Import errors

```bash
# Réinstaller le projet
poetry install
```

---

## 📚 Références

- **PEP 8** : https://peps.python.org/pep-0008/
- **PEP 257** : https://peps.python.org/pep-0257/
- **Pre-commit Hooks** : https://pre-commit.com/
- **Intervals.icu API** : https://intervals.icu/api

---

**Auteur :** Claude Code (Anthropic)
**Date :** 2026-01-04
**Version :** 1.1.0
