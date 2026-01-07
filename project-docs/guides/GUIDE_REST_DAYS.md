# Guide: Gestion des Jours de Repos dans Intervals.icu

**Version:** 1.0.0
**Date:** 7 janvier 2026
**Sprint:** R6 - PID Baseline & Calibration

---

## 📋 Table des Matières

1. [Problème](#problème)
2. [Bonne Pratique](#bonne-pratique)
3. [Exemples](#exemples)
4. [Impact sur Monitoring](#impact-sur-monitoring)
5. [Correction d'Erreurs](#correction-derreurs)

---

## ❌ Problème

### Symptôme Observé

**Faux positif dans le monitoring d'adherence:**

```bash
🔴 MISSED
Planned: 1 workouts
Skipped: S074-07-REC-ReposComplet
Adherence Rate: 0%
```

### Cause Racine

Un **jour de repos** a été créé comme **WORKOUT** dans Intervals.icu:

```json
{
  "id": 86044991,
  "name": "S074-07-REC-ReposComplet",
  "category": "WORKOUT",  ❌ ERREUR
  "type": "VirtualRide"   ❌ ERREUR
}
```

**Conséquence:**
- Le système pense que c'est un workout à réaliser
- Pas d'activité complétée → détecté comme "sauté"
- Monitoring d'adherence déclenche un faux positif

---

## ✅ Bonne Pratique

### Option 1: Event NOTE (Recommandé)

**Pour un jour de repos complet:**

```json
{
  "category": "NOTE",
  "name": "Repos complet",
  "description": "Journée de récupération complète",
  "start_date_local": "2026-01-11T00:00:00"
}
```

**Avantages:**
- ✅ Visible dans le calendrier Intervals.icu
- ✅ Ne compte pas comme workout à réaliser
- ✅ Pas de faux positif dans le monitoring
- ✅ Traçabilité (description peut expliquer pourquoi)

**Création via API:**

```python
from cyclisme_training_logs.api.intervals_client import IntervalsClient

client = IntervalsClient(athlete_id, api_key)

note_data = {
    "category": "NOTE",
    "name": "Repos complet",
    "description": "Journée de récupération complète - Sprint R6 Phase 1",
    "start_date_local": "2026-01-11T00:00:00",
}

client.create_event(note_data)
```

**Création via Intervals.icu UI:**

1. Ouvrir Calendar
2. Cliquer sur le jour de repos
3. "Add event" → Type: **Note**
4. Title: "Repos complet"
5. Save

### Option 2: Pas d'Event (Alternative)

**Laisser le jour vide** = repos implicite

**Avantages:**
- ✅ Simple
- ✅ Pas de faux positif

**Inconvénients:**
- ❌ Moins explicite
- ❌ Pas de traçabilité

### Option 3: Event REST (Pour Repos Actif)

**Pour repos actif (stretching, yoga, marche légère):**

```json
{
  "category": "REST",
  "type": "Rest",
  "name": "Repos actif - Stretching",
  "description": "30min stretching + mobilité",
  "start_date_local": "2026-01-11T00:00:00"
}
```

**Usage:**
- Repos actif avec activité légère
- Distinction claire vs repos complet
- Toujours pas compté comme workout à réaliser

---

## ⚠️ À Éviter Absolument

### ❌ Créer un WORKOUT pour un Repos

```json
{
  "category": "WORKOUT",  ❌ MAUVAIS
  "type": "VirtualRide",  ❌ MAUVAIS
  "name": "S074-07-REC-ReposComplet"
}
```

**Problèmes:**
1. Système pense que c'est un workout à compléter
2. Monitoring détecte un workout "sauté"
3. Faux positif dans adherence tracking
4. Données Sprint R6 baseline polluées

### ❌ Utiliser des Acronymes Trompeurs

```
S074-07-REC-ReposComplet  ❌ Contient "REC" mais reste WORKOUT
S075-07-REPOS-Dimanche    ❌ Contient "REPOS" mais reste WORKOUT
```

**Note:** Le système de monitoring filtre maintenant `REC`/`REPOS`/`RECOVERY`/`REST` dans les noms, mais **c'est un band-aid**. La vraie solution est d'utiliser la bonne catégorie.

---

## 📊 Exemples

**Note:** Les semaines commencent le **LUNDI**
- S075 = Lundi 5 jan → Dimanche 11 jan
- S076 = Lundi 12 jan → Dimanche 18 jan

### Exemple 1: Semaine Normale avec Repos Dimanche

```python
# Lundi-Samedi : WORKOUT events
workouts = [
    {"category": "WORKOUT", "name": "S075-01-END-Endurance", "date": "2026-01-05"},
    {"category": "WORKOUT", "name": "S075-02-INT-SweetSpot", "date": "2026-01-06"},
    # ... S075-03 à S075-06
]

# Dimanche : NOTE (repos)
repos = {
    "category": "NOTE",
    "name": "Repos complet",
    "description": "Récupération post-semaine intensive",
    "date": "2026-01-11"
}
```

### Exemple 2: Semaine avec Repos Actif Mercredi

```python
# Lun-Mar : WORKOUT
# Mercredi : REST (repos actif)
repos_actif = {
    "category": "REST",
    "type": "Rest",
    "name": "Repos actif - Yoga",
    "description": "60min yoga + stretching",
    "date": "2026-01-08"
}
# Jeu-Sam : WORKOUT
# Dimanche : NOTE (repos complet)
```

### Exemple 3: Week-end Longue Sortie + Repos

```python
# Samedi : Sortie longue
sortie = {
    "category": "WORKOUT",
    "name": "S075-06-END-EnduranceLongue",
    "tss": 120,
    "date": "2026-01-11"
}

# Dimanche : Repos complet (récupération)
repos = {
    "category": "NOTE",
    "name": "Repos complet",
    "description": "Récupération post-sortie longue 120 TSS",
    "date": "2026-01-11"
}
```

---

## 🔍 Impact sur Monitoring

### Monitoring d'Adherence (launchd)

**Script:** `scripts/monitoring/check_workout_adherence.py`

**Filtres appliqués:**

```python
# Exclusions automatiques
planned_workouts = [
    e for e in events
    if e.get("category") == "WORKOUT"
    and not e.get("name", "").startswith("[")  # [ANNULÉE], [SAUTÉE]
    and "REC" not in e.get("name", "").upper()
    and "REPOS" not in e.get("name", "").upper()
    and "RECOVERY" not in e.get("name", "").upper()
    and "REST" not in e.get("name", "").upper()
]
```

**Comportement:**

| Event Type | Name | Monitoring Result |
|------------|------|-------------------|
| `NOTE` | "Repos complet" | ✅ Exclu (correct) |
| `REST` | "Repos actif" | ✅ Exclu (correct) |
| `WORKOUT` avec "REC" | "S074-07-REC-Repos" | ✅ Exclu (band-aid) |
| `WORKOUT` sans "REC" | "S074-07-Dimanche" | ❌ Inclus → Faux positif |

**Meilleure pratique:** Utiliser `NOTE` ou `REST` (pas de band-aid nécessaire)

---

## 🛠️ Correction d'Erreurs

### Si Vous Avez Déjà Créé un WORKOUT pour un Repos

**Étape 1: Identifier l'Event**

```bash
cd ~/cyclisme-training-logs

python3 << 'PYEOF'
from cyclisme_training_logs.api.intervals_client import IntervalsClient
from cyclisme_training_logs.config import get_intervals_config

config = get_intervals_config()
client = IntervalsClient(config.athlete_id, config.api_key)

# Trouver les faux workouts de repos
events = client.get_events(oldest='2026-01-01', newest='2026-01-31')

print("Faux workouts de repos détectés:\n")
for e in events:
    name = e.get('name', '')
    if e.get('category') == 'WORKOUT' and any(
        keyword in name.upper() for keyword in ['REC', 'REPOS', 'REST', 'RECOVERY']
    ):
        print(f"- ID: {e['id']}")
        print(f"  Name: {name}")
        print(f"  Date: {e.get('start_date_local', '')[:10]}")
        print()
PYEOF
```

**Étape 2: Supprimer le Faux WORKOUT**

```python
# Supprimer l'event incorrect
client.delete_event(86044991)  # Remplacer par l'ID trouvé
```

**Étape 3: Créer un NOTE Correct**

```python
# Créer le repos correct
note_data = {
    "category": "NOTE",
    "name": "Repos complet",
    "description": "Journée de récupération complète",
    "start_date_local": "2026-01-04T00:00:00",
}
client.create_event(note_data)
```

**Étape 4: Vérifier**

```bash
poetry run python scripts/monitoring/check_workout_adherence.py --date 2026-01-04 --dry-run
```

**Résultat attendu:**

```
✅ COMPLETE
Planned: 0 workouts
Adherence Rate: 100%
```

---

## 📋 Checklist Création Repos

Avant de créer un jour de repos, vérifier:

- [ ] **Category = NOTE** (ou REST pour repos actif)
- [ ] **PAS Category = WORKOUT**
- [ ] Name explicite ("Repos complet", "Repos actif", etc.)
- [ ] Description optionnelle (contexte, raison)
- [ ] Date correcte

**Template rapide:**

```python
repos_note = {
    "category": "NOTE",
    "name": "Repos complet",
    "description": f"Récupération complète - {raison}",
    "start_date_local": f"{date}T00:00:00",
}
```

---

## 🎯 Sprint R6 Context

**Phase 1-2 Observation/Calibration (S075-S080):**

Les jours de repos doivent être **correctement identifiés** car:

1. **Baseline data collection** : Seuls les vrais workouts comptent
2. **PID calibration** : Adhérence = ratio workouts complétés / workouts planifiés
3. **Faux positifs polluent les données** : Repo détecté comme "sauté" fausse l'adherence

**Importance:**
- Adherence rate précis → calibration PID fiable
- Repos bien identifiés → pas de pollution données
- Monitoring fonctionnel → feedback Sprint R6 valide

---

## 📚 Références

### Scripts Connexes

- `scripts/monitoring/check_workout_adherence.py` - Monitoring adherence
- `cyclisme_training_logs/api/intervals_client.py` - API Intervals.icu

### Documentation

- [GUIDE_MONITORING.md](GUIDE_MONITORING.md) - Monitoring adherence complet
- [Intervals.icu API Docs](https://intervals.icu/api) - Documentation officielle

### Commits

- `0a7a3db` - Exclusion rest days from monitoring (band-aid)
- `[current]` - Fix rest day events + documentation

---

## 🔧 Maintenance

**Si vous modifiez les filtres de monitoring:**

Mettre à jour:
1. `scripts/monitoring/check_workout_adherence.py` (filtres)
2. Ce guide (section "Impact sur Monitoring")
3. Tests unitaires si ajoutés

---

**Document créé par:** Claude Code
**Date:** 2026-01-07
**Version:** 1.0.0
**Sprint:** R6 - PID Baseline & Calibration
