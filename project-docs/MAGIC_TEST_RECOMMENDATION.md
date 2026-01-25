# ✨ Recommandation Automatique Tests FTP "Comme par Magie"

## 🎯 Ce qui s'est passé

Une recommandation de tests FTP va apparaître automatiquement lors de votre prochain `end-of-week` workflow, grâce au système d'intelligence intégré.

## 🔮 Comment ça marche

### 1. Détection Automatique

Le script `pid-daily-evaluation` qui tourne maintenant intégré dans `end-of-week` (Step 1b) :

1. **Analyse l'historique** : Cherche le dernier test FTP (activité avec IF > 0.90, durée 40-60min)
2. **Calcule le temps écoulé** : Compare avec le cycle PID recommandé (6-8 semaines)
3. **Évalue la condition** : Vérifie TSB, CTL, adhérence, qualité CV
4. **Décide** : Détermine si un test est opportun et quand

### 2. Création de l'Adaptation

Si un test est recommandé, le système créé automatiquement une **adaptation de protocole** dans `TrainingIntelligence`:

```json
{
  "id": "ftp_test_cycle_ADD_1769338007",
  "protocol_name": "ftp_test_cycle",
  "adaptation_type": "ADD",
  "current_rule": "Dernier test: 8.0 semaines",
  "proposed_rule": "Semaine affûtage puis tests FTP (TSS -40%)",
  "justification": "Cycle PID dépassé (8.0 > 6-8 sem), TSB insuffisant",
  "confidence": "high",
  "status": "PROPOSED",
  "evidence": [
    "Dernier test FTP: 8.0 semaines",
    "Cycle PID recommandé: 6-8 semaines",
    "TSB actuel: 0.0",
    "Adhérence: 100%",
    "Qualité CV: 2.4%",
    "Capacité TSS: 155%"
  ]
}
```

### 3. Affichage dans end-of-week

Lors du workflow `end-of-week` (Step 1b), la recommandation s'affiche:

```
================================================================================
🧠 STEP 1b/6: Évaluation PID & Training Intelligence
================================================================================

  ℹ️  Collecte des métriques d'entraînement...
  📅 Période: 2026-01-19 → 2026-01-25

[...]

  ============================================================================
  🎯 RECOMMANDATION DÉTECTÉE: NEEDS_TAPER
  ============================================================================
  💡 Test FTP recommandé avec affûtage (dernier: 8.0 sem)
  📅 Semaine prochaine après réduction volume (-40% TSS)
  ⏰ Dernier test: 8.0 semaines
  💪 TSB actuel: 0.0
  ============================================================================
```

## 📊 Votre Situation Actuelle

### Détection réalisée aujourd'hui (25/01/2026)

- **Dernier test FTP**: ~8.0 semaines (détecté via IF > 0.90)
- **TSB actuel**: 0.0 (neutre, pas assez frais)
- **CTL**: 42.8 (fitness modéré)
- **Adhérence**: 100% ✅
- **Qualité CV**: 2.4% découplage ✅
- **Capacité TSS**: 155% ✅

### Recommandation

**Status**: `NEEDS_TAPER`

**Action recommandée**:
1. Semaine S078 (26 jan - 1 fév): **Affûtage** avec réduction -40% TSS
2. Semaine S079 (2-8 fév): **Tests FTP** (Zwift Camp Base Line)

**Justification**:
- Cycle PID largement dépassé (8 sem vs 6-8 recommandé)
- Condition excellente MAIS TSB insuffisant pour test immédiat
- Besoin d'1 semaine de récupération pour optimiser les résultats

## 🎬 Ce soir quand vous lancerez end-of-week

```bash
poetry run end-of-week --week-completed S077 --week-next S078
```

Vous verrez automatiquement:
1. L'évaluation PID (Step 1b)
2. **La recommandation de tests** avec tous les détails
3. L'adaptation sauvegardée dans `~/data/intelligence.json`

## 📂 Fichiers concernés

- **Intelligence**: `~/data/intelligence.json` (contient l'adaptation)
- **Log PID**: `~/data/monitoring/pid_evaluation.jsonl` (historique évaluations)
- **Adhérence**: `~/data/monitoring/workout_adherence.jsonl` (base de données)

## 🔄 Cycle Complet

```
Adhérence collectée (22:00 quotidien)
    ↓
workout_adherence.jsonl
    ↓
end-of-week lancé (manuellement)
    ↓
Step 1b: PID Evaluation
    ↓
├─→ Collecte métriques (adhérence, CV, TSS)
├─→ Création learnings
├─→ **CHECK TEST OPPORTUNITY** ← MAGIE ICI
│   ├─→ Analyse temps depuis dernier test
│   ├─→ Évalue condition (TSB, CTL, fitness)
│   └─→ Crée adaptation si test recommandé
    ↓
Adaptation sauvegardée dans intelligence.json
    ↓
Affichage recommandation dans workflow ✨
```

## 💡 Pourquoi c'est "magique"

1. **Automatique**: Aucune intervention manuelle requise
2. **Intelligent**: Analyse multifactorielle (temps, condition, performance)
3. **Contextualisé**: Prend en compte votre situation réelle
4. **Actionnable**: Donne timing précis et plan d'action
5. **Traçable**: Toutes les preuves documentées

## 🔮 Prochaines Évolutions

- Détection plus précise du dernier test (chercher dans events Intervals.icu)
- Recommandation personnalisée du protocole de tests
- Auto-génération du planning d'affûtage
- Notification proactive (email/Slack) quand test devient opportun

## 📚 Références

- PID Discrete Controller: `cyclisme_training_logs/intelligence/discrete_pid_controller.py`
- Training Intelligence: `cyclisme_training_logs/intelligence/training_intelligence.py`
- PID Daily Evaluation: `cyclisme_training_logs/scripts/pid_daily_evaluation.py`
- End-of-Week Workflow: `cyclisme_training_logs/workflows/end_of_week.py`

---

**Créé**: 2026-01-25
**Par**: Claude Code + Stéphane Jouve
**Sprint**: R9.E - Enhancement PID & Intelligence
