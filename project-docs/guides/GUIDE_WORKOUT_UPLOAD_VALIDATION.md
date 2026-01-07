# Guide : Validation Robuste Upload Workouts

**Date création :** 7 janvier 2026
**Context :** Incident S075-03 - Warmup/Cooldown omis lors upload
**Objectif :** Éviter omissions structurelles lors injection workouts

---

## Incident S075-03 (07/01/2026)

**Problème détecté :**
- Workout S075-03-TEC-CadenceVariation uploadé vers Intervals.icu
- Description texte complète (warmup + main + cooldown)
- `workout_doc.steps` incomplet : **uniquement main set**
- Warmup (10min) et Cooldown (10min) omis dans structure

**Impact :**
- Home trainer n'a pas exécuté warmup/cooldown
- Séance incomplète (40min au lieu de 60min attendues)
- TSS incorrect
- Structure d'entraînement compromise

**Root cause :**
- Upload sans validation complète de la structure
- Pas de vérification duration totale vs description
- Pas de checklist avant push API

---

## Checklist Validation Upload Workout

### 1. Validation Structure Complète

**Avant tout upload, vérifier :**

```python
def validate_workout_structure(workout_doc, expected_duration_min):
    """
    Valide que le workout_doc contient toutes les sections attendues.

    Args:
        workout_doc: Dict structure Intervals.icu
        expected_duration_min: Durée totale attendue (minutes)

    Returns:
        (bool, list[str]) : (is_valid, errors)
    """
    errors = []

    # 1. Vérifier présence steps
    if "steps" not in workout_doc:
        errors.append("❌ Pas de 'steps' dans workout_doc")
        return False, errors

    steps = workout_doc["steps"]

    # 2. Identifier sections par text
    sections_found = {
        "warmup": False,
        "main": False,
        "cooldown": False
    }

    for step in steps:
        text = step.get("text", "").lower()
        if "warmup" in text or "échauffement" in text:
            sections_found["warmup"] = True
        elif "main" in text or "série" in text or "set" in text:
            sections_found["main"] = True
        elif "cooldown" in text or "retour" in text or "récup" in text:
            sections_found["cooldown"] = True

    # 3. Vérifier sections manquantes
    for section, found in sections_found.items():
        if not found:
            errors.append(f"⚠️  Section '{section}' manquante dans steps")

    # 4. Calculer durée totale
    total_duration = calculate_total_duration(steps)
    expected_duration_sec = expected_duration_min * 60

    if abs(total_duration - expected_duration_sec) > 30:  # tolérance 30s
        errors.append(
            f"❌ Durée incohérente: "
            f"{total_duration}s trouvés vs {expected_duration_sec}s attendus"
        )

    # 5. Validation réussie si aucune erreur
    is_valid = len(errors) == 0

    if is_valid:
        print(f"✅ Validation workout: {len(steps)} steps, {total_duration//60}min")
    else:
        print(f"❌ Validation échouée ({len(errors)} erreurs)")
        for error in errors:
            print(f"   {error}")

    return is_valid, errors


def calculate_total_duration(steps):
    """Calcule durée totale récursive avec reps."""
    total = 0
    for step in steps:
        if "duration" in step:
            duration = step["duration"]
        elif "steps" in step:
            # Sous-étapes avec reps
            reps = step.get("reps", 1)
            duration = calculate_total_duration(step["steps"]) * reps
        else:
            duration = 0

        total += duration

    return total
```

### 2. Sections Attendues Standard

**Pour tout workout structuré :**

1. **Warmup (Échauffement)**
   - Durée : 10-15min minimum
   - Progression graduelle (rampes)
   - Cadence modérée (85rpm)

2. **Main Set (Corps de séance)**
   - Peut contenir répétitions (`reps`)
   - Intervalles spécifiques
   - Objectif principal workout

3. **Cooldown (Retour au calme)**
   - Durée : 10-15min minimum
   - Régression graduelle (rampes)
   - Cadence modérée (85rpm)

**Exception :** Workouts très courts (<30min) peuvent omettre sections

### 3. Validation Description vs Structure

**Comparaison texte ↔ workout_doc :**

