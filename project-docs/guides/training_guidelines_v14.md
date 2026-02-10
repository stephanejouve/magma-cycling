# Protocole d'Entraînement et Directives v1.4

## Convention de Nommage

Format : `SSSS-JJ-TYPE-NomDeLExercice-VVVV`

- SSSS : Numéro de la semaine (ex: S001)
- JJ : Jour de la semaine (01 à 07)
- TYPE : Code du type d'exercice
- NomDeLExercice : CamelCase sans accents
- VVVV : Version (ex: V001)

## Types d'Exercices

1. END - Endurance
2. INT - Intervalles
3. FTP - Test FTP
4. SPR - Sprint
5. CLM - Contre-la-montre
6. REC - Récupération
7. FOR - Force
8. CAD - Cadence
9. TEC - Technique
10. MIX - Mixte
11. PDC - Perte De Calories
12. TST - Test PMA

## Format Intervals.icu

### Structure de Base

```
Nom du bloc
- durée intensité cadence

Bloc répété Nx
- étape 1
- étape 2
```

### Paramètres Standards

- Durées : "30s", "10m", "1h30"
- Intensités : "80%", "80-90%", "Ramp 60-80%"
- Cadences : "90rpm", "85-95rpm"

### Valeurs Recommandées

- Échauffement : 80-90 rpm, 50-65% FTP
- Récupération : 85 rpm, 55-65% FTP
- Efforts modérés : 90-95 rpm, 75-85% FTP
- Efforts intenses : 95-100 rpm, >85% FTP
- Retour au calme : 85-80 rpm, 65-50% FTP

## Structures Types

### 1. Endurance (END)

```
Warmup
- 12m Ramp 50-65% 85rpm
- 3m 65% 90rpm

Main
- 45m 65-75% 85-95rpm

Cooldown
- 10m Ramp 65-50% 85rpm
```

### 2. Intervalles (INT)

```
Warmup
- 10m Ramp 50-65% 85rpm
- 5m 65% 90rpm

Main set 4x
- 3m 90% 95rpm
- 2m 60% 85rpm

Cooldown
- 8m Ramp 65-50% 85rpm
```

### 3. Force (FOR)

```
Warmup
- 12m Ramp 50-65% 85rpm

Main 3x
- 5m 75% 65rpm
- 3m 60% 90rpm

Cooldown
- 10m 60% 85rpm
```

## Arsenal HIIT Varié (Nouveauté v1.4)

### Rotation 5 Formats
1. **2x2 Adaptation** : 4×(1min 109% + 1min 130% + 2min 66%)
2. **Micro-Intervalles 30/30** : 12×(30s 120% + 30s 60%)
3. **Pyramide Explosive** : 1-2-3-2-1min progression intensité
4. **Tabata Adapté** : 4×(4×20s 140% + 10s 50% + 4min récup)
5. **Escalier Dégressif** : 4-3-2-1min intensité progressive

### VO2 Max Integration
- **Fréquence** : 1×/semaine maximum (âge 53)
- **Formats** : 4×4min 110% / Dégressif / Montagne-spécifique
- **TSB requis** : >-5 pour exécution optimale

## Stratégie Nutrition Terrain (Nouveauté v1.4)

### Capacité Individuelle
- **Limite physiologique** : 30-45g glucides/h (non-professionnel)
- **Format validé** : Rice cake maison 30g (25g glucides nets)
- **Timing optimal** : 15min avant efforts + toutes 20-30min

### Protocole par Durée
- **60-75min** : 1 prise T+20min (avant première difficulté)
- **75-90min** : 2 prises T+20min + T+50min
- **90-120min** : 3 prises T+15min + T+40min + T+70min
- **>120min** : Ajouter gel/liquide selon tolérance

### Outils Technologiques
- **RideWithGPS** : Waypoints nutrition automatiques
- **Wahoo ELEMNT** : Alertes temps/distance redondantes
- **Integration** : Export direct parcours→compteur
- **Personnalisation** : Messages rappel stratégie

## Points de Validation

### 1. Pré-création

- Objectif clair défini
- Durée totale calculée
- Zones d'intensité identifiées
- Cadences appropriées
- **Nutrition planifiée** (si terrain >60min)

### 2. Pendant la Création

- Respect de la syntaxe
- Instructions claires
- Progression logique
- Messages d'encouragement
- **Waypoints nutrition** (terrain uniquement)

### 3. Post-création

- Test du format dans Intervals.icu
- Vérification du TSS calculé
- Validation de la durée totale
- Cohérence des transitions
- **Programmation alertes** (parcours terrain)

## Adaptations Contextuelles

### Selon TSB

- TSB < -10 : Réduire intensités de 5%
- TSB < -15 : Réduire volumes de 20%
- TSB > +10 : Possible d'augmenter intensité

### Selon Objectifs

- Perte de poids : séances plus longues en Z2
- Force : cadence basse, résistance élevée
- Endurance : volume progressif en Z2
- **HRRc development** : Priorité récupération cardiovasculaire

### Selon Conditions Terrain (Nouveauté v1.4)

- **Vallonné modéré** : Workout ≠ réalité (variations IF/TSS inévitables)
- **Relief >200m** : Anticiper écarts 15-25% vs prévisions indoor
- **Montées >5%** : Nutrition 15min avant obligatoire
- **Parcours >30km** : Stratégie nutrition systématique
- **Météo défavorable** : Adaptation indoor alternative

### Selon Conditions Météo

- Canicule (>30°C) : Mode survival 30-45min, timing 05h30-07h00
- Normal (20-25°C) : Planning standard post-milestone
- Frais (<20°C) : Innovation Over/Under possible
- **Orage/pluie** : Report terrain sécurité prioritaire

## Périodisation (Nouveauté v1.4)

### Macro Cycles (4 semaines)
- **Cycle 1** : Base HRRc (80% endurance + 20% HIIT léger)
- **Cycle 2** : Seuil lactique (60% endurance + 30% sweet-spot + 10% HIIT)
- **Cycle 3** : VO2 Max (50% endurance + 30% VO2 + 20% maintien)

### Micro Cycles (1 semaine)
- **Semaines 1-3** : Progression charge +10-15%
- **Semaine 4** : Décharge -30% + tests validation

## Templates Terrain + Nutrition (Nouveauté v1.4)

### Terrain 60-75min
```
Waypoint 1 : T+20min (Km 8-12)
Nutrition : 1 rice cake 30g
Alertes : RideWithGPS + Wahoo 20min
Intensité : 65-75% FTP adaptatif relief
```

### Terrain 75-90min
```
Waypoint 1 : T+20min (avant première difficulté)
Waypoint 2 : T+50min (avant deuxième difficulté)
Nutrition : 2 rice cakes 30g
Alertes : 20min + 50min
```

### Terrain 90-120min
```
Waypoints : T+15/40/70min
Nutrition : 3 prises (rice cake + gel possible)
Alertes : Triple redondance tech
Hydratation : 600ml/h minimum
```

### Upload Automatique

- API Intervals.icu intégrée
- Planification batch semaine
- Adaptation temps réel conditions
- **Documentation nutrition** : Commentaires automatiques

## Notes Techniques

1. Toujours inclure échauffement progressif
2. Prévoir transitions adaptées
3. Inclure retour au calme
4. Documenter les points techniques
5. **Programmer nutrition terrain** : Waypoints + alertes
6. **Complexité terrain** : Accepter variations vs workout théorique
7. **Capacité glucides** : Respecter limite 30-45g/h individuelle
