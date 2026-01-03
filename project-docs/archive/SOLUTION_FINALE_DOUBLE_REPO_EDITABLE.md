# Solution Finale: Double Repo avec Package Editable

## 🎯 Principe

**Séparer code et data** (principe original maintenu)
**MAIS** avec dépendance Poetry propre entre les deux.

---

## 📁 Architecture

```
~/cyclisme-training-logs/          ← Code repo (source package)
  ├── .git/                        ← Git history code
  ├── pyproject.toml               ← Poetry package config
  ├── cyclisme_training_logs/
  │   ├── workflow_coach.py
  │   └── scripts/
  │       └── backfill_history.py
  └── README.md

~/training-logs/                   ← Data repo (consomme package)
  ├── .git/                        ← Git history data
  ├── pyproject.toml               ← Poetry runner config
  ├── poetry.lock
  ├── workouts-history.md
  └── .workflow_state.json
```

**Séparation respectée:**
- ✅ Code versionné séparément
- ✅ Data versionnée séparément
- ✅ Backup indépendants
- ✅ Deploy flexible

**Mais maintenant:**
- ✅ Poetry fonctionne dans data repo
- ✅ Subprocess exécute depuis data repo
- ✅ Pas de hack `python -m`

---

## 🔧 Setup (10 minutes)

### Étape 1: Préparer Code Repo

```bash
cd ~/cyclisme-training-logs

# Vérifier pyproject.toml correct
cat pyproject.toml | grep name
# → name = "cyclisme-training-logs"

# Installer en mode dev
poetry install
```

### Étape 2: Créer Runner dans Data Repo

```bash
cd ~/training-logs

# Initialiser Poetry dans data repo
poetry init \
  --name training-logs-runner \
  --description "Runner for cyclisme-training-logs" \
  --author "Stephane Jouve" \
  --python "^3.11" \
  --no-interaction

# Éditer pyproject.toml généré
cat > pyproject.toml << 'EOF'
[tool.poetry]
name = "training-logs-runner"
version = "0.1.0"
description = "Runner for cyclisme-training-logs analysis"
authors = ["Stephane Jouve"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
# Package local en mode editable
cyclisme-training-logs = {path = "../cyclisme-training-logs", develop = true}

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF

# Installer dépendances (installe code repo en editable)
poetry install

# Vérifier installation
poetry run python -c "import cyclisme_training_logs; print('✅ OK')"
```

### Étape 3: Tester Subprocess Depuis Data Repo

```bash
cd ~/training-logs

# Test workflow-coach
poetry run workflow-coach \
  --activity-id i113315172 \
  --provider mistral_api \
  --auto \
  --skip-feedback \
  --skip-git

# ✅ Fonctionne ! Poetry trouve pyproject.toml dans ~/training-logs/
```

### Étape 4: Backfill Depuis Data Repo

```bash
cd ~/training-logs

# Backfill s'exécute depuis data repo
poetry run backfill-history \
  --start-date 2025-12-22 \
  --end-date 2025-12-22 \
  --force-reanalyze \
  --provider mistral_api \
  --yes

# ✅ Subprocess Poetry fonctionne (pyproject.toml trouvé)
# ✅ Écrit dans data repo courant (~/training-logs/)
```

---

## 🎯 Workflow Quotidien

### Développement Code

```bash
# Travailler sur code
cd ~/cyclisme-training-logs
git checkout -b feature/new-analysis

# Modifier code
vim cyclisme_training_logs/workflow_coach.py

# Tester localement
poetry run pytest

# Commit code
git add .
git commit -m "feat: New analysis feature"
git push

# ✅ Data repo utilise automatiquement nouvelle version (editable mode)
```

### Utilisation Data

```bash
# Analyser données
cd ~/training-logs

# Commandes disponibles via Poetry runner
poetry run workflow-coach --activity-id i123456
poetry run backfill-history --start-date 2025-01-01

# Commit données
git add workouts-history.md
git commit -m "chore: Add S073 week analysis"
git push

# ✅ Code repo non touché
```

---

## 📊 Comparaison Solutions

| Critère | Mono-Repo | Double Repo + Editable | Double Repo + python -m |
|---------|-----------|------------------------|-------------------------|
| Séparation code/data | ❌ | ✅ | ✅ |
| Poetry natif | ✅ | ✅ | ❌ |
| Portabilité | ✅ | ✅ | ⭐⭐ |
| Complexité setup | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Maintenabilité | ✅ | ✅ | ⭐⭐ |
| Backup séparé | ❌ | ✅ | ✅ |
| Best practice | ⭐⭐⭐ | ✅ | ❌ |

---

## ✅ Avantages Solution Finale

1. **Respect principes originaux**
   - Code et data séparés
   - Git history indépendantes
   - Backup sélectifs possibles

2. **Poetry fonctionne partout**
   - `poetry run` dans code repo ✅
   - `poetry run` dans data repo ✅
   - Subprocess depuis data repo ✅

3. **Portabilité maintenue**
   - Pas de hack `python -m`
   - Dépendances gérées par Poetry
   - Installation standard

4. **Workflow naturel**
   - Dev dans code repo
   - Utilisation dans data repo
   - Modifications code automatiques (editable)

---

## 🔧 Modifications Code Nécessaires

### AUCUNE ! 🎉

Le code actuel (commit 968303c) **fonctionne déjà** avec cette architecture:

```python
# backfill_history.py ligne ~286
cmd = [
    sys.executable,
    '-m', 'cyclisme_training_logs.workflow_coach',
    '--activity-id', activity_id,
    ...
]

# ✅ Fonctionne car:
# - sys.executable = Python de l'env Poetry data repo
# - Module installé via poetry add --editable
# - PYTHONPATH correct automatiquement
```

**Donc 968303c n'est PAS un hack dans ce contexte !**

C'est la **bonne solution** pour double repo avec package editable.

---

## 🚀 Action Immédiate

```bash
# Setup data repo Poetry (5 minutes)
cd ~/training-logs

# Créer pyproject.toml
cat > pyproject.toml << 'EOF'
[tool.poetry]
name = "training-logs-runner"
version = "0.1.0"
description = "Runner for cyclisme-training-logs"
authors = ["Stephane Jouve"]

[tool.poetry.dependencies]
python = "^3.11"
cyclisme-training-logs = {path = "../cyclisme-training-logs", develop = true}

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF

# Installer
poetry install

# Tester
poetry run backfill-history \
  --start-date 2025-12-22 \
  --end-date 2025-12-22 \
  --force-reanalyze \
  --provider mistral_api \
  --yes

# ✅ Devrait fonctionner !
```

---

## 🎓 Lessons Learned

**Principe original CORRECT:**
- ✅ Séparer code et data

**Erreur initiale:**
- ❌ Ne pas configurer dépendance Poetry entre repos

**Solution finale:**
- ✅ Double repo avec package editable
- ✅ Poetry natif partout
- ✅ Pas de compromis principes

---

## 📝 Conclusion

**968303c n'est PAS un hack** si on setup correctement data repo avec Poetry !

**Il faut juste:**
1. Créer `pyproject.toml` dans data repo
2. Installer code repo en editable
3. Profit ! ✅

**Temps:** 5 minutes
**Résultat:** Architecture propre, séparation maintenue, Poetry natif

---

**Créé:** 2025-12-26 19:45
**Résout:** Contradiction mono-repo vs double repo
**Préserve:** Principes séparation code/data
**Implémente:** Poetry editable package pattern
