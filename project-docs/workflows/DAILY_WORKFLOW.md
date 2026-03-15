# Workflow Quotidien - Magma Cycling

**Version** : 2.0
**Date** : Mars 2026
**Architecture** : Facades + mixins (post-refactoring Phase 3)

---

## Vue d'Ensemble

Ce document decrit les 4 workflows quotidiens disponibles pour traiter les seances d'entrainement cyclisme.

**Principe** : Chaque seance doit etre analysee avec l'un de ces workflows selon le contexte.

**Regle Control Tower** : Toute modification de planning passe par `PlanningControlTower` — backup automatique, audit, atomicite. Ne jamais editer les fichiers planning manuellement.

---

## Les 4 Workflows

### 1. Workflow Standard

**Alias** : `train` | **Commande** : `poetry run workflow-coach`
**Facade** : `WorkflowCoach` | **Mixins** : `FeedbackMixin`, `AIAnalysisMixin`, `HistoryMixin`, `GitOpsMixin`

**Quand l'utiliser** :
- Apres chaque seance normale (Lun/Mar/Jeu/Sam/Dim)
- Traitement complet avec feedback

**Ce qu'il fait** :
1. Collecte le feedback athlete (RPE, sensations, HRRc)
2. Genere l'analyse AI de la seance via AI provider
3. Met a jour `workouts-history.md`
4. Cree un commit git avec l'analyse
5. Affiche un resume de la seance

**Duree** : 3-5 minutes

```bash
train
```

---

### 2. Workflow avec Asservissement Planning

**Alias** : `trains --week-id SXXX` | **Commande** : `poetry run workflow-coach --servo-mode --week-id SXXX`
**Facade** : `WorkflowCoach` | **Mixins** : les memes + `ServoControlMixin`, `IntervalsAPIMixin`

**Quand l'utiliser** :
- Mercredi soir (milieu de semaine)
- Vendredi soir (avant weekend)
- Quand fatigue ressentie et ajustement planning necessaire

**Ce qu'il fait** :
1. Tout du workflow standard (feedback + analyse + commit)
2. Analyse les signaux de fatigue (HRV, RPE, TSB)
3. Propose des ajustements planning si necessaire
4. Peut remplacer workouts sur Intervals.icu (avec confirmation)

**Duree** : 5-8 minutes

```bash
trains --week-id S085
```

**Scenarios d'ajustement typiques** :
- HRV baisse de -15% : Propose recuperation active au lieu de Sweet-Spot
- RPE > 9 deux jours de suite : Propose jour de repos additionnel
- TSB < 0 avec VO2 max prevu : Propose report du workout

---

### 3. Workflow Rapide

**Alias** : `train-fast` | **Commande** : `poetry run workflow-coach --skip-feedback --skip-git`
**Facade** : `WorkflowCoach` | **Mixins** : `AIAnalysisMixin`, `HistoryMixin` (feedback et git skipes)

**Quand l'utiliser** :
- Multi-seances rapprochees (2 workouts le meme jour)
- Rattrapage de plusieurs analyses en une fois
- Mode debug

**Duree** : 1-2 minutes

```bash
train-fast
```

---

### 4. Workflow Reconciliation

**Alias** : `trainr --week-id SXXX` | **Commande** : `poetry run workflow-coach --reconcile --week-id SXXX`
**Facade** : `WorkflowCoach` | **Mixins** : `ReconciliationMixin`, `SpecialSessionsMixin`, `GitOpsMixin`

**Quand l'utiliser** :
- Plusieurs jours sans analyse (retour de voyage, maladie)
- Seances planifiees mais sautees/annulees
- Nettoyage de semaine avant analyse hebdomadaire

**Duree** : 5-10 minutes

```bash
trainr --week-id S085
```

---

## Tableau Comparatif

| Workflow | Alias | Feedback | Analyse | Git | Planning | Duree | Frequence |
|----------|-------|----------|---------|-----|----------|-------|-----------|
| **Standard** | `train` | oui | oui | oui | non | 3-5min | Quotidien |
| **Asservissement** | `trains --week-id` | oui | oui | oui | oui | 5-8min | 2-3x/semaine |
| **Rapide** | `train-fast` | non | oui | non | non | 1-2min | Occasionnel |
| **Reconciliation** | `trainr --week-id` | non | oui | oui | oui | 5-10min | 1x/semaine |

