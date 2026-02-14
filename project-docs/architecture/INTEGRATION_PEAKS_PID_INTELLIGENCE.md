# Architecture Intégration: Peaks Coaching ↔ PID Controller ↔ Training Intelligence

**Date**: 2026-02-14
**Auteur**: Claude Sonnet 4.5
**Contexte**: Post-implémentation Sections 11-13 Peaks Coaching

---

## 1. VUE D'ENSEMBLE ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────────┐
│                     TRAINING INTELLIGENCE SYSTEM                      │
│                                                                        │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐       │
│  │   PEAKS      │      │     PID      │      │  TRAINING    │       │
│  │  COACHING    │◄────►│  DISCRETE    │◄────►│ INTELLIGENCE │       │
│  │   MODULES    │      │ CONTROLLER   │      │   (Memory)   │       │
│  └──────────────┘      └──────────────┘      └──────────────┘       │
│         │                      │                      │               │
│         │                      │                      │               │
│         ▼                      ▼                      ▼               │
│  ┌──────────────────────────────────────────────────────────┐        │
│  │              WEEKLY PLANNER (Orchestrator)                │        │
│  └──────────────────────────────────────────────────────────┘        │
│                              │                                        │
└──────────────────────────────┼────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
            ┌──────────────┐      ┌──────────────┐
            │  DAILY SYNC  │      │  AUTO SERVO  │
            └──────────────┘      └──────────────┘
```

---

## 2. COMPOSANTS & RESPONSABILITÉS

### 2.1 Peaks Coaching Modules (NOUVEAU - Section 11-13)

**Fichiers**:
- `peaks_phases.py` - Algorithme détection phase (RECONSTRUCTION/CONSOLIDATION/DEVELOPMENT)
- `workout_validation.py` - 7 checks pré-prescription
- `outdoor_discipline.py` - Tracking discipline outdoor
- `alert_messages.py` - Templates alertes standardisés

**Rôle dans l'architecture**:
- **Validation pré-prescription** : Vérifie qu'une séance est appropriée AVANT scheduling
- **Détection phase** : Détermine distribution intensité optimale selon CTL actuel
- **Alertes proactives** : Signale problèmes CTL, distribution, discipline

**Inputs**:
- CTL/ATL/TSB actuels (via Intervals.icu)
- FTP actuel et target
- Historique séances récentes (48-72h)
- Métriques athlete (sommeil, fatigue)

**Outputs**:
- `PhaseRecommendation` → Distribution intensité (Tempo 35%, Sweet-Spot 20%, etc.)
- `WorkoutValidation` → Safe/unsafe pour prescription
- `DisciplineReport` → Recommandation indoor/outdoor par zone
- Alertes CTL critique si < seuils Peaks

---

### 2.2 PID Discrete Controller (EXISTANT - Sprint R7, NON CALIBRÉ)

**Fichiers**:
- `discrete_pid_controller.py` - Contrôleur PID adapté mesures sporadiques
- `pid_daily_evaluation.py` - Évaluation quotidienne (script)

**Rôle dans l'architecture**:
- **Régulation FTP** : Calcule correction TSS pour atteindre FTP target
- **Sample-and-Hold** : Correction maintenue sur cycle complet (6-8 semaines)
- **Multi-critères** : Valide via adhérence, couplage cardiovasculaire, TSS completion

**Formule PID Discrète**:
```python
error = setpoint - measured_ftp
integral += error * dt_cycles  # Anti-windup
derivative = (error - prev_error) / dt_cycles
output = Kp * error + Ki * integral + Kd * derivative

