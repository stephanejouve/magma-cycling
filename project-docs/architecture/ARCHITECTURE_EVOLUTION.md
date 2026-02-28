# Architecture Evolution - PID Controller

**Date:** 14 janvier 2026
**Décision:** MOA Analysis + PO Validation
**Sprint:** R9 (Consolidation)

---

## Contexte

### Architecture Initiale - PID Continu

**Implementation:** `magma_cycling/intelligence/pid_controller.py`

**Assumptions:**
```python
# Suppose mesure FTP fréquente (hebdomadaire)
controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)
correction = controller.compute(measured_value=current_ftp, dt=1.0)
# dt=1.0 → Correction chaque semaine
```

**Problème identifié (14 jan 2026):**

PO concern: *"notre valeur de consigne c'est la FTP correct ? [...] attention à bien intégrer les trois correction proportionnelle intégrale et dérivée, pour ne pas entrer en pompage"*

PO concern: *"la mesure de FTP n'est faite qu'entre deux cycle [...] je ne sais pas si sur la seule observation des workouts réussis on peut le faire"*

**Analyse MOA:**
- ❌ FTP mesurée uniquement tous les 6-8 semaines (tests programmés)
- ❌ Entre tests: FTP inconnue, estimation incertaine (±10-15W)
- ❌ PID Continu nécessite feedback fréquent → architecture invalide
- ⚠️ Risques: pompage, integral biaisé, derivative sans sens

---

## Architecture Cible - PID Discret

### Principe

**Sample-and-Hold sur cycles:**
```python
# Correction UNIQUEMENT lors test FTP validé
Test S001: FTP=200W → Correction: +8 TSS/semaine
  ↓ Application
S002-S007: +8 TSS (pas de PID)
  ↓ Nouveau test
Test S007: FTP=206W → Correction: +7 TSS/semaine
  ↓ Application
S008-S013: +7 TSS (pas de PID)
```

**Implementation:** `magma_cycling/intelligence/discrete_pid_controller.py`

```python
controller = DiscretePIDController(kp=0.008, ki=0.001, kd=0.12, setpoint=260)

# Appelé UNIQUEMENT lors test FTP
correction = controller.compute_cycle_correction(
    measured_ftp=206,              # Test réel S007
    cycle_duration_weeks=6,        # S001→S006 écoulés
)

# Résultat appliqué S008-S013 (6 semaines)
print(correction["tss_per_week"])  # +7 TSS
```

### Avantages

✅ **Adapté mesures sporadiques**
- Fréquence PID = fréquence tests FTP (6 semaines)
- dt effectif = cycle_duration_weeks (pas 1)
- Mesures FTP réelles (pas estimations)

✅ **Pas de pompage**
- Integral accumule sur cycles, pas semaines
- Derivative calculée entre tests (pas bruit hebdo)
- Dead-band ±3W (ignore variations naturelles)

✅ **Gains conservateurs**
- Kp=0.008 (vs 0.01 continu) → -20%
- Ki=0.001 (vs 0.002 continu) → -50%
- Kd=0.12 (vs 0.15 continu) → -20%

---

## Enhancement - Grandeurs Complémentaires

**Rationale PO:** *"on essaye et on réfléchi a d'autres grandeur à associer permettant de fiabiliser la boucle"*

### Grandeurs P0 (Prioritaires)

**1. Adherence Rate** (Discipline)
```python
# Observable: workout_adherence.jsonl (daily logs)
adherence = completed_workouts / planned_workouts  # Sur cycle

if adherence < 0.80:
    # Red flag: Discipline faible
    correction["tss_per_week"] *= 0.7  # Réduire gains
```

**2. Cardiovascular Coupling** (Qualité)
```python
# Observable: Découplage cardio per workout
avg_coupling = mean(découplage_workouts_cycle)  # %

if avg_coupling > 0.08:
    # Red flag: Surcharge détectée (qualité dégradée)
    correction["tss_per_week"] *= 0.6  # Réduire drastiquement
```

