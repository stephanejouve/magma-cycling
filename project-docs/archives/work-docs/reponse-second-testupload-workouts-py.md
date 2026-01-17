stephanejouve@Tiresias cyclisme-training-logs % python3 scripts/upload_workouts.py S069 --start-date 2025-11-24
✅ API Intervals.icu connectée

📋 Lecture presse-papier...
  ✅ Jour 01 (24/11) : S069-01-TYPE-NomExercice-V001
  ✅ Jour 01 (24/11) : ... ===` et `=== FIN WORKOUT ===`
- Directement copiable dans Intervals.icu Workout Builder

### Convention de Nommage

- **Format** : `SSSS-JJ-TYPE-NomExercice-V001`
- **SSSS** : S069
- **JJ** : 01 à 07 (lundi à dimanche)
- **TYPE** : END, INT, FTP, REC, FOR, CAD, TEC, MIX, TST
- **NomExercice** : CamelCase sans accents (ex: EnduranceBase, SweetSpotProgressif)

### Types d'Entraînements (CODE)

- **END** : Endurance (Z2, base aérobie)
- **INT** : Intervalles (Sweet-Spot, Seuil, VO2)
- **FTP** : Test FTP ou séance FTP spécifique
- **REC** : Récupération active
- **FOR** : Force (cadence basse, couple élevé)
- **CAD** : Technique cadence (variations RPM)
- **TEC** : Technique générale
- **MIX** : Mixte (plusieurs types dans la séance)
- **TST** : Test (VO2 max, sprint, etc.)

### Contraintes Obligatoires

1. **Dimanche = REPOS OBLIGATOIRE** (aucune séance)
2. **TSB Management** :
   - Si TSB actuel < +5 : Pas de VO2 max
   - Si TSB < 0 : Prioriser récupération/endurance
   - Si TSB > +10 : Possibilité intensité élevée
3. **Progression CTL** : +3 à +4 points/semaine maximum
4. **Indoor-only** : Toutes séances indoor (Zwift/TrainingPeaks Virtual)
5. **Hydratation** : Spécifier protocole si séance >75min
6. **Mercredi allégé** : Séance technique ou récupération privilégiée

### Structure Type par Jour

- **Lundi** : Endurance Z2 ou Technique
- **Mardi** : Sweet-Spot ou Intervalles modérés
- **Mercredi** : Technique/Cadence ou Récupération
- **Jeudi** : Endurance progressive ou Force
- **Vendredi** : Activation ou Sweet-Spot léger
- **Samedi** : Volume (endurance longue) ou Intensité haute si TSB favorable
- **Dimanche** : **REPOS COMPLET**

### Règles Intensité

1. **Z2 (Endurance)** : 60-75% FTP
   - Durée : 45-90min
   - Cadence : 85-90 rpm naturelle

2. **Sweet-Spot** : 88-93% FTP
   - Blocs : 8-12min maximum
   - Récupération : 50% de la durée bloc
   - Maximum 3-4 blocs par séance

3. **Seuil** : 95-105% FTP
   - Blocs : 5-8min maximum
   - Récupération : durée bloc minimum
   - Précédé de validation TSB

4. **VO2 Max** : 106-120% FTP
   - **UNIQUEMENT si TSB ≥ +5**
   - Blocs : 3-5min
   - Ratio travail/repos : 1:1 minimum
   - Maximum 20min cumulés haute intensité

### Checklist VO2 Max (5 critères)

Si tu proposes une séance VO2 max, vérifie :
1. ✅ TSB actuel ≥ +5
2. ✅ Pas d'intensité >85% FTP dans les 48h précédentes
3. ✅ Placé mardi ou jeudi (milieu de semaine)
4. ✅ Séance récupération le lendemain
5. ✅ CTL progression raisonnable (+3-4 max)

### Validation Technique

Pour chaque séance, spécifie :
- **Découplage cardiaque attendu** : <7.5% optimal
- **RPE estimé** : Échelle 1-10
- **Focus technique** : Cadence, position, transitions
- **Hydratation** : 500ml/h standard, 600ml/h si >75min ou >88% FTP

### Documentation par Séance

```markdown
### WORKOUT: S069-0X-TYPE-NomExercice-V001

**Objectif** : [Objectif physiologique]
**TSS** : [valeur]
**Durée** : [minutes]
**IF** : [Intensity Factor]

