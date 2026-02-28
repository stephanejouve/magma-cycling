# Sprint R10 - PID Calibration Complete 🎯

**Date début**: 2026-02-15 (Demain)
**Durée estimée**: 5-7 jours
**Priorité**: P0 (CRITIQUE)
**Status**: READY TO START ✅

---

## PRÉREQUIS VALIDÉS ✅

### Tests S080 Complétés
- ✅ S080-01: Activation Légère (40min, 30 TSS) - 2026-02-09
- ✅ S080-02: Test FTP 20min (40.5min, 36 TSS) - 2026-02-10
- ✅ S080-03: Test VO2Max 5min (41min, 32 TSS) - 2026-02-11
- ✅ S080-04: Récupération Active (35min, 25 TSS) - 2026-02-12
- ✅ S080-05: Test Sprint 5sec (40.5min, 27 TSS) - 2026-02-13
- ✅ S080-06: Test Anaérobie 1min (43.5min, 38 TSS) - 2026-02-14

**Résultats attendus** (à extraire Intervals.icu):
- FTP baseline: 220W → FTP mesuré: ???W (test 20min S080-02)
- VO2max 5min: ???W
- Sprint 5sec: ???W
- Anaérobie 1min: ???W

### Architecture Prête
- ✅ `discrete_pid_controller.py` implémenté (gains par défaut)
- ✅ Peaks Coaching intégré (validation + contraintes)
- ✅ Training Intelligence memory opérationnelle
- ✅ Proactive Compensation active (terme Intégral I)
- ✅ Architecture documentée (INTEGRATION_PEAKS_PID_INTELLIGENCE.md)

### Données Disponibles
- ✅ 49 jours historique (depuis S074 environ)
- ✅ CTL/ATL/TSB tracking actif
- ✅ Tests FTP précédents baseline (sem42/2025 si dispo)

---

## OBJECTIFS SPRINT R10

### 1. Calibration Gains PID (Kp, Ki, Kd)

**Méthode**: Ziegler-Nichols adapté systèmes discrets lents

**Étapes**:
1. Extraire FTP tests S080 depuis Intervals.icu
2. Calculer baseline: FTP_initial = 220W (connu), FTP_measured_S080 = ???W
3. Estimer réponse système (time constant τ, delay L)
4. Calculer gains théoriques Ziegler-Nichols
5. Ajuster gains pour Masters 50+ (response lente, conservateur)
6. Valider par simulation backtest S074-S080

**Formules Ziegler-Nichols (PID discret)**:
```python
# Méthode empirique basée step response
K = delta_output / delta_error  # Process gain
τ = time_constant  # Semaines pour atteindre 63.2%
L = delay  # Semaines latence réponse

# Gains PID
Kp = 1.2 / (K * L)
Ki = Kp / (2 * L)
Kd = Kp * L / 2

# Ajustements Masters 50+ (plus conservateur)
Kp *= 0.8  # -20% réactivité
Ki *= 0.5  # -50% accumulation
Kd *= 0.8  # -20% anticipation
```

**Gains actuels (à valider)**:
- Kp = 0.008
- Ki = 0.001
- Kd = 0.12

**Gains attendus post-calibration**:
- Kp = 0.006-0.010 (ajusté selon réponse réelle)
- Ki = 0.0008-0.0015
- Kd = 0.10-0.15

---

### 2. Seuils Validation Multi-Critères

**Implémentation**: `compute_cycle_correction_enhanced()`

**Critères validation** (déjà dans code):
1. **Adherence rate**: >85% (séances complétées vs planifiées)
2. **Cardiovascular coupling**: <7% (découplage moyen)
3. **TSS completion rate**: >85% (TSS réel vs prévu)

**Action si validation FAIL**:
```python
if not validation["validated"]:
    # Réduire correction PID de 50%
    tss_correction_adjusted = tss_correction * 0.5
    warning = "Correction réduite: validation multi-critères non satisfaite"
```

**Nouveaux seuils à ajouter** (Peaks integration):
```python
# Seuil 4: CTL minimum (Peaks)
ctl_minimum_for_ftp = (ftp_current / 220) * 55
if ctl_current < ctl_minimum_for_ftp:
    validation["ctl_check"] = False
    recommendation = "Attendre CTL ≥ minimum avant correction agressive"

# Seuil 5: TSB acceptable
if tsb_current < -15:  # Fatigue excessive
    validation["tsb_check"] = False
    recommendation = "Semaine récupération avant correction PID"

# Seuil 6: Outdoor discipline (nouveau module)
if outdoor_discipline_failures >= 2:
    validation["quality_check"] = False
    recommendation = "Problème qualité (discipline), pas volume. Switch indoor."
```

---

### 3. Système Corrections TSS Automatiques

**Flux intégration Weekly Planner**:

```python
# weekly_planner.py - Génération semaine S081+

# 1. Détection phase Peaks
phase_rec = determine_training_phase(
    ctl_current=41.8,
    ftp_current=220,
    ftp_target=260,
    athlete_age=54
)
# → RECONSTRUCTION_BASE, 350 TSS base, Tempo 35%

# 2. PID correction (si test récent S080)
if test_ftp_recent:
    pid_controller = DiscretePIDController(
        kp=0.008,  # Gains calibrés
        ki=0.001,
        kd=0.12,
        setpoint=260
    )

    correction = pid_controller.compute_cycle_correction_enhanced(
        measured_ftp=222,  # Exemple résultat S080
        cycle_duration_weeks=6,
        adherence_rate=0.87,
        avg_cardiovascular_coupling=0.062,
        tss_completion_rate=0.82
    )

    if correction["validation"]["validated"]:
        tss_weekly_adjusted = phase_rec.weekly_tss_load + correction["tss_per_week"]
    else:
        tss_weekly_adjusted = phase_rec.weekly_tss_load
        logger.warning("PID correction rejected: validation failed")

# 3. Peaks override si critique
if phase_rec.ctl_current < 50:
    tss_weekly_adjusted = phase_rec.weekly_tss_load  # Ignore PID
    logger.info("Peaks override: CTL critique, TSS strict")

# 4. Génération plan avec TSS adjusted
weekly_plan = generate_weekly_plan(
    tss_target=tss_weekly_adjusted,
    distribution=phase_rec.intensity_distribution,
    constraints=training_intelligence.get_constraints()
)
```

**CLI Command**:
```bash
# Nouveau: Calibration PID
poetry run calibrate-pid --test-week S080 --baseline-ftp 220 --target-ftp 260

# Nouveau: Apply PID correction manually
poetry run apply-pid-correction --week S081 --measured-ftp 222

# Nouveau: Simulate PID response
poetry run simulate-pid --cycles 10 --initial-ftp 220 --target-ftp 260
```

---

### 4. Tests Automatisés (≥20 scenarios)

**Fichier**: `tests/intelligence/test_discrete_pid_calibration.py`

**Scénarios à tester**:

1. **Convergence normale** (10 tests)
   - FTP 220W → 260W en 16 semaines
   - Différents gains Kp/Ki/Kd
   - Validation steady-state error <3W

2. **Overshoot prevention** (3 tests)
   - Correction excessive détectée
   - Overshoot <5% (max 263W pour target 260W)
   - Anti-windup actif

3. **Validation multi-critères** (4 tests)
   - Adherence <85% → Correction réduite
   - Coupling >7% → Warning
   - TSS completion <85% → Correction rejetée
   - CTL critique → Peaks override

4. **Peaks integration** (3 tests)
   - Phase RECONSTRUCTION: Correction limitée
   - CTL <50: PID disabled
   - Distribution Peaks maintenue

**Exemple test**:
```python
def test_pid_convergence_reconstruction_phase():
    """Test PID converges with Peaks RECONSTRUCTION phase constraints."""
    controller = DiscretePIDController(
        kp=0.008, ki=0.001, kd=0.12, setpoint=260
    )

    ftp_current = 220
    ctl_current = 42.0

    # Simulate 16 weeks (4 cycles x 4 weeks)
    for cycle in range(4):
        correction = controller.compute_cycle_correction_enhanced(
            measured_ftp=ftp_current,
            cycle_duration_weeks=4,
            adherence_rate=0.90,
            avg_cardiovascular_coupling=0.05,
            tss_completion_rate=0.92
        )

        # Apply correction (simplified model)
        ftp_current += correction["tss_per_week"] / 12.5  # +1W per 12.5 TSS
        ctl_current += 2.5  # +2.5 CTL per week

        # Peaks validation
        phase = determine_training_phase(ctl_current, ftp_current, 260)
        if phase.phase == TrainingPhase.RECONSTRUCTION_BASE and ctl_current < 50:
            # Should limit correction
            assert correction["tss_per_week"] <= 10, "Correction too aggressive for RECONSTRUCTION"

    # Verify convergence after 16 weeks
    assert ftp_current >= 240, "FTP should progress significantly"
    assert ftp_current <= 263, "FTP should not overshoot >5%"
```

---

## PLAN D'ACTION 5 JOURS

### Jour 1 (Lundi 2026-02-15) - EXTRACTION & ANALYSE

**Matin**:
- [ ] Extraire résultats tests S080 depuis Intervals.icu API
  ```bash
  poetry run extract-test-results --week S080 --output data/tests/S080_results.json
  ```
- [ ] Analyser FTP baseline vs measured
- [ ] Calculer CTL progression S074-S080
- [ ] Documenter metrics: adherence, coupling, TSS completion

