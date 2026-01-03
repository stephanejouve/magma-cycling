# Adaptations Protocoles S071

## Ajustements Suite Enseignements

### 1. Format Double Séance Endurance
**Ajout nouveau protocole** :

**Prérequis exécution** :
- TSB minimum : +7
- Sommeil veille : >6h
- Pas d'intensité >85% FTP dans 48h précédentes

**Structure validée** :
- Session 1 (matin/après-midi) : Endurance 75-80min, TSS 50-55, IF 0.65-0.66
- Session 2 (soir) : Technique cadence 40min, TSS 20-25, IF 0.56-0.58
- Intervalle minimum : 4h entre sessions
- Charge cumulée : TSS 70-80, durée totale 115-120min

**Fréquence** : 1×/semaine maximum

**Validation** : S071-06A+06B (TSS 77, TSB +8 maintenu post-exécution)

---

### 2. Template Technique Cadence
**Version obsolète V000** : Supprimée (structure défectueuse, bloc non répété)

**Version opérationnelle V001** :
```
Warmup: 12m Ramp 50-65% 85rpm
Main set 5×:
- 3m 65% 60rpm
- 2m 60% 100rpm
Cooldown: 10m Ramp 65-50% 85rpm
Total: 64min | TSS: 35-40 | IF: 0.56-0.58
```

**Application** :
- Récupération active standalone : TSS 35-40
- Post-endurance double séance : TSS 20-25 (réduction intensité si fatigue)

**Point surveillance** : RPE subjectif élevé (6/10) malgré métriques objectives conformes, possiblement lié sommeil déficitaire.

---

### 3. Protocole Hydratation Compensatoire
**Nouveau protocole exceptionnel** :

**Contexte application** :
- Post-alcool (repas festif, événement social)
- Alimentation enrichie/déséquilibrée J-1
- Hydratation sous-optimale détectée

**Méthode** :
- Supplémentation isotonique renforcée (quantification précise à documenter)
- Hydratation inter-sessions optimisée (fréquence augmentée)
- Nutrition pré-séance ajustée (glucides complexes privilégiés)

**Validation** : S071-06A+06B (double séance qualité maintenue, découplage 1.5%/-3.2%)

**Limites** :
- Protocole non-reproductible systématiquement (contexte exceptionnel)
- Quantification précise apports manquante (à standardiser si réplication)
- Impact long-terme non documenté (unique occurrence S071)

---

## Nouveaux Seuils/Critères Techniques

### 1. Découplage Négatif Monitoring
**Seuil alerte** : Découplage <-3% reproductible sur 3+ séances

**Critères investigation** :
- Vérifier données FC/puissance brutes Intervals.icu web
- Comparer calibration capteurs (FC thoracique vs optique)
- Documenter pattern selon format séance (endurance, technique, critérium)

**Hypothèses** :
- Indicateur amélioration efficacité cardiovasculaire Z1-Z2 (HRRc)
- Artefact calibration FC ou échauffement progressif
- Adaptation post-maladie (phase récupération S027-S029)

**Action S072** : Validation reproductibilité pattern, décision diagnostic selon résultats.

---

### 2. TSB Minimum Double Séance
**Ancien critère** : Non spécifié

**Nouveau seuil** : TSB minimum +7 validé

**Justification** : S071-06A+06B exécutées TSB +8, charge 77 TSS tolérée sans dégradation post-séance.

**Marge sécurité** : TSB +7 conservateur, progression possible vers +5 si sommeil >7h et validation S072.

---

### 3. Cadence Critérium Cible
**Ancien critère** : Non spécifié format critérium

**Nouveau seuil** : Cadence minimum 85rpm relances

**Justification** : Glasgow Crit cadence 74rpm associée abandon prématuré (-7min) et fatigue neuromusculaire suggérée.

**Application** : Séances spécifiques accélérations haute cadence (90-95rpm) si format critérium maintenu.

---

## Modifications Hydratation/Nutrition

### 1. Protocole Isotonique Compensatoire
**Ajout protocole exceptionnel** :
- Application : Post-alcool ou alimentation festive J-1
- Méthode : Supplémentation isotonique renforcée (quantités à standardiser)
- Timing : Hydratation inter-sessions optimisée si double séance
- Validation : S071-06A+06B qualité maintenue

**Limite** : Quantification précise manquante, à documenter si réplication.

