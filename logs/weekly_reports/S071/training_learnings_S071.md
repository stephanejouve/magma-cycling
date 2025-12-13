# Enseignements d'Entraînement S071

## 1. Capacité Double Endurance Validée

### Découverte Majeure
**Samedi 13/12** : Première double séance journée complétée avec succès (S071-06A: 55 TSS + S071-06B: 22 TSS = 77 TSS total).

### Preuves Objectives
- TSB pré-double : +8
- TSB post-double : +8 (maintenu)
- Découplage S071-06A : 1.5% (excellent)
- Découplage S071-06B : -3.2% (atypique mais aucun signe fatigue)
- RPE constant 4/10 sur les deux séances
- Aucune dégradation métriques FC/puissance

### Implications
- **Progression volume possible** via doubles séances weekend sans compromettre TSB
- Format validé : Endurance 75min (55 TSS) + Technique 45min (22 TSS)
- **Condition critique** : TSB ≥+8 pré-double + sommeil ≥7h veille (non vérifié S071 car donnée manquante)

### Application S072+
Introduire double séance systématique samedi si :
1. TSB vendredi soir ≥+8
2. Sommeil validé ≥7h
3. Format : Endurance 60-75min AM + Récup/Technique 40-50min PM
4. Cible : 70-85 TSS journalier cumulé

---

## 2. Limite Neuromusculaire Formats Explosifs

### Découverte Majeure
**Glasgow Crit Circuit (08/12)** : Cadence anormalement basse **74rpm** vs profil habituel 84-86rpm sur efforts explosifs.

### Preuves Objectives
- Cadence moyenne 74rpm (-13% vs standard)
- NP/Pavg ratio 1.34 (haute variabilité)
- Abandon séance 38min vs 45min planifié
- IF 0.85 mais incapacité maintenir cadence cible
- Historique : Cadence 85-87rpm toutes endurances S071

### Analyse Technique
**Hypothèses** :
1. Fatigue neuromusculaire fibres rapides (explosivité)
2. Coordination sous-optimale cadence élevée en relances
3. Gestion inadéquate ratio force/vitesse accélérations

**Pattern identifié** :
- Endurance stable : Cadence optimale 85-87rpm ✅
- Explosif/critérium : Cadence chute <80rpm ❌

### Protocole Correction S072+
**Séances spécifiques cadence explosif** :
```
Warmup 10min 65% 85rpm
Main 6x
- 30s 120% 95-100rpm (focus cadence haute)
- 90s 60% 85rpm (récup complète)
Cooldown 8min 60% 85rpm
```

**Fréquence** : 1×/semaine jusqu'à validation 85rpm+ maintenu en explosif.

---

## 3. Découplages Cardiovasculaires Atypiques

### Découverte Majeure
**Découplages négatifs exceptionnels** : -3.2% (S071-06B), -15.6% (S071-02), -7.9% (Glasgow), -4.5% (S071-03a).

### Preuves Objectives
| Séance | Découplage | Type | Contexte |
|--------|------------|------|----------|
| S071-06B | -3.2% | Technique | 2ème séance journée |
| S071-02 | -15.6% | Récup | Post-critérium |
| Glasgow | -7.9% | Explosif | Format court |
| S071-03a | -4.5% | Technique | Séance avortée |

**Contraste** : Endurances S071-04 (+1.0%) et S071-06A (+1.5%) découplages positifs normaux.

### Analyse Technique
**Découplage négatif** = FC diminue proportionnellement plus que puissance (efficacité cardiovasculaire améliorée en cours séance).

**Causes possibles** :
1. **Échauffement progressif** : FC descend après pic initial (probable S071-06B 2ème séance)
2. **Amélioration conductivité** : Phénomène adaptatif rare
3. **Artefact calibration** : Capteur FC/puissance désynchronisé (hypothèse prioritaire vu amplitude -15.6%)

### Action Immédiate
**Vérification technique S072** :
1. Recalibrer capteur puissance Wahoo
2. Vérifier sangle cardio contact/batterie
3. Comparer données Zwift vs Wahoo (dual recording)
4. Documenter reproductibilité découplages négatifs prochaines séances

**Si reproductible** : Indicateur positif efficacité Z1, documenter comme pattern validé.
**Si non-reproductible** : Confirmer problème matériel, remplacer capteur défaillant.

