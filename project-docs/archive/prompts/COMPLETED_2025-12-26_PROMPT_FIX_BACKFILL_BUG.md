# FIX CRITICAL: backfill_history.py écrit dans mauvais repo

## 🚨 Bug Identifié

**Symptôme:**
```bash
backfill_history.py écrit dans:
~/cyclisme-training-logs/cyclisme_training_logs/logs/workouts-history.md ❌

Au lieu de:
~/training-logs/workouts-history.md ✅
```

**Root Cause:**
```python
# backfill_history.py ligne 65
project_root = Path(__file__).parent
# = ~/cyclisme-training-logs/cyclisme_training_logs/scripts/../
# = ~/cyclisme-training-logs/cyclisme_training_logs/

# Ligne 216
subprocess.run(cmd, cwd=str(project_root))  # ❌ Mauvais CWD !

# workflow_coach.py ligne 105 hérite:
self.project_root = Path.cwd()  # ← CWD hérité = mauvais repo

# Ligne 1763 fallback:
history_file = self.project_root / "logs" / "workouts-history.md"
# = ~/cyclisme-training-logs/cyclisme_training_logs/logs/workouts-history.md ❌
```

---

## ✅ Solution: 2 Fixes Obligatoires

### Fix 1: backfill_history.py (PRIORITAIRE)

**Fichier:** `cyclisme_training_logs/scripts/backfill_history.py`

**Ligne 216:** Remplacer CWD par data_repo_path

```python
# AVANT
result = subprocess.run(
    cmd,
    cwd=str(project_root),  # ❌ Mauvais CWD
    capture_output=True,
    text=True,
    timeout=300
)

# APRÈS
result = subprocess.run(
    cmd,
    cwd=str(self.data_config.data_repo_path),  # ✅ Bon repo
    capture_output=True,
    text=True,
    timeout=300
)
```

**Justification:**
- `self.data_config` existe déjà (ligne 103)
- Utilise configuration .env `TRAINING_DATA_REPO`
- Workflow-coach hérite bon CWD

---

### Fix 2: workflow_coach.py (DÉFENSE PROFONDEUR)

**Fichier:** `cyclisme_training_logs/workflow_coach.py`

**Ligne 1763:** Supprimer fallback hardcodé

```python
# AVANT
if self.config:
    history_file = self.config.workouts_history_path
else:
    history_file = self.project_root / "logs" / "workouts-history.md"  # ❌

# APRÈS
if self.config:
    history_file = self.config.workouts_history_path
else:
    # Toujours utiliser DataRepoConfig, jamais fallback
    from cyclisme_training_logs.config import get_data_config
    history_file = get_data_config().workouts_history_path  # ✅
```

**Autres lignes à corriger:**
- Ligne 2151 (même pattern)
- Ligne 2405 (message log incorrect)
- Lignes 2660, 2738 (git add hardcodé)

---

## 🧪 Tests de Validation

### Test 1: Dry-run backfill

```bash
cd ~/cyclisme-training-logs

# Avant fix
poetry run backfill-history \
  --start-date 2024-08-01 \
  --end-date 2024-08-05 \
  --dry-run

# Vérifier CWD dans logs:
# Devrait afficher: CWD = ~/training-logs/ ✅
```

### Test 2: Backfill réel

```bash
# Après fix, exécuter:
poetry run backfill-history \
  --start-date 2024-08-01 \
  --end-date 2024-08-01 \
  --provider mistral_api \
  --yes

# Vérifier fichier modifié:
ls -lhat ~/training-logs/workouts-history.md
# Devrait être récent ✅

ls -lhat ~/cyclisme-training-logs/cyclisme_training_logs/logs/workouts-history.md
# Ne devrait PAS exister ❌
```

### Test 3: Config validation

```bash
poetry run python -c "
from cyclisme_training_logs.config import get_data_config
config = get_data_config()
print('Data repo:', config.data_repo_path)
print('Workouts:', config.workouts_history_path)
assert config.data_repo_path == Path.home() / 'training-logs'
print('✅ Config OK')
"
```

---

## 📋 Checklist Pré-Merge

- [ ] Fix 1: backfill_history.py ligne 216 (CWD)
- [ ] Fix 2: workflow_coach.py ligne 1763 (fallback)
- [ ] Fix 2: workflow_coach.py ligne 2151 (fallback)
- [ ] Fix 2: workflow_coach.py autres hardcodés
- [ ] Test dry-run réussi
- [ ] Test backfill 1 activité réussi
- [ ] Fichier écrit dans ~/training-logs/ ✅
- [ ] Aucun fichier dans ~/cyclisme-training-logs/logs/ ❌
- [ ] Git commit dans bon repo
- [ ] Documentation mise à jour

---

## 🎯 Impact

**Avant fix:**
- Backfill août 2024: 3 séances écrites mauvais endroit
- Données perdues (non trackées Git)
- Confusion multi-repos

**Après fix:**
- Toutes analyses dans bon repo
- Git tracking correct
- Données centralisées ~/training-logs/

**Migration manuelle nécessaire:**
```bash
# Récupérer données perdues
tail -200 ~/cyclisme-training-logs/cyclisme_training_logs/logs/workouts-history.md > /tmp/lost_data.md

# Injecter dans bon repo
cd ~/training-logs
cat /tmp/lost_data.md >> workouts-history.md
git add workouts-history.md
git commit -m "Migration: Récupération backfill août 2024"
```

---

## 📚 Contexte Additionnel

**Config .env validée:**
```bash
TRAINING_DATA_REPO=/Users/stephanejouve/training-logs  ✅
```

**Architecture repos:**
```
~/training-logs/                          ← REPO DONNÉES (bon)
~/cyclisme-training-logs/                 ← REPO CODE
  ├── cyclisme_training_logs/
  │   ├── scripts/backfill_history.py     ← BUG ICI
  │   ├── workflow_coach.py               ← FALLBACK ICI
  │   └── logs/ (NE DEVRAIT PAS EXISTER)  ❌
```

**Coût migration manuelle évité:**
- 3 séances perdues août
- Potentiellement dizaines si backfill complet
- Risque data loss futures analyses

---

## 🚀 Priorité

**P0 - CRITIQUE**

Bloque backfill production, risque data loss, confusion multi-repos.

Fix immédiat requis avant tout backfill supplémentaire.

---

**Créé:** 2025-12-26 17:30
**Auteur:** Investigation session /mnt/transcripts/2025-12-26-16-18-05-backfill-config-bug-investigation.txt
