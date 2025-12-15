# Exemple de Format d'Analyse

Ce document montre le format attendu pour les analyses générées par Claude.ai

## Format Standard

```markdown
### S067-03-INT-SweetSpotMaintien
Date : 14/11/2025

#### Métriques Pré-séance
- CTL : 59
- ATL : 70
- TSB : -11
- Sommeil : 6.2h

#### Exécution
- Durée : 58min
- IF : 0.77
- TSS : 58
- Puissance moyenne : 161W
- Puissance normalisée : 170W
- Cadence moyenne : 88rpm
- FC moyenne : 112bpm
- Découplage : 2.3%

#### Exécution Technique
Séance Sweet-Spot réalisée à 88% FTP (170W NP) sur 58 minutes. Découplage cardiovasculaire à 2.3% valide la qualité d'exécution (seuil <7.5% largement respecté). Cadence stable à 88rpm et FC moyenne contenue à 112bpm démontrent un contrôle technique optimal malgré le TSB négatif pré-séance.

#### Charge d'Entraînement
TSS de 58 réalisé avec TSB pré-séance à -11, ce qui confirme une fatigue résiduelle modérée mais gérable. L'IF de 0.77 est approprié pour une séance d'intensité modérée dans ce contexte de charge accumulée.

#### Validation Objectifs
- ✅ Découplage <7.5% : 2.3% (validation qualité)
- ✅ Sweet-Spot 88-90% FTP : 88% (cible atteinte)
- ✅ Durée planifiée : 58min réalisés

#### Points d'Attention
- TSB négatif (-11) : fatigue résiduelle à surveiller
- Sommeil sous optimal (6.2h vs cible 7h+) : facteur limitant potentiel

#### Recommandations Progression
1. Prévoir récupération active ou repos complet dans les 24-48h (TSB négatif)
2. Maintenir intensité Sweet-Spot 88-90% pour consolidation avant progression vers 90%+

#### Métriques Post-séance
- CTL : 59
- ATL : 70
- TSB : -11

---
```

## Sections Obligatoires

### 1. En-tête
```markdown
### [Nom de la séance]
Date : JJ/MM/AAAA
```

### 2. Métriques Pré-séance
```markdown
#### Métriques Pré-séance
- CTL : [valeur]
- ATL : [valeur]
- TSB : [valeur avec signe +/-]
- Sommeil : [heures]h
```

### 3. Exécution (métriques brutes)
```markdown
#### Exécution
- Durée : [min]min
- IF : [ratio 0.00]
- TSS : [valeur]
- Puissance moyenne : [W]W
- Puissance normalisée : [W]W
- Cadence moyenne : [rpm]rpm
- FC moyenne : [bpm]bpm
- Découplage : [%]% ou N/A
```

### 4. Exécution Technique (analyse qualitative)
```markdown
#### Exécution Technique
[2-3 phrases factuelles sur :
- Validation de la zone d'intensité cible
- Qualité technique (découplage, cadence, FC)
- Cohérence entre les métriques
- Comparaison avec les objectifs]
```

**Exemple :**
> Séance Sweet-Spot réalisée à 88% FTP (170W NP) sur 58 minutes. Découplage cardiovasculaire à 2.3% valide la qualité d'exécution (seuil <7.5% largement respecté). Cadence stable à 88rpm et FC moyenne contenue à 112bpm démontrent un contrôle technique optimal malgré le TSB négatif pré-séance.

### 5. Charge d'Entraînement
```markdown
#### Charge d'Entraînement
[2 phrases sur :
- Impact du TSS réalisé
- Implications du TSB pré/post séance
- Contexte de fatigue]
```

**Exemple :**
> TSS de 58 réalisé avec TSB pré-séance à -11, ce qui confirme une fatigue résiduelle modérée mais gérable. L'IF de 0.77 est approprié pour une séance d'intensité modérée dans ce contexte de charge accumulée.