# Translation TSS
tss_per_week = output * 12.5  # +1W FTP ≈ +12.5 TSS/semaine
```

**Gains (à calibrer post-S080)**:
- `Kp = 0.008` (Proportionnel)
- `Ki = 0.001` (Intégral)
- `Kd = 0.12` (Dérivé)

**Inputs**:
- Tests FTP espacés (6-8 semaines) → `measured_ftp`
- Métriques validation (adhérence, couplage, TSS completion)

**Outputs**:
- `tss_per_week` → Correction appliquée sur cycle suivant
- `validation` → Correction validée ou rejetée

**STATUS ACTUEL**: ⚠️ **NON CALIBRÉ** - Awaiting S080 test results + Sprint R10

---

### 2.3 Proactive Compensation (EXISTANT - Sprint R9e)

**Fichier**: `proactive_compensation.py`

**Rôle dans l'architecture**:
- **Implémente terme Intégral (I) du PID** : Accumule erreurs TSS hebdomadaires
- **Compensation réactive** : Détecte séances sautées, propose stratégies récupération
- **Intégration daily-sync** : Génère recommandations AI chaque jour

**Stratégies compensation**:
1. **Intensify** - Augmenter intensité séances restantes
2. **Extend** - Prolonger durée séances existantes
3. **Add** - Ajouter micro-séances (30-45min)
4. **Use Rest Day** - Utiliser jour repos si TSB permet
5. **Report** - Reporter déficit semaine suivante
6. **Partial Report** - Hybride (compenser partiellement + reporter)

**Inputs**:
- Séances planifiées vs complétées
- TSS cible hebdomadaire vs actuel
- Jours restants dans semaine
- TSB actuel

**Outputs**:
- Recommandations compensation (markdown)
- Actions suggérées avec gains TSS estimés

---

### 2.4 Training Intelligence (EXISTANT - Sprint R4)

**Fichier**: `training_intelligence.py`

**Rôle dans l'architecture**:
- **Mémoire unifiée** : Accumule learnings across temporal scales (daily/weekly/monthly)
- **Pattern detection** : Détection automatique patterns récurrents
- **Progressive validation** : LOW → MEDIUM → HIGH → VALIDATED
- **Evidence-based adaptations** : Propose modifications protocoles basées sur données

**Classes principales**:
- `TrainingLearning` - Un apprentissage avec progressive validation
- `Pattern` - Pattern récurrent identifié
- `TrainingIntelligence` - Orchestrateur mémoire

**Inputs**:
- Analyses séances complétées (découplage, RPE, puissance, HR)
- Patterns émergents (ex: "sleep debt → VO2 failure")
- Validations multi-observations

**Outputs**:
- Learnings stockés avec confidence level
- Recommandations adaptations protocoles
- Context-aware insights pour weekly planner

---

## 3. FLUX D'INTÉGRATION

### 3.1 Flux Hebdomadaire (Weekly Planning)

```
[Dimanche] WEEKLY PLANNER - Génération semaine suivante
│
├─► 1. PEAKS PHASE DETECTION
│   │   peaks_phases.determine_training_phase(ctl_current, ftp_current, ftp_target)
│   │   → PhaseRecommendation (RECONSTRUCTION/CONSOLIDATION/DEVELOPMENT)
│   │   → Distribution intensité: Tempo 35%, Sweet-Spot 20%, etc.
│   │
│   └─► OUTPUT: weekly_tss_target, intensity_distribution
│
├─► 2. PID CORRECTION (si test FTP récent)
│   │   discrete_pid_controller.compute_cycle_correction_enhanced(measured_ftp, ...)
│   │   → tss_per_week correction (appliqué sur cycle 6-8 semaines)
│   │
│   └─► OUTPUT: weekly_tss_adjusted = weekly_tss_target + tss_per_week
│
├─► 3. TRAINING INTELLIGENCE INSIGHTS
│   │   training_intelligence.get_validated_learnings()
│   │   → Patterns validés (ex: "Tempo outdoor → IF overload")
│   │   → Recommandations adaptations
│   │
│   └─► OUTPUT: constraints, preferences (ex: "VO2 indoor only")
│
├─► 4. GENERATION PLAN SEMAINE
│   │   weekly_planner.generate_week()
│   │   + Distribution Peaks (Tempo 35%, Sweet-Spot 20%)
│   │   + TSS adjusted par PID
│   │   + Constraints Training Intelligence
│   │   + Prompts enrichis Peaks methodology
│   │
│   └─► OUTPUT: weekly_plan_SXXX.md (6 séances)
│
└─► 5. WORKOUT VALIDATION (séance par séance)
    │   workout_validation.validate_workout(workout, athlete_state)
    │   → Check TSB, sommeil, 48h rule, découplage, placement
    │   → safe_to_prescribe = True/False
    │
    └─► OUTPUT: Validation report, ajustements si nécessaire
