# FIX: Capture stdout + stderr dans backfill subprocess

## Problème

Subprocess échoue (return code 1) mais stderr vide:
```
❌ Échec analyse: i113315172
   Return code: 1
   # Pas de message d'erreur affiché!
```

## Root Cause

Code actuel capture seulement stderr:
```python
# backfill_history.py ligne ~300
if result.returncode == 0:
    print(f"✅ Succès: {activity_id}")
    return True
else:
    print(f"❌ Échec analyse: {activity_id}")
    print(f"   Return code: {result.returncode}")
    if result.stderr:  # ❌ Seulement stderr
        print(f"   Error:\n{result.stderr[:500]}")
    return False
```

**Problème:** Beaucoup de programmes Python écrivent erreurs sur stdout !

## Solution

Afficher stdout ET stderr:

```python
def analyze_activity(self, activity: Dict) -> bool:
    """Analyze single activity using workflow-coach."""

    activity_id = str(activity.get('id', ''))

    if not activity_id:
        print(f"⚠️  Activité sans ID, skip")
        return False

    print(f"🚀 Lancement analyse automatique...")

    cmd = [
        sys.executable,
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
            cwd=str(self.data_config.data_repo_path),
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

            # ✅ Afficher stdout ET stderr
            if result.stdout:
                print(f"   Output:\n{result.stdout[:1000]}")
            if result.stderr:
                print(f"   Error:\n{result.stderr[:1000]}")

            # Si les deux vides, debug info
            if not result.stdout and not result.stderr:
                print(f"   ⚠️  Aucune sortie capturée!")
                print(f"   Command: {' '.join(cmd)}")
                print(f"   CWD: {self.data_config.data_repo_path}")

            return False

    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout (300s) pour {activity_id}")
        return False

    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {e}")
        return False
```

## Alternative: Mode Verbose Optionnel

Ajouter flag `--verbose` pour debug détaillé:

```python
# backfill_history.py
def add_arguments(self, parser):
    # ... autres arguments
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Afficher sortie complète subprocess'
    )

def analyze_activity(self, activity: Dict) -> bool:
    # ... setup cmd

    result = subprocess.run(
        cmd,
        cwd=str(self.data_config.data_repo_path),
        capture_output=not self.verbose,  # ✅ Pas de capture si verbose
        text=True,
        timeout=300
    )

    if self.verbose:
        # Sortie déjà affichée en live
        print(f"\n{'='*70}")
        print(f"Return code: {result.returncode}")
        print(f"{'='*70}\n")
    else:
        # Afficher stdout + stderr si échec
        if result.returncode != 0:
            # ... code actuel
```

Usage:
```bash
poetry run backfill-history \
  --start-date 2025-12-22 \
  --end-date 2025-12-22 \
  --verbose \  # ✅ Voir sortie subprocess
  --yes
```

## Validation

Test 1: Avec fix stdout
```bash
poetry run backfill-history \
  --start-date 2025-12-22 \
  --end-date 2025-12-22 \
  --yes

# Résultat attendu:
❌ Échec analyse: i113315172
   Return code: 1
   Output:
Traceback (most recent call last):
  File "...", line X, in <module>
    ...
ModuleNotFoundError: No module named 'anthropic'  # ← Exemple erreur
```

Test 2: Avec flag --verbose
```bash
poetry run backfill-history \
  --start-date 2025-12-22 \
  --end-date 2025-12-22 \
  --verbose \
  --yes

# Résultat attendu:
🚀 Lancement analyse automatique...
[Sortie complète workflow-coach en live]
Traceback (most recent call last):
  ...
======================================================================
Return code: 1
======================================================================
```

## Fichiers Modifiés

```
scripts/backfill_history.py
  Ligne ~300-320: Afficher stdout + stderr
  Ligne ~60-80: (Optionnel) Flag --verbose
```

## Priorité

**P1 - Important pour debug**

Sans fix:
- ❌ Erreurs invisibles (return code 1 sans détail)
- ❌ Debug impossible

Avec fix:
- ✅ Erreurs visibles (stdout + stderr)
- ✅ Debug rapide
- ✅ (Optionnel) Mode verbose pour investigation

---

**Créé:** 2025-12-26 20:00
**Bloque:** Debug backfill failures
**Solution:** Capture stdout en plus de stderr
