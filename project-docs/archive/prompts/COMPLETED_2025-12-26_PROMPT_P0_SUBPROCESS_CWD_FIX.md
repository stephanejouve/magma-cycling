# FIX P0: Subprocess CWD - Python Direct au Lieu de Poetry

**Bug:** `poetry run workflow-coach` échoue car exécuté depuis data repo

**Erreur:**
```
Poetry could not find a pyproject.toml file in /Users/stephanejouve/training-logs
```

---

## PROBLÈME

### Ligne problématique
**Fichier:** `scripts/backfill_history.py` ligne ~260

```python
# Commande actuelle
cmd = [
    'poetry', 'run', 'workflow-coach',  # ❌ Poetry cherche pyproject.toml
    '--activity-id', activity_id,
    '--provider', self.provider,
    '--auto',
    '--skip-feedback',
    '--skip-git'
]

# CWD = data repo
subprocess.run(
    cmd,
    cwd=str(self.data_config.data_repo_path),  # /Users/stephanejouve/training-logs
    capture_output=True,
    text=True,
    timeout=300
)
```

**Pourquoi ça échoue:**
1. `cwd=/Users/stephanejouve/training-logs` (data repo)
2. Poetry cherche `pyproject.toml` dans ce dossier
3. `pyproject.toml` est dans `/Users/stephanejouve/cyclisme-training-logs` (code repo)
4. Poetry échoue avec "could not find pyproject.toml"

---

## SOLUTION: Python Direct

### Modifications `scripts/backfill_history.py`

**Ajouter imports (ligne ~60):**
```python
import sys
```

**Remplacer analyze_activity() lignes ~240-290:**

```python
def analyze_activity(self, activity: Dict) -> bool:
    """
    Analyze single activity using workflow-coach.
    
    Uses direct Python execution instead of 'poetry run' to avoid
    pyproject.toml lookup in wrong directory.
    """
    activity_id = str(activity.get('id', ''))
    
    if not activity_id:
        print(f"⚠️  Activité sans ID, skip")
        return False
    
    print(f"🚀 Lancement analyse automatique...")
    
    # Construire commande Python directe
    # Au lieu de: poetry run workflow-coach --activity-id ...
    # Utiliser: python -m cyclisme_training_logs.workflow_coach --activity-id ...
    
    cmd = [
        sys.executable,  # Python actuel (même que backfill)
        '-m', 'cyclisme_training_logs.workflow_coach',
        '--activity-id', activity_id,
        '--provider', self.provider,
        '--auto',
        '--skip-feedback',
        '--skip-git'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(self.data_config.data_repo_path),  # ✅ OK maintenant
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"✅ Succès: {activity_id}")
            return True
        else:
            print(f"❌ Échec analyse: {activity_id}")
            print(f"   Return code: {result.returncode}")
            if result.stderr:
                print(f"   Error:\n{result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout (300s) pour {activity_id}")
        return False
        
    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {e}")
        return False
```

---

## ALTERNATIVE: Dual CWD Approach

Si problème avec Python module import, utiliser ce pattern:

```python
def analyze_activity(self, activity: Dict) -> bool:
    """Analyze with proper CWD handling"""
    
    activity_id = str(activity.get('id', ''))
    
    # Commande Poetry MAIS depuis code repo
    cmd = [
        'poetry', 'run', 'workflow-coach',
        '--activity-id', activity_id,
        '--provider', self.provider,
        '--auto',
        '--skip-feedback',
        '--skip-git'
    ]
    
    # Définir variables d'environnement pour pointer vers data repo
    env = os.environ.copy()
    env['TRAINING_DATA_REPO'] = str(self.data_config.data_repo_path)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(Path.home() / 'cyclisme-training-logs'),  # ✅ Code repo pour Poetry
            env=env,  # ✅ Data repo via env var
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # ... reste identique
```

**Avantage:** Poetry fonctionne (trouve pyproject.toml)
**Condition:** workflow_coach doit lire `TRAINING_DATA_REPO` pour savoir où écrire

---

## VALIDATION

### Test 1: Python Direct

```bash
# Depuis data repo
cd ~/training-logs

# Tester commande Python directe
python3 -m cyclisme_training_logs.workflow_coach \
  --activity-id i113315172 \
  --provider mistral_api \
  --auto \
  --skip-feedback \
  --skip-git
```

**Résultat attendu:**
```
✅ Analyse réussie
📝 Markdown généré
💾 Sauvegardé dans ~/training-logs/workouts-history.md
```

### Test 2: Backfill après fix

```bash
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
À analyser: 1

🚀 Lancement analyse automatique...
✅ Succès: i113315172

📊 STATISTIQUES FINALES:
   ✅ Succès: 1
   ❌ Échecs: 0
```

---

## CONTEXTE COMMITS

```
af47692 - fix(P0): Backfill write to correct data repo
  → Fixait CWD mais créait ce nouveau bug Poetry
  
b4caf45 - fix(P0): Rate limiting retry
  → Enrichissement fonctionne maintenant
  
[CE COMMIT] - fix(P0): Use Python direct instead of Poetry in subprocess
  → Évite lookup pyproject.toml dans mauvais repo
```

---

## FICHIERS MODIFIÉS

```
scripts/backfill_history.py
  Ligne ~60: Ajouter import sys
  Ligne ~240-290: Remplacer analyze_activity() avec Python direct
```

---

## PRIORITÉ

**P0 - CRITIQUE**

Sans fix:
- ❌ Backfill échoue 100% (4/4 activités)
- ❌ Erreur Poetry pyproject.toml
- ❌ Aucune analyse générée

Avec fix:
- ✅ subprocess exécute Python directement
- ✅ Pas de dépendance Poetry dans subprocess
- ✅ CWD data repo fonctionne

---

## NOTES

**Pourquoi Python direct fonctionne:**
- `python -m cyclisme_training_logs.workflow_coach` ne cherche PAS pyproject.toml
- Module import fonctionne si PYTHONPATH correct (hérité du parent)
- CWD peut être data repo sans problème

**Pourquoi Poetry échouait:**
- `poetry run` nécessite pyproject.toml dans CWD ou parents
- CWD = data repo (pas de pyproject.toml)
- Poetry refuse d'exécuter

---

**Créé:** 2025-12-26 19:15  
**Bloque:** Backfill production toutes périodes  
**Dépend de:** Commits af47692, b4caf45  
**Priorité:** P0 (système non fonctionnel)
