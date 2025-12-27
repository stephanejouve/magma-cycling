# Résumé : Bug Boucle Infinie Workflow

**Date** : 2025-12-25
**Priorité** : 🔴 P0 CRITIQUE

---

## 🎯 Problème Identifié

Les workflows `trainr` et `trains` **bouclent à l'infini** car :

1. ❌ **Sessions traitées non marquées** : Repos/sautées documentées ne sont pas enregistrées dans l'état persistant
2. ❌ **Re-détection systématique** : `step_1b_detect_all_gaps()` re-détecte les mêmes sessions à chaque itération
3. ❌ **Boucle while True sans condition intelligente** : Pas de vérification si nouveaux gaps détectés

---

## 📊 Preuves

### Log trainr (Reconciliation)
```
[INFO] Séances sautées : 1
[WARNING] ⏭️  SKIPPED : S072-05 [2025-12-19]

→ User traite [2]
→ "⚠️  Aucune réconciliation disponible"
→ Git commit error

🔄 Retour détection gaps...

[INFO] Séances sautées : 1  ← MÊME SESSION RE-DÉTECTÉE !
[WARNING] ⏭️  SKIPPED : S072-05 [2025-12-19]
```

### Log trains (Servo Mode)
```
📊 RÉSUMÉ GAPS DÉTECTÉS
💤 Repos planifiés : 1 (S072-07)
⏭️  Séances sautées : 1 (S072-05)

→ User traite repos S072-07
→ Markdown généré ✅
→ Insertion workouts-history.md ✅
→ Commit git ✅

🔄 Retour détection gaps...

📊 RÉSUMÉ GAPS DÉTECTÉS  ← SECONDE ITÉRATION
💤 Repos planifiés : 1 (S072-07)  ← DÉJÀ DOCUMENTÉ !
⏭️  Séances sautées : 1 (S072-05)
```

---

## 🛠️ Solution (3 Fixes P0)

### Fix #1 : Tracking Sessions Spéciales
Étendre `WorkflowState` pour persister sessions documentées :

```python
state.mark_special_session_documented(session_id, type, date)
state.is_special_session_documented(session_id, date)
```

**Impact** : Repos/annulations/sautées marquées après traitement

### Fix #2 : Filtrage Détection
Filtrer sessions déjà documentées dans `step_1b_detect_all_gaps()` :

```python
rest_days_filtered = [
    rest for rest in rest_days
    if not state.is_special_session_documented(rest['session_id'], rest['date'])
]
```

**Impact** : Sessions traitées n'apparaissent plus dans gaps

### Fix #3 : Sortie Intelligente Boucle
Tracker signature gaps et sortir si aucun nouveau gap :

```python
while True:
    choice, current_gaps = self.step_1b_detect_all_gaps()

    if current_gaps == seen_gaps:  # Aucun nouveau gap
        break

    seen_gaps = current_gaps
```

**Impact** : Boucle s'arrête quand tous gaps traités

---

## 📋 Plan Implémentation

| Phase | Tâche | Effort |
|-------|-------|--------|
| 1 | Extension WorkflowState | 2h |
| 2 | Filtrage détection | 2h |
| 3 | Détection intelligente boucle | 1h |
| 4 | Handler séances sautées | 2h |
| 5 | Tests intégration | 2h |

**Total** : 9 heures

---

## ✅ Validation Attendue

**Avant fix** :
- ❌ trainr : Boucle infinie après traitement
- ❌ trains : Boucle infinie après traitement
- ❌ User doit Ctrl+C pour sortir

**Après fix** :
- ✅ trainr : Traite sautées → Sort de la boucle
- ✅ trains : Traite repos → Traite sautées → Sort de la boucle
- ✅ Message "✅ Tous les gaps traités !" affiché

---

## 📎 Références

- **Audit complet** : `docs/audits/AUDIT_WORKFLOW_LOOP_BUG.md`
- **Fichier principal** : `cyclisme_training_logs/workflow_coach.py:2191-2258` (boucle while)
- **Détection gaps** : `cyclisme_training_logs/workflow_coach.py:775-1005`
- **WorkflowState** : `cyclisme_training_logs/workflow_state.py`

---

**Prochaine étape** : Implémenter fixes P0 (Phase 1-3 minimum)