**Après-midi**:
- [ ] Calculer gains théoriques Ziegler-Nichols
- [ ] Ajuster gains Masters 50+ (conservateurs)
- [ ] Simuler réponse système avec gains théoriques
- [ ] Comparer vs gains actuels (0.008, 0.001, 0.12)

**Livrable**: Document `PID_CALIBRATION_ANALYSIS_S080.md` avec gains recommandés

---

### Jour 2 (Mardi) - IMPLÉMENTATION CALIBRATION

**Matin**:
- [ ] Implémenter `calibrate_pid.py` script CLI
- [ ] Intégrer méthode Ziegler-Nichols
- [ ] Ajouter validation backtest S074-S080
- [ ] Générer rapport calibration automatique

**Après-midi**:
- [ ] Tester calibration sur données S074-S080
- [ ] Comparer prédictions PID vs réalité
- [ ] Ajuster gains si nécessaire
- [ ] Valider convergence théorique (16 semaines FTP 220→260)

**Livrable**: CLI `poetry run calibrate-pid` opérationnel

---

### Jour 3 (Mercredi) - VALIDATION MULTI-CRITÈRES

**Matin**:
- [ ] Implémenter seuils validation Peaks (CTL, TSB)
- [ ] Ajouter validation outdoor discipline
- [ ] Enrichir `compute_cycle_correction_enhanced()`
- [ ] Tester validation avec cas edge (CTL<50, TSB<-15, etc.)

**Après-midi**:
- [ ] Intégrer validation dans weekly planner
- [ ] Implémenter Peaks override logic
- [ ] Tester flux complet: Peaks detection → PID correction → Validation
- [ ] Documenter règles override

**Livrable**: Validation multi-critères opérationnelle (6 critères)

---

### Jour 4 (Jeudi) - INTÉGRATION WEEKLY PLANNER

**Matin**:
- [ ] Modifier `weekly_planner.py` pour appel PID
- [ ] Implémenter logique TSS adjustment
- [ ] Ajouter section rapport "PID Correction Applied"
- [ ] Tester génération S081 avec correction PID

**Après-midi**:
- [ ] Implémenter CLI commands:
  - `poetry run apply-pid-correction --week S081`
  - `poetry run simulate-pid --cycles 10`
- [ ] Intégrer rapports PID dans daily-sync
- [ ] Tester flux end-to-end S080 → S081

**Livrable**: Weekly planner intégré PID, génération S081 avec correction

---

### Jour 5 (Vendredi) - TESTS & DOCUMENTATION

**Matin**:
- [ ] Écrire 20+ tests automatisés PID
- [ ] Valider tous scenarios (convergence, overshoot, validation, Peaks)
- [ ] Atteindre >90% coverage PID modules
- [ ] Fixer bugs détectés par tests

**Après-midi**:
- [ ] Documenter gains calibrés finaux
- [ ] Écrire guide utilisateur PID
- [ ] Mettre à jour ROADMAP (R10 → DONE)
- [ ] Préparer démo système complet

**Livrable**:
- Tests suite complète (≥20 tests passing)
- Documentation gains PID calibrés
- Sprint R10 DONE ✅

---

## MÉTRIQUES DE SUCCÈS

### Critères Validation Sprint

1. **PID Calibré** ✅
   - Gains Kp/Ki/Kd optimisés basés données réelles
   - Validation backtest S074-S080 (<10% erreur prédiction)
   - Convergence théorique 16 semaines validée

2. **Validation Multi-Critères** ✅
   - 6 critères implémentés (adherence, coupling, TSS, CTL, TSB, discipline)
   - Peaks override actif (CTL<50, phase RECONSTRUCTION)
   - Tests edge cases passent (100% coverage critères)

3. **Intégration Weekly Planner** ✅
   - Génération S081 avec correction PID réussie
   - Rapport "PID Correction Applied" dans weekly_plan.md
   - CLI commands opérationnels (calibrate, apply, simulate)

4. **Tests Automatisés** ✅
   - ≥20 tests scenarios PID
   - Coverage >90% modules PID
   - CI/CD passe (pre-commit hooks OK)

5. **Documentation** ✅
   - Gains calibrés documentés avec justification
   - Guide utilisateur PID rédigé
   - Architecture updated (INTEGRATION_PEAKS_PID_INTELLIGENCE.md)

---

## RISQUES & MITIGATIONS

### Risque 1: Tests S080 incomplets

**Impact**: Impossible calibrer sans FTP baseline
**Probabilité**: FAIBLE (tests semblent complétés)
**Mitigation**:
- Vérifier dès demain matin extraction résultats
- Si manquant: Utiliser baseline 220W + progression estimée
- Recalibrer quand tests disponibles

### Risque 2: Gains théoriques inadaptés

