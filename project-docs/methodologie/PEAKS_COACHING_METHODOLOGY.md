# Enseignements Peaks Coaching Group - Intégration Prompts IA

## Métadonnées
- **Source** : Peaks Coaching Group / Hunter Allen
- **Références** : shoppeaks.com, "Training and Racing with a Power Meter"
- **Application** : Cycliste Masters 54 ans, FTP 220W → 260W
- **Date compilation** : 14 février 2026

---

## 1. PRINCIPES FONDAMENTAUX

### 1.1 Citation Philosophique Centrale
**"Testing is training and training is testing"** - Dr. Andrew Coggan

**Implications pour l'IA** :
- Intégrer tests dans semaines d'entraînement normales
- Ne pas bloquer semaines dédiées uniquement aux tests
- Tests multiples peuvent être combinés même journée

### 1.2 Méthode Traditionnelle vs Polarisée

**CRITIQUE : Entraînement Polarisé NON recommandé pour :**
- Cyclistes >35 ans non-élites
- Tout cycliste avec budget temps 8-15h/semaine
- Masters cherchant maintien fitness année complète

**Distribution Polarisée (À ÉVITER)** :
- 70-80% endurance très lente (Z1-Z2 bas)
- 20-30% intensité maximale (FTP/VO2/AC)
- Zéro "in-between" (Tempo/Sweet-Spot)

**Problèmes Polarisé** :
- Psychologiquement insoutenable long terme
- Ennui extrême (3-4h endurance lente)
- Souffrance constante (intervalles all-out)
- Taux abandon élevé après 2-3 mois
- Perte fitness excessive entre pics

**RECOMMANDATION : Méthode Traditionnelle**

**Distribution Intensité (Hunter Allen)** :
- 10% Récupération
- 25% Endurance (56-75% FTP)
- **35% Tempo (76-91% FTP)** ← ZONE PRINCIPALE
- 15% FTP (94-105% FTP)
- 10% VO2 max (106-120% FTP)
- 5% Anaérobie + Neuromusculaire (>120% FTP)

**Avantages Méthode Traditionnelle** :
- Psychologiquement "do-able"
- Variété séances = plaisir préservé
- Maintien CTL élevé année complète
- Adaptation Masters 50+ (voir section dédiée)

---

## 2. SWEET-SPOT : ZONE OPTIMALE FTP

### 2.1 Définition Précise
**Sweet-Spot = 88-93% FTP**

**Caractéristiques** :
- Chevauche haut Tempo (88-91%) + bas FTP (91-93%)
- "Biggest bang for your training buck" (Hunter Allen)
- Plus haut effet entraînement pour améliorer FTP
- Psychologiquement soutenable durées prolongées
- Équilibre optimal stress physiologique / faisabilité mentale

### 2.2 Utilisation Sweet-Spot

**Pour l'IA - Recommandations** :
- Fondation des cycles développement FTP
- Volume majoritaire semaines progression (40-50% TSS total)
- Formats : 2x20min, 3x15min, 4x12min, continu 40-60min
- Découplage cardio-puissance <7.5% = validation qualité
- Priorité Sweet-Spot sur FTP strict pour sustainability

**Contexte Tempo (76-91% FTP)** :
- Complément Sweet-Spot
- Volume combiné Tempo + Sweet-Spot = 50-60% TSS hebdomadaire
- Base aérobie sans fatigue excessive

---

## 3. GESTION CTL - SPÉCIFICITÉ MASTERS 50+

### 3.1 Principe Fondamental CTL Masters

**Citation Hunter Allen (critique)** :
> "When you are 60 years young and your CTL drops from 80 down to 50, it's a long fight for months to get it back to 80!"

**Stratégie Masters 50+** :
- Maintenir CTL à **90% du maximum** en permanence
- Éviter variations importantes (>15 points)
- Pics 8 semaines = dernier 10% seulement
- Récupération lente âge 50+ = prévention baisse prioritaire

**Pour l'IA - Alertes Critiques** :
```
SI CTL baisse >10 points sur 4 semaines :
  → Alerte reconstruction base nécessaire
  → Prioriser volume Tempo/Sweet-Spot
  → Réduire intensité VO2/AC temporairement
  → Objectif : +2 à +3 points CTL/semaine pendant 6-8 semaines
```

