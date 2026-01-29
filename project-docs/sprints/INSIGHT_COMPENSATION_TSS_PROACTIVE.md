# 🧠 INSIGHT MOA - Compensation TSS Proactive

**Date** : 28 Janvier 2026
**Session** : Discussion architecture Training Intelligence
**Participants** : PO (Stéphane Jouve), Claude Code (Dev)
**Statut** : ✅ Validé - À implémenter S080

---

## 📋 Résumé Exécutif

**Insight Critique** : Le système servo actuel est UNIQUEMENT réactif (déclenché par séance complétée). Cette approche est **incohérente avec la logique PID discrete controller** qui utilise le terme Intégral pour détecter et corriger les erreurs accumulées.

**Impact Business** :
- Séances sautées → Aucune action système (déficit TSS non géré)
- Quota hebdomadaire non maintenu
- Perte efficacité planification
- **Incohérence architecture** : PID sans terme Intégral actif

**Recommandation** : Implémenter mode **PROACTIF** avant Sprint R10 (calibration PID)

**Priorité** : 🔴 HAUTE (cohérence architecturale)

---

## 🎯 Problème Identifié

### Comportement Actuel (Mode Réactif Uniquement)

**Scénario 1 : Séance complétée + fatigue**
```
Lundi : Séance 60 TSS faite, découplage 8.5%
Lundi 21:30 (daily-sync) :
  ✅ Analyse AI
  ✅ Servo détecte fatigue
  ✅ Recommande alléger mercredi
  ✅ Email envoyé
```
→ **Fonctionne** ✅

**Scénario 2 : Séance sautée**
```
Lundi : Séance 60 TSS planifiée mais sautée (réunion)
Lundi 21:30 (daily-sync) :
  ℹ️  0 activité détectée
  ❌ Pas d'analyse
  ❌ Pas de servo
  ❌ Déficit -60 TSS ignoré
```
→ **Ne fonctionne PAS** ❌

**Impact sur la semaine** :
- Déficit TSS s'accumule
- Quota hebdomadaire compromis
- Aucune proposition compensation
- Récupération terme Intégral PID impossible

---

## 🧠 Justification Architecture PID

### Rappel : Composantes PID Discrete Controller

**P (Proportionnel)** : Réagit à erreur ACTUELLE
- Écart TSS cette semaine

**I (Intégral)** ⭐ : Réagit à erreur ACCUMULÉE
- **Déficit TSS cumulé sur plusieurs semaines**
- **Détecte patterns répétitifs (séances souvent sautées)**
- **C'est le mode proactif !**

**D (Dérivé)** : Réagit à TENDANCE
- Vitesse dégradation forme
- Prévient fatigue

### Incohérence Actuelle

Le système actuel :
- ✅ Utilise P (ajustement séance-par-séance)
- ❌ **N'utilise PAS I** (déficits non détectés)
- ⚠️ Utilise partiellement D (via PID evaluation 23h)

**Conclusion** : L'architecture PID est incomplète sans détection proactive des déficits.

---

## 💡 Solution Proposée

### Mode Proactif - Compensation TSS Intelligente

**Déclenchement** :
1. Daily-sync détecte séance planifiée non exécutée
2. Calcul déficit TSS hebdomadaire
3. Si déficit > seuil (ex: 50 TSS) → Analyse AI
4. Recommandations contextuelles

**Architecture** :
```python
# Dans daily_sync.py
def evaluate_weekly_deficit(week_id, check_date):
    """Évalue déficit TSS et décide intervention."""

    # 1. Charger planning
    planning = load_week_planning(week_id)

    # 2. Calculer déficit
    planned_tss = sum(s["tss"] for s in past_sessions)
    completed_tss = sum(a["tss"] for a in completed)
    deficit = planned_tss - completed_tss

    # 3. Seuil PID Intégral
    if abs(deficit) > 50:  # Configurable
        # 4. Contexte complet
        context = {
            "deficit": deficit,
            "cancelled_reasons": get_cancellation_reasons(),
            "remaining_sessions": get_remaining_sessions(),
            "athlete_state": get_current_metrics(),
            "rest_days": get_available_rest_days(),
            "indoor_sessions": get_convertible_sessions(),
        }

        # 5. Appel AI avec 6 stratégies
        return generate_proactive_recommendations(context)
```

