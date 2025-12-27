# 🎯 Guide Workflow Coach - Analyse de Séance

Le **Workflow Coach** est un orchestrateur interactif qui guide l'utilisateur à travers toutes les étapes d'analyse d'une séance cyclisme avec Claude.ai.

## 🚀 Démarrage Rapide

```bash
# Lancement standard (guidage complet)
python3 scripts/workflow_coach.py

# Mode rapide (sans feedback ni git)
python3 scripts/workflow_coach.py --skip-feedback --skip-git

# Analyser une séance spécifique
python3 scripts/workflow_coach.py --activity-id i123456
```

## 🔍 Détection Multi-Séances (NOUVEAU)

Le workflow intègre désormais la **détection automatique des séances non analysées** !

### Fonctionnement

Lorsque tu lances le workflow sans spécifier `--activity-id`, le système :

1. **Charge l'état** : Lit `.workflow_state.json` pour savoir quelle est la dernière séance analysée
2. **Récupère les activités récentes** : Appelle l'API Intervals.icu pour les 7-30 derniers jours
3. **Détecte les gaps** : Identifie les séances non encore analysées
4. **Affiche un menu interactif** selon le nombre détecté :
   - **0 séance** : Message "Aucune activité non analysée !"
   - **1 séance** : Propose d'analyser directement ou d'annuler
   - **2+ séances** : Menu complet avec 4 options

### Menu Interactif (2+ séances)

```
📊 3 ACTIVITÉS NON ANALYSÉES DÉTECTÉES

1. [2025-11-21] Zwift - Morning Endurance (partie 1)
   ID: i107779438 | Durée: 45min | TSS: 42

2. [2025-11-21] Zwift - Morning Endurance (partie 2)
   ID: i107779439 | Durée: 43min | TSS: 40

3. [2025-11-20] Sweet Spot 2x15min
   ID: i107779437 | Durée: 75min | TSS: 68

OPTIONS :
  1 - Analyser la DERNIÈRE séance uniquement
  2 - Choisir UNE séance spécifique
  3 - Analyser TOUTES en mode batch
  0 - Annuler
```

### Cas d'Usage

#### Déconnexion Zwift
Tu as fait une séance Zwift qui s'est déconnectée → 2 activités distinctes dans Intervals.icu

**Solution** : Option 3 (mode batch) pour analyser les deux en une seule session

#### Weekend Multi-Séances
Tu analyses le lundi, tu as fait 3 séances samedi-dimanche

**Solution** : Option 3 (mode batch) ou Option 2 (choisir les plus importantes)

#### Rattrapage
Tu n'as pas analysé depuis 1 semaine → 5 séances en attente

**Solution** : Option 3 (mode batch) pour tout traiter d'un coup

### Mode Batch

Quand tu sélectionnes l'option 3, le système :

1. **Boucle sur chaque séance** (ex: "📊 SÉANCE 2/3")
2. **Génère le prompt** pour chaque activité
3. **Copie dans le presse-papier**
4. **Attend ton signal** après avoir copié la réponse de Claude
5. **Propose l'insertion automatique** via `insert_analysis.py`
6. **Marque comme analysée** dans le state
7. **Passe à la suivante**

**Avantage** : Tu restes dans Claude.ai, pas besoin de relancer le workflow entre chaque séance !

### Option --list

Liste les séances non analysées sans lancer l'analyse :

```bash
python3 scripts/prepare_analysis.py --list

📋 3 activité(s) non analysée(s) :

1. [2025-11-21] Zwift - Morning Endurance (partie 1)
   ID: i107779438 | Durée: 45min | TSS: 42

2. [2025-11-21] Zwift - Morning Endurance (partie 2)
   ID: i107779439 | Durée: 43min | TSS: 40

3. [2025-11-20] Sweet Spot 2x15min
   ID: i107779437 | Durée: 75min | TSS: 68
```

---

## 📋 Vue d'Ensemble du Workflow

