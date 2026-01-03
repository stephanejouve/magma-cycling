# 🏷️ PROMPT CLAUDE CODE - INTÉGRATION TAGS GARTNER TIME

**Objectif :** Intégrer le système de tags Gartner TIME dans le projet cyclisme-training-logs

**Durée estimée :** 2-3 heures

**Prérequis :**
- Documents lus : `GARTNER_TIME_INVENTORY.md` et `DOCSTRING_TEMPLATE_V2_GARTNER.md`
- Projet : `~/cyclisme-training-logs/`

---

## 🎯 MISSION

Intégrer le système de classification Gartner TIME dans le projet en 4 étapes :

1. **Créer script de validation** automatique des tags
2. **Créer documentation** architecture avec tags
3. **Ajouter tags** à 6 fichiers core (Priority 1)
4. **Valider** l'implémentation

---

## 📋 ÉTAPE 1 : CRÉER SCRIPT VALIDATION

### **Fichier à créer :** `scripts/validate_gartner_tags.py`

**Location :** `~/cyclisme-training-logs/scripts/validate_gartner_tags.py`

**Contenu :**

```python
#!/usr/bin/env python3
"""
Script de validation des tags Gartner TIME dans les docstrings.

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P2
DOCSTRING: v2

Valide que tous les fichiers Python du projet ont des docstrings conformes
au standard v2 avec tags Gartner TIME (I/T/M/E).

Examples:
    Validation complète du projet::

        poetry run python scripts/validate_gartner_tags.py

    Validation d'un fichier spécifique::

        poetry run python scripts/validate_gartner_tags.py --file workflow_coach.py

    Génération rapport HTML::

        poetry run python scripts/validate_gartner_tags.py --html report.html

Author: Claude Code
Created: 2025-12-26
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import argparse


@dataclass
class ValidationResult:
    """Résultat de validation d'un fichier."""
    file_path: Path
    valid: bool
    errors: List[str]
    warnings: List[str]
    gartner_tag: str = ""
    status: str = ""
    priority: str = ""
    docstring_version: str = ""


class GartnerTagValidator:
    """Validateur de tags Gartner TIME dans les docstrings."""

    REQUIRED_TAGS = ['GARTNER_TIME', 'STATUS', 'LAST_REVIEW', 'PRIORITY', 'DOCSTRING']
    VALID_GARTNER_VALUES = ['I', 'T', 'M', 'E']
    VALID_PRIORITIES = ['P0', 'P1', 'P2', 'P3', 'P4']

    def __init__(self, project_root: Path):
        """
        Initialiser le validateur.

        Args:
            project_root: Racine du projet Python à valider
        """
        self.project_root = project_root

    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Valider un fichier Python.

        Args:
            file_path: Chemin du fichier à valider

        Returns:
            ValidationResult avec détails de validation
        """
        errors = []
        warnings = []

        # Lire le fichier
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return ValidationResult(
                file_path=file_path,
                valid=False,
                errors=[f"Impossible de lire le fichier: {e}"],
                warnings=[]
            )

        # Parser AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return ValidationResult(
                file_path=file_path,
                valid=False,
                errors=[f"Erreur syntaxe Python: {e}"],
                warnings=[]
            )

        # Extraire docstring
        docstring = ast.get_docstring(tree)

        if not docstring:
            return ValidationResult(
                file_path=file_path,
                valid=False,
                errors=["Missing module docstring"],
                warnings=[]
            )

        # Vérifier tags requis
        result = ValidationResult(
            file_path=file_path,
            valid=True,
            errors=[],
            warnings=[]
        )

        for tag in self.REQUIRED_TAGS:
            if f'{tag}:' not in docstring:
                errors.append(f"Missing required tag: {tag}")

        # Extraire et valider GARTNER_TIME
        gartner_match = re.search(r'GARTNER_TIME:\s*([ITME])', docstring)
        if gartner_match:
            result.gartner_tag = gartner_match.group(1)
            if result.gartner_tag not in self.VALID_GARTNER_VALUES:
                errors.append(f"Invalid GARTNER_TIME value: {result.gartner_tag}")
        else:
            if 'GARTNER_TIME:' in docstring:
                errors.append("GARTNER_TIME tag present but invalid format")

        # Extraire STATUS
        status_match = re.search(r'STATUS:\s*(.+)', docstring)
        if status_match:
            result.status = status_match.group(1).strip()

        # Extraire PRIORITY
        priority_match = re.search(r'PRIORITY:\s*(P[0-4])', docstring)
        if priority_match:
            result.priority = priority_match.group(1)
            if result.priority not in self.VALID_PRIORITIES:
                errors.append(f"Invalid PRIORITY value: {result.priority}")

        # Extraire DOCSTRING version
        docstring_match = re.search(r'DOCSTRING:\s*(.+)', docstring)
        if docstring_match:
            result.docstring_version = docstring_match.group(1).strip()

        # Vérifier LAST_REVIEW format
        review_match = re.search(r'LAST_REVIEW:\s*(\d{4}-\d{2}-\d{2})', docstring)
        if not review_match and 'LAST_REVIEW:' in docstring:
            errors.append("LAST_REVIEW format incorrect (attendu: YYYY-MM-DD)")

        # Vérifier Examples section
        if 'Examples:' not in docstring:
            warnings.append("Missing Examples section")
        else:
            # Compter les code blocks (::)
            code_blocks = docstring.count('::')
            if code_blocks < 2:
                warnings.append("Examples section should have at least 2 code blocks")

        # Vérifier Author/Created
        if 'Author:' not in docstring:
            warnings.append("Missing Author metadata")
        if 'Created:' not in docstring:
            warnings.append("Missing Created metadata")

        # Vérifier tags conditionnels selon GARTNER_TIME
        if result.gartner_tag == 'M':  # Migrate
            if 'MIGRATION_TARGET:' not in docstring:
                warnings.append("GARTNER_TIME=M but no MIGRATION_TARGET tag")

        if result.gartner_tag == 'E':  # Eliminate
            if 'DEPRECATION_DATE:' not in docstring:
                warnings.append("GARTNER_TIME=E but no DEPRECATION_DATE tag")
            if 'REMOVAL_DATE:' not in docstring:
                warnings.append("GARTNER_TIME=E but no REMOVAL_DATE tag")

        if result.gartner_tag == 'T':  # Tolerate
            if 'REPLACEMENT:' not in docstring:
                warnings.append("GARTNER_TIME=T but no REPLACEMENT tag suggested")

        result.errors = errors
        result.warnings = warnings
        result.valid = len(errors) == 0

        return result

    def validate_all_files(self, pattern: str = "*.py") -> Dict[Path, ValidationResult]:
        """
        Valider tous les fichiers Python du projet.

        Args:
            pattern: Pattern de fichiers à valider (défaut: "*.py")

        Returns:
            Dict avec chemin fichier → résultat validation
        """
        results = {}

        for py_file in self.project_root.rglob(pattern):
            # Ignorer __pycache__, .venv, etc.
            if any(part.startswith('.') or part == '__pycache__' for part in py_file.parts):
                continue

            results[py_file] = self.validate_file(py_file)

        return results

    def print_report(self, results: Dict[Path, ValidationResult]):
        """
        Afficher rapport de validation dans le terminal.

        Args:
            results: Résultats de validation à afficher
        """
        print("\n" + "="*80)
        print("📊 GARTNER TIME TAGS VALIDATION REPORT")
        print("="*80 + "\n")

        # Statistiques globales
        total_files = len(results)
        valid_files = sum(1 for r in results.values() if r.valid)
        coverage_pct = (valid_files / total_files * 100) if total_files > 0 else 0

        print(f"Total files: {total_files}")
        print(f"Valid files: {valid_files} ({coverage_pct:.1f}%)")
        print(f"Invalid files: {total_files - valid_files}\n")

        # Distribution tags Gartner
        gartner_counts = {'I': 0, 'T': 0, 'M': 0, 'E': 0, 'None': 0}
        for result in results.values():
            tag = result.gartner_tag if result.gartner_tag else 'None'
            gartner_counts[tag] = gartner_counts.get(tag, 0) + 1

        print("📋 GARTNER TIME Distribution:")
        print(f"  🟢 I (Invest):   {gartner_counts['I']:3d} files")
        print(f"  🟡 T (Tolerate): {gartner_counts['T']:3d} files")
        print(f"  🔵 M (Migrate):  {gartner_counts['M']:3d} files")
        print(f"  🔴 E (Eliminate):{gartner_counts['E']:3d} files")
        print(f"  ⚠️  None:        {gartner_counts['None']:3d} files\n")

        # Fichiers avec erreurs
        files_with_errors = {f: r for f, r in results.items() if r.errors}
        if files_with_errors:
            print("❌ FILES WITH ERRORS:\n")
            for file_path, result in sorted(files_with_errors.items()):
                relative_path = file_path.relative_to(self.project_root)
                print(f"  {relative_path}")
                for error in result.errors:
                    print(f"    ❌ {error}")
                print()

        # Fichiers avec warnings
        files_with_warnings = {f: r for f, r in results.items() if r.warnings}
        if files_with_warnings:
            print("⚠️  FILES WITH WARNINGS:\n")
            for file_path, result in sorted(files_with_warnings.items()):
                relative_path = file_path.relative_to(self.project_root)
                print(f"  {relative_path}")
                for warning in result.warnings:
                    print(f"    ⚠️  {warning}")
                print()

        # Résumé final
        print("="*80)
        if valid_files == total_files:
            print("✅ ALL FILES VALID!")
        else:
            print(f"⚠️  {total_files - valid_files} file(s) need attention")
        print("="*80 + "\n")

    def generate_html_report(self, results: Dict[Path, ValidationResult], output_path: Path):
        """
        Générer rapport HTML de validation.

        Args:
            results: Résultats de validation
            output_path: Chemin du fichier HTML à générer
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Gartner TIME Tags Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-box { flex: 1; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-box.valid { background: #4CAF50; color: white; }
        .stat-box.invalid { background: #f44336; color: white; }
        .stat-box.total { background: #2196F3; color: white; }
        .distribution { margin: 20px 0; }
        .tag-bar { height: 30px; margin: 10px 0; border-radius: 5px; display: flex; align-items: center; padding-left: 10px; color: white; }
        .tag-I { background: #4CAF50; }
        .tag-T { background: #FF9800; }
        .tag-M { background: #2196F3; }
        .tag-E { background: #f44336; }
        .tag-None { background: #9E9E9E; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        tr:hover { background: #f5f5f5; }
        .error { color: #f44336; }
        .warning { color: #FF9800; }
        .valid { color: #4CAF50; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Gartner TIME Tags Validation Report</h1>
"""

        # Stats
        total_files = len(results)
        valid_files = sum(1 for r in results.values() if r.valid)
        invalid_files = total_files - valid_files
        coverage_pct = (valid_files / total_files * 100) if total_files > 0 else 0

        html += f"""
        <div class="stats">
            <div class="stat-box total">
                <h2>{total_files}</h2>
                <p>Total Files</p>
            </div>
            <div class="stat-box valid">
                <h2>{valid_files}</h2>
                <p>Valid ({coverage_pct:.1f}%)</p>
            </div>
            <div class="stat-box invalid">
                <h2>{invalid_files}</h2>
                <p>Invalid</p>
            </div>
        </div>
"""

        # Distribution
        gartner_counts = {'I': 0, 'T': 0, 'M': 0, 'E': 0, 'None': 0}
        for result in results.values():
            tag = result.gartner_tag if result.gartner_tag else 'None'
            gartner_counts[tag] = gartner_counts.get(tag, 0) + 1

        html += '<div class="distribution"><h2>📋 GARTNER TIME Distribution</h2>'
        for tag, count in gartner_counts.items():
            pct = (count / total_files * 100) if total_files > 0 else 0
            width = pct
            icon = {'I': '🟢', 'T': '🟡', 'M': '🔵', 'E': '🔴', 'None': '⚠️'}[tag]
            label = {'I': 'Invest', 'T': 'Tolerate', 'M': 'Migrate', 'E': 'Eliminate', 'None': 'No Tag'}[tag]
            html += f'<div class="tag-bar tag-{tag}" style="width: {width}%;">{icon} {label}: {count} ({pct:.1f}%)</div>'
        html += '</div>'

        # Table détails
        html += """
        <h2>📄 Detailed Results</h2>
        <table>
            <tr>
                <th>File</th>
                <th>Tag</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Version</th>
                <th>Issues</th>
            </tr>
"""

        for file_path, result in sorted(results.items()):
            relative_path = file_path.relative_to(self.project_root)
            status_class = 'valid' if result.valid else 'error'
            issues_count = len(result.errors) + len(result.warnings)

            html += f"""
            <tr>
                <td>{relative_path}</td>
                <td>{result.gartner_tag or '-'}</td>
                <td>{result.status or '-'}</td>
                <td>{result.priority or '-'}</td>
                <td>{result.docstring_version or '-'}</td>
                <td class="{status_class}">{issues_count} issue(s)</td>
            </tr>
"""

        html += """
        </table>
    </div>
</body>
</html>
"""

        output_path.write_text(html, encoding='utf-8')
        print(f"✅ HTML report generated: {output_path}")


def main():
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(
        description="Validate Gartner TIME tags in Python docstrings"
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Validate specific file instead of all project'
    )
    parser.add_argument(
        '--html',
        type=str,
        help='Generate HTML report at specified path'
    )
    parser.add_argument(
        '--project-root',
        type=str,
        default='cyclisme_training_logs',
        help='Project root directory (default: cyclisme_training_logs)'
    )

    args = parser.parse_args()

    # Déterminer project root
    if Path(args.project_root).is_absolute():
        project_root = Path(args.project_root)
    else:
        project_root = Path.cwd() / args.project_root

    if not project_root.exists():
        print(f"❌ Project root not found: {project_root}")
        sys.exit(1)

    # Créer validateur
    validator = GartnerTagValidator(project_root)

    # Valider
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = project_root / file_path

        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)

        result = validator.validate_file(file_path)
        results = {file_path: result}
    else:
        results = validator.validate_all_files()

    # Afficher rapport
    validator.print_report(results)

    # Générer HTML si demandé
    if args.html:
        html_path = Path(args.html)
        validator.generate_html_report(results, html_path)

    # Exit code selon résultats
    invalid_count = sum(1 for r in results.values() if not r.valid)
    sys.exit(0 if invalid_count == 0 else 1)


if __name__ == '__main__':
    main()
```

