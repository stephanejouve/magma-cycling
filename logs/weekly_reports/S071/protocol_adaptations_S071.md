# Adaptations Protocoles S071

## 1. Double Séance Weekend

### Ajustement
**Nouveau protocole validé** : Autorisation double endurance samedi sous conditions strictes.

### Justification Data
- S071-06A + S071-06B : 77 TSS total, TSB maintenu +8
- Découplages excellents (1.5% / -3.2%)
- RPE constant 4/10, aucune dégradation performance

### Critères d'Application
```
IF (TSB_vendredi_soir ≥ +8) AND (Sommeil_nuit ≥ 7h) THEN
  AUTORISER Double_Séance_Samedi
    Session_AM: Endurance 60-75min (50-60 TSS)
    Session_PM: Technique/Récup 40-50min (20-25 TSS)
    TSS_Total: 70-85
ELSE
  Séance_Unique 90min standard
END IF
```

### Exclusions
- ❌ Si TSB <+8 vendredi soir
- ❌ Si sommeil <7h validé Withings
- ❌ Si séance AM découplage >7.5% (fatigue détectée)
- ❌ Dimanche (repos protocole maintenu absolu)

### Fréquence
- Maximum 2×/mois initialement
- Progression possible 1×/semaine si validations continues 3+ occurrences

---

## 2. Cadence Formats Explosifs

### Seuil Critique Identifié
**Nouveau critère validation cadence** : 
- Endurance Z1-Z2 : 84-87rpm ✅ (maintenu)
- **Explosif/Critérium : ≥85rpm obligatoire** (nouveau seuil)

### Justification Data
Glasgow Crit : 74rpm = échec technique (-13% vs standard), abandon prématuré 38min vs 45min.

### Protocole Correction
**Séances spécifiques hebdomadaires S072+** :
```
Cadence Explosif (45min, TSS ~35)
Warmup
- 10m Ramp 50-65% 85rpm

Main set 6x
- 30s 120% 95-100rpm FOCUS CADENCE
- 90s 60% 85rpm récup

Cooldown
- 8m 60% 85rpm
```

**Fréquence** : 1×/semaine (mardi ou jeudi) jusqu'à validation maintien ≥85rpm en critérium.

**Test validation** : Glasgow Crit repeat dans 4 semaines, objectif cadence ≥85rpm sur durée complète 45min.

### Surveillance Renforcée
Tout format explosif/HIIT :
- Cadence ≥85rpm obligatoire (consigne explicite workout)
- Si chute <80rpm en cours séance : Arrêt immédiat, analyse cause
- Documentation cadence moyenne post-séance systématique

---

## 3. Hydratation Contexte Festif

### Nouveau Protocole Occasionnel
**Hydratation renforcée période festive** :
- Volume : 600ml/h (+20% vs standard 500ml/h)
- Supplémentation : Comprimé isotonique si alcool/repas arrosé <6h pré-séance
- Application : 2ème séance journée prioritaire si double endurance

### Justification Data
S071-06A/06B : Performance maintenue malgré "repas arrosé, alcool" grâce supplémentation.

### Limites d'Usage
- **Fréquence max** : 1×/mois (périodes fêtes/événements sociaux)
- **Non-standard** : Protocole 500ml/h reste référence hors contexte festif
- **Condition** : TSB ≥+8 obligatoire si contexte sub-optimal

### Exclusion
- ❌ Ne pas utiliser comme compensation hydratation insuffisante récurrente
- ❌ Pas de double séance si alcool + sommeil <6h cumulés

---

## 4. Découplage Cardiovasculaire

### Seuils Mis à Jour
**Ancien protocole** :
- <5% : Excellent
- 5-7.5% : Acceptable
- >7.5% : Dérive

**Nouveau protocole** :
- **<3% : Exceptionnel** (nouveau palier identifié S071)
- 3-7.5% : Excellent/Acceptable (maintenu)
- >7.5% : Dérive (maintenu)
- **Négatif <-5% : Investigation technique** (nouveau seuil)

### Justification Data
- S071-04 : 1.0%, S071-06A : 1.5%, S071-03 : 3.0% → Palier exceptionnel validé
- S071-06B : -3.2%, S071-02 : -15.6% → Découplages négatifs inhabituels nécessitent vérification

### Actions Associées
**Si découplage <3%** : 
- Documenter séance comme référence technique
- Pattern validé excellente base aérobie

