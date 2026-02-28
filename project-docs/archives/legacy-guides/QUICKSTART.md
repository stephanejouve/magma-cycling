# 🚀 Démarrage Rapide - Analyse Automatique

## 🎯 Workflow Coach (NOUVEAU - LE PLUS SIMPLE)

**Un seul script qui orchestre tout le processus** avec guidage interactif !

```bash
# Workflow complet guidé (recommandé pour débuter)
python3 scripts/workflow_coach.py

# Mode rapide (sans feedback ni git)
python3 scripts/workflow_coach.py --skip-feedback --skip-git
```

**Avantages** :
- ✅ Guidage étape par étape
- ✅ Détecte automatiquement le contexte (nouveau chat/existant/projet)
- ✅ Validation avant insertion
- ✅ Gestion erreurs intégrée
- ✅ Git commit optionnel
- ⏱️ 4-5 minutes total

📖 **Documentation complète** : [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)

---

## 🔥 Détection Multi-Séances (NOUVEAU)

Le système détecte automatiquement les **séances non analysées** et propose un menu interactif !

### Cas d'Usage Réels

#### 📶 Déconnexion Zwift
```bash
python3 scripts/workflow_coach.py

# Affiche :
# 📊 2 ACTIVITÉS NON ANALYSÉES DÉTECTÉES
#
# 1. [2025-11-21] Zwift - Morning Endurance (partie 1)
#    ID: i107779438 | Durée: 45min | TSS: 42
#
# 2. [2025-11-21] Zwift - Morning Endurance (partie 2)
#    ID: i107779439 | Durée: 43min | TSS: 40
#
# OPTIONS :
#   1 - Analyser la DERNIÈRE séance uniquement
#   2 - Choisir UNE séance spécifique
#   3 - Analyser TOUTES en mode batch  ← Choisir 3 !
#   0 - Annuler
```

**Solution** : Option 3 (mode batch) → Les deux sont analysées dans la même session Claude !

#### 🏔️ Weekend Multi-Séances
Tu analyses le lundi, tu as fait 3 séances samedi-dimanche :

```bash
python3 scripts/workflow_coach.py

# Menu avec 3 séances
# → Option 3 (batch) pour tout traiter
# → Ou Option 2 pour choisir les plus importantes
```

#### 🎯 Analyser une Séance Spécifique
Tu veux analyser une vieille séance (pas la dernière) :

```bash
# Lister les séances non analysées
python3 scripts/prepare_analysis.py --list

# Analyser directement par ID
python3 scripts/workflow_coach.py --activity-id i107779437
```

#### ⚡ Mode Batch Direct (sans workflow_coach)
Pour experts : analyser plusieurs séances en une commande

```bash
python3 scripts/prepare_analysis.py

# Le menu apparaît automatiquement si gaps détectés
# Sélectionner option 3 (batch)
# → Reste dans Claude.ai, pas besoin de relancer !
```

### Avantages Mode Batch

✅ **Gain de temps** : Analyse 3 séances en 5 minutes (vs 15 min séparément)

✅ **Context continuity** : Reste dans la même conversation Claude

✅ **Insertion auto** : Propose `insert_analysis.py` après chaque analyse

✅ **Tracking état** : Marque automatiquement chaque séance comme analysée

---

## ⚡ Workflow Standard (3 commandes - Expert)

```bash
# 1. Préparer le prompt (copié automatiquement dans le presse-papier)
./scripts/prepare_analysis.py

# 2. → Coller dans Claude.ai → Copier la réponse

# 3. Insérer l'analyse
./scripts/insert_analysis.py
```

## 🌟 Workflow Enrichi (+30 secondes, **RECOMMANDÉ**)

```bash
# 1. Collecter votre ressenti (RPE + quelques mots)
./scripts/collect_athlete_feedback.py --quick

# 2. Préparer le prompt (intègre automatiquement le feedback)
./scripts/prepare_analysis.py

# 3. → Coller dans Claude.ai → Copier la réponse

# 4. Insérer l'analyse
./scripts/insert_analysis.py
```

**Pourquoi ?** Claude croise métriques objectives + ressenti subjectif = analyse beaucoup plus pertinente ! 🎯

Voir [WORKFLOW_WITH_FEEDBACK.md](WORKFLOW_WITH_FEEDBACK.md) pour les détails.

## 📖 Workflow Détaillé

### 1️⃣ Générer le Prompt

