"""Sample data fixtures for reports testing.

Provides realistic test data for report generation and validation.

Author: Claude Code (Sprint R10 MVP)
Created: 2026-01-18
"""

# Sample week data for S076 (complete with all required fields)
SAMPLE_WEEK_DATA_S076 = {
    "week_number": "S076",
    "start_date": "2026-01-13",
    "end_date": "2026-01-19",
    "tss_planned": 450,
    "tss_realized": 423,
    "objectives": [
        "Valider protocole Z2 indoor 90min",
        "Tester capacité SST outdoor 3x8min",
        "Confirmer récupération post-bloc intensif",
    ],
    "activities": [
        {
            "id": "12345",
            "name": "Z2 Base Indoor - Test Protocol",
            "start_date": "2026-01-13T09:00:00",
            "type": "Ride",
            "moving_time": 5400,  # 90 min
            "tss": 85,
            "if_": 0.72,
            "np": 180,
            "avg_hr": 135,
            "indoor": True,
        },
        {
            "id": "12346",
            "name": "SST Intervals Outdoor 3x8",
            "start_date": "2026-01-15T14:00:00",
            "type": "Ride",
            "moving_time": 4200,  # 70 min
            "tss": 95,
            "if_": 0.88,
            "np": 220,
            "avg_hr": 155,
            "indoor": False,
        },
        {
            "id": "12347",
            "name": "Recovery Spin",
            "start_date": "2026-01-16T10:00:00",
            "type": "Ride",
            "moving_time": 3600,  # 60 min
            "tss": 42,
            "if_": 0.55,
            "np": 140,
            "avg_hr": 120,
            "indoor": True,
        },
    ],
    "wellness_data": {
        "hrv_avg": 58,
        "hrv_trend": "stable",
        "sleep_quality_avg": 7.2,
        "fatigue_score_avg": 3.5,
        "readiness_avg": 8.1,
    },
    "learnings": [
        {
            "type": "protocol_validation",
            "title": "Z2 Indoor Protocol Validated",
            "description": "90min Z2 indoor @ 72% IF maintenu sans dérive cardiaque",
            "session_id": "12345",
            "confidence": "high",
        },
        {
            "type": "performance_discovery",
            "title": "SST Outdoor Capacity Confirmed",
            "description": "3x8min SST @ 88% IF avec récupération complète inter-intervalles",
            "session_id": "12346",
            "confidence": "high",
        },
    ],
    "metrics_evolution": {
        "start": {"ctl": 100, "atl": 50, "tsb": 50, "hrv": 58},
        "end": {"ctl": 105, "atl": 55, "tsb": 50, "hrv": 58},
    },
}

# Sample activities for S076
SAMPLE_ACTIVITIES_S076 = [
    {
        "id": "12345",
        "name": "Z2 Base Indoor - Test Protocol",
        "start_date": "2026-01-13T09:00:00",
        "type": "Ride",
        "moving_time": 5400,  # 90 min
        "tss": 85,
        "if_": 0.72,
        "np": 180,
        "avg_hr": 135,
        "indoor": True,
    },
    {
        "id": "12346",
        "name": "SST Intervals Outdoor 3x8",
        "start_date": "2026-01-15T14:00:00",
        "type": "Ride",
        "moving_time": 4200,  # 70 min
        "tss": 95,
        "if_": 0.88,
        "np": 220,
        "avg_hr": 155,
        "indoor": False,
    },
    {
        "id": "12347",
        "name": "Recovery Spin",
        "start_date": "2026-01-16T10:00:00",
        "type": "Ride",
        "moving_time": 3600,  # 60 min
        "tss": 42,
        "if_": 0.55,
        "np": 140,
        "avg_hr": 120,
        "indoor": True,
    },
]

# Sample wellness data
SAMPLE_WELLNESS_DATA = {
    "hrv_avg": 58,
    "hrv_trend": "stable",
    "sleep_quality_avg": 7.2,
    "fatigue_score_avg": 3.5,
    "readiness_avg": 8.1,
}