**Si découplage négatif <-5%** :
- Vérifier calibration capteur FC (sangle contact/batterie)
- Vérifier calibration capteur puissance (zero offset Wahoo)
- Comparer données Zwift vs Wahoo (dual recording)
- Si reproductible 3× : Accepter comme pattern physiologique rare, documenter

---

## 5. Gestion Erreurs Workout

### Protocole Réactivité Renforcé
**Détection anomalie structure** :
1. Arrêt immédiat si structure workout incohérente détectée
2. Vérification template Intervals.icu
3. Correction immédiate
4. Re-exécution même jour si TSB permet (Z1-Z2 uniquement)

### Justification Data
S071-03a : Erreur détectée 17min, corrigée, S071-03 refaite avec succès même jour (TSS 37/37 validé).

### Checklist Pré-Upload Workout
**Validation obligatoire avant planification** :
1. ✅ Syntaxe répétitions correcte (`3x` ou `Repeat="3"`)
2. ✅ Preview Intervals.icu : durée totale cohérente
3. ✅ Test 5min structure si nouveau format
4. ✅ Comparaison TSS calculé vs attendu (±10% max)

### Temps Perdu Acceptable
- Correction + re-exécution Z1-Z2 : <1h acceptable
- Si Z3+ : Reporter au lendemain (pas de double intensité même jour)

---

## 6. Données Sommeil

### Surveillance Renforcée Obligatoire
**Problème identifié S071** : Sommeil 0.0h récurrent (5/7 jours) invalide analyses récupération/décisions intensité.

### Protocole Correction S072
1. **Vérification intégration Withings** : Résoudre problème API/synchronisation
2. **Saisie manuelle backup** : Si API défaillante, saisir manuellement heures sommeil Intervals.icu
3. **Critère validation séance intensité** : Sommeil ≥7h **obligatoire** pour VO2/Sweet-Spot (VETO si donnée manquante)

### Actions Immédiates
- Tester synchronisation Withings → Intervals.icu
- Si échec technique : Saisie manuelle quotidienne matin (5min max)
- Documentation sommeil **non-négociable** pour décisions intensité

---

## Modifications Hydratation/Nutrition

### Hydratation Standard Maintenue
**Protocole base inchangé** :
- 500ml/h intensité <88% FTP
- 600ml/h intensité ≥88% FTP ou séances longues >75min

**Exception festif occasionnel** : Voir protocole section 3 ci-dessus.

### Nutrition Terrain
Aucune séance terrain S071 → Protocole nutrition terrain (rice cakes, waypoints) non testé.
**Maintien protocole existant sans modification.**

---

## Adaptations Matériel/Discipline

### Discipline Indoor-Only Maintenue
100% séances indoor S071 → Stratégie indoor-only validée, aucun changement.

### Surveillance Capteurs
**Nouveau protocole vérification mensuelle** :
1. Calibration capteur puissance Wahoo (zero offset)
2. Test batterie sangle cardio
3. Vérification contact sangle (humidification pré-séance)
4. Dual recording Zwift + Wahoo pour cross-validation

**Justification** : Découplages négatifs S071 suggèrent possible dérive capteurs.

---

## Exclusions Mises à Jour

### Formats Interdits (Ajouts S071)
- ❌ **Récupération 50% FTP avec variabilité** : S071-02 TSS dépassé +72%, privilégier puissance constante uniquement
- ❌ **Critérium/Explosif sans consigne cadence** : Glasgow échec 74rpm, cadence ≥85rpm désormais obligatoire explicite
- ❌ **Double séance si TSB <+8** : Critère strict, aucune exception

### Formats Maintenus Interdits
- ❌ Dimanche séances (repos protocole absolu)
- ❌ VO2 Max si sommeil <7h (maintenu)
- ❌ Sweet-Spot si TSB <+5 (maintenu)

---

## Synthèse Adaptations S071

### Nouveaux Protocoles
1. Double endurance weekend sous conditions (TSB ≥+8, sommeil ≥7h)
2. Cadence explosif ≥85rpm obligatoire + séances spécifiques correction
3. Hydratation festif occasionnel +20% volume
4. Découplage <3% palier exceptionnel, négatif <-5% investigation
5. Réactivité erreurs workout immédiate

### Protocoles Renforcés
1. Sommeil données obligatoires (Withings ou saisie manuelle)
2. Vérification capteurs mensuelle (FC + puissance)
3. Validation workout pré-upload systématique

### Protocoles Maintenus
1. Hydratation standard 500-600ml/h
2. Indoor-only discipline
3. Dimanche repos absolu
4. Découplage >7.5% = dérive

---