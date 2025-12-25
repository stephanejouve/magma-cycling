# Workflow Quotidien - Cyclisme Training Logs

**Documentation complète du workflow d'analyse journalière**

---

## 📋 Vue d'Ensemble

Ce document décrit les 4 workflows quotidiens disponibles pour traiter tes séances d'entraînement cyclisme.

**Principe**: Chaque séance doit être analysée avec l'un de ces workflows selon le contexte.

---

## 🎯 Les 4 Workflows

### 1️⃣ Workflow Standard (Le Plus Courant)

**Alias**: `train`

**Quand l'utiliser**:
- Après chaque séance normale (Lun/Mar/Jeu/Sam/Dim)
- Quand tu veux un traitement complet avec feedback

**Ce qu'il fait**:
1. ✅ Collecte ton feedback athlète (RPE, sensations, HRRc)
2. ✅ Génère l'analyse AI de la séance (via Claude.ai)
3. ✅ Met à jour `logs/workouts-history.md`
4. ✅ Crée un commit git avec l'analyse
5. ✅ Affiche un résumé de la séance

**Durée**: 3-5 minutes (interaction AI requise)

**Exemple**:
```bash
# Après ta séance Zwift du lundi soir
train
```

**Interaction requise**:
- Copier le prompt généré → Claude.ai
- Copier la réponse de Claude → Terminal
- Confirmer le commit git (o/n)

---

### 2️⃣ Workflow avec Asservissement Planning

**Alias**: `trains --week-id SXXX`

**Quand l'utiliser**:
- Mercredi soir (milieu de semaine)
- Vendredi soir (avant weekend)
- Quand tu sens de la fatigue et veux ajuster le planning

**Ce qu'il fait**:
1. ✅ Tout du workflow standard (feedback + analyse + commit)
2. ✅ **Analyse les signaux de fatigue** (HRV, RPE, TSB)
3. ✅ **Propose des ajustements planning** si nécessaire
4. ✅ Peut remplacer workouts sur Intervals.icu (avec confirmation)

**Durée**: 5-8 minutes (+ temps décision ajustements)

**Exemple**:
```bash
# Mercredi soir, semaine S073, après séance
trains --week-id S073
```

**Scénarios d'ajustement typiques**:
- HRV baisse de -15% → Propose récupération active au lieu de Sweet-Spot
- RPE > 9 deux jours de suite → Propose jour de repos additionnel
- TSB < 0 avec VO2 max prévu → Propose report du workout

**⚠️ Recommandation**: Utiliser 2-3 fois par semaine maximum (ne pas sur-ajuster)

---

### 3️⃣ Workflow Rapide (Debug/Multi-Séances)

**Alias**: `train-fast`

**Quand l'utiliser**:
- Multi-séances rapprochées (2 workouts le même jour)
- Rattrapage de plusieurs analyses en une fois
- Mode debug (test modifications code)

**Ce qu'il fait**:
1. ✅ Génère l'analyse AI uniquement
2. ⏩ **Skip** la collecte feedback manuel
3. ⏩ **Skip** le commit git

**Durée**: 1-2 minutes

**Exemple**:
```bash
# Samedi: séance matinale + séance après-midi
train              # Première séance (complet)
train-fast         # Deuxième séance (rapide)

# Puis en fin de journée, commit groupé:
cd ~/cyclisme-training-logs
git add .
git commit -m "Analyses: 2 séances samedi S073-05"
```

**⚠️ Attention**: Ne pas oublier de commiter manuellement plus tard!

---

### 4️⃣ Workflow Réconciliation (Rattrapage Batch)

**Alias**: `trainr --week-id SXXX`

**Quand l'utiliser**:
- Plusieurs jours sans analyse (retour de voyage, maladie)
- Séances planifiées mais sautées/annulées
- Nettoyage de semaine avant analyse hebdomadaire

**Ce qu'il fait**:
1. ✅ Détecte les séances planifiées non exécutées
2. ✅ Propose classification pour chaque séance:
   - `skipped`: Sautée volontairement
   - `cancelled`: Annulée pour cause valable
   - `rescheduled`: Reportée à une autre date
3. ✅ Met à jour le planning sur Intervals.icu
4. ✅ Crée un commit batch des modifications

**Durée**: 5-10 minutes (selon nombre de séances)

**Exemple**:
```bash
# Dimanche soir, semaine S073, avant de lancer wa
trainr --week-id S073
```

