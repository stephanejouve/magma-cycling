# FIX: prepare_analysis.py Path - Utiliser Module au Lieu de Path Absolu

## Problème

workflow_coach.py échoue en cherchant prepare_analysis.py:

```
Python: can't open file '/Users/stephanejouve/training-logs/magma_cycling/prepare_analysis.py':
[Errno 2] No such file or directory
```

## Root Cause

Code workflow_coach.py utilise path absolu basé sur CWD:

```python
# ❌ MAUVAIS (quelque part dans workflow_coach.py)
subprocess.run([
    sys.executable,
    str(Path.cwd() / 'magma_cycling' / 'prepare_analysis.py'),
    '--activity-id', activity_id,
    ...
])
```

**Pourquoi ça échoue:**
- CWD = `~/training-logs/` (data repo)
- Cherche `~/training-logs/magma_cycling/prepare_analysis.py`
- Fichier réel: `~/magma-cycling/magma_cycling/prepare_analysis.py`

## Solution: Python Module (-m)

### Option 1: Utiliser -m (RECOMMANDÉ)

```python
# ✅ BON: Module import
subprocess.run([
    sys.executable,
    '-m', 'magma_cycling.prepare_analysis',
    '--activity-id', activity_id,
    ...
])
```

**Pourquoi ça marche:**
- Module installé via Poetry (editable)
- Python trouve automatiquement via PYTHONPATH
- Fonctionne depuis n'importe quel CWD

### Option 2: Import Direct (Alternative)

Si prepare_analysis peut être importé comme module:

```python
# ✅ Alternative: Import direct
from magma_cycling.prepare_analysis import main

# Appeler directement
result = main(
    activity_id=activity_id,
    provider=provider,
    ...
)
```

**Avantages:**
- Pas de subprocess overhead
- Meilleur error handling
- Partage même environnement

## Modifications

### Fichier: magma_cycling/workflow_coach.py

**Chercher ces lignes (probablement ~150-200):**

```python
# ❌ Code actuel
subprocess.run([
    sys.executable,
    str(Path.cwd() / 'magma_cycling' / 'prepare_analysis.py'),
    '--activity-id', activity_id,
    # ... autres args
])
```

**Remplacer par:**

```python
# ✅ Fix: Module import
subprocess.run([
    sys.executable,
    '-m', 'magma_cycling.prepare_analysis',
    '--activity-id', activity_id,
    # ... autres args
])
```

**OU Alternative (import direct):**

```python
# ✅ Alternative: Import et appel direct
from magma_cycling.prepare_analysis import main as prepare_main

result = prepare_main(
    activity_id=activity_id,
    provider=provider,
    # ... autres args
)
```

## Autres Scripts à Vérifier

Chercher TOUS les subprocess avec paths absolus:

```bash
cd ~/magma-cycling

# Chercher patterns problématiques
grep -n "Path.cwd()" magma_cycling/workflow_coach.py
grep -n "subprocess.run" magma_cycling/workflow_coach.py | grep -v "'-m'"

# Tous doivent utiliser '-m' module syntax
```

**Exemple autres scripts probablement affectés:**
```python
# timeline_injector.py ?
subprocess.run([sys.executable, str(Path.cwd() / 'magma_cycling' / 'timeline_injector.py')])

# ✅ Fix:
subprocess.run([sys.executable, '-m', 'magma_cycling.timeline_injector'])
```

## Validation

### Test 1: prepare_analysis direct

```bash
cd ~/training-logs

# Test module import
python3 -m magma_cycling.prepare_analysis --help
```

**Résultat attendu:**
```
usage: prepare_analysis.py [-h] --activity-id ID ...
✅ Module accessible
```

### Test 2: workflow-coach complet

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
✅ Analyse réussie (plus d'erreur prepare_analysis.py)
💾 Markdown généré
```

### Test 3: Backfill

```bash
cd ~/magma-cycling

poetry run backfill-history \
  --start-date 2025-12-22 \
  --end-date 2025-12-22 \
  --force-reanalyze \
  --provider mistral_api \
  --yes
```

**Résultat attendu:**
```
✅ 1 activités trouvées
🚀 Lancement analyse automatique...
✅ Succès: i113315172

STATISTIQUES FINALES:
   ✅ Succès: 1
   ❌ Échecs: 0
```

## Pattern Global

**RÈGLE:** Dans une architecture package, **TOUJOURS** utiliser module import:

```python
# ❌ ÉVITER
subprocess.run([sys.executable, str(Path('script.py'))])
subprocess.run([sys.executable, 'path/to/script.py'])

# ✅ UTILISER
subprocess.run([sys.executable, '-m', 'package.module'])
```

**Pourquoi:**
- ✅ Fonctionne depuis n'importe quel CWD
- ✅ Utilise PYTHONPATH correctement
- ✅ Compatible package editable
- ✅ Portable entre environnements

## Checklist Complète

```bash
cd ~/magma-cycling

# 1. Chercher tous subprocess
grep -rn "subprocess.run" magma_cycling/ | grep -v "'-m'"

# 2. Pour chaque occurrence:
#    - Vérifier si path absolu utilisé
#    - Remplacer par '-m' module syntax

# 3. Tester chaque module individuellement
python3 -m magma_cycling.prepare_analysis --help
python3 -m magma_cycling.timeline_injector --help
# ... etc

# 4. Test integration complet
poetry run workflow-coach --help
poetry run backfill-history --help
```

## Priorité

**P0 - CRITIQUE**

Bloque:
- ❌ workflow_coach en mode auto
- ❌ Backfill production
- ❌ Tous les subprocess internes

## Impact Estimé

**Scripts probablement affectés:**
1. prepare_analysis.py ← **Confirmé**
2. timeline_injector.py ← **À vérifier**
3. Autres subprocess internes ← **À vérifier**

**Temps fix:** 5-10 minutes (chercher-remplacer)
**Validation:** 5 minutes (tests)
**Total:** ~15 minutes

---

**Créé:** 2025-12-26 20:30
**Bloque:** Backfill production
**Solution:** Utiliser `-m` module import partout
**Priorité:** P0 (bloquant critique)
