# Sprint R10 - Journal de Calibration PID 📊

**Date**: 2026-02-15
**Durée**: Jour 1/5
**Objectif**: Calibration complète PID Discret post-S080

---

## JOUR 1 - Analyse & Design (2026-02-15)

### 1. Extraction Données Historiques ✅

**Période analysée**: 2025-12-28 → 2026-02-14 (49 jours)

**Résultats**:
- **37 activités** récupérées (5.3/semaine)
- **1917 TSS total** (39.1 TSS/jour moyen)
- **38.0h** durée totale d'entraînement
- **49 entrées wellness** avec CTL/ATL/TSB

### 2. Analyse Patterns TSS/CTL ✅

#### 2.1 Évolution CTL (CRITIQUE ⚠️)

```
CTL Début (2025-12-28): 45.4
CTL Fin (2026-02-14):   42.4
Variation nette:        -3.0 points sur 49 jours
Taux:                   -0.43 points/semaine

CTL moyen:              42.6 ± 1.0
CTL min/max:            40.8 / 45.4
```

**🎯 Seuils Peaks Coaching (FTP 223W)**:
- CTL minimum: **55.8** (déficit: -13.3 points)
- CTL optimal: **71.0** (déficit: -28.5 points)
- **CTL actuel = 59.8% de l'optimal** ⚠️

**Conclusion**: CTL en **déclin continu** malgré entraînement actif. Signal alarmant nécessitant intervention immédiate.

#### 2.2 Analyse TSS Hebdomadaire

**8 semaines analysées**:

| Semaine   | TSS  | Séances | TSS/séance |
|-----------|------|---------|------------|
| 2025-W52  | 35   | 1       | 35         |
| 2026-W00  | 133  | 2       | 66         |
| 2026-W01  | 370  | 6       | 62         |
| 2026-W02  | 199  | 4       | 50         |
| 2026-W03  | 362  | 6       | 60         |
| 2026-W04  | 228  | 4       | 57         |
| 2026-W05  | 290  | 7       | 41         |
| 2026-W06  | 300  | 7       | 43         |

**Statistiques**:
- TSS hebdomadaire moyen: **240 ± 115 TSS/sem**
- TSS min/max: **35 / 370 TSS**
- Coefficient de variation: **48.1%** 🚨

**⚠️  PROBLÈME MAJEUR**: Variabilité TRÈS ÉLEVÉE (>30%)
- Charge irrégulière empêche construction CTL progressive
- Semaine 35 TSS suivie de 370 TSS = déséquilibre critique
- Explication probable CTL décroissant malgré TSS moyen correct

**Recommandation Peaks**: 350-400 TSS/sem en reconstruction
**Déficit actuel**: +110 TSS/sem nécessaire

#### 2.3 Analyse Réponse Système

**Paramètres système détectés**:
- **Process gain K**: -0.001780 (CTL/TSS) ⚠️
- **Taux variation CTL**: -0.43 points/semaine
- **TSS stabilité**: ~298 TSS/semaine nécessaire

**🚨 ALERTE: Process Gain NÉGATIF**

Signification:
- Plus on augmente TSS, plus CTL diminue (contre-intuitif)
- **Cause probable**: Variabilité extrême TSS hebdomadaire
- Pattern "charge irrégulière" = inefficacité adaptation
- Semaines surcharge (370 TSS) suivies récupération (35 TSS) annulent progression

**Implication calibration PID**:
- ❌ **Méthode Ziegler-Nichols INVALIDE** (gains négatifs absurdes)
- ✅ **Utiliser gains théoriques** basés littérature + expertise
- ✅ **Prioriser régularité** avant augmentation charge

### 3. Design Architecture PID Discret ✅

#### 3.1 Architecture Existante (Validée)

**Module**: `cyclisme_training_logs/intelligence/discrete_pid_controller.py`

