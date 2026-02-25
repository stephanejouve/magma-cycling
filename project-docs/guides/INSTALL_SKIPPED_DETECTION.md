# Installation Détection Séances Sautées

## 🎯 Objectif

Ajouter la détection automatique des séances planifiées dans Intervals.icu mais non exécutées.

## 📦 Fichiers fournis

```
cyclisme-training-logs/
├── scripts/
│   ├── planned_sessions_checker.py           [NOUVEAU]
│   └── test_skipped_detection.py             [NOUVEAU]
├── patches/
│   ├── add_skipped_sessions_detection.patch  [PATCH workflow_coach.py]
│   └── add_skipped_status_support.patch      [PATCH rest_and_cancellations.py]
└── docs/
    └── SKIPPED_SESSIONS_DETECTION.md         [DOCUMENTATION]
```

## ⚡ Installation rapide (5 minutes)

### Étape 1 : Vérifier l'environnement

```bash
cd /path/to/cyclisme-training-logs

# Vérifier que tu es à jour
git status

# Créer une branche pour cette feature
git checkout -b feature/skipped-sessions-detection
```

### Étape 2 : Appliquer les patches

```bash
# Patch 1 : Ajouter détection dans workflow_coach.py
git apply patches/add_skipped_sessions_detection.patch

# Patch 2 : Support statut "skipped" dans rest_and_cancellations.py
git apply patches/add_skipped_status_support.patch

# Vérifier que les patches ont été appliqués
git status
```

**Attendu :**
```
On branch feature/skipped-sessions-detection
Changes not staged for commit:
  modified:   scripts/workflow_coach.py
  modified:   scripts/rest_and_cancellations.py

Untracked files:
  scripts/planned_sessions_checker.py
  scripts/test_skipped_detection.py
  patches/add_skipped_sessions_detection.patch
  patches/add_skipped_status_support.patch
  docs/SKIPPED_SESSIONS_DETECTION.md
```

### Étape 3 : Tester l'installation

```bash
# Test basique (derniers 7 jours)
python3 scripts/test_skipped_detection.py

# Si succès, tu verras :
# ✅ Credentials chargés (athlete: iXXXXXX)
# 📅 Période analysée : ...
# ✅ Excellent ! Toutes les séances planifiées ont été exécutées.
# OU
# ⚠️  X séance(s) sautée(s) détectée(s)
```

### Étape 4 : Valider dans le workflow

```bash
# Lancer le workflow principal
python3 scripts/workflow_coach.py

# Tu devrais voir dans le menu :
# 🔍 Détection Gaps
# ...
# ⏭️  Séances planifiées sautées : X
```

### Étape 5 : Commiter

```bash
# Ajouter tous les fichiers
git add scripts/planned_sessions_checker.py
git add scripts/test_skipped_detection.py
git add scripts/workflow_coach.py
git add scripts/rest_and_cancellations.py
git add patches/
git add docs/SKIPPED_SESSIONS_DETECTION.md

# Commiter
git commit -m "feat: Détection automatique séances planifiées sautées

- Nouveau module planned_sessions_checker.py
- Intégration dans workflow_coach.py (step_1b)
- Support statut 'skipped' dans rest_and_cancellations.py
- Script de test test_skipped_detection.py
- Documentation complète

Résout : Détection séances planifiées non exécutées"

# Merger dans main
git checkout main
git merge feature/skipped-sessions-detection

# Pousser (optionnel)
git push origin main
```

## 🔧 En cas de problème

### Conflit lors de l'application des patches

Si `git apply` échoue :

```bash
# Vérifier les conflits
git apply --check patches/add_skipped_sessions_detection.patch

# Si conflit, appliquer manuellement :
# 1. Ouvrir scripts/workflow_coach.py
# 2. Ajouter import ligne 36 :
from planned_sessions_checker import PlannedSessionsChecker

# 3. Ajouter attribut ligne 57 :
self.skipped_sessions = None

# 4. Ajouter détection dans step_1b_detect_all_gaps() après ligne 199
# (Voir contenu du patch pour détails)
```

### Test échoue avec erreur API

```bash
# Vérifier credentials
cat ~/.intervals_config.json

# Si absent, créer :
cat > ~/.intervals_config.json << EOF
{
  "athlete_id": "iXXXXXX",
  "api_key": "ta_clé_api_ici"
}
EOF
```

### Workflow ne détecte rien

**Normal si :**
- Pas de workouts planifiés dans Intervals.icu
- Tous les workouts planifiés ont été exécutés
- Workouts planifiés sont dans le futur

**Vérifier :**
```bash
# Lancer en mode verbose
python3 scripts/test_skipped_detection.py --verbose

# Vérifier API directement
curl -u "API_KEY:ta_clé" \
  "https://intervals.icu/api/v1/athlete/iXXXXXX/events?newest=2025-12-13&oldest=2025-12-06"
```

## 📚 Utilisation

### Mode automatique (recommandé)

```bash
# Le workflow détecte automatiquement
python3 scripts/workflow_coach.py

# Choisir option [2] ou [3] pour traiter les séances sautées
```

### Mode test (vérification)

```bash
# Test rapide
python3 scripts/test_skipped_detection.py

# Test avec markdown
python3 scripts/test_skipped_detection.py --generate-markdown

# Test sur période custom
python3 scripts/test_skipped_detection.py --days 14
```

### Mode programmatique

```python
from planned_sessions_checker import PlannedSessionsChecker

checker = PlannedSessionsChecker("iXXXXXX", "ta_clé")
skipped = checker.detect_skipped_sessions("2025-12-01", "2025-12-13")

for session in skipped:
    print(f"Sautée : {session['planned_name']}")
```

## 📖 Documentation complète

Voir `docs/SKIPPED_SESSIONS_DETECTION.md` pour :
- Algorithme détaillé
- Cas d'usage
- Troubleshooting
- API reference

## ✅ Checklist de validation

- [ ] Patches appliqués sans erreur
- [ ] `test_skipped_detection.py` s'exécute sans erreur
- [ ] `workflow_coach.py` affiche section "Séances planifiées sautées"
- [ ] Import `PlannedSessionsChecker` fonctionne
- [ ] Credentials API chargés correctement
- [ ] Commits créés et poussés (optionnel)

## 🎉 Succès !

Si tous les tests passent, le système est opérationnel.

**Prochaines utilisations :**
- Lancer `workflow_coach.py` comme d'habitude
- Les séances sautées apparaîtront automatiquement dans les gaps
- Option batch disponible pour les documenter

**Bénéfices :**
✅ Détection 100% automatique (pas de JSON manuel)
✅ Synchronisé temps réel avec Intervals.icu
✅ Calcul impact TSS automatique
✅ Documentation markdown générée
✅ Intégré dans workflow existant

---

**Support** : En cas de problème, consulter `docs/SKIPPED_SESSIONS_DETECTION.md` section Troubleshooting
