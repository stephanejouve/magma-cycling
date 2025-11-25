# Guide d'Utilisation - Analyse Hebdomadaire

## Vue d'ensemble

Le script `weekly_analysis.py` génère automatiquement les **6 fichiers markdown obligatoires** du rapport hebdomadaire en utilisant Claude.ai pour analyser les données d'entraînement de la semaine.

## Prérequis

1. **Configuration API Intervals.icu**
   - Fichier `~/.intervals_config.json` avec :
     ```json
     {
       "athlete_id": "i123456",
       "api_key": "YOUR_API_KEY"
     }
     ```

2. **Données disponibles**
   - Séances analysées dans `logs/workouts-history.md`
   - Métriques accessibles via API Intervals.icu

3. **Environnement**
   - Python 3.x
   - Accès au presse-papier (pbcopy/pbpaste)
   - Accès à Claude.ai

## Usage de Base

### Analyse d'une semaine

```bash
# Avec calcul automatique de la date de début
python3 scripts/weekly_analysis.py S068

# Avec date de début spécifique
python3 scripts/weekly_analysis.py S068 --start-date 2024-11-18
```

### Format du numéro de semaine

- Format : `SXXX` (ex: S001, S068, S099)
- Le script calcule automatiquement :
  - Date de début (si non fournie)
  - Date de fin (début + 6 jours)
  - Semaine suivante (pour transition)

## Workflow

### Étape 1 : Collecte des données

Le script collecte automatiquement :

1. **Séances de la semaine** depuis `workouts-history.md`
   - Filtrées par plage de dates
   - Dédupliquées
   - Triées chronologiquement

2. **Métriques évolution** via API Intervals.icu
   - CTL/ATL/TSB début et fin de semaine
   - Évolution quotidienne
   - Poids début/fin

3. **Fichiers contexte**
   - `project_prompt_v2_1_revised.md` (profil athlète)
   - `cycling_training_concepts.md` (référence cyclisme)
   - Documentation complète (si disponible)

### Étape 2 : Génération du prompt

Le script génère un prompt complet contenant :
- Contexte athlète complet
- Toutes les analyses de séances de la semaine
- Métriques d'évolution
- Instructions pour générer les 6 fichiers

Le prompt est automatiquement copié dans le presse-papier.

### Étape 3 : Analyse par Claude

**Actions manuelles :**

1. Ouvrir Claude.ai : https://claude.ai
2. Coller le prompt (Cmd+V)
3. Attendre la génération (1-2 minutes)
4. Copier TOUTE la réponse de Claude
5. Appuyer sur Entrée dans le terminal

### Étape 4 : Extraction des fichiers

Le script parse automatiquement la réponse de Claude et extrait les 6 fichiers :

1. `workout_history_sXXX.md`
2. `metrics_evolution_sXXX.md`
3. `training_learnings_sXXX.md`
4. `protocol_adaptations_sXXX.md`
5. `transition_sXXX_sYYY.md`
6. `bilan_final_sXXX.md`

### Étape 5 : Sauvegarde

Les fichiers sont automatiquement sauvegardés dans :
```
logs/weekly_reports/SXXX/
```

Option de commit git automatique proposée.

## Les 6 Fichiers Générés

### 1. workout_history_sXXX.md

**Contenu :**
- Chronologie complète des séances de la semaine
- Reprise des analyses depuis workouts-history.md
- Métriques pré/post par séance
- Découvertes techniques
- Notes coach

### 2. metrics_evolution_sXXX.md

**Contenu :**
- Tableau FTP (si test effectué)
- Progression quotidienne TSB/Fatigue/Condition
- Évolution du poids
- CTL/ATL/TSB début → fin
- Validations techniques

### 3. training_learnings_sXXX.md

**Contenu :**
- Découvertes techniques majeures (3-5 points)
- Patterns physiologiques identifiés
- Protocoles validés ou invalidés
- Points de surveillance pour le futur

### 4. protocol_adaptations_sXXX.md

**Contenu :**
- Ajustements de seuils/critères
- Nouveaux protocoles établis
- Modifications hydratation/nutrition
- Exclusions mises à jour

### 5. transition_sXXX_sYYY.md