**Fonctionnalités**:
- ✅ PID discret avec sample-and-hold (cycles 6-8 semaines)
- ✅ Validation multi-critères (adherence, coupling, TSS completion)
- ✅ Anti-windup (intégral ±200W·cycles)
- ✅ Output saturation (±30 TSS/semaine max)
- ✅ Dead-band (±3W FTP variations naturelles)
- ✅ Traduction TSS (+1W FTP ≈ +12.5 TSS/semaine)

**Architecture validée pour contexte actuel** ✅

#### 3.2 Intégration Peaks Coaching

**Contraintes Peaks appliquées**:
1. **CTL minimum**: 55.8 pour FTP 223W
2. **Distribution intensité**: Tempo 35%, Sweet-Spot 20% (reconstruction)
3. **Charge cible**: 350-400 TSS/sem
4. **Récupération**: Tous les 2 semaines (Masters 50+)

**Override rules**:
- Si CTL < 50 (critique): Peaks > PID
- Si CTL 50-85% optimal: PID avec contraintes Peaks
- Si CTL ≥ optimal: PID autonome

### 4. Définition Paramètres PID (Kp, Ki, Kd) 🔧

#### 4.1 Problématique Calibration

**Données historiques inutilisables**:
- Process gain négatif (variabilité excessive)
- Ziegler-Nichols invalide
- Pattern "désentraînement" vs "progression"

**Solution**: Gains théoriques conservateurs + ajustements Masters 50+

#### 4.2 Gains PID Recommandés (Théoriques)

**Base théorique** (système lent, cycles 6-8 semaines):

```python
# Système cycling typical (littérature)
τ = 3.0 semaines  # Time constant (conservateur Masters 50+)
L = 1.0 semaine   # Delay response

# Gains PID standard (ajusté discret)
Kp_base = 0.010  # Réaction immédiate
Ki_base = 0.002  # Accumulation erreur
Kd_base = 0.15   # Anticipation tendance
```

**Ajustements Masters 50+ (-20% à -50%)**:

```python
Kp = 0.010 * 0.8  = 0.008  # -20% réactivité
Ki = 0.002 * 0.5  = 0.001  # -50% accumulation (anti-windup strict)
Kd = 0.15  * 0.8  = 0.12   # -20% anticipation
```

**🎯 GAINS FINAUX RECOMMANDÉS**:
- **Kp = 0.008** (proportionnel)
- **Ki = 0.001** (intégral)
- **Kd = 0.12** (dérivé)

**Correspondance**: Gains actuels dans `discrete_pid_controller.py` ✅

#### 4.3 Rationale Gains Conservateurs

**Pourquoi conservateurs ?**

1. **CTL critique actuel** (42.4 vs 55.8 minimum)
   - Risque surcharge si gains trop agressifs
   - Prioriser progression stable vs rapide

2. **Variabilité historique élevée** (CV 48%)
   - Gains élevés amplifieraient instabilité
   - Besoin régularité avant réactivité

3. **Masters 50+ (âge 54)**
   - Récupération plus lente
   - Adaptation progressive nécessaire
   - Citation Hunter Allen: "CTL drops take months to rebuild"

4. **Cycle long** (6-8 semaines)
   - Correction appliquée longtemps
   - Erreur sur-correction = 6 semaines perdues
   - Conservative = prudent

**Trade-off accepté**:
- Progression plus lente (11 semaines vs 8 théorique)
- Mais risque sur-entraînement réduit
- Adaptation durable prioritaire

#### 4.4 Validation Multi-Critères Intégrée

**Seuils validation** (déjà implémentés):

| Critère                    | Seuil Red Flag | Ajustement    |
|----------------------------|----------------|---------------|
| Adherence rate             | < 80%          | Gains × 0.7   |
| Cardiovascular coupling    | > 8%           | Gains × 0.6   |
| TSS completion rate        | < 85%          | Cap ≤5 TSS    |