**3. TSS Completion Rate** (Capacité)
```python
# Observable: TSS réalisé vs planifié
tss_completion = tss_realized / tss_planned  # Sur cycle

if tss_completion < 0.85:
    # Red flag: Capacité insuffisante
    correction["tss_per_week"] = min(correction["tss_per_week"], 5)
```

### Architecture Enhanced

```python
correction = controller.compute_cycle_correction_enhanced(
    measured_ftp=206,
    cycle_duration_weeks=6,
    # Grandeurs complémentaires
    adherence_rate=0.92,              # ✅ Discipline OK
    avg_cardiovascular_coupling=0.062, # ✅ Qualité OK
    tss_completion_rate=0.94,         # ✅ Capacité OK
)

# Résultat avec validation
print(correction["validation"])
# {
#   "red_flags": [],
#   "warnings": [],
#   "confidence": 1.0,
#   "validated": True
# }
```

**Bénéfices fiabilisation:**
- Détection incohérences (FTP+gain mais découplage élevé)
- Ajustement contextuel (adherence faible → gains réduits)
- Warnings actionnables (surcharge masquée détectée)

---

## Tests Existants - Status

### test_pid_controller.py (30 tests)

**Valident mécanique de base:**
- ✅ P/I/D terms calculation
- ✅ Anti-windup saturation (±100W integral)
- ✅ Output saturation (±50 TSS)
- ✅ Convergence simulation
- ✅ Adaptive gains from intelligence

**Status:** CONSERVÉS (validation mécanique réutilisable)

**Note:** Architecture PID Continu (dt=1.0) remplacée mais formules P/I/D identiques. Tests restent valides pour mécanique.

### test_discrete_pid_controller.py (35+ tests)

**À créer:**
- Base PID Discret (28 tests)
- Enhanced validation (7+ tests)
- Simulation convergence cycles
- Validation multi-critères

---

## Décision Stratégique - Architecture Dual

### Phase 1: PID Discret Niveau Cycle (P0 - Immédiat)

**Scope:** PID Complet (P+I+D) sur mesures FTP tests (6-8 semaines)

**Implementation:** `discrete_pid_controller.py`
- Correction TSS cycle complet
- Validation grandeurs complémentaires
- Tests 35+ comprehensive

**Timeline:** 14 jan → ~2 fév (8-10h)

**Calibration:** 2 cycles observation (~12 semaines)

### Phase 2: Niveau Temps Réel (Conditionnel)

**Décision:** Post-calibration (~Fin mars 2026)

**SI PID Discret succès (critères validés):**
- ✅ AJOUTER Niveau 1 (Corrections P temps réel)
- ✅ Monitoring adherence hebdo
- ✅ Monitoring coupling post-séance
- ✅ Sprint 4-6h implémentation

**SI PID Discret échec:**
- ❌ ABANDONNER approche PID
- 🔄 EXPLORER alternatives (heuristiques, Kalman, autre)

**Critères succès PID Discret:**
```python
validation_criteria = {
    "ftp_progression": ">= +3W/cycle",
    "convergence": "Error décroissant",
    "stability": "Pas d'oscillations",
    "validation_quality": "Red flags <20% cycles",
}
```

---

## Timeline

```
14 jan 2026 : Analyse MOA → Biais identifié
14 jan 2026 : Décision PO → Option A validée
14 jan 2026 : Push tests PID Continu + ARCHITECTURE_EVOLUTION.md
14-21 jan   : Implémentation PID Discret Enhanced (8-10h)
~2 fév 2026 : Review MOA/PO + décision instrumentation
Mars 2026   : Calibration 2 cycles + décision Phase 2
```

---

## Références

- **Spec complète:** `DISCRETE_PID_ARCHITECTURE_SPEC.md` (MOA, 28KB)
- **Enhanced architecture:** Conversation MOA/PO 14 jan 2026
- **Tests PID Continu:** Commit 0d117f6 (baseline mécanique)

---

**Version:** 1.0.0
**Authors:** MOA (Analysis) + PO (Validation)
**Status:** APPROVED - Ready for implementation