**Impact**: PID converge trop lent ou overshoot
**Probabilité**: MOYENNE (système complexe Masters 50+)
**Mitigation**:
- Approche itérative: gains théoriques → simulation → ajustement
- Validation backtest S074-S080 obligatoire
- Conservative approach: sous-estimer réactivité (Kp, Ki)

### Risque 3: Intégration Peaks complexe

**Impact**: Conflits logique Peaks ↔ PID
**Probabilité**: FAIBLE (architecture déjà documentée)
**Mitigation**:
- Suivre règles override documentées
- Peaks > PID en cas conflit
- Tests edge cases complets (CTL<50, TSB<-15, etc.)

### Risque 4: Tests automatisés chronophages

**Impact**: Jour 5 insuffisant pour 20+ tests
**Probabilité**: MOYENNE (tests PID peuvent être longs)
**Mitigation**:
- Paralléliser tests (pytest-xdist)
- Prioriser tests critiques (convergence, validation)
- Accepter 15+ tests si 20 pas atteignable

---

## RESSOURCES NÉCESSAIRES

### Données
- ✅ Tests S080 results (Intervals.icu API)
- ✅ Historique S074-S080 (49 jours)
- ✅ CTL/ATL/TSB metrics
- ✅ FTP baseline 220W (connu)

### Modules Existants
- ✅ `discrete_pid_controller.py` (architecture prête)
- ✅ `peaks_phases.py` (détection phase + distribution)
- ✅ `workout_validation.py` (validation pré-prescription)
- ✅ `training_intelligence.py` (memory patterns)
- ✅ `weekly_planner.py` (génération plans)

### Nouveaux Modules à Créer
- [ ] `scripts/calibrate_pid.py` (CLI calibration)
- [ ] `scripts/apply_pid_correction.py` (CLI apply)
- [ ] `scripts/simulate_pid.py` (CLI simulation)
- [ ] `tests/intelligence/test_discrete_pid_calibration.py` (test suite)

### Documentation à Créer/Mettre à Jour
- [ ] `PID_CALIBRATION_ANALYSIS_S080.md` (analyse gains)
- [ ] `PID_USER_GUIDE.md` (guide utilisateur)
- [ ] Update `INTEGRATION_PEAKS_PID_INTELLIGENCE.md` (gains calibrés)
- [ ] Update `ROADMAP.md` (R10 → DONE)

---

## NEXT STEPS (Demain Matin)

### Action Immédiate #1: Extraire Résultats S080

```bash
cd /Users/stephanejouve/magma-cycling

# Check tests S080 disponibles
poetry run python -c "
from magma_cycling.api.intervals_client import IntervalsClient
client = IntervalsClient()
events = client.get_events('2026-02-09', '2026-02-14')  # Semaine S080
tests = [e for e in events if 'TST' in e.get('name', '')]
print(f'Tests S080 trouvés: {len(tests)}')
for test in tests:
    print(f\"  - {test['name']}: {test.get('icu_training_load', 'N/A')} TSS\")
"
```

### Action Immédiate #2: Vérifier FTP Mesuré

```bash
# Extraire FTP test 20min (S080-02)
poetry run python -c "
from magma_cycling.api.intervals_client import IntervalsClient
client = IntervalsClient()
athlete = client.get_athlete()
print(f\"FTP actuel Intervals.icu: {athlete.get('ftp', 'N/A')}W\")
print(f\"CTL actuel: {athlete.get('ctl', 'N/A')}\")
print(f\"ATL actuel: {athlete.get('atl', 'N/A')}\")
print(f\"TSB actuel: {athlete.get('form', 'N/A')}\")
"
```

### Action Immédiate #3: Créer Structure Sprint

```bash
# Créer dossiers Sprint R10
mkdir -p project-docs/sprints/R10_PID_calibration
mkdir -p data/tests/S080
mkdir -p scripts/pid_tools

# Créer fichiers tracking
touch project-docs/sprints/R10_PID_calibration/DAILY_LOG.md
touch project-docs/sprints/R10_PID_calibration/PID_CALIBRATION_ANALYSIS.md
```

---

## CONCLUSION

**Status**: 🟢 **READY TO START**

**Prérequis**: ✅ TOUS VALIDÉS
- Tests S080 complétés
- Architecture Peaks intégrée
- Modules PID implémentés
- Documentation à jour

**Confiance**: 🎯 **HAUTE** (9/10)
- Architecture claire et documentée
- Plan d'action détaillé jour par jour
- Risques identifiés avec mitigations
- Métriques succès définies

**Recommandation**: 🚀 **GO FOR SPRINT R10 DEMAIN**

**Première action demain**: Extraire résultats tests S080 et vérifier FTP mesuré → Calibration gains théoriques → Simulation backtest

---

*Plan Sprint R10 créé le 2026-02-14*
*Prêt pour démarrage 2026-02-15* 🎯