---

## 🔄 6 Stratégies de Compensation

### 1. Intensifier Séances Existantes
**Gain** : +10-20 TSS/séance
**Conditions** : Forme OK, ≥2 jours restants
**Exemple** : 50 TSS → 65 TSS

### 2. Ajouter Séance Courte
**Gain** : +30-40 TSS
**Conditions** : Disponibilité, forme OK
**Exemple** : Ajouter récupération active 35 TSS

### 3. Convertir Indoor → Outdoor ⭐ NOUVEAU
**Gain** : +15-25% TSS (même durée)
**Conditions** : Météo >5°C, route sécurisée
**Exemple** : SS indoor 55 TSS → outdoor 70 TSS (+15)

**Rationale** : Outdoor plus exigeant (vent, terrain, mental)

### 4. Utiliser Jour de Repos ⭐ NOUVEAU
**Gain** : +40-80 TSS
**Conditions** : TSB >+5, forme excellente
**Exemple** : Dimanche repos → sortie endurance 60 TSS

**Garde-fou** : Max 1 fois/2 semaines

### 5. Compensation Partielle + Report
**Gain** : Variable
**Conditions** : Trop tard dans semaine
**Exemple** : +40 TSS cette semaine, -20 TSS suivante

### 6. Accepter Déficit
**Gain** : 0 TSS
**Conditions** : Fatigue détectée
**Rationale** : Récupération > TSS quota

---

## 🤖 Décision Intelligente AI

**Matrice de Décision** :

| Contexte | Jours Restants | Forme | Décision |
|----------|----------------|-------|----------|
| Circonstances | ≥3 jours | Bonne | **Compenser immédiat** |
| Circonstances | 1-2 jours | Bonne | **Partiel + report** |
| Circonstances | 0 jour | Bonne | **Reporter S+1** |
| Fatigue | Peu importe | Mauvaise | **Accepter déficit** |

**Prompt AI** (simplifié) :
```
Déficit : -60 TSS (2 séances sautées)
Raisons : Réunions professionnelles (pas fatigue)
Jours restants : 4 (Mercredi, Jeudi, Samedi, Dimanche)
Repos prévu : Dimanche
Indoor : Mercredi SS (55 TSS), Jeudi Tempo (45 TSS)

Métriques :
- TSB : +6 (excellente)
- Sommeil : 8.1h
- HRV : +5%

Météo semaine : 8-12°C, sec

Question : Stratégie compensation optimale ?

Stratégies disponibles :
1. Intensifier existantes
2. Ajouter séance courte
3. Convert indoor → outdoor
4. Utiliser repos dimanche
5. Combinaison
6. Accepter déficit

→ Recommande plan réaliste pour compenser -60 TSS
```

**Exemple Réponse AI** :
```json
{
  "strategy": "combined",
  "actions": [
    {"type": "convert_outdoor", "session": "Mercredi SS", "gain": 15},
    {"type": "convert_outdoor", "session": "Jeudi Tempo", "gain": 12},
    {"type": "use_rest_day", "day": "Dimanche", "workout": "END 60 TSS"},
    {"type": "intensify", "session": "Samedi", "from": 50, "to": 63}
  ],
  "total_compensated": 60,
  "conditions": ["Météo >5°C", "TSB >+5"],
  "rationale": "Forme excellente permet charge. Météo favorable conversions outdoor. Dimanche disponible."
}
```

---

## 📅 Plan d'Implémentation Recommandé

### Option Recommandée : Mini-Sprint S080