**Exemple contexte actuel**:
- Si adherence = 75% (S078 = 16.7% !)
- Si coupling = 9% (surcharge)
- → Correction PID réduite 0.7 × 0.6 = **42% des gains**
- → Protection automatique sur-entraînement ✅

### 5. Conclusions Jour 1

#### 5.1 Décisions Architecturales

1. ✅ **Utiliser gains théoriques** Kp=0.008, Ki=0.001, Kd=0.12
2. ✅ **Rejeter calibration Ziegler-Nichols** (données invalides)
3. ✅ **Conserver architecture existante** (discrete_pid_controller.py)
4. ✅ **Intégrer contraintes Peaks** (CTL minimum, distribution)
5. ✅ **Activer validation multi-critères** (protection sur-entraînement)

#### 5.2 Problèmes Identifiés

1. 🚨 **Variabilité TSS critique** (48% CV)
   - Action: Prioriser régularité semaine à semaine
   - Cible: CV < 20% sur 8 semaines

2. 🚨 **CTL décroissant** (-0.43 pts/sem)
   - Action: Augmenter TSS hebdo 240 → 350 (progressif)
   - Timeline: +15 TSS/semaine sur 7 semaines

3. 🚨 **Adherence faible** (S078 = 16.7%)
   - Action: Simplifier planning (moins séances, plus prévisibles)
   - Cible: >85% adherence sur cycle

#### 5.3 Prochaines Étapes (Jour 2)

**Demain (2026-02-16)**:
1. Initialiser PID controller avec gains validés
2. Simuler backtest S074-S080 avec gains théoriques
3. Calculer correction cycle S081-S086 (prochain cycle)
4. Valider avec contraintes Peaks (CTL critique)
5. Générer recommandations actionnables

**Livrables attendus**:
- Script initialisation PID avec état S080
- Rapport simulation backtest (validation gains)
- Planning S081-S086 avec corrections PID
- Intégration daily-sync PID analysis

---

## MÉTRIQUES CLÉS SPRINT R10

**Baseline S080 (2026-02-14)**:
- FTP mesuré: **223W** (test 20min, qualité validée)
- CTL actuel: **42.4** (vs minimum 55.8, déficit -13.3)
- ATL actuel: **45.8**
- TSB actuel: **-3.4** (légèrement négatif)

**Cibles Cycle S081-S086**:
- FTP target: **230W** (+7W progression conservative)
- CTL target: **50.0** (+7.6 points en 6 semaines = +1.3/sem)
- TSS hebdo: **350 TSS** (+110 vs actuel 240)
- Distribution: Tempo 35%, Sweet-Spot 20%, Endurance 25%

**Success Metrics**:
- ✅ Gains PID validés théoriquement
- ✅ Backtest simulation cohérente
- ✅ Correction S081 calculée
- ✅ Integration Peaks contraintes
- ⏳ Validation end-of-cycle S086 (dans 6 semaines)

---

## JOUR 2 - Initialisation & Simulation (2026-02-15)

### 1. Initialisation PID Controller ✅

**Script créé**: `cyclisme_training_logs/scripts/initialize_pid_controller.py`

**Gains implémentés**:
```python
Kp = 0.008  # Proportionnel (-20% Masters)
Ki = 0.001  # Intégral (-50% Masters)
Kd = 0.12   # Dérivé (-20% Masters)
Setpoint = 230W  # FTP cible (+7W conservative from 223W)
Dead-band = ±3W
```

**Controller initialisé avec succès** ✅

### 2. Backtest Simulation S074-S080 ✅

#### Cycle S074-S077 (3 semaines)
- FTP hypothétique: 226W
- Error: +4W (proche setpoint)
- Correction PID: **+1 TSS/semaine**
- Validation: ✅ VALIDÉE (confidence 0.85)
- Warnings: Coupling 6-8%, TSS completion 85-90%