```bash
cd /Users/stephanejouve/magma-cycling
./scripts/prepare_analysis.py
```

**Résultat :**
- ✅ Dernière séance récupérée depuis Intervals.icu
- ✅ Prompt copié dans le presse-papier
- ✅ Instructions affichées

### 2️⃣ Obtenir l'Analyse de Claude

1. Ouvrir https://claude.ai
2. Coller (`Cmd+V`)
3. Attendre la réponse (~30 secondes)
4. **Copier UNIQUEMENT le bloc markdown** (de `###` jusqu'à la dernière ligne)

💡 **Important** : Ne pas copier le texte explicatif de Claude, seulement la structure markdown.

### 3️⃣ Insérer dans les Logs

```bash
./scripts/insert_analysis.py
```

**Le script :**
- ✅ Valide le format
- ✅ Détecte les doublons
- ✅ Insère au bon endroit
- ✅ Affiche le `git diff`

### 4️⃣ Commit (Optionnel)

```bash
git add logs/workouts-history.md
git commit -m "Analyse: Séance du [DATE]"
git push
```

## 🎯 Options Utiles

### Analyser une séance spécifique

```bash
./scripts/prepare_analysis.py --activity-id 123456789
```

### Mode test (sans modification)

```bash
./scripts/insert_analysis.py --dry-run
```

### Analyser depuis un fichier

```bash
# Si vous avez sauvegardé la réponse de Claude
./scripts/insert_analysis.py --file analysis.md
```

## ⚙️ Configuration Requise

Le fichier `~/.intervals_config.json` doit exister :

```json
{
  "athlete_id": "i123456",
  "api_key": "YOUR_API_KEY"
}
```

**Obtenir l'API key :** intervals.icu → Settings → Developer Settings

## ⚠️ Activités Strava

Les activités Strava ont des **données limitées** (restrictions API).

**Détection automatique** :
- Le script affiche un avertissement
- Claude.ai reçoit des instructions adaptées
- Analyse basée sur données disponibles (FC, TSS, durée)

**Vérifier vos sources** :
```bash
./scripts/check_activity_sources.py
```

## 🐛 Problèmes Courants

### "athlete_id et api_key requis"
→ Créer `~/.intervals_config.json`

### "Erreur API: 401"
→ Vérifier l'API key dans la config

### "Sections manquantes"
→ Claude a généré une réponse incomplète, relancer

### Doublons détectés
→ Vérifier `logs/workouts-history.md`, supprimer si nécessaire

### Activité Strava : données manquantes
→ Normal, le script gère automatiquement le cas

## 📊 Bilan Hebdomadaire (Fin de Semaine)

```bash
# 1. Préparer le prompt de bilan (toutes les séances de la semaine)
./scripts/prepare_weekly_report.py --week 067 --start-date 2025-11-11

# 2. → Coller dans Claude.ai → Attendre 2-3 minutes

# 3. → Copier TOUS les fichiers générés

# 4. Organiser automatiquement les 6 fichiers
./scripts/organize_weekly_report.py --week 067

# 5. Commit
git add bilans_hebdo/s067/
git commit -m "Bilan: Semaine S067"
```

**Résultat** : 6 fichiers markdown archivés dans `bilans_hebdo/s067/`

Voir [WEEKLY_REPORT_WORKFLOW.md](WEEKLY_REPORT_WORKFLOW.md) pour les détails complets.

## 📚 Documentation Complète

- [README_ANALYSIS.md](README_ANALYSIS.md) - Documentation technique complète
- [WORKFLOW_WITH_FEEDBACK.md](WORKFLOW_WITH_FEEDBACK.md) - Workflow avec feedback athlète
- [WEEKLY_REPORT_WORKFLOW.md](WEEKLY_REPORT_WORKFLOW.md) - Bilans hebdomadaires
- [EXAMPLE_ANALYSIS_FORMAT.md](EXAMPLE_ANALYSIS_FORMAT.md) - Format d'analyse

## ⏱️ Temps Total

**Par séance** : ~2 minutes
- 30s : Génération du prompt
- 60s : Claude analyse
- 30s : Insertion et vérification

**Par semaine (bilan)** : ~5 minutes
- 1min : Préparation prompt
- 3min : Claude génère 6 fichiers
- 1min : Organisation automatique

---

**Prêt ?** → `./scripts/prepare_analysis.py` 🚴
