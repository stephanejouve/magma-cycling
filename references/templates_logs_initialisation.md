# Templates d'Initialisation des 4 Logs Principaux

Ce fichier contient les templates vierges pour initialiser les 4 fichiers de documentation continue.

---

## 1. workouts-history.md

```markdown
# Historique des Entraînements

> Documentation chronologique complète de toutes les séances réalisées.
> Mise à jour : Après chaque séance

## Semaine S001 (JJ/MM/AAAA - JJ/MM/AAAA)

### S001-01-END-EchauffementBase-V001
Date : JJ/MM/AAAA
Fichier : S001-01-END-EchauffementBase-V001.zwo

#### Métriques Pré-séance
- CTL : XX
- ATL : XX
- TSB : XX
- Poids : XX.Xkg
- Sommeil : Xh XXmin

#### Description
[Description de la séance planifiée]

#### Exécution
- Durée réalisée : XXmin
- IF : X.XX
- TSS : XX
- Puissance moyenne : XXXW
- Puissance normalisée : XXXW
- Cadence moyenne : XXrpm
- FC moyenne : XXXbpm
- RPE : X/10
- Découplage cardiovasculaire : X.X%

#### Métriques Post-séance
- CTL : XX
- ATL : XX
- TSB : XX

#### Retour Athlète
[Ressenti général, points positifs, difficultés rencontrées]

#### Notes Coach
[Observations techniques, validations, points d'attention]

---

## Semaine S002 (JJ/MM/AAAA - JJ/MM/AAAA)

### S002-01-...
[Template identique]

---

## Instructions d'Utilisation

### Mise à Jour Systématique
- Remplir immédiatement après chaque séance
- Ne jamais modifier les entrées passées (historique figé)
- Ajouter nouvelles semaines au début du fichier (ordre antichronologique)

### Conventions
- Dates au format : JJ/MM/AAAA
- Durées en minutes entières
- Puissances en Watts (W)
- Cadences en RPM
- FC en BPM
- RPE sur échelle 1-10
- Découplage en pourcentage avec 1 décimale

### Métriques Obligatoires
- CTL/ATL/TSB pré et post (estimer si données indisponibles)
- IF, TSS, puissance moyenne
- RPE (perception effort)
- Découplage (validateur qualité entraînement)
```

---

## 2. metrics-evolution.md