Le script orchestre 7 étapes séquentielles (+ étape 1b si gaps détectés) :

### 1️⃣ Bienvenue et Présentation
Affiche le plan du workflow et explique que :
- Le prompt généré contient **automatiquement** tout le contexte nécessaire
- **Aucun upload de fichier requis** (contexte inclus dans le prompt)
- Tous les éléments sont chargés depuis le projet local

⏱️ **Temps** : 10 secondes

### 1️⃣b Détection Multi-Séances (Automatique si gaps)
Si 2+ séances non analysées sont détectées :
- Affiche la liste des séances en attente
- Informe que le menu interactif sera proposé à l'étape suivante
- Options : analyser une seule, choisir, ou mode batch

⏱️ **Temps** : 5 secondes

💡 **Skip** : Automatique si `--activity-id` fourni ou si 0-1 séance détectée

### 2️⃣ Collecte Feedback Athlète (Optionnel)
Lance `collect_athlete_feedback.py` pour capturer le ressenti subjectif.

⏱️ **Temps** : 30 secondes (quick) ou 2-3 min (full)

💡 **Avantage** : Claude croise métriques objectives + ressenti subjectif

### 3️⃣ Préparation Prompt
Lance `prepare_analysis.py` pour :
- Récupérer la séance depuis Intervals.icu
- Charger le contexte athlète depuis `references/project_prompt_v2_1_revised.md`
- Charger l'historique depuis `logs/workouts-history.md`
- Intégrer les concepts depuis `references/cycling_training_concepts.md`
- Récupérer le workout planifié (si disponible)
- Intégrer le feedback athlète (si collecté)
- Générer le prompt complet optimisé
- Copier dans le presse-papier

⏱️ **Temps** : 10 secondes

### 4️⃣ Envoi à Claude.ai
Instructions pour :
- Ouvrir Claude.ai (nouveau chat ou conversation existante)
- Coller le prompt complet
- Attendre la réponse (~30-60s)
- Copier UNIQUEMENT le bloc markdown généré

⏱️ **Temps** : 1-2 minutes

### 5️⃣ Validation Analyse
Checklist de validation avant insertion :
- ✓ Format markdown correct
- ✓ Toutes les sections présentes
- ✓ Contenu cohérent et factuel

⚠️ **Point d'arrêt** : Si invalide, possibilité de corriger et relancer

### 6️⃣ Insertion dans les Logs
Lance `insert_analysis.py` pour :
- Valider le format markdown
- Détecter les doublons
- Insérer au bon endroit dans `workouts-history.md`
- Afficher le diff

⏱️ **Temps** : 5 secondes

### 7️⃣ Commit Git (Optionnel)
Propose de commiter avec un message auto-généré :
```
Analyse: [Nom Séance]

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

Propose aussi le `git push` vers remote.

⏱️ **Temps** : 10 secondes

---

## ⏱️ Temps Total

- **Minimum** : ~3 minutes (sans feedback, séance simple)
- **Standard** : ~4 minutes (avec feedback quick)
- **Complet** : ~5-6 minutes (avec feedback full + commit)

💡 **Gain de temps** : Aucun upload manuel de fichiers requis !

---

## 🎮 Modes d'Utilisation

### Mode Standard (Recommandé)
```bash
python3 scripts/workflow_coach.py
```
- Guidage complet interactif
- Feedback athlète proposé
- Git commit proposé
- Adapté pour première utilisation

### Mode Rapide
```bash
python3 scripts/workflow_coach.py --skip-feedback --skip-git
```
- Skip feedback et commit
- Analyse basée uniquement sur métriques
- Pas de commit automatique
- Adapté pour analyses multiples rapides

### Mode Séance Spécifique
```bash
python3 scripts/workflow_coach.py --activity-id i123456
```
- Analyser une séance passée
- Utile pour rattraper des analyses manquées
- Même workflow complet

### Mode Projet Claude Code
```bash
# Depuis Claude Code
python3 scripts/workflow_coach.py
```
- Adapte les instructions pour contexte projet
- Skip l'upload de fichiers (déjà dans le projet)
- Simplifie les instructions de copier-coller

---

## 📊 Flux de Données

```
Intervals.icu API
    ↓
