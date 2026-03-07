# Addendum au design doc Withings BP — Champs wellness supplémentaires

**Contexte** : En complément de la Phase 1-5 (tension artérielle), 4 champs supplémentaires à pousser vers Intervals.icu wellness.

---

## Champ 1 — `restingHR` (FC repos)

**Source** : Données sleep Withings déjà collectées (`hr_min` dans le résultat `get_sleep`)

**Destination** : Intervals.icu wellness field natif `restingHR`

**Fichier à modifier** : `magma_cycling/_mcp/handlers/withings.py`

**Modification** : Dans la section sync sleep existante, ajouter `restingHR` au dict wellness poussé vers Intervals.icu :

```python
# Dans la boucle de sync sleep, après construction du wellness dict
if sleep_data.hr_min:
    wellness["restingHR"] = sleep_data.hr_min
```

**Aucun nouveau model nécessaire** — la donnée existe déjà dans `SleepMeasurement.hr_min`.

**Aucun nouveau tool MCP nécessaire** — s'intègre au sync existant.

---

## Champs 2-4 — `muscleMass`, `boneMass`, `bodyWater` (composition corporelle)

**Source** : Données pesée Withings déjà collectées via `get_measurements()`. Types API Withings :

| Type Withings | Champ          | Unité |
|---------------|----------------|-------|
| 76            | `muscleMass`   | kg    |
| 88            | `boneMass`     | kg    |
| 77            | `bodyWater`    | kg    |

**Destination** : Intervals.icu **custom wellness fields** (à créer manuellement dans Settings → Wellness Fields)

**Configuration requise dans Intervals.icu** (une seule fois, manuellement) :

| Field Name   | Type  | Unit |
|--------------|-------|------|
| `muscleMass` | float | kg   |
| `boneMass`   | float | kg   |
| `bodyWater`  | float | kg   |

### Fichiers à modifier

**1. `magma_cycling/api/withings_client.py`** — `get_measurements()`

Ajouter le parsing des types 76, 77, 88 dans la méthode existante (s'ils ne sont pas déjà extraits) :

```python
# Types à parser en plus de weight (1) et fat (6/8)
# 76 → muscle_mass_kg
# 77 → body_water_kg  (valeur brute / 100 si en %)
# 88 → bone_mass_kg
```

**2. `magma_cycling/models/withings_models.py`** — `BodyMeasurement`

Ajouter les champs optionnels au model existant :

```python
class BodyMeasurement(BaseModel):
    # ... champs existants (weight, fat_ratio, fat_mass, etc.)
    muscle_mass_kg: float | None = Field(default=None, description="Muscle mass (kg)")
    bone_mass_kg: float | None = Field(default=None, description="Bone mass (kg)")
    body_water_kg: float | None = Field(default=None, description="Body water (kg)")
```

**3. `magma_cycling/_mcp/handlers/withings.py`** — sync weight handler

Dans la section sync weight, ajouter au dict wellness :

```python
# Après les champs weight et bodyFat existants
if body_data.muscle_mass_kg:
    wellness["muscleMass"] = body_data.muscle_mass_kg
if body_data.bone_mass_kg:
    wellness["boneMass"] = body_data.bone_mass_kg
if body_data.body_water_kg:
    wellness["bodyWater"] = body_data.body_water_kg
```

---

## Résumé des modifications par fichier

| Fichier | Modifications |
|---------|---------------|
| `withings_client.py` | Parser types 76, 77, 88 dans `get_measurements()` |
| `withings_models.py` | Ajouter `muscle_mass_kg`, `bone_mass_kg`, `body_water_kg` à `BodyMeasurement` |
| `handlers/withings.py` | Pousser `restingHR` dans sync sleep + `muscleMass`, `boneMass`, `bodyWater` dans sync weight |

**Aucun nouveau fichier à créer** — tout s'intègre dans l'existant.

**Prérequis** : Créer les 3 custom wellness fields dans Intervals.icu avant de lancer le sync.

---

## Ordre d'implémentation suggéré

1. `restingHR` — modification triviale, 0 risque (champ natif Intervals)
2. Extend `BodyMeasurement` model + parser `withings_client.py`
3. Créer les custom fields dans Intervals.icu
4. Ajouter les 3 champs au sync weight handler
5. Tests : `poetry run pytest tests/ -x`
6. Test réel : `withings-sync-to-intervals` avec `data_types: ["all"]`
