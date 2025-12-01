# Adaptations Protocolaires S069

## 1. Seuils Décisionnels VFC Affinés

### Modifications Critères Existants

**AVANT S069 :**
Seuil unique VFC 55ms pour VETO intensité, sans gradation fine.

**APRÈS S069 (Validé) :**
Matrice décisionnelle combinant VFC + Sommeil pour autorisation intensité :

| VFC (ms) | Interprétation | Actions Autorisées | Exclusions |
|----------|---------------|-------------------|-----------|
| >70 | Optimal | Toutes intensités (VO2 si sommeil 7h+) | Aucune |
| 60-70 | Bon | Sweet-spot 88-90% autorisé, VO2 conditionnel | VO2 si sommeil <7h |
| 55-60 | Acceptable | Z2 max (75% FTP), sweet-spot si sommeil 7h+ | VO2, seuil (>95% FTP) |
| 50-55 | Alerte | Z1 uniquement (50-60% FTP) | Toute intensité >70% FTP |
| <50 | Critique | Repos complet obligatoire | Tout entraînement |

### Justification Données S069
- VFC 81ms (J1) : Sweet-spot autorisé, exécuté J2 avec succès (IF 0.73, découplage 2.0%)
- VFC 60ms (J2) : Z2 validé, progression possible
- VFC 51ms (J3) : Alerte émise, intensité interdite → Respecté (Z1 technique, IF 0.63)
- VFC 61ms (J4) : Récupération validée, Z2-force acceptable

### Application Obligatoire S070+
Monitoring VFC quotidien avant toute séance. Décision intensité basée tableau, pas ressenti subjectif. Logging VFC systématique dans wellness Intervals.icu.

---

## 2. Protocole Test Reprise Post-Maladie Formalisé

### Nouveau Protocole Obligatoire

**Conditions Déclenchement :**
- Arrêt entraînement >3 jours consécutifs (maladie, blessure, surmenage)
- Symptômes respiratoires (toux, rhinopharyngite, bronchite)
- VFC <50ms maintenue >48h

**Structure Test Reprise :**
```
Warmup
- 10m Ramp 40-50% 80rpm

Test Validation
- 15m 50-60% 85rpm
- Surveillance : FC, RPE, symptômes respiratoires, découplage

Cooldown
- 10m Ramp 50-40% 80rpm
```

**Durée totale :** 35 minutes  
**TSS cible :** 15-20  
**IF cible :** 0.50-0.55

**Critères Validation Progression :**
1. ✅ FC <100bpm moyenne (âge 54)
2. ✅ RPE ≤3/10
3. ✅ Aucun symptôme respiratoire aggravé (toux, essoufflement)
4. ✅ Découplage <5%
5. ✅ VFC lendemain maintenue ou augmentée vs pré-test

**Actions Post-Test :**
- **5/5 validés** : Progression Z2 (60-70% FTP) J+1, sweet-spot possible J+3 si VFC >60ms
- **3-4/5 validés** : Répéter test J+2, maintien Z1 entre-temps
- **<3/5 validés** : Repos 48h supplémentaires, consultation médicale si symptômes persistants >7 jours

### Application S070
Test reprise obligatoire lundi S070-01 (35min Z1, 50-60% FTP). Validation avant progression Z2 mardi.

---

## 3. Hydratation Séances Force Outdoor Ajustée

### Observation S069-04
Prospect Park (70min, 6 montées, RPE 6/10) : Hydratation non documentée post-séance, mais découplage 4.9% suggère gestion correcte. Néanmoins, RPE élevé (6 vs 3-4 attendu Z2) partiellement attribuable à déshydratation potentielle relief.

### Protocole Renforcé Terrain Relief

**Séances outdoor >60min + dénivelé >100m :**
- **Pré-séance** : 500ml eau 1h avant (vs 250ml indoor standard)
- **Pendant** : 150ml/15min si montées >5% (vs 125ml/15min plat)
- **Post-séance immédiat** : 500ml dans 30min (vs 250ml indoor)
- **Waypoints RideWithGPS** : Alertes nutrition automatiques T+20min, T+40min si parcours >90min

