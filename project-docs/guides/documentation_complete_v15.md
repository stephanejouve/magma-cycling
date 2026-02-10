# Documentation Complète du Suivi v1.5

## Table des Matières

1. Régénération des Composants
2. Utilisation de l'API Intervals.icu
3. Formats de Documentation
4. Processus de Suivi
5. Gestion des Adaptations
6. Notes Importantes
7. **Gestion Nutrition Terrain (Nouveauté v1.4)**
8. **Périodisation et Cycles (Nouveauté v1.4)**

## 1. Régénération des Composants

### Prérequis

Pour chaque nouvelle session avec Claude :

1. Charger .env
2. Charger training-protocol-guidelines.md
3. Charger cette documentation
4. **Charger cycle-tracking.md** (position périodisation)

### Génération des Composants

1. **WorkoutCreator**
```
Prompt : "Peux-tu recréer le composant WorkoutCreator pour créer un nouvel entraînement ?"
```

2. **FeedbackSystem**
```
Prompt : "Peux-tu recréer le composant FeedbackSystem pour saisir les retours d'entraînement ?"
```

3. **NutritionPlanner** (Nouveauté v1.4)
```
Prompt : "Peux-tu créer le composant NutritionPlanner pour planifier la nutrition terrain ?"
```

## 2. Utilisation de l'API Intervals.icu

### Configuration de Base

```javascript
const API_CONFIG = {
  ATHLETE_ID: process.env.VITE_INTERVALS_ATHLETE_ID,
  API_KEY: process.env.VITE_INTERVALS_API_KEY,
  API_BASE_URL: 'https://intervals.icu/api/v1'
};

const getHeaders = () => ({
  'Authorization': `Basic ${btoa('API_KEY:' + API_CONFIG.API_KEY)}`,
  'Content-Type': 'application/json'
});
```

### Endpoints Principaux

#### Activités

```javascript
// Récupérer les activités
const getActivities = async (startDate, endDate) => {
  const response = await fetch(
    `${API_CONFIG.API_BASE_URL}/athlete/${API_CONFIG.ATHLETE_ID}/activities?oldest=${startDate}&newest=${endDate}`,
    { headers: getHeaders() }
  );
  return await response.json();
};

// Uploader une activité
const uploadActivity = async (activityFile) => {
  const formData = new FormData();
  formData.append('file', activityFile);

  const response = await fetch(
    `${API_CONFIG.API_BASE_URL}/athlete/${API_CONFIG.ATHLETE_ID}/activities`,
    {
      method: 'POST',
      headers: getHeaders(),
      body: formData
    }
  );
  return await response.json();
};
```

#### Workouts

```javascript
// Créer un workout
const createWorkout = async (workoutData) => {
  const response = await fetch(
    `${API_CONFIG.API_BASE_URL}/athlete/${API_CONFIG.ATHLETE_ID}/workouts`,
    {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(workoutData)
    }
  );
  return await response.json();
};

// Récupérer les workouts planifiés
const getPlannedWorkouts = async (startDate, endDate) => {
  const response = await fetch(
    `${API_CONFIG.API_BASE_URL}/athlete/${API_CONFIG.ATHLETE_ID}/events?category=WORKOUT&oldest=${startDate}&newest=${endDate}`,
    { headers: getHeaders() }
  );
  return await response.json();
};
```

#### Wellness

```javascript
// Mettre à jour les données wellness
const updateWellness = async (date, data) => {
  const response = await fetch(
    `${API_CONFIG.API_BASE_URL}/athlete/${API_CONFIG.ATHLETE_ID}/wellness/${date}`,
    {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({
        ...data,
        locked: true
      })
    }
  );
  return await response.json();
};
```

#### Nutrition Data (Nouveauté v1.4)