```python
def cross_validate_description(description, workout_doc):
    """
    Vérifie cohérence entre description texte et structure.
    """
    errors = []

    # Parser description (recherche keywords)
    desc_lower = description.lower()
    has_warmup_text = "warmup" in desc_lower or "échauffement" in desc_lower
    has_cooldown_text = "cooldown" in desc_lower or "retour" in desc_lower

    # Vérifier workout_doc
    steps = workout_doc.get("steps", [])
    has_warmup_step = any("warmup" in s.get("text", "").lower() for s in steps)
    has_cooldown_step = any("cooldown" in s.get("text", "").lower() for s in steps)

    # Cross-validation
    if has_warmup_text and not has_warmup_step:
        errors.append("❌ Warmup mentionné dans description mais absent de steps")

    if has_cooldown_text and not has_cooldown_step:
        errors.append("❌ Cooldown mentionné dans description mais absent de steps")

    return errors
```

### 4. Template Workout Complet

**Exemple structure correcte (S075-03) :**

```json
{
  "workout_doc": {
    "steps": [
      {
        "text": "Warmup",
        "power": {"units": "%ftp", "value": [50, 65]},
        "cadence": {"units": "rpm", "value": 85},
        "duration": 600
      },
      {
        "reps": 5,
        "text": "Main set: 5x",
        "steps": [
          {
            "power": {"units": "%ftp", "value": 65},
            "cadence": {"units": "rpm", "value": 60},
            "duration": 180
          },
          {
            "power": {"units": "%ftp", "value": 65},
            "cadence": {"units": "rpm", "value": 100},
            "duration": 180
          },
          {
            "power": {"units": "%ftp", "value": 65},
            "cadence": {"units": "rpm", "value": 85},
            "duration": 120
          }
        ]
      },
      {
        "text": "Cooldown",
        "power": {"units": "%ftp", "value": [65, 50]},
        "cadence": {"units": "rpm", "value": 85},
        "duration": 600
      }
    ],
    "description": "Technique Cadence (60min, 40 TSS)"
  }
}
```

**Durée totale :** 600 + (180+180+120)*5 + 600 = 3600s = 60min ✅

---

## Workflow Upload Robuste

### Étapes obligatoires

```
1. 📝 Créer workout_doc complet
   ├─ Warmup step(s)
   ├─ Main set step(s)
   └─ Cooldown step(s)

2. ✅ Valider structure
   └─ validate_workout_structure()

3. ✅ Cross-validation description
   └─ cross_validate_description()

4. 📊 Vérifier métriques
   ├─ Durée totale
   ├─ TSS cohérent
   └─ IF/NP raisonnables

5. 🔍 Review visuel
   └─ Afficher steps before upload

6. 🚀 Upload API
   └─ PUT /athlete/{id}/events/{event_id}

7. ✅ Validation post-upload
   └─ GET + vérifier workout_doc reçu
```

### Exemple Implémentation

```python
def upload_workout_safe(event_id, workout_doc, description, expected_duration_min):
    """
    Upload workout avec validation complète.
    """
    print(f"\n🔧 Upload workout {event_id}")
    print(f"   Description: {description}")
    print(f"   Durée attendue: {expected_duration_min}min")

    # 1. Validation structure
    is_valid, errors = validate_workout_structure(workout_doc, expected_duration_min)
    if not is_valid:
        print("❌ Validation échouée - upload annulé")
        return False

    # 2. Cross-validation description
    cross_errors = cross_validate_description(description, workout_doc)
    if cross_errors:
        print("⚠️  Incohérences détectées:")
        for err in cross_errors:
            print(f"   {err}")

        # Demander confirmation user
        confirm = input("\nContinuer malgré les warnings ? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ Upload annulé")
            return False

    # 3. Review visuel
    print("\n📋 Structure à uploader:")
    display_workout_structure(workout_doc)

    # 4. Upload
    print("\n🚀 Upload vers Intervals.icu...")
    response = api_put_workout(event_id, workout_doc)

    if response.status_code != 200:
        print(f"❌ Erreur API: {response.status_code}")
        return False

    # 5. Validation post-upload
    print("✅ Upload réussi - Validation post-upload...")
    uploaded = api_get_workout(event_id)

    is_valid_post, post_errors = validate_workout_structure(
        uploaded["workout_doc"],
        expected_duration_min
    )

    if is_valid_post:
        print("✅ Validation post-upload OK")
        return True
    else:
        print("❌ Validation post-upload échouée!")
        for err in post_errors:
            print(f"   {err}")
        return False


def display_workout_structure(workout_doc):
    """Affiche structure lisible pour review."""
    steps = workout_doc.get("steps", [])
    total_duration = calculate_total_duration(steps)

    print(f"   Total steps: {len(steps)}")
    print(f"   Durée totale: {total_duration//60}min {total_duration%60}s")
    print(f"\n   Steps:")

    for i, step in enumerate(steps, 1):
        text = step.get("text", f"Step {i}")

        if "reps" in step:
            reps = step["reps"]
            sub_duration = calculate_total_duration(step.get("steps", []))
            print(f"   {i}. {text} (x{reps}, {sub_duration}s each)")
        else:
            duration = step.get("duration", 0)
            power = step.get("power", {}).get("value", "?")
            print(f"   {i}. {text} ({duration}s, {power}% FTP)")
```