**Calcul Besoins Individualisés :**
- Base : 500ml/h effort modéré (65-75% FTP)
- +150ml/h si relief (6+ montées ou >200m dénivelé/h)
- +250ml/h si température >25°C

### Validation S070
Si sortie outdoor longue planifiée (>75min), pré-programmer waypoints hydratation/nutrition. Test protocole sur séance Z2 avant application sweet-spot outdoor (si autorisé futur).

---

## 4. Exclusion Sweet-Spot <6h30 Sommeil Consolidé

### Règle Stricte Établie

**AVANT S069 :**
Sweet-spot autorisé si VFC >55ms, sommeil >5h toléré.

**APRÈS S069 (Validé) :**
Sweet-spot authentique (88-90% FTP) INTERDIT si :
- Sommeil <6h30 nuit précédente
- OU Moyenne sommeil <6h sur 3 nuits précédentes
- OU VFC <60ms

**Définition Sweet-Spot Authentique :**
- IF ≥0.88 (88% FTP minimum)
- Durée cumulée blocs ≥20min (ex: 3×8min, 2×12min, 4×6min)
- Découplage cible <5% validation qualité

**Alternative Si Conditions Non Remplies :**
- Tempo modéré (Z3, 76-85% FTP) : IF 0.76-0.85, autorisé si VFC >55ms
- Endurance Z2 renforcée (70-75% FTP) : Toujours possible si VFC >50ms

### Justification S069-02
Séance étiquetée "sweet-spot" réellement tempo (IF 0.73) suite sommeil 4.8h. Exécution correcte (découplage 2.0%) mais intensité insuffisante stimulus FTP vrai. Éviter confusion nomenclature/réalité.

### Application S070+
Renommage séances selon intensité réelle :
- IF 0.88-0.93 : "Sweet-Spot"
- IF 0.76-0.87 : "Tempo"
- IF 0.65-0.75 : "Endurance Z2 Haute"

Validation sommeil 6h30+ obligatoire avant planification sweet-spot authentique.

---

## 5. Surveillance Profondeur Sommeil Ajoutée

### Nouvelle Métrique Tracking

**AVANT S069 :**
Durée sommeil + VFC suffisants.

**APRÈS S069 (Complément) :**
Ajout profondeur sommeil dans évaluation qualité récupération :

| Profondeur | % Sommeil Profond | Qualité | Impact Performance |
|-----------|------------------|---------|-------------------|
| Excellente | >20% | Optimale | Intensité haute OK |
| Bonne | 15-20% | Correcte | Sweet-spot OK |
| Acceptable | 10-15% | Limite | Z2 max, surveillance |
| Mauvaise | <10% | Insuffisante | Z1 max même si durée >7h |

**Observations S069 :**
- J3 (mercredi) : 12% profond → Qualité "Mauvaise" malgré VFC 51ms validant alerte
- J4 (jeudi) : 11% profond → Amélioration durée (6h30) mais profondeur reste problématique

### Calcul Sommeil Efficace
**Formule ajustée :**
```
Sommeil Efficace = Durée Totale × (% Profond / 15%)
```

**Exemples :**
- 7h avec 20% profond : 7 × (20/15) = 9.3h efficaces (excellent)
- 7h avec 10% profond : 7 × (10/15) = 4.7h efficaces (insuffisant)
- 5h avec 18% profond : 5 × (18/15) = 6h efficaces (acceptable)

### Seuils Décisionnels Sommeil Efficace
- **>7h efficaces** : Intensité haute autorisée (VO2)
- **6-7h efficaces** : Sweet-spot OK
- **5-6h efficaces** : Z2 max
- **<5h efficaces** : Z1 max ou repos

### Application S070
Tracking quotidien sommeil efficace dans wellness Intervals.icu. Matrice décision VFC × Sommeil Efficace × Profondeur pour autorisation intensité.

---

## 6. Interdiction Compensation Volume Post-Arrêt

### Règle Nouvelle

**Principe :**
Après arrêt entraînement >3 jours (maladie, surmenage, blessure), pas de compensation réactive volume/intensité pour "rattraper" TSS perdu.

**Justification S069 :**
TSB +19 post-arrêt = surcondition excessive nécessitant retour progressif. Compensation volume rapide (ex: 2×séances/jour S070) risquerait nouvelle surcharge système déjà fragilisé (VFC instable, dette sommeil historique).

