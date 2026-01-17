# FIX: Supprimer Vérification CWD dans workflow_coach.py

## Problème

workflow_coach.py refuse de s'exécuter depuis ~/training-logs/:

```
❌ Erreur: Ce script doit être lancé depuis la racine du projet.
   Répertoire courant: /Users/stephanejouve/training-logs
```

## Root Cause

Code workflow_coach.py vérifie que CWD = code repo:

```python
# workflow_coach.py (probablement ligne 30-40)
if not (Path.cwd() / 'pyproject.toml').exists():
    print("❌ Erreur: Ce script doit être lancé depuis la racine du projet.")
    print(f"   Répertoire courant: {Path.cwd()}")
    print("\n   cd ~/cyclisme-training-logs")
    print("   python3 cyclisme_training_logs/workflow_coach.py")
    sys.exit(1)
```

**Pourquoi c'était là:**
- Protection quand workflow_coach était script standalone
- S'assurer exécution depuis bon dossier

**Pourquoi ça ne marche plus:**
- Architecture double repo
- workflow_coach s'exécute depuis data repo
- pyproject.toml est dans code repo

## Solution

### Option 1: Supprimer Complètement la Vérification (RECOMMANDÉ)

```python
# workflow_coach.py
# SUPPRIMER ce bloc (chercher "Répertoire courant"):

# ❌ À SUPPRIMER
if not (Path.cwd() / 'pyproject.toml').exists():
    print("❌ Erreur: Ce script doit être lancé depuis la racine du projet.")
    print(f"   Répertoire courant: {Path.cwd()}")
    print("\n   cd ~/cyclisme-training-logs")
    print("   python3 cyclisme_training_logs/workflow_coach.py")
    sys.exit(1)
```

**Pourquoi c'est OK:**
- config.py gère déjà les paths correctement
- Package mode = pas besoin vérification CWD
- get_data_config() trouve automatiquement data repo

### Option 2: Vérification Intelligente (Alternative)

Si on veut garder une vérification:

```python
# workflow_coach.py
from .config import get_data_config

# Vérifier que data repo existe (au lieu de CWD check)
try:
    data_config = get_data_config()
    if not data_config.data_repo_path.exists():
        print(f"❌ Data repo not found: {data_config.data_repo_path}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)

# ✅ Pas de vérification CWD, juste que data repo accessible
```

## Modifications

### Fichier: cyclisme_training_logs/workflow_coach.py

**Chercher ces lignes (probablement ~30-40):**
```python
if not (Path.cwd() / 'pyproject.toml').exists():
    print("❌ Erreur: Ce script doit être lancé depuis la racine du projet.")
    print(f"   Répertoire courant: {Path.cwd()}")
    print("\n   cd ~/cyclisme-training-logs")
    print("   python3 cyclisme_training_logs/workflow_coach.py")
    sys.exit(1)
```

**SUPPRIMER complètement ce bloc**

**OU remplacer par:**
```python
# Vérification data repo accessible (optionnel)
from .config import get_data_config
try:
    data_config = get_data_config()
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)
```

## Validation

### Test 1: Depuis data repo

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
✅ Analyse réussie (plus d'erreur CWD)
💾 Markdown généré
```

### Test 2: Backfill

```bash
cd ~/cyclisme-training-logs

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

### Test 3: Depuis code repo (backward compat)

```bash
cd ~/cyclisme-training-logs

poetry run workflow-coach --help
```

**Résultat attendu:**
```
✅ Fonctionne aussi (pas de régression)
```

## Contexte Architecture

**Avant (mono-repo implicite):**
```
workflow_coach.py exécuté depuis ~/cyclisme-training-logs/
CWD = code repo ✅
pyproject.toml dans CWD ✅
Vérification CWD OK ✅
```

**Après (double repo):**
```
workflow_coach.py exécuté depuis ~/training-logs/
CWD = data repo ✅
pyproject.toml dans code repo (pas CWD) ❌
Vérification CWD FAIL ❌
```

**Solution:**
```
Supprimer vérification CWD obsolète
config.py gère paths automatiquement ✅
Fonctionne depuis n'importe où ✅
```

## Impact

**Sans fix:**
- ❌ workflow_coach échoue depuis data repo
- ❌ Backfill échoue (subprocess)
- ❌ Architecture double repo cassée

**Avec fix:**
- ✅ workflow_coach fonctionne partout
- ✅ Backfill fonctionne
- ✅ Architecture double repo opérationnelle

## Priorité

**P0 - CRITIQUE**

Bloque:
- ❌ Backfill production
- ❌ Workflow depuis data repo
- ❌ Architecture complète

## Notes

Cette vérification était une **protection temporaire** du début du projet.
Maintenant que:
- ✅ Package mode établi
- ✅ config.py robuste
- ✅ Architecture double repo

Elle est **obsolète et bloquante**.

Safe à supprimer ! ✅

---

**Créé:** 2025-12-26 20:15
**Bloque:** Backfill production
**Solution:** Supprimer vérification CWD obsolète
**Priorité:** P0 (bloquant système complet)
