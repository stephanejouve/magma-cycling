# Planning Preferences - Stéphane Jouve

**Auteur**: Stéphane Jouve + Claude Code
**Créé**: 2026-02-15
**Version**: 1.0.0
**Usage**: Contraintes et préférences pour génération planning hebdomadaire (end-of-week, workflow-coach)

---

## 🗓️ Organisation Hebdomadaire

### Jour Léger Préféré: **MERCREDI**

**Rationale**:
- **Pratique**: Permet de remonter/déposer matériel vélo (entretien, maintenance)
- **Physiologique**: Coupure en milieu de semaine après lundi-mardi
- **CTL**: Maximise jours actifs (dimanche disponible pour sortie endurance)
- **Récupération**: Position milieu semaine optimale pour Masters 50+

**Format mercredi**:
- **Priorité 1**: Repos complet (0 TSS) si besoin maintenance vélo
- **Priorité 2**: Séance courte/légère (20-40 TSS, recovery/endurance facile) si forme OK
- **Flexibility**: Adapter selon sensation, TSB, et besoins logistiques

**❌ À éviter**: Dimanche comme jour repos systématique
- Historique: Anciens plannings laissaient souvent dimanche libre
- Problème: Sous-optimal pour reconstruction CTL (perte 1 jour actif/semaine)
- Exception: Dimanche OFF acceptable en semaine récupération ou si TSB < -15

### Structure Hebdomadaire Type (Charge)

```
Lundi:    Séance qualité (Tempo/Sweet-Spot)           50-55 TSS
Mardi:    Séance qualité ou endurance                 45-55 TSS
Mercredi: REPOS ou séance courte (maintenance)        0-40 TSS  ← JOUR LÉGER
Jeudi:    Séance endurance ou qualité                 50-60 TSS
Vendredi: Séance qualité (Tempo/Sweet-Spot)           48-55 TSS
Samedi:   Sortie longue endurance                     60-80 TSS
Dimanche: Endurance modérée ou tempo                  50-70 TSS
```

**TSS Total Charge**: 303-405 TSS/semaine (flexible selon phase)

### Structure Hebdomadaire Type (Récupération)

```
Lundi:    Recovery active                             28-35 TSS
Mardi:    Endurance légère                           40-45 TSS
Mercredi: REPOS complet (maintenance)                 0 TSS     ← JOUR LIBRE
Jeudi:    Endurance légère                           40-45 TSS
Vendredi: Recovery active                            28-35 TSS
Samedi:   Endurance modérée                          50-60 TSS
Dimanche: Endurance légère ou OFF                    0-45 TSS
```

**TSS Total Recovery**: 186-265 TSS/semaine

---

## 📋 Contraintes Logistiques

### Jours Disponibles
- **Lundi-Dimanche**: Tous les jours disponibles pour entraînement
- **Mercredi**: Préférence pour repos/maintenance (pas obligatoire)
- **Durée max**: 90-120min maximum (sortie longue weekend)

### Matériel
- **Mercredi**: Jour préféré pour entretien/réparations vélo
- **Impact planning**: Recovery active ou OFF le mercredi si maintenance prévue

### Météo (Hiver)
- **Indoor prioritaire**: Tempo, Sweet-Spot, VO2max
- **Outdoor possible**: Endurance, Recovery si météo acceptable
- **Flexibility**: Templates adaptables indoor/outdoor

---

## 🎯 Règles Génération Planning (IA)

### Priorités (par ordre)
1. **Distribution TSS**: Respecter Peaks Coaching (Tempo 35%, Sweet-Spot 20%, etc.)
2. **Mercredi repos/light**: Priorité haute pour maintenance
3. **Quality sessions**: Mardi/Vendredi idéal (frais après repos mercredi)
4. **Long ride**: Samedi ou dimanche (flexibility)
5. **Progressive overload**: Augmentation CTL régulière (+1.5-3 pts/sem)