```markdown
# Évolution des Métriques

> Suivi longitudinal des indicateurs clés de performance et de forme.
> Mise à jour : Après chaque séance + bilans hebdomadaires/mensuels

## FTP (Functional Threshold Power)

| Date | Valeur (W) | W/kg | Contexte | Méthode |
|------|------------|------|----------|---------|
| JJ/MM/AAAA | 220 | 2.62 | Baseline initiale | Test 20min |
| | | | | |

### Notes FTP
- Baseline actuelle : 220W
- Objectif à terme : 260W+
- Tests planifiés : [dates et protocoles]

---

## Poids Corporel

| Date | Poids (kg) | Pesée | Note |
|------|------------|-------|------|
| JJ/MM/AAAA | 83.8 | Matin | Post-réveil, avant petit-déjeuner |
| | | | |

### Tendance
- Baseline : 83.8kg
- Plage cible : [selon objectifs]
- Variations saisonnières observées : [patterns]

---

## Métriques de Forme (CTL/ATL/TSB)

### Évolution CTL (Chronic Training Load / Fitness)

| Semaine | CTL Début | CTL Fin | Évolution | Notes |
|---------|-----------|---------|-----------|-------|
| S001 | 54 | 56 | +2 | Progression contrôlée |
| | | | | |

**Points Clés de Progression**
- Baseline : CTL 54
- Objectif : Progression +2-4 points/semaine
- Seuils identifiés : [limites observées]

### Évolution ATL (Acute Training Load / Fatigue)

| Semaine | ATL Moyen | ATL Max | Notes |
|---------|-----------|---------|-------|
| S001 | XX | XX | [Observations] |
| | | | |

**Patterns Observés**
- Pics post-intensité : [valeurs typiques]
- Récupération : [durées observées]
- Seuils alertes : [limites fatigue]

### Évolution TSB (Training Stress Balance / Forme)

| Date | TSB | Contexte | Performance |
|------|-----|----------|-------------|
| JJ/MM/AAAA | +3 | Pré-séance Sweet-Spot | Exécution réussie |
| | | | |

**Plages Optimales Identifiées**
- VO2 Max : TSB +5 minimum (checklist validée)
- Sweet-Spot : TSB -5 à +5 
- Endurance : TSB quelconque
- Tests : TSB +5 à +15

---

## Autres Métriques

### Sommeil (Withings)

| Date | Durée | Qualité | FC Repos | Note |
|------|-------|---------|----------|------|
| JJ/MM/AAAA | 5h33 | XX% | 40 bpm | Dette sommeil |
| | | | | |

**Patterns Identifiés**
- Moyenne actuelle : 5h33
- Cible : 7h+ minimum
- Impact sur VO2 : Corrélation validée
- FC repos baseline : 40 bpm

### Asymétrie Pédalage (Wahoo)

| Type Effort | Droite | Gauche | Notes |
|-------------|--------|--------|-------|
| Explosif (>110% FTP) | 56% | 44% | Pattern établi |
| Modéré (75-95% FTP) | 50% | 50% | Équilibre naturel |
| | | | |

**Enseignements**
- Asymétrie effort-dépendante
- Pas d'intervention nécessaire (physiologique)
- Surveillance continue

---

## Validations Techniques

### Découplage Cardiovasculaire

| Séance | Type | Découplage | Validation |
|--------|------|------------|------------|
| SXXX-XX-... | Sweet-Spot | 6.2% | ✅ <7.5% |
| | | | |

**Seuil Validation** : <7.5% systématiquement

### Capacités Identifiées

**Indoor**
- Sweet-Spot consolidé : 88-90% FTP
- Progression testée : 88%+ à valider
- Limites observées : [selon données]

**Outdoor (terrain)**
- Capacité supérieure indoor : 54km RPE 4/10 = 163 TSS
- Discipline intensité : Problématique établie
- Stratégie : Indoor-only 2-3 mois

---

## Instructions d'Utilisation

### Fréquence Mise à Jour
- **FTP** : Après chaque test formel
- **Poids** : Hebdomadaire minimum
- **CTL/ATL/TSB** : Après chaque séance (estimé ou Intervals.icu)
- **Sommeil** : Quotidien si disponible (Withings)
- **Asymétrie** : Analyse mensuelle des tendances

### Analyse Tendances
- Révision hebdomadaire : Bilans sXXX
- Révision mensuelle : Progression cycles
- Alertes : Déviations significatives protocoles
```

---

## 3. training-learnings.md