**Validation :**
```bash
# Test basique
poetry run python scripts/validate_gartner_tags.py

# Test fichier spécifique
poetry run python scripts/validate_gartner_tags.py --file cyclisme_training_logs/config.py

# Générer rapport HTML
poetry run python scripts/validate_gartner_tags.py --html validation_report.html
```

---

## 📋 ÉTAPE 2 : CRÉER DOCUMENTATION ARCHITECTURE

### **Fichier à créer :** `docs/ARCHITECTURE.md`

**Location :** `~/cyclisme-training-logs/docs/ARCHITECTURE.md`

**Contenu :**

```markdown
# 🏗️ ARCHITECTURE DU PROJET

**Dernière mise à jour :** 2025-12-26
**Version :** 2.0 (Post-Prompt 1 + Gartner TIME)

---

## 📊 CLASSIFICATION GARTNER TIME

Ce projet utilise le framework **Gartner TIME** pour classifier et gérer l'évolution de ses composants :

| Tag | Signification | Icône | Fichiers | Action |
|-----|---------------|-------|----------|--------|
| **I** | **Invest** - Stratégique | 🟢 | ~25 (62%) | Maintenir + Évolution |
| **T** | **Tolerate** - Legacy | 🟡 | ~8 (20%) | Maintenance minimale |
| **M** | **Migrate** - En migration | 🔵 | ~2 (5%) | Migration active |
| **E** | **Eliminate** - À supprimer | 🔴 | ~1 (2%) | Décommissionnement |

**Voir détails :** `GARTNER_TIME_INVENTORY.md`

---

## 🎯 COMPOSANTS PRINCIPAUX

### **Core Workflow** (Priority P0) 🟢

#### `workflow_coach.py` - Orchestrateur Principal
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P0 - Critical

Orchestrateur du workflow quotidien d'analyse de séance.
Guide l'utilisateur à travers : détection type session, collecte feedback,
préparation prompt, validation, insertion, commit.

Usage: poetry run workflow-coach --activity-id i123456
```

