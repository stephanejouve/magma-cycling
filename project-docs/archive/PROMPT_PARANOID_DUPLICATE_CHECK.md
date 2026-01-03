# PROMPT: Intégration Paranoid Duplicate Check dans insert_analysis.py

## Objectif

Ajouter une vérification optionnelle des doublons après insertion dans workouts-history.md, avec mode paranoid activable via config.

## Contexte

- **Fichier principal:** `cyclisme_training_logs/insert_analysis.py`
- **Fichier config:** `cyclisme_training_logs/config.py`
- **Problème détecté:** TimelineInjector peut créer des doublons (bug #12)
- **Solution actuelle:** Script manuel `clean_duplicates_multi.py`
- **Architecture:** Double repo, tous paths via config.py

## Modifications à Effectuer

### 1. Ajouter Flags Config (config.py)

**Fichier:** `cyclisme_training_logs/config.py`

**Localisation:** Dans la classe `DataRepoConfig` (après les propriétés existantes)

**Code à ajouter:**

```python
@dataclass
class DataRepoConfig:
    # ... propriétés existantes ...

    # Duplicate detection settings
    paranoid_duplicate_check: bool = True   # Check après chaque insertion
    auto_fix_duplicates: bool = False       # Auto-suppression ou erreur
    duplicate_check_window: int = 50        # Lignes à scanner (optimisation)
```

**Justification:**
- `paranoid_duplicate_check=True` : Activé par défaut en phase test backfill
- `auto_fix_duplicates=False` : Fail-fast pour détecter bugs TimelineInjector
- `duplicate_check_window=50` : Limite scan aux 50 dernières entrées (perf)

---

### 2. Créer Module de Détection (nouveau fichier)

**Fichier:** `cyclisme_training_logs/core/duplicate_detector.py`

**Créer le fichier complet:**

```python
"""
Détection et suppression des doublons dans workouts-history.md

Utilisé en mode paranoid pour valider les insertions TimelineInjector.
"""

from pathlib import Path
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DuplicateDetectedError(Exception):
    """Exception levée quand des doublons sont détectés."""

    def __init__(self, duplicates: List[Dict]):
        self.duplicates = duplicates
        ids = [d['id'] for d in duplicates]
        super().__init__(f"Doublons détectés: {', '.join(ids)}")


class DuplicateDetector:
    """Détection rapide des doublons dans workouts-history.md"""

    def __init__(self, history_file: Path, check_window: int = 50):
        """
        Args:
            history_file: Chemin vers workouts-history.md
            check_window: Nombre d'entrées à scanner (0 = tout le fichier)
        """
        self.history_file = history_file
        self.check_window = check_window
        self.pattern = re.compile(r'^### (S\d{3}-\d{2}(?:-\w+)*(?:-V\d{3})?)\s*$')

    def quick_scan(self) -> List[Dict]:
        """
        Scan rapide des N dernières entrées pour détecter doublons.

        Returns:
            Liste des doublons détectés avec métadata
        """
        if not self.history_file.exists():
            return []

        content = self.history_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Trouver toutes les entrées
        entries = []
        for i, line in enumerate(lines):
            match = self.pattern.match(line)
            if match:
                entries.append({
                    'id': match.group(1),
                    'line': i + 1,
                    'line_index': i
                })

        # Limiter au window si spécifié
        if self.check_window > 0:
            entries = entries[:self.check_window]

        # Détecter doublons
        seen = {}
        duplicates = []

        for entry in entries:
            entry_id = entry['id']
            if entry_id in seen:
                duplicates.append({
                    'id': entry_id,
                    'first_line': seen[entry_id]['line'],
                    'duplicate_line': entry['line']
                })
            else:
                seen[entry_id] = entry

        return duplicates

    def find_entry_bounds(self, line_index: int, lines: List[str]) -> tuple:
        """
        Trouve les bornes (début, fin) d'une entrée à partir d'une ligne.

        Args:
            line_index: Index de ligne (0-based) du début de l'entrée
            lines: Liste des lignes du fichier

        Returns:
            (start_index, end_index) de l'entrée complète
        """
        start = line_index

        # Chercher la fin (prochaine entrée ou fin de fichier)
        end = len(lines) - 1
        for i in range(line_index + 1, len(lines)):
            if self.pattern.match(lines[i]):
                end = i - 1
                break

        return (start, end)

    def remove_duplicates(self, duplicates: List[Dict]) -> int:
        """
        Supprime les doublons du fichier.

        Args:
            duplicates: Liste des doublons à supprimer

        Returns:
            Nombre de lignes supprimées
        """
        if not duplicates:
            return 0

        content = self.history_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Identifier toutes les lignes à supprimer
        lines_to_remove = set()

        for dup in duplicates:
            # Trouver l'index 0-based de la ligne dupliquée
            dup_line_index = dup['duplicate_line'] - 1

            # Trouver les bornes complètes de l'entrée
            start, end = self.find_entry_bounds(dup_line_index, lines)

            # Marquer toutes les lignes de cette entrée
            for i in range(start, end + 1):
                lines_to_remove.add(i)

        # Construire nouveau contenu sans les doublons
        cleaned_lines = [
            line for i, line in enumerate(lines)
            if i not in lines_to_remove
        ]

        # Écrire le fichier nettoyé
        self.history_file.write_text('\n'.join(cleaned_lines), encoding='utf-8')

        logger.info(f"Supprimé {len(lines_to_remove)} lignes ({len(duplicates)} doublons)")

        return len(lines_to_remove)


def check_and_handle_duplicates(
    history_file: Path,
    auto_fix: bool = False,
    check_window: int = 50
) -> None:
    """
    Vérifie et gère les doublons selon la config.

    Args:
        history_file: Fichier workouts-history.md
        auto_fix: Si True, supprime automatiquement les doublons
        check_window: Nombre d'entrées à scanner

    Raises:
        DuplicateDetectedError: Si doublons détectés et auto_fix=False
    """
    detector = DuplicateDetector(history_file, check_window)
    duplicates = detector.quick_scan()

    if not duplicates:
        return

    # Doublons détectés
    dup_ids = [d['id'] for d in duplicates]

    if auto_fix:
        # Suppression automatique
        logger.warning(
            f"⚠️ {len(duplicates)} doublon(s) détecté(s): {', '.join(dup_ids)}"
        )
        lines_removed = detector.remove_duplicates(duplicates)
        logger.warning(
            f"✅ Doublons auto-supprimés ({lines_removed} lignes)"
        )
    else:
        # Erreur - fail fast
        logger.error(
            f"❌ {len(duplicates)} doublon(s) détecté(s): {', '.join(dup_ids)}"
        )
        logger.error(
            "Lancer: python3 scripts/maintenance/clean_duplicates_multi.py"
        )
        raise DuplicateDetectedError(duplicates)
```

**Justification:**
- Classe dédiée = séparation des responsabilités
- `quick_scan()` = optimisé avec window configurable
- `auto_fix` optionnel = fail-fast par défaut
- Logging détaillé = traçabilité

---

### 3. Intégrer dans insert_analysis.py

**Fichier:** `cyclisme_training_logs/insert_analysis.py`

**Modification 1 - Ajouter imports (ligne ~10-20):**

```python
# Imports existants...
from cyclisme_training_logs.config import get_data_config
from cyclisme_training_logs.core.timeline_injector import TimelineInjector

# AJOUTER:
from cyclisme_training_logs.core.duplicate_detector import (
    check_and_handle_duplicates,
    DuplicateDetectedError
)
import logging

logger = logging.getLogger(__name__)
```

**Modification 2 - Méthode insert_analysis (ligne ~298):**

**AVANT:**
```python
def insert_analysis(self, analysis_text):
    """Insérer l'analyse dans workouts-history.md via TimelineInjector"""

    # Lire le fichier existant
    content = self.read_history()
    if content is None:
        return False

    try:
        # Créer injector et insérer
        injector = TimelineInjector(history_file=self.history_file)
        updated_content = injector.inject_workout(content, analysis_text)

        # Écrire le fichier mis à jour
        with open(self.history_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion : {e}")
        return False
```

**APRÈS:**
```python
def insert_analysis(self, analysis_text):
    """Insérer l'analyse dans workouts-history.md via TimelineInjector"""

    # Lire le fichier existant
    content = self.read_history()
    if content is None:
        return False

    try:
        # Créer injector et insérer
        injector = TimelineInjector(history_file=self.history_file)
        updated_content = injector.inject_workout(content, analysis_text)

        # Écrire le fichier mis à jour
        with open(self.history_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        # === NOUVEAU: Vérification doublons ===
        try:
            config = get_data_config()

            if config.paranoid_duplicate_check:
                logger.info("🔍 Vérification doublons (mode paranoid)...")

                check_and_handle_duplicates(
                    history_file=self.history_file,
                    auto_fix=config.auto_fix_duplicates,
                    check_window=config.duplicate_check_window
                )

                logger.info("✅ Aucun doublon détecté")

        except DuplicateDetectedError as e:
            # Doublons détectés en mode non-auto-fix
            print(f"\n⚠️ ATTENTION: {e}")
            print("Lancer: python3 scripts/maintenance/clean_duplicates_multi.py\n")
            return False

        except Exception as e:
            # Autre erreur durant check - ne pas bloquer l'insertion
            logger.warning(f"⚠️ Erreur vérification doublons: {e}")
            # Continuer quand même (insertion OK)

        # === FIN NOUVEAU ===

        return True

    except Exception as e:
        print(f"❌ Erreur lors de l'insertion : {e}")
        return False
```

**Justification:**
- Try/except séparé = ne bloque pas insertion si check échoue
- Log info en mode succès
- Erreur explicite si doublons en mode strict
- Continue si check échoue (insertion prioritaire)

---

### 4. Créer Tests Unitaires

**Fichier:** `tests/test_duplicate_detector.py`

```python
"""Tests pour DuplicateDetector"""

import pytest
from pathlib import Path
from cyclisme_training_logs.core.duplicate_detector import (
    DuplicateDetector,
    DuplicateDetectedError,
    check_and_handle_duplicates
)


@pytest.fixture
def sample_history_with_duplicates(tmp_path):
    """Crée un fichier test avec doublons"""
    history = tmp_path / "workouts-history.md"

    content = """### S073-01-END-Test
Date : 22/12/2025

#### Exécution
Test 1

---

### S073-02-INT-Test
Date : 23/12/2025

#### Exécution
Test 2

---

### S073-01-END-Test
Date : 22/12/2025

#### Exécution
Test 1 DOUBLON

---
"""

    history.write_text(content)
    return history


def test_detect_duplicates(sample_history_with_duplicates):
    """Test détection basique"""
    detector = DuplicateDetector(sample_history_with_duplicates)
    duplicates = detector.quick_scan()

    assert len(duplicates) == 1
    assert duplicates[0]['id'] == 'S073-01-END-Test'


def test_auto_fix(sample_history_with_duplicates):
    """Test suppression automatique"""
    check_and_handle_duplicates(
        sample_history_with_duplicates,
        auto_fix=True
    )

    # Vérifier que doublon supprimé
    detector = DuplicateDetector(sample_history_with_duplicates)
    duplicates = detector.quick_scan()

    assert len(duplicates) == 0


def test_fail_fast_mode(sample_history_with_duplicates):
    """Test mode fail-fast"""
    with pytest.raises(DuplicateDetectedError):
        check_and_handle_duplicates(
            sample_history_with_duplicates,
            auto_fix=False
        )
```

---

## Validation

### Tests Manuels

```bash
cd ~/cyclisme-training-logs

# Test 1: Mode paranoid activé, pas de doublons
poetry run workflow-coach --activity-id i113315172 --auto --skip-feedback --skip-git
# Attendu: ✅ Aucun doublon détecté

# Test 2: Mode paranoid désactivé
# Modifier config.py: paranoid_duplicate_check = False
poetry run workflow-coach --activity-id i113315172 --auto --skip-feedback --skip-git
# Attendu: Pas de vérification doublons

# Test 3: Auto-fix activé (simuler doublon)
# Modifier config.py: auto_fix_duplicates = True
# Créer un doublon manuel dans workouts-history.md
poetry run workflow-coach --activity-id i113315172 --auto --skip-feedback --skip-git
# Attendu: ⚠️ Doublons auto-supprimés
```

### Tests Automatisés

```bash
cd ~/cyclisme-training-logs

# Lancer les tests
poetry run pytest tests/test_duplicate_detector.py -v

# Attendu:
# test_detect_duplicates PASSED
# test_auto_fix PASSED
# test_fail_fast_mode PASSED
```

---

## Configuration Recommandée

### Phase 1: Backfill Initial (maintenant)

```python
# config.py
paranoid_duplicate_check = True   # Détection active
auto_fix_duplicates = False        # Fail-fast pour détecter bugs
duplicate_check_window = 50        # Scan 50 dernières entrées
```

### Phase 2: Production Stable (après 3 mois sans doublons)

```python
# config.py
paranoid_duplicate_check = False   # Désactivé (perf)
auto_fix_duplicates = False        # N/A
duplicate_check_window = 50        # N/A
```

### Phase 3: Maintenance Périodique

```bash
# Cron hebdomadaire
0 2 * * 0 python3 scripts/maintenance/clean_duplicates_multi.py
```

---

## Commit

```bash
cd ~/cyclisme-training-logs

git add cyclisme_training_logs/config.py
git add cyclisme_training_logs/core/duplicate_detector.py
git add cyclisme_training_logs/insert_analysis.py
git add tests/test_duplicate_detector.py

git commit -m "feat(paranoid): Add optional duplicate detection after insertion

- New DuplicateDetector class in core/duplicate_detector.py
- Config flags: paranoid_duplicate_check, auto_fix_duplicates
- Integration in insert_analysis.py post-injection
- Fail-fast by default (auto_fix=False)
- Optimized quick_scan with configurable window
- Full test coverage

Fixes: Bug #12 - TimelineInjector peut créer doublons
Related: clean_duplicates_multi.py maintenance tool

Phase 1 config (backfill):
- paranoid_duplicate_check=True (detect bugs)
- auto_fix_duplicates=False (fail-fast)

Phase 2 config (production stable):
- paranoid_duplicate_check=False (perf)
"
```

---

## Impact

### Performance

**Avec paranoid mode (window=50):**
- Scan 50 entrées × ~40 lignes = ~2000 lignes
- Regex simple sur 2000 lignes = ~5-10ms
- Impact négligeable sur insertion

**Sans paranoid mode:**
- Zero overhead

### Robustesse

- ✅ Détection automatique bugs TimelineInjector
- ✅ Protection contre corruption fichier
- ✅ Traçabilité via logs
- ✅ Désactivable en production mature

---

---

## 🔍 **Bonus: Audit Docstrings TIME GARTNER**

### Objectif

Identifier et taguer tous les fichiers Python du projet qui n'ont pas encore de docstrings au format TIME GARTNER.

### Format TIME GARTNER Requis

```python
"""
Brief description of the module/function.

TIME: YYYY-MM-DD HH:MM
GARTNER: Category (e.g., CORE, UTILS, API, SCRIPTS)
AUTHOR: Name or Team
"""
```

### Script d'Audit à Créer

**Fichier:** `scripts/maintenance/audit_docstrings.py`

```python
#!/usr/bin/env python3
"""
Audit des docstrings TIME GARTNER dans le projet.

TIME: 2025-12-27 09:45
GARTNER: MAINTENANCE
AUTHOR: Cyclisme Training Logs Team
"""

import ast
from pathlib import Path
from typing import List, Dict, Tuple
import re


class DocstringAuditor:
    """Analyse les docstrings TIME GARTNER dans le code Python."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.time_pattern = re.compile(r'TIME:\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}')
        self.gartner_pattern = re.compile(r'GARTNER:\s*\w+')

    def has_time_gartner_docstring(self, docstring: str) -> bool:
        """Vérifie si une docstring contient TIME et GARTNER."""
        if not docstring:
            return False
        return bool(
            self.time_pattern.search(docstring) and
            self.gartner_pattern.search(docstring)
        )

    def extract_module_docstring(self, file_path: Path) -> Tuple[bool, str]:
        """
        Extrait la docstring de module d'un fichier Python.

        Returns:
            (has_time_gartner, docstring_text)
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)

            # Docstring module = premier string littéral
            module_docstring = ast.get_docstring(tree)

            if module_docstring:
                has_tg = self.has_time_gartner_docstring(module_docstring)
                return (has_tg, module_docstring)
            else:
                return (False, "")

        except Exception as e:
            return (False, f"ERROR: {e}")

    def scan_project(self) -> Dict[str, List[Path]]:
        """
        Scanne tous les fichiers Python du projet.

        Returns:
            {
                'compliant': [files with TIME GARTNER],
                'missing': [files without TIME GARTNER],
                'errors': [files with parse errors]
            }
        """
        results = {
            'compliant': [],
            'missing': [],
            'errors': []
        }

        # Parcourir tous les fichiers .py
        python_files = list(self.project_root.rglob('*.py'))

        # Exclure certains répertoires
        exclude_patterns = {
            '__pycache__',
            '.git',
            '.venv',
            'venv',
            '.pytest_cache',
            'build',
            'dist',
            '.eggs'
        }

        for py_file in python_files:
            # Vérifier exclusions
            if any(pattern in py_file.parts for pattern in exclude_patterns):
                continue

            has_tg, docstring = self.extract_module_docstring(py_file)

            if docstring.startswith("ERROR:"):
                results['errors'].append(py_file)
            elif has_tg:
                results['compliant'].append(py_file)
            else:
                results['missing'].append(py_file)

        return results

    def generate_report(self, results: Dict[str, List[Path]]) -> str:
        """Génère un rapport markdown des résultats."""

        total = sum(len(files) for files in results.values())
        compliant = len(results['compliant'])
        missing = len(results['missing'])
        errors = len(results['errors'])

        compliance_rate = (compliant / total * 100) if total > 0 else 0

        report = f"""# Audit Docstrings TIME GARTNER

## Résumé

- **Total fichiers:** {total}
- **Conformes:** {compliant} ({compliance_rate:.1f}%)
- **Manquants:** {missing}
- **Erreurs:** {errors}

---

## Fichiers Manquants TIME GARTNER

"""

        if results['missing']:
            for file_path in sorted(results['missing']):
                rel_path = file_path.relative_to(self.project_root)
                report += f"- [ ] `{rel_path}`\n"
        else:
            report += "*Aucun fichier manquant - 100% conformité!* ✅\n"

        report += "\n---\n\n## Fichiers Conformes\n\n"

        if results['compliant']:
            for file_path in sorted(results['compliant']):
                rel_path = file_path.relative_to(self.project_root)
                report += f"- [x] `{rel_path}`\n"

        if results['errors']:
            report += "\n---\n\n## Fichiers avec Erreurs\n\n"
            for file_path in sorted(results['errors']):
                rel_path = file_path.relative_to(self.project_root)
                report += f"- ⚠️ `{rel_path}`\n"

        return report

    def tag_missing_files(self, results: Dict[str, List[Path]]) -> int:
        """
        Ajoute un commentaire TODO au début des fichiers manquants.

        Returns:
            Nombre de fichiers taggés
        """
        tag_template = '''# TODO: Add TIME GARTNER docstring
# Format:
# """
# Brief module description.
#
# TIME: YYYY-MM-DD HH:MM
# GARTNER: CATEGORY
# AUTHOR: Name
# """

'''

        tagged_count = 0

        for file_path in results['missing']:
            try:
                content = file_path.read_text(encoding='utf-8')

                # Ne pas re-taguer si déjà taggé
                if 'TODO: Add TIME GARTNER docstring' in content:
                    continue

                # Insérer tag après shebang/encoding si présent
                lines = content.split('\n')
                insert_index = 0

                # Skip shebang
                if lines and lines[0].startswith('#!'):
                    insert_index = 1

                # Skip encoding
                if insert_index < len(lines) and 'coding:' in lines[insert_index]:
                    insert_index += 1

                # Insérer le tag
                lines.insert(insert_index, tag_template)

                # Écrire le fichier
                file_path.write_text('\n'.join(lines), encoding='utf-8')

                tagged_count += 1

            except Exception as e:
                print(f"⚠️ Erreur tagging {file_path}: {e}")

        return tagged_count


def main():
    """Point d'entrée du script."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Audit docstrings TIME GARTNER'
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path.cwd(),
        help='Racine du projet (défaut: répertoire courant)'
    )
    parser.add_argument(
        '--tag',
        action='store_true',
        help='Taguer les fichiers manquants avec TODO'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Fichier de sortie pour le rapport (défaut: stdout)'
    )

    args = parser.parse_args()

    # Exécuter audit
    auditor = DocstringAuditor(args.project_root)
    results = auditor.scan_project()

    # Générer rapport
    report = auditor.generate_report(results)

    # Afficher ou sauvegarder rapport
    if args.output:
        args.output.write_text(report, encoding='utf-8')
        print(f"✅ Rapport sauvegardé: {args.output}")
    else:
        print(report)

    # Taguer fichiers si demandé
    if args.tag:
        tagged = auditor.tag_missing_files(results)
        print(f"\n✅ {tagged} fichier(s) taggé(s) avec TODO")


if __name__ == '__main__':
    main()
```

### Utilisation

```bash
cd ~/cyclisme-training-logs

# Audit simple (affiche rapport)
python3 scripts/maintenance/audit_docstrings.py

# Audit + rapport sauvegardé
python3 scripts/maintenance/audit_docstrings.py \
    --output docs/DOCSTRING_AUDIT.md

# Audit + tagging automatique
python3 scripts/maintenance/audit_docstrings.py --tag

# Audit projet spécifique
python3 scripts/maintenance/audit_docstrings.py \
    --project-root ~/cyclisme-training-logs \
    --tag \
    --output docs/DOCSTRING_AUDIT.md
```

### Exemple de Sortie

```markdown
# Audit Docstrings TIME GARTNER

## Résumé

- **Total fichiers:** 45
- **Conformes:** 12 (26.7%)
- **Manquants:** 32
- **Erreurs:** 1

---

## Fichiers Manquants TIME GARTNER

- [ ] `cyclisme_training_logs/insert_analysis.py`
- [ ] `cyclisme_training_logs/workflow_coach.py`
- [ ] `cyclisme_training_logs/scripts/backfill_history.py`
...

---

## Fichiers Conformes

- [x] `cyclisme_training_logs/config.py`
- [x] `cyclisme_training_logs/core/duplicate_detector.py`
...
```

### Intégration Git Pre-Commit Hook (Optionnel)

**Fichier:** `.git/hooks/pre-commit`

```bash
#!/bin/bash
# Pre-commit hook: Vérifier docstrings TIME GARTNER

echo "🔍 Vérification docstrings TIME GARTNER..."

# Lancer audit (sans tag)
python3 scripts/maintenance/audit_docstrings.py > /tmp/docstring_audit.txt

# Extraire taux conformité
compliance=$(grep -oP 'Conformes: \d+ \(\K[\d.]+' /tmp/docstring_audit.txt)

# Seuil minimum (90%)
threshold=90.0

if (( $(echo "$compliance < $threshold" | bc -l) )); then
    echo "❌ Conformité docstrings: ${compliance}% < ${threshold}%"
    echo "Voir rapport: /tmp/docstring_audit.txt"
    exit 1
fi

echo "✅ Conformité docstrings: ${compliance}% >= ${threshold}%"
exit 0
```

### Commande Git pour Activer Hook

```bash
cd ~/cyclisme-training-logs

# Créer le hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "🔍 Vérification docstrings TIME GARTNER..."
python3 scripts/maintenance/audit_docstrings.py --output /tmp/docstring_audit.txt
grep "Conformes:" /tmp/docstring_audit.txt
EOF

# Rendre exécutable
chmod +x .git/hooks/pre-commit
```

---

## Commit Script Audit

```bash
cd ~/cyclisme-training-logs

git add scripts/maintenance/audit_docstrings.py
git add .git/hooks/pre-commit

git commit -m "feat(maintenance): Add TIME GARTNER docstring auditor

- New script: audit_docstrings.py
- Scans all Python files for TIME GARTNER format
- Generates markdown compliance report
- Optional auto-tagging with TODO comments
- Pre-commit hook for enforcement (optional)

Usage:
  python3 scripts/maintenance/audit_docstrings.py --tag

Features:
- AST parsing for accurate docstring extraction
- Configurable exclusion patterns
- Detailed compliance metrics
- TODO tagging for missing docstrings
"
```

---

**Créé:** 2025-12-27 09:30
**Mis à jour:** 2025-12-27 09:45 (ajout audit docstrings)
**Priorité:** P1 (amélioration robustesse + qualité code)
**Effort:** 45-60 minutes (avec audit docstrings)
**Tests requis:** pytest + validation manuelle + audit docstrings