**Cas d'usage typiques**:
- 3 jours sans entraînement → Classifier les 3 workouts manqués
- Semaine avec 2 séances sautées → Nettoyer le planning
- Avant `wa` (analyse hebdo) → S'assurer que tout est à jour

---

## 📊 Tableau Comparatif

| Workflow | Alias | Feedback | Analyse | Git | Planning | Durée | Fréquence |
|----------|-------|----------|---------|-----|----------|-------|-----------|
| **Standard** | `train` | ✅ | ✅ | ✅ | ❌ | 3-5min | Quotidien |
| **Asservissement** | `trains --week-id` | ✅ | ✅ | ✅ | ✅ | 5-8min | 2-3x/semaine |
| **Rapide** | `train-fast` | ❌ | ✅ | ❌ | ❌ | 1-2min | Occasionnel |
| **Réconciliation** | `trainr --week-id` | ❌ | ✅ | ✅ | ✅ | 5-10min | 1x/semaine |

---

## 🔄 Enchainement Quotidien Recommandé

### Lundi

```bash
# MATIN: Cycle hebdomadaire complet
wa --week-id S072 --start-date 2025-12-16       # 1. Analyser semaine passée
wp --week-id S073 --start-date 2025-12-23       # 2. Planifier semaine courante
wu --week-id S073 --start-date 2025-12-23       # 3. Uploader workouts

# SOIR: Première séance de la semaine
train
```

### Mardi

```bash
# SOIR: Séance standard
train
```

### Mercredi

```bash
# SOIR: Séance avec vérification planning
trains --week-id S073
```

**Pourquoi mercredi?** Milieu de semaine, bon moment pour ajuster si fatigue accumulée.

### Jeudi

```bash
# SOIR: Séance standard
train
```

### Vendredi

```bash
# SOIR: Séance avec vérification planning
trains --week-id S073
```

**Pourquoi vendredi?** Ajuster le weekend si nécessaire (volume samedi, repos dimanche).

### Samedi

```bash
# MATIN: Séance volume weekend (09:00)
train

# Si 2e séance après-midi:
train-fast
```

### Dimanche

```bash
# SOIR: Séance finale ou repos
train  # Si séance

# Réconciliation si séances manquées dans la semaine
trainr --week-id S073  # Optionnel, si nécessaire
```

---

## 📅 Cycle Hebdomadaire Complet

Voici le **cycle complet** sur 7 jours:

```
┌─────────────────────────────────────────────────────────┐
│ LUNDI (Jour J)                                          │
│ ├─ MATIN: wa S072 → wp S073 → wu S073 (cycle hebdo)   │
│ └─ SOIR: train (1ère séance semaine)                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ MARDI (J+1)                                             │
│ └─ SOIR: train                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ MERCREDI (J+2) ⚡ CHECKPOINT 1                          │
│ └─ SOIR: trains --week-id S073 (avec asservissement)   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ JEUDI (J+3)                                             │
│ └─ SOIR: train                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ VENDREDI (J+4) ⚡ CHECKPOINT 2                          │
│ └─ SOIR: trains --week-id S073 (ajustement weekend)    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ SAMEDI (J+5) 🏔️ VOLUME WEEKEND                         │
│ ├─ MATIN (09:00): train (séance longue)                │
│ └─ APREM (optionnel): train-fast (si 2e séance)        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ DIMANCHE (J+6) 🧹 CLEAN SLATE                           │
│ ├─ SOIR: train (si séance) OU repos                    │
│ └─ SOIR: trainr --week-id S073 (si réconciliation)     │
└─────────────────────────────────────────────────────────┘
                          ↓
                  [Retour LUNDI J+7]
```

---

## 💡 Règles d'Or

### 1. Une Séance = Un Workflow
**Jamais de séance non analysée.** Traite chaque workout le jour même.

### 2. Mercredi + Vendredi = Asservissement
Ces 2 checkpoints hebdomadaires permettent d'ajuster le planning si nécessaire.

### 3. Dimanche Soir = Clean Slate
Avant lundi matin (cycle hebdo), tout doit être propre:
- Toutes les séances analysées
- Séances manquées réconciliées
- Git à jour

### 4. Multi-Séances = train + train-fast
Si 2 séances le même jour: feedback complet sur la 1ère, rapide sur la 2e.

### 5. Commit Quotidien
Chaque jour = 1 commit minimum. Historique git propre = meilleur suivi.

---

## 🚨 Cas Particuliers

### Séance Annulée (Blessure/Maladie)