#### `config.py` - Configuration Centrale
```
GARTNER_TIME: I (Invest)
STATUS: Production (Post-fix Prompt 1)
PRIORITY: P0 - Critical
RECENT_CHANGES: DataRepoConfig + TRAINING_DATA_REPO

Séparation code/données via DataRepoConfig.
Configuration paths externes vers ~/training-logs.

Usage: Variable TRAINING_DATA_REPO=~/training-logs
```

#### `prepare_analysis.py` - Génération Prompts
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P0 - Critical

Génération prompts Coach pour analyse séance.
Collecte données Intervals.icu, feedback athlète, état workflow.

Usage: poetry run prepare-analysis --activity-id i123456
```

---

### **Insertion & Migration** (Priority P1) 🔵

#### `insert_analysis.py` - Insertion Analyses
```
GARTNER_TIME: M (Migrate)
STATUS: Migration (v1 → v2)
PRIORITY: P1 - High
MIGRATION_TARGET: core/timeline_injector.py

ACTUELLEMENT : Append-only insertion
FUTUR (Prompt 2) : Chronological injection via TimelineInjector

Usage: poetry run insert-analysis [--dry-run]
```

#### `backfill_history.py` - Backfill Historique
```
GARTNER_TIME: M (Migrate)
STATUS: Migration (v1 → v2)
PRIORITY: P2 - Medium
MIGRATION_TARGET: core/timeline_injector.py