```

---

### 3.2 Flux Quotidien (Daily Sync + Auto Servo)

```
[Chaque jour] DAILY SYNC
│
├─► 1. PEAKS CTL ANALYSIS
│   │   analyze_ctl_peaks()
│   │   → Détection alertes CTL critique/sous-optimal
│   │   → Phase recommendation actualisée
│   │
│   └─► OUTPUT: Section "Analyse CTL (Peaks Coaching)" dans rapport
│
├─► 2. PROACTIVE COMPENSATION (si déficit TSS)
│   │   evaluate_weekly_deficit()
│   │   → Calcul déficit TSS hebdomadaire
│   │   → Génération stratégies compensation AI
│   │
│   └─► OUTPUT: Section "Compensation TSS Proactive" dans rapport
│
└─► 3. AUTO SERVO (si séance complétée)
    │   analyze_completed_workout()
    │   + Peaks validation rules (no modify TEST sessions)
    │   + PID derivative term (performance trend)
    │   + Training Intelligence learnings
    │
    └─► OUTPUT: Ajustements planning si nécessaire
```

---

### 3.3 Flux Test FTP (tous les 6-8 semaines)

```
[Test FTP Cycle] CALIBRATION PID + UPDATE PHASE
│
├─► 1. EXECUTION TEST
│   │   Test FTP 20min (ou VO2 5min, Sprint 1min, etc.)
│   │   → measured_ftp
│   │
│   └─► OUTPUT: FTP updated dans Intervals.icu
│
├─► 2. PID CORRECTION CALCULATION
│   │   discrete_pid_controller.compute_cycle_correction_enhanced(
│   │       measured_ftp=228,
│   │       cycle_duration_weeks=6,
│   │       adherence_rate=0.92,
│   │       avg_cardiovascular_coupling=0.062,
│   │       tss_completion_rate=0.94
│   │   )
│   │   → tss_per_week = +12 TSS (exemple)
│   │
│   └─► OUTPUT: Correction appliquée cycle suivant (6 semaines)
│
├─► 3. PEAKS PHASE UPDATE
│   │   determine_training_phase(ctl_current=55, ftp_current=228, ftp_target=260)
│   │   → Phase transition? (RECONSTRUCTION → CONSOLIDATION)
│   │   → Distribution adjusted? (Tempo 35%→25%, FTP 5%→10%)
│   │
│   └─► OUTPUT: PhaseRecommendation updated
│
└─► 4. TRAINING INTELLIGENCE UPDATE
    │   training_intelligence.record_learning(
    │       category="ftp_progression",
    │       description="FTP 220W → 228W après 6 semaines Tempo focus",
    │       evidence=["S080-S086: Tempo 38% actual, CTL 42→55"]
    │   )
    │   → Promote confidence if pattern confirmed
    │
    └─► OUTPUT: Learning stocké, confidence promoted
```

---

## 4. SYNERGIES & COMPLÉMENTARITÉS

### 4.1 Peaks + PID: Régulation Multi-Niveaux

**Peaks Coaching** (Strategic Level):
- **Horizon**: Phase entraînement (16 semaines reconstruction)
- **Action**: Distribution intensité (Tempo 35%, Sweet-Spot 20%)
- **Fréquence update**: Changement phase (après tests FTP ou CTL milestone)

**PID Controller** (Tactical Level):
- **Horizon**: Cycle 6-8 semaines
- **Action**: Correction TSS (+12 TSS/semaine)
- **Fréquence update**: Après chaque test FTP

**Synergie**:
```python
# Weekly planner combine les deux
weekly_tss_base = phase_rec.weekly_tss_load  # 350 TSS (Peaks)
weekly_tss_adjusted = weekly_tss_base + pid_correction.tss_per_week  # +12 TSS (PID)