# Sample learnings (training intelligence)
SAMPLE_LEARNINGS = [
    {
        "type": "protocol_validation",
        "title": "Z2 Indoor Protocol Validated",
        "description": "90min Z2 indoor @ 72% IF maintenu sans dérive cardiaque",
        "session_id": "12345",
        "confidence": "high",
    },
    {
        "type": "performance_discovery",
        "title": "SST Outdoor Capacity Confirmed",
        "description": "3x8min SST @ 88% IF avec récupération complète inter-intervalles",
        "session_id": "12346",
        "confidence": "high",
    },
]

# Sample valid workout_history report
SAMPLE_WORKOUT_HISTORY_REPORT = """# Workout History S076

## Contexte Semaine

**Semaine S076** (13-19 janvier 2026)
**TSS Planifié:** 450 | **TSS Réalisé:** 423 (94%)
**Objectifs:** Valider protocole Z2 indoor 90min, Tester capacité SST outdoor 3x8min

La semaine s'inscrit dans une phase de validation de protocoles établis durant le bloc hivernal, avec un focus particulier sur la capacité à maintenir des efforts Z2 prolongés en indoor et la confirmation des capacités SST en conditions outdoor.

## Chronologie Complète

### Lundi 13 Janvier - Z2 Base Indoor - Test Protocol
**TSS:** 85 | **IF:** 0.72 | **Durée:** 90min
**Objectif:** Valider protocole Z2 indoor 90min

Première validation du protocole Z2 indoor sur 90 minutes. Maintien stable à 72% IF (180W NP) avec fréquence cardiaque moyenne de 135 bpm. Aucune dérive cardiaque observée sur la durée, confirmant l'adaptation au format indoor prolongé. Wellness pré-séance: HRV 58, Readiness 8.1/10.

**Découverte majeure:** Protocole validé - capacité confirmée à maintenir 90min Z2 indoor sans dégradation.

### Mercredi 15 Janvier - SST Intervals Outdoor 3x8
**TSS:** 95 | **IF:** 0.88 | **Durée:** 70min
**Objectif:** Tester capacité SST outdoor 3x8min

Sortie outdoor en conditions réelles avec 3 intervalles de 8 minutes en SST. Puissance normalisée de 220W (88% IF) maintenue sur l'ensemble des intervalles avec récupération complète entre les efforts. Fréquence cardiaque moyenne de 155 bpm, stable sur chaque intervalle. Conditions météo favorables (8°C, vent modéré).

**Découverte majeure:** Capacité SST outdoor confirmée - tolérance excellent aux efforts soutenus prolongés.

### Jeudi 16 Janvier - Recovery Spin
**TSS:** 42 | **IF:** 0.55 | **Durée:** 60min

Séance de récupération active post-SST. Maintien volontaire à basse intensité (140W NP, 55% IF) avec fréquence cardiaque de 120 bpm. Sensations de fraîcheur confirmant la bonne récupération du bloc intensif précédent.

## Métriques Évolution

**Métriques physiologiques:**
- HRV moyenne: 58 (stable, tendance neutre)
- Qualité sommeil: 7.2/10 (maintenue)
- Score fatigue: 3.5/10 (faible)
- Readiness moyenne: 8.1/10 (excellente)

**Métriques performance:**
- TSS réalisé: 423/450 (94% objectif)
- IF moyen: 0.72 (cible endurance respectée)
- 3 séances complétées dont 2 protocoles validés

## Enseignements Majeurs

### 1. Protocole Z2 Indoor 90min Validé
Capacité confirmée à maintenir 90 minutes en Z2 indoor (72% IF) sans dérive cardiaque ni fatigue excessive. Ce protocole devient référence pour les futures séances indoor longues.

### 2. Capacité SST Outdoor Confirmée
Performance SST outdoor (3x8min @ 88% IF) réalisée avec succès, confirmant l'adaptation aux efforts soutenus en conditions réelles. Récupération inter-intervalles complète.

### 3. Récupération Optimale Maintenue
Indicateurs wellness stables (HRV 58, Readiness 8.1) témoignent d'une gestion appropriée de la charge et de la récupération post-bloc intensif.

## Recommandations

1. **Protocole Z2 Indoor:** Intégrer systématiquement dans la programmation hivernale (1-2x/semaine)
2. **Progression SST:** Envisager extension à 4x8min pour la prochaine phase
3. **Wellness Monitoring:** Maintenir surveillance HRV pré-séances clés
4. **Outdoor Training:** Privilégier sorties outdoor pour intervalles SST (meilleure tolérance observée)

---

**Rapport généré avec [Claude Code](https://claude.com/claude-code) - Sprint R10 MVP**
"""

# Sample valid bilan_final report
SAMPLE_BILAN_FINAL_REPORT = """# Bilan Final S076

## Objectifs vs Réalisé

**Objectifs planifiés:**
1. Valider protocole Z2 indoor 90min ✅
2. Tester capacité SST outdoor 3x8min ✅
3. Confirmer récupération post-bloc intensif ✅

**TSS:** 423/450 (94%) - Objectif atteint avec marge appropriée

Les trois objectifs de validation de protocoles ont été pleinement atteints, confirmant la maturité des adaptations développées durant le bloc hivernal. La légère sous-réalisation TSS (6%) reflète une gestion prudente de la charge, cohérente avec la phase de consolidation.

## Métriques Finales

| Métrique | Début Semaine | Fin Semaine | Évolution |
|----------|---------------|-------------|-----------|
| HRV | 58 | 58 | Stable ✅ |
| Readiness | 8.1/10 | 8.1/10 | Maintenue ✅ |
| Fatigue Score | 3.5/10 | 3.5/10 | Faible ✅ |
| TSS Cumulé | 0 | 423 | +423 |

Stabilité remarquable des indicateurs wellness témoignant d'une charge bien dosée et d'une récupération optimale.

## Découvertes Majeures

### 1. Protocole Z2 Indoor 90min Validé
Maintien stable 72% IF sur 90 minutes sans dérive cardiaque ni fatigue excessive. Ce protocole devient référence pour programmation hivernale indoor.

### 2. Capacité SST Outdoor Confirmée
Performance 3x8min @ 88% IF avec récupération complète inter-intervalles. Tolérance excellente aux efforts soutenus en conditions réelles.

### 3. Récupération Post-Bloc Optimale
Indicateurs wellness stables (HRV 58, Readiness 8.1) confirment gestion appropriée de la charge et récupération efficace.

## Séances Clés

**Session 1 - Z2 Indoor 90min (13/01):**
Validation réussie du protocole Z2 prolongé. Performance: 85 TSS, 72% IF, FC 135 bpm stable. Aucune dérive observée.

**Session 2 - SST 3x8min Outdoor (15/01):**
Confirmation capacité SST outdoor. Performance: 95 TSS, 88% IF, FC 155 bpm stable. Récupération complète entre intervalles.

## Protocoles Établis/Validés

1. **Z2 Indoor 90min:** Protocole validé (72% IF, 180W NP, FC ~135 bpm)
2. **SST Outdoor 3x8min:** Protocole confirmé (88% IF, 220W NP, récup 4-5min)
3. **Recovery Active:** Format 60min @ 55% IF efficace pour récupération post-intensif

## Ajustements Recommandés

1. **Volume SST:** Progression vers 4x8min envisageable pour prochaine phase
2. **Fréquence Indoor:** Intégrer 1-2 séances Z2 indoor/semaine dans programmation
3. **Monitoring Wellness:** Maintenir surveillance HRV pré-séances clés
4. **Mix Indoor/Outdoor:** Privilégier outdoor pour intervalles SST (meilleure tolérance)

## Enseignements Comportementaux

- **Discipline Indoor:** Capacité maintenue sur formats longs (90min) avec focus mental approprié
- **Gestion Récupération:** Respect scrupuleux des zones basses en recovery (patience confirmée)
- **Adaptation Outdoor:** Tolérance excellente aux efforts soutenus en conditions réelles

## Conclusion

Semaine de validation pleinement réussie avec 3/3 objectifs atteints. Les protocoles Z2 indoor prolongé et SST outdoor sont désormais établis comme références pour la programmation future. Stabilité remarquable des indicateurs wellness témoigne d'une gestion optimale de la charge d'entraînement.

---

**Rapport généré avec [Claude Code](https://claude.com/claude-code) - Sprint R10 MVP**
"""