---

## 4. Hydratation Contexte Sub-Optimal Gérée

### Découverte Majeure
**Double séance samedi 13/12** réussie malgré contexte période festive (repas arrosé, alcool, alimentation enrichie).

### Preuves Objectives
- Retour athlète : "Repas arrosé, alcool, supplémentation isotonique"
- Performance maintenue : IF 0.65 cible respectée
- Découplages validés : 1.5% et -3.2%
- RPE stable 4/10 sur les 2 séances
- TSB maintenu +8 post-effort

### Protocole Adapté Validé
**Supplémentation isotonique complémentaire** :
- Bidon standard + comprimé boisson isotonique
- Volume estimé : 600ml/h vs 500ml/h protocole standard
- Application : S071-06B uniquement (2ème séance)

### Limites Identifiées
- Protocole validé **ponctuellement**, non-reproductible systématiquement
- Contexte festif = exception, hydratation normale préférable
- Données Withings sommeil manquantes (0.0h) limitent analyse récupération complète

### Application S072+
**Protocole festif occasionnel** :
1. Supplémentation isotonique si repas arrosé <6h pré-séance
2. Volume +20% hydratation (600ml/h vs 500ml/h)
3. Limite double séance : Accepter uniquement si TSB ≥+8
4. Fréquence max : 1×/mois (périodes fêtes/événements)

**Priorité S072** : Retour hydratation standard 500ml/h hors contexte festif.

---

## 5. Erreur Structure Workout Corrigée Rapidement

### Découverte Processus
**Mercredi 10/12** : S071-03a avortée (17min vs 64min prévu) suite erreur template Intervals.icu (bloc principal non répété 5×).

### Preuves Objectives
- S071-03a : TSS 9 vs 13 planifié, interrompu avant cooldown
- Correction immédiate template
- S071-03 refaite : TSS 37/37, découplage 3.0% validé
- Total temps perdu : <1h (incluant correction + re-exécution)

### Protocole Validation Renforcé
**Checklist pré-upload workout** :
1. Vérifier syntaxe répétitions (`3x` ou `Repeat="3"`)
2. Tester preview Intervals.icu avant planification
3. Valider durée totale calculée vs attendue
4. Si doute : Exécuter version test 5min, vérifier structure

### Enseignement Comportemental
**Réactivité exemplaire** :
- Détection erreur immédiate (pas d'acharnement séance invalide)
- Correction template sans délai
- Re-exécution même jour (aucune perte TSS hebdo)
- Pas d'impact TSB/fatigue grâce intensité légère (Z1)

**Application future** : Maintenir cette réactivité pour toute anomalie technique détectée en cours séance.

---

## Synthèse Protocoles Validés S071

### ✅ Validés
1. **Double endurance weekend** : 75min AM + 45min PM si TSB ≥+8
2. **Découplages 1-3%** : Validation excellente base aérobie endurance
3. **Hydratation festif ponctuel** : +20% volume + isotonique si contexte sub-optimal
4. **Réactivité erreurs techniques** : Correction immédiate > acharnement

### ❌ Invalidés
1. **Récupération 50% FTP variable** : S071-02 dérive vers endurance (TSS +72%), privilégier 50% stable uniquement
2. **Cadence basse formats explosifs** : 74rpm insuffisant, nécessite travail spécifique 90-100rpm

### ⚠️ À Investiguer S072
1. **Découplages négatifs >5%** : Vérifier reproductibilité vs artefact calibration
2. **Sommeil données manquantes** : Intégrer Withings systématiquement
3. **Cadence explosif** : Tester séances spécifiques haute cadence, documenter progression

---

## Points Surveillance S072

1. **Volume progression** : TSS 300-320 hebdo (vs 239 S071) via introduction double séance + retour séances complètes
2. **Cadence explosif** : Séance test accélérations 95-100rpm, valider maintien cadence vs chute <80rpm
3. **Calibration capteurs** : Vérifier FC/puissance si découplages négatifs persistent
4. **Sommeil données** : Résoudre problème intégration Withings (actuellement 0.0h récurrent critique)
5. **Hydratation standard** : Retour protocole 500ml/h normal post-période festive

---