### 3.2 CTL Cible selon FTP

**Référence empirique** :
- FTP 220W → CTL minimum 55-65
- FTP 240W → CTL minimum 65-75
- FTP 260W → CTL minimum 70-80

**Règle IA** :
```
SI FTP_cible > FTP_actuel :
  CTL_cible = CTL_actuel * (FTP_cible / FTP_actuel) * 1.15

Exemple :
  FTP 220W, CTL 42, Objectif 260W
  → CTL_cible = 42 * (260/220) * 1.15 = 57 MINIMUM
  → CTL_optimal = 70-75 pour FTP 260W stable
```

### 3.3 Volume TSS Hebdomadaire

**Reconstruction CTL** :
- Semaines charge : 350-400 TSS
- Semaines récup : 250-280 TSS
- Ratio 3:1 (3 charge, 1 récup)
- Progression : +2.5 points CTL/semaine soutenable

**Maintien CTL** :
- 320-380 TSS/semaine
- Ratio 2:1 ou 3:1 selon fatigue accumulée

---

## 4. WORK:REST RATIO MASTERS

### 4.1 Découverte Hunter Allen

**Formule secrète** (basée 500+ athlètes 65+ ans) :
- Plans Grandmasters 65+ intègrent ratios work:rest spécifiques
- Plans Masters 40+ : plus de repos que plans standards

**Pour l'IA - Règles Adaptation Âge** :
```
SI âge >= 65 ans :
  work:rest = ratio Grandmasters (non spécifié exactement)
  Fréquence récup semaines : chaque 2-3 semaines vs 3-4

SI âge 50-64 ans :
  work:rest = ratio Masters
  Semaine récup : tous les 3 semaines minimum

SI âge 40-49 ans :
  work:rest = ratio Masters léger
  Semaine récup : tous les 3-4 semaines

SI âge <40 ans ET non-élite :
  work:rest = standard
  Semaine récup : tous les 4 semaines
```

### 4.2 Exception Élite Masters

**Règle** :
```
SI âge <50 ans ET niveau = cat 1 / élite :
  → Utiliser plans standards (pas Masters)

SI âge >=50 ans QUEL QUE SOIT niveau :
  → Toujours plans Masters
```

---

## 5. TESTS ET POWER PROFILING

### 5.1 Tests Multiples Même Journée

**Protocole Hunter Allen validé** :
- **Ordre recommandé** : 5s sprint → 1min AC → 5min VO2 → 20min FTP
- Échauffement minimal entre tests (5-7min Z1)
- **Pré-requis** : TSB +10 minimum, sommeil >7h, fraîcheur optimale

**Pour l'IA - Planification Tests** :
```
JAMAIS bloquer semaine entière tests uniquement
JAMAIS FTP + VO2 + AC dans semaines successives séparées

Options valides :
  A) Tous tests même journée (post-affûtage)
  B) Test FTP seul semaine N, test 1min+5min semaine N+8
  C) Tests intégrés dans semaines entraînement normales
```

### 5.2 Test 1 Minute Anaérobie

**Protocole Critique** :

**Échauffement (20-30min MAX)** :
- 15-20min endurance (50-75% FTP)
- 3x1min drills cadence (110-120 rpm, ≤70% FTP wattage)
- 5min récup Z1
- **IMPORTANT** : Trop échauffement (>30min) = baisse performance

**Structure Test** :
- Durée réelle : 1min05 (capture meilleur 1min)
- Explosion maximale 0-30s (sprint out-of-saddle)
- Tenir coûte que coûte 30-60s (dégradation attendue)
- Terrain : Pente 5-9% idéale (aplatissement au sommet)

**Validation Qualité** :
- Courbe puissance = pic immédiat puis dégradation continue
- Si plateau puissance dernières 30s → test raté (pas assez fort début)

**Fréquence** : Toutes les 8 semaines (comme FTP)

**Utilisation 1min** :
- Marqueur fraîcheur/fatigue
- Capacité anaérobie comme indicateur surcharge
- Power profiling complet (5s, 1min, 5min, 20min)