Backfill workouts historiques depuis Intervals.icu.
DÉPEND DE : Chronological injection (Prompt 2 Phase 1)

Usage: poetry run backfill-history --start-date 2024-08-01 --limit 10
```

---

### **Intervals.icu Integration** (Priority P1-P2) 🟢

#### `sync_intervals.py` - Synchronisation
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P1 - High

Synchronisation bidirectionnelle avec Intervals.icu.
Upload workouts, download activités, sync état.

Usage: poetry run sync-intervals
```

#### `upload_workouts.py` - Upload Workouts
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P1 - High

Upload fichiers .zwo vers bibliothèque Intervals.icu.

Usage: poetry run upload-workouts workout.zwo
```

#### `planned_sessions_checker.py` - Vérification Sessions
```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P2 - Medium

Vérification cohérence sessions planifiées vs réalisées.

Usage: poetry run check-planned-sessions
```

---

### **Analysis & Planning** (Priority P2-P3) 🟡

#### `weekly_planner.py` - Planning Hebdomadaire
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Legacy)
PRIORITY: P2 - Medium
REPLACEMENT: analyzers/weekly_analyzer.py (Prompt 2 Phase 2)

Planification hebdomadaire actuelle.
SERA REMPLACÉ PAR : Système automatisé v2 (6 reports)

Usage: poetry run weekly-planner --week S073
```