```javascript
// Ajouter données nutrition terrain
const addNutritionData = async (activityId, nutritionData) => {
  const response = await fetch(
    `${API_CONFIG.API_BASE_URL}/athlete/${API_CONFIG.ATHLETE_ID}/activities/${activityId}`,
    {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({
        description: `Nutrition: ${nutritionData.timing} - ${nutritionData.amount}g glucides`,
        ...nutritionData
      })
    }
  );
  return await response.json();
};
```

### Gestion des Erreurs

```javascript
try {
  const response = await apiCall();
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  // Traitement des données
} catch (error) {
  console.error('API Error:', error);
  // Gestion de l'erreur
}
```

### Bonnes Pratiques

1. Toujours vérifier les réponses
2. Utiliser le verrouillage des données wellness
3. Gérer les timeouts
4. Mettre en cache quand possible
5. Utiliser des intervalles raisonnables pour les polling
6. **Documenter nutrition terrain** : Commentaires automatiques

## 3. Formats de Documentation

### Historique des Séances

```markdown
### SXXX-JJ-TYPE-NomSeance
Date : JJ/MM/AAAA

#### Métriques Pré-séance
- CTL : XX
- ATL : XX
- TSB : XX

#### Exécution
- IF : X.XX
- TSS : XX
- Puissance normalisée : XXXW
- RPE : X/10

#### Nutrition (Terrain uniquement)
- Timing : T+XXmin
- Quantité : XXg glucides
- Format : Rice cake/Gel/Liquide
- Efficacité : Échelle 1-5

#### Retour Athlète
[Feedback]

#### Notes Coach
[Observations]
```

### Suivi des Métriques

```markdown
## FTP
| Date | Valeur (W) | W/kg | Contexte |
|------|------------|------|----------|
| JJ/MM/AAAA | XXX | X.XX | Test/Estimation |

## Evolution CTL/ATL/TSB
[Documentation quotidienne]

## HRRc Tracking (Nouveauté v1.4)
| Date | HRRc | Contexte | Évolution |
|------|------|----------|-----------|
| JJ/MM/AAAA | XX | Post-HIIT/Endurance | Tendance |
```

### Rapport Hebdomadaire Standard (6 Fichiers Obligatoires)