prepare_analysis.py
    ↓
[Clipboard: Prompt]
    ↓
Claude.ai
    ↓
[Clipboard: Analyse markdown]
    ↓
insert_analysis.py
    ↓
workouts-history.md
    ↓
git commit (optionnel)
```

---

## 🛠️ Options de Ligne de Commande

| Option | Description | Usage |
|--------|-------------|-------|
| `--skip-feedback` | Ne pas collecter le feedback athlète | Mode rapide |
| `--skip-git` | Ne pas proposer le commit git | Commit manuel plus tard |
| `--activity-id ID` | Analyser une séance spécifique | Rattrapage séances passées |

### Exemples Combinés

```bash
# Séance spécifique, sans feedback, avec commit
python3 scripts/workflow_coach.py --activity-id i123456 --skip-feedback

# Analyse rapide de la dernière séance
python3 scripts/workflow_coach.py --skip-feedback --skip-git

# Workflow complet avec tout
python3 scripts/workflow_coach.py
```

---

## ⚠️ Gestion des Erreurs

### Erreur API Intervals.icu
**Symptôme** : `❌ Erreur lors de la préparation du prompt`

**Solutions** :
```bash
# Vérifier la config
cat ~/.intervals_config.json

# Tester manuellement
python3 scripts/prepare_analysis.py
```

### Format Markdown Invalide
**Symptôme** : `❌ Erreur lors de l'insertion de l'analyse`

**Solutions** :
- Vérifier que seul le bloc markdown est copié (pas de texte avant/après)
- Recopier la réponse de Claude
- Valider le format avec `scripts/insert_analysis.py --dry-run`

### Interruption (Ctrl+C)
Le workflow gère proprement l'interruption à tout moment.

**Actions** :
- Relancer le script pour reprendre
- Les étapes déjà complétées (feedback) sont conservées
- Aucun fichier corrompu

---

## 🧪 Scénarios de Test

### Test 1 : Workflow Complet
```bash
python3 scripts/workflow_coach.py
# Vérifier guidage complet (7 étapes)
# Tester avec feedback athlète
# Vérifier commit git
```

### Test 2 : Mode Rapide
```bash
python3 scripts/workflow_coach.py --skip-feedback --skip-git
# Vérifier workflow minimal (~3 min)
```

### Test 3 : Validation Refusée
```bash
python3 scripts/workflow_coach.py
# À l'étape 5 (validation), répondre 'n'
# Vérifier sortie propre
```

---

## 🎯 Cas d'Usage

### Analyse Post-Séance Immédiate
**Contexte** : Viens de terminer une séance

```bash
# Avec feedback (recommandé)
python3 scripts/workflow_coach.py

# Sans feedback (rapide)
python3 scripts/workflow_coach.py --skip-feedback
```

### Rattrapage Analyses Manquées
**Contexte** : Plusieurs séances à analyser rétroactivement

```bash
# Séance 1
python3 scripts/workflow_coach.py --activity-id i123456 --skip-feedback

# Séance 2
python3 scripts/workflow_coach.py --activity-id i123457 --skip-feedback

