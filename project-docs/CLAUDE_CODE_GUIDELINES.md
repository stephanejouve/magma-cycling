# Guidelines Claude Code - Cyclisme Training Logs

**Purpose:** Rappels importants et bonnes pratiques pour Claude Code sur ce projet

---

## ⚠️ FICHIERS VOLUMINEUX - NE PAS LIRE ENTIÈREMENT

### ROADMAP.md (36607 tokens - LIMITE: 25000 tokens)

**❌ NE JAMAIS FAIRE:**
```python
Read(file_path="/Users/.../ROADMAP.md")  # ERREUR: Dépasse 25000 tokens
```

**✅ TOUJOURS FAIRE:**

#### 1. Utiliser GREP pour recherche ciblée
```python
Grep(
    pattern="Sprint S[0-9]+|Phase 2.5",
    path="project-docs/ROADMAP.md",
    output_mode="content",
    -n=True,
    -C=5  # Context lines
)
```

#### 2. Utiliser Read avec offset/limit
```python
# Pour section spécifique (estimer ligne via grep d'abord)
Read(
    file_path="project-docs/ROADMAP.md",
    offset=680,    # Ligne de départ
    limit=50       # Nombre de lignes
)
```

#### 3. Workflow recommandé pour ROADMAP
```
Étape 1: Grep pattern pour trouver ligne approximative
Étape 2: Read avec offset/limit pour section précise
Étape 3: Edit pour modifier section ciblée
```

**Exemple concret:**
```python
# 1. Trouver où est "Phase 2.5"
Grep(pattern="Phase 2.5", path="ROADMAP.md", -n=True)
# → Résultat: ligne 692

# 2. Lire juste cette section
Read(file_path="ROADMAP.md", offset=690, limit=100)

# 3. Modifier si nécessaire
Edit(file_path="ROADMAP.md", old_string="...", new_string="...")
```

---

## 📝 CONVENTIONS DE COMMIT

### Format Standard
```bash
<type>(<scope>): <description> [ROADMAP@<sha>]

Example:
feat(external): Add Zwift workout search [ROADMAP@eeea982]
fix(daily-sync): Handle None values in prompts [ROADMAP@eeea982]
docs(roadmap): Update Sprint S3 status [ROADMAP@eeea982]
```

### Obtenir le SHA actuel de ROADMAP
```bash
git log -1 --format="%h" project-docs/ROADMAP.md
```

### Types de commit
- `feat`: Nouvelle feature
- `fix`: Bug fix
- `docs`: Documentation uniquement
- `test`: Ajout/modification tests
- `refactor`: Refactoring sans changement fonctionnel
- `chore`: Maintenance (deps, config)

---

## 🗂️ AUTRES FICHIERS VOLUMINEUX

### Liste des fichiers à surveiller (> 2000 lignes)

| Fichier | Lignes | Action |
|---------|--------|--------|
| `ROADMAP.md` | ~3000 | Grep + offset/limit |
| `zwift_seed_data.py` | ~1500 | Read complet OK (< 25000 tokens) |
| `proactive_compensation.py` | ~600 | Read complet OK |

**Règle générale:**
- Fichier < 2000 lignes → Read direct OK
- Fichier > 2000 lignes → Grep d'abord, puis Read ciblé

---

## 🔧 SCRIPTS UTILES

### Session Summary
```bash
# Générer résumé session automatique depuis JSONL
python scripts/maintenance/session_summarizer.py \
    ~/.claude/projects/-Users-stephanejouve-magma-cycling/<session-id>.jsonl \
    --output project-docs/sessions/SESSION_YYYYMMDD_AUTO_SUMMARY.md
```

**Toujours utiliser le script, ne pas créer manuellement !**

### Daily-Sync Debug
```bash
# Logs
tail -f ~/Library/Logs/cyclisme-rept-daily-sync.log
tail -f ~/Library/Logs/cyclisme-rept-daily-sync.error.log

# Force reanalysis (supprimer entrée tracking)
jq 'del(."YYYY-MM-DD")' ~/training-logs/data/activities_tracking.json > temp.json
mv temp.json ~/training-logs/data/activities_tracking.json
```

---

## 🎯 BONNES PRATIQUES GÉNÉRALES

### 1. Lecture de fichiers
- **Toujours préférer:** Grep → Read ciblé
- **Éviter:** Read sans vérifier taille d'abord

### 2. Commits
- **Un commit = une feature/fix logique**
- **Toujours inclure [ROADMAP@SHA]** pour features liées roadmap
- **Co-Authored-By:** Claude Sonnet 4.5 <noreply@anthropic.com>

### 3. Session Summary
- **Utiliser script automatique** `session_summarizer.py`
- **Ne pas créer manuellement** (sauf exceptions documentées)

### 4. Tests
- **Toujours valider** que tests passent avant commit
- **Poetry run pytest** avant push

---

## 📚 RÉFÉRENCES RAPIDES

### Chemins Importants
- **ROADMAP:** `project-docs/ROADMAP.md`
- **Sessions:** `project-docs/sessions/`
- **Data:** `~/training-logs/data/`
- **Reports:** `~/training-logs/daily-reports/`

### CLI Commands
```bash
# Zwift workouts
poetry run seed-zwift-workouts --collection build-me-up
poetry run search-zwift-workouts --category FTP

# Daily sync
poetry run daily-sync --send-email --ai-analysis --auto-servo

# Tests
poetry run pytest tests/ -v
```

---

## 🚨 ERREURS COMMUNES À ÉVITER

### 1. ❌ Lire ROADMAP.md entièrement
**Erreur vue:** Plusieurs fois dans sessions précédentes
**Solution:** Utiliser Grep + offset/limit (voir section ci-dessus)

### 2. ❌ F-strings avec format specifiers + conditionnels
```python
# ❌ ERREUR
f"{value:.2f if value else 'N/A'}"  # ValueError

# ✅ CORRECT
formatted = f"{value:.2f}" if value else "N/A"
f"Value: {formatted}"
```

### 3. ❌ Oublier encoding='utf-8' dans open()
```python
# ❌ ERREUR
with open(file_path, 'r') as f:

# ✅ CORRECT
with open(file_path, 'r', encoding='utf-8') as f:
```

### 4. ❌ Créer résumé session manuellement
**Action:** Toujours utiliser `scripts/maintenance/session_summarizer.py`

---

## 📅 DERNIÈRE MISE À JOUR

**Date:** 2026-02-10
**Session:** d71ddbcd-7e4d-4290-8284-0f381e67577b
**Contexte:** Ajout guidelines après erreur répétée lecture ROADMAP.md

**Historique des updates:**
- 2026-02-10: Création initiale (erreur ROADMAP.md récurrente)

---

## 💡 AMÉLIORATIONS FUTURES

**À considérer si problème persiste:**
1. Script helper `roadmap_section.py` pour extraire sections
2. Pre-commit hook vérifiant taille fichiers avant Read
3. Validation automatique conventions commit

**Note:** Préférer solutions simples (grep/offset) avant automation complexe