### 6. Validation Objectifs
```markdown
#### Validation Objectifs
- ✅/❌ [Critère 1 : description et résultat]
- ✅/❌ [Critère 2 : description et résultat]
- ✅/❌ [Critère 3 : optionnel si pertinent]
```

**Exemples de critères :**
- Découplage <7.5%
- Zone d'intensité cible (Sweet-Spot 88-90% FTP, Endurance 60-70%, etc.)
- Durée planifiée
- Cadence cible
- FC dans zone attendue
- TSB pré-séance minimum (pour VO2)

### 7. Points d'Attention
```markdown
#### Points d'Attention
- [Point factuel 1 : observation nécessitant surveillance]
- [Point factuel 2 : si pertinent]
```

**Exemples :**
- TSB négatif (-11) : fatigue résiduelle à surveiller
- Sommeil sous optimal (6.2h vs cible 7h+) : facteur limitant potentiel
- Découplage proche seuil : surveiller hydratation prochaine séance
- Puissance 0W (source Strava) : vérifier données web Intervals.icu

### 8. Recommandations Progression
```markdown
#### Recommandations Progression
1. [Recommandation concrète et actionnable 1]
2. [Recommandation concrète et actionnable 2]
```

**Exemples :**
- Prévoir récupération active ou repos complet dans les 24-48h (TSB négatif)
- Maintenir intensité Sweet-Spot 88-90% pour consolidation avant progression vers 90%+
- Augmenter durée Sweet-Spot de 8 à 10 minutes par intervalle si découplage reste <5%
- Attendre TSB +5 minimum avant prochaine séance VO2max

### 9. Métriques Post-séance
```markdown
#### Métriques Post-séance
- CTL : [valeur]
- ATL : [valeur]
- TSB : [valeur avec signe +/-]
```

## Cas Particuliers

### Activité Strava (données limitées)

Si puissance = 0W, TSS disponible mais pas de puissance :

```markdown
#### Exécution
- Durée : 193min
- IF : 0.85
- TSS : 233
- Puissance moyenne : _Données non disponibles (source Strava)_
- Puissance normalisée : _Données non disponibles (source Strava)_
- Cadence moyenne : 71rpm
- FC moyenne : 113bpm
- Découplage : 3.4%

#### Exécution Technique
Sortie terrain de 193 minutes avec TSS élevé de 233 et IF 0.85, suggérant une intensité soutenue. Données de puissance non disponibles (source Strava), analyse basée sur FC moyenne (113bpm), cadence (71rpm) et découplage (3.4%). Effort cohérent avec une sortie endurance intensive.

#### Points d'Attention
- Données puissance manquantes (source Strava) : vérifier sur Intervals.icu web
- Découplage à 3.4% : qualité validée malgré durée longue
```

## Règles d'Or

1. **Factuel uniquement** : Pas d'interprétation subjective
2. **Concis** : 2-3 phrases maximum par section qualitative
3. **Actionnable** : Recommandations concrètes et réalisables
4. **Cohérent** : Croiser les métriques (IF vs découplage vs FC)
5. **Contextuel** : Tenir compte TSB, sommeil, historique récent

## Anti-patterns à Éviter

❌ Texte explicatif avant/après le bloc markdown
❌ Blocs de code (```markdown)
❌ Phrases génériques ("Bonne séance", "Continuer ainsi")
❌ Répétition des métriques déjà affichées dans Exécution
❌ Recommandations vagues ("Surveiller la fatigue")
❌ Plus de 3 phrases dans sections qualitatives

✅ Bloc markdown direct
✅ Format exact respecté
✅ Analyse factuelle et technique
✅ Recommandations spécifiques ("Prévoir repos 24-48h")
✅ Concision et précision

---

**Version** : 2.0
**Dernière mise à jour** : 15 novembre 2025
**Compatible avec** : prepare_analysis.py v2.0+