```markdown
# Enseignements d'Entraînement

> Journal des découvertes techniques, patterns physiologiques, protocoles validés/invalidés.
> Mise à jour : Après chaque découverte significative + bilans hebdomadaires

## Intensités Optimales

### Sweet Spot (88-93% FTP)

#### Intensité Validée : 88-90% FTP
**Durée optimale** : X-X minutes par intervalle
**Format de récupération** : X minutes à 65% FTP
**Cadence idéale** : 85-90 rpm
**Nombre répétitions** : 3-4x selon durée

**Pattern Observé**
- [Découvertes spécifiques]

**Points d'Attention**
- [Limites identifiées]
- [Conditions prérequis]

**Progression**
- État actuel : 88-90% validé
- Test suivant : 88%+ à confirmer selon TSB
- Timeline : [dates progression]

---

### Seuil (95-105% FTP)

#### Protocole Actuel
**Durées maximales** : [selon données]
**Formats efficaces** : [structures validées]

**Signes de Rupture**
- [Indicateurs limite]
- [Moments critiques]

**Adaptations Nécessaires**
- [Ajustements protocole]

---

### VO2 Max (106-120% FTP)

#### Checklist Validée (5 Critères Obligatoires)
1. ✅ TSB minimum +5
2. ✅ Sommeil >7h la veille
3. ✅ Pas d'intensité >85% FTP dans les 48h précédentes
4. ✅ FC repos matinale dans plage normale (±5 bpm de 40)
5. ✅ Aucun signe fatigue résiduelle

**Intensité Testée**
- Référence : 250W (114% FTP actuelle)
- Durée intervalles : [données validation]
- Ratio travail/repos : [protocole établi]

**Limitants Identifiés**
- Sommeil = facteur critique validé
- TSB insuffisant = échec garanti
- [Autres patterns]

---

## Patterns Physiologiques Spécifiques

### Capacité Terrain vs Indoor

**Découverte Majeure**
- Terrain : Capacité significativement supérieure
  - Exemple : 54km outdoor RPE 4/10 = 163 TSS
  - Tolérance volume/intensité augmentée
  
- Indoor : Perception effort différente
  - Zwift : [caractéristiques]
  - TrainingPeaks Virtual : [caractéristiques]

**Problématique Discipline**
- Pattern : Surcharge systématique terrain (échecs répétés)
- Cause : Euphorie montées + terrain varié
- Solution : Stratégie indoor-only 2-3 mois
- Objectif : Établir discipline avant retour progressif outdoor

---

### Découplage Cardiovasculaire

**Seuil Validation Établi : <7.5%**
- Systématiquement respecté séances qualité
- Indicateur fiable qualité entraînement
- Corrélation avec perception effort

**Usage**
- Validation post-séance automatique
- Alerte si >7.5% : Revoir protocole

---

### Asymétrie Pédalage

**Pattern Validé : Effort-Dépendant**
- Explosif (>110% FTP) : 56% droite / 44% gauche
- Modéré (75-95% FTP) : 50% droite / 50% gauche

**Interprétation**
- Physiologique, pas pathologique
- Pas d'intervention nécessaire
- Surveillance continue trends

---

## Protocoles Validés

### Hydratation

#### Intensité >88% FTP
**Protocole** : Fréquence doublée des prises
**Validation** : [dates tests, résultats]
**Format** : Isotonique, [quantités]

#### Séances Longues (>90min)
**Protocole** : [timing optimisé]
**Validation** : [données terrain]

---

### Nutrition Terrain

#### Capacité Individuelle : Maximum 45g Glucides/Heure
**Validation** : [dates tests]
**Format Privilégié** : Rice cakes (tolérance confirmée)

#### Timing Optimal : 15min Avant Efforts Principaux
**Ciblage** : Montées >5% grade
**Planification** : Waypoints automatiques RideWithGPS → Wahoo

**Protocole Messages**
- Format : "Nutrition T+XXmin - Rice cake 30g"
- Redondance : Temps + distance (sécurité)

---

### Activation Neuromusculaire

**Principe** : Systématique avant intensité
**Format** : [structure validée]
**Durée** : [timing optimal]
**Validation** : [impact observé]

---

## Protocoles Invalidés / Adaptés

### [Exemple : Format Intensité X]
**Test Initial** : [date, conditions]
**Résultats** : [observations]
**Raison Échec** : [analyse]
**Adaptation** : [nouveau protocole]

---

## Limites et Seuils Découverts

### Facteur Limitant Principal : Dette Sommeil

**Données**
- Moyenne actuelle : 5h33
- Cible minimum : 7h+
- Impact validé : Échec VO2 si <7h

**Corrélations Établies**
- Sommeil <6h → Intensité >95% FTP compromise
- Sommeil <7h → VO2 max déconseillé (checklist)

**Stratégie**
- Priorité absolue : Améliorer hygiène sommeil
- Adaptations séances : Selon qualité nuit précédente

---

### Plages TSB Optimales

**Par Type Séance**
- VO2 Max : TSB +5 minimum (rigide)
- Sweet-Spot : TSB -5 à +5 (flexible)
- Endurance : TSB quelconque
- Tests FTP : TSB +5 à +15 (optimal)

---

## Points de Surveillance Futurs

### À Valider
- [ ] Progression Sweet-Spot 88% → 90%+
- [ ] Capacité force-endurance cadences basses
- [ ] [Autres hypothèses à tester]

### À Monitorer
- [ ] Évolution asymétrie pédalage long terme
- [ ] Corrélation sommeil/performance (quantification)
- [ ] [Autres métriques intérêt]

---

## Instructions d'Utilisation

### Quand Documenter
- **Immédiatement** : Découverte significative pendant/après séance
- **Hebdomadaire** : Synthèse patterns semaine (fichier sXXX)
- **Mensuel** : Révision protocoles, validation enseignements

### Format Entrées
- **Titre descriptif** : Nature découverte
- **Contexte** : Date, conditions, séance concernée
- **Données** : Métriques objectives supportant observation
- **Analyse** : Interprétation factuelle
- **Action** : Protocole modifié ou à tester

### Critères Qualité
- Factuel (pas d'opinions non supportées)
- Quantifié (métriques précises)
- Reproductible (conditions claires)
- Actionnable (implications protocoles)
```

