# Guide Workflow Coach - Analyse de Seance

**Version** : 2.0
**Date** : Mars 2026
**Architecture** : Facade `WorkflowCoach` + 11 mixins

---

## Demarrage Rapide

```bash
# Lancement standard (guidage complet)
poetry run workflow-coach

# Mode rapide (sans feedback ni git)
poetry run workflow-coach --skip-feedback --skip-git

# Analyser une seance specifique
poetry run workflow-coach --activity-id i123456

# Mode asservissement
poetry run workflow-coach --servo-mode --week-id S085

# Mode reconciliation
poetry run workflow-coach --reconcile --week-id S085

# Mode automatique (non interactif)
poetry run workflow-coach --auto
```

---

## Architecture

La facade `WorkflowCoach` delegue a 11 mixins specialises dans `workflows/coach/` :

| Mixin | Responsabilite | Methodes principales |
|-------|---------------|---------------------|
| **GapDetectionMixin** | Detection seances non analysees | `step_1b_detect_all_gaps()`, `_detect_unanalyzed_activities()` |
| **FeedbackMixin** | Collecte ressenti athlete | `step_2_collect_feedback()`, `_validate_feedback_collection()` |
| **AIAnalysisMixin** | Preparation et envoi analyse AI | `step_3_prepare_analysis()`, `_detect_week_id()` |
| **SessionDisplayMixin** | Affichage prompt et analyse | `step_4_paste_prompt()`, `step_5_validate_analysis()` |
| **HistoryMixin** | Insertion dans workouts-history | `step_6_insert_analysis()`, `_insert_to_history()` |
| **GitOpsMixin** | Commit git automatique | `step_7_git_commit()`, `_optional_git_commit()` |
| **ServoControlMixin** | Asservissement planning | `_apply_lighten()`, `_update_planning_json()` |
| **IntervalsAPIMixin** | Communication API Intervals.icu | `load_credentials()`, `load_workout_templates()` |
| **ReconciliationMixin** | Reconciliation planifie vs realise | `reconcile_week()`, `_display_reconciliation_report()` |
| **SpecialSessionsMixin** | Repos, annulations, sauts | `_handle_rest_cancellations()`, `_handle_skipped_sessions()` |
| **UIHelpersMixin** | Utilitaires affichage terminal | Helpers d'affichage interactif |

---

## Pipeline en 7 etapes

### Etape 1 : Detection multi-seances
**Mixin** : `GapDetectionMixin`

Le systeme detecte automatiquement les activites non analysees :
- Charge l'etat depuis `.workflow_state.json`
- Interroge l'API Intervals.icu (7-30 derniers jours)
- Identifie les gaps (seances non analysees)
- Menu interactif : derniere / choisir / batch

### Etape 2 : Collecte feedback (optionnel)
**Mixin** : `FeedbackMixin`

Capture le ressenti subjectif de l'athlete : RPE, sensations, HRRc.
Skip avec `--skip-feedback`. Les donnees wellness Intervals.icu (Feel, sommeil, CTL/ATL/TSB) sont toujours incluses dans le prompt.

### Etape 3 : Preparation analyse AI
**Mixin** : `AIAnalysisMixin`

- Detecte le week_id correspondant a l'activite
- Verifie la disponibilite du planning
- Construit le prompt via `PromptBuilder.build_prompt(mission="daily_feedback")`
- Envoie au provider AI selectionne

### Etape 4 : Affichage et envoi
**Mixin** : `SessionDisplayMixin`

Selon le provider :
- **clipboard** : copie dans le presse-papier, attend le retour utilisateur
- **claude_api / mistral_api / openai_api** : appel API direct, affichage resultat
- **ollama** : appel local

### Etape 5 : Validation analyse
**Mixin** : `SessionDisplayMixin`

Checklist de validation : format markdown, sections presentes, coherence contenu.

### Etape 6 : Insertion dans les logs
**Mixin** : `HistoryMixin`

- Detecte le type de session depuis le markdown
- Verifie les doublons (detection paranoiaque)
- Insere dans `workouts-history.md`

### Etape 7 : Commit git
**Mixin** : `GitOpsMixin`

Commit automatique avec message genere. Skip avec `--skip-git`.

---

## AI Provider System

