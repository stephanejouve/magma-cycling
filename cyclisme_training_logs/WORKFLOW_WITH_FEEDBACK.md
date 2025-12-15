# Workflow Enrichi avec Feedback Athlète

## 🎯 Pourquoi Collecter le Feedback ?

L'analyse de Claude devient **beaucoup plus pertinente** en croisant :
- ✅ **Métriques objectives** : Puissance, FC, TSS, découplage...
- ✅ **Ressenti subjectif** : RPE, fatigue, difficultés, sensations...

**Exemple concret** :
- Métriques : IF 0.85, découplage 2.3%, TSS 58 → "Séance bien exécutée"
- Feedback : RPE 9/10, "jambes lourdes, très difficile" → Alerte fatigue !
- **Analyse enrichie** : Séance techniquement bonne MAIS signal de surmenage

## 🚀 Workflow Complet (Recommandé)

### Option A : Workflow Enrichi (2 minutes de plus)

```bash
# 1. Collecter le feedback athlète (30 secondes)
./scripts/collect_athlete_feedback.py --quick

# 2. Générer le prompt (intègre automatiquement le feedback)
./scripts/prepare_analysis.py

# 3. Coller dans Claude.ai
# → Claude reçoit métriques + ressenti

# 4. Insérer l'analyse
./scripts/insert_analysis.py
```

### Option B : Workflow Standard (sans feedback)

```bash
# 1. Générer le prompt (sans feedback)
./scripts/prepare_analysis.py

# 2. Coller dans Claude.ai
# → Claude analyse uniquement les métriques

# 3. Insérer l'analyse
./scripts/insert_analysis.py
```

## 📝 collect_athlete_feedback.py

### Mode Rapide (30 secondes)

```bash
./scripts/collect_athlete_feedback.py --quick
```

**Questions posées** :
1. **RPE** (1-10) : Intensité perçue
2. **Ressenti général** : En quelques mots

**Exemple** :
```
📊 RPE (1-10) : 7

💭 Ressenti général en quelques mots
→ Bonne séance, jambes répondent bien
```

### Mode Complet (2-3 minutes)

```bash
./scripts/collect_athlete_feedback.py
```

**Questions posées** :
1. **RPE** (1-10)
2. **Ressenti général** (fatigue, forme, motivation)
3. **Difficultés rencontrées** ? (oui/non)
   - Si oui : description multi-lignes
4. **Points positifs** ? (oui/non)
   - Si oui : description multi-lignes
5. **Contexte particulier** ? (sommeil, nutrition, stress, météo...)
6. **Sensations physiques** ? (checklist)
   - Douleurs musculaires
   - Jambes lourdes
   - Bonne récupération
   - Fatigue générale
   - Tension/raideur
   - Autre (texte libre)
7. **Notes libres** : Observations additionnelles

### Commandes Utiles

```bash
# Afficher le feedback en attente
./scripts/collect_athlete_feedback.py --show

# Effacer le feedback non utilisé
./scripts/collect_athlete_feedback.py --clear

# Aide complète
./scripts/collect_athlete_feedback.py --help
```

## 📊 Exemple de Feedback

### Mode Rapide
```json
{
  "rpe": 7,
  "ressenti_general": "Bonne séance, jambes répondent bien"
}
```

### Mode Complet
```json
{
  "rpe": 8,
  "ressenti_general": "Séance difficile mais motivé",
  "difficultes": "Intervalles 3 et 4 très durs à tenir\nFC qui monte vite",
  "points_positifs": "Bon échauffement\nCadence stable",
  "contexte": "Sommeil court (5h30), stress au travail",
  "sensations_physiques": ["Jambes lourdes", "Fatigue générale"],
  "notes_libres": "À surveiller pour prochaine séance VO2"
}
```

## 🔄 Intégration dans le Prompt

Le feedback est automatiquement ajouté au prompt pour Claude :

```markdown
## 💭 Retour Athlète (Ressenti Subjectif)

**RPE** : 8/10

**Ressenti** : Séance difficile mais motivé

**Difficultés** :
Intervalles 3 et 4 très durs à tenir
FC qui monte vite

**Points positifs** :
Bon échauffement
Cadence stable

**Contexte** : Sommeil court (5h30), stress au travail

**Sensations physiques** : Jambes lourdes, Fatigue générale

**Notes libres** :
À surveiller pour prochaine séance VO2

**Important** : Ce retour subjectif enrichit l'analyse objective des métriques.
Croiser les deux perspectives pour une analyse complète.
```

## 📈 Impact sur l'Analyse de Claude

### Sans Feedback (analyse standard)
```markdown
#### Exécution Technique
Séance Sweet-Spot réalisée à 88% FTP avec découplage 2.3%.
Qualité technique validée.

#### Recommandations Progression
1. Maintenir intensité 88-90% pour consolidation
2. Augmenter durée intervalles si découplage reste <5%
```