---

### 2. Nutrition Pré-Double Séance
**Nouveau critère** : Glucides complexes privilégiés si alimentation enrichie J-1

**Application** :
- Session 1 (matin) : Petit-déjeuner léger glucides lents (flocons avoine, pain complet)
- Inter-sessions : Hydratation renforcée + collation légère si intervalle >6h
- Session 2 (soir) : Éviter apports lourds 2h pré-séance

**Validation** : S071-06A+06B malgré repas festif J-1.

---

## Adaptations Matériel/Discipline

### 1. Capteur Puissance Zwift
**Problème identifié** : S071-01 données puissance brutes manquantes

**Action** : Vérifier calibration pré-séance systématique

**Protocole ajouté** :
- Spin down capteur avant chaque séance
- Validation données puissance instantanée <5min échauffement
- Backup FC si défaillance technique détectée

---

### 2. Discipline Intensité Critérium
**Problème identifié** : Glasgow Crit abandon prématuré (-7min, -15.6% durée)

**Nouveau critère** : Respecter durée minimale 45min format critérium

**Adaptations** :
- Validation parcours Zwift complet avant départ (distance cible 18-20km)
- Cadence relances 85-90rpm vs libre
- Privilégier qualité relances vs volume si contrainte temps

**Alternative** : Séances spécifiques accélérations haute cadence 1×/semaine si critérium maintenu.

---

## Exclusions/Interdictions Mises à Jour

### 1. Template S071-03a-TechniqueCadence-V000
**Statut** : Obsolète, exclu du catalogue

**Raison** : Structure défectueuse (bloc principal non répété 5×)

**Remplacement** : Version V001 opérationnelle exclusivement

---

### 2. Format Récupération "Libre" Non-Structuré
**Problème identifié** : S071-02 intensité dépassée (IF 0.65 vs 0.50 cible, TSS +72%)

**Nouveau critère** : Format récupération strictement structuré (zones fixes) vs libre

**Application** :
- Récupération active : IF max 0.58, TSS max 30
- Structure imposée : SteadyState ou Ramp progressif uniquement
- Variabilité puissance limitée : VI <1.10

**Justification** : Éviter dérive intensité involontaire sur séances récupération.

---

## Surveillance Renforcée Identifiée

### 1. Sommeil (Priorité Critique)
**Observation S071** : 0.0h renseigné systématiquement

**Impact** : RPE subjectif 6/10 vs métriques objectives conformes (S071-03)

**Actions requises** :
1. Corriger intégration données Withings immédiatement
2. Validation manuelle sommeil >7h avant Sweet-Spot S072
3. Monitoring HRV si données Withings disponibles

**Seuil alerte** : Sommeil <6h = VETO VO2/Sweet-Spot, adaptation endurance Z2 uniquement.

---

### 2. Poids Variation Rapide
**Observation S071** : +1.3kg en 6 jours (84.6kg → 85.9kg)

**Facteurs** : Hydratation renforcée, alimentation festive, rétention isotonique

**Actions requises** :
1. Monitoring quotidien poids S072 (stabilisation attendue)
2. Distinction rétention eau temporaire vs masse grasse (tendance 3-5 jours)
3. Ajustement apports si variation >+2kg maintenue >7 jours

**Seuil alerte** : +2kg maintenu >7 jours = investigation composition corporelle (Withings).

---

### 3. Découplage Négatif Reproductibilité
**Observation S071** : 3 séances/8 découplage <-3%

**Actions requises** :
1. Vérification données FC/puissance brutes Intervals.icu web
2. Comparaison calibration capteurs (FC thoracique vs optique si disponible)
3. Documentation pattern S072 (séances endurance >60min)

**Seuil validation** : Si découplage <-3% sur 3+ séances S072, considérer indicateur amélioration efficacité cardiovasculaire validé.

---

### 4. Cadence Critérium
**Observation S071** : 74rpm Glasgow Crit (vs 84-86rpm standard)

**Actions requises** :
1. Séances spécifiques accélérations haute cadence 1×/semaine si critérium maintenu S072
2. Monitoring cadence relances 85-90rpm systématique
3. Validation pattern fatigue neuromusculaire si cadence <80rpm reproductible

**Seuil alerte** : Cadence <80rpm reproductible format critérium = exclusion temporaire format explosif, focus endurance Z2.

---
