# Migration vers Control Tower - Plan d'Action

## 🎯 Objectif

Garantir que TOUS les scripts qui modifient des fichiers de planning passent par la Control Tower pour:
- ✅ Backup automatique
- ✅ Audit logging complet
- ✅ Protection contre modifications concurrentes
- ✅ Rollback capability

## 📋 Scripts à Migrer

### Priorité HAUTE (modifient directement planning JSON)

1. **cyclisme_training_logs/update_session_status.py** ✅
   - Met à jour le statut des sessions
   - Status: ✅ MIGRÉ (commit a7bfd34)
   - Permission: ✅ | Backup: ✅ | Audit: ✅

2. **cyclisme_training_logs/shift_sessions.py** ✅
   - Décale/swap les sessions
   - Status: ✅ MIGRÉ (commit à venir)
   - Permission: ✅ | Backup: ✅ | Audit: ✅

3. **cyclisme_training_logs/weekly_planner.py** ✅
   - Crée les plannings hebdomadaires
   - Status: ✅ MIGRÉ (commit à venir)
   - Permission: ✅ | Backup: ✅ | Audit: ✅ | Create: ✅

4. **cyclisme_training_logs/daily_sync.py** ✅
   - Synchronise avec Intervals.icu
   - Status: ✅ MIGRÉ (commit à venir)
   - Permission: ✅ | Backup: ✅ | Audit: ✅ | Read-only: ✅

5. **cyclisme_training_logs/rest_and_cancellations.py** ✅
   - Gère les repos/annulations
   - Status: ✅ MIGRÉ (commit à venir)
   - Read-only: ✅ (via planning_tower.read_week())

### Priorité MOYENNE (lisent et écrivent potentiellement)

6. **cyclisme_training_logs/planned_sessions_checker.py**
   - Vérifie les sessions planifiées
   - Status: ❌ À VÉRIFIER (lecture seule?)

7. **cyclisme_training_logs/workflows/end_of_week.py**
   - Workflow fin de semaine
   - Status: ❌ À MIGRER

8. **cyclisme_training_logs/workflow_coach.py**
   - Coach workflow principal
   - Status: ❌ À MIGRER

### Priorité BASSE (principalement lecture)

9. **cyclisme_training_logs/monthly_analysis.py**
   - Analyse mensuelle
   - Status: ℹ️ LECTURE SEULE (utiliser read_week())

## 🔧 Patterns de Migration

### Pattern 1: Script avec accès direct WeeklyPlan

**AVANT:**
```python
from cyclisme_training_logs.planning.models import WeeklyPlan

planning_file = planning_dir / f"week_planning_{week_id}.json"
plan = WeeklyPlan.from_json(planning_file)

# Modifications
plan.planned_sessions[0].status = "completed"

# Sauvegarde
plan.to_json(planning_file)
```

**APRÈS:**
```python
from cyclisme_training_logs.planning.control_tower import planning_tower

with planning_tower.modify_week(
    week_id,
    requesting_script="my-script-name",
    reason="Update session status from Intervals.icu"
) as plan:
    # Modifications
    plan.planned_sessions[0].status = "completed"
    # Sauvegarde automatique + backup + audit log
```

### Pattern 2: Fonction qui modifie planning

**AVANT:**
```python
def update_session(week_id: str, session_id: str, new_status: str):
    planning_file = get_planning_file(week_id)
    plan = WeeklyPlan.from_json(planning_file)

    for session in plan.planned_sessions:
        if session.session_id == session_id:
            session.status = new_status

    plan.to_json(planning_file)
```

**APRÈS:**
```python
from cyclisme_training_logs.planning.control_tower import (
    planning_tower,
    requires_tower_permission
)

@requires_tower_permission()
def update_session(week_id: str, session_id: str, new_status: str):
    with planning_tower.modify_week(
        week_id,
        requesting_script="update_session",
        reason=f"Update {session_id} to {new_status}"
    ) as plan:
        for session in plan.planned_sessions:
            if session.session_id == session_id:
                session.status = new_status
        # Auto-saved + backup + audit
```

### Pattern 3: Lecture seule (pas de modification)

**AVANT:**
```python
planning_file = planning_dir / f"week_planning_{week_id}.json"
plan = WeeklyPlan.from_json(planning_file)

# Lecture seulement
print(plan.tss_target)
```

**APRÈS:**
```python
from cyclisme_training_logs.planning.control_tower import planning_tower

# Pas de backup nécessaire pour lecture seule
plan = planning_tower.read_week(week_id)

# Lecture seulement
print(plan.tss_target)
```

## ✅ Checklist Migration

Pour chaque script:

- [ ] Identifier toutes les fonctions qui modifient planning
- [ ] Remplacer accès direct par `planning_tower.modify_week()`
- [ ] Ajouter `requesting_script` avec nom clair
- [ ] Ajouter `reason` explicite
- [ ] Ajouter decorator `@requires_tower_permission()` si fonction
- [ ] Tester avec dry-run
- [ ] Vérifier backup créé
- [ ] Vérifier audit log
- [ ] Tester rollback
- [ ] Commit avec message descriptif

## 🧪 Tests de Validation

Après migration de chaque script:

```python
# 1. Vérifier backup automatique
from cyclisme_training_logs.planning.control_tower import planning_tower
backups_before = len(planning_tower.list_backups("S081"))

# Exécuter script
my_script_function("S081")

backups_after = len(planning_tower.list_backups("S081"))
assert backups_after > backups_before, "Backup non créé!"

# 2. Vérifier audit log
from cyclisme_training_logs.planning.audit_log import audit_log
recent = audit_log.get_recent_operations(1, week_id="S081")
assert recent[0].tool == "my_script_name", "Audit non logged!"

# 3. Tester protection concurrence
try:
    planning_tower.request_permission("S081", "script1", "test")
    planning_tower.request_permission("S081", "script2", "test")
    assert False, "Devrait lever RuntimeError!"
except RuntimeError:
    pass  # Bon comportement
finally:
    planning_tower.release_permission("S081", "script1")
```

## 📊 Progression

- Scripts à migrer: 9
- Scripts migrés: 5 ✅
- Scripts en cours: 0
- % complété: 56%

### ✅ Scripts Migrés

1. **update_session_status.py** - ✅ MIGRÉ (2026-02-20)
   - Permission system: ✅
   - Backup automatique: ✅
   - Audit log: ✅
   - Tests: ✅
   - Commit: a7bfd34

2. **shift_sessions.py** - ✅ MIGRÉ (2026-02-20)
   - Permission system: ✅
   - Backup automatique: ✅
   - Audit log: ✅
   - Tests: ✅ (dry-run tested)
   - Commit: 921ee22

3. **rest_and_cancellations.py** - ✅ MIGRÉ (2026-02-20)
   - Mode: Read-only (planning_tower.read_week)
   - Bug fix: WeeklyPlan object access corrected
   - Deprecated: planning_dir parameter
   - Tests: Syntax validated
   - Commit: 3aa6fa0

4. **daily_sync.py** - ✅ MIGRÉ (2026-02-20)
   - Mode: Read + Write (planning_tower.read_week + modify_week)
   - Permission system: ✅
   - Backup automatique: ✅
   - Audit log: ✅
   - Optimization: Batch updates per week
   - Removed: Hardcoded paths
   - Tests: Syntax validated
   - Commit: bc6b2a1

5. **weekly_planner.py** - ✅ MIGRÉ (2026-02-20)
   - Mode: Create + Write (WeeklyPlan.to_json + modify_week)
   - Permission system: ✅
   - Audit log: ✅ (CREATE operation logged)
   - Pydantic validation: ✅
   - Methods migrated: update_session_status(), save_planning_json()
   - Tests: Syntax validated
   - Commit: À venir

## 🚀 Ordre de Migration Recommandé

1. update_session_status.py (simple, utilisé fréquemment)
2. shift_sessions.py (compléter migration)
3. rest_and_cancellations.py (simple)
4. daily_sync.py (critique, utilisé quotidiennement)
5. weekly_planner.py (complexe mais fondamental)
6. workflow_coach.py (complexe)
7. workflows/end_of_week.py
8. planned_sessions_checker.py (vérifier si lecture seule)
9. monthly_analysis.py (lecture seule probable)

## ⚠️ Règles STRICTES

1. **JAMAIS** modifier `week_planning_*.json` directement sans passer par Control Tower
2. **TOUJOURS** utiliser `planning_tower.modify_week()` pour modifications
3. **TOUJOURS** spécifier `requesting_script` et `reason`
4. **TOUJOURS** tester le rollback après migration
5. **JAMAIS** ignorer un `RuntimeError` de permission denied

## 🆘 Troubleshooting

### "Permission DENIED - week locked"

```python
# Vérifier qui a le lock
# (Implémenter méthode show_locks())
planning_tower.show_current_locks()

# Forcer release si script planté (DANGER!)
planning_tower._lock_holders.clear()  # En dernier recours seulement!
```

### "Backup failed"

```python
# Vérifier espace disque
# Vérifier permissions write
# Vérifier backup_dir existe
```

### "Audit log corruption"

```python
# Backup du log
cp .planning_audit.jsonl .planning_audit.jsonl.backup

# Nettoyer lignes corrompues
# Réexécuter opération
```