**Timeline** :
```
28 Jan 2026 (Aujourd'hui) :
  ✅ Insight documenté
  ✅ Fix servo non-interactif (commit e54f0c1)
  ✅ ROADMAP mis à jour

29 Jan - 09 Fév (S078-S079) :
  🏖️ Pause stratégique
  📊 Système en observation
  💾 Accumulation données

10-12 Fév (S080 Semaine 1) :
  🔧 Mini-Sprint Compensation TSS Proactive

  Jour 1 : Détection proactive
    - Calcul déficit TSS
    - Détection séances sautées
    - Intégration daily-sync

  Jour 2 : AI Recommendations
    - Prompt avec 6 stratégies
    - Parsing réponses
    - Logique décision (matrice)

  Jour 3 : Tests & Integration
    - Tests unitaires (≥15 tests)
    - Email formatting
    - Documentation

13-16 Fév (S080 Semaine 2) :
  🧪 Tests conditions réelles
  🎨 Polish & ajustements
  📚 Documentation finale

17 Fév+ (S081+) :
  🚀 Sprint R10 - PID Calibration Complete
  (Compensation TSS déjà opérationnelle)
```

**Durée estimée** : 2-3 jours développement

**Effort** : Moyen (architecture déjà bien comprise)

---

## 📊 Livrables Attendus

### Code
- [ ] `daily_sync.py` : Fonction `evaluate_weekly_deficit()`
- [ ] Calcul déficit TSS avec historique semaine
- [ ] Détection séances sautées vs planifiées
- [ ] 6 stratégies compensation implémentées
- [ ] Prompt AI avec contexte complet
- [ ] Parsing réponses AI (JSON)
- [ ] Intégration email daily report
- [ ] Garde-fous (TSB, historique, météo)

### Tests
- [ ] Tests calcul déficit (5 scénarios)
- [ ] Tests stratégies compensation (6 stratégies)
- [ ] Tests décision AI (matrice complète)
- [ ] Tests garde-fous (rest day, outdoor)
- [ ] Tests intégration email

### Documentation
- [ ] README compensation TSS
- [ ] Exemples prompts AI
- [ ] Guide utilisation MOA
- [ ] Update ROADMAP

---

## 🎯 Bénéfices Attendus

### Court Terme (S080-S082)
- ✅ Détection automatique déficits TSS
- ✅ Recommandations intelligentes par email
- ✅ Maintien quota hebdomadaire
- ✅ Cohérence architecture PID

### Moyen Terme (S083+)
- ✅ Données compensation pour calibration PID
- ✅ Learnings patterns séances sautées
- ✅ Optimisation stratégies via feedback
- ✅ Adaptation automatique progressive

### Long Terme (Q2 2026)
- ✅ Système PID complet (P+I+D actifs)
- ✅ Intelligence proactive mature
- ✅ Auto-adaptation planning avancée
- ✅ Réduction intervention manuelle

---

## 🔗 Références

### Code Existant
- `daily_sync.py` : Ligne 613-762 (servo réactif actuel)
- `workflow_coach.py` : Ligne 590-650 (_apply_lighten avec fix non-interactif)
- `pid_daily_evaluation.py` : Évaluation quotidienne 23h

### Commits Liés
- `e54f0c1` - fix(servo): Make servo-mode non-interactive (28 Jan 2026)
- Future : `feat: Add TSS deficit proactive compensation`

### Documentation
- `ROADMAP.md` : Ligne 815-823 (Sprint R7 - Full Automation)
- `SESSION_R9E_PHASE1_25JAN2026_SUMMARY.md` : Session contexte

---

## ✅ Validation PO

**Question PO** : _"Quand recommandes-tu de coder ceci ?"_

**Réponse Dev** : Mini-Sprint S080 (début février)
- Cohérence architecture PID (terme Intégral)
- Avant calibration PID (R10)
- Timeline pragmatique
- Fonctionnalité autonome testable

**Statut** : ✅ Insight validé, à planifier S080

---

**Document préparé par** : Claude Code (Dev)
**Pour** : Stéphane Jouve (PO/MOA)
**Date** : 28 Janvier 2026
**Next Step** : Planifier mini-sprint S080 (10-12 février)