### Avec Feedback (analyse enrichie)
```markdown
#### Exécution Technique
Séance Sweet-Spot réalisée à 88% FTP avec découplage 2.3% (excellent).
MAIS RPE 8/10 avec difficultés sur intervalles 3-4 et FC qui monte vite.
Contradiction métriques/ressenti suggère fatigue résiduelle.

#### Validation Objectifs
- ✅ Découplage <7.5% : 2.3% (validation technique)
- ⚠️  RPE élevé (8/10) malgré IF modéré : signal surmenage
- ❌ Contexte défavorable : sommeil 5h30 + stress

#### Points d'Attention
- Sommeil court (5h30) : facteur limitant identifié
- RPE élevé vs métriques modérées : surveiller surmenage
- Jambes lourdes + fatigue générale : récupération insuffisante

#### Recommandations Progression
1. **Priorité récupération** : repos 48h ou récupération active uniquement
2. **Reporter VO2** jusqu'à TSB +5 ET sommeil >7h
3. Surveiller hydratation et nutrition (stress augmente besoins)
```

## 🎯 Quand Utiliser le Feedback ?

### ✅ Recommandé Pour :
- **Séances clés** : VO2, FTP, Sweet-Spot, longues sorties
- **Périodes de fatigue** : Quand TSB négatif ou sommeil insuffisant
- **Contexte particulier** : Stress, maladie, conditions météo difficiles
- **Ressenti inhabituel** : Séance plus dure ou plus facile que prévu
- **Suivi surmenage** : Croiser métriques objectives + ressenti

### ⏭️ Optionnel Pour :
- Séances de récupération simples
- Endurance de base sans incidents
- Quand ressenti = normal et attendu

## ⚙️ Configuration

### Emplacement des Fichiers

```
.athlete_feedback/
└── last_feedback.json  # Feedback en attente d'utilisation
```

**Important** :
- ✅ `.athlete_feedback/` est dans `.gitignore` (pas de commit)
- ✅ Le feedback est **automatiquement effacé** après utilisation
- ✅ Un feedback = une séance uniquement

### Cycle de Vie du Feedback

```
1. collect_athlete_feedback.py
   → Crée .athlete_feedback/last_feedback.json

2. prepare_analysis.py
   → Lit et intègre le feedback dans le prompt
   → Efface automatiquement le fichier après utilisation

3. Prochaine séance
   → Aucun feedback résiduel, système propre
```

## 🔧 Dépannage

### "Aucun feedback en attente"

**Normal si** :
- Première utilisation
- Feedback déjà utilisé pour une séance précédente
- Feedback effacé manuellement avec `--clear`

**Solution** : Collecter un nouveau feedback avec `collect_athlete_feedback.py`

### Feedback non intégré dans le prompt

**Causes possibles** :
1. Feedback collecté APRÈS génération du prompt
2. Fichier `.athlete_feedback/last_feedback.json` manquant
3. Erreur dans le fichier JSON

**Solution** :
```bash
# Vérifier le feedback
./scripts/collect_athlete_feedback.py --show

# Régénérer le prompt
./scripts/prepare_analysis.py
```

### Feedback réutilisé pour plusieurs séances

**Cause** : Bug dans l'effacement automatique

**Solution temporaire** :
```bash
./scripts/collect_athlete_feedback.py --clear
```

## 📊 Statistiques d'Usage

**Temps ajouté** :
- Mode rapide : +30 secondes
- Mode complet : +2-3 minutes

**Bénéfice** :
- Analyse Claude **beaucoup plus contextuelle**
- Détection précoce du surmenage
- Recommandations personnalisées
- Meilleure traçabilité du ressenti

**Recommandation** : Utiliser le feedback pour **toutes les séances clés** (VO2, FTP, Sweet-Spot, longues sorties).

## 🚀 Workflow Complet Exemple

```bash
# Après la séance
$ ./scripts/collect_athlete_feedback.py --quick

📊 RPE (1-10) : 8

💭 Ressenti général en quelques mots
→ Difficile, jambes lourdes

📋 RÉSUMÉ DU FEEDBACK
====================================
📊 RPE : 8/10
💭 Ressenti : Difficile, jambes lourdes
====================================

💾 Sauvegarder ce feedback ? (O/n) : O
✅ Feedback sauvegardé !

📝 PROCHAINE ÉTAPE :
   ./scripts/prepare_analysis.py

# Générer l'analyse
$ ./scripts/prepare_analysis.py

🔄 Préparation du prompt d'analyse...
📥 Récupération de la dernière activité...
   ✅ Activité : S067-03-INT-SweetSpotMaintien
   📅 Date : 2025-11-14

📖 Chargement du contexte...
   ✅ Feedback athlète trouvé !
      RPE : 8/10
      Ressenti : Difficile, jambes lourdes...

✍️  Génération du prompt...
📋 Copie dans le presse-papier...
   ✅ Prompt copié !
   ✅ Feedback athlète consommé et effacé

# Le feedback est maintenant intégré au prompt
# Coller dans Claude.ai...

# Après analyse de Claude
$ ./scripts/insert_analysis.py
✅ Analyse insérée avec succès !
```

---

**Version** : 1.0
**Dernière mise à jour** : 15 novembre 2025
**Compatibilité** : prepare_analysis.py v2.1+, insert_analysis.py v2.0+