### 5.3 Ratio AC / FTP

**Attendu** :
- 1min power = 1.6-1.7x FTP pour cycliste équilibré
- Exemple : FTP 220W → 1min attendu 350-375W

**Pour l'IA - Analyse Profil** :
```
Ratio_AC = Power_1min / FTP

SI Ratio_AC > 1.8 : Profil puncheur/sprinteur
SI Ratio_AC 1.5-1.8 : Profil équilibré
SI Ratio_AC < 1.5 : Profil rouleur/grimpeur

Recommandation entraînement :
  Profil puncheur → Focus FTP/VO2, maintien AC
  Profil équilibré → Distribution traditionnelle
  Profil rouleur → Focus AC/VO2, maintien FTP
```

---

## 6. CONCEPTS ANTI-PRODUCTIFS

### 6.1 "Junk Miles" - Définition et Évitement

**Junk Miles = Kilomètres sans objectif structuré**

**Caractéristiques** :
- Volume pour volume
- Aucune zone cible respectée
- Fatigue sans amélioration
- Illusion productivité

**Risque Masters 50+** :
- Récupération limitée gaspillée
- Creuse fatigue sans bénéfice
- Retarde séances qualité

**Pour l'IA - Prévention** :
```
TOUTE séance doit avoir objectif clair :
  - Zone(s) cible précise(s)
  - Durée/TSS planifié
  - Découplage attendu
  - Placement dans cycle

SI séance = "sortie libre" ou "selon envie" :
  → INTERDIRE sauf semaine récup totale
  → Remplacer par structure minimale (ex: Z2 strict)
```

### 6.2 Outdoor Discipline Failures

**Contexte utilisateur spécifique** :
- 4 échecs consécutifs outdoor (surcharge +13% à +38% IF)
- Indoor-only strategy validée

**Pour l'IA - Règle Générale** :
```
SI historique >2 échecs discipline outdoor sur zone cible :
  → Recommander indoor pour cette zone
  → Outdoor réservé Z1-Z2 uniquement
  → Retour outdoor après 2-3 mois discipline indoor validée
```

---

## 7. ADAPTATION ENTRAÎNEMENT - TIMING

### 7.1 Délai Adaptation Physiologique

**Principe fondamental Hunter Allen** :
> "Training Adaptation takes between 6 and 8 weeks"

**Pour l'IA - Règles Temporelles** :
```
Tout stimulus entraînement → Effet mesurable 6-8 semaines après

Implications planification :
  - Cycle minimum = 6 semaines
  - Test FTP après 6-8 semaines stimulation appropriée
  - Pic compétition = 8 semaines avant date cible
  - Changement méthode = attendre 6 semaines avant évaluation
```

### 7.2 Cycles Périodisation

**Structure recommandée** :
- 6 semaines développement capacité spécifique
- 1-2 semaines récup/transition
- Nouveau cycle 6 semaines sur capacité différente OU intensification même capacité

**Exemple séquence** :
```
Semaines 1-6 : Sweet-Spot focus (88-93% FTP)
Semaine 7 : Récup
Semaines 8-13 : FTP + VO2 mix
Semaine 14 : Récup
Semaines 15-20 : Peak / Affûtage
```

---

## 8. ZONE 2 - ADAPTATIONS PHYSIOLOGIQUES

### 8.1 Bénéfices Zone 2 (Endurance 56-75% FTP)

**Tableau 3.2 "Training and Racing with Power Meter"** :

**Adaptations** :
- ↑ Capillarisation
- ↑ Fonction mitochondriale
- ↑ Métabolisme lipides (fat oxidation)
- Conversion fibres Type IIx (glycolytiques rapides) → Type IIa (oxydatives rapides)

**Requis** :
- **Longues durées** (>2h idéalement)
- Intensité basse stricte
- Bénéfice = temps passé (volume > intensité)

### 8.2 Pour l'IA - Usage Zone 2

**Contexte budget temps 8-12h/semaine** :
- Zone 2 pure = 20-25% volume total maximum
- Combinaison Z2 + Tempo = plus efficient
- Séances longues weekend : inclure Z2 mais aussi Tempo/Sweet-Spot

