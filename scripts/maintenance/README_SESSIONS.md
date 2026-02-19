# Session Management Scripts

Scripts pour gérer et archiver les sessions Claude Code.

## 📋 Scripts Disponibles

### 1. `session_summarizer.py` - Résumé de Sessions

Génère des résumés markdown automatiques à partir des fichiers JSONL de session.

**Usage:**
```bash
# Résumer une session spécifique
python scripts/maintenance/session_summarizer.py ~/.claude/projects/.../session.jsonl

# Avec sortie personnalisée
python scripts/maintenance/session_summarizer.py session.jsonl --output summary.md

# Afficher dans stdout
python scripts/maintenance/session_summarizer.py session.jsonl --stdout
```

**Contenu du résumé:**
- Vue d'ensemble (date, durée, objectif)
- Commits créés
- Fichiers créés/modifiés
- Décisions prises (questions posées)
- Tâches trackées (todos)
- Outils utilisés
- Erreurs rencontrées

### 2. `archive_claude_sessions.py` - Archivage de Sessions

Archive et résume automatiquement les anciennes sessions Claude Code.

**Usage:**
```bash
# Lister toutes les sessions
python scripts/maintenance/archive_claude_sessions.py

# Archiver sessions >30 jours (dry-run)
python scripts/maintenance/archive_claude_sessions.py --auto --dry-run

# Archiver sessions >30 jours (réel)
python scripts/maintenance/archive_claude_sessions.py --auto

# Archiver sessions >60 jours
python scripts/maintenance/archive_claude_sessions.py --auto --days 60

# Archiver une session spécifique
python scripts/maintenance/archive_claude_sessions.py --session-id abc12345
```

**Ce que fait le script:**
1. ✅ Liste toutes les sessions Claude Code
2. 📝 Génère un résumé markdown pour chaque session
3. 📦 Crée une archive compressée (.tar.gz) contenant:
   - Fichier JSONL de la session
   - Résumé markdown
4. 🗑️ Supprime les fichiers originaux après archivage
5. 💾 Stocke les archives dans `project-docs/sessions/archives/`

**Code couleur des sessions:**
- 🟢 Vert: < 7 jours (récentes)
- 🟡 Jaune: 7-30 jours (moyennes)
- 🔴 Rouge: > 30 jours (anciennes, candidates à l'archivage)

### 3. `cleanup_old_archives.py` - Nettoyage des Archives

Nettoie les anciennes archives de sprint pour libérer de l'espace.

**Usage:**
```bash
# Garder les 3 archives les plus récentes
poetry run cleanup-archives

# Garder les 5 archives les plus récentes
poetry run cleanup-archives --keep 5

# Garder les archives des 30 derniers jours
poetry run cleanup-archives --keep-days 30

# Dry-run (preview)
poetry run cleanup-archives --dry-run
```

## 🔄 Workflow Recommandé

### Archivage Mensuel

```bash
# 1. Voir les sessions actuelles
python scripts/maintenance/archive_claude_sessions.py

# 2. Dry-run pour preview
python scripts/maintenance/archive_claude_sessions.py --auto --dry-run

# 3. Archiver (sessions >30 jours)
python scripts/maintenance/archive_claude_sessions.py --auto

# 4. Vérifier les archives créées
ls -lh project-docs/sessions/archives/
```

### Archivage Trimestriel

```bash
# Archiver sessions >60 jours
python scripts/maintenance/archive_claude_sessions.py --auto --days 60

# Nettoyer anciennes archives de sprint
poetry run cleanup-archives --keep-days 90
```

## 📁 Structure des Fichiers

```
project-docs/sessions/
├── archives/                          # Archives compressées
│   ├── session_98f83f8f_20260219.tar.gz
│   └── session_46864120_20260219.tar.gz
└── SESSION_*_SUMMARY.md              # Résumés markdown

~/.claude/projects/-Users-.../
├── 98f83f8f-11cb-43bf-8018-ed3cc6bdac9f.jsonl  # Sessions actives
└── 46864120-e85e-4d67-a77a-e39a0d41cf00.jsonl
```

## 🛡️ Sécurité

- **Dry-run first**: Toujours utiliser `--dry-run` avant d'archiver
- **Backup**: Les archives sont créées AVANT suppression des originaux
- **Compression**: Les archives .tar.gz économisent ~70% d'espace
- **Vérification**: Le script vérifie que l'archive est créée avant suppression

## 💡 Conseils

1. **Fréquence**: Archiver tous les mois (sessions >30 jours)
2. **Espace**: Une session moyenne fait ~10 MB, archive ~3 MB
3. **Récupération**: Décompresser avec `tar -xzf session_*.tar.gz`
4. **Git**: Les archives ne sont PAS commitées (trop volumineuses)

## 📊 Exemple de Sortie

```
Claude Code Sessions:

Session ID           Age          Size       Last Modified
----------------------------------------------------------------------
98f83f8f-11cb-43bf-8   0 days     8.0 MB   2026-02-19 07:24
65660f48-330a-4ff4-9   2 days     6.4 MB   2026-02-16 18:46
d71ddbcd-7e4d-4290-8   8 days     5.4 MB   2026-02-10 22:23
46864120-e85e-4d67-a  32 days    16.6 MB   2026-01-17 19:50  ← À archiver

💡 Tip: Use --auto to archive old sessions automatically
```
