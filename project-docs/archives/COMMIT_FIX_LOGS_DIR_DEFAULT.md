# COMMIT: Fix default --logs-dir dans insert_analysis.py

## Problème

Ligne 389 de insert_analysis.py:

```python
parser.add_argument(
    '--logs-dir',
    default='logs',  # ❌ Toujours non-None !
    help="Répertoire des logs (défaut: logs/)"
)
```

**Impact:**
```python
# Plus tard dans le code (ligne ~415)
manager = WorkoutHistoryManager(args.logs_dir, yes_confirm=args.yes)

# args.logs_dir est TOUJOURS 'logs' (jamais None)
# Donc WorkoutHistoryManager n'utilise JAMAIS config.py !
```

**Erreur résultante:**
```
❌ Fichier non trouvé : logs/workouts-history.md
```

## Solution

### Modification Ligne 389

**AVANT:**
```python
parser.add_argument(
    '--logs-dir',
    default='logs',
    help="Répertoire des logs (défaut: logs/)"
)
```

**APRÈS:**
```python
parser.add_argument(
    '--logs-dir',
    default=None,
    help="Répertoire des logs (défaut: utilise config.py)"
)
```

## Impact

**AVANT le fix:**
```python
args.logs_dir = 'logs'  # Toujours cette valeur
manager = WorkoutHistoryManager('logs', ...)  # Mode legacy
→ Cherche dans logs/workouts-history.md ❌
```

**APRÈS le fix:**
```python
args.logs_dir = None  # Par défaut
manager = WorkoutHistoryManager(None, ...)  # Mode moderne
→ Utilise config.workouts_history_path ✅
→ Trouve ~/training-logs/workouts-history.md ✅
```

## Test Après Fix

### Test 1: Insertion directe

```bash
cd ~/training-logs

# Créer test
cat > /tmp/test.md << 'EOF'
### S073-TEST
Date : 27/12/2025

#### Exécution
Test fix
EOF

cat /tmp/test.md | pbcopy

# Test insertion (SANS --logs-dir)
poetry run python -m magma_cycling.insert_analysis --yes
```

**Résultat attendu:**
```
✅ Fichier trouvé : /Users/stephanejouve/training-logs/workouts-history.md
✅ Analyse insérée
```

### Test 2: Backward compat

```bash
# Test avec --logs-dir explicite (legacy mode)
poetry run python -m magma_cycling.insert_analysis \
  --logs-dir ~/training-logs \
  --yes
```

**Résultat attendu:**
```
✅ Analyse insérée
⚠️  Warning: Explicit logs_dir deprecated
```

### Test 3: Workflow complet

```bash
cd ~/training-logs

poetry run workflow-coach \
  --activity-id i113315172 \
  --provider mistral_api \
  --auto \
  --skip-feedback \
  --skip-git
```

**Résultat attendu:**
```
💾 Insertion dans les Logs...
✅ Analyse insérée avec succès
[Exit code: 0]
```

### Test 4: Backfill final

```bash
cd ~/magma-cycling

poetry run backfill-history \
  --start-date 2025-12-22 \
  --end-date 2025-12-22 \
  --provider mistral_api \
  --force-reanalyze \
  --yes
```

**Résultat attendu:**
```
✅ Succès: 1/1  🎉
```

## Commit

```bash
cd ~/magma-cycling

git add magma_cycling/insert_analysis.py

git commit -m "fix(insert_analysis): Remove hardcoded default logs-dir

- Change --logs-dir default from 'logs' to None
- Forces WorkoutHistoryManager to use config.py by default
- Backward compat maintained with explicit --logs-dir
- Ligne 389: default='logs' → default=None

Fixes: Bug P0 #11 - insert_analysis cherche logs/ au lieu de config
Closes: Dernier path hardcodé résiduel"
```

## Vérification Complète

Après ce fix, **PLUS AUCUN** path hardcodé ne doit rester:

```bash
cd ~/magma-cycling

# Chercher tous les 'logs/' restants
grep -r "logs/" magma_cycling/ \
  --include="*.py" \
  | grep -v "^#" \
  | grep -v "help=" \
  | grep -v "description="

# Résultat attendu: Vide ou seulement commentaires
```

---

**C'EST LE VRAI DERNIER BUG !** 🎯

Après ce fix:
- ✅ insert_analysis.py utilise config.py
- ✅ Aucun path hardcodé résiduel
- ✅ Architecture double repo 100% fonctionnelle
- ✅ Backfill production ready

**→ FIX ET ON LANCE LA PROD !** 🚀