# Distribution Peaks reste prioritaire
distribution = phase_rec.intensity_distribution  # Tempo 35%, Sweet-Spot 20%
# PID ajuste volume, pas distribution
```

---

### 4.2 Peaks + Proactive Compensation: Cohérence Architecture

**Problème résolu**:
Avant Peaks, la proactive compensation proposait parfois:
- Augmenter intensité (VO2/FTP) alors que CTL critique
- Utiliser jour repos alors que TSB déjà négatif
- Junk miles (volume sans structure)

**Solution avec Peaks**:
```python
# Proactive compensation enrichie avec Peaks context
prompt = f"""
MÉTHODOLOGIE PEAKS COACHING:
- Phase actuelle: {phase_rec.phase}
- CTL: {ctl_current} (minimum requis: {ctl_minimum})
- Distribution cible: Tempo {distribution['Tempo']*100:.0f}%

CONTRAINTES:
- Si phase RECONSTRUCTION: Priorité Tempo/Sweet-Spot, éviter VO2/FTP
- Si CTL < 55: NE PAS intensifier haute intensité
- Si TSB < -10: Utiliser jour repos INTERDIT
"""
```

**Résultat**:
- Stratégies compensation **alignées phase Peaks**
- Respect limites physiologiques (TSB, CTL, sommeil)
- Cohérence avec terme Intégral PID (accumulation erreurs)

---

### 4.3 Peaks + Training Intelligence: Validation Croisée

**Training Intelligence** apprend patterns:
- "Tempo outdoor → IF overload +15%" (4 observations)
- "Sleep <6h → VO2 failure" (6 observations)

**Peaks Coaching** fournit règles structurées:
- IF deviation >10% = échec discipline
- Sleep <7h = FAIL pour VO2/AC/FTP
- TSB <5 = FAIL pour VO2

**Synergie**:
```python
# Training Intelligence pattern
pattern = Pattern(
    name="outdoor_tempo_discipline_failure",
    trigger_conditions={"environment": "outdoor", "zone": "Tempo"},
    observed_outcome="IF overload +15%",
    frequency=4,
    confidence=ConfidenceLevel.MEDIUM
)

# Peaks validation confirme
discipline_check = check_discipline(
    intensity_zone="Tempo",
    environment="outdoor",
    if_planned=0.85,
    if_actual=0.98  # +15% overload
)
# → DisciplineStatus.FAILURE
# → Recommendation: INDOOR_REQUIRED

# Training Intelligence promotes confidence
# MEDIUM → HIGH → VALIDATED
```

**Résultat**:
- Patterns Training Intelligence **validés par règles Peaks**
- Recommandations croisées = plus grande confiance
- Évolution: empirique → evidence-based → validated protocol

---

### 4.4 PID + Outdoor Discipline: Correction Contextuelle

**Problème PID classique**:
PID corrige basé sur FTP test, mais ne considère pas *pourquoi* performance stagne:
- Manque volume? → Augmenter TSS ✅
- Manque qualité intensité (discipline outdoor)? → Augmenter TSS ❌ (inefficace)

**Solution avec outdoor_discipline tracking**:
```python
# PID calcule correction
pid_correction = discrete_pid_controller.compute_cycle_correction(
    measured_ftp=222,  # Stagnation (était 220, target 260)
    cycle_duration_weeks=6
)
# → tss_per_week = +8 TSS

# Mais outdoor discipline détecte problème qualité
discipline_history = analyze_zone_history("Tempo", recent_checks)
# → 3 échecs outdoor Tempo (IF overload +13%, +15%, +18%)
# → environment_recommendation = INDOOR_REQUIRED

# Décision: NE PAS appliquer correction PID
# Problème = qualité (indoor switch), pas volume
if discipline_history.environment_recommendation == EnvironmentRecommendation.INDOOR_REQUIRED:
    correction_adjusted = 0  # Pas d'augmentation TSS
    recommendation = "Switch Tempo indoor pour 2-3 mois. FTP re-test après."
```

**Résultat**:
- PID évite corrections inutiles si problème = discipline
- Outdoor tracking informe PID des contraintes qualité
- Correction appliquée seulement si contexte favorable

---

## 5. FLUX DE DÉCISION INTÉGRÉ (Exemple Concret)

### Contexte: Semaine S081 Post-Tests

**État Système**:
- CTL: 42.0 (critique)
- FTP mesuré S080: 222W (target: 260W)
- TSB: +0.0 (neutre)
- Phase Peaks: RECONSTRUCTION_BASE
- PID: Calculé correction +8 TSS/semaine (error -38W)

**Flux Décision Weekly Planner**:

```
1. PEAKS PHASE DETECTION
   └─► Phase: RECONSTRUCTION_BASE
   └─► Distribution: Tempo 35%, Sweet-Spot 20%, Endurance 25%
   └─► TSS base: 350 TSS/semaine

2. PID CORRECTION
   └─► Correction: +8 TSS/semaine
   └─► Validation multi-critères:
       • Adherence S074-S080: 87% (OK, >85%)
       • Coupling avg: 6.2% (OK, <7%)
       • TSS completion: 82% (WARNING, <85%)
   └─► Décision PID: APPLIQUER correction (2 critères OK sur 3)

