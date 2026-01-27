# Gestion des Journaux de Session

**Objectif:** Maintenir des fichiers de session JSONL légers et navigables (<10MB par fichier).

## 📁 Structure

```
project-docs/sessions/
├── SESSION_R9E_PHASE1_25JAN2026.jsonl           # Original (archivé après split)
├── SESSION_R9E_PHASE1_25JAN2026_chunk001.jsonl  # Chunk 1 (3.4 MB)
├── SESSION_R9E_PHASE1_25JAN2026_chunk002.jsonl  # Chunk 2 (6.3 MB)
├── ...
├── SESSION_R9E_PHASE1_25JAN2026_chunk008.jsonl  # Chunk 8 (299 KB)
└── SESSION_R9E_PHASE1_25JAN2026_INDEX.md        # Index de navigation
```

---

## 🔧 Utilisation Manuelle

### Split d'un gros fichier JSONL

```bash
# Split avec taille par défaut (1500 lignes/chunk)
python scripts/maintenance/split_session_logs.py project-docs/sessions/SESSION_XXX.jsonl

# Split avec génération automatique de résumé
python scripts/maintenance/split_session_logs.py SESSION_XXX.jsonl --summarize

# Spécifier une taille de chunk personnalisée
python scripts/maintenance/split_session_logs.py SESSION_XXX.jsonl --chunk-size 2000

# Compresser les chunks avec gzip
python scripts/maintenance/split_session_logs.py SESSION_XXX.jsonl --compress

# Dry run pour prévisualiser
python scripts/maintenance/split_session_logs.py SESSION_XXX.jsonl --dry-run
```

### Générer un résumé de session

```bash
# Générer résumé d'une session
python scripts/maintenance/session_summarizer.py project-docs/sessions/SESSION_XXX.jsonl

# Spécifier le fichier de sortie
python scripts/maintenance/session_summarizer.py SESSION_XXX.jsonl --output custom_summary.md

# Afficher le résumé dans le terminal
python scripts/maintenance/session_summarizer.py SESSION_XXX.jsonl --stdout
```

### Navigation dans les chunks

**Utiliser l'index:**
```bash
cat project-docs/sessions/SESSION_R9E_PHASE1_25JAN2026_INDEX.md
```

**Chercher dans tous les chunks:**
```bash
grep -n "pattern" project-docs/sessions/SESSION_R9E_PHASE1_25JAN2026_chunk*.jsonl
```

**Lire un chunk spécifique:**
```bash
less project-docs/sessions/SESSION_R9E_PHASE1_25JAN2026_chunk005.jsonl
```

**Extraire les messages utilisateur d'un chunk:**
```bash
jq 'select(.type == "user") | .message.content' SESSION_R9E_PHASE1_25JAN2026_chunk005.jsonl
```

---

## 🤖 Automatisation

### Intégration au project_cleaner

Le `project_cleaner.py` détecte et split **automatiquement** les fichiers JSONL > 10 MB :

```bash
# Cleanup quotidien (inclut le split automatique)
poetry run project-clean

# Dry run pour voir ce qui serait splité
poetry run project-clean --dry-run

# Deep cleanup avec rapport détaillé
poetry run project-clean --deep
```

**LaunchAgent quotidien:** Le cleaner s'exécute automatiquement chaque jour via LaunchAgent.

### Comportement automatique

1. **Détection:** Le cleaner scanne `project-docs/sessions/*.jsonl`
2. **Seuil:** Fichiers > 10 MB sont splités
3. **Split:** Création de chunks de 1500 lignes + index
4. **Résumé:** Génération automatique d'un résumé markdown (`*_SUMMARY.md`)
5. **Archive:** Original renommé en `.jsonl.original`
6. **Log:** Rapport dans la sortie du cleaner

### Résumés automatiques

Chaque session splitée génère un résumé qui contient:

- **📋 Overview:** Date, durée, requête initiale
- **🎯 Commits:** Liste des commits créés
- **📁 Fichiers:** Fichiers créés/modifiés
- **🤔 Décisions:** Questions posées et réponses
- **✅ Tasks:** Todos complétés/en cours/pending
- **🔧 Stats:** Outils utilisés (Bash, Read, Edit, etc.)
- **⚠️ Erreurs:** Erreurs rencontrées (si applicable)

**Exemple:** `SESSION_R9E_PHASE1_25JAN2026_SUMMARY.md`

---

## 📊 Métriques et Statistiques

### Index généré automatiquement

Chaque session splitée génère un fichier `*_INDEX.md` contenant:

- **Total chunks:** Nombre de fichiers créés
- **Total lines:** Lignes totales splitées
- **Total size:** Taille cumulée
- **Par chunk:**
  - Nom du fichier
  - Nombre de lignes
  - Taille (KB)
  - Timestamps début/fin
  - Nombre de messages

**Exemple:**
```markdown
# Session Log Index: SESSION_R9E_PHASE1_25JAN2026

**Generated:** 2026-01-27 19:33:13
**Total chunks:** 8
**Total lines:** 10,578
**Total size:** 38.2 MB

### Chunk 001
**File:** `SESSION_R9E_PHASE1_25JAN2026_chunk001.jsonl`
**Lines:** 1,500
**Size:** 3527.2 KB
**Start:** 2026-01-18T08:23:16.566Z
**End:** 2026-01-18T10:35:44.662Z
**Messages:** 1161
```