---

## 4. workout-templates.md

```markdown
# Templates d'Entraînement

> Catalogue évolutif des formats de séances validés avec contextes d'utilisation.
> Mise à jour : Après validation nouveau format ou modification >20%

## Formats Sweet Spot (88-93% FTP)

### Template SST-1 : Consolidation Base

**Structure**
```
Warmup (15min)
- 10min : 50% → 75% FTP, 85 rpm
- 5min : 75% FTP, 90 rpm

Main Set (3x)
- 8min : 90% FTP, 90 rpm
- 3min : 65% FTP, 85 rpm (récupération active)

Cooldown (10min)
- 10min : 65% → 50% FTP, 85 rpm
```

**Métriques**
- Durée totale : ~45 min
- TSS estimé : ~XX
- IF estimé : ~X.XX

**Contexte d'Utilisation**
- **TSB recommandé** : -5 à +5
- **Placement semaine** : Mardi ou Jeudi (post-repos)
- **Objectif** : Développement capacité aérobie haute
- **Prérequis** : Aucun (séance baseline)

**Adaptations Possibles**
- Intensité main set : 88-92% FTP selon forme
- Durée intervalles : 6-10min selon capacité
- Nombre répétitions : 2-4x selon TSS cible

**Versioning**
- Version actuelle : V001
- Dernière modification : JJ/MM/AAAA
- Raison : [si applicable]

---

### Template SST-2 : [Autre Format]

[Structure identique]

---

## Formats Endurance (60-75% FTP)

### Template END-1 : Sortie Roulante

**Structure**
```
Phase unique
- 60-90min : 65-70% FTP, 85-90 rpm
- Variations cadence : ±5 rpm toutes les 10min
- Hydratation : Toutes les 15min
```

**Métriques**
- Durée : 60-90min (modulable)
- TSS estimé : XX-XX selon durée
- IF estimé : 0.65-0.70

**Contexte d'Utilisation**
- **TSB recommandé** : Quelconque
- **Placement semaine** : Flexible, souvent post-intensité
- **Objectif** : Récupération active, maintien volume
- **Prérequis** : Aucun

**Adaptations Terrain**
- Parcours plat privilégié
- Tolérance variations naturelles ±10% FTP
- Nutrition si >90min : 30-45g glucides/heure

---

## Formats Seuil (95-105% FTP)

### Template THR-1 : Intervalles Seuil

**Structure**
```
Warmup (15min)
- 10min : 50% → 75% FTP, 85 rpm
- 5min : 75% → 85% FTP, 90 rpm

Main Set (4x)
- 5min : 95-100% FTP, 90-95 rpm
- 5min : 60% FTP, 85 rpm