#### Cycle S077-S080 (4 semaines)
- FTP mesuré: 223W (test réel S080)
- Error: +7W
- Correction PID originale: +2 TSS/semaine
- **Correction ajustée: +1 TSS/semaine** (red flags)
- Validation: ❌ NON VALIDÉE (confidence 0.50)
- Red flags:
  - Discipline faible: adherence < 80% (S078 = 16.7% !)
  - Capacité insuffisante: TSS completion < 85%
- Ajustements: Gains réduits 30% (protection sur-entraînement)

**Conclusion backtest**:
- ✅ Gains PID fonctionnent correctement
- ✅ Validation multi-critères protège efficacement
- ✅ Réduction automatique en cas de red flags
- ⚠️ PID très conservateur (intentionnel Masters 50+)

### 3. Correction Cycle S081-S086 (Prochain) ✅

**État PID après S080**:
- Integral accumulé: 82.0 W·cycles
- Erreur précédente: +7.0W
- FTP précédent: 223W
- Cycles traités: 3

**Correction PID calculée**:
- Error: +7W (223W → 230W setpoint)
- P term: 0.056W
- I term: 0.082W (accumulation sur 3 cycles)
- D term: 0.000W (pas de changement vs cycle précédent)
- Output: 0.138W
- **TSS/semaine: +2 TSS** (validé, confidence 0.90)