#### `prepare_weekly_report.py` - Rapport Hebdomadaire
```
GARTNER_TIME: T (Tolerate)
STATUS: Production (Legacy)
PRIORITY: P3 - Low
REPLACEMENT: workflows/workflow_weekly.py (Prompt 2 Phase 2)

Préparation rapport hebdomadaire manuel.
SERA REMPLACÉ PAR : Workflow automatisé v2

Usage: poetry run prepare-weekly-report --week S073
```

---

### **AI Providers** (Priority P2) 🟢

Multi-provider AI analysis avec support :
- Mistral API (défaut)
- Claude API
- OpenAI API
- Ollama (local)
- Gemini (expérimental)

```
GARTNER_TIME: I (Invest)
STATUS: Production
PRIORITY: P2 - Medium

Tous fichiers ai_providers/*.py stratégiques.
```

---

## 🗺️ ROADMAP MIGRATIONS

### **Phase 1 : Core Infrastructure** (Semaine 1)
```
Prompt 2 Phase 1 - Création composants v2

🆕 core/timeline_injector.py → 🟢 I (Invest)
🆕 core/data_aggregator.py → 🟢 I (Invest)
🆕 core/prompt_generator.py → 🟢 I (Invest)
🆕 analyzers/daily_aggregator.py → 🟢 I (Invest)

🔵 insert_analysis.py → 🟢 I (après refactor)
🔵 backfill_history.py → 🟢 I (après refactor)
```