---

## Checklist Manuelle Pré-Upload

Avant chaque upload, vérifier manuellement :

- [ ] **Description texte complète** (warmup/main/cooldown mentionnés)
- [ ] **workout_doc.steps** contient minimum 3 steps (ou 1 si très court)
- [ ] **Premier step = Warmup** (ramp progressif)
- [ ] **Dernier step = Cooldown** (ramp dégressif)
- [ ] **Durée totale cohérente** avec description
- [ ] **TSS calculé** correspond à intensité prévue
- [ ] **Cadences spécifiées** pour tous les steps
- [ ] **Review visuel** de la structure avant upload
- [ ] **Validation post-upload** systématique

---

## Scripts à Créer

### 1. `validate_workout.py`

```bash
poetry run python scripts/validation/validate_workout.py \
  --event-id 86803817 \
  --check-structure \
  --check-duration \
  --check-description
```

### 2. `upload_workout_safe.py`

```bash
poetry run python scripts/validation/upload_workout_safe.py \
  --event-id 86803817 \
  --workout-file workouts/S075-03.json \
  --dry-run  # test sans upload
```

### 3. Hook pre-upload

Intégrer validation dans workflow :

```bash
# Avant upload
poetry run validate-workout --event-id $EVENT_ID

# Si validation OK → upload
poetry run upload-workout --event-id $EVENT_ID
```

---

## Correction Rétrospective

**Si omission détectée APRÈS entraînement :**

1. **Documenter incident**
   - Workout ID
   - Date
   - Sections manquantes
   - Impact athlète

2. **Correction données**
   - Si possible : corriger workout_doc (historique)
   - Sinon : ajouter note dans event

3. **Ajuster métriques**
   - TSS réel vs prévu
   - Durée réelle
   - IF/NP réels

4. **Learning**
   - Ajouter cas au guide
   - Améliorer validation
   - Tester prévention

---

## Métriques Validation

**Track dans monitoring :**

```json
{
  "date": "2026-01-07",
  "event": "workout_upload_validation",
  "workout_id": "S075-03",
  "validation": {
    "structure_complete": false,
    "missing_sections": ["warmup", "cooldown"],
    "duration_match": false,
    "expected_min": 60,
    "actual_min": 40
  },
  "impact": "high",
  "detected_when": "post_workout"
}
```

---

## Références

**Intervals.icu API :**
- Workout structure: https://intervals.icu/api/
- Steps format: nested with reps support
- Power: %ftp or watts
- Duration: seconds

**Related guides :**
- `GUIDE_WORKOUT_GENERATION.md` (si existe)
- `GUIDE_INTERVALS_API.md` (si existe)
- `GUIDE_MONITORING.md` (validation post-upload)

---

**Prochaines actions suggérées :**

1. Implémenter `validate_workout.py`
2. Intégrer validation dans workflow upload existant
3. Créer tests automatisés validation
4. Documenter cas edge (workouts courts, bricks, etc.)
5. Review tous uploads récents (S075-01, S075-02, S075-03)

---

**Lesson learned :**
> "Un workout incomplet uploadé = entraînement raté. La validation doit être systématique et automatique, pas optionnelle."
