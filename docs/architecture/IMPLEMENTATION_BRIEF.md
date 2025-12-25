# Brief Implémentation - Système Asservissement Coach AI

## 📚 Pré-requis Lecture

Lire d'abord **POETRY_ARCHITECTURE.md** pour patterns techniques.

## Vision Système

Transformer boucle ouverte (analyse → recommandations texte) en boucle fermée (analyse → modifications automatiques planning).

## Architecture Cible
```
┌──────────────────────┐
│  PLANIFICATION       │
│  Upload S0XX         │
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│  EXÉCUTION           │
│  Séances réalisées   │
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│  MESURE              │◄─── 🆕 Planning restant
│  AI analyse          │
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│  DÉCISION            │◄─── 🆕 Catalogue templates
│  AI propose modif    │
└──────┬───────────────┘
       ▼
┌──────────────────────┐
│  CORRECTION          │◄─── 🆕 Modification auto
│  DELETE/POST API     │
│  Update JSON         │
└──────┬───────────────┘
       └──────► Boucle
```

## État Actuel (✅ Validé)

### Tests Réussis
```bash
poetry run pytest tests/test_asservissement.py -v
# 8 passed in 0.18s ✅
```

### Structure Créée
```
data/
├── week_planning/
│   └── week_planning_S072.json  ✅
└── workout_templates/
    ├── recovery_active_30tss.json  ✅
    ├── recovery_active_25tss.json  ✅
    ├── recovery_short_20tss.json   ✅
    ├── endurance_light_35tss.json  ✅
    ├── endurance_short_40tss.json  ✅
    └── sweetspot_short_50tss.json  ✅
```

### Code Implémenté

**workflow_coach.py** - Nouvelles méthodes :
```python
load_remaining_sessions(week_id)                    ✅
format_remaining_sessions_compact(sessions)         ✅
load_workout_templates()                            ✅
build_ai_prompt(data, context, sessions)            ✅
parse_ai_modifications(response)                    ✅
apply_planning_modifications(mods, week_id)         ✅
_apply_lighten(mod, week_id)                        ✅
_get_workout_id_intervals(date)                     ✅
_delete_workout_intervals(workout_id)               ✅
_upload_workout_intervals(date, code, structure)    ✅
_update_planning_json(week_id, date, new, old, why) ✅
_extract_day_number(date_str, week_id)              ✅
```

## Workflow Usage

### Sans Modification
```bash
train  # ou: poetry run workflow-coach

🤖 WORKFLOW COACH AI
📅 Semaine : S072
📋 Planning restant : 5 séances
🤖 Analyse AI en cours...
✅ Planning maintenu tel quel
💾 Sauvegarde logs...
✅ WORKFLOW TERMINÉ
```

### Avec Modification
```bash
train

🤖 WORKFLOW COACH AI
📅 Semaine : S072
📋 Planning restant : 5 séances
🤖 Analyse AI en cours...

📋 1 modification(s) détectée(s)

🔄 Allégement via 'Récupération Active 30 TSS'
   Date : 2025-12-18
   Raison : HRV -15%
   
   Appliquer ? (o/n) : o
   
   🗑️  Ancien workout supprimé
   ⬆️  Nouveau workout uploadé
   📝 Planning JSON mis à jour
   ✅ Modification appliquée

✅ WORKFLOW TERMINÉ
```

## Prompt AI Enrichi

Ajout ~330 tokens (+15%) :
```markdown
## PLANNING RESTANT SEMAINE (5 séances)

2025-12-18: S072-03-END-EnduranceProgressive-V001 (50 TSS)
2025-12-19: S072-04-INT-SweetSpotCourt-V001 (55 TSS)
2025-12-20: S072-05-REC-RecuperationActive-V001 (30 TSS)
2025-12-21: S072-06-INT-VO2MaxCourt-V001 (65 TSS)
2025-12-22: REPOS (0 TSS)

## CATALOGUE TEMPLATES DISPONIBLES

**RÉCUPÉRATION** :
- recovery_active_30tss : 45min Z1-Z2 (30 TSS)
- recovery_active_25tss : 40min Z1-Z2 (25 TSS)
- recovery_short_20tss : 30min Z1 (20 TSS)

**ENDURANCE** :
- endurance_light_35tss : 50min Z2 bas (35 TSS)
- endurance_short_40tss : 55min Z2 (40 TSS)

**INTENSITÉ** :
- sweetspot_short_50tss : 2x10min 88-90% FTP (50 TSS)

Si allégement nécessaire, format JSON :
{
  "modifications": [{
    "action": "lighten",
    "target_date": "YYYY-MM-DD",
    "current_workout": "SXXX-XX-TYPE-V001",
    "template_id": "recovery_active_30tss",
    "reason": "HRV -15%"
  }]
}
```

## Structure Planning JSON
```json
{
  "week_id": "S072",
  "start_date": "2025-12-16",
  "end_date": "2025-12-22",
  "sessions": [
    {
      "day": "2025-12-18",
      "workout_code": "S072-03-END-V001",
      "type": "END",
      "tss_planned": 50,
      "status": "planned",
      "history": []
    }
  ]
}
```

## Structure Template JSON
```json
{
  "id": "recovery_active_30tss",
  "name": "Récupération Active 30 TSS",
  "type": "REC",
  "tss": 30,
  "duration_minutes": 45,
  "workout_code_pattern": "{week_id}-{day_num:02d}-REC-RecuperationActive-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-60% 85rpm\n...",
  "use_cases": ["lighten_from_endurance"],
  "prerequisites": {
    "min_tsb": -15,
    "max_tsb": 999
  }
}
```

## Métriques Impact

- Lignes code : ~350 ajoutées
- Fichiers créés : 8 (6 templates + planning + tests)
- Tests : 8 unitaires ✅
- Temps implémentation : ~2-3h
- Dépendances nouvelles : 0

## ROI Estimé

- Coût tokens AI : +$0.78/an (+15%)
- Gain temps : 495€/an (20min → 2.5min post-séance)
- **Ratio : 634:1**

## Problèmes Connus Résolus

1. ✅ Dossier `data/week_planning/` créé
2. ✅ 6 templates JSON validés
3. ✅ Tests unitaires passants
4. ✅ Intégration workflow_coach.py complète

## Séances Sautées à Réconcilier

État actuel système :
```
⏭️  Séances planifiées sautées : 3
   • [2025-12-04] S070-04-END-EnduranceProgressive-V001
   • [2025-12-12] S071-05-INT-SweetSpotCourt-V001
   • [2025-12-16] S072-02-CAD-CadenceExplosif-V001
```

**Action** : Réconciliation manuelle via `poetry run planned-checker`

## Prochaines Étapes

1. ✅ Tests validation passés
2. ⏳ Réconcilier 3 séances sautées
3. ⏳ Tester workflow terrain (séance réelle)
4. ⏳ Valider modification automatique
5. ⏳ Documentation finale

## Validation Fonctionnelle

### Checklist
- [x] Structure data/ créée
- [x] 6 templates JSON validés
- [x] workflow_coach.py modifié
- [x] Tests unitaires créés
- [x] `poetry run pytest` OK
- [ ] Réconciliation séances sautées
- [ ] Workflow terrain testé
- [ ] Modification auto validée

---

**Système asservissement opérationnel - Tests ✅**
**Prêt pour validation terrain** 🚀