[Structure Intervals.icu]

**Points clés** :
- [Consigne technique 1]
- [Consigne technique 2]
- [Hydratation si nécessaire]

**Placement semaine** : [Justification]
```

---

## Format Intervals.icu - Rappel

Utilise la syntaxe Intervals.icu standard :

```
Warmup
- 10m 50-65% 85rpm

Main set
- 8m 90% 90rpm
- 3m 65% 85rpm

Cooldown
- 10m 65-50% 85rpm
```

**Syntaxe** :
- Durée : `10m`, `30s`, `1h`
- Intensité : `90%` (% FTP) ou `100-140w` (watts absolus)
- Cadence : `85rpm` ou `80-90rpm` (plage)
- Répétitions : Préfixer bloc avec `3x` si répétitions

---

## Livrables Attendus

Génère **7 blocs WORKOUT** (un par jour, dimanche = mention repos) au format texte pur Intervals.icu.

**Exemple de format attendu** :

```
=== WORKOUT S069-01-END-EnduranceBase-V001
  ✅ Jour 02 (25/11) : S069-02-INT-SweetSpot-V001

📊 Total : 3 workout(s) dans le presse-papier

⚠️  ATTENTION : Upload RÉEL sur Intervals.icu
   3 workout(s) seront créés pour S069

Continuer ? (o/n) : o

======================================================================
📤 UPLOAD WORKOUTS VERS INTERVALS.ICU
Semaine : S069
Période : 24/11/2025 → 30/11/2025
Mode : RÉEL
======================================================================

📅 Jour 01 - 2025-11-24
   S069-01-TYPE-NomExercice-V001
❌ Erreur HTTP : 422 Client Error: Unprocessable Entity for url: https://intervals.icu/api/v1/athlete/i151223/events
   Détail : {'status': 422, 'error': 'type is required for category WORKOUT'}
   Données envoyées : {'category': 'WORKOUT', 'name': '[Nom séance] ([durée]min, [TSS] TSS)', 'description': '[Nom séance] ([durée]min, [TSS] TSS)\n\nWarmup\n- [durée] [intensité%] [cadence]rpm\n\nMain set\n- [structure]\n\nCooldown  \n- [durée] [intensité%] [cadence]rpm', 'start_date_local': '2025-11-24'}
  ❌ Échec : [Nom séance] ([durée]min, [TSS] TSS)

