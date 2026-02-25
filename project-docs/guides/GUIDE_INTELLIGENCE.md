# Guide Training Intelligence & Feedback Loop

**Version :** 2.2.0
**Sprint :** R4++
**Date :** 2026-01-02

---

## Table des Matières

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Concepts Clés](#concepts-clés)
4. [Cas d'Usage](#cas-dusage)
5. [Exemples Complets](#exemples-complets)
6. [Backfill Historique](#backfill-historique)
7. [Contrôle PID Adaptatif](#contrôle-pid-adaptatif)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Introduction

### Problème Résolu : Silos Temporels

Avant Sprint R4, les analyses quotidiennes, hebdomadaires et mensuelles fonctionnaient en **silos isolés** :

- **Analyse quotidienne** : Génère insights post-séance, mais sans mémoire des découvertes passées
- **Analyse hebdomadaire** : Synthétise 6 jours, mais ne capitalise pas sur patterns récurrents
- **Analyse mensuelle** : Vue stratégique, mais déconnectée du feedback terrain

**Conséquence** : Enseignements dispersés, patterns non détectés, protocoles non validés.

### Solution : Mémoire Partagée Multi-Temporelle

Le module **Training Intelligence** crée une **mémoire partagée** accessible aux 3 niveaux temporels :

```
                    ┌──────────────────────────────┐
                    │   Training Intelligence      │
                    │   (Mémoire Partagée)         │
                    ├──────────────────────────────┤
                    │  - Learnings                 │
                    │  - Patterns                  │
                    │  - Protocol Adaptations      │
                    └──────────────────────────────┘
                               ▲  ▲  ▲
                ┌──────────────┼──┼──┼──────────────┐
                │              │  │  │              │
         ┌──────▼──────┐  ┌───▼──▼──▼───┐  ┌──────▼──────┐
         │   DAILY     │  │   WEEKLY    │  │  MONTHLY    │
         │  Analysis   │  │  Synthesis  │  │   Trends    │
         └─────────────┘  └─────────────┘  └─────────────┘

         POST-SÉANCE      BILAN SEMAINE    STRATÉGIE MOIS
```

### Architecture Feedback Loop

1. **Accumulation** : Chaque niveau enrichit la mémoire avec ses découvertes
2. **Validation** : Confidence progresse avec répétitions (LOW → MEDIUM → HIGH → VALIDATED)
3. **Insights** : Chaque niveau consulte la mémoire pour recommandations contextuelles
4. **Évolution** : Protocoles adaptés automatiquement selon evidence

---

## Installation

### Prérequis

- Python 3.11+
- Poetry
- Cyclisme Training Logs v2.0.0+ (Sprint R3)

### Installation Module

```bash
cd ~/cyclisme-training-logs

# Installer dépendances (déjà incluses depuis Sprint R4)
poetry install

# Vérifier installation
poetry run pytest tests/intelligence/ -v
# Attendu : 19/19 passing
```

### Configuration .env

Le module Training Intelligence utilise les mêmes configurations que le reste du projet.

Optionnel - Définir répertoire persistance intelligence :

```bash
# Ajout facultatif à .env
INTELLIGENCE_DATA_DIR=~/cyclisme-training-logs-data/intelligence
```

Par défaut, la persistance JSON se fait via `Path` en mémoire (pas de hardcoded paths).

---

## Concepts Clés

### 1. Learnings (Enseignements)

**Définition** : Enseignement extrait des données d'entraînement avec validation progressive.

**Attributs** :
- `id` : Identifiant unique (`category_timestamp`)
- `category` : Catégorie (ex : "sweet-spot", "hydration", "recovery")
- `description` : Ce qui a été appris (concis, actionnable)
- `evidence` : Liste de preuves (IDs séances + métriques)
- `confidence` : Niveau de confiance (LOW/MEDIUM/HIGH/VALIDATED)
- `level` : Niveau d'analyse où découvert (DAILY/WEEKLY/MONTHLY)
- `impact` : Impact estimé (LOW/MEDIUM/HIGH)
- `applied` : Appliqué aux protocoles (booléen)
- `validated` : Statut validé (booléen, True si VALIDATED)

**Progression Confidence** :
```
LOW (1-2 obs) → MEDIUM (3-5 obs) → HIGH (6-10 obs) → VALIDATED (10+ obs)
```

**Exemple** :
```python
from cyclisme_training_logs.intelligence import TrainingIntelligence, AnalysisLevel

intelligence = TrainingIntelligence()

# Jour 1 : Découverte initiale
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88-90% FTP sustainable 2x10min, RPE 7",
    evidence=["S024-04: 2x10@88% FTP, découplage 5.2%"],
    level=AnalysisLevel.DAILY
)
print(f"Confidence: {learning.confidence}")  # LOW

# Jour 3 : Confirmation
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88-90% FTP sustainable 2x10min, RPE 7",
    evidence=["S024-06: 2x10@89% FTP, découplage 4.8%"],
    level=AnalysisLevel.DAILY
)
print(f"Confidence: {learning.confidence}")  # Still LOW (need 3)

# Jour 5 : Passage MEDIUM
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88-90% FTP sustainable 2x10min, RPE 7",
    evidence=["S024-08: 2x10@90% FTP, découplage 5.0%"],
    level=AnalysisLevel.DAILY
)
print(f"Confidence: {learning.confidence}")  # MEDIUM (3 obs)
```

---

### 2. Patterns (Patterns Récurrents)

**Définition** : Pattern récurrent identifié sur plusieurs séances avec conditions déclencheurs.

**Attributs** :
- `id` : Identifiant unique (`pattern_name_timestamp`)
- `name` : Nom descriptif (snake_case, ex : `sleep_debt_vo2_failure`)
- `trigger_conditions` : Dict conditions déclencheurs (ex : `{"sleep": "<6h", "workout_type": "VO2"}`)
- `observed_outcome` : Ce qui se passe quand déclenché
- `frequency` : Nombre de fois observé
- `first_seen` : Date première observation
- `last_seen` : Date dernière observation
- `confidence` : Confiance basée sur fréquence

**Opérateurs Conditions** :
- `<` : Inférieur (ex : `"<6h"` → sleep < 6)
- `>` : Supérieur (ex : `">90"` → intensity > 90)
- `=` : Égalité stricte (ex : `"=VO2"` → workout_type == "VO2")
- Valeur directe : Match exact (ex : `"Endurance"`)

**Exemple** :
```python
from datetime import date

# Observation 1 : Échec VO2 après nuit courte
pattern = intelligence.identify_pattern(
    name="sleep_debt_vo2_failure",
    trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
    observed_outcome="Incapacité finir intervalles, RPE 9+",
    observation_date=date(2026, 1, 5)
)
print(f"Frequency: {pattern.frequency}, Confidence: {pattern.confidence}")
# Frequency: 1, Confidence: LOW

# Observation 2-4 : Pattern se confirme
for observation_date in [date(2026, 1, 10), date(2026, 1, 15), date(2026, 1, 20)]:
    pattern = intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        observed_outcome="Incapacité finir intervalles, RPE 9+",
        observation_date=observation_date
    )

print(f"Frequency: {pattern.frequency}, Confidence: {pattern.confidence}")
# Frequency: 4, Confidence: MEDIUM

# Utilisation : Vérifier si conditions actuelles matchent
if pattern.matches({"sleep": 5.5, "workout_type": "VO2"}):
    print("⚠️  ATTENTION: Pattern détecté, risque échec VO2")
```

---

### 3. Protocol Adaptations (Adaptations Protocoles)

**Définition** : Adaptation proposée à un protocole existant basée sur evidence.

**Attributs** :
- `id` : Identifiant unique (`protocol_type_timestamp`)
- `protocol_name` : Nom protocole (ex : "vo2_veto", "hydration")
- `adaptation_type` : Type modification (ADD/MODIFY/REMOVE)
- `current_rule` : Règle actuelle
- `proposed_rule` : Règle proposée
- `justification` : Pourquoi adapter
- `evidence` : Preuves supportant l'adaptation
- `confidence` : Confiance basée sur count evidence
- `status` : Statut (PROPOSED/TESTED/VALIDATED/REJECTED)

**Lifecycle Status** :
```
PROPOSED → TESTED → VALIDATED
             ↓
          REJECTED
```

**Exemple** :
```python
# Proposer adaptation protocole VETO VO2 pour master athlete
adaptation = intelligence.propose_adaptation(
    protocol_name="vo2_veto",
    adaptation_type="MODIFY",
    current_rule="Sleep < 6h → VETO",
    proposed_rule="Sleep < 6.5h → VETO (master athlete)",
    justification="Athlète master 54 ans nécessite +30min récup vs senior",
    evidence=[
        "S024-05: 6.2h sleep, VO2 RPE 9 vs target 7-8",
        "S024-10: 6.0h sleep, abandon intervalles 3/5",
        "S024-15: 6.3h sleep, fréquence anormalement haute +8%"
    ]
)

print(f"Status: {adaptation.status}")           # PROPOSED
print(f"Confidence: {adaptation.confidence}")   # MEDIUM (3 evidence)

# Après tests terrain, marquer comme VALIDATED
adaptation.status = "VALIDATED"
```

---

### 4. Multi-Temporal Insights

**Principe** : Chaque niveau temporel consulte l'intelligence pour insights contextuels.

#### Daily Insights (Post-Séance)

**Fonction** : `get_daily_insights(context)`

**Retour** :
- `relevant_learnings` : Learnings pertinents pour contexte
- `active_patterns` : Patterns matchant conditions actuelles
- `recommendations` : Liste recommandations (strings)

**Exemple** :
```python
# Contexte : Séance sweet-spot planifiée 89% FTP, sommeil OK
insights = intelligence.get_daily_insights({
    "workout_type": "sweet-spot",
    "planned_intensity": 89,
    "sleep": 7.5
})

print("Recommandations :")
for rec in insights["recommendations"]:
    print(f"  - {rec}")
# Output:
#   - 88-90% FTP sustainable 2x10min, RPE 7 (Confidence: MEDIUM, 3 observations)

print(f"\nPatterns actifs : {len(insights['active_patterns'])}")
# Output: 0 (pas de pattern déclenché car sleep >= 6h)
```

#### Weekly Synthesis (Bilan Semaine)

**Fonction** : `get_weekly_synthesis(week_number)`

**Retour** :
- `total_learnings` : Nombre total learnings
- `high_confidence_learnings` : Learnings HIGH/VALIDATED
- `active_patterns` : Patterns actifs (MEDIUM+)
- `pending_adaptations` : Adaptations en attente (PROPOSED)

**Exemple** :
```python
synthesis = intelligence.get_weekly_synthesis(week_number=2)

print(f"Total learnings : {synthesis['total_learnings']}")
print(f"High confidence : {len(synthesis['high_confidence_learnings'])}")
print(f"Patterns actifs : {len(synthesis['active_patterns'])}")
print(f"Adaptations pending : {len(synthesis['pending_adaptations'])}")
```

#### Monthly Trends (Stratégie Mois)

**Fonction** : `get_monthly_trends(month, year)`

**Retour** :
- `validated_learnings` : Learnings validés (VALIDATED)
- `top_patterns` : Top 10 patterns par fréquence
- `validated_adaptations` : Adaptations validées (VALIDATED)

**Exemple** :
```python
trends = intelligence.get_monthly_trends(month=1, year=2026)

print("Protocoles validés :")
for learning in trends["validated_learnings"]:
    print(f"  - {learning.description} ({len(learning.evidence)} obs)")

print("\nTop patterns :")
for pattern in trends["top_patterns"][:3]:
    print(f"  - {pattern.name} (freq: {pattern.frequency})")
```

---

## Cas d'Usage

### Quotidien : Post-Séance

**Workflow** :
1. Effectuer séance
2. Ajouter learning si découverte
3. Consulter insights pour prochaine séance
4. Sauvegarder état

**Code Complet** :
```python
from datetime import date, datetime
from pathlib import Path
from cyclisme_training_logs.intelligence import (
    TrainingIntelligence,
    AnalysisLevel
)

# Charger intelligence (ou créer si première fois)
intelligence_file = Path("~/cyclisme-training-logs-data/intelligence/state.json").expanduser()

if intelligence_file.exists():
    intelligence = TrainingIntelligence.load_from_file(intelligence_file)
else:
    intelligence = TrainingIntelligence()

# Post-séance S024-04 : Découverte sweet-spot optimal
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88-90% FTP sustainable 2x10min",
    evidence=["S024-04: 2x10@88% FTP, RPE 7, découplage 5.2%"],
    level=AnalysisLevel.DAILY,
    impact="MEDIUM"
)

print(f"✅ Learning ajouté (confidence: {learning.confidence.value})")

# Préparer prochaine séance : Consulter insights
insights = intelligence.get_daily_insights({
    "workout_type": "vo2",
    "planned_intensity": 120,
    "sleep": 5.5  # Nuit courte !
})

if insights["active_patterns"]:
    print("\n⚠️  WARNINGS :")
    for warning in insights["recommendations"]:
        if "⚠️" in warning:
            print(f"  {warning}")

# Sauvegarder état
intelligence.save_to_file(intelligence_file)
print(f"\n💾 État sauvegardé : {intelligence_file}")
```

---

### Hebdomadaire : Bilan

**Workflow** :
1. Synthétiser semaine écoulée
2. Identifier patterns émergents
3. Proposer adaptations protocoles si patterns récurrents
4. Sauvegarder état

**Code Complet** :
```python
from pathlib import Path
from cyclisme_training_logs.intelligence import TrainingIntelligence

# Charger état
intelligence_file = Path("~/cyclisme-training-logs-data/intelligence/state.json").expanduser()
intelligence = TrainingIntelligence.load_from_file(intelligence_file)

# Synthèse semaine 2
synthesis = intelligence.get_weekly_synthesis(week_number=2)

print(f"📊 SEMAINE 2 - SYNTHÈSE INTELLIGENCE\n")
print(f"Total learnings      : {synthesis['total_learnings']}")
print(f"High confidence      : {len(synthesis['high_confidence_learnings'])}")
print(f"Patterns actifs      : {len(synthesis['active_patterns'])}")
print(f"Adaptations pending  : {len(synthesis['pending_adaptations'])}")

# Analyser patterns émergents
print("\n🔍 PATTERNS DÉTECTÉS :\n")
for pattern in synthesis["active_patterns"]:
    print(f"- {pattern.name}")
    print(f"  Fréquence    : {pattern.frequency}")
    print(f"  Confidence   : {pattern.confidence.value}")
    print(f"  Outcome      : {pattern.observed_outcome}")
    print(f"  First seen   : {pattern.first_seen}")
    print(f"  Last seen    : {pattern.last_seen}\n")

# Si pattern fréquent détecté → Proposer adaptation
for pattern in synthesis["active_patterns"]:
    if pattern.frequency >= 3 and "vo2" in pattern.name.lower():
        # Pattern VO2 échec détecté
        adaptation = intelligence.propose_adaptation(
            protocol_name="vo2_veto",
            adaptation_type="MODIFY",
            current_rule="Sleep < 6h → VETO",
            proposed_rule="Sleep < 6.5h → VETO (master athlete)",
            justification=f"Pattern {pattern.name} observé {pattern.frequency} fois",
            evidence=[f"Pattern frequency: {pattern.frequency}"]
        )
        print(f"💡 ADAPTATION PROPOSÉE : {adaptation.protocol_name}")
        print(f"   {adaptation.current_rule} → {adaptation.proposed_rule}\n")

# Sauvegarder
intelligence.save_to_file(intelligence_file)
```

---

### Mensuel : Stratégie

**Workflow** :
1. Lister protocoles validés (VALIDATED)
2. Analyser patterns confirmés
3. Définir objectifs mois suivant
4. Intégrer adaptations validées dans protocoles officiels

**Code Complet** :
```python
from pathlib import Path
from cyclisme_training_logs.intelligence import TrainingIntelligence

# Charger état
intelligence_file = Path("~/cyclisme-training-logs-data/intelligence/state.json").expanduser()
intelligence = TrainingIntelligence.load_from_file(intelligence_file)

# Tendances mois janvier 2026
trends = intelligence.get_monthly_trends(month=1, year=2026)

print("📈 TENDANCES JANVIER 2026\n")
print("=" * 60)

# 1. PROTOCOLES VALIDÉS (10+ observations)
print("\n✅ PROTOCOLES VALIDÉS (intégrer au workflow) :\n")
for learning in trends["validated_learnings"]:
    print(f"- {learning.description}")
    print(f"  Catégorie    : {learning.category}")
    print(f"  Evidence     : {len(learning.evidence)} observations")
    print(f"  Impact       : {learning.impact}")
    print(f"  Découvert    : {learning.level.value}\n")

# 2. TOP PATTERNS
print("\n🔁 TOP PATTERNS (prévention) :\n")
for i, pattern in enumerate(trends["top_patterns"][:5], 1):
    print(f"{i}. {pattern.name}")
    print(f"   Fréquence    : {pattern.frequency}")
    print(f"   Confidence   : {pattern.confidence.value}")
    print(f"   Outcome      : {pattern.observed_outcome}\n")

# 3. ADAPTATIONS VALIDÉES
print("\n🔧 ADAPTATIONS VALIDÉES (appliquer) :\n")
for adaptation in trends["validated_adaptations"]:
    print(f"- Protocole : {adaptation.protocol_name}")
    print(f"  Type      : {adaptation.adaptation_type}")
    print(f"  Avant     : {adaptation.current_rule}")
    print(f"  Après     : {adaptation.proposed_rule}")
    print(f"  Evidence  : {len(adaptation.evidence)} preuves\n")

# 4. OBJECTIFS MOIS SUIVANT
print("\n🎯 OBJECTIFS FÉVRIER 2026 :\n")
print("1. Appliquer adaptations validées aux protocoles officiels")
print("2. Tester learnings HIGH confidence (promouvoir vers VALIDATED)")
print("3. Surveiller patterns fréquents (>5) pour prévention")
print("4. Continuer accumulation evidence sweet-spot optimal")

# Sauvegarder
intelligence.save_to_file(intelligence_file)
```

---

## Exemples Complets

### Exemple 1 : Sweet-Spot Optimal (Jour 1 → Mois 1)

**Contexte** : Athlète master 54 ans cherche intensité sweet-spot optimale (88-92% FTP).

**Jour 1 (5 Jan) - Découverte Initiale**
```python
from datetime import date
from cyclisme_training_logs.intelligence import TrainingIntelligence, AnalysisLevel

intelligence = TrainingIntelligence()

# Séance S002-01 : Sweet-spot 2x10min @ 88% FTP
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88% FTP sustainable 2x10min, RPE 7",
    evidence=["S002-01: 2x10@88%, découplage 5.2%, HR avg 155"],
    level=AnalysisLevel.DAILY
)
# Confidence: LOW
```

**Jour 8 (12 Jan) - Confirmation**
```python
# Séance S002-03 : Sweet-spot 2x10min @ 89% FTP
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88% FTP sustainable 2x10min, RPE 7",
    evidence=["S002-03: 2x10@89%, découplage 4.8%, HR avg 157"],
    level=AnalysisLevel.DAILY
)
# Confidence: LOW (2 obs)
```

**Jour 12 (16 Jan) - Passage MEDIUM**
```python
# Séance S002-04 : Sweet-spot 2x10min @ 90% FTP
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88% FTP sustainable 2x10min, RPE 7",
    evidence=["S002-04: 2x10@90%, découplage 5.0%, HR avg 156"],
    level=AnalysisLevel.DAILY
)
# Confidence: MEDIUM (3 obs) ✅
```

**Semaine 3 (19 Jan) - Synthèse Hebdo**
```python
synthesis = intelligence.get_weekly_synthesis(week_number=3)

# Résultat :
# - 1 learning MEDIUM confidence
# - Recommandation : Utiliser 88-90% FTP pour sweet-spot
```

**Jour 40 (14 Fév) - Passage HIGH**
```python
# Après 6 séances confirmant l'hypothèse
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88% FTP sustainable 2x10min, RPE 7",
    evidence=["S003-02: 2x10@89%, découplage 4.5%, excellent ressenti"],
    level=AnalysisLevel.WEEKLY
)
# Confidence: HIGH (6 obs) 🎯
```

**Mois 1 (31 Jan) - Tendances**
```python
trends = intelligence.get_monthly_trends(month=1, year=2026)

# Sweet-spot learning = HIGH confidence
# → Utiliser 88-90% FTP comme protocole standard
```

**Jour 90 (5 Avr) - Protocole Validé**
```python
# Après 10+ séances confirmées
learning = intelligence.add_learning(
    category="sweet-spot",
    description="88% FTP sustainable 2x10min, RPE 7",
    evidence=["S005-03: 2x10@88%, 10ème confirmation"],
    level=AnalysisLevel.MONTHLY
)
# Confidence: VALIDATED (10+ obs) ⭐
# validated: True

# → Intégrer au workflow officiel comme protocole master athlete
```

---

### Exemple 2 : Prévention VO2 Échec (Pattern Detection → Warning)

**Contexte** : Détecter conditions menant à échec VO2 (sleep debt).

**Observation 1 (10 Jan)**
```python
from datetime import date

# Séance S002-02 échouée : VO2 5x3min @ 120% FTP, abandon après 2 intervalles
pattern = intelligence.identify_pattern(
    name="sleep_debt_vo2_failure",
    trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
    observed_outcome="Abandon intervalles, RPE 9+ vs target 7-8",
    observation_date=date(2026, 1, 10)
)
# Frequency: 1, Confidence: LOW
```

**Observation 2 (17 Jan)**
```python
# Séance S002-05 échouée : Même conditions (5.5h sleep + VO2)
pattern = intelligence.identify_pattern(
    name="sleep_debt_vo2_failure",
    trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
    observed_outcome="Abandon intervalles, RPE 9+ vs target 7-8",
    observation_date=date(2026, 1, 17)
)
# Frequency: 2, Confidence: LOW
```

**Observation 3 (24 Jan) - Pattern Confirmé**
```python
# Séance S003-01 échouée : 3ème occurrence
pattern = intelligence.identify_pattern(
    name="sleep_debt_vo2_failure",
    trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
    observed_outcome="Abandon intervalles, RPE 9+ vs target 7-8",
    observation_date=date(2026, 1, 24)
)
# Frequency: 3, Confidence: MEDIUM ✅
```

**Utilisation : Prévention (31 Jan)**
```python
# Veille séance VO2 : Sommeil court (5.5h)
context = {
    "sleep": 5.5,           # Nuit courte !
    "workout_type": "VO2",
    "planned_intensity": 120
}

insights = intelligence.get_daily_insights(context)

# Vérifier warnings
if insights["active_patterns"]:
    print("⚠️  WARNINGS DÉTECTÉS :")
    for pattern in insights["active_patterns"]:
        print(f"Pattern : {pattern.name}")
        print(f"Outcome : {pattern.observed_outcome}")
        print(f"Fréquence : {pattern.frequency}")

    # Recommandation : ANNULER ou MODIFIER séance
    print("\n💡 RECOMMANDATION : Remplacer VO2 par Endurance Z2")
```

**Proposer Adaptation Protocole (Semaine 5)**
```python
# Pattern observé 4 fois → Proposer adapter protocole VETO
adaptation = intelligence.propose_adaptation(
    protocol_name="vo2_veto",
    adaptation_type="MODIFY",
    current_rule="Sleep < 6h → VETO",
    proposed_rule="Sleep < 6.5h → VETO (master athlete)",
    justification="Master 54 ans nécessite +30min récup vs senior, 4 échecs documentés",
    evidence=[
        "S002-02: 5.8h sleep → Échec VO2",
        "S002-05: 5.5h sleep → Échec VO2",
        "S003-01: 5.7h sleep → Échec VO2",
        "S003-04: 6.2h sleep → Échec VO2"
    ]
)
# Status: PROPOSED
# Confidence: MEDIUM (4 evidence)

# Tester terrain puis marquer VALIDATED
```

---

## Backfill Historique

### Principe

Training Intelligence peut être **pré-remplie** depuis l'historique Intervals.icu pour éviter de partir de zéro. Le **backfill** extrait automatiquement learnings et patterns depuis 2 ans de données (2024-2025) pour accélérer l'accumulation de knowledge.

**Avantages** :
- ✅ Démarrer avec 10+ learnings VALIDATED au lieu de 0
- ✅ Détecter patterns récurrents (VO2/sommeil, outdoor discipline)
- ✅ Identifier FTP progression historique
- ✅ Gains PID adaptatifs immédiatement opérationnels

**Données Extraites** :
1. **Sweet-Spot Sessions** : Intensité optimale (88-90% FTP)
2. **VO2/Sleep Correlation** : Impact sommeil sur VO2 max
3. **Outdoor Discipline** : Overshoot intensité sorties outdoor
4. **FTP Progression** : Évolution FTP sur période

---

### Installation Script

Le script `backfill-intelligence` est installé automatiquement avec le projet :

```bash
cd ~/cyclisme-training-logs
poetry install

# Vérifier disponibilité
poetry run backfill-intelligence --help
```

**Prérequis** :
- Intervals.icu API key (obtenir depuis Settings > API → Generate Key)
- Athlete ID (format `iXXXXXX`, visible dans URL Intervals.icu)

---

### Configuration Credentials

**Méthode 1 : Fichier .env (Recommandé)**

```bash
# Éditer .env à la racine du projet
cd ~/cyclisme-training-logs
nano .env

# Ajouter :
INTERVALS_ATHLETE_ID=iXXXXXX
INTERVALS_API_KEY=votre_api_key_ici
```

**Méthode 2 : Arguments CLI**

```bash
poetry run backfill-intelligence \
  --athlete-id iXXXXXX \
  --api-key votre_api_key \
  --start-date 2024-01-01 \
  --end-date 2025-12-31
```

---

### Usage Basique

**Backfill Complet 2024-2025** :

```bash
poetry run backfill-intelligence \
  --start-date 2024-01-01 \
  --end-date 2025-12-31 \
  --output ~/cyclisme-training-logs-data/intelligence/intelligence_backfilled.json
```

**Output Attendu** :
```
🚀 Starting backfill: 2024-01-01 → 2025-12-31
📁 Output: /Users/you/cyclisme-training-logs-data/intelligence/intelligence_backfilled.json
============================================================

📥 Fetching activities from 2024-01-01 to 2025-12-31...
   ✅ Fetched 247 activities

😴 Fetching wellness data from 2024-01-01 to 2025-12-31...
   ✅ Fetched 730 wellness entries

🍭 Analyzing Sweet-Spot sessions...
   ✅ Created learning: 87 sessions, confidence=validated

😴 Analyzing VO2/sleep correlation...
   ✅ Created pattern: 12 failures/34 attempts, confidence=validated

🚴 Analyzing outdoor discipline...
   ✅ Created pattern: 156 outdoor rides, +15.3% IF, confidence=validated

📈 Analyzing FTP progression...
   ✅ Created learning: +10W over 24 months, confidence=high

💾 Saving intelligence to /Users/you/cyclisme-training-logs-data/intelligence/intelligence_backfilled.json...

============================================================
✨ Backfill complete!
   Learnings: 2
   Patterns: 2
   Saved to: /Users/you/cyclisme-training-logs-data/intelligence/intelligence_backfilled.json
```

---

### Analyses Extraites

#### 1. Sweet-Spot Sessions

**Objectif** : Identifier intensité sweet-spot optimale (88-92% FTP).

**Méthode** :
- Classifier toutes activités avec IF 0.85-0.93 ou nom contenant "sweet", "ss", "sst"
- Calculer moyenne IF, durée, découplage
- Créer learning si >= 10 sessions trouvées

**Exemple Output** :
```python
# Learning créé :
category = "sweet-spot"
description = "88-90% FTP sustainable for 2x10min+ intervals"
evidence = [
    "87 sessions completed",
    "Avg IF 0.89",
    "Intensity range 88-90% FTP sustainable"
]
confidence = ConfidenceLevel.VALIDATED  # 87 sessions
```

---

#### 2. VO2/Sleep Correlation

**Objectif** : Détecter pattern échec VO2 max après nuit courte (<6h).

**Méthode** :
- Identifier activités VO2 (IF > 1.05 ou nom contenant "vo2", "max", "hiit")
- Croiser avec données wellness (sleepSecs)
- Compter échecs (IF faible + TSS bas) vs succès
- Créer pattern si >= 10 échecs détectés

**Exemple Output** :
```python
# Pattern créé :
name = "sleep_debt_vo2_failure"
trigger_conditions = {"sleep": "<6h", "workout_type": "VO2"}
observed_outcome = "Incapacité finir intervalles, RPE 9+ (12 échecs sur 34 tentatives)"
frequency = 34
confidence = ConfidenceLevel.VALIDATED
```

---

#### 3. Outdoor Discipline

**Objectif** : Mesurer overshoot intensité sorties outdoor vs indoor.

**Méthode** :
- Séparer activités "Ride" (outdoor) vs "VirtualRide" (indoor)
- Calculer IF moyen outdoor vs indoor
- Si overshoot > 10% → Créer pattern

**Exemple Output** :
```python
# Pattern créé :
name = "outdoor_intensity_overshoot"
trigger_conditions = {"workout_location": "outdoor"}
observed_outcome = "IF +15.3% vs indoor (0.78 vs 0.67)"
frequency = 156
confidence = ConfidenceLevel.VALIDATED
```

---

#### 4. FTP Progression

**Objectif** : Documenter progression FTP sur période historique.

**Méthode** :
- Récupérer FTP actuelle depuis athlete profile
- Estimer FTP début période (approximation linéaire)
- Calculer progression W et %

**Exemple Output** :
```python
# Learning créé :
category = "ftp_progression"
description = "FTP progression 250W → 260W"
evidence = [
    "FTP 250W → 260W",
    "+10W (+4.0%)",
    "Rate: +0.42W/month over 24 months"
]
confidence = ConfidenceLevel.HIGH
```

---

### Utilisation Intelligence Backfillée

**Charger intelligence backfillée** :

```python
from pathlib import Path
from cyclisme_training_logs.intelligence import TrainingIntelligence

# Charger fichier backfillé
intelligence_file = Path("~/cyclisme-training-logs-data/intelligence/intelligence_backfilled.json").expanduser()
intelligence = TrainingIntelligence.load_from_file(intelligence_file)

print(f"Learnings : {len(intelligence.learnings)}")
print(f"Patterns  : {len(intelligence.patterns)}")

# Vérifier learnings VALIDATED
validated = [l for l in intelligence.learnings.values() if l.validated]
print(f"\nLearnings VALIDATED : {len(validated)}")
for learning in validated:
    print(f"  - {learning.description} ({len(learning.evidence)} obs)")

# Vérifier patterns fréquents
frequent_patterns = [p for p in intelligence.patterns.values() if p.frequency >= 10]
print(f"\nPatterns fréquents : {len(frequent_patterns)}")
for pattern in frequent_patterns:
    print(f"  - {pattern.name} (freq: {pattern.frequency})")
```

**Output Attendu** :
```
Learnings : 2
Patterns  : 2

Learnings VALIDATED : 1
  - 88-90% FTP sustainable for 2x10min+ intervals (3 obs)

Patterns fréquents : 2
  - sleep_debt_vo2_failure (freq: 34)
  - outdoor_intensity_overshoot (freq: 156)
```

---

### Merger avec Intelligence Existante

Si vous avez déjà une intelligence active, vous pouvez merger le backfill :

```python
from pathlib import Path
from cyclisme_training_logs.intelligence import TrainingIntelligence

# Charger intelligence active
active_file = Path("~/cyclisme-training-logs-data/intelligence/state.json").expanduser()
active = TrainingIntelligence.load_from_file(active_file)

# Charger backfill
backfill_file = Path("~/cyclisme-training-logs-data/intelligence/intelligence_backfilled.json").expanduser()
backfill = TrainingIntelligence.load_from_file(backfill_file)

# Merger (backfill → active)
active.learnings.update(backfill.learnings)
active.patterns.update(backfill.patterns)

print(f"Intelligence mergée :")
print(f"  Learnings : {len(active.learnings)}")
print(f"  Patterns  : {len(active.patterns)}")

# Sauvegarder merged
active.save_to_file(active_file)
print(f"✅ Sauvegardé : {active_file}")
```

---

### Troubleshooting Backfill

#### Problème : API Key Invalid

**Symptôme** :
```
❌ Error fetching activities: 401 Unauthorized
```

**Solution** :
1. Vérifier API key dans Intervals.icu Settings → API
2. Régénérer API key si expirée
3. Mettre à jour `.env` avec nouvelle key

---

#### Problème : Aucune Activité Trouvée

**Symptôme** :
```
📥 Fetching activities from 2024-01-01 to 2025-12-31...
   ✅ Fetched 0 activities
```

**Causes Possibles** :
1. Athlete ID incorrect (vérifier format `iXXXXXX`)
2. Période sans données (vérifier calendrier Intervals.icu)
3. Activités supprimées ou privées

**Solution** :
```bash
# Tester API manuellement
curl -u "API_iXXXXXX:votre_api_key" \
  "https://intervals.icu/api/v1/athlete/iXXXXXX/activities?oldest=2024-01-01&newest=2024-12-31"
```

---

#### Problème : Confidence Plus Basse qu'Attendu

**Symptôme** : Sweet-spot learning = MEDIUM au lieu de VALIDATED malgré 87 sessions.

**Cause** : Confidence basée sur **count d'evidence**, pas count de sessions.

**Solution** : Le backfill assigne directement confidence selon session count :
```python
# Code backfill (backfill_intelligence.py:199-206)
session_count = len(sweet_spot_sessions)
if session_count >= 10:
    learning.confidence = ConfidenceLevel.VALIDATED
elif session_count >= 6:
    learning.confidence = ConfidenceLevel.HIGH
elif session_count >= 3:
    learning.confidence = ConfidenceLevel.MEDIUM
```

---

### Customisation Backfill

Le script backfill est extensible pour analyses custom :

```python
from cyclisme_training_logs.scripts.backfill_intelligence import IntervalsICUBackfiller

# Créer backfiller custom
backfiller = IntervalsICUBackfiller(
    athlete_id="iXXXXXX",
    api_key="your_api_key"
)

# Fetch data
activities = backfiller.fetch_activities("2024-01-01", "2025-12-31")
wellness = backfiller.fetch_wellness("2024-01-01", "2025-12-31")

# Analyse custom : Hydratation impact
hydration_sessions = [
    a for a in activities
    if a.get("name", "").lower().find("hydrat") != -1
]

if len(hydration_sessions) >= 5:
    backfiller.intelligence.add_learning(
        category="hydration",
        description="Hydratation optimale identifiée",
        evidence=[f"{len(hydration_sessions)} sessions analysées"],
        level=AnalysisLevel.WEEKLY
    )

# Sauvegarder
backfiller.intelligence.save_to_file(Path("~/data/intelligence_custom.json"))
```

---

## Contrôle PID Adaptatif

### Principe

Training Intelligence intègre un **contrôleur PID** (Proportionnel-Intégral-Dérivé) pour ajuster automatiquement la charge d'entraînement selon l'écart entre **FTP cible** et **FTP actuelle**.

**Composantes PID** :
- **P (Proportionnel)** : Réaction immédiate à l'écart FTP actuel
- **I (Intégral)** : Correction cumulative des écarts persistants
- **D (Dérivé)** : Anticipation tendances (FTP augmente/diminue)

**Gains Adaptatifs** :
Les gains Kp, Ki, Kd sont calculés **automatiquement** depuis Training Intelligence accumulée :
- **Kp** : Basé sur learnings validés (confiance système)
- **Ki** : Basé sur evidence cumulée (stabilité corrections)
- **Kd** : Basé sur patterns fréquents (détection tendances)

---

### Formule PID

**Équation** :
```
output = Kp × error + Ki × ∫error dt + Kd × d(error)/dt
```

**Traduction TSS** :
```
TSS_adjustment = output × 12.5

Approximation : +1W FTP ≈ +10-15 TSS/semaine sustained
Multiplicateur : 12.5 (milieu de gamme)
```

**Saturations** :
- **Integral Anti-Windup** : ±100W (éviter accumulation excessive)
- **Output Saturation** : ±50 TSS/semaine (limites raisonnables)

---

### Gains Adaptatifs - Règles de Calcul

#### Kp (Proportionnel) : Basé sur Learnings Validés

**Formule** :
```python
validated_count = count(learnings with confidence HIGH or VALIDATED)

Kp = 0.005 + (validated_count / 100) × 0.010
Kp = min(Kp, 0.015)  # Cap à 0.015
```

**Interprétation** :
- Plus de learnings validés = confiance système élevée = Kp agressif
- Range : 0.005 (conservateur) → 0.015 (agressif)

**Exemple** :
```python
# Débutant : 0 learnings validés
Kp = 0.005  # Conservateur

# Expérimenté : 10 learnings validés
Kp = 0.005 + (10 / 100) × 0.010 = 0.006

# Expert : 50 learnings validés
Kp = 0.005 + (50 / 100) × 0.010 = 0.010

# Veteran : 100+ learnings validés
Kp = 0.015 (cap atteint)
```

---

#### Ki (Intégral) : Basé sur Evidence Cumulée

**Formule** :
```python
total_evidence = sum(len(learning.evidence) for all learnings)

if total_evidence > 50:
    Ki = 0.003
elif total_evidence > 20:
    Ki = 0.002
else:
    Ki = 0.001
```

**Interprétation** :
- Plus d'evidence = corrections cumulatives plus fortes
- Paliers : 0.001 (défaut) → 0.002 (stable) → 0.003 (très stable)

---

#### Kd (Dérivé) : Basé sur Patterns Fréquents

**Formule** :
```python
frequent_patterns = count(patterns with frequency >= 10)

if frequent_patterns >= 3:
    Kd = 0.25
elif frequent_patterns >= 1:
    Kd = 0.15
else:
    Kd = 0.10
```

**Interprétation** :
- Plus de patterns détectés = meilleure anticipation tendances
- Paliers : 0.10 (défaut) → 0.15 (anticipation modérée) → 0.25 (anticipation forte)

---

### Usage Basique

**Correction Simple** :

```python
from cyclisme_training_logs.intelligence import (
    TrainingIntelligence,
    PIDController,
    compute_pid_gains_from_intelligence
)

# Charger intelligence (avec backfill recommandé)
intelligence = TrainingIntelligence.load_from_file("~/data/intelligence.json")

# Calculer gains adaptatifs
gains = compute_pid_gains_from_intelligence(intelligence)
print(f"Gains calculés : Kp={gains['kp']:.3f}, Ki={gains['ki']:.3f}, Kd={gains['kd']:.3f}")

# Créer contrôleur
controller = PIDController(
    kp=gains["kp"],
    ki=gains["ki"],
    kd=gains["kd"],
    setpoint=260  # FTP cible = 260W
)

# Calculer correction
correction = controller.compute(measured_value=220, dt=1.0)  # FTP actuelle = 220W

print(f"\n📊 CORRECTION PID :")
print(f"Error          : {correction['error']} W")
print(f"P term         : {correction['p_term']:.3f}")
print(f"I term         : {correction['i_term']:.3f}")
print(f"D term         : {correction['d_term']:.3f}")
print(f"Output         : {correction['output']:.3f} W/semaine")
print(f"TSS adjustment : {correction['tss_adjustment']} TSS/semaine")

# Recommandation actionnable
recommendation = controller.get_action_recommendation(correction)
print(f"\n💡 RECOMMANDATION : {recommendation}")
```

**Output Attendu** :
```
Gains calculés : Kp=0.007, Ki=0.002, Kd=0.15

📊 CORRECTION PID :
Error          : 40.0 W
P term         : 0.280
I term         : 0.080
D term         : 6.000
Output         : 6.360 W/semaine
TSS adjustment : +25 TSS/semaine

💡 RECOMMANDATION : Augmenter TSS +25/semaine - Focus Sweet-Spot 88-90% FTP
```

---

### Intégration TrainingIntelligence

Training Intelligence fournit une méthode intégrée `get_pid_correction()` :

```python
from pathlib import Path
from cyclisme_training_logs.intelligence import TrainingIntelligence

# Charger intelligence
intelligence = TrainingIntelligence.load_from_file(
    Path("~/data/intelligence_backfilled.json")
)

# Obtenir correction PID + recommandation
result = intelligence.get_pid_correction(
    current_ftp=220,  # FTP actuelle
    target_ftp=260,   # FTP cible
    dt=1.0            # Delta temps (semaines)
)

# Afficher résultats
print(f"📊 GAINS ADAPTATIFS :")
print(f"  Kp : {result['gains']['kp']:.3f}")
print(f"  Ki : {result['gains']['ki']:.3f}")
print(f"  Kd : {result['gains']['kd']:.3f}")

print(f"\n📈 CORRECTION :")
print(f"  Error : {result['correction']['error']} W")
print(f"  TSS adjustment : {result['correction']['tss_adjustment']} TSS/semaine")

print(f"\n💡 RECOMMANDATION :")
print(f"  {result['recommendation']}")
```

---

### Workflow Hebdomadaire avec PID

**Scénario** : Ajuster charge hebdomadaire basée sur FTP tests réguliers.

```python
from pathlib import Path
from cyclisme_training_logs.intelligence import TrainingIntelligence

# Charger intelligence
intelligence_file = Path("~/data/intelligence.json").expanduser()
intelligence = TrainingIntelligence.load_from_file(intelligence_file)

# Objectif : Atteindre 265W FTP en 12 semaines
target_ftp = 265
current_ftp = 250

print(f"🎯 OBJECTIF : {current_ftp}W → {target_ftp}W sur 12 semaines")
print(f"=" * 60)

# Simuler 12 semaines avec ajustements PID
for week in range(1, 13):
    # Obtenir correction PID
    result = intelligence.get_pid_correction(
        current_ftp=current_ftp,
        target_ftp=target_ftp,
        dt=1.0
    )

    tss_adj = result["correction"]["tss_adjustment"]
    recommendation = result["recommendation"]

    print(f"\n📅 SEMAINE {week} :")
    print(f"  FTP actuelle : {current_ftp}W")
    print(f"  Écart cible  : {result['correction']['error']}W")
    print(f"  TSS ajust    : {tss_adj:+d} TSS/semaine")
    print(f"  Action       : {recommendation}")

    # Simuler progression (+1W toutes les 2 semaines si TSS augmenté)
    if tss_adj > 0 and week % 2 == 0:
        current_ftp += 1.0

    # Convergence atteinte ?
    if abs(result["correction"]["error"]) < 3:
        print(f"\n✅ OBJECTIF ATTEINT à semaine {week} !")
        break

# Sauvegarder état
intelligence.save_to_file(intelligence_file)
```

---

### Reset PID State

Le contrôleur PID maintient un **état interne** (integral, prev_error). Vous devez **reset** l'état dans ces situations :

1. **Changement phase entraînement** (base → build → peak)
2. **Après pause longue** (>2 semaines sans entraînement)
3. **Changement objectif FTP** (nouvelle cible)

```python
from cyclisme_training_logs.intelligence import PIDController

controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

# Utiliser plusieurs semaines
for week in range(10):
    correction = controller.compute(measured_value=240, dt=1.0)

# État PID accumulé
print(f"Integral : {controller.state.integral}")
print(f"Prev error : {controller.state.prev_error}")

# Reset avant nouvelle phase
controller.reset()

print(f"\nAprès reset :")
print(f"Integral : {controller.state.integral}")  # 0.0
print(f"Prev error : {controller.state.prev_error}")  # 0.0
```

---

### Anti-Windup et Saturation

#### Anti-Windup (Integral)

L'integral term peut **accumuler indéfiniment** si erreur persiste. Anti-windup **sature l'integral** à ±100W :

```python
# Code PID (pid_controller.py:138-141)
max_integral = 100.0
if abs(self.state.integral) > max_integral:
    self.state.integral = max_integral if self.state.integral > 0 else -max_integral
```

**Exemple** :
```python
controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)

# Erreur constante pendant 100 semaines
for week in range(100):
    correction = controller.compute(measured_value=220, dt=1.0)

# Integral saturé à ±100W
assert abs(controller.state.integral) <= 100.0
```

---

#### Output Saturation (TSS)

L'output TSS est **saturé à ±50 TSS/semaine** pour éviter ajustements irréalistes :

```python
# Code PID (pid_controller.py:154-157)
max_tss_change = 50
if abs(tss_adjustment) > max_tss_change:
    tss_adjustment = max_tss_change if tss_adjustment > 0 else -max_tss_change
```

**Exemple** :
```python
# Gains très élevés + erreur énorme
controller = PIDController(kp=0.1, ki=0.05, kd=0.5, setpoint=260)
correction = controller.compute(measured_value=160, dt=1.0)  # Erreur 100W

# TSS adjustment saturé
assert abs(correction["tss_adjustment"]) <= 50
```

---

### Troubleshooting PID

#### Problème : Gains Tous à Minimum (0.005, 0.001, 0.10)

**Cause** : Intelligence vide ou peu de learnings/patterns.

**Solution** : Exécuter backfill historique pour pré-remplir intelligence :
```bash
poetry run backfill-intelligence --start-date 2024-01-01 --end-date 2025-12-31
```

---

#### Problème : TSS Adjustment Toujours Saturé (±50)

**Cause** : Écart FTP trop important ou gains trop élevés.

**Solution 1** : Réduire objectif FTP (approche incrémentale)
```python
# Au lieu de 220W → 260W direct
# Faire 220W → 235W (12 semaines) → 250W (12 semaines) → 260W
```

**Solution 2** : Reset PID après plateau
```python
controller.reset()  # Clear integral accumulation
```

---

#### Problème : Oscillations (TSS +30 → -20 → +25)

**Cause** : Kd (dérivé) trop élevé ou dt variable.

**Solution** :
```python
# Forcer dt constant (toujours 1.0 semaine)
correction = controller.compute(measured_value=ftp, dt=1.0)

# OU réduire Kd manuellement
controller.kd = 0.10  # Au lieu de 0.25
```

---

### Limites Système PID

**PID suppose** :
1. ✅ Feedback régulier (FTP tests toutes les 2-4 semaines)
2. ✅ Relation linéaire TSS ↔ FTP (approximation)
3. ✅ Pas de facteurs externes majeurs (blessure, maladie)

**PID ne remplace pas** :
- ❌ Planification macro-cycle (périodisation)
- ❌ Choix type séances (sweet-spot vs VO2 vs endurance)
- ❌ Gestion fatigue aiguë (nécessite patterns wellness)

**Utiliser PID comme** :
- ✅ Guideline ajustement charge hebdo
- ✅ Détection stagnation (integral croissant sans progrès)
- ✅ Validation empirique (comparer recommandation vs ressenti)

---

## API Reference

### TrainingIntelligence

#### `__init__() -> None`
Initialise intelligence avec mémoire vide.

#### `add_learning(category, description, evidence, level, impact="MEDIUM", confidence=None) -> TrainingLearning`
Ajoute ou met à jour learning.

**Args** :
- `category` (str) : Catégorie (ex : "sweet-spot")
- `description` (str) : Description concise
- `evidence` (List[str]) : Preuves
- `level` (AnalysisLevel) : Niveau découverte
- `impact` (str) : Impact (LOW/MEDIUM/HIGH)
- `confidence` (ConfidenceLevel) : Override auto-compute

**Returns** : TrainingLearning créé/mis à jour

#### `identify_pattern(name, trigger_conditions, observed_outcome, observation_date) -> Pattern`
Identifie ou met à jour pattern.

**Args** :
- `name` (str) : Nom pattern (snake_case)
- `trigger_conditions` (Dict) : Conditions déclencheurs
- `observed_outcome` (str) : Résultat observé
- `observation_date` (date) : Date observation

**Returns** : Pattern créé/mis à jour

#### `propose_adaptation(protocol_name, adaptation_type, current_rule, proposed_rule, justification, evidence) -> ProtocolAdaptation`
Propose adaptation protocole.

**Args** :
- `protocol_name` (str) : Nom protocole
- `adaptation_type` (str) : ADD/MODIFY/REMOVE
- `current_rule` (str) : Règle actuelle
- `proposed_rule` (str) : Règle proposée
- `justification` (str) : Pourquoi
- `evidence` (List[str]) : Preuves

**Returns** : ProtocolAdaptation créée

#### `get_daily_insights(context) -> Dict`
Insights quotidiens.

**Args** :
- `context` (Dict) : Contexte séance

**Returns** : Dict avec keys :
- `relevant_learnings` : List[TrainingLearning]
- `active_patterns` : List[Pattern]
- `recommendations` : List[str]

#### `get_weekly_synthesis(week_number) -> Dict`
Synthèse hebdomadaire.

**Args** :
- `week_number` (int) : Numéro semaine ISO

**Returns** : Dict avec keys :
- `total_learnings` : int
- `high_confidence_learnings` : List[TrainingLearning]
- `active_patterns` : List[Pattern]
- `pending_adaptations` : List[ProtocolAdaptation]

#### `get_monthly_trends(month, year) -> Dict`
Tendances mensuelles.

**Args** :
- `month` (int) : Mois (1-12)
- `year` (int) : Année

**Returns** : Dict avec keys :
- `validated_learnings` : List[TrainingLearning]
- `top_patterns` : List[Pattern]
- `validated_adaptations` : List[ProtocolAdaptation]

#### `get_pid_correction(current_ftp, target_ftp, dt=1.0) -> Dict`
Obtenir correction PID automatique pour progression FTP (Sprint R4++).

**Args** :
- `current_ftp` (float) : FTP actuelle (W)
- `target_ftp` (float) : FTP cible (W)
- `dt` (float) : Delta temps depuis dernier appel (semaines, défaut 1.0)

**Returns** : Dict avec keys :
- `correction` (Dict) : Output from PIDController.compute()
  - `error` (float) : Écart FTP (W)
  - `p_term` (float) : Contribution proportionnelle
  - `i_term` (float) : Contribution intégrale
  - `d_term` (float) : Contribution dérivée
  - `output` (float) : Correction totale (W/semaine)
  - `tss_adjustment` (int) : Ajustement TSS hebdo suggéré
- `recommendation` (str) : Action suggérée (français)
- `gains` (Dict) : Gains adaptatifs calculés
  - `kp` (float) : Gain proportionnel
  - `ki` (float) : Gain intégral
  - `kd` (float) : Gain dérivé

**Example** :
```python
result = intelligence.get_pid_correction(
    current_ftp=220,
    target_ftp=260,
    dt=1.0
)
print(f"TSS adjustment: {result['correction']['tss_adjustment']}")
print(f"Recommendation: {result['recommendation']}")
```

#### `save_to_file(file_path: Path) -> None`
Sauvegarde état JSON.

#### `load_from_file(file_path: Path) -> TrainingIntelligence`
Charge état JSON (classmethod).

---

### PIDController

#### `__init__(kp, ki, kd, setpoint) -> None`
Initialise contrôleur PID.

**Args** :
- `kp` (float) : Gain proportionnel (0.005-0.015 recommandé)
- `ki` (float) : Gain intégral (0.001-0.005 recommandé)
- `kd` (float) : Gain dérivé (0.1-0.3 recommandé)
- `setpoint` (float) : FTP cible (W)

**Raises** :
- `ValueError` : Si gains négatifs ou setpoint <= 0

#### `compute(measured_value, dt=1.0) -> Dict`
Calculer correction PID.

**Args** :
- `measured_value` (float) : FTP actuelle (W)
- `dt` (float) : Delta temps depuis dernier appel (semaines, défaut 1.0)

**Returns** : Dict avec keys :
- `error` (float) : Écart FTP (W)
- `p_term` (float) : Contribution proportionnelle
- `i_term` (float) : Contribution intégrale
- `d_term` (float) : Contribution dérivée
- `output` (float) : Correction totale (W/semaine suggérée)
- `tss_adjustment` (int) : Ajustement TSS hebdo suggéré (±50 max)

**Example** :
```python
controller = PIDController(kp=0.01, ki=0.002, kd=0.15, setpoint=260)
correction = controller.compute(measured_value=220, dt=1.0)
print(f"TSS adjustment: {correction['tss_adjustment']}")
```

#### `reset() -> None`
Reset internal PID state (integral, prev_error).

Utiliser lors de :
- Changement phase entraînement
- Après pause longue (>2 semaines)
- Changement objectif FTP

#### `get_action_recommendation(correction) -> str`
Traduire correction PID en recommandation actionnable.

**Args** :
- `correction` (Dict) : Output from compute()

**Returns** : str - Recommandation texte (français)

**Example** :
```python
correction = controller.compute(measured_value=220)
recommendation = controller.get_action_recommendation(correction)
print(recommendation)
# "Augmenter TSS +25/semaine - Focus Sweet-Spot 88-90% FTP"
```

---

### compute_pid_gains_from_intelligence

#### `compute_pid_gains_from_intelligence(intelligence) -> Dict`
Calculer gains PID optimaux depuis Training Intelligence.

**Args** :
- `intelligence` (TrainingIntelligence) : Instance (avec backfill recommandé)

**Returns** : Dict avec keys :
- `kp` (float) : 0.005-0.015 (basé sur learnings validés)
- `ki` (float) : 0.001-0.003 (basé sur evidence cumulée)
- `kd` (float) : 0.10-0.25 (basé sur patterns fréquents)

**Gain Calculation Rules** :
- **Kp** : Based on validated learnings count (confidence)
  - 0 learnings → 0.005 (conservateur)
  - 100+ learnings → 0.015 (agressif)
- **Ki** : Based on cumulative evidence (stability)
  - <20 evidence → 0.001
  - 20-50 evidence → 0.002
  - >50 evidence → 0.003
- **Kd** : Based on frequent patterns (trend detection)
  - 0-0 patterns (freq >= 10) → 0.10
  - 1-2 patterns → 0.15
  - 3+ patterns → 0.25

**Example** :
```python
intelligence = TrainingIntelligence.load_from_file("~/data/intelligence.json")
gains = compute_pid_gains_from_intelligence(intelligence)
print(f"Kp={gains['kp']:.3f}, Ki={gains['ki']:.3f}, Kd={gains['kd']:.3f}")
```

---

## Troubleshooting

### Problème : Learning non détecté comme similaire

**Symptôme** : Ajout learning crée nouveau au lieu de renforcer existant.

**Cause** : Description pas exactement identique.

**Solution** :
```python
# ❌ Mauvais (descriptions différentes)
intelligence.add_learning(
    category="sweet-spot",
    description="88% FTP sustainable",
    ...
)
intelligence.add_learning(
    category="sweet-spot",
    description="88-90% FTP sustainable",  # Différent !
    ...
)

# ✅ Bon (descriptions identiques)
description = "88-90% FTP sustainable 2x10min"
intelligence.add_learning(category="sweet-spot", description=description, ...)
intelligence.add_learning(category="sweet-spot", description=description, ...)
```

### Problème : Pattern ne matche pas conditions

**Symptôme** : `pattern.matches(context)` retourne False alors que conditions semblent bonnes.

**Cause** : Clé manquante dans context ou opérateur mal formé.

**Solution** :
```python
# Pattern trigger_conditions
pattern.trigger_conditions = {"sleep": "<6h", "workout_type": "VO2"}

# ❌ Mauvais (clé "sleep" manquante)
pattern.matches({"workout_type": "VO2"})  # False

# ❌ Mauvais (valeur "VO2" pas match "=VO2")
pattern.trigger_conditions = {"workout_type": "=VO2"}
pattern.matches({"workout_type": "VO2"})  # False (besoin "=")

# ✅ Bon
pattern.matches({"sleep": 5.5, "workout_type": "VO2"})  # True
```

### Problème : Fichier JSON corrompu après crash

**Symptôme** : `load_from_file()` lève exception JSON.

**Solution** :
```python
from pathlib import Path
import json

intelligence_file = Path("~/cyclisme-training-logs-data/intelligence/state.json").expanduser()

try:
    intelligence = TrainingIntelligence.load_from_file(intelligence_file)
except (FileNotFoundError, json.JSONDecodeError):
    print("⚠️  Fichier corrompu, création nouveau")
    intelligence = TrainingIntelligence()
```

---

## FAQ

### Q1 : Quelle différence entre Learning et Pattern ?

**Learning** : Enseignement sur **ce qui fonctionne** (ex : "88% FTP optimal").
**Pattern** : Observation de **ce qui échoue** dans certaines conditions (ex : "Sleep < 6h → Échec VO2").

### Q2 : Quand marquer adaptation comme VALIDATED ?

Après avoir **testé terrain** l'adaptation proposée et confirmé qu'elle résout le problème.

Exemple :
1. Pattern détecté : Sleep < 6h → Échec VO2
2. Adaptation proposée : Modifier VETO de 6h → 6.5h
3. Tester : Annuler VO2 si sleep < 6.5h pendant 2 semaines
4. Si 0 échec : Marquer `adaptation.status = "VALIDATED"`

### Q3 : Combien de temps conserver l'historique ?

Le module Training Intelligence **ne supprime jamais** automatiquement. À vous de décider :

- **Option 1** : Conserver tout (recommandé, taille JSON < 1MB/an)
- **Option 2** : Archiver learnings/patterns LOW confidence après 3 mois
- **Option 3** : Reset annuel (sauvegarder puis recommencer)

### Q4 : Peut-on merger plusieurs fichiers intelligence ?

Oui, manuellement :
```python
intel1 = TrainingIntelligence.load_from_file(Path("file1.json"))
intel2 = TrainingIntelligence.load_from_file(Path("file2.json"))

# Merger
intel1.learnings.update(intel2.learnings)
intel1.patterns.update(intel2.patterns)
intel1.adaptations.update(intel2.adaptations)

# Sauvegarder merged
intel1.save_to_file(Path("merged.json"))
```

### Q5 : Comment intégrer avec analyses quotidiennes/hebdo/mensuelles ?

Les modules existants peuvent appeler Training Intelligence :

**Analyse quotidienne** :
```python
# Dans daily_aggregator.py
from cyclisme_training_logs.intelligence import TrainingIntelligence, AnalysisLevel

def analyze_session(session_data):
    # ... analyse existante ...

    # Charger intelligence
    intelligence = TrainingIntelligence.load_from_file(intelligence_file)

    # Ajouter learning si découverte
    if discovery:
        intelligence.add_learning(...)

    # Consulter insights pour recommandations
    insights = intelligence.get_daily_insights(context)

    # Sauvegarder
    intelligence.save_to_file(intelligence_file)
```

---

**Fin du Guide Training Intelligence v2.1.0**

Pour support technique, voir :
- [CHANGELOG.md](../CHANGELOG.md) - Historique versions
- [README.md](../README.md) - Vue d'ensemble projet
- Sphinx API : `docs/_build/html/modules/intelligence.html`
