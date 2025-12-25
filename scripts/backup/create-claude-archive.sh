#!/bin/bash

# Script de création d'archive complète pour Claude Code
# Projet: Système d'Asservissement Coach AI Cyclisme

set -e  # Exit on error

cd ~/cyclisme-training-logs

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_DIR="/tmp/claude-code-context_${TIMESTAMP}"

echo "=== Création structure archive ==="
mkdir -p "${ARCHIVE_DIR}"

echo "=== Copie fichiers racine ==="
cp pyproject.toml "${ARCHIVE_DIR}/"
cp poetry.lock "${ARCHIVE_DIR}/"
cp .gitignore "${ARCHIVE_DIR}/"
cp README.md "${ARCHIVE_DIR}/"
cp COMMANDS.md "${ARCHIVE_DIR}/"
cp ALIASES.md "${ARCHIVE_DIR}/"

echo "=== Copie modules Python ==="
mkdir -p "${ARCHIVE_DIR}/cyclisme_training_logs"
cp cyclisme_training_logs/*.py "${ARCHIVE_DIR}/cyclisme_training_logs/"

echo "=== Copie logs ==="
mkdir -p "${ARCHIVE_DIR}/logs"
cp logs/workouts-history.md "${ARCHIVE_DIR}/logs/" 2>/dev/null || echo "⚠️  workouts-history.md absent"

mkdir -p "${ARCHIVE_DIR}/logs/weekly_reports/S070"
cp logs/weekly_reports/S070/*.md "${ARCHIVE_DIR}/logs/weekly_reports/S070/" 2>/dev/null || echo "⚠️  S070 absent"

mkdir -p "${ARCHIVE_DIR}/logs/weekly_reports/S071"
cp logs/weekly_reports/S071/*.md "${ARCHIVE_DIR}/logs/weekly_reports/S071/" 2>/dev/null || echo "⚠️  S071 absent"

echo "=== Création exemples structures ==="
mkdir -p "${ARCHIVE_DIR}/examples/planning"
mkdir -p "${ARCHIVE_DIR}/examples/templates"

cat > "${ARCHIVE_DIR}/examples/planning/example_week_planning.json" << 'EOFPLANNING'
{
  "week_id": "S072",
  "start_date": "2025-12-16",
  "end_date": "2025-12-22",
  "created_at": "2025-12-15T10:00:00",
  "last_updated": "2025-12-15T10:00:00",
  "version": 1,
  "sessions": [
    {
      "day": "2025-12-16",
      "workout_code": "S072-01-INT-SweetSpot-V001",
      "type": "INT",
      "tss_planned": 60,
      "description": "Sweet-Spot 3x10min 88-90% FTP",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-17",
      "workout_code": "S072-02-END-EnduranceBase-V001",
      "type": "END",
      "tss_planned": 45,
      "description": "Endurance 60min Z2",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-18",
      "workout_code": "S072-03-END-EnduranceProgressive-V001",
      "type": "END",
      "tss_planned": 50,
      "description": "Endurance progressive 65min",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-19",
      "workout_code": "S072-04-INT-SweetSpotCourt-V001",
      "type": "INT",
      "tss_planned": 55,
      "description": "Sweet-Spot 2x12min",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-20",
      "workout_code": "S072-05-REC-RecuperationActive-V001",
      "type": "REC",
      "tss_planned": 30,
      "description": "Récupération active 45min",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-21",
      "workout_code": "S072-06-INT-VO2MaxCourt-V001",
      "type": "INT",
      "tss_planned": 65,
      "description": "VO2 Max 5x3min 106% FTP",
      "status": "planned",
      "history": []
    },
    {
      "day": "2025-12-22",
      "workout_code": "REPOS",
      "type": "REST",
      "tss_planned": 0,
      "description": "Repos hebdomadaire obligatoire",
      "status": "rest_day",
      "history": []
    }
  ]
}
EOFPLANNING

cat > "${ARCHIVE_DIR}/examples/templates/recovery_active_30tss.json" << 'EOFTEMPLATE1'
{
  "id": "recovery_active_30tss",
  "name": "Récupération Active 30 TSS",
  "type": "REC",
  "tss": 30,
  "duration_minutes": 45,
  "description": "Récupération active 45min Z1-Z2",
  "workout_code_pattern": "{week_id}-{day_num:02d}-REC-RecuperationActive-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-60% 85rpm\n\nMain set\n- 25m 60% 85rpm cadence libre\n\nCooldown\n- 10m ramp 60-50% 85rpm",
  "use_cases": ["lighten_from_endurance", "lighten_from_sweetspot", "emergency_recovery"],
  "prerequisites": {
    "min_tsb": -15,
    "max_tsb": 999,
    "min_hrv_drop": -20,
    "max_hrv_drop": 0
  }
}
EOFTEMPLATE1

cat > "${ARCHIVE_DIR}/examples/templates/recovery_active_25tss.json" << 'EOFTEMPLATE2'
{
  "id": "recovery_active_25tss",
  "name": "Récupération Active 25 TSS",
  "type": "REC",
  "tss": 25,
  "duration_minutes": 40,
  "description": "Récupération active 40min Z1",
  "workout_code_pattern": "{week_id}-{day_num:02d}-REC-RecuperationCourte-V001",
  "intervals_icu_format": "Warmup\n- 8m ramp 45-55% 85rpm\n\nMain set\n- 24m 55% 85rpm cadence libre\n\nCooldown\n- 8m ramp 55-45% 85rpm",
  "use_cases": ["lighten_from_endurance_base", "recovery_between_intensity"],
  "prerequisites": {
    "min_tsb": -20,
    "max_tsb": 999
  }
}
EOFTEMPLATE2

cat > "${ARCHIVE_DIR}/examples/templates/recovery_short_20tss.json" << 'EOFTEMPLATE3'
{
  "id": "recovery_short_20tss",
  "name": "Récupération Courte 20 TSS",
  "type": "REC",
  "tss": 20,
  "duration_minutes": 30,
  "description": "Récupération courte 30min Z1",
  "workout_code_pattern": "{week_id}-{day_num:02d}-REC-RecuperationUltraLegere-V001",
  "intervals_icu_format": "Warmup\n- 5m ramp 45-50% 85rpm\n\nMain set\n- 20m 50% 85rpm cadence libre\n\nCooldown\n- 5m ramp 50-45% 85rpm",
  "use_cases": ["emergency_recovery", "extreme_fatigue", "hrv_drop_severe"],
  "prerequisites": {
    "min_tsb": -25,
    "max_tsb": 999,
    "min_hrv_drop": -25,
    "max_hrv_drop": -10
  }
}
EOFTEMPLATE3

cat > "${ARCHIVE_DIR}/examples/templates/endurance_light_35tss.json" << 'EOFTEMPLATE4'
{
  "id": "endurance_light_35tss",
  "name": "Endurance Légère 35 TSS",
  "type": "END",
  "tss": 35,
  "duration_minutes": 50,
  "description": "Endurance légère 50min Z2 bas",
  "workout_code_pattern": "{week_id}-{day_num:02d}-END-EnduranceLegere-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-65% 85rpm\n\nMain set\n- 30m 65% 85-90rpm cadence libre\n\nCooldown\n- 10m ramp 65-50% 85rpm",
  "use_cases": ["lighten_from_endurance_normal", "maintain_volume_reduce_load"],
  "prerequisites": {
    "min_tsb": -10,
    "max_tsb": 999
  }
}
EOFTEMPLATE4

cat > "${ARCHIVE_DIR}/examples/templates/endurance_short_40tss.json" << 'EOFTEMPLATE5'
{
  "id": "endurance_short_40tss",
  "name": "Endurance Courte 40 TSS",
  "type": "END",
  "tss": 40,
  "duration_minutes": 55,
  "description": "Endurance courte 55min Z2",
  "workout_code_pattern": "{week_id}-{day_num:02d}-END-EnduranceCourte-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-70% 85rpm\n\nMain set\n- 35m 70% 85-90rpm cadence libre\n\nCooldown\n- 10m ramp 70-50% 85rpm",
  "use_cases": ["lighten_from_sweetspot", "reduce_volume_maintain_quality"],
  "prerequisites": {
    "min_tsb": -5,
    "max_tsb": 999
  }
}
EOFTEMPLATE5

cat > "${ARCHIVE_DIR}/examples/templates/sweetspot_short_50tss.json" << 'EOFTEMPLATE6'
{
  "id": "sweetspot_short_50tss",
  "name": "Sweet-Spot Court 50 TSS",
  "type": "INT",
  "tss": 50,
  "duration_minutes": 50,
  "description": "Sweet-Spot court 2x10min 88-90% FTP",
  "workout_code_pattern": "{week_id}-{day_num:02d}-INT-SweetSpotCourt-V001",
  "intervals_icu_format": "Warmup\n- 10m ramp 50-75% 85rpm\n- 5m 75% 90rpm\n\nMain set 2x\n- 10m 90% 90rpm\n- 4m 60% 85rpm\n\nCooldown\n- 10m ramp 65-50% 85rpm",
  "use_cases": ["lighten_from_sweetspot_long", "lighten_from_vo2", "maintain_quality_reduce_volume"],
  "prerequisites": {
    "min_tsb": 0,
    "max_tsb": 999,
    "min_hrv_drop": -10,
    "max_hrv_drop": 5
  }
}
EOFTEMPLATE6

echo "=== Création IMPLEMENTATION_BRIEF.md ==="
cat > "${ARCHIVE_DIR}/IMPLEMENTATION_BRIEF.md" << 'EOFBRIEF'
# Brief Implémentation - Système Asservissement Coach AI

## Vision du Projet

Transformer le système actuel d'analyse quotidienne (boucle ouverte) en système d'**asservissement automatique** (boucle fermée) permettant au coach AI de détecter la fatigue et d'ajuster automatiquement le planning hebdomadaire.

## Contexte Athlète

- **Nom** : Stéphane, 54 ans
- **FTP actuel** : 220W
- **Objectif** : 260W
- **Facteur limitant** : Sommeil (moyenne 5h33 vs cible 7h+)
- **Physiologie** : FC repos 40 bpm, excellente récupération
- **Discipline** : Indoor-only suite échecs outdoor

## État Actuel (Boucle Ouverte) ❌
```
1. Collecte données séance
2. Analyse AI
3. Sauvegarde logs
4. Git commit
```

**Problème** : Recommandations texte uniquement, pas d'action automatique

## Objectif Cible (Boucle Fermée) ✅
```
1. Collecte données séance
2. 🆕 Chargement planning restant semaine
3. Analyse AI enrichie (prompt + planning + catalogue)
4. 🆕 Parsing recommandations JSON
5. 🆕 Application modifications automatiques
6. Sauvegarde logs
7. Git commit
```

## Modifications Code Requises (~350 lignes)

Voir README_ARCHIVE.md pour détails complets
EOFBRIEF

echo "=== Création CURRENT_STATE.md ==="
cat > "${ARCHIVE_DIR}/CURRENT_STATE.md" << 'EOFSTATE'
# État Actuel du Projet

## Métriques Actuelles

- **FTP** : 220W
- **Poids** : ~84kg
- **CTL** : ~54-56
- **TSS hebdomadaire** : 320-380

## Scripts Poetry (15 total)
```bash
workflow-coach          # Orchestrateur principal
weekly-analysis         # Analyse hebdomadaire
upload-workouts         # Upload Intervals.icu
```

## Problèmes Connus

- Dossier `data/week_planning/` absent
- Fichiers planning JSON absents
- Séances sautées non réconciliées
EOFSTATE

echo "=== Création README_ARCHIVE.md ==="
cat > "${ARCHIVE_DIR}/README_ARCHIVE.md" << 'EOFREADME'
# Archive Contexte Complet - Claude Code

## Contenu

- **IMPLEMENTATION_BRIEF.md** : Vision + objectifs
- **CURRENT_STATE.md** : État actuel
- **examples/** : Structures JSON référence
- **cyclisme_training_logs/** : Code source complet
- **logs/** : Historiques S070, S071

## Utilisation

1. Lire IMPLEMENTATION_BRIEF.md
2. Explorer code workflow_coach.py
3. Consulter examples/ pour structures
4. Implémenter modifications (~350 lignes)

## Structure Cible
```
~/cyclisme-training-logs/
├── data/                    # 🆕 À CRÉER
│   ├── week_planning/
│   └── workout_templates/
└── cyclisme_training_logs/
    └── workflow_coach.py    # À MODIFIER
```
EOFREADME

echo "=== Création archive tar.gz ==="
cd /tmp
tar -czf "claude-code-context_${TIMESTAMP}.tar.gz" "claude-code-context_${TIMESTAMP}/"
mv "claude-code-context_${TIMESTAMP}.tar.gz" ~/

echo ""
echo "✅ Archive créée : ~/claude-code-context_${TIMESTAMP}.tar.gz"
echo ""
du -h ~/claude-code-context_${TIMESTAMP}.tar.gz
echo ""
echo "🎯 Prêt pour Claude Code"

rm -rf "${ARCHIVE_DIR}"