**Si budget temps <10h/semaine** :
```
Prioriser Tempo/Sweet-Spot sur Z2 pure
Z2 réservée :
  - Échauffements/retours calme
  - Récupération active
  - Séances longues >2h30 (si disponibles)
```

---

## 9. INTERVALLES TO EXHAUSTION

### 9.1 Concept

**Section "Training and Racing with a Power Meter"** :
- Minimum 1x/semaine : intervalles poussés jusqu'à incapacité continuer
- Objectif : habituer mental à souffrance course
- Test réussite : "Race felt easier than training"

### 9.2 Pour l'IA - Application

**Format** :
```
1x/semaine : séance avec intervalles "jusqu'à échec"

Exemples :
  - Intervalles FTP jusqu'à incapacité maintenir puissance
  - VO2 répétitions jusqu'à impossibilité compléter intervalle
  - Sweet-Spot jusqu'à RPE >9/10

MAIS respecter :
  - TSB minimum pour séance
  - Pas si fatigue résiduelle
  - Placement stratégique dans semaine (pas veille repos)
```

---

## 10. NUTRITION - PRINCIPES

### 10.1 Citation Centrale

**"You can't out-exercise a bad diet"** - Hunter Allen

**Pour l'IA - Considérations** :
- Performance = entraînement + nutrition + lifestyle
- Calories élevées cyclistes = risque volume aliments faible qualité
- Énergie rapide (gels, barres) utile pendant séance ≠ alimentation quotidienne

### 10.2 Continuous Glucose Monitoring (CGM)

**Livre Hunter Allen (juin 2025)** :
- Stabilité glycémique > mesure unique matinale
- Patterns glucose pendant entraînement = clé performance
- **Potentiel futur** : Recommandations nutrition basées CGM

**Pour l'IA - Évolution Future** :
```
Si données CGM disponibles :
  → Adapter recommandations nutrition pré/pendant/post séance
  → Identifier patterns hypoglycémie effort
  → Optimiser timing glucides
```

---

## 11. RÈGLES DÉCISIONNELLES POUR L'IA

### 11.1 Construction Plan Hebdomadaire

**Algorithme Recommandé** :

```python
# Inputs
athlete_age = 54
FTP_current = 220
FTP_target = 260
CTL_current = 42
weekly_hours = 10  # Budget temps

# Calculs
CTL_target = 70  # Pour FTP 260W
CTL_deficit = CTL_target - CTL_current  # 28 points
weeks_reconstruction = CTL_deficit / 2.5  # ~11 semaines

# Phase actuelle
if CTL_current < (0.85 * CTL_target):  # Si <85% cible
    phase = "RECONSTRUCTION_BASE"
    distribution = {
        "Recovery": 0.10,
        "Endurance": 0.25,
        "Tempo": 0.35,      # FOCUS
        "Sweet-Spot": 0.20,  # FOCUS
        "FTP": 0.05,
        "VO2": 0.03,
        "AC_Neuro": 0.02
    }
    weekly_TSS = 350  # Semaine charge
    recovery_week_frequency = 3  # Tous les 3 semaines

elif CTL_current < CTL_target:
    phase = "CONSOLIDATION"
    distribution = {
        "Recovery": 0.10,
        "Endurance": 0.20,
        "Tempo": 0.25,
        "Sweet-Spot": 0.25,  # FOCUS
        "FTP": 0.10,
        "VO2": 0.08,
        "AC_Neuro": 0.02
    }
    weekly_TSS = 380
    recovery_week_frequency = 3

else:  # CTL >= target
    phase = "DEVELOPMENT_FTP"
    distribution = {
        "Recovery": 0.10,
        "Endurance": 0.20,
        "Tempo": 0.20,
        "Sweet-Spot": 0.20,
        "FTP": 0.15,         # FOCUS
        "VO2": 0.10,
        "AC_Neuro": 0.05
    }
    weekly_TSS = 380
    recovery_week_frequency = 4  # Moins fréquent si CTL solide

# Ajustement Masters 50+
if athlete_age >= 50:
    recovery_week_frequency = max(recovery_week_frequency - 1, 2)
    # Jamais >3 semaines charge consécutives Masters 50+
```

