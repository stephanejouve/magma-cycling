# Archives Claude Code

Ce répertoire contient les archives complètes du projet pour partager le contexte avec Claude Code ou les prompts MOA.

## Format des Archives

- **Nom**: `claude-code-context_YYYYMMDD_HHMMSS.tar.gz`
- **Checksum**: `claude-code-context_YYYYMMDD_HHMMSS.tar.gz.sha256` (SHA256)
- **Contenu**:
  - Code source complet (cyclisme_training_logs/)
  - Documentation technique (POETRY_ARCHITECTURE.md, IMPLEMENTATION_BRIEF.md, etc.)
  - Logs récents (workouts-history.md, 3 dernières semaines de rapports)
  - Exemples (planning JSON, workout templates)
  - Configuration (pyproject.toml, poetry.lock)

## Génération d'une Nouvelle Archive

Pour créer une archive à jour du projet:

```bash
cd ~/cyclisme-training-logs
./scripts/backup/create_claude_code_archive.sh
```

L'archive sera créée dans ce répertoire: `project-docs/archives/claude-code/`

## Scripts Disponibles

Deux scripts peuvent créer des archives (contenu similaire):
- `scripts/backup/create-claude-archive.sh` - Version simplifiée
- `scripts/backup/create_claude_code_archive.sh` - Version complète avec documentation Poetry

## Utilisation

### Pour Claude Code
1. Extraire l'archive: `tar -xzf claude-code-context_*.tar.gz`
2. Lire dans l'ordre:
   - `POETRY_ARCHITECTURE.md` (architecture technique)
   - `IMPLEMENTATION_BRIEF.md` (vision système)
   - `CURRENT_STATE.md` (état actuel)
   - `README_ARCHIVE.md` (guide utilisation)

### Pour Prompts MOA
Fournir le chemin complet de l'archive la plus récente comme contexte dans le prompt.

### Vérification d'Intégrité

Pour vérifier qu'une archive n'a pas été corrompue:

```bash
cd project-docs/archives/claude-code
shasum -a 256 -c claude-code-context_YYYYMMDD_HHMMSS.tar.gz.sha256
# Résultat attendu: claude-code-context_YYYYMMDD_HHMMSS.tar.gz: OK
```

## Politique de Rétention

Les archives ne sont pas trackées par git (`.gitignore` contient `*.gz`).

Recommandation: Conserver les 3-5 archives les plus récentes, supprimer les anciennes pour économiser l'espace disque.

## Emplacement Ancien (Déprécié)

Avant le 18/01/2026, les archives étaient créées dans `~/` (répertoire home). Cet emplacement n'est plus utilisé. Les anciennes archives peuvent être supprimées ou déplacées ici si nécessaire.