Le systeme utilise `AIProviderFactory` pour abstraire le fournisseur AI :

| Provider | Usage | Configuration |
|----------|-------|---------------|
| **claude_api** | Analyses automatiques (daily-sync, end-of-week) | `ANTHROPIC_API_KEY` |
| **mistral_api** | Alternative/fallback | `MISTRAL_API_KEY` |
| **openai_api** | Alternative | `OPENAI_API_KEY` |
| **ollama** | Modele local | Ollama installe localement |
| **clipboard** | Mode interactif (workflow-coach) | Aucune config requise |

Le provider est selectionne via `--provider` en CLI ou configure par defaut selon le workflow :
- `workflow-coach` : clipboard (interactif)
- `daily-sync --ai-analysis` : claude_api
- `end-of-week --auto` : claude_api avec fallback mistral_api

---

## Services transverses

### Control Tower (`planning/control_tower.py`)

Gardien centralise de tous les fichiers planning :
- **Lecture** : `PlanningControlTower.read_week()` — acces en lecture seule
- **Modification** : `PlanningControlTower.modify_week()` — context manager avec backup automatique
- **Audit** : chaque operation loggee en JSONL (timestamp, operation, tool, reason)
- **Atomicite** : une seule modification a la fois, rollback si erreur

### Prompt Builder (`prompts/prompt_builder.py`)

Construction standardisee des prompts AI :
- `build_prompt(mission="daily_feedback"|"weekly_planning")` : assemble systeme + mission + contexte
- `format_athlete_profile()` : profil athlete depuis `config/athlete_context.yaml`
- `load_current_metrics()` : FTP, CTL, ATL, ramp_rate depuis env + API

### Event Sync (`utils/event_sync.py`)

Logique de synchronisation partagee entre `WorkoutUploader` et MCP :
- `evaluate_sync()` : decide CREATE / UPDATE / SKIP
- `calculate_description_hash()` : detection de changements
- `compute_start_time()` : calcul heure de debut

---

## Flux de donnees

```
Intervals.icu API
       |
       v
PromptGenerator (prepare_analysis.py)
       |
       v
PromptBuilder.build_prompt(mission="daily_feedback")
       |
       v
AIProvider (claude_api / mistral_api / clipboard)
       |
       v
HistoryMixin._insert_to_history()
       |
       v
workouts-history.md (data repo)
       |
       v
GitOpsMixin.step_7_git_commit()
```

---

## Modes d'utilisation

### Mode Standard
```bash
poetry run workflow-coach
```
Guidage complet interactif avec feedback, analyse AI, insertion, commit.

### Mode Rapide
```bash
poetry run workflow-coach --skip-feedback --skip-git
```
Analyse uniquement, sans feedback ni commit.

### Mode Asservissement
```bash
poetry run workflow-coach --servo-mode --week-id S085
```
Analyse + ajustement automatique du planning futur selon signaux de fatigue.

### Mode Reconciliation
```bash
poetry run workflow-coach --reconcile --week-id S085
```
Detection des seances planifiees non executees, classification batch.

### Mode Automatique
```bash
poetry run workflow-coach --auto
```
Non interactif, utilise pour automation LaunchAgent.

---

## Options de ligne de commande

| Option | Description |
|--------|-------------|
| `--skip-feedback` | Ne pas collecter le feedback athlete |
| `--skip-git` | Ne pas proposer le commit git |
| `--activity-id ID` | Analyser une seance specifique (ID Intervals.icu, ex: `i129821327`) |
| `--week-id SXXX` | Specifier la semaine cible |
| `--servo-mode` | Activer l'asservissement planning |
| `--reconcile` | Mode reconciliation batch |
| `--auto` | Mode non interactif |
| `--provider NAME` | Forcer un AI provider |

---

## Gestion des erreurs

| Erreur | Cause | Solution |
|--------|-------|----------|
| Erreur API Intervals.icu | Credentials invalides | Verifier `~/.intervals_config.json` |
| Format markdown invalide | Copie incorrecte | Recopier uniquement le bloc markdown |
| Doublon detecte | Analyse deja inseree | Utiliser `scripts/debug/clean_duplicates.py` |
| Interruption Ctrl+C | Arret utilisateur | Relancer, etapes deja completees conservees |

---

**Version** : 2.0
**Date** : Mars 2026
