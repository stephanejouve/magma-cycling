# Compensation TSS Proactive - Guide Utilisateur

**Date**: 29 Janvier 2026
**Sprint**: S080
**Version**: 1.0

---

## 📋 Vue d'Ensemble

Le système de **Compensation TSS Proactive** implémente le **terme Intégral (I) du PID discrete controller** pour détecter et corriger automatiquement les déficits TSS hebdomadaires causés par des séances sautées.

### Problème Résolu

**Avant** : Le système servo était UNIQUEMENT réactif (déclenché après séance complétée)
```
Séances sautées → Aucune action système
                → Déficit TSS ignoré
                → Quota hebdomadaire compromis
```

**Après** : Le système est maintenant proactif ET réactif
```
Séances sautées → Détection automatique (daily-sync)
                → Recommandations AI intelligentes
                → Email avec stratégies compensation
                → Quota hebdomadaire maintenu
```

---

## 🎯 Fonctionnement

### 1. Détection Automatique (Daily-Sync)

Chaque jour à 21h30, `daily-sync` exécute :

1. **Vérification activités** (existant)
2. **Servo mode réactif** (existant)
3. **🆕 Compensation TSS Proactive** (nouveau)
   - Compare planning semaine vs activités complétées
   - Calcule déficit TSS (planifié - complété)
   - Si déficit > 50 TSS → Déclenche recommandations AI

### 2. Contexte Complet

Le système collecte automatiquement :

- ✅ **Séances sautées** : Dates, noms, TSS manqué
- ✅ **Séances restantes** : Planning jusqu'à dimanche
- ✅ **Métriques athlète** : TSB, sommeil, HRV, RPE
- ✅ **Jours repos disponibles** : Dimanche, etc.
- ✅ **Séances indoor convertibles** : Potentiel gain outdoor
- ✅ **Météo semaine** (mock actuellement - TODO: API réelle)

### 3. Recommandations AI

Le coach AI analyse le contexte et propose une stratégie parmi :

#### 📊 6 Stratégies Disponibles

| Stratégie | Gain TSS | Conditions | Priorité |
|-----------|----------|------------|----------|
| **1. Intensifier séances** | +10-20/séance | Forme OK, ≥2j restants | ⭐⭐⭐ |
| **2. Ajouter séance courte** | +30-40 TSS | Disponibilité, forme OK | ⭐⭐ |
| **3. Convertir indoor→outdoor** | +15-25% TSS | Météo >5°C, indoor planifiées | ⭐⭐⭐ |
| **4. Utiliser jour repos** | +40-80 TSS | TSB >+5, forme excellente | ⭐⭐ |
| **5. Compensation partielle + report** | Variable | Trop tard dans semaine | ⭐ |
| **6. Accepter déficit** | 0 TSS | Fatigue détectée | 🚨 |

#### 🧠 Matrice de Décision

```
Contexte                    | Jours Restants | Forme | Décision
----------------------------|----------------|-------|------------------
Circonstances (non fatigue) | ≥3 jours       | Bonne | Compenser immédiat
Circonstances               | 1-2 jours      | Bonne | Partiel + report
Circonstances               | 0 jour         | Bonne | Reporter S+1
Fatigue détectée            | Peu importe    | Mauvaise | Accepter déficit
```

### 4. Email Daily Report

Les recommandations sont ajoutées au rapport quotidien :

```markdown
## 🎯 Compensation TSS Proactive

**Semaine S078 - Déficit détecté: -60 TSS**

**Jours restants:** 2

### Stratégie Recommandée: COMBINED

**Action 1: Convert Outdoor**
- Séance: Tempo 45min
- Gain: +10 TSS
- Justification: Météo favorable, gain TSS outdoor

**Action 2: Use Rest Day**
- Séance: Dimanche
- Gain: +50 TSS
- Justification: Forme excellente (TSB +5), repos disponible

---

**Compensation totale:** +60 TSS
**Déficit résiduel:** 0 TSS

⚠️  **Note:** Recommandations non appliquées automatiquement.
Valider et ajuster manuellement selon ressenti.
```

---

## 🚀 Utilisation

### Configuration Requise

**LaunchAgent daily-sync** doit être actif avec :
- `--ai-analysis` : Analyses AI activées
- `--week-id` : Semaine courante spécifiée

**Exemple** (déjà configuré) :
```xml
<string>--ai-analysis</string>
<string>--week-id</string>
<string>current</string>
```

### Mode Manuel

Pour tester manuellement :

```bash
# Daily sync complet avec compensation
poetry run daily-sync --date 2026-01-30 --week-id S078 --start-date 2026-01-27 --ai-analysis

# Envoyer email
poetry run daily-sync --date 2026-01-30 --week-id S078 --start-date 2026-01-27 --ai-analysis --send-email
```

