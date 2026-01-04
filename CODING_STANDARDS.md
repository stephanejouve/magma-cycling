# Standards de Production - Cyclisme Training Logs

**Date d'application : 2026-01-04**

## Docstrings (OBLIGATOIRE)

Tous les modules, classes, fonctions et méthodes publiques du code de production doivent respecter **PEP 257** et **Google Style**.

### ✅ Règles obligatoires

1. **Toujours terminer la première ligne par un point** (D400/D415)
   ```python
   def calculate_tss(power: int, duration: int) -> float:
       """Calculate Training Stress Score from power and duration."""
   ```

2. **Mode impératif pour les fonctions** (D401)
   ```python
   # ✅ BON
   def process_workout(data: dict) -> dict:
       """Process workout data and return metrics."""

   # ❌ MAUVAIS
   def process_workout(data: dict) -> dict:
       """Processes workout data and returns metrics."""  # Pas d'impératif
   ```

3. **Ligne blanche entre résumé et description** (D205)
   ```python
   """
   Calculate weekly training load.

   This function aggregates daily TSS values and computes
   CTL, ATL, and TSB metrics.
   """
   ```

4. **Pas de ligne blanche après la docstring** (D202)
   ```python
   def my_function():
       """Do something useful."""
       return 42  # Pas de ligne blanche ici
   ```

5. **Docstrings obligatoires** (D100, D103, D104)
   - Modules : toujours
   - Fonctions/méthodes publiques : toujours
   - Classes publiques : toujours

### 📝 Format Google Style

```python
def calculate_training_load(
    workouts: list[dict],
    athlete_profile: dict,
    start_date: str | None = None
) -> dict[str, float]:
    """Calculate training load metrics for a period.

    Aggregates workout data and computes CTL, ATL, TSB and other
    performance management metrics based on athlete's training history.

    Args:
        workouts: List of workout dictionaries with TSS and date.
        athlete_profile: Athlete configuration including FTP and thresholds.
        start_date: Optional start date (ISO format). Defaults to 42 days ago.

    Returns:
        Dictionary containing CTL, ATL, TSB, and ramp rate values.

    Raises:
        ValueError: If workouts list is empty or invalid.
        KeyError: If required athlete profile fields are missing.

    Examples:
        Basic usage::

            profile = {"ftp": 250, "weight": 70}
            workouts = [{"tss": 100, "date": "2024-01-15"}, ...]
            metrics = calculate_training_load(workouts, profile)
            print(f"CTL: {metrics['ctl']}, TSB: {metrics['tsb']}")

    Note:
        CTL and ATL use exponential moving averages with time constants
        of 42 and 7 days respectively.
    """
    # Implementation
```

## Enforcement (Application)

### Pre-commit Hooks

Le pre-commit hook `pydocstyle` est activé et bloque tout commit non conforme :

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/pycqa/pydocstyle
  rev: 6.3.0
  hooks:
    - id: pydocstyle
      args: ['--convention=google', '--add-ignore=D212']
```

### Exclusions

Les répertoires suivants sont exclus (code utilitaire/temporaire) :
- `tests/` - tests unitaires
- `scripts/debug/` - scripts de debug temporaires
- `scripts/fix_*` - scripts de migration one-shot
- `withings_integration/` - intégration externe
- `backups/` - sauvegardes
- `*patches/` - correctifs temporaires

### Vérification manuelle

```bash
# Vérifier tout le projet
poetry run pydocstyle cyclisme_training_logs/

# Vérifier un fichier spécifique
poetry run pydocstyle cyclisme_training_logs/core/data_aggregator.py

# Exécuter tous les hooks pre-commit
pre-commit run --all-files
```

## PEP 8 Compliance

Le code est **100% conforme PEP 8** avec les adaptations modernes suivantes:

### Standard Moderne (2024+)

**Longueur de ligne : 100 caractères**
- PEP 8 historique : 79 caractères (terminaux 80 colonnes)
- Standard moderne : 100 caractères (écrans larges, lisibilité accrue)
- Adopté par : Black, Google, Facebook, Instagram, Lyft, ...

**Opérateurs binaires : saut AVANT**
- PEP 8 mise à jour (2016) : saut de ligne AVANT l'opérateur
- Meilleure lisibilité (opérateur aligné à gauche)
- Adopté par Black

**Slicing : espaces selon contexte**
- Black optimise espacement pour lisibilité
- Peut ajouter espaces avant `:` dans slicing complexe

### Configuration

**Fichier :** `.pycodestyle`
```ini
[pycodestyle]
max_line_length = 100
ignore = E203,E501,W503
```

**Vérification :**
```bash
poetry run pycodestyle cyclisme_training_logs/ --ignore=E203,E501,W503
# ✅ 0 violations
```

### Exceptions Acceptées

- **E203** : Whitespace before `:` (conflit Black/slicing)
- **E501** : Line > 79 chars (acceptons 100 chars)
- **W503** : Line break before binary operator (PEP 8 mise à jour)

**Références :**
- [PEP 8 - Binary Operators](https://www.python.org/dev/peps/pep-0008/#should-a-line-break-before-or-after-a-binary-operator)
- [Black Code Style](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html)

## Autres Standards

### Code Formatting

- **Black** : formatage automatique (100 caractères/ligne)
- **Ruff** : linting Python moderne
- **isort** : tri des imports (profile black)

### Type Hints

Utiliser les type hints modernes (Python 3.11+) :

```python
# ✅ BON (Python 3.11+)
def process_data(items: list[str]) -> dict[str, int]:
    pass

# ❌ ANCIEN (Python 3.9)
from typing import List, Dict
def process_data(items: List[str]) -> Dict[str, int]:
    pass
```

## Exceptions

Pour contourner temporairement les hooks (urgence uniquement) :

```bash
git commit --no-verify -m "Emergency fix"
```

**⚠️ À utiliser avec parcimonie et corriger immédiatement après.**

## Documentation Sphinx

Reconstruire la doc après modifications des docstrings :

```bash
# Nettoyer et reconstruire
rm -rf docs/_build
sphinx-build -b html docs/ docs/_build/html

# Ouvrir dans le navigateur
open docs/_build/html/index.html
```

## Références

- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [pydocstyle Documentation](http://www.pydocstyle.org/)

---

**Mise à jour :** 2026-01-04
**Responsable :** Équipe Cyclisme Training Logs
