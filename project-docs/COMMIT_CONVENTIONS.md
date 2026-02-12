# Commit Message Conventions

**Dernière mise à jour:** 25 janvier 2026

---

## 🎯 Objectif

Établir une traçabilité claire entre les commits git et les versions de la ROADMAP pour éviter confusion lors de révisions historiques (ex: réorganisation Sprint R9, 25 jan 2026).

---

## 📋 Format Général

```
<type>(<scope>): <description> [ROADMAP@<commit-sha>]

<body détaillant le contexte sprint/feature>

Refs: ROADMAP.md "<Section Title>"
ROADMAP commit: <commit-sha> (<date>)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 🏷️ Convention Référencement ROADMAP

### Format Tag

**`[ROADMAP@<commit-sha>]`**

Le SHA référence le commit ROADMAP actif au moment du développement.

### Trouver le Commit ROADMAP Actuel

```bash
# Dernier commit modifiant ROADMAP.md
git log -1 --oneline project-docs/ROADMAP.md

# Exemple de sortie:
# b0a8b9e docs: Update ROADMAP - Sprint R9 complete [ROADMAP@e43557e]
```

Utiliser ce SHA dans les commits de développement:

```
feat(R9.F): Add pattern analysis [ROADMAP@b0a8b9e]
```

---

## 🔄 Règle Spéciale: Commits Modifiant ROADMAP

### Principe de Séparation

**Règle:** Quand vous modifiez `ROADMAP.md`, **commitez-le séparément** du code d'implémentation.

**Pourquoi?**
- Facilite le tracking des versions successives du ROADMAP
- Permet aux commits suivants de référencer la nouvelle version `[ROADMAP@SHA]`
- Évite la circularité `[ROADMAP modified]`

### Workflow Recommandé

**✅ BON (2 commits séparés):**

```bash
# Commit 1: Modifier SEULEMENT le ROADMAP
git add project-docs/ROADMAP.md
git commit -m "docs(roadmap): Add Test History Tracking proposal to backlog"
# → SHA: abc1234
# → Nouvelle version ROADMAP créée

# Commit 2: Implémenter les changements de code
git add cyclisme_training_logs/
git commit -m "feat(servo): Implement test history tracking [ROADMAP@abc1234]"
# → Référence la nouvelle version!
```

**❌ MOINS OPTIMAL (1 commit mixte):**

```bash
# Tout dans 1 commit
git add project-docs/ROADMAP.md cyclisme_training_logs/
git commit -m "feat(servo): Implement feature [ROADMAP modified]"
# → Tag spécial car ROADMAP inclus
```

### Tags Spéciaux

**`[ROADMAP@<sha>]`**
- Commit implémente une feature **basée sur** une version ROADMAP existante
- Référence le SHA du dernier commit ayant modifié ROADMAP.md

**`[ROADMAP modified]`**
- Commit **modifie le ROADMAP** lui-même (+ potentiellement du code)
- Utilisé quand ROADMAP et code sont dans le même commit
- Tag spécial car auto-référence impossible (circularité Git)

### Exemples Workflow

**Scénario 1: Planification puis implémentation**

```bash
# Étape 1: Ajouter proposition au ROADMAP
git add project-docs/ROADMAP.md
git commit -m "docs(roadmap): Add Sprint R14 PID improvements"
# → SHA: xyz5678

# Étape 2-N: Implémenter en référençant ROADMAP
git commit -m "feat(R14): Improve PID controller [ROADMAP@xyz5678]"
git commit -m "test(R14): Add PID calibration tests [ROADMAP@xyz5678]"
git commit -m "docs(R14): Update guide [ROADMAP@xyz5678]"
```

**Scénario 2: Documentation a posteriori**

```bash
# Développement terminé
git commit -m "feat(servo): Add auto-detection [ROADMAP@abc1234]"

# Puis documenter dans ROADMAP
git add project-docs/ROADMAP.md
git commit -m "docs(roadmap): Document servo auto-detection feature"
```

### Quand utiliser `[ROADMAP modified]`?

**Cas acceptables:**
- Commit de correction typo dans ROADMAP + code
- Refactoring mineur touchant ROADMAP + implémentation
- Urgence nécessitant commit atomique

**Dans tous les autres cas:** Préférer 2 commits séparés.

---

## 📝 Exemples

### Exemple 1: Feature Sprint

```
feat(R9.F): Add advanced pattern analysis [ROADMAP@b0a8b9e]

Implement risk scoring system for workout adherence patterns.
Part of Sprint R9.F - Advanced Pattern Analysis (25 Jan 2026).

Features:
- Pattern detection for day-of-week adherence
- Clustering of skip reasons
- Risk scoring 0-100 scale

Refs: ROADMAP.md "Sprint R9.F - Advanced Pattern Analysis"
ROADMAP commit: b0a8b9e (25 Jan 2026)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Exemple 2: Documentation

```
docs: Update ROADMAP - Add Sprint R10 PID Calibration [ROADMAP@f5g621d]

Add detailed Sprint R10 planning for PID calibration post-S080.

Changes:
- Add Sprint R10 section (PID Calibration)
- Define prerequisites (S080 tests)
- Detail livrables and acceptance criteria

Refs: ROADMAP.md "Sprint R10 - PID Calibration"
ROADMAP commit: This commit (f5g621d)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Exemple 3: Fix durant Sprint

```
fix(R9.E): Correct adherence calculation from 100% to 77.8% [ROADMAP@c2f299b]

Critical bug fix in baseline preliminary analysis.
Discovery: Adherence was incorrectly calculated at 100% due to
skipped workouts not being counted.

Actual adherence: 14/18 = 77.8%

Fixed in <3h during Sprint R9.E (25 Jan 2026).

Refs: ROADMAP.md "Sprint R9.E - Baseline Preliminary Analysis"
ROADMAP commit: c2f299b (25 Jan 2026)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 🔄 Pourquoi Cette Convention ?

### Problème Résolu

**Cas réel - Sprint R9 (25 Jan 2026):**

```
GIT HISTORY                      ROADMAP ACTUEL
───────────────                  ──────────────
Sprint R9 Grappe (15 Jan)   ≠   Sprint R9 Monitoring (04-25 Jan)
R9.A: Workflow Tests        ≠   R9.A: Daily Workout Sync
R9.B: Code Reusability      ≠   R9.B: Session Update
...                              ...
```

La réorganisation a créé une dualité entre git history et ROADMAP.

### Solution

Avec `[ROADMAP@<sha>]`, on sait **quelle version de la ROADMAP** un commit référence:

```bash
# Commit référençant ancienne structure
git show 24f17b6
# → [ROADMAP@ancien-sha] Sprint R9 Grappe

# Commit référençant nouvelle structure
git show b0a8b9e
# → [ROADMAP@e43557e] Sprint R9 Monitoring
```

---

## 🔍 Traçabilité Historique

### Retrouver l'État ROADMAP d'un Commit

```bash
# 1. Voir le commit
git show <commit-sha>

# 2. Extraire référence ROADMAP
git log --format=%B -1 <commit-sha> | grep "ROADMAP@"

# Exemple:
# [ROADMAP@b0a8b9e]

# 3. Voir ROADMAP à ce moment
git show b0a8b9e:project-docs/ROADMAP.md
```

### Comparer Versions ROADMAP

```bash
# Différence entre 2 versions ROADMAP
git diff 8830afa:project-docs/ROADMAP.md \
         b0a8b9e:project-docs/ROADMAP.md

# Voir l'évolution d'un sprint
git log --oneline project-docs/ROADMAP.md | \
  grep -i "sprint r9"
```

---

## 🎯 Convention Scope (sprints)

### Format Scope Sprint

- `(R9.A)` - Sous-sprint spécifique
- `(R9)` - Sprint général
- `(S080)` - Milestone semaine
- `(roadmap)` - Modification ROADMAP

### Exemples

```
feat(R9.F): Add pattern analysis [ROADMAP@b0a8b9e]
docs(roadmap): Update Sprint R9 [ROADMAP@b0a8b9e]
test(R9.C): Add adherence monitoring tests [ROADMAP@c2f299b]
fix(S080): Correct FTP test protocol [ROADMAP@f5g621d]
```

---

## 📚 Référence Rapide

### Template Commit Standard

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description> [ROADMAP@$(git log -1 --format=%h project-docs/ROADMAP.md)]

<body>

Refs: ROADMAP.md "<section>"
ROADMAP commit: $(git log -1 --format='%h (%ad)' --date=short project-docs/ROADMAP.md)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### Commande Helper (optionnel)

Ajouter à `.bashrc` ou `.zshrc`:

```bash
# Get current ROADMAP commit SHA
roadmap_sha() {
  git log -1 --format=%h project-docs/ROADMAP.md 2>/dev/null || echo "unknown"
}

# Template commit message
alias commit-sprint='echo "[ROADMAP@$(roadmap_sha)]"'
```

Usage:

```bash
git commit -m "feat(R9.F): Add feature $(commit-sprint)"
```

---

## ✅ Validation

### Checklist Commit Sprint

Avant de commiter un travail lié à un sprint:

- [ ] Message inclut `[ROADMAP@<sha>]`
- [ ] Scope correspond au sprint (ex: `R9.F`, `R10`, `S080`)
- [ ] Section `Refs:` pointe vers ROADMAP.md
- [ ] SHA ROADMAP correspond à `git log -1 project-docs/ROADMAP.md`
- [ ] Message body explique contexte sprint

---

## 🔗 Voir Aussi

- **ROADMAP.md** : État actuel sprints et planning
- **CODING_STANDARDS.md** : Standards généraux projet
- **SPRINT_NAMING.md** : Convention nommage sprints

---

**Note:** Cette convention a été établie suite à la réorganisation Sprint R9 (25 Jan 2026) pour éviter confusion future entre git history et versions ROADMAP.

_Pour historique complet, voir: ROADMAP.md "Note sur Réorganisation Historique"_