**Protocole Reprise Graduelle :**
- **Semaine 1 post-arrêt** : 60-70% charge habituelle (190-240 TSS si cible 320-380)
- **Semaine 2** : 80-90% charge (260-340 TSS)
- **Semaine 3** : 100% charge si validations OK (320-380 TSS)

**Exceptions :**
Aucune. Santé long terme > performance court terme.

### Application S070
- TSS cible S070 : 240 TSS maximum (-25% vs 320 baseline)
- Pas double séance avant S071
- Pas sweet-spot avant VFC >60ms + sommeil 6h30+ consolidé

---

## 7. Critères Outdoor vs Indoor Formalisés

### Matrice Décision Terrain

**INDOOR OBLIGATOIRE si :**
- Intensité >85% FTP (sweet-spot, seuil, VO2)
- Séances structure intervalles précise (ex: 4×8min 90% FTP)
- VFC <60ms (environnement contrôlé requis)
- Sommeil <6h30 (éviter variations terrain imprévisibles)

**OUTDOOR AUTORISÉ si :**
- Z1-Z2 légère (IF <0.70)
- Récupération technique (cadence, transitions)
- Contexte social validé (Foudre, groupes contrôlés)
- VFC >60ms ET sommeil >6h

**OUTDOOR AVEC ADAPTATION si :**
- Force-endurance relief modéré (Prospect Park validé)
- Accepter variations IF/TSS ±15% vs prévision indoor
- Waypoints nutrition programmés si >75min
- RPE surveillance (stop si >7/10)

### Validation S069-04
Prospect Park (outdoor, 70min, 6 montées, TSS 53) acceptable récupération (VFC 61ms, sommeil 6h30, IF 0.67) mais écarts cadence vs consignes indoor. Confirme pertinence stratégie indoor-only haute intensité.

---

## Modifications Hydratation Aucune

### Protocole Existant Maintenu
Pas de modification protocole hydratation base (500ml/h effort modéré) suite S069. Ajout spécifique terrain relief (section 3) complément non remplacement.

### Validation S069
Découplages exceptionnels (0.2%, 0.6%, 2.0%, 4.9%) suggèrent hydratation adequat indoor. Outdoor S069-04 : 4.9% découplage acceptable (<<7.5%) malgré relief, protocole validé.

---

## Exclusions Mises à Jour

### Formats Interdits S070 (Temporaire)
1. VO2 max (106-120% FTP) : Interdit jusqu'à VFC >70ms + sommeil 7h+ + CTL >55
2. Sweet-spot authentique (88-90% FTP) : Interdit jusqu'à VFC >60ms + sommeil 6h30+
3. Seuil lactique (95-105% FTP) : Interdit jusqu'à VFC >65ms + sommeil 7h+
4. Double séance : Interdit jusqu'à CTL >54 + VFC stable >60ms 5 jours consécutifs

### Formats Autorisés S070 (Progression)
1. Test reprise Z1 (50-60% FTP, 35min) : Lundi S070-01 obligatoire
2. Endurance Z2 (60-75% FTP) : Autorisé si test reprise validé + VFC >55ms
3. Tempo léger (76-85% FTP) : Autorisé fin S070 si VFC >60ms + sommeil 6h+
4. Récupération technique Z1 : Toujours autorisé (IF <0.60)

---

## Surveillance Renforcée S070

### Monitoring Quotidien Obligatoire
1. **VFC matin** : Mesure avant lever, logging Intervals.icu wellness
2. **Sommeil efficace** : Calcul durée × (profondeur/15%), objectif >6h efficaces
3. **Symptômes respiratoires** : Toux résiduelle stop intensité, consultation si >7 jours
4. **FC repos** : Baseline 40-45bpm, alerte si >50bpm maintenu >48h
5. **Poids** : Mesure matin, surveillance stabilité ±0.5kg (déshydratation/rétention)

### Critères Escalation Médicale
- Toux persistante >10 jours post-arrêt
- VFC <50ms maintenue >72h malgré repos
- FC repos >55bpm maintenue >48h
- Essoufflement anormal Z1 (50-60% FTP)
- Fatigue chronique non résolue après 2 semaines

---