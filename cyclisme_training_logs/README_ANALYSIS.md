# 🤖 Workflow d'Analyse Automatique

Système hybride pour générer des analyses d'entraînement avec Claude.ai

## 🎯 Objectif

Automatiser le processus d'analyse des séances en :
1. Récupérant les données depuis Intervals.icu
2. Générant un prompt optimisé pour Claude.ai
3. Insérant automatiquement l'analyse dans `workouts-history.md`

## 📋 Prérequis

### Configuration Intervals.icu

Créer `~/.intervals_config.json` :

```json
{
  "athlete_id": "i123456",
  "api_key": "YOUR_API_KEY_HERE"
}
```

**Obtenir l'API key :**
1. Connexion sur https://intervals.icu
2. Settings → Developer Settings → API Key
3. Copier la clé générée

### Dépendances Python

```bash
pip3 install requests
```

## ⚠️ Activités Strava : Données Limitées

**Problème** : Les activités synchronisées depuis Strava ont des restrictions API. Certaines métriques (puissance, découplage) peuvent être manquantes.

**Solution** : Les scripts détectent automatiquement les activités Strava et :
- ✅ Affichent un avertissement dans le terminal
- ✅ Ajoutent une note dans le prompt pour Claude.ai
- ✅ Claude analyse avec les données disponibles (FC, TSS, durée)

### Vérifier les sources de vos activités

```bash
./scripts/check_activity_sources.py
./scripts/check_activity_sources.py --last-days 14
```

Ce script liste toutes les activités récentes avec leur source pour identifier rapidement les activités Strava.

## 🚀 Workflow Complet

### Étape 1 : Préparer le Prompt

```bash
cd /Users/stephanejouve/cyclisme-training-logs
./scripts/prepare_analysis.py
```

**Ce script :**
- ✅ Récupère la dernière séance depuis Intervals.icu
- ✅ Charge le contexte athlète depuis `references/project_prompt_v2.md`
- ✅ Charge les 3 dernières séances pour contexte
- ✅ Génère un prompt optimisé pour Claude.ai
- ✅ Copie automatiquement dans le presse-papier macOS
- ✅ Affiche les instructions suivantes

**Options disponibles :**

```bash
# Analyser une séance spécifique par ID
./scripts/prepare_analysis.py --activity-id 123456789

# Utiliser une config alternative
./scripts/prepare_analysis.py --config ~/my_config.json

# Depuis un autre répertoire
./scripts/prepare_analysis.py --project-root /path/to/project
```

### Étape 2 : Obtenir l'Analyse de Claude.ai

1. **Ouvrir Claude.ai** : https://claude.ai
2. **Coller le prompt** : `Cmd+V` (déjà dans le presse-papier)
3. **Attendre la réponse** de Claude (~30 secondes)
4. **Copier UNIQUEMENT le bloc markdown** de l'analyse (de `###` jusqu'à `---`)

💡 **Astuce** : Claude génère parfois du texte explicatif avant/après. Ne copier QUE la partie structurée en markdown.

**Format attendu** : Voir [EXAMPLE_ANALYSIS_FORMAT.md](EXAMPLE_ANALYSIS_FORMAT.md) pour le format complet avec exemples.

### Étape 3 : Insérer l'Analyse

```bash
./scripts/insert_analysis.py
```

**Ce script :**
- ✅ Lit le presse-papier (réponse de Claude)
- ✅ Parse et extrait le bloc markdown
- ✅ Valide le format (9 sections obligatoires - voir format ci-dessous)
- ✅ Détecte les doublons potentiels
- ✅ Insère dans `logs/workouts-history.md` au bon endroit
- ✅ Affiche le `git diff` pour vérification
- ✅ Propose les commandes git pour commit

**Sections validées :**
1. Métriques Pré-séance
2. Exécution (métriques brutes)
3. Exécution Technique
4. Charge d'Entraînement
5. Validation Objectifs
6. Points d'Attention
7. Recommandations Progression
8. Métriques Post-séance

**Options disponibles :**

```bash
# Mode test (affiche sans modifier)
./scripts/insert_analysis.py --dry-run

# Lire depuis un fichier au lieu du presse-papier
./scripts/insert_analysis.py --file analysis.md

# Spécifier le répertoire des logs
./scripts/insert_analysis.py --logs-dir logs/
```

### Étape 4 : Vérifier et Commit

```bash
# Vérifier les modifications
git diff logs/workouts-history.md

# Ajouter au staging
git add logs/workouts-history.md

# Commit
git commit -m "Analyse: Séance du 14/11/2025"

# Push (optionnel)
git push
```

## 📊 Exemple Complet

```bash
# Terminal
$ ./scripts/prepare_analysis.py
🔄 Préparation du prompt d'analyse...

📥 Récupération de la dernière activité...
   ✅ Activité : S067-03-INT-SweetSpotMaintien
   📅 Date : 2025-11-14

📖 Chargement du contexte...
✍️  Génération du prompt...
📋 Copie dans le presse-papier...
   ✅ Prompt copié !

============================================================
✅ PROMPT PRÊT POUR CLAUDE.AI
============================================================

📝 ÉTAPES SUIVANTES :

1. Ouvrir Claude.ai dans votre navigateur
   → https://claude.ai

2. Coller le prompt (Cmd+V)

3. Attendre l'analyse de Claude

4. Copier la réponse de Claude (UNIQUEMENT le bloc markdown)

5. Exécuter le script d'insertion :
   python3 scripts/insert_analysis.py

============================================================
```

*→ Ouvrir Claude.ai, coller, obtenir réponse, copier*

```bash
$ ./scripts/insert_analysis.py
📋 Insertion de l'analyse dans workouts-history.md

📋 Lecture du presse-papier...
   ✅ Contenu récupéré

🔍 Extraction du bloc markdown...
   ✅ Bloc extrait

✓  Validation de l'analyse...
   ✅ Format valide

📄 Aperçu de l'analyse :
------------------------------------------------------------
### S067-03-INT-SweetSpotMaintien
Date : 14/11/2025

#### Métriques Pré-séance
- CTL : 59
- ATL : 70
...
------------------------------------------------------------

Insérer cette analyse ? (Y/n) : Y

✍️  Insertion dans workouts-history.md...
   ✅ Analyse insérée avec succès !

📊 Vérification des modifications...

============================================================
GIT DIFF
============================================================
[... git diff output ...]

============================================================
✅ INSERTION TERMINÉE
============================================================

📝 ÉTAPES SUIVANTES :

1. Vérifier les modifications :
   git diff logs/workouts-history.md

2. Ajouter au commit :
   git add logs/workouts-history.md

3. Commit :
   git commit -m "Analyse: Séance du 14/11/2025"

4. Push (optionnel) :
   git push

============================================================
```

## 🔧 Dépannage

### Erreur "athlete_id et api_key requis"

**Solution** : Créer `~/.intervals_config.json` avec vos credentials Intervals.icu

### Erreur "Erreur API: 401"

**Solution** : Vérifier que l'API key est correcte et valide

### Erreur "pbcopy not found" / "pbpaste not found"

**Solution** : Ces commandes sont spécifiques à macOS. Sur Linux :
- Installer `xclip` ou `xsel`
- Modifier les scripts pour utiliser ces outils

### "Sections manquantes dans l'analyse"

**Cause** : Claude.ai a généré une réponse incomplète

**Solution** :
1. Relancer Claude.ai avec le même prompt
2. Ou utiliser `--dry-run` pour voir ce qui manque
3. Éditer manuellement l'analyse avant insertion

### Doublons détectés

**Cause** : Une entrée existe déjà pour cette date/séance

**Solution** :
- Vérifier `logs/workouts-history.md` manuellement
- Supprimer le doublon existant si obsolète
- Ou forcer l'insertion en confirmant le warning

### Activité Strava avec données manquantes

**Cause** : Restrictions API Strava limitent l'accès aux données

**Solution** :
1. Le script détecte automatiquement et avertit
2. Claude.ai génère une analyse basée sur les données disponibles
3. Vérifier manuellement sur Intervals.icu web si besoin
4. Compléter l'analyse avec les données visibles sur le web

## 🎨 Personnalisation

### Changer le nombre de séances récentes dans le contexte

Éditer `prepare_analysis.py` ligne ~240 :

```python
recent_workouts = generator.load_recent_workouts(limit=3)  # ← Changer ici
```