---

## Enchainement Quotidien Recommande

### Lundi
```bash
# MATIN : Cycle hebdomadaire complet
poetry run weekly-analysis --week-id S084     # 1. Analyser semaine passee (wa)
poetry run weekly-planner S085 --start-date 2026-03-16  # 2. Planifier semaine (wp)
poetry run upload-workouts --week-id S085     # 3. Uploader workouts (wu)

# SOIR : Premiere seance de la semaine
train
```

### Mardi / Jeudi
```bash
train  # Seance standard
```

### Mercredi (Checkpoint 1)
```bash
trains --week-id S085  # Avec asservissement
```

### Vendredi (Checkpoint 2)
```bash
trains --week-id S085  # Ajustement weekend
```

### Samedi
```bash
train              # Seance longue matin
train-fast         # 2e seance optionnelle
```

### Dimanche
```bash
train              # Si seance
trainr --week-id S085  # Reconciliation si necessaire
```

---

## Automation LaunchAgent

La chaine quotidienne est automatisee via LaunchAgents :

| Heure | Service | Description |
|-------|---------|-------------|
| 21:00 | `withings-presync` | Sync donnees sante Withings vers Intervals.icu |
| 21:30 | `daily-sync` | Synchronisation activites + analyse AI auto + servo |
| 22:00 | `adherence-check` | Verification adherence planning |
| 23:00 | `pid-evaluation` | Evaluation PID quotidienne |

Le dimanche a 20:00, `end-of-week --auto` boucle la semaine et genere le planning S+1 automatiquement.

---

## Regles d'Or

### 1. Une Seance = Un Workflow
Jamais de seance non analysee. Traite chaque workout le jour meme.

### 2. Mercredi + Vendredi = Asservissement
Ces 2 checkpoints hebdomadaires permettent d'ajuster le planning si necessaire.

### 3. Dimanche Soir = Clean Slate
Avant lundi matin, tout doit etre propre : toutes les seances analysees, seances manquees reconciliees, git a jour.

### 4. Multi-Seances = train + train-fast
Si 2 seances le meme jour : feedback complet sur la 1ere, rapide sur la 2e.

### 5. Control Tower = Source de verite
Toute modification planning passe par PlanningControlTower. Ne jamais editer les JSON directement.

### 6. Commit Quotidien
Chaque jour = 1 commit minimum. Historique git propre = meilleur suivi.

---

## Facades et Mixins

| Facade | Repertoire mixins | Nombre |
|--------|------------------|--------|
| `WorkflowCoach` | `workflows/coach/` | 11 mixins |
| `DailySync` | `workflows/sync/` | 7 mixins |
| `EndOfWeekWorkflow` | `workflows/eow/` | 5 mixins |
| `WeeklyPlanner` | `workflows/planner/` | 4 mixins |
| `WorkoutUploader` | `workflows/uploader/` | 3 mixins |
| `PromptGenerator` | `workflows/prompt/` | 4 mixins |

---

## Cas Particuliers

### Seance Annulee (Blessure/Maladie)
```bash
trainr --week-id S085
# Selectionner "cancelled" avec raison
```

### Seance Reportee (Imprevu)
```bash
trainr --week-id S085
# Selectionner "rescheduled"
```

### Plusieurs Jours sans Analyse
```bash
# 1. Reconcilier les seances manquees
trainr --week-id S085

# 2. Analyser les seances executees (une par une)
train --activity-id i129821327
train --activity-id i129821328
```

---

## Troubleshooting

### API Intervals.icu non disponible
```bash
# Verifier config
poetry run python -c "from magma_cycling.api.intervals_client import IntervalsClient; print('OK')"
```

### Git commit echoue
```bash
git status
git add logs/workouts-history.md
git commit -m "Analyse: seance"
```

---

**Version** : 2.0
**Date** : Mars 2026
