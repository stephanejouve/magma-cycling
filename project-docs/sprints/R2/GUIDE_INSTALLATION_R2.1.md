# Sprint R2.1 - Guide d'Installation Rapide

## 📦 Fichiers Livrés

**3 fichiers à intégrer :**

```
📂 Livrable Sprint R2.1/
├── metrics_advanced.py           # Module principal (715 lignes)
├── test_metrics_advanced.py      # Tests complets (405 lignes)
└── SPRINT_R2.1_DOCUMENTATION.md  # Documentation complète
```

---

## ⚡ Installation en 3 Étapes

### Étape 1 : Copier le Module Principal

```bash
# Copier vers le package utils/
cp metrics_advanced.py cyclisme_training_logs/utils/metrics_advanced.py
```

**Vérification :**
```bash
ls -lh cyclisme_training_logs/utils/metrics_advanced.py
# Expected: -rw-r--r--  1 user  group   27K Jan  1 12:00 metrics_advanced.py
```

---

### Étape 2 : Copier les Tests

```bash
# Copier vers tests/utils/
cp test_metrics_advanced.py tests/utils/test_metrics_advanced.py
```

**Vérification :**
```bash
ls -lh tests/utils/test_metrics_advanced.py
# Expected: -rw-r--r--  1 user  group   16K Jan  1 12:00 test_metrics_advanced.py
```

---

### Étape 3 : Exécuter la Test Suite

```bash
# Option 1: Tous les tests
poetry run pytest tests/ -v

# Option 2: Seulement tests Sprint R2.1
poetry run pytest tests/utils/test_metrics_advanced.py -v

# Option 3: Avec coverage
poetry run pytest tests/utils/test_metrics_advanced.py --cov=cyclisme_training_logs.utils.metrics_advanced
```

**Résultat Attendu :**
```
tests/utils/test_metrics_advanced.py::test_calculate_ramp_rate_weekly_increase PASSED
tests/utils/test_metrics_advanced.py::test_calculate_ramp_rate_biweekly PASSED
tests/utils/test_metrics_advanced.py::test_calculate_ramp_rate_declining PASSED
...
tests/utils/test_metrics_advanced.py::test_overtraining_risk_custom_thresholds PASSED

============ 33 passed in 0.12s ============
```

---

## ✅ Validation Finale

### Test d'Import

```bash
poetry run python3 -c "
from cyclisme_training_logs.utils.metrics_advanced import (
    calculate_ramp_rate,
    get_weekly_metrics_trend,
    detect_training_peaks,
    get_recovery_recommendation,
    format_metrics_comparison,
    detect_overtraining_risk
)
print('✅ All 6 functions imported successfully')
"
```

### Test Fonctionnel Rapide

```bash
poetry run python3 << 'EOF'
from cyclisme_training_logs.utils.metrics_advanced import detect_overtraining_risk

# Test CRITIQUE: Détection surmenage
result = detect_overtraining_risk(
    ctl=65.0,
    atl=120.0,
    tsb=-27.0,
    sleep_hours=5.5,
    profile={'age': 54, 'category': 'master', 'sleep_dependent': True}
)

print(f"Risk Level: {result['risk_level']}")
print(f"VETO: {result['veto']}")
print(f"Recommendation: {result['recommendation']}")

assert result['veto'] is True, "VETO should be triggered"
print("\n✅ detect_overtraining_risk() working correctly")
EOF
```

---

## 🔧 Intégration Workflows (Optionnel)

### rest_and_cancellations.py

**Ajout VETO Logic :**

```python
# Début du fichier
from cyclisme_training_logs.utils.metrics_advanced import detect_overtraining_risk

# Dans la fonction principale
def check_session_veto(wellness_data, athlete_profile):
    """Check if session should be vetoed due to overtraining risk."""
    
    ctl = wellness_data.get('ctl', 0)
    atl = wellness_data.get('atl', 0)
    tsb = wellness_data.get('ctl', 0) - wellness_data.get('atl', 0)
    sleep_hours = wellness_data.get('sleep_hours')
    
    risk = detect_overtraining_risk(
        ctl=ctl,
        atl=atl,
        tsb=tsb,
        sleep_hours=sleep_hours,
        profile=athlete_profile
    )
    
    if risk['veto']:
        return {
            'cancel_session': True,
            'reason': risk['recommendation'],
            'factors': risk['factors']
        }
    
    return {'cancel_session': False}
```