### 11.2 Validation Séance Individuelle

**Checklist Avant Prescription** :

```python
def validate_workout(workout, athlete_state):
    """
    Validation séance avant prescription
    """
    checks = []

    # 1. TSB approprié
    if workout.intensity == "VO2":
        if athlete_state.TSB < 5:
            checks.append("FAIL: TSB insuffisant pour VO2")

    if workout.intensity == "FTP":
        if athlete_state.TSB < -10:
            checks.append("FAIL: TSB trop négatif pour FTP")

    # 2. Sommeil
    if workout.intensity in ["VO2", "AC"]:
        if athlete_state.sleep_hours < 7:
            checks.append("FAIL: Sommeil insuffisant haute intensité")

    # 3. Historique récent
    high_intensity_last_48h = count_high_intensity_48h(athlete_state)
    if workout.intensity in ["VO2", "AC"] and high_intensity_last_48h > 0:
        checks.append("WARNING: Intensité élevée <48h")

    # 4. Découplage attendu
    if workout.duration_minutes > 60:
        if workout.intensity == "Sweet-Spot":
            expected_decoupling = 5.0  # <7.5% acceptable
        if workout.intensity == "FTP":
            expected_decoupling = 8.0  # <10% acceptable

    # 5. Placement semaine
    if workout.intensity == "Recovery" and workout.day == "Wednesday":
        checks.append("WARNING: Récup milieu semaine inhabituel")

    # 6. Volume cohérent
    if workout.TSS > (athlete_state.weekly_TSS_target * 0.30):
        checks.append("WARNING: Séance >30% TSS hebdo")

    return checks
```

### 11.3 Alerte Dérive Discipline

**Monitoring Outdoor** :

```python
def check_outdoor_discipline(workout_actual, workout_planned):
    """
    Détection échecs discipline outdoor
    """
    if workout_actual.environment == "outdoor":
        IF_deviation = (workout_actual.IF - workout_planned.IF) / workout_planned.IF

        if IF_deviation > 0.10:  # >10% surcharge
            discipline_failures_count += 1

            if discipline_failures_count >= 2:
                recommendation = "SWITCH_TO_INDOOR"
                message = f"Échec discipline outdoor détecté ({discipline_failures_count}x). Recommandation : indoor pour zones >{workout_planned.intensity}"

    return recommendation, message
```

---

## 12. MESSAGES TYPES POUR L'IA

### 12.1 CTL Trop Bas

**Template** :
```
⚠️ ALERTE CTL CRITIQUE

CTL actuel : {CTL_current}
CTL requis FTP {FTP_target}W : {CTL_required}
Déficit : {CTL_deficit} points

ANALYSE :
Baisse CTL de {CTL_drop} points détectée sur {weeks} semaines.
À {age} ans, récupération CTL lente (Hunter Allen : "long fight for months").

PLAN RECONSTRUCTION :
Phase 1 ({weeks_phase1} semaines) : {CTL_current} → {CTL_intermediate}
  - Volume : {TSS_weekly} TSS/semaine
  - Focus : Tempo (35%) + Sweet-Spot (20%)
  - Récup : Tous les {recovery_frequency} semaines

Délai réaliste objectif FTP {FTP_target}W : {total_weeks} semaines
```

### 12.2 Distribution Intensité Inadaptée

**Template** :
```
📊 RÉVISION DISTRIBUTION INTENSITÉ

Distribution actuelle détectée :
{current_distribution}

PROBLÈME :
{issue_description}

Distribution recommandée (Hunter Allen - Méthode Traditionnelle) :
- Tempo (76-91% FTP) : 35%
- Sweet-Spot (88-93% FTP) : Intégré dans 35% ci-dessus
- Endurance (56-75% FTP) : 25%
- FTP (94-105%) : 15%
- VO2 (106-120%) : 10%
- AC/Neuro (>120%) : 5%

JUSTIFICATION :
"{quote_hunter_allen}"
```

### 12.3 Test Mal Exécuté

