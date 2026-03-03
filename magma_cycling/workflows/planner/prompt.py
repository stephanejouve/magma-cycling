"""Prompt generation methods for WeeklyPlanner."""

import json
import sys


class PromptMixin:
    """Full planning prompt assembly."""

    def generate_planning_prompt(self) -> str:
        """Generate le prompt complet pour l'assistant IA."""
        print("\n✍️ Génération du prompt de planification...", file=sys.stderr)

        next_week = self._next_week_number()
        date_start_str = self.start_date.strftime("%d/%m/%Y")
        date_end_str = self.end_date.strftime("%d/%m/%Y")

        # Load periodization context and previous week workouts
        periodization_context = self.load_periodization_context()
        previous_week_workouts = self.load_previous_week_workouts()

        # Load mesocycle enriched context (every 6 weeks)
        mesocycle_context = self._load_mesocycle_context()

        prompt = f"""# Planification Hebdomadaire Cyclisme - {self.week_number}.

## Contexte Athlète

{self.context_files.get('project_prompt', '[Project prompt non chargé]')}

---

## Période à Planifier

- **Semaine** : {self.week_number}
- **Dates** : {date_start_str} → {date_end_str} (7 jours)
- **Semaine suivante** : {next_week}

---

## État Actuel

### Métriques Actuelles
```json
{json.dumps(self.current_metrics, indent=2, ensure_ascii=False)}
```

### Bilan Semaine Précédente ({self._previous_week_number()})

{self.previous_week_bilan}

{previous_week_workouts}

---
"""
        # Add periodization context if available
        if periodization_context:
            pc = periodization_context
            prompt += f"""
## 🎯 Contexte Périodisation (Stratégie Macro-Cycle)

### Phase Actuelle : {pc['phase']}

**Objectifs Cycle** :
- CTL actuel : {pc['ctl_current']:.1f}
- CTL cible : {pc['ctl_target']:.0f}
- Déficit CTL : {pc['ctl_deficit']:.1f} points
- FTP actuel : {pc['ftp_current']}W
- FTP cible : {pc['ftp_target']}W

**Progression** :
- Durée reconstruction estimée : {pc['weeks_to_target']} semaines
- TSS semaines charge : {pc['weekly_tss_load']} TSS
- TSS semaines récupération : {pc['weekly_tss_recovery']} TSS
- Fréquence récupération : Tous les {pc['recovery_week_frequency']} semaines

**Distribution Intensité Recommandée pour Phase {pc['phase']}** :
"""
            for zone, percentage in pc["intensity_distribution"].items():
                focus_marker = " ← **FOCUS**" if percentage >= 0.20 else ""
                prompt += f"- **{zone}** : {percentage * 100:.0f}%{focus_marker}\n"

            prompt += f"""
**État PID Controller** : {pc['pid_status']}

**Rationale Phase** :
{pc['rationale']}

**➡️ CRITIQUE pour Planification** : Les workouts de la semaine {self.week_number} doivent être alignés avec la phase {pc['phase']}. Respecter la distribution intensité recommandée ci-dessus et l'objectif TSS hebdomadaire ({pc['weekly_tss_load']} TSS semaine charge, {pc['weekly_tss_recovery']} TSS semaine récup).

---
"""

        # Add mesocycle enriched context if available (every 6 weeks)
        if mesocycle_context:
            prompt += mesocycle_context
            prompt += "\n---\n"

        prompt += """
## MÉTHODOLOGIE PEAKS COACHING (HUNTER ALLEN) - PRINCIPES OBLIGATOIRES

### Distribution Intensité Hebdomadaire (Méthode Traditionnelle)
**PRIORITAIRE pour Masters 50+ avec budget 8-12h/semaine :**
- **Récupération** : 10% TSS total
- **Endurance (56-75% FTP)** : 25%
- **Tempo (76-91% FTP)** : 35% ← **ZONE PRINCIPALE**
- **Sweet-Spot (88-93% FTP)** : Inclus dans Tempo, **PRIORISER en phase reconstruction CTL**
- **FTP (94-105%)** : 15%
- **VO2 max (106-120%)** : 10%
- **Anaérobie + Neuro (>120%)** : 5%

**Rationale** : Méthode Traditionnelle > Polarisée pour Masters 50+. Polarisée = psychologiquement insoutenable long terme (ennui Z1-Z2 + souffrance constante VO2/AC), taux abandon élevé.

---

## PRÉFÉRENCES PLANNING ATHLÈTE (PRIORITAIRE)

{self.context_files.get('planning_preferences', '[Préférences non chargées]')}

---

### Sweet-Spot : Zone Optimale FTP
**"Biggest bang for your training buck"** - Hunter Allen
- **88-93% FTP** (chevauche haut Tempo + bas FTP)
- Plus haut effet entraînement pour améliorer FTP avec sustainability psychologique
- Formats : 2x20min, 3x15min, 4x12min, continu 40-60min
- Découplage <7.5% = validation qualité

### Gestion CTL Masters 50+
**Citation Hunter Allen** : *"When you are 60 years young and your CTL drops from 80 down to 50, it's a long fight for months to get it back to 80!"*

**Règles Critiques** :
- **Maintenir CTL à 90% du maximum** en permanence (éviter variations >15 points)
- **CTL cible selon FTP** :
  - FTP 220W → CTL minimum 55-65
  - FTP 240W → CTL minimum 65-75
  - FTP 260W → CTL minimum 70-80
- **Alerte si drop >10 points en 4 semaines** (récupération lente âge 50+)
- **Progression CTL** : +2 à +3 points/semaine soutenable (max +4)
- **Semaines récup** : Tous les 3 semaines MAXIMUM (Masters 50+), jamais >3 semaines charge consécutives

### Volume TSS Recommandé
- **Semaines charge** : 350-400 TSS
- **Semaines récup** : 250-280 TSS
- **Ratio** : 3:1 (3 charge, 1 récup) ou 2:1 si fatigue accumulée

### Tests & Power Profiling
**"Testing is training and training is testing"** - Dr. Andrew Coggan
- **Ne JAMAIS bloquer semaine entière tests uniquement**
- Tests multiples même journée = OK (ordre : 5s → 1min → 5min → 20min)
- Pré-requis : TSB +10 minimum, sommeil >7h, fraîcheur optimale
- Fréquence : Tous les 8 semaines (comme FTP)

### Adaptation Physiologique
**Délai effet mesurable : 6-8 semaines**
- Cycle minimum = 6 semaines même stimulus
- Test FTP après 6-8 semaines stimulation appropriée
- Ne pas changer méthode avant 6 semaines (attendre délai adaptation)

### Éviter "Junk Miles"
**Junk Miles = Volume sans objectif structuré**
- TOUTE séance doit avoir zone(s) cible précise(s)
- Pas de "sortie libre" ou "selon envie" sauf semaine récup totale
- Si outdoor = >2 échecs discipline IF, basculer indoor cette zone

---

## Concepts d'Entraînement

{self.context_files.get('cycling_concepts', '[Concepts non chargés]')}

---

## Protocoles Validés

{self.context_files.get('protocols', '[Protocoles non chargés]')}

---

## 🧠 Intelligence AI & Adaptations Recommandées

**IMPORTANT:** Les adaptations ci-dessous proviennent du système PID (Planification Intelligente Dynamique) qui analyse l'évolution de l'athlète. Ces recommandations doivent être **prioritaires** dans la planification.

```json
{self.context_files.get('intelligence', '[Aucune recommandation disponible]')}
```

**Instructions CRITIQUES pour Test FTP:**

Si une adaptation recommande un test FTP avec affûtage, suivre ce timing précis:

1. **Semaine ACTUELLE ({self.week_number})**:
   - Continuer entraînement normal ou légère réduction volume
   - Ne PAS faire le test cette semaine
   - Ne PAS faire l'affûtage cette semaine

2. **Semaine SUIVANTE ({self._next_week_number()})**:
   - Semaine d'affûtage: réduction -40% TSS
   - Exemple: si CTL ~45, viser ~230 TSS total
   - Focus: endurance douce, récupération, fraîcheur

3. **Semaine APRÈS ({self._week_after_next()})**:
   - Test FTP samedi (jour 6)
   - Repos dimanche
   - TSB optimal pour test: +5 à +15

**Autres adaptations:**
- Analyser "evidence" pour contexte (dernier test, TSB, adhérence)
- Prioriser adaptations status="PROPOSED" + confidence="high"

---

## 🚨 RÉPÉTITIONS - RÈGLE CRITIQUE (À LIRE EN PREMIER)

**⚠️ ERREUR FRÉQUENTE À ÉVITER ABSOLUMENT** : Le placement du multiplicateur de répétition.

### ✅ FORMAT CORRECT (UNIQUE FORMAT ACCEPTÉ)

Le multiplicateur (2x, 3x, 4x, 5x...) doit TOUJOURS être placé **sur la ligne du titre de section**, jamais ailleurs.

**Structure obligatoire** :
```
[Nom section] [multiplicateur]x
- [intervalle 1]
- [intervalle 2]
- [intervalle N]
```

### 📋 Exemples Corrects Multiples

**Exemple 1 - Sweet Spot 3x10min** :
```
Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm
```
Résultat : 3 répétitions du bloc complet (10m effort + 4m récup) = 42min total

**Exemple 2 - VO2 max 5x3min** :
```
Main set 5x
- 3m 110% 95rpm
- 3m 55% 85rpm
```
Résultat : 5 répétitions du bloc = 30min total

**Exemple 3 - Seuil 4x8min** :
```
Main set 4x
- 8m 98% 90rpm
- 4m 60% 85rpm
```
Résultat : 4 répétitions du bloc = 48min total

**Exemple 4 - Pyramide 2x (structure complexe)** :
```
Main set 2x
- 3m 95% 92rpm
- 2m 65% 85rpm
- 5m 98% 90rpm
- 3m 65% 85rpm
- 3m 95% 92rpm
- 2m 65% 85rpm
```
Résultat : 2 répétitions de toute la pyramide = 36min total

### ❌ FORMATS INCORRECTS (NE JAMAIS FAIRE)

**ERREUR #1 - Multiplicateur dans la ligne d'intervalle** :
```
Main set
- 3x 10m 90%      ← ❌ FAUX - Intervals.icu ne comprendra pas
- 4m 62%
```
**Ce qui se passera** : Intervals.icu créera 1 seul intervalle bizarre ou erreur de parsing.

**ERREUR #2 - Section non standard avec multiplicateur** :
```
Test capacité 3x   ← ❌ FAUX - "Test capacité" n'est pas une section Intervals.icu
- 5m 70%
```
**Correction** : Utiliser `Main set 3x` ou `Intervals 3x`

**ERREUR #3 - Multiplicateur seul sur une ligne** :
```
Main set
3x                 ← ❌ FAUX - Le 3x doit être sur la même ligne que "Main set"
- 10m 90%
- 4m 62%
```

**ERREUR #4 - Format "répéter X fois"** :
```
Main set (répéter 3 fois)  ← ❌ FAUX - Intervals.icu ne comprend que "3x"
- 10m 90%
```

### 📊 Tableau Comparatif

| ❌ INCORRECT | ✅ CORRECT |
|-------------|-----------|
| `Main set`<br>`- 3x 10m 90%` | `Main set 3x`<br>`- 10m 90%` |
| `Test 4x`<br>`- 5m 95%` | `Main set 4x`<br>`- 5m 95%` |
| `Main set`<br>`3x`<br>`- 8m 88%` | `Main set 3x`<br>`- 8m 88%` |
| `Intervals (x3)`<br>`- 5m 110%` | `Intervals 3x`<br>`- 5m 110%` |

### 🎯 Sections Valides pour Répétitions

Seules ces sections sont reconnues par Intervals.icu :
- `Main set 3x` ✅
- `Intervals 4x` ✅
- `Work 5x` ✅
- `Efforts 2x` ✅

Sections NON valides :
- `Test capacité 3x` ❌
- `Bloc principal 4x` ❌
- `Série 5x` ❌

**Utiliser toujours "Main set" en cas de doute.**

---

## Guide Intervals.icu Workout Builder

**Documentation officielle** : Le fichier `David_-_Intervals_icu_-_Workout_builder_-_Guide_-_.pdf` dans le projet contient la syntaxe complète.

**Syntaxe de base validée** :
- Durée : `10m`, `30s`, `1h30`
- Intensité : `90%` (% FTP) ou `100-140w` (watts absolus)
- Cadence : `85rpm` ou `80-90rpm` (plage)
- Ramp : `ramp 50-65%` (progression)

**Exemple complet valide avec répétitions** :
```
Warmup
- 12m ramp 50-65% 85rpm
- 3m 65% 90rpm

Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm

Cooldown
- 10m ramp 65-50% 85rpm
```

---

## Mission

Génère les **7 entraînements** pour la semaine {self.week_number} selon les critères suivants :

### Format de Sortie OBLIGATOIRE - Intervals.icu Natif

Pour chaque jour, génère **UNIQUEMENT** le code Intervals.icu pur (pas de markdown, pas de balises) :

```
=== WORKOUT {self.week_number}-01-TYPE-NomExercice-V001 ===

[Nom séance] ([durée]min, [TSS] TSS)

Warmup
- [durée] [intensité%] [cadence]rpm

Main set
- [structure]

Cooldown
- [durée] [intensité%] [cadence]rpm

=== FIN WORKOUT ===
```

**IMPORTANT** :
- Pas de `###`, `**`, ou autre markdown
- Format texte pur Intervals.icu uniquement
- Chaque workout séparé par `=== WORKOUT ... ===` et `=== FIN WORKOUT ===`
- Directement copiable dans Intervals.icu Workout Builder

### Convention de Nommage

- **Format** : `SSSS-JJ-TYPE-NomExercice-V001`
- **SSSS** : {self.week_number}
- **JJ** : 01 à 07 (lundi à dimanche)
- **TYPE** : END, INT, FTP, SPR, CLM, REC, FOR, CAD, TEC, MIX, PDC, TST
- **NomExercice** : CamelCase sans accents (ex: EnduranceBase, SweetSpotProgressif)

### Types d'Entraînements (CODE)

- **END** : Endurance (Z2, base aérobie)
- **INT** : Intervalles (Sweet-Spot, Seuil, VO2)
- **FTP** : Test FTP ou séance FTP spécifique
- **SPR** : Sprint (efforts maximaux courts)
- **CLM** : Contre-la-montre (efforts soutenus haute intensité)
- **REC** : Récupération active
- **FOR** : Force (cadence basse, couple élevé)
- **CAD** : Technique cadence (variations RPM)
- **TEC** : Technique générale
- **MIX** : Mixte (plusieurs types dans la séance)
- **PDC** : Pédaling/Cadence (technique pédalage)
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
### WORKOUT: {self.week_number}-0X-TYPE-NomExercice-V001

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
- **Répétitions** : Mettre le multiplicateur sur la ligne du titre de section
  - ✅ Correct : `Main set 3x`
  - ❌ Incorrect : `- 3x 10m 90%`

---

## Livrables Attendus

Génère **7 blocs WORKOUT** (un par jour, dimanche = mention repos) au format texte pur Intervals.icu.

**Exemple de format attendu** :

```
=== WORKOUT {self.week_number}-01-END-EnduranceBase-V001 ===

Endurance Base (70min, 52 TSS)

Warmup
- 12m ramp 50-65% 85rpm
- 3m 65% 90rpm

Main set
- 45m 68-72% 88rpm

Cooldown
- 10m ramp 65-50% 85rpm

=== FIN WORKOUT ===


=== WORKOUT {self.week_number}-02-INT-SweetSpot-V001 ===

Sweet Spot 3x10 (74min, 78 TSS)

Warmup
- 12m ramp 50-65% 85rpm
- 5m 65% 90rpm

Main set 3x
- 10m 90% 92rpm
- 4m 62% 85rpm

Cooldown
- 10m ramp 65-50% 85rpm

=== FIN WORKOUT ===
```

**Continue ce format pour les 7 jours.** Chaque workout doit être :
- Délimité par `=== WORKOUT ... ===` et `=== FIN WORKOUT ===`
- Format texte pur (pas de markdown **bold** ou ###)
- Directement copiable dans Intervals.icu
- Syntaxe validée : durée + % FTP + cadence

---
{self._load_available_zwift_workouts()}
---

## Commence Maintenant la Planification !

Génère les 7 entraînements pour {self.week_number} ({date_start_str} → {date_end_str}) au format ci-dessus.

**RAPPEL CRITIQUE** :
- ✅ Format TEXTE PUR Intervals.icu (pas de markdown)
- ✅ Délimiteurs `=== WORKOUT ... ===` et `=== FIN WORKOUT ===`
- ✅ Syntaxe : `10m 90% 92rpm` (espace entre valeurs)
- ✅ Ramp : `ramp 50-65%` (pas `Ramp`)
- ❌ AUCUN `**bold**`, `###`, ou autre markdown
- ❌ AUCUNE explication après les workouts

**🚨 RÉPÉTITIONS - RAPPEL FINAL** :
- ✅ CORRECT : `Main set 3x` sur la ligne du titre
- ✅ CORRECT : `Main set 5x` sur la ligne du titre
- ❌ FAUX : `- 3x 10m 90%` dans l'intervalle
- ❌ FAUX : `Main set` puis `3x` sur ligne suivante
- ❌ FAUX : `Test capacité 3x` (section invalide)

**Exemple répétitions valide** :
```
Main set 4x
- 8m 95% 90rpm
- 4m 62% 85rpm
```

Le but est que je puisse **copier-coller directement** chaque bloc dans Intervals.icu Workout Builder sans modification.
"""
        return prompt