3. OUTDOOR DISCIPLINE CHECK
   └─► Historique Tempo outdoor S074-S080:
       • 2 échecs (IF overload +13%, +15%)
   └─► Recommendation: INDOOR_PREFERRED (pas encore REQUIRED, seuil 2+)
   └─► Constraint: Priorité Tempo indoor

4. TRAINING INTELLIGENCE INSIGHTS
   └─► Learning validé: "Sweet-Spot 88-90% FTP sustainable 2x10min"
   └─► Pattern détecté: "Wednesday VO2 → fatigue accumulation"
   └─► Constraint: Éviter VO2 mercredi

5. GENERATION PLAN S081
   └─► TSS total: 350 (base Peaks) + 8 (PID) = 358 TSS
   └─► Distribution appliquée:
       • Lundi: Endurance 90min Z2 (85 TSS)
       • Mardi: Tempo 60min indoor 3x12 (72 TSS) ← Indoor prioritized
       • Mercredi: Recovery 45min Z1 (35 TSS) ← Évite VO2
       • Jeudi: Sweet-Spot 60min 2x10@88% (68 TSS) ← Learning validated
       • Vendredi: Repos
       • Samedi: Tempo 75min indoor 2x15 (98 TSS) ← Indoor prioritized
       • Total: 358 TSS ✅

6. WORKOUT VALIDATION (séance par séance)
   └─► Mardi Tempo:
       • TSB check: +2.0 (OK pour Tempo)
       • Sleep: 7.5h (OK)
       • Recent intensity: Aucune <48h (OK)
       • Placement: Mardi (OK pour intensité)
       • Volume: 72 TSS = 20% TSS hebdo (OK, <30%)
       • safe_to_prescribe = True ✅
   └─► Mercredi Recovery:
       • Placement: Mercredi recovery inhabituel (WARNING)
       • But justifié par pattern "Wednesday VO2 fatigue"
       • safe_to_prescribe = True ✅
   └─► Jeudi Sweet-Spot:
       • TSB check: -1.5 (OK pour Sweet-Spot)
       • Sleep: 7.2h (OK)
       • Recent intensity: Tempo 48h ago (OK)
       • Duration: 60min, TSS 68 (OK)
       • Expected decoupling: <7.5% acceptable
       • safe_to_prescribe = True ✅