### **Phase 2 : Weekly Analysis** (Semaine 2)
```
Prompt 2 Phase 2 - Système hebdomadaire automatisé

🆕 analyzers/weekly_analyzer.py → 🟢 I (Invest)
🆕 analyzers/weekly_aggregator.py → 🟢 I (Invest)
🆕 workflows/workflow_weekly.py → 🟢 I (Invest)

🟡 weekly_planner.py → 🔴 E (deprecated)
🟡 prepare_weekly_report.py → 🔴 E (deprecated)
```

### **Phase 3 : Cleanup** (Semaine 3)
```
Élimination dead code

🔴 weekly_analysis.py → DELETED
🟡 Legacy utilities → ARCHIVED
```

---

## 📝 STANDARDS DOCUMENTATION

### **Docstrings v2**

Tous fichiers doivent suivre template standardisé :

```python
"""
Description concise en une ligne

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P1
DOCSTRING: v2

Description détaillée en français...

Examples:
    Command-line usage::
        poetry run command --option

    Programmatic usage::
        from module import Class
        obj = Class()
        result = obj.method()

Author: Claude Code
Created: YYYY-MM-DD
"""
```

**Voir détails :** `DOCSTRING_TEMPLATE_V2_GARTNER.md`

---

## 🔍 VALIDATION CONTINUE

### **Script de Validation**

```bash
# Valider tous fichiers
poetry run python scripts/validate_gartner_tags.py

# Rapport HTML
poetry run python scripts/validate_gartner_tags.py --html report.html
```

### **Cadence Review**

| Tag | Fréquence | Action |
|-----|-----------|--------|
| 🟢 I | Monthly | Update LAST_REVIEW |
| 🟡 T | Quarterly | Assess still needed |
| 🔵 M | Weekly | Track migration progress |
| 🔴 E | One-time | Execute elimination |

---

## 🎯 OBJECTIFS PROJET

### **Court Terme (1 mois)**
- ✅ Logs path externe (TRAINING_DATA_REPO) ← FAIT
- 🔵 Chronological injection (Prompt 2 Phase 1)
- 📝 Standardisation docstrings 6 fichiers core (Prompt 3 Priority 1)

### **Moyen Terme (2-3 mois)**
- 📊 Weekly analysis automatisé (6 reports)
- 🔄 Migration complète v1 → v2
- 📚 Documentation 100% v2

### **Long Terme (6 mois)**
- 🚀 Cycle analysis
- 📈 Position query
- 🧹 Élimination legacy complet

---

## 📊 MÉTRIQUES QUALITÉ

**Objectifs :**
- Docstring v2 coverage : 0% → 100%
- Tests passing : 273/273 (100%)
- Gartner I (Invest) : 62% → 80%
- Gartner T/E (Legacy) : 22% → 5%

**Suivi :**
```bash
poetry run python scripts/validate_gartner_tags.py
```

---