# Commit groupé
git add logs/workouts-history.md
git commit -m "Analyses: Rattrapage semaine 067"
```

### Analyse Comparative Workout Planifié
**Contexte** : Séance avec workout planifié dans Intervals.icu

```bash
python3 scripts/workflow_coach.py
# Le script détecte automatiquement le workout planifié
# Claude compare planifié vs réalisé
```

---

## 📚 Scripts Associés

Le workflow coach orchestre ces scripts :

| Script | Rôle | Documentation |
|--------|------|---------------|
| `collect_athlete_feedback.py` | Collecte ressenti | [WORKFLOW_WITH_FEEDBACK.md](WORKFLOW_WITH_FEEDBACK.md) |
| `prepare_analysis.py` | Génère prompt | [README_ANALYSIS.md](README_ANALYSIS.md) |
| `insert_analysis.py` | Insère analyse | [README_ANALYSIS.md](README_ANALYSIS.md) |

---

## 💡 Bonnes Pratiques

### ✅ À Faire

- **Collecter le feedback systématiquement** pour analyses plus riches
- **Valider l'analyse avant insertion** pour garantir qualité
- **Commiter régulièrement** pour historique versionné
- **Relire l'analyse** après insertion pour s'approprier les recommandations

### ❌ À Éviter

- Ne pas copier le texte explicatif de Claude (seulement markdown)
- Ne pas skipper la validation (étape 6) par précipitation
- Ne pas analyser plusieurs séances simultanément (risque confusion clipboard)
- Ne pas modifier manuellement le markdown copié avant insertion

---

## 🔧 Personnalisation

### Changer le Message de Commit
Éditer `workflow_coach.py` ligne ~450 :

```python
commit_msg = f"Analyse: {short_name}\n\nVotre message personnalisé"
```

### Ajouter des Validations Custom
Ajouter dans `step_6_validate_analysis()` :

```python
# Vérification custom
if "votre_critère" not in clipboard:
    print("⚠️  Critère manquant")
```

### Modifier les Fichiers Contexte Chargés
Le contexte est chargé automatiquement depuis 3 fichiers locaux :

```python
# Dans prepare_analysis.py
generator.load_athlete_context()  # project_prompt_v2_1_revised.md
generator.load_recent_workouts()  # workouts-history.md
# + cycling_training_concepts.md (intégré dans le prompt)
```

Pour modifier le contexte, éditer directement ces fichiers markdown.

---

## 📖 Ressources Complémentaires

- **Démarrage rapide** : [QUICKSTART.md](QUICKSTART.md)
- **Documentation technique** : [README_ANALYSIS.md](README_ANALYSIS.md)
- **Feedback athlète** : [WORKFLOW_WITH_FEEDBACK.md](WORKFLOW_WITH_FEEDBACK.md)
- **Bilans hebdo** : [WEEKLY_REPORT_WORKFLOW.md](WEEKLY_REPORT_WORKFLOW.md)
- **Format analyse** : [EXAMPLE_ANALYSIS_FORMAT.md](EXAMPLE_ANALYSIS_FORMAT.md)

---

## 🐛 Dépannage

### Le script ne trouve pas `workouts-history.md`
```bash
# Vérifier le répertoire courant
pwd

# Naviguer vers la racine du projet
cd /Users/stephanejouve/cyclisme-training-logs

# Relancer
python3 scripts/workflow_coach.py
```

### Le presse-papier est vide après `prepare_analysis.py`
```bash
# Tester manuellement
python3 scripts/prepare_analysis.py
pbpaste | head

# Si vide, problème config Intervals.icu
cat ~/.intervals_config.json
```

### Git commit échoue
```bash
# Vérifier git status
git status

# Vérifier config git
git config user.name
git config user.email

# Commiter manuellement si nécessaire
git add logs/workouts-history.md
git commit -m "Analyse: Séance"
```

---

## 🎉 Avantages du Workflow Coach

✅ **Guidage complet** : Plus besoin de se souvenir des commandes

✅ **Validation intégrée** : Détection erreurs avant insertion

✅ **Gain de temps** : Orchestration automatique des 3 scripts

✅ **Flexibilité** : Options pour adapter à chaque cas d'usage

✅ **Robustesse** : Gestion erreurs et interruptions

✅ **Contexte adaptatif** : Détecte et s'adapte à l'environnement Claude

---

**Prêt ?** → `python3 scripts/workflow_coach.py` 🚴