📅 Jour 01 - 2025-11-24
   ... ===` et `=== FIN WORKOUT ===`
- Directement copiable dans Intervals.icu Workout Builder

### Convention de Nommage

- **Format** : `SSSS-JJ-TYPE-NomExercice-V001`
- **SSSS** : S069
- **JJ** : 01 à 07 (lundi à dimanche)
- **TYPE** : END, INT, FTP, REC, FOR, CAD, TEC, MIX, TST
- **NomExercice** : CamelCase sans accents (ex: EnduranceBase, SweetSpotProgressif)

### Types d'Entraînements (CODE)

- **END** : Endurance (Z2, base aérobie)
- **INT** : Intervalles (Sweet-Spot, Seuil, VO2)
- **FTP** : Test FTP ou séance FTP spécifique
- **REC** : Récupération active
- **FOR** : Force (cadence basse, couple élevé)
- **CAD** : Technique cadence (variations RPM)
- **TEC** : Technique générale
- **MIX** : Mixte (plusieurs types dans la séance)
- **TST** : Test (VO2 max, sprint, etc.)

### Contraintes Obligatoires

1. **Dimanche = REPOS OBLIGATOIRE** (aucune séance)
2. **TSB Management** :
   - Si TSB actuel < +5 : Pas de VO2 max
   - Si TSB < 0 : Prioriser récupération/endurance
   - Si TSB > +10 : Possibilité intensité élevée
3. **Progression CTL** : +3 à +4 points/semaine maximum
4. **Indoor-only** : Toutes séances indoor (Zwift/TrainingPeaks Virtual)
5. **Hydratation** : Spécifier protocole si séance >75min
6. **Mercredi allégé** : Séance technique ou récupération privilégiée

### Structure Type par Jour

- **Lundi** : Endurance Z2 ou Technique
- **Mardi** : Sweet-Spot ou Intervalles modérés
- **Mercredi** : Technique/Cadence ou Récupération
- **Jeudi** : Endurance progressive ou Force
- **Vendredi** : Activation ou Sweet-Spot léger
- **Samedi** : Volume (endurance longue) ou Intensité haute si TSB favorable
- **Dimanche** : **REPOS COMPLET**

### Règles Intensité

1. **Z2 (Endurance)** : 60-75% FTP
   - Durée : 45-90min
   - Cadence : 85-90 rpm naturelle

2. **Sweet-Spot** : 88-93% FTP
   - Blocs : 8-12min maximum
   - Récupération : 50% de la durée bloc
   - Maximum 3-4 blocs par séance

3. **Seuil** : 95-105% FTP
   - Blocs : 5-8min maximum
   - Récupération : durée bloc minimum
   - Précédé de validation TSB

4. **VO2 Max** : 106-120% FTP
   - **UNIQUEMENT si TSB ≥ +5**
   - Blocs : 3-5min
   - Ratio travail/repos : 1:1 minimum
   - Maximum 20min cumulés haute intensité

### Checklist VO2 Max (5 critères)

Si tu proposes une séance VO2 max, vérifie :
1. ✅ TSB actuel ≥ +5
2. ✅ Pas d'intensité >85% FTP dans les 48h précédentes
3. ✅ Placé mardi ou jeudi (milieu de semaine)
4. ✅ Séance récupération le lendemain
5. ✅ CTL progression raisonnable (+3-4 max)

### Validation Technique

Pour chaque séance, spécifie :
- **Découplage cardiaque attendu** : <7.5% optimal
- **RPE estimé** : Échelle 1-10
- **Focus technique** : Cadence, position, transitions
- **Hydratation** : 500ml/h standard, 600ml/h si >75min ou >88% FTP

### Documentation par Séance

```markdown
### WORKOUT: S069-0X-TYPE-NomExercice-V001

**Objectif** : [Objectif physiologique]
**TSS** : [valeur]
**Durée** : [minutes]
**IF** : [Intensity Factor]

[Structure Intervals.icu]

**Points clés** :
- [Consigne technique 1]
- [Consigne technique 2]
- [Hydratation si nécessaire]

**Placement semaine** : [Justification]
```

---

## Format Intervals.icu - Rappel

Utilise la syntaxe Intervals.icu standard :

```
Warmup
- 10m 50-65% 85rpm

Main set
- 8m 90% 90rpm
- 3m 65% 85rpm

Cooldown
- 10m 65-50% 85rpm
```

**Syntaxe** :
- Durée : `10m`, `30s`, `1h`
- Intensité : `90%` (% FTP) ou `100-140w` (watts absolus)
- Cadence : `85rpm` ou `80-90rpm` (plage)
- Répétitions : Préfixer bloc avec `3x` si répétitions

---

## Livrables Attendus

Génère **7 blocs WORKOUT** (un par jour, dimanche = mention repos) au format texte pur Intervals.icu.

**Exemple de format attendu** :

```
=== WORKOUT S069-01-END-EnduranceBase-V001
  ⏭️  Ignoré (jour de repos)

📅 Jour 02 - 2025-11-25
   S069-02-INT-SweetSpot-V001
❌ Erreur HTTP : 422 Client Error: Unprocessable Entity for url: https://intervals.icu/api/v1/athlete/i151223/events
   Détail : {'status': 422, 'error': 'type is required for category WORKOUT'}
   Données envoyées : {'category': 'WORKOUT', 'name': 'Sweet Spot 3x10 (74min, 78 TSS)', 'description': 'Sweet Spot 3x10 (74min, 78 TSS)\n\nWarmup\n- 12m ramp 50-65% 85rpm\n- 5m 65% 90rpm\n\nMain set 3x\n- 10m 90% 92rpm\n- 4m 62% 85rpm\n\nCooldown\n- 10m ramp 65-50% 85rpm', 'start_date_local': '2025-11-25'}
  ❌ Échec : Sweet Spot 3x10 (74min, 78 TSS)

======================================================================
📊 RÉSUMÉ
======================================================================
✅ Succès   : 0
❌ Échecs   : 2
⏭️  Ignorés  : 1
📝 Total    : 3
======================================================================
stephanejouve@Tiresias cyclisme-training-logs %
