# FEATURE: Ajouter --force-reanalyze à backfill_history.py

## Contexte

Après fix P0 (commit af47692), les 3 activités août 2024 analysées dans le mauvais repo sont toujours marquées comme "analysées" dans `.workflow_state.json`.

Backfill dry-run montre:
```
Total activités: 1
Déjà analysées: 0
À analyser: 0  # ❌ Devrait être 1
```

## Solution Requise

Ajouter flag `--force-reanalyze` qui ignore l'état `workflow_state.json` et force la réanalyse.

---

## Implémentation

### Fichier: `cyclisme_training_logs/scripts/backfill_history.py`

**1. Ajouter argument CLI:**

```python
# Ligne ~520 (dans argparse setup)
parser.add_argument(
    '--force-reanalyze',
    action='store_true',
    help='Force re-analyze activities even if already in workflow state'
)
```

**2. Modifier __init__:**

```python
# Ligne ~76
def __init__(
    self,
    provider: str = "mistral_api",
    batch_size: int = 10,
    dry_run: bool = False,
    yes_confirm: bool = False,
    force_reanalyze: bool = False  # ← NOUVEAU
):
    # ...
    self.force_reanalyze = force_reanalyze
```

**3. Modifier filter_unanalyzed:**

```python
# Ligne ~156
def filter_unanalyzed(
    self,
    activities: List[Dict],
    skip_planned: bool = False
) -> List[Dict]:
    """Filter activities that need analysis."""
    
    # Si force_reanalyze, ignorer workflow_state
    if self.force_reanalyze:
        print("⚡ Force re-analyze: ignoring workflow state")
        analyzed = set()  # ← Set vide = tout à analyser
    else:
        analyzed = self.get_analyzed_activities()
    
    # ... reste du code identique
```

**4. Passer flag dans main:**

```python
# Ligne ~550
backfiller = HistoryBackfiller(
    provider=args.provider,
    batch_size=args.batch_size,
    dry_run=args.dry_run,
    yes_confirm=args.yes,
    force_reanalyze=args.force_reanalyze  # ← NOUVEAU
)
```

---

## Tests de Validation

### Test 1: Dry-run avec force

```bash
poetry run backfill-history \
  --start-date 2024-08-01 \
  --end-date 2024-08-01 \
  --force-reanalyze \
  --dry-run
```

**Résultat attendu:**
```
⚡ Force re-analyze: ignoring workflow state
Total activités: 1
Déjà analysées: 0
À analyser: 1  # ✅ Maintenant détecté
```

### Test 2: Re-analyze réel

```bash
poetry run backfill-history \
  --start-date 2024-08-01 \
  --end-date 2024-08-01 \
  --force-reanalyze \
  --provider mistral_api \
  --yes
```

**Résultat attendu:**
```
✅ Analyse réussie: i47053576
💾 Commit batch 1...
✅ Committed dans ~/training-logs/
```

---

## Documentation

### Help Text

```bash
poetry run backfill-history --help
```

Devrait afficher:
```
optional arguments:
  --force-reanalyze     Force re-analyze activities even if already 
                        in workflow state (useful after fixing bugs)
```

### README Update

Ajouter exemple:
```markdown
### Force Re-Analyze

If activities were analyzed with bugs (e.g. written to wrong repo):

\`\`\`bash
poetry run backfill-history \\
  --start-date 2024-08-01 \\
  --end-date 2024-08-31 \\
  --force-reanalyze \\
  --yes
\`\`\`
```

---

## Impact

**Avant feature:**
- ❌ Impossible de ré-analyser activités déjà dans state
- ❌ Obligation de modifier manuellement .workflow_state.json
- ❌ Risque corruption state file

**Après feature:**
- ✅ Flag simple pour force re-analyze
- ✅ Workflow state préservé (pas de modification manuelle)
- ✅ Safe: dry-run possible avec --force-reanalyze

---

## Priorité

**P1 - HAUTE**

Bloque correction des 3 activités août mal analysées.

Nécessaire pour valider fix P0 (commit af47692).

---

**Créé:** 2025-12-26 17:45
**Dépend de:** Fix P0 commit af47692