```bash
# Ne pas laisser le workout planifié "pending"
trainr --week-id S073

# Sélectionner "cancelled" avec raison
# → Le planning Intervals.icu sera mis à jour
```

### Séance Reportée (Imprévu)

```bash
trainr --week-id S073

# Sélectionner "rescheduled"
# → Permet de tracker les reports pour analyse hebdo
```

### Plusieurs Jours sans Analyse

```bash
# Rattraper toutes les séances en batch
cd ~/cyclisme-training-logs

# 1. Réconcilier les séances manquées
trainr --week-id S073

# 2. Analyser les séances exécutées (une par une)
train --activity-id 123456  # Séance 1
train --activity-id 123457  # Séance 2
train --activity-id 123458  # Séance 3
```

### Mode Debug (Développement)

```bash
# Tester modifications code sans feedback/git
train-fast

# Ou avec options explicites
train --skip-feedback --skip-git
```

---

## 🔧 Options Avancées

### Analyser une Séance Spécifique

```bash
# Par défaut, train prend la dernière activité
train

# Forcer une activité spécifique par ID
train --activity-id i123456
```

### Skip Options

```bash
# Skip feedback uniquement
train --skip-feedback

# Skip git uniquement
train --skip-git

# Skip les deux (= train-fast)
train --skip-feedback --skip-git
```

### Mode Réconciliation avec Skip

```bash
# Réconciliation rapide (sans git interactif)
trainr --week-id S073 --skip-git
```

---

## 📈 Métriques de Suivi

Pour vérifier que ton workflow quotidien est optimal:

### Commits Git

```bash
# Nombre de commits cette semaine (devrait être ~6-7)
git log --since="1 week ago" --oneline | wc -l
```

**Target**: 6-7 commits/semaine (1 par jour de séance + 1 hebdo)

### Historique Workouts

```bash
# Dernières séances analysées
tail -20 logs/workouts-history.md
```

**Vérifier**: Aucune séance > 2 jours sans analyse

### Planning Cohérence

```bash
# Vérifier planning semaine
check
```

**Vérifier**: Pas de "pending" en retard, statuts corrects

---

## 🎯 Checklist Quotidienne

Après chaque séance, pose-toi ces questions:

- [ ] La séance est-elle terminée et synchronisée sur Intervals.icu?
- [ ] Quel workflow utiliser? (train / trains / train-fast)
- [ ] Ai-je besoin de vérifier le planning? (Mer/Ven → trains)
- [ ] Y a-t-il une 2e séance prévue aujourd'hui? (train-fast pour la 2e)
- [ ] Le commit git est-il fait? (vérifier avec `git status`)

---

## 📚 Ressources Complémentaires

### Fichiers de Référence

- `COMMANDS.md` - Quick reference des alias
- `Documentation_Complète_du_Suivi_v1_5.md` - Documentation projet complète
- `UNIFORMISATION_WEEK_ID.md` - Format arguments standardisés

### Scripts Associés

- `workflow_coach.py` - Script principal (via alias `train`)
- `upload_workouts.py` - Upload workouts (via alias `wu`)
- `weekly_planner.py` - Planning hebdo (via alias `wp`)
- `weekly_analysis.py` - Analyse hebdo (via alias `wa`)

### Logs et Historique

- `logs/workouts-history.md` - Historique toutes séances
- `logs/weekly_reports/SXXX/` - Rapports hebdomadaires

---

## 🆘 Troubleshooting

### "Poetry command not found"

```bash
# Vérifier Poetry installé
poetry --version

# Si erreur, réinstaller
curl -sSL https://install.python-poetry.org | python3 -
```

### "API Intervals.icu non disponible"

```bash
# Vérifier config
cat ~/.intervals_config.json

# Doit contenir:
# {
#   "athlete_id": "iXXXXXX",
#   "api_key": "XXXXX"
# }
```

### "Git commit failed"

```bash
# Vérifier statut
cd ~/cyclisme-training-logs
git status

# Résoudre conflits si nécessaire
git add .
git commit -m "fix: résolution conflit"
```

### "Prompt trop long pour Claude.ai"

```bash
# Utiliser --skip-feedback pour réduire
train --skip-feedback
```

---

## 📞 Support

**Questions ou bugs**:
- Vérifier `COMMANDS.md` pour quick reference
- Consulter `--help` sur chaque commande
- Check git history: `git log --oneline -20`

---

**Version**: 1.0
**Date**: 2025-12-21
**Dernière mise à jour**: Ajout workflows asservissement et réconciliation
