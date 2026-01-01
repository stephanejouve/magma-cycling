# Documentation Sprints - Cyclisme Training Logs

Ce répertoire contient la documentation des sprints de développement et les livrables MOA.

## Structure

```
sprints/
├── R1/                                # Sprint R1 - Infrastructure de base
│   └── LIVRAISON_MOA_SPRINT_R1.md    # Livrable MOA Sprint R1
│
└── R2/                                # Sprint R2 - Centralisation CTL/ATL/TSB
    ├── LIVRAISON_MOA_SPRINT_R2.md    # Livrable complet Sprint R2
    ├── REPONSE_MOA_SPRINT_R2.md      # Réponses aux 7 questions MOA
    └── SPRINT_R2_VALIDATION_S074.md  # Validation sur données réelles S074
```

## Sprints

### Sprint R1 - Infrastructure de Base
**Date:** Décembre 2025
**Objectifs:**
- Mise en place infrastructure projet
- Workflows de base
- Documentation initiale

**Documentation:** [R1/LIVRAISON_MOA_SPRINT_R1.md](R1/LIVRAISON_MOA_SPRINT_R1.md)

---

### Sprint R2 - Centralisation CTL/ATL/TSB + Configuration
**Date:** 2026-01-01
**Status:** ✅ TERMINÉ - 100%

**Objectifs:**
- ✅ Centraliser extraction CTL/ATL/TSB (8 fichiers migrés)
- ✅ Externaliser configuration (17 variables .env)
- ✅ Créer modules config/ (athlete_profile, thresholds)
- ✅ Créer utilities utils/metrics.py (6 fonctions)
- ✅ Tests complets (48 nouveaux tests, 100% passing)
- ✅ Validation S074 sur données réelles

**Résultats:**
- 3 nouveaux modules créés
- 8 fichiers migrés (~150 lignes dupliquées éliminées)
- 17 variables d'environnement ajoutées
- 48 nouveaux tests (404 tests total)
- 0 régression

**Documentation:**
- [R2/LIVRAISON_MOA_SPRINT_R2.md](R2/LIVRAISON_MOA_SPRINT_R2.md) - Livrable complet
- [R2/REPONSE_MOA_SPRINT_R2.md](R2/REPONSE_MOA_SPRINT_R2.md) - Réponses MOA détaillées
- [R2/SPRINT_R2_VALIDATION_S074.md](R2/SPRINT_R2_VALIDATION_S074.md) - Validation production

---

## Format des Livrables

Chaque sprint contient:

1. **LIVRAISON_MOA_SPRINT_XX.md**
   - Résumé exécutif
   - Objectifs atteints
   - Modules créés
   - Migrations effectuées
   - Tests et validation
   - Métriques du sprint

2. **REPONSE_MOA_SPRINT_XX.md** (si applicable)
   - Réponses aux questions MOA
   - Clarifications techniques
   - Justifications des choix d'architecture

3. **SPRINT_XX_VALIDATION_YYY.md** (si applicable)
   - Validation sur données réelles
   - Tests end-to-end
   - Preuves de fonctionnement

---

## Prochains Sprints

### Sprint R2.1 (Optionnel - P3)
**Objectif:** Advanced Metrics Utilities
- 5 fonctions avancées (weekly trends, peak detection, ramp rate, recovery recommendations)
- 15-20 tests additionnels

### Sprint R3 (Proposé - P2)
**Objectif:** Recovery Monitoring Pipeline
- Data pipeline HRV/Sleep/HR
- RecoveryAnalyzer activation
- Integration Garmin/Whoop/Oura

---

**Généré le:** 2026-01-01
**Maintenu par:** Équipe Cyclisme Training Logs