#### 1. workout_history_sXXX.md
**Contenu obligatoire :**
- Contexte semaine (TSS réalisé vs planifié, discipline, semaine #)
- Chronologie complète : 7 séances détaillées
- Format par séance : Durée | TSS | IF | RPE + métriques pré/post
- Découvertes techniques par séance
- Notes coach factuelles
- Métriques évolution finale vs début
- Enseignements majeurs (3-5 points)
- Recommandations semaine suivante

#### 2. metrics_evolution_sXXX.md
**Contenu obligatoire :**
- Tableau FTP : Date | Valeur | W/kg | Contexte
- Progression quotidienne : TSB/Fatigue/Condition/TSS
- Évolution poids début→fin
- Métriques clés final : CTL/ATL/TSB estimés
- Validations techniques semaine (découplage, capacités)

#### 3. training_learnings_sXXX.md
**Contenu obligatoire :**
- Découvertes techniques majeures (sweet-spot, volume, etc.)
- Patterns physiologiques identifiés
- Innovations testées (matériel, nutrition, formats)
- Limites/seuils découverts
- Protocoles validés/invalidés
- Points surveillance futurs

#### 4. protocol_adaptations_sXXX.md
**Contenu obligatoire :**
- Ajustements protocoles suite enseignements
- Nouveaux seuils/critères techniques
- Modifications hydratation/nutrition
- Adaptations matériel/discipline
- Exclusions/interdictions mises à jour
- Surveillance renforcée identifiée

#### 5. transition_sXXX_sXXX.md
**Contenu obligatoire :**
- État final semaine (TSB/Fatigue/Validations)
- Acquisitions confirmées vs échecs
- Options progression semaine suivante (2-3 scénarios)
- Recommandation justifiée
- Timeline objectifs (tests, cycles)
- Risques identifiés progression

#### 6. bilan_final_sXXX.md
**Contenu obligatoire :**
- Objectifs visés vs réalisés (synthèse factuelle)
- Métriques finales comparées début
- Découvertes majeures (max 3-4 points critiques)
- Séances clés analysées (succès/échecs)
- Protocoles établis/validés
- Ajustements recommandés cycle suivant
- Enseignements comportementaux
- Conclusion synthétique (2-3 phrases)

### Règles Production
**Ordre obligatoire :** 1→2→3→4→5→6 (dépendances logiques)
**Format :** Markdown copiable, titres standardisés, listes factuelles
**Longueur :** Concision privilégiée, faits vs opinions
**Versioning :** Fichiers sXXX numérotés chronologiquement
**Stockage :** 6 blocs markdown séparés par conversation
**Artefact :** Template semaine suivante (workout_templates_sXXX) systématique

### Critères Qualité
**Factuel :** Métriques précises, données vérifiables
**Concis :** Éviter redondances entre fichiers
**Actionnable :** Recommandations spécifiques semaine suivante
**Traçable :** Progression/régression identifiable
**Complet :** Aucun aspect technique omis

## 4. Processus de Suivi

### Quotidien

1. Récupérer feedback matin
2. Adapter séance si nécessaire
3. Collecter données post-séance
4. Documenter adaptations
5. **Vérifier position TSB** : Guide décisions
6. **Nutrition terrain** : Programmer waypoints si applicable

### Hebdomadaire

1. Analyser progression
2. Compiler bilan
3. Planifier semaine suivante
4. Mettre à jour documentation
5. **Évaluer progression cycle** : Position X/4
6. **Ajuster nutrition** : Apprentissages terrain

### Mensuel

1. Réviser templates
2. Ajuster protocoles
3. Mettre à jour docs
4. Évaluer progression
5. **Valider transition cycles** : Tests obligatoires
6. **Optimiser nutrition** : Capacité individuelle

## 5. Gestion des Adaptations

### Reports de Séance

1. Documenter raison
2. Proposer alternative
3. Ajuster planning
4. Suivre impact TSB
5. **Adapter nutrition** : Report terrain→indoor

### Ajustements d'Intensité

1. Selon TSB actuel
2. Selon feedback
3. Selon objectifs
4. Documenter changements
5. **Terrain vs indoor** : Accepter variations

### Adaptations Météo (Nouveauté v1.4)

1. **Orage/pluie** : Report sécurité prioritaire
2. **Canicule** : Réduction intensité + timing matinal
3. **Alternatives indoor** : Templates équivalents
4. **Documentation** : Impact sur planification

## 6. Notes Importantes

### Composants

- Régénérer au début session
- Vérifier configuration
- Tester fonctionnement
- **Inclure outils nutrition** : RideWithGPS + Wahoo

### Documentation

- Mettre à jour régulièrement
- Format standardisé
- Archiver versions
- **Tracer nutrition terrain** : Apprentissages

### Communication

- Notes claires et précises
- Justifier modifications
- Tracer historique
- **Complexité terrain** : Expliquer variations workout

### Artefacts Templates Hebdomadaires
- Principe : Chaque transition semaine SXXX→SXXX+1 génère artefact markdown dédié templates semaine suivante.
- Nomenclature artefact :

	ID : workout_templates_sXXX (exemple: 	workout_templates_s061)
	Titre : Templates d'Entraînement SXXX
	Type : text/markdown

- Contenu obligatoire :

	Contexte semaine : État post-semaine précédente, validations, questions ouvertes
	Templates par type : Sweet-spot, Endurance, Activation, Récupération, Tests
Adaptations spécifiques : Hydratation, nutrition, surveillance
	Exclusions : Formats interdits, conditions prérequis
	Timeline progression : Objectifs semaine + transition suivante

- Versioning templates :

	Structure <20% modifiée : Même version
	Structure >20% modifiée : Version +1 avec documentation changements

- Maintenance :

- Génération : Fin analyse semaine précédente
- Persistance : Conversation uniquement (non sauvegarde externe)
- Régénération : Prompt standard début nouvelle session Claude

- Usage :

	Référence planification semaine courante
	Base adaptation temps réel selon TSB/fatigue
	Historique évolution protocoles

- Cette règle assure continuité planning hebdomadaire et traçabilité évolution templates selon apprentissages terrain.

## 7. Gestion Nutrition Terrain (Nouveauté v1.4)

### Planification Parcours

#### Phase Analyse
1. **Profil dénivelé** : Identifier montées principales >5%
2. **Timing montées** : Calculer arrivée estimée sur difficultés
3. **Durée totale** : Estimer besoins glucides (30-45g/h)
4. **Points stratégiques** : 15min avant chaque effort

#### Phase Programmation
1. **RideWithGPS** : Créer waypoints nutrition automatiques
2. **Messages personnalisés** : "Nutrition T+XXmin - Rice cake 30g"
3. **Export Wahoo** : Synchronisation directe parcours
4. **Alertes redondantes** : Temps + distance sécurité

#### Phase Validation
1. **Capacité respectée** : Maximum 45g/h
2. **Timing optimal** : 15-20min avant efforts
3. **Format adapté** : Digestibilité validée
4. **Backup plan** : Alternative si problème

### Outils Documentation

#### Templates Nutrition
- **Par durée** : 60-75min / 75-90min / 90-120min
- **Par relief** : Plat / Vallonné / Montagneux
- **Par météo** : Normal / Chaud / Froid
- **Personnalisables** : Selon tolérance individuelle

#### Feedback Post-Terrain
```markdown
## Nutrition Terrain - Retour SXXX-XX
- **Stratégie planifiée** : Timing + quantités
- **Exécution réelle** : Respect protocole
- **Efficacité ressentie** : Échelle 1-5
- **Problèmes identifiés** : Timing/quantité/format
- **Adaptations futures** : Améliorations
- **Corrélation performance** : TSS/IF vs nutrition
```

#### Base Données Apprentissages
- **Parcours réussis** : Stratégies validées
- **Échecs nutritionnels** : Causes identifiées
- **Évolution capacité** : Progression 30→45g/h
- **Formats optimaux** : Rice cake vs gel vs liquide

### Integration API Intervals.icu

#### Données Automatisées
- **Commentaires nutrition** : Ajout automatique séances terrain
- **Métriques corrélées** : TSS/IF/HRRc vs stratégie nutrition
- **Apprentissages** : Base données performances nutrition
- **Templates** : Génération automatique selon historique

#### Analyses Avancées
- **Performance vs nutrition** : Corrélations statistiques
- **Optimisation progressive** : Suggestions adaptations
- **Alertes** : Sous-nutrition détectée post-séance
- **Planification** : Recommandations parcours futurs

## 8. Périodisation et Cycles (Nouveauté v1.4)

### Suivi Position Cycles

#### Documentation Obligatoire
```markdown
# Position Périodisation Actuelle
- **Macro Cycle** : X - Nom (SXXX-SYYY)
- **Micro Cycle** : Semaine X/4
- **Focus dominant** : XX% Endurance + XX% Intensité
- **Objectif spécifique** : Description
- **Tests validation** : Programmés fin cycle
```

#### Transitions Cycles
1. **Tests obligatoires** : Validation acquis avant transition
2. **Adaptation progressive** : Pas de saut phases
3. **Documentation impact** : Métriques évolution
4. **Ajustements** : Selon réponse individuelle

### Arsenal Structuré

#### Cycle 1 - Base HRRc
- **HIIT léger** : 2x2, micro-intervalles 30/30
- **Endurance dominante** : 70-80% volume
- **Tests** : HRRc monitoring, capacité récupération

#### Cycle 2 - Seuil Lactique
- **Sweet-Spot focus** : 88-93% FTP développement
- **HIIT adapté** : Pyramide, escalier dégressif
- **Tests** : Durée sweet-spot, tolérance lactique

#### Cycle 3 - VO2 Max
- **Haute intensité** : 106-120% FTP
- **Formats spécifiques** : 4×4min, dégressif, montagne
- **Tests** : Capacité aérobie maximale

### Adaptations Coaches

#### Respect Périodisation
1. **Position obligatoire** : Vérifier cycle-tracking.md
2. **Progression naturelle** : Pas de forcing transitions
3. **Tests validation** : Acquis confirmés avant passage
4. **Documentation** : Traçabilité évolution

#### Flexibilité Encadrée
1. **Micro-adaptations** : Selon TSB quotidien
2. **Macro-respect** : Objectifs cycles maintenus
3. **Innovation conditionnelle** : Arsenal approprié cycle
4. **Récupération prioritaire** : Âge 53 facteur limitant


## 9.Source Complémentaire Workouts
#### Site référence : https://whatsonzwift.com/workouts/
Utilisation Ressource
Consultation Catalogues

### Accès direct workouts Zwift officiels
Programmes saisonniers (Zwift Camp, Build Me Up, etc.)
Détails techniques : Durée, TSS, zones, structure
Comparaison formats disponibles

####Intégration Planning
Conditions utilisation :

TSB >+10 pour tests maximaux
Alignement objectifs cycle en cours
Validation coach avant exécution
Documentation post-séance obligatoire

### Programmes Identifiés
Zwift Camp: Baseline (Septembre-Octobre)
4 workouts diagnostiques :

Red Zone Repeats (40min, 27 TSS) - Sprint 5s
Power Punches (43min, 38 TSS) - Anaérobie 1min
Climb Control (41min, 55 TSS) - VO2 5min
Flat Out Fast (40min, 70 TSS) - FTP 20min

Usage recommandé :

### Tests baseline début cycle
Validation FTP réelle vs estimation
Diagnostic capacités VO2/sprint/anaérobie
Fréquence : 1×/cycle macro (4 semaines)

### Autres Programmes Disponibles

Build Me Up
FTP Builder
Workouts spécifiques routes/événements
Programmes saisonniers Zwift

### Règles Intégration
#### Priorités :

Templates personnalisés > Workouts Zwift externes
Workouts externes = tests/validation uniquement
Pas substitution séances planifiées sans validation
Documentation What's on Zwift obligatoire si modification

#### Protocole utilisation :

Identification workout pertinent (URL What's on Zwift)
Validation coach (TSB, timing, objectifs)
Exécution selon protocoles établis
Documentation complète post-séance
Analyse résultats vs baseline personnelle

Documentation Post-Workout Externe
Ajouts obligatoires historique :
markdown### SXXX-XX-TST-NomWorkoutZwift
Source : [URL What's on Zwift]
Type : Test baseline / Workout externe

#### Justification
- Objectif : Diagnostic FTP/VO2/Sprint
- Alternative templates : Pourquoi workout externe choisi

#### Résultats vs Baseline
- Métrique testée : Valeur obtenue
- Comparaison estimation actuelle
- Ajustements protocoles recommandés
Exemples Application S062
Tests Baseline samedi 12/10 :

Flat Out Fast : FTP 20min (vs 220W estimation)
Climb Control : VO2 5min (baseline inexistante)
Source : whatsonzwift.com/workouts/zwift-camp-baseline
Justification : Diagnostic critique post-régression CTL

#### Documentation attendue :

FTP réelle mesurée vs 220W
VO2 5min baseline établie
Ajustement zones si FTP <220W
Plan reconstruction selon résultats
---

**Version 1.4 - Intégration enseignements S050**
**Nutrition terrain + Périodisation + Arsenal HIIT/VO2 + Complexité terrain**