### Anti-Patterns (à éviter)
- ❌ Dimanche repos systématique (sauf récupération)
- ❌ 3 jours intenses consécutifs sans repos
- ❌ Sweet-Spot + Tempo back-to-back (fatigue cumulative Masters 50+)
- ❌ Recovery active le weekend (perte opportunité volume)
- ❌ Ignorer découplage >7.5% (forcer intensité)

### Adaptation Dynamique
Si signaux d'alerte détectés (servo mode):
- **Découplage >7.5%**: Remplacer intensité par recovery/endurance
- **Sommeil <7h**: Alléger charge jour suivant
- **TSB < -10**: Insérer jour repos supplémentaire
- **Adherence <70%**: Révision planning (simplification)

---

## 🔧 Exemples Semaine Type

### Exemple 1: Reconstruction CTL (Phase actuelle Sprint R10)

**Objectif**: 350 TSS/semaine, Focus Tempo 35% + Sweet-Spot 20%

| Jour      | Séance                  | Type       | TSS | Notes                    |
|-----------|-------------------------|------------|-----|--------------------------|
| Lundi     | Tempo Intervals T1      | Tempo      | 50  | 3x12min @ 85% FTP        |
| Mardi     | Endurance Steady        | Endurance  | 55  | 75min Z2                 |
| Mercredi  | **REPOS** ou Recovery   | OFF/Rec    | 0   | **Maintenance vélo**     |
| Jeudi     | Endurance Steady        | Endurance  | 55  | 75min Z2                 |
| Vendredi  | Sweet-Spot Classic SS1  | SS         | 55  | 3x10min @ 90% FTP        |
| Samedi    | Long Endurance          | Endurance  | 70  | 90min Z2                 |
| Dimanche  | Tempo Endurance T2      | Tempo      | 48  | 40min continu 80-85% FTP |

**Total**: 333 TSS (proche cible 350)
**Distribution**: Tempo 29%, Sweet-Spot 17%, Endurance 54%

### Exemple 2: Semaine Récupération (Post-charge)

**Objectif**: 250 TSS/semaine, Intensité réduite

| Jour      | Séance                  | Type       | TSS | Notes                    |
|-----------|-------------------------|------------|-----|--------------------------|
| Lundi     | Recovery Active         | Recovery   | 30  | 45min Z1                 |
| Mardi     | Endurance Light         | Endurance  | 45  | 60min Z2 facile          |
| Mercredi  | **REPOS complet**       | OFF        | 0   | **Maintenance vélo**     |
| Jeudi     | Endurance Light         | Endurance  | 45  | 60min Z2 facile          |
| Vendredi  | Recovery Active         | Recovery   | 30  | 45min Z1                 |
| Samedi    | Endurance Moderate      | Endurance  | 60  | 80min Z2                 |
| Dimanche  | Endurance Light ou OFF  | End/OFF    | 40  | 55min Z2 ou repos        |

**Total**: 250 TSS
**Focus**: Récupération active, pas d'intensité

---

## 📌 Notes Importantes

### Masters 50+ Considerations
- **Récupération**: 24-36h minimum entre séances intenses
- **Charge maximale**: 400-450 TSS/semaine maximum (éviter surcharge)
- **Qualité > Volume**: Préférer 5 séances bien faites vs 7 médiocres
- **Découplage**: Indicateur critique (>7.5% = stop intensité)

### Context Sprint R10 (Février-Mars 2026)
- **Phase**: RECONSTRUCTION_BASE (CTL 42.4 → 57 minimum)
- **Mode**: PEAKS_OVERRIDE actif (CTL < 50)
- **Focus**: Tempo 35% + Sweet-Spot 20%
- **Target**: 350 TSS/semaine charge, 250 TSS recovery
- **Test FTP**: Prévu fin S086 (28 mars 2026)

### Intégration Workflow
Ce document doit être consulté par:
- ✅ `end-of-week` (génération planning dimanche 20h00)
- ✅ `workflow-coach` (servo mode ajustements)
- ✅ `daily-sync` (recommandations compensation)
- ✅ Claude Code (contexte sessions planning)

---

**Dernière mise à jour**: 2026-02-15
**Prochain review**: Fin Sprint R10 (post-test FTP S086)