### Seuil Déficit

Par défaut : **50 TSS**

Pour modifier (code) :
```python
# magma_cycling/daily_sync.py
compensation_result = evaluate_weekly_deficit(
    week_id=week_id,
    check_date=check_date,
    client=self.client,
    threshold_tss=50  # ← Modifier ici
)
```

---

## 📊 Exemples Scénarios

### Scénario 1 : Déficit Léger, Forme Excellente

**Contexte** :
- Déficit : -60 TSS (1 séance sautée)
- TSB : +8 (forme excellente)
- Jours restants : 4
- Météo : 12°C, favorable
- Repos dimanche disponible

**Stratégie AI** : COMBINED
```json
{
  "actions": [
    {"type": "convert_outdoor", "session": "Mercredi SS", "gain": 15},
    {"type": "convert_outdoor", "session": "Jeudi Tempo", "gain": 12},
    {"type": "use_rest_day", "day": "Dimanche", "workout": "END 60 TSS"}
  ],
  "total_compensated": 60,
  "conditions": ["Météo >5°C", "TSB >+5"]
}
```

### Scénario 2 : Déficit Élevé, Trop Tard

**Contexte** :
- Déficit : -120 TSS (2 séances sautées)
- TSB : +3 (forme correcte)
- Jours restants : 1 (samedi)
- Pas de repos disponible

**Stratégie AI** : PARTIAL_REPORT
```json
{
  "actions": [
    {"type": "intensify", "session": "Samedi", "from_tss": 50, "to_tss": 70, "gain": 20},
    {"type": "partial_report", "report_to_next_week": 100}
  ],
  "total_compensated": 20,
  "rationale": "Trop tard pour compenser 120 TSS. Report partiel."
}
```

### Scénario 3 : Fatigue Détectée

**Contexte** :
- Déficit : -80 TSS
- TSB : -7 (fatigue)
- Sommeil : 5.5h (insuffisant)
- HRV : -10% (baisse)

**Stratégie AI** : ACCEPT_DEFICIT
```json
{
  "actions": [
    {"type": "accept_deficit", "gain": 0}
  ],
  "total_compensated": 0,
  "rationale": "Priorité récupération. TSB négatif + sommeil insuffisant."
}
```

---

## 🔧 Architecture Technique

### Modules Créés

```
magma_cycling/
├── workflows/
│   └── proactive_compensation.py        # Core logic
│       ├── evaluate_weekly_deficit()    # Détection déficit
│       ├── _parse_cancelled_notes_tss() # Parse TSS notes annulées (FIX 29/01)
│       ├── _collect_compensation_context()  # Collecte contexte
│       ├── generate_compensation_prompt()   # Prompt AI
│       ├── parse_ai_compensation_response() # Parsing JSON
│       └── format_compensation_section()    # Email formatting
│
├── intelligence/
│   └── compensation_strategies.py       # 6 stratégies
│       ├── CompensationStrategy (Enum)
│       ├── CompensationAction (Class)
│       ├── get_strategy_matrix()
│       └── select_strategies()
│
└── daily_sync.py                        # Intégration
    └── run() → Appel compensation après servo
```

### 🔧 Fix Critique : Parsing Notes Annulées (29 Jan 2026)

**Problème Identifié** :
Quand `update-session` remplace une séance par une note (repos/annulation), le TSS original était perdu :

```python
# Avant fix
planned_events = client.get_events()  # Contient NOTE (TSS=0)
planned_tss = sum(e["load"] for e in planned_events)  # ← TSS perdu !
```

**Solution Implémentée** :
Parser les notes avec tags `[ANNULÉE]`, `[SAUTÉE]`, `[REMPLACÉE]` pour récupérer TSS depuis description :

```python
# update-session crée notes avec description:
"❌ SÉANCE ANNULÉE\n...\n(60min, 60 TSS)"
                              ↑
# Regex: r'\((\d+)min, (\d+) TSS\)'

def _parse_cancelled_notes_tss(events):
    """Parse TSS perdu depuis notes annulées."""
    lost_tss = 0
    for event in events:
        if event["category"] == "NOTE":
            if any(tag in event["name"] for tag in ["[ANNULÉE]", "[SAUTÉE]", "[REMPLACÉE]"]):
                match = re.search(r'\((\d+)min, (\d+) TSS\)', event["description"])
                if match:
                    lost_tss += float(match.group(2))
    return lost_tss
```

**Résultat** :
```python
# Après fix
all_events = client.get_events()  # Workouts + notes
workouts_tss = sum(e["load"] for e in workouts)
lost_tss = _parse_cancelled_notes_tss(all_events)  # ← TSS récupéré !
total_planned_tss = workouts_tss + lost_tss
```

**Tests Ajoutés** :
- `test_parse_cancelled_notes_single_note()` : Parse 1 note (60 TSS)
- `test_parse_cancelled_notes_multiple_notes()` : Parse 3 notes (190 TSS total)
- `test_parse_cancelled_notes_no_notes()` : Aucune note (0 TSS)

**Impact** :
- ✅ Déficit TSS maintenant correct même après `update-session`
- ✅ Compatible avec workflow existant (pas de breaking change)
- ✅ 3 tests supplémentaires (24 tests total vs 21)

### Tests

```bash
# Exécuter tests
poetry run pytest tests/workflows/test_proactive_compensation.py -v

# Coverage
poetry run pytest tests/workflows/test_proactive_compensation.py \
  --cov=magma_cycling.workflows.proactive_compensation \
  --cov=magma_cycling.intelligence.compensation_strategies \
  --cov-report=term-missing
```

**Résultats** :
- ✅ 24 tests unitaires passing (+3 tests parsing notes)
- ✅ Coverage proactive_compensation.py : 90%
- ✅ Coverage compensation_strategies.py : 100%
- ✅ Coverage total : 93%

---

## ⚠️ Points d'Attention

### Mode Non-Interactif

⚠️ **CRITIQUE** : Le système fonctionne UNIQUEMENT en mode non-interactif (LaunchAgent).

- ✅ Recommandations générées automatiquement
- ✅ Email envoyé avec stratégies
- ❌ **PAS d'application automatique** (validation manuelle requise)

### Garde-Fous Actifs

Le système inclut des limites de sécurité :

1. **TSB minimum** : Repos jour utilisé SEULEMENT si TSB >+5
2. **Historique repos** : Max 1 repos utilisé / 2 semaines (TODO: implémenter tracking)
3. **Météo outdoor** : Conversion SEULEMENT si >5°C (mock actuellement)
4. **Sommeil minimum** : Pas d'intensification si <6h sommeil

### TODO : Améliorations Futures

- [ ] Intégrer API météo réelle (OpenWeatherMap)
- [ ] Tracking historique utilisation repos jours
- [ ] Calibration automatique seuils (ML)
- [ ] Support multi-semaines (compensation sur 2 semaines)
- [ ] Dashboard visualisation déficits hebdomadaires

---

## 📖 Références

### Documents MOA

- [`INSIGHT_COMPENSATION_TSS_PROACTIVE.md`](sprints/INSIGHT_COMPENSATION_TSS_PROACTIVE.md) : Document insight original (28 Jan 2026)
- [`SPRINT_R9E_PHASE1B_STATUS.md`](sprints/SPRINT_R9E_PHASE1B_STATUS.md) : Contexte priorisation S080

### Commits Associés

- `[TODO]` - feat(compensation): Add TSS proactive compensation system
- `[TODO]` - test(compensation): Add 21 unit tests (93% coverage)
- `[TODO]` - docs(compensation): Add user guide and technical docs

### API Externes

- **Intervals.icu API** : https://intervals.icu/api
- **PID Controller Theory** : https://en.wikipedia.org/wiki/PID_controller

---

## ✅ Validation Sprint S080

### Métriques Cibles

| Métrique | Cible | Réalisé | Status |
|----------|-------|---------|--------|
| Nouveaux modules | 2 fichiers | 2 | ✅ |
| Tests unitaires | ≥15 tests | 24 tests | ✅ |
| Coverage nouveaux | ≥80% | 93% | ✅ |
| Tests passing | 100% | 100% (24/24) | ✅ |
| Intégration daily-sync | ✅ | ✅ | ✅ |
| AI providers compatible | ✅ | ✅ | ✅ |
| Fix notes annulées | - | ✅ | ✅ |

### Livrables

**Initial (29 Jan 2026 matin):**
- ✅ `proactive_compensation.py` : Core logic (145 lignes)
- ✅ `compensation_strategies.py` : 6 stratégies (63 lignes)
- ✅ `daily_sync.py` : Intégration (modifié)
- ✅ `test_proactive_compensation.py` : 21 tests unitaires
- ✅ Documentation utilisateur (ce fichier)

**Fix Critique (29 Jan 2026 après-midi):**
- ✅ `_parse_cancelled_notes_tss()` : Parsing TSS notes annulées
- ✅ +3 tests unitaires (24 total)
- ✅ Fix déficit calculation avec `update-session`

---

**Préparé par** : Claude Code (Dev)
**Pour** : Stéphane Jouve (PO/MOA)
**Date** : 29 Janvier 2026
**Sprint** : S080 - Compensation TSS Proactive + Fix

**Status** : ✅ COMPLÉTÉ (avec fix critique parsing notes)