Cooldown (10min)
- 10min : 65% → 50% FTP, 85 rpm
```

**Métriques**
- Durée totale : ~65 min
- TSS estimé : ~XX
- IF estimé : ~X.XX

**Contexte d'Utilisation**
- **TSB recommandé** : 0 à +5
- **Placement semaine** : Mercredi ou Samedi (post-récupération)
- **Objectif** : Développement FTP
- **Prérequis** : Sommeil >6h, pas d'intensité 48h avant

**Adaptations Possibles**
- Intensité : 95-105% FTP selon validation
- Durée intervalles : 4-8min selon capacité
- Nombre répétitions : 3-5x selon TSS cible

---

## Formats VO2 Max (106-120% FTP)

### Template VO2-1 : Intervalles Courts

**⚠️ CHECKLIST OBLIGATOIRE AVANT EXÉCUTION**
- [ ] TSB ≥ +5
- [ ] Sommeil ≥ 7h la veille
- [ ] Aucune intensité >85% FTP dans les 48h
- [ ] FC repos matinale normale (40 ± 5 bpm)
- [ ] Aucun signe fatigue résiduelle

**Structure**
```
Warmup (20min)
- 10min : 50% → 75% FTP, 85 rpm
- 5min : 75% → 85% FTP, 90 rpm
- 5min : Activation neuromusculaire
  - 3x (20sec @ 120% FTP, 40sec @ 60% FTP)

Main Set (5x)
- 3min : 110-115% FTP, 95-100 rpm
- 3min : 55% FTP, 85 rpm

Cooldown (15min)
- 15min : 65% → 50% FTP, 85 rpm
```

**Métriques**
- Durée totale : ~65 min
- TSS estimé : ~XX
- IF estimé : ~X.XX

**Contexte d'Utilisation**
- **TSB recommandé** : +5 à +10 (strict)
- **Placement semaine** : Uniquement si checklist validée
- **Objectif** : Développement VO2 max
- **Prérequis** : Checklist 5 critères (non négociable)

**Intensités Testées**
- Référence validée : 250W (114% FTP220)
- Progression : À valider selon protocole

**Hydratation Renforcée**
- Fréquence doublée pendant main set
- Isotonique requis

---

## Formats Activation Neuromusculaire

### Template ACT-1 : Pré-Intensité

**Structure**
```
Phase unique (10min)
- 5min : 60% FTP, 85 rpm (échauffement)
- 5x (20sec @ 120% FTP, 40sec @ 60% FTP)
```

**Contexte d'Utilisation**
- **Placement** : Systématique avant séance intensité
- **Objectif** : Préparation neuromusculaire
- **Durée** : 10min (intégré warmup ou séparé)

---

## Formats Récupération

### Template REC-1 : Récupération Active

**Structure**
```
Phase unique (30-45min)
- 30-45min : 50-60% FTP, 85 rpm
- Cadence stable, aucune variation
```

**Contexte d'Utilisation**
- **TSB recommandé** : Négatif (fatigue élevée)
- **Placement semaine** : Post-intensité ou lendemain séance dure
- **Objectif** : Favoriser récupération active
- **Intensité max** : 60% FTP (strict)

---

## Formats Tests

### Template TEST-FTP : Test 20 Minutes

**⚠️ CONDITIONS OPTIMALES REQUISES**
- [ ] TSB ≥ +10
- [ ] Sommeil >7h minimum 2 nuits consécutives
- [ ] Aucune intensité >80% FTP dans les 72h
- [ ] Motivation élevée (mental = facteur clé)

**Structure**
```
Warmup (20min)
- 10min : 50% → 75% FTP, 85 rpm
- 5min : 75% → 85% FTP, 90 rpm
- 5min : Activation neuromusculaire

Test (20min)
- 20min : Effort maximal soutenable, 90-95 rpm
- Objectif : Puissance moyenne maximale sur 20min