**Contenu :**
- État final de la semaine actuelle
- Acquisitions validées vs échecs
- 2-3 options de progression pour la semaine suivante
- Recommandation choisie avec justification

### 6. bilan_final_sXXX.md

**Contenu :**
- Objectifs visés vs réalisés
- Métriques finales comparées aux attentes
- 3-4 découvertes majeures
- Protocoles établis cette semaine
- Conclusion synthétique (2-3 lignes)

## Gestion des Erreurs

### Aucune séance trouvée

```
⚠️  Aucune séance trouvée pour cette semaine
```

**Solutions :**
- Vérifier les dates (--start-date)
- Vérifier que les séances sont bien dans `workouts-history.md`
- Vérifier le format des dates dans le fichier (JJ/MM/YYYY)

### API Intervals.icu indisponible

```
⚠️  API non disponible, skip métriques
```

**Solutions :**
- Vérifier `~/.intervals_config.json`
- Vérifier la connexion internet
- Le script continue sans les métriques

### Parsing de réponse échoué

```
⚠️  Attention : X fichier(s) extrait(s) au lieu de 6
```

**Solutions :**
- Vérifier que toute la réponse de Claude est copiée
- Vérifier que Claude a généré les 6 sections FILE
- Relancer Claude avec le prompt si nécessaire

## Exemples

### Analyse de la semaine courante

```bash
# Semaine 68 avec calcul auto des dates
python3 scripts/weekly_analysis.py S068
```

### Analyse d'une semaine spécifique

```bash
# Semaine du 18 au 24 novembre 2024
python3 scripts/weekly_analysis.py S047 --start-date 2024-11-18
```

### Analyse avec commit git

```bash
python3 scripts/weekly_analysis.py S068
# À la fin, répondre 'o' pour commiter automatiquement
```

## Structure des Fichiers de Sortie

```
logs/
└── weekly_reports/
    └── S068/
        ├── workout_history_S068.md
        ├── metrics_evolution_S068.md
        ├── training_learnings_S068.md
        ├── protocol_adaptations_S068.md
        ├── transition_S068_S069.md
        └── bilan_final_S068.md
```

## Conseils d'Utilisation

1. **Timing optimal**
   - Lancer le dimanche soir ou lundi matin
   - Quand toutes les séances de la semaine sont analysées

2. **Qualité des données**
   - S'assurer que toutes les séances sont analysées dans workouts-history.md
   - Vérifier que les métriques Intervals.icu sont à jour

3. **Révision post-génération**
   - Relire les fichiers générés
   - Corriger manuellement si nécessaire
   - Valider la cohérence entre les 6 fichiers

4. **Versioning**
   - Utiliser le commit git automatique pour tracer l'historique
   - Les commits incluent le détail des fichiers générés

## Dépannage

### Le script ne trouve pas prepare_analysis.py

**Erreur :**
```
ModuleNotFoundError: No module named 'prepare_analysis'
```

**Solution :**
```bash
# Lancer depuis la racine du projet
cd /Users/stephanejouve/cyclisme-training-logs
python3 scripts/weekly_analysis.py S068
```

### Presse-papier ne fonctionne pas

**Erreur :**
```
⚠️  Erreur copie presse-papier
```

**Solution :**
- Sur macOS : pbcopy/pbpaste sont natifs
- Sur Linux : installer xclip
- En dernier recours : le prompt s'affiche dans le terminal

### Format de date incorrect dans workouts-history.md

**Problème :**
Les séances ne sont pas détectées.

**Solution :**
Vérifier que les dates dans workouts-history.md sont au format :
```markdown
### Nom de la Séance
Date : 14/11/2024
```

## Référence Complète

- **Documentation projet** : `Documentation_Complète_du_Suivi_v1_5.md`
- **Workflow quotidien** : `scripts/WORKFLOW_GUIDE.md`
- **Script préparation** : `scripts/prepare_analysis.py`
- **Exemples bilans** : `logs/weekly_reports/*/`

## Support

En cas de problème :
1. Vérifier les prérequis
2. Lire les messages d'erreur complets
3. Consulter ce guide
4. Vérifier les fichiers de logs

---

**Version** : 1.0
**Dernière mise à jour** : 2024-11-23
**Auteur** : Claude Code