---

## 💡 Pourquoi Résumés + Chunks ?

### Pour Claude (IA)

**Problème:** Claude ne peut pas lire les gros chunks (limite 256KB)

**Solution:** Résumés légers (~5-10KB) lisibles directement
- ✅ Comprend rapidement le contexte d'une session passée
- ✅ Identifie les décisions et commits importants
- ✅ Voit les fichiers modifiés sans lire le JSONL complet
- ✅ Peut répondre à "où en sommes-nous ?" sans aide

**Impact:** Claude récupère le contexte en <10 secondes vs impossible avant

### Pour l'Humain

**Bénéfices complémentaires:**
- 🔍 Navigation rapide dans l'historique
- 📊 Vue d'ensemble des accomplissements
- 🎯 Retrouver rapidement une décision passée
- 📁 Identifier quand un fichier a été créé/modifié
- ⏱️ Tracking du temps passé par session

**Workflow:** Résumé pour vue globale → Chunks pour détails si besoin

## 🎯 Bonnes Pratiques

### Quand spliter manuellement?

- Fichier > 10 MB (automatique via cleaner)
- Fichier difficile à lire/chercher
- Avant commit (pour performances Git)

### Quand NE PAS spliter?

- Fichiers < 5 MB (overhead inutile)
- Sessions actives (attendre la fin)
- Fichiers déjà compressés `.gz`

### Résumés vs Chunks vs Documentation

**Résumé (`*_SUMMARY.md`):**
- Vue globale rapide
- Lisible par Claude et humains
- Généré automatiquement
- **Utiliser pour:** Comprendre rapidement une session passée

**Chunks (`*_chunk*.jsonl`):**
- Détails complets de la conversation
- Trop gros pour Claude (3-8 MB)
- Navigation avec grep/jq
- **Utiliser pour:** Recherche précise, debugging, audit

**Documentation projet:**
- ROADMAP.md, CHANGELOG.md, etc.
- Vue stratégique long-terme
- Maintenue manuellement
- **Utiliser pour:** Comprendre le projet dans sa globalité

### Gestion du Git

**Fichiers à commit:**
- ✅ Chunks splitées (`*_chunk*.jsonl`)
- ✅ Index de navigation (`*_INDEX.md`)
- ✅ Fichiers compressés (`.jsonl.gz`)

**Fichiers à ignorer:**
- ❌ Originaux archivés (`.jsonl.original`)
- ❌ Fichiers temporaires de split

**Ajout au .gitignore si besoin:**
```gitignore
# Session logs - keep only chunks and compressed
project-docs/sessions/*.jsonl.original
```

---

## 🔍 Dépannage

### "Would split but file already has chunks"

Le script détecte automatiquement les fichiers déjà splitées (nom contient `_chunk`).

**Solution:** Si re-split nécessaire, supprimer d'abord les anciens chunks :
```bash
rm project-docs/sessions/SESSION_XXX_chunk*.jsonl
rm project-docs/sessions/SESSION_XXX_INDEX.md
```

### "Import error: split_session_logs module not found"

Le `project_cleaner.py` importe dynamiquement le module.

**Solution:** Vérifier que `split_session_logs.py` existe :
```bash
ls -l scripts/maintenance/split_session_logs.py
```

### Chunks de tailles variables

Normal ! La taille dépend du contenu JSON (messages longs = chunks plus gros).

**Ajustement:** Utiliser `--chunk-size` plus petit si besoin :
```bash
python scripts/maintenance/split_session_logs.py SESSION_XXX.jsonl --chunk-size 1000
```

---

## 📝 Exemple Complet

### Session R9E Phase 1 (25 jan 2026)

**Avant split:**
- 1 fichier: `SESSION_R9E_PHASE1_25JAN2026.jsonl` (38.2 MB, 10,578 lignes)
- Difficile à lire, git diff lent

**Après split:**
- 8 chunks: 3.4 MB à 7.6 MB chacun
- Index de navigation complet
- Original archivé: `.jsonl.original`
- Version compressée: `.jsonl.gz` (7.8 MB)

**Avantages:**
- ✅ Fichiers navigables dans IDE
- ✅ Git diff rapide (seul le chunk modifié)
- ✅ Recherche ciblée par période (timestamps dans index)
- ✅ Backup granulaire (chunks séparés)

---

## 🚀 Roadmap Future

### Améliorations potentielles

1. **Compression automatique des chunks**
   - Gzipper chunks > 5 MB après split
   - Économie d'espace disque et GitHub

2. **Rotation par date**
   - Archiver sessions > 90 jours
   - Déplacer vers `project-docs/sessions/archive/`

3. **Métadonnées enrichies**
   - Extraire commits mentionnés
   - Index des fichiers modifiés par chunk
   - Timeline visuelle des activités

4. **Dashboard de sessions**
   - Vue HTML des sessions avec recherche
   - Statistiques d'utilisation de Claude Code
   - Heatmap des jours d'activité

---

**Dernière mise à jour:** 27 janvier 2026
**Responsable:** Claude Sonnet 4.5 + Stéphane