Cooldown (15min)
- 15min : 65% → 50% FTP, 85 rpm
```

**Calcul FTP**
- FTP = Puissance moyenne 20min × 0.95

**Fréquence**
- Maximum 1x / 6 semaines
- Idéalement 1x / 8-12 semaines

---

## Formats Spécifiques Terrain

### Template TER-1 : Sortie Terrain Contrôlée

**⚠️ ATTENTION : Discipline intensité critique**

**Principe**
- Parcours : Dénivelé modéré (<500m/50km)
- Intensité cible : 70-75% FTP moyenne
- Durée : 90-120min
- **Règle absolue** : Respecter limites intensité malgré terrain

**Nutrition Terrain**
- Planification : Waypoints RideWithGPS
- Timing : 15min avant montées >5%
- Format : Rice cakes 30g
- Capacité max : 45g glucides/heure

**Retour Indoor Obligatoire Si**
- Échec discipline 2 séances consécutives
- Surcharge TSS >+30% planifié
- TSB post-séance < -15

---

## Instructions Versioning

### Quand Créer Nouvelle Version

**Modification Mineure (<20% structure)**
- Ajustement intensité ±5%
- Modification durée intervalles ±2min
- Changement nombre répétitions ±1
→ **Conserver même version, documenter note**

**Modification Majeure (>20% structure)**
- Changement type intervalles
- Modification ratio travail/repos significative
- Ajout/suppression phase complète
→ **Version +1, documenter raison changement**

### Nomenclature Versions
- V001 : Version initiale
- V002 : Première modification majeure
- V003 : etc.

### Documentation Changements
```markdown
**Changelog**
- V002 (JJ/MM/AAAA) : [Description modification]
- V001 (JJ/MM/AAAA) : Version initiale
```

---

## Index Templates par Objectif

### Développement FTP
- SST-1, SST-2 : Sweet-Spot (priorité)
- THR-1 : Seuil (complémentaire)

### Développement VO2 Max
- VO2-1 : Intervalles courts (checklist stricte)

### Maintien Volume
- END-1 : Endurance base
- REC-1 : Récupération active

### Préparation Tests
- TEST-FTP : Test 20min (conditions optimales)

---

## Instructions d'Utilisation

### Sélection Template
1. Identifier objectif séance
2. Vérifier TSB actuel vs recommandé template
3. Valider prérequis (sommeil, fatigue, délai dernière intensité)
4. Adapter si nécessaire selon conditions

### Création Nouveau Template
1. Tester format minimum 2x
2. Valider métriques (TSS, IF, découplage)
3. Documenter contexte utilisation
4. Assigner version V001
5. Mettre à jour index

### Archivage Templates Obsolètes
- Ne jamais supprimer (historique)
- Marquer [OBSOLÈTE] dans titre
- Documenter raison abandon
- Déplacer en fin de fichier
```

---

## Instructions Finales

### Initialisation des 4 Fichiers

1. **Copier chaque template ci-dessus dans un fichier séparé**
   - `workouts-history.md`
   - `metrics-evolution.md`
   - `training-learnings.md`
   - `workout-templates.md`

2. **Personnaliser les baselines**
   - Remplir FTP actuelle, poids, CTL/ATL/TSB de départ
   - Ajouter première séance dans workouts-history.md
   - Documenter premiers enseignements si applicable

3. **Maintenir à jour systématiquement**
   - workouts-history.md : Après CHAQUE séance
   - metrics-evolution.md : Après chaque séance + bilans hebdo
   - training-learnings.md : Après découverte significative
   - workout-templates.md : Après validation nouveau format

### Relation avec Bilans Hebdomadaires

Les **4 logs** sont des **documents vivants** mis à jour au fil de l'eau.

Les **6 fichiers hebdomadaires** (sXXX) sont des **snapshots** périodiques qui synthétisent les logs pour une semaine donnée.

**Flux de travail type :**
```
Séance réalisée
    ↓
Mise à jour workouts-history.md
    ↓
Mise à jour metrics-evolution.md
    ↓
Découverte ? → Mise à jour training-learnings.md
    ↓
Fin de semaine
    ↓
Génération 6 fichiers sXXX (synthèses)
    ↓
Nouveau template validé ? → Mise à jour workout-templates.md
```

### Backup et Versioning

- **Sauvegardes régulières** : Hebdomadaires minimum
- **Versioning** : Git recommandé pour traçabilité complète
- **Format** : Markdown pur (compatible tous éditeurs)

---

**Templates créés** : Novembre 2025  
**Version** : 1.0  
**Usage** : Initialisation logs ou reset complet documentation