**Template** :
```
❌ ANALYSE TEST 1 MINUTE

Résultat : {power_1min}W moyens

PROBLÈME DÉTECTÉ :
Courbe puissance montre {issue_description}

PROTOCOLE CORRECT (Hunter Allen) :
1. Échauffement 20min maximum (pas plus !)
2. Explosion maximale 0-30s (sprint out-saddle)
3. Tenir coûte que coûte 30-60s
4. Attendre dégradation puissance continue

VALIDATION QUALITÉ :
✓ Pic puissance immédiat
✓ Dégradation continue jusqu'à fin
✗ Plateau dernières 30s = pas assez fort début

Retest recommandé : {date_recommendation}
```

---

## 13. RÉFÉRENCES COMPLÈTES

### 13.1 Sources Primaires

**Livres** :
- "Training and Racing with a Power Meter" (Hunter Allen, Dr. Andrew Coggan)
- "Cutting-Edge Cycling" (Hunter Allen, Stephen Cheung PhD)
- "Training and Competing with a Continuous Glucose Monitor" (Hunter Allen, 2025)

**Articles Web** :
- "The 1 Minute Test - How you should do it" (shoppeaks.com)
- "Why Polarized training is NOT for you!" (shoppeaks.com)

### 13.2 Concepts Propriétaires

**Peaks Coaching Group** :
- Performance Management Chart (PMC)
- Work:Rest Ratio Masters/Grandmasters (formule secrète 500+ athlètes)
- Sweet-Spot training emphasis
- Traditional Method intensity distribution

---

## 14. INTÉGRATION PROMPTS SYSTÈME

### 14.1 Section À Ajouter - Prompt Principal

```markdown
## MÉTHODOLOGIE ENTRAÎNEMENT (PEAKS COACHING GROUP / HUNTER ALLEN)

### Principes Fondamentaux
- Méthode Traditionnelle (distribution équilibrée) > Polarisée
- Sweet-Spot (88-93% FTP) = zone optimale développement FTP
- CTL Masters 50+ : maintenir 90% max, éviter drops >10 points
- Testing = Training : tests intégrables dans semaines normales
- Adaptation physiologique = 6-8 semaines délai

### Distribution Intensité Recommandée
{Insérer section 1.2}

### Gestion CTL Âge 50+
{Insérer section 3}

### Validation Séances
{Insérer sections 11.2 et 6.1}
```

### 14.2 Section À Ajouter - Prompt Analyse

```markdown
## ANALYSE MÉTRIQUES

### CTL Warning Thresholds
- Alert si drop >10 points en 4 semaines
- Alert si CTL < 0.85 * CTL_required_for_FTP_target
- Recommandation reconstruction si détecté

### Test Quality Validation
{Insérer section 5.2}

### Discipline Monitoring
{Insérer section 11.3}
```

### 14.3 Section À Ajouter - Prompt Recommandations

```markdown
## RECOMMANDATIONS ENTRAÎNEMENT

### Algorithme Sélection Phase
{Insérer section 11.1}

### Templates Semaines Type
{Créer à partir principes sections 1-3}

### Messages Alertes
{Insérer section 12}
```

---

## 15. CHECKLIST VALIDATION IA

**Avant déploiement modifications prompts, vérifier** :

- [ ] Distribution intensité respecte 35% Tempo/Sweet-Spot
- [ ] CTL monitoring intégré avec alertes âge 50+
- [ ] Tests FTP/VO2/AC ne bloquent jamais semaine entière seuls
- [ ] Junk miles impossible (toute séance = objectif défini)
- [ ] Work:rest ratio Masters appliqué (récup tous les 3 semaines max)
- [ ] Sweet-Spot priorisé sur FTP strict développement base
- [ ] Délai adaptation 6-8 semaines respecté cycles
- [ ] Validation découplage <7.5% intégrée
- [ ] Budget temps 8-12h optimisé (pas formats 3-4h Z2 pure)
- [ ] Messages utilisent quotes Hunter Allen quand pertinent

---

**FIN DOCUMENT DE RÉFÉRENCE**

*Ce document doit être utilisé pour enrichir les prompts système de l'IA prescriptrice d'entraînement. Toute recommandation générée doit être validée contre ces principes méthodologiques.*