### Modifier le format du prompt

Éditer la méthode `generate_prompt()` dans `prepare_analysis.py`

### Changer la position d'insertion

Éditer la méthode `insert_analysis()` dans `insert_analysis.py`

Par défaut, insère après `## Historique`. Pour changer :

```python
insert_marker = "## Historique"  # ← Changer le marqueur
```

## 📚 Structure des Scripts

```
scripts/
├── prepare_analysis.py       # Génère le prompt pour Claude.ai (séance)
│   ├── IntervalsAPI          # Client API Intervals.icu
│   └── PromptGenerator       # Génération du prompt
│
├── insert_analysis.py        # Insère l'analyse dans les logs
│   ├── ClipboardReader       # Lecture presse-papier
│   ├── AnalysisParser        # Parsing et validation
│   └── WorkoutHistoryManager # Gestion de workouts-history.md
│
├── collect_athlete_feedback.py # Collecte ressenti athlète (optionnel)
│   └── FeedbackCollector     # Questions structurées RPE/ressenti
│
├── prepare_weekly_report.py # Génère le prompt bilan hebdomadaire
│   └── WeeklyReportGenerator # Extraction séances + génération prompt
│
├── organize_weekly_report.py # Organise les 6 fichiers de bilan
│   └── WeeklyReportOrganizer # Parsing et sauvegarde automatique
│
├── check_activity_sources.py # Vérifie les sources des activités
│   └── IntervalsAPI          # Liste activités avec détection Strava
│
├── sync_intervals.py         # Script existant (sync automatique)
│
├── README_ANALYSIS.md        # Cette documentation
├── QUICKSTART.md             # Guide de démarrage rapide
├── EXAMPLE_ANALYSIS_FORMAT.md # Exemple de format d'analyse
├── WORKFLOW_WITH_FEEDBACK.md # Workflow avec feedback athlète
└── WEEKLY_REPORT_WORKFLOW.md # Workflow bilans hebdomadaires
```

## 🔄 Intégration avec sync_intervals.py

Les deux workflows sont complémentaires :

**sync_intervals.py** :
- ✅ Synchronisation automatique de TOUTES les séances
- ✅ Métriques brutes insérées automatiquement
- ❌ Pas d'analyse qualitative
- ❌ "Retour Athlète" et "Notes Coach" vides

**prepare_analysis.py + insert_analysis.py** :
- ✅ Analyse qualitative détaillée par Claude.ai
- ✅ "Retour Athlète" et "Notes Coach" remplis
- ✅ Contexte personnalisé
- ❌ Manuel (mais rapide : ~2 min/séance)
- ❌ Une séance à la fois

**Recommandation** :
1. Utiliser `sync_intervals.py` pour la sync de masse (hebdomadaire)
2. Utiliser `prepare_analysis.py` pour les séances importantes nécessitant analyse

## 🚀 Améliorations Futures

### Idées d'évolution

- [ ] Support Linux (xclip/xsel)
- [ ] Mode batch (analyser plusieurs séances)
- [ ] Intégration directe avec Claude API (pas de copier-coller)
- [ ] Export des analyses en JSON pour statistiques
- [ ] Génération automatique des bilans hebdomadaires
- [ ] Interface web simple (Flask/Streamlit)
- [ ] Cache des prompts générés
- [ ] Historique des analyses avec versioning

### Contributions

Pull requests bienvenues pour ajouter ces fonctionnalités !

## 📝 Notes

- **Pourquoi ce workflow hybride ?** Les activités Strava sont parfois bloquées par l'API Intervals.icu. Ce workflow permet d'analyser même ces séances.
- **Pourquoi ne pas utiliser l'API Claude ?** Pour l'instant, préférence pour le contrôle manuel et vérification visuelle de l'analyse avant insertion.
- **Temps moyen** : ~2 minutes par séance (30s préparation + 60s Claude + 30s insertion)

## 🙏 Crédits

- **Claude (Anthropic)** : Assistant coach et génération des analyses
- **Intervals.icu** : API d'entraînement
- **Stéphane Jouve** : Athlète et conception du workflow

---

**Version** : 1.0.0
**Dernière mise à jour** : 15 novembre 2025
**Statut** : ✅ Opérationnel