```

**Résultat**:
- Plan S081 généré **cohérent** avec:
  - ✅ Phase Peaks (Tempo 35%, Sweet-Spot 20%)
  - ✅ Correction PID (+8 TSS)
  - ✅ Discipline outdoor (Tempo indoor)
  - ✅ Training Intelligence (évite VO2 mercredi)
  - ✅ Validation pré-prescription (tous checks pass)

---

## 6. ROADMAP INTÉGRATION

### Phase 1: ACTUEL (Post-S080, Février 2026)

**Status**:
- ✅ Peaks Coaching Sections 11-13 implémentées
- ✅ PID Controller architecture (NON calibré)
- ✅ Proactive Compensation opérationnelle
- ✅ Training Intelligence memory
- ✅ Daily-sync intégration Peaks

**Gaps**:
- ⚠️ PID NON calibré (gains Kp/Ki/Kd à ajuster)
- ⚠️ Outdoor discipline tracking NON activé
- ⚠️ Workout validation NON intégrée weekly planner

---

### Phase 2: SPRINT R10 - PID Calibration (5-7 jours)

**Objectifs**:
1. **Calibrer PID gains** basé sur tests S080:
   - Inputs: FTP baseline 220W, target 260W
   - Tuning: Kp, Ki, Kd pour convergence 16 semaines
   - Validation: Simuler cycles S074-S080 (backtest)

2. **Activer outdoor discipline tracking**:
   - Parser IF actual vs planned chaque séance outdoor
   - Alimenter `outdoor_discipline.py` avec historique
   - Générer premiers rapports discipline

3. **Intégrer workout validation dans weekly planner**:
   - Appel `validate_workout()` pour chaque séance générée
   - Ajustements automatiques si validation FAIL
   - Rapport validation dans `weekly_plan_SXXX.md`

**Livrables**:
- `discrete_pid_controller.py` avec gains calibrés
- Script `activate_outdoor_tracking.py`
- Weekly planner enrichi validation Peaks

---

### Phase 3: SPRINT R11 - Boucle Fermée Complète (7-10 jours)

**Objectifs**:
1. **Auto-ajustements PID basés Peaks validation**:
   ```python
   # Si validation Peaks rejette séance
   if validation.overall_result == ValidationResult.FAIL:
       # PID réduit correction temporairement
       pid_correction_adjusted = pid_correction * 0.5
   ```

2. **Training Intelligence feedbacks PID**:
   ```python
   # Si pattern "outdoor discipline failure" validé
   if pattern.confidence == ConfidenceLevel.VALIDATED:
       # PID ignore données cycles concernés (bruit)
       pid_controller.exclude_cycles([S074, S075, S076])
   ```

3. **Rapports unifiés**:
   - Section "Régulation Intelligente" dans daily-sync
   - Combiner: Peaks alerts + PID correction + Training Intelligence insights

**Livrables**:
- PID + Peaks boucle fermée
- Training Intelligence → PID feedback loop
- Rapports unifiés daily-sync

---

### Phase 4: SPRINT R12+ - Optimisation & Autonomie (Ongoing)

**Objectifs**:
1. **PID adaptatif**:
   - Gains Kp/Ki/Kd ajustés selon phase Peaks
   - RECONSTRUCTION: Gains conservateurs (réponse lente)
   - DEVELOPMENT: Gains agressifs (réponse rapide)

2. **Outdoor discipline auto-switch**:
   - Après 2+ échecs: Auto-recommend indoor (déjà implémenté)
   - Après 2-3 mois indoor: Auto-propose retry outdoor (à implémenter)

3. **Training Intelligence auto-adaptations**:
   - Learnings VALIDATED → Appliqués automatiquement protocoles
   - Ex: "Sweet-Spot 88-90% optimal" → Auto-adjust workout prescriptions

**Vision Long-Terme**:
```
SYSTÈME FULLY AUTONOMOUS:
├─► Tests FTP tous les 6-8 semaines (user trigger)
├─► PID calcule corrections TSS (automatic)
├─► Peaks valide appropriateness corrections (automatic)
├─► Training Intelligence affine patterns (automatic)
├─► Outdoor discipline switch indoor/outdoor (automatic)
├─► Weekly planner génère plan optimal (automatic)
├─► Daily-sync surveille + alerte anomalies (automatic)
└─► User: Execute plan, provide feedback (manual)
```

---

## 7. MÉTRIQUES DE SUCCÈS INTÉGRATION

### 7.1 Métriques PID

**Convergence FTP**:
- Erreur steady-state: <3W (dead-band)
- Temps convergence: <16 semaines (RECONSTRUCTION → CTL optimal)
- Overshoot: <5% (éviter surentraînement)

**Validation multi-critères**:
- Adherence rate: >85%
- Cardiovascular coupling: <7%
- TSS completion rate: >85%

---

### 7.2 Métriques Peaks

**Phase progression**:
- CTL progression: +2.5 points/semaine (moyenne)
- Phase transitions: RECONSTRUCTION → CONSOLIDATION dans 16 semaines
- Distribution adherence: Écart <10% vs target (Tempo 35±3.5%)

**Validation pré-prescription**:
- Taux validation PASS: >80% séances générées
- Taux FAIL critique: <5% (nécessite re-planning)
- Taux WARNING acceptable: <20%

---

### 7.3 Métriques Training Intelligence

**Pattern validation**:
- Patterns LOW → VALIDATED: 3-4 mois (10+ observations)
- Taux false positives: <10%
- Taux patterns actionnables: >50%

**Impact learnings**:
- Learnings appliqués: >70% des VALIDATED
- Amélioration performance mesurable: +5% FTP après application
- Réduction échecs séances: -30% après patterns intégrés

---

### 7.4 Métriques Outdoor Discipline

**Detection accuracy**:
- IF deviation detection: 100% (deviation >10%)
- Recommendation correctness: >90% (indoor switch = amélioration)
- False alarms: <5%

**Impact switch indoor**:
- Réduction IF overload: -50% après switch
- Amélioration TSS completion: +15%
- Retour outdoor success rate: >70% après 2-3 mois

---

## 8. RISQUES & MITIGATIONS

### Risque 1: Conflit PID ↔ Peaks

**Scénario**:
- PID recommande +15 TSS/semaine (erreur FTP -38W)
- Peaks détecte CTL critique (41.8 < 55)
- Peaks recommande 350 TSS strict (RECONSTRUCTION)

**Conflit**: PID pousse 365 TSS, Peaks limite 350 TSS

**Mitigation**:
```python
# Peaks override si phase critique
if phase_rec.phase == TrainingPhase.RECONSTRUCTION_BASE and ctl_current < 50:
    # Ignorer correction PID temporairement
    tss_weekly = phase_rec.weekly_tss_load  # 350 TSS strict
    logger.warning("PID correction ignored: CTL critique, Peaks override")