**Version :** 2.0
**Dernière mise à jour :** 2025-12-26
**Prochaine révision :** Post-Prompt 2 Phase 1
```

---

## 📋 ÉTAPE 3 : AJOUTER TAGS AUX FICHIERS CORE (Priority 1)

### **Fichiers à modifier (6 fichiers) :**

1. `cyclisme_training_logs/workflow_coach.py`
2. `cyclisme_training_logs/prepare_analysis.py`
3. `cyclisme_training_logs/insert_analysis.py`
4. `cyclisme_training_logs/backfill_history.py`
5. `cyclisme_training_logs/manage_state.py`
6. `cyclisme_training_logs/config.py`

### **Transformation à appliquer :**

Pour CHAQUE fichier, **REMPLACER** le docstring actuel par le template v2 :

#### **Template Standard (Production)**

```python
"""
[Description concise existante en une ligne]

GARTNER_TIME: I
STATUS: Production
LAST_REVIEW: 2025-12-26
PRIORITY: P0
DOCSTRING: v2

[Description détaillée existante en français - préserver texte actuel]

Examples:
    Command-line usage::

        [Exemples réels d'utilisation du script]

    Programmatic usage::

        from cyclisme_training_logs.[module] import [Class]

        obj = [Class](param="value")
        result = obj.method()

Author: Claude Code
Created: [Date originale si présente, sinon 2024-11-XX]
Updated: 2025-12-26 (Added Gartner TIME tags)
"""
```

#### **Template Migration (Pour insert_analysis.py et backfill_history.py)**

```python
"""
[Description concise]

GARTNER_TIME: M
STATUS: Migration (v1 → v2)
LAST_REVIEW: 2025-12-26
PRIORITY: P1
MIGRATION_TARGET: core/timeline_injector.py
DEPRECATION_PLAN: Refactor with TimelineInjector after Prompt 2 Phase 1
DOCSTRING: v2

[Description détaillée]

Examples:
    Current usage (v1)::

        [Exemples actuels]

    Future usage (v2) - After migration::

        from cyclisme_training_logs.core.timeline_injector import TimelineInjector

        injector = TimelineInjector()
        injector.insert_chronologically(workout_data)

Author: Claude Code
Created: [Date originale]
Updated: 2025-12-26 (Added Gartner TIME tags - Migration status)
"""
```

### **Règles Importantes :**

1. **PRÉSERVER** le texte français existant dans description
2. **AJOUTER** section Examples avec code réaliste et exécutable
3. **INCLURE** tous imports nécessaires dans Examples
4. **RESPECTER** le format exact des tags (GARTNER_TIME: I, pas I:)
5. **UTILISER** PRIORITY selon inventaire :
   - workflow_coach.py : P0
   - prepare_analysis.py : P0
   - config.py : P0
   - insert_analysis.py : P1 (GARTNER_TIME: M)
   - backfill_history.py : P2 (GARTNER_TIME: M)
   - manage_state.py : P1

---

## 📋 ÉTAPE 4 : VALIDATION

### **4.1. Exécuter Script Validation**

```bash
# Valider les 6 fichiers modifiés
poetry run python scripts/validate_gartner_tags.py --file cyclisme_training_logs/workflow_coach.py
poetry run python scripts/validate_gartner_tags.py --file cyclisme_training_logs/prepare_analysis.py
poetry run python scripts/validate_gartner_tags.py --file cyclisme_training_logs/config.py
poetry run python scripts/validate_gartner_tags.py --file cyclisme_training_logs/insert_analysis.py
poetry run python scripts/validate_gartner_tags.py --file cyclisme_training_logs/backfill_history.py
poetry run python scripts/validate_gartner_tags.py --file cyclisme_training_logs/manage_state.py

# Validation complète projet
poetry run python scripts/validate_gartner_tags.py
```

**Résultat attendu :**
```
✅ Valid: 6/6 files (100%)

📋 GARTNER TIME Distribution:
  🟢 I (Invest):   4 files
  🔵 M (Migrate):  2 files
```

### **4.2. Vérifier Tests Passent**

```bash
poetry run pytest
```

**Résultat attendu :**
```
✅ 273 tests passing
```

### **4.3. Générer Rapport HTML**

```bash
poetry run python scripts/validate_gartner_tags.py --html validation_report.html
```

**Résultat attendu :**
```
✅ HTML report generated: validation_report.html
```

### **4.4. Git Commit**

```bash
cd ~/cyclisme-training-logs

# Ajouter nouveaux fichiers
git add scripts/validate_gartner_tags.py
git add docs/ARCHITECTURE.md

# Ajouter fichiers modifiés
git add cyclisme_training_logs/workflow_coach.py
git add cyclisme_training_logs/prepare_analysis.py
git add cyclisme_training_logs/config.py
git add cyclisme_training_logs/insert_analysis.py
git add cyclisme_training_logs/backfill_history.py
git add cyclisme_training_logs/manage_state.py

# Commit
git commit -m "feat: integrate Gartner TIME classification system

- Add validate_gartner_tags.py script with HTML reporting
- Add ARCHITECTURE.md with Gartner TIME overview
- Add Gartner TIME tags to 6 core files (Priority 1)
  - workflow_coach.py (I/P0)
  - prepare_analysis.py (I/P0)
  - config.py (I/P0)
  - manage_state.py (I/P1)
  - insert_analysis.py (M/P1)
  - backfill_history.py (M/P2)
- All docstrings upgraded to v2 standard with Examples
- Validation: 6/6 files passing (100%)
- Tests: 273/273 passing (100%)