### weekly_planner.py

**Ajout Recovery Recommendations :**

```python
from cyclisme_training_logs.utils.metrics_advanced import get_recovery_recommendation

def adjust_weekly_plan(tsb, atl_ctl_ratio, athlete_profile):
    """Adjust weekly plan based on recovery needs."""
    
    rec = get_recovery_recommendation(tsb, atl_ctl_ratio, athlete_profile)
    
    if rec['priority'] in ['critical', 'high']:
        return {
            'reduce_intensity': True,
            'max_intensity_pct': rec['intensity_limit'],
            'max_duration_min': rec['duration_limit'],
            'add_rest_days': rec['rest_days']
        }
    
    return {'reduce_intensity': False}
```

---

## 📊 Métriques Sprint R2.1

**Code:**
- Lignes code: 715 (metrics_advanced.py)
- Lignes tests: 405 (test_metrics_advanced.py)
- Ratio tests/code: 57%

**Tests:**
- Total: 33 tests
- Coverage: 100%
- Temps exécution: ~0.12s

**Documentation:**
- Docstrings: Google Style
- Type hints: 100%
- Examples: Tous les fonctions

---

## 🚨 Points d'Attention

### 1. Fonction CRITIQUE

`detect_overtraining_risk()` est une fonction de SÉCURITÉ pour athlète master (54 ans).

**Utilisation obligatoire avant séances haute intensité (>85% FTP) :**

```python
risk = detect_overtraining_risk(ctl, atl, tsb, sleep_hours, profile)

if risk['veto']:
    # ANNULER LA SÉANCE
    log.warning(f"VETO: {risk['recommendation']}")
    cancel_session()
```

### 2. Thresholds Master Athlete

Les seuils par défaut sont **calibrés pour athlète master (50+ ans)** :

```python
# Defaults in detect_overtraining_risk()
{
    'tsb_critical': -25.0,      # VETO si TSB < -25
    'ratio_critical': 1.8,       # VETO si ATL/CTL > 1.8
    'sleep_veto': 5.5,           # VETO si sommeil < 5.5h
    'sleep_critical': 6.0,       # Critique si < 6h
}
```

**Athlètes seniors (20-40 ans)** peuvent utiliser thresholds plus permissifs.

### 3. Dépendances

Aucune dépendance externe. Module utilise uniquement :
- `typing` (standard library)
- `statistics` (standard library)

---

## 📋 Checklist Post-Installation

- [ ] `metrics_advanced.py` copié vers `cyclisme_training_logs/utils/`
- [ ] `test_metrics_advanced.py` copié vers `tests/utils/`
- [ ] Tests exécutés : `poetry run pytest tests/utils/test_metrics_advanced.py -v`
- [ ] 33/33 tests PASSING
- [ ] Import test réussi
- [ ] Test fonctionnel `detect_overtraining_risk()` validé
- [ ] (Optionnel) Intégration workflows
- [ ] (Optionnel) README.md mis à jour
- [ ] (Optionnel) CHANGELOG.md mis à jour

---

## 🎯 Prochains Sprints

**Sprint R3 - Planning Manager (P1 CRITICAL)**
- Gestion échéances et objectifs
- Calendrier entraînements
- Synchronisation Intervals.icu

**Sprint R4 - Date Utilities (P1 CRITICAL)**
- Calculs dates semaines
- Gestion périodes entraînement
- Helpers temporels

**Sprint R6 - Energy Systems Analysis (P2)**
- Analyse systèmes énergétiques
- Distribution zones
- Optimisation mixte aérobie/anaérobie

---

**Version:** 1.0  
**Date:** 2026-01-01  
**Sprint:** R2.1  
**Status:** ✅ READY FOR INTEGRATION