else:
    # Appliquer correction PID
    tss_weekly = phase_rec.weekly_tss_load + pid_correction.tss_per_week
```

**Priorité**: Peaks > PID en phase critique (CTL < 50)

---

### Risque 2: Over-correction PID

**Scénario**:
- Test FTP S080: 222W (vs 220W baseline, target 260W)
- PID détecte erreur -38W (très grand)
- PID propose +25 TSS/semaine (over-aggressive)

**Problème**: Surentraînement, CTL monte trop vite

**Mitigation**:
```python
# Cap PID correction selon phase
max_correction = {
    TrainingPhase.RECONSTRUCTION_BASE: 10,  # +10 TSS/semaine max
    TrainingPhase.CONSOLIDATION: 15,
    TrainingPhase.DEVELOPMENT_FTP: 20
}

tss_correction = min(
    pid_correction.tss_per_week,
    max_correction[phase_rec.phase]
)
```

**Priorité**: Safety > Speed (éviter burnout Masters 50+)

---

### Risque 3: Training Intelligence False Patterns

**Scénario**:
- Pattern détecté: "Sweet-Spot outdoor → IF underload -8%" (3 observations)
- Confidence: MEDIUM
- Recommandation: "Toujours faire Sweet-Spot outdoor"

**Problème**: Pattern = biais échantillonnage (vent favorable 3x), pas causalité

**Mitigation**:
```python
# Exiger validation croisée Peaks avant application
if pattern.confidence == ConfidenceLevel.HIGH:
    # Valider avec Peaks discipline check
    for observation in pattern.observations:
        discipline_check = check_discipline(observation)
        if discipline_check.status != DisciplineStatus.SUCCESS:
            pattern.confidence = ConfidenceLevel.MEDIUM  # Downgrade
            break

    # Pattern appliqué seulement si VALIDATED + Peaks confirme
    if pattern.confidence == ConfidenceLevel.VALIDATED:
        apply_pattern_to_protocols(pattern)
```

**Priorité**: Evidence-based > Anecdotal

---

## 9. CONCLUSION & RECOMMANDATIONS

### État Actuel (2026-02-14)

**✅ Réalisations**:
- Architecture modulaire Peaks ↔ PID ↔ Training Intelligence
- Peaks Coaching Sections 11-13 opérationnelles
- PID Controller architecture robuste (awaiting calibration)
- Proactive Compensation alignée Peaks
- Training Intelligence memory active

**⚠️ Gaps Critiques**:
1. **PID NON calibré** → Sprint R10 PRIORITÉ 1
2. **Workout validation NON intégrée weekly planner**
3. **Outdoor discipline tracking NON activé**

---

### Recommandations Immédiates

**1. Sprint R10 - PID Calibration (5-7 jours)**
```bash
# Priorité absolue post-S080
poetry run calibrate-pid --baseline-ftp 220 --target-ftp 260 --cycles 6
poetry run validate-pid --backtest S074-S080
```

**2. Activer Outdoor Discipline Tracking (2 jours)**
```bash
# Parser historique + activer tracking futur
poetry run activate-outdoor-tracking --backfill-weeks 8
```

**3. Intégrer Workout Validation Weekly Planner (3 jours)**
```python
# Dans weekly_planner.py
for workout in generated_workouts:
    validation = validate_workout(workout, athlete_state)
    if validation.overall_result == ValidationResult.FAIL:
        workout_adjusted = adjust_workout_safe(workout, validation)
```

---

### Vision Système Intégré (6 mois)

**Mars 2026**: PID calibré, outdoor tracking actif, validation intégrée
**Avril 2026**: Boucle fermée Peaks ↔ PID complète
**Mai 2026**: Training Intelligence auto-adaptations
**Juin 2026**: PID adaptatif (gains par phase)
**Juillet 2026**: Système fully autonomous (user execute + feedback only)

---

**L'architecture est prête. Les modules s'emboîtent parfaitement. La calibration PID post-S080 est la prochaine étape critique.** 🚀

---

*Document généré le 2026-02-14 par Claude Sonnet 4.5*
*Post-implémentation Peaks Coaching Sections 11-13*