Related: GARTNER_TIME_INVENTORY.md, DOCSTRING_TEMPLATE_V2_GARTNER.md"
```

---

## ✅ CRITÈRES DE SUCCÈS

### **Script Validation**
- [x] `scripts/validate_gartner_tags.py` créé et fonctionnel
- [x] Validation fichier unique fonctionne
- [x] Validation projet complet fonctionne
- [x] Génération rapport HTML fonctionne
- [x] Exit code 0 si tous fichiers valides

### **Documentation**
- [x] `docs/ARCHITECTURE.md` créé
- [x] Overview Gartner TIME présent
- [x] Roadmap migrations documentée
- [x] Standards docstrings v2 expliqués

### **Fichiers Core Modifiés**
- [x] 6 fichiers ont tags Gartner TIME
- [x] Docstrings suivent template v2
- [x] Section Examples présente et réaliste
- [x] Tags PRIORITY corrects (P0/P1/P2)
- [x] Tags GARTNER_TIME corrects (I ou M)
- [x] LAST_REVIEW = 2025-12-26

### **Validation**
- [x] Script validation tous fichiers : 6/6 (100%)
- [x] Tests pytest : 273/273 passing
- [x] Rapport HTML généré sans erreur
- [x] Git commit avec message descriptif

### **Qualité Code**
- [x] Imports corrects dans Examples
- [x] Code Examples exécutable
- [x] Pas de typos dans tags
- [x] Format dates YYYY-MM-DD
- [x] Texte français préservé

---

## 📊 RÉSULTATS ATTENDUS

### **Avant Prompt**
```
Docstring v2 coverage: 0/40 (0%)
Gartner TIME tags: 0/40 (0%)
Validation script: ❌ Absent
Documentation: ❌ Absente
```

### **Après Prompt**
```
Docstring v2 coverage: 6/40 (15%)
Gartner TIME tags: 6/40 (15%)
Validation script: ✅ Présent et fonctionnel
Documentation: ✅ ARCHITECTURE.md complet

Fichiers P0 (Critical): 3/3 (100%) ✅
Fichiers P1 (High): 2/3 (67%)
Fichiers P2 (Medium): 1/1 (100%) ✅
```

---

## 🚀 ÉTAPES SUIVANTES (Après ce Prompt)

### **Prompt 2 Phase 1 : Migration v2 Core**
- Créer `core/timeline_injector.py` (nouveau, tag I)
- Créer `core/data_aggregator.py` (nouveau, tag I)
- Refactor `insert_analysis.py` (M → I)
- Refactor `backfill_history.py` (M → I)

### **Prompt 3 Priority 2 : Standardisation Suite**
- 15 fichiers restants (P1-P2)
- Ajout tags Gartner TIME
- Docstrings v2 complètes

---

## 📝 NOTES IMPORTANTES

### **Préserver Code Existant**
- ❌ NE PAS modifier la logique Python existante
- ✅ SEULEMENT modifier les docstrings
- ✅ AJOUTER tags dans docstrings
- ✅ AJOUTER section Examples

### **Exemples Réalistes**
- ✅ Code doit être exécutable
- ✅ Imports doivent être corrects
- ✅ Au moins 2 examples par fichier
- ✅ Commentaires si utiles

### **Tags Exacts**
```
CORRECT ✅ :  GARTNER_TIME: I
INCORRECT ❌: GARTNER_TIME=I
INCORRECT ❌: I (Invest)
INCORRECT ❌: gartner_time: i
```

### **Git Commit**
- Un seul commit pour tout le travail
- Message descriptif avec bullet points
- Mentionner fichiers modifiés
- Inclure métriques validation

---

## 🎯 RÉSUMÉ MISSION

**Tu dois :**

1. ✅ Créer `scripts/validate_gartner_tags.py` (script complet fourni)
2. ✅ Créer `docs/ARCHITECTURE.md` (contenu complet fourni)
3. ✅ Modifier 6 fichiers core avec tags Gartner TIME (templates fournis)
4. ✅ Valider avec script (commandes fournies)
5. ✅ Git commit (message fourni)

**Temps estimé :** 2-3 heures

**Résultat attendu :** 6 fichiers core avec docstrings v2 + tags Gartner TIME ✅

---

**Prêt à exécuter ?** 🚀