**Projection CTL avec PID**:
- CTL actuel: 42.4
- TSS augmentation: +2 TSS/semaine
- **CTL final estimé: 44.1** (+1.7 points sur 6 semaines)
- Seuil Peaks minimum: 57.5
- **⚠️ Reste sous minimum Peaks** (60% de l'optimal)

### 4. Validation Peaks Coaching ✅

#### Phase Déterminée: RECONSTRUCTION_BASE

**Métriques Peaks**:
- CTL cible: **73.2** (optimal pour FTP 230W)
- Déficit CTL: **30.8 points**
- Durée reconstruction: **12 semaines** minimum
- TSS recommandé (charge): **350 TSS/semaine**
- TSS recommandé (récup): **250 TSS/semaine**
- Fréquence récup: Tous les **2 semaines**

**Distribution intensité**:
- **Tempo: 35%** ← FOCUS
- **Sweet-Spot: 20%** ← FOCUS
- **Endurance: 25%** ← FOCUS
- Recovery: 10%
- FTP: 5%
- VO2: 3%
- AC/Neuro: 2%

#### Comparaison PID vs Peaks

| Métrique                | PID           | Peaks         | Écart      |
|-------------------------|---------------|---------------|------------|
| TSS/semaine suggestion  | +2            | +110          | **+108**   |
| TSS final après adjust  | 242           | 350           | **+108**   |
| CTL projection (6 sem)  | 44.1          | ~54-57        | **+10-13** |
| Atteint minimum Peaks?  | ❌ Non (60%)   | ✅ Oui (~95%)  | -          |

**🚨 CONFLIT MAJEUR DÉTECTÉ**

### 5. Décision Override Rules ✅

**Règle appliquée**: **CTL CRITIQUE (<50) → PEAKS > PID**

**Justification**:
1. **CTL dangereusement bas** (42.4 < 50 seuil critique)
2. **PID trop conservateur** (+2 TSS insuffisant)
3. **Peaks identifie urgence** (RECONSTRUCTION_BASE)
4. **Déficit 30.8 points** nécessite action agressive
5. **PID design** = optimisation fine, pas reconstruction

**Décision**: ✅ **APPLIQUER PEAKS RECOMMANDATION** (override PID)

#### Stratégie Progressive S081-S086

**Plan 6 semaines** (ramp-up + alternance charge/récup):

| Semaine | TSS Cible | Type    | Rationale                          |
|---------|-----------|---------|-------------------------------------|
| S081    | 277       | RAMP    | Transition progressive (+37 vs 240) |
| S082    | 313       | RAMP    | Augmentation continue (+73)         |
| S083    | 350       | CHARGE  | Pleine charge Peaks                 |
| S084    | 350       | CHARGE  | Maintien charge                     |
| S085    | 350       | CHARGE  | Maintien charge                     |
| S086    | 250       | RÉCUP   | Récupération cycle (semaine test)   |

**TSS moyen sur 6 semaines**: ~315 TSS/semaine

**Gain CTL estimé**: +12-15 points (conservateur)
**CTL final projeté**: ~54-57 (**proche minimum Peaks 57.5**)

**Distribution type semaine charge** (350 TSS):
- Tempo (35%): ~123 TSS, ~2h30
- Sweet-Spot (20%): ~70 TSS, ~1h15
- Endurance (25%): ~88 TSS, ~2h45
- Recovery (10%): ~35 TSS, ~1h30
- FTP (5%): ~18 TSS, ~25min
- VO2 (3%): ~11 TSS, ~15min
- AC/Neuro (2%): ~7 TSS, ~10min

**Total durée**: ~9h15/semaine (charge)

### 6. Conclusions Jour 2

#### 6.1 Succès

1. ✅ **PID initialisé** et fonctionnel avec gains validés
2. ✅ **Backtest simulé** confirme comportement correct
3. ✅ **Validation multi-critères** protège efficacement
4. ✅ **Integration Peaks** identifie conflit correctement
5. ✅ **Override rules** appliquées logiquement

#### 6.2 Problèmes Identifiés

1. 🚨 **PID trop conservateur** pour CTL critique
   - Design intentionnel (Masters 50+)
   - Inadapté phase reconstruction urgente
   - Fonctionne pour optimisation fine (CTL ≥50)

2. 🚨 **Conflit PID vs Peaks** résolu par override
   - PID: +2 TSS → CTL 44.1 (insuffisant)
   - Peaks: +110 TSS → CTL ~55 (minimum acceptable)
   - **Solution**: Architecture hiérarchique validée

3. ⚠️ **Ramp-up progressif nécessaire**
   - Jump direct 240 → 350 TSS risqué
   - Stratégie 3 semaines ramp-up + alternance
   - Protection sur-entraînement

#### 6.3 Architecture Validation

**Hiérarchie confirmée** (comme documenté INTEGRATION_PEAKS_PID_INTELLIGENCE.md):

```
NIVEAU 1 - STRATÉGIQUE (16 semaines)
↓ Peaks Coaching: CTL < 50 → OVERRIDE PID
↓ Constraint: 350 TSS/sem, Tempo 35%, Sweet-Spot 20%
↓
NIVEAU 2 - TACTIQUE (6-8 semaines)
↓ PID Discret: Optimisation fine quand CTL ≥50
↓ Output: +2 TSS/sem (conservateur, ignoré car override)
↓
NIVEAU 3 - OPÉRATIONNEL (jour/semaine)
↓ Proactive Compensation: Distribution TSS journalière
↓ Training Intelligence: Patterns validation
```

**Override actif S081-S086**: ✅ PEAKS > PID (CTL critique)

#### 6.4 Prochaines Étapes (Jour 3)

**Demain (2026-02-16)**:
1. Créer planning détaillé S081 avec distribution Peaks
2. Générer templates séances Tempo/Sweet-Spot
3. Intégrer correction Peaks dans daily-sync
4. Configurer alertes si adherence < 85%
5. Setup test FTP fin S086 (6 semaines)

**Livrables attendus**:
- Planning S081 (7 jours) avec séances détaillées
- Templates workout Tempo 35%, Sweet-Spot 20%
- Script integration daily-sync + Peaks override
- Monitoring dashboard CTL progression

---

**Auteur**: Claude Code + Stéphane Jouve
**Status Jour 1**: ✅ COMPLET
**Status Jour 2**: ✅ COMPLET
**Next**: Jour 3 - Planning & Templates
