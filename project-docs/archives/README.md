# Archives

Ce répertoire contient les archives du projet pour référence historique et partage de contexte.

## Structure

### `old-releases/`
Anciennes releases Sprint R4 (obsolètes, remplacées par les sprints R5-R9)
- Les fichiers `.tar.gz` ne sont pas trackés par git (voir `.gitignore`)
- Conservés pour référence historique uniquement
- Ces fichiers ne sont plus utilisés depuis Sprint R5

### `claude-code/`
Archives complètes du projet pour Claude Code et MOA
- Créées automatiquement par `scripts/backup/create-claude-archive.sh` ou `create_claude_code_archive.sh`
- Contenu : code source, documentation, logs récents, exemples
- Format : `claude-code-context_YYYYMMDD_HHMMSS.tar.gz`
- Les fichiers `.tar.gz` ne sont pas trackés par git (voir `.gitignore`)
- **Utilisation** : Archives de contexte complet pour nouvelles sessions Claude Code ou prompts MOA

## Génération d'Archive

### Méthode Automatique (Recommandée)

Utilise le système de contrôle par flag pour déclencher l'archivage au prochain run du bot:

```bash
cd ~/magma-cycling
./scripts/maintenance/request_archive.sh

# Forcer création immédiate (optionnel)
poetry run project-clean
```

**Quand utiliser**: Requêtes MOA, livraisons sprint, sessions Claude Code importantes

**Documentation complète**: Voir [GUIDE_ARCHIVE_AUTOMATION.md](../guides/GUIDE_ARCHIVE_AUTOMATION.md)

### Méthode Manuelle (Alternative)

Création directe sans passer par le bot de nettoyage:

```bash
cd ~/magma-cycling
./scripts/backup/create_claude_code_archive.sh
# Archive créée dans: project-docs/archives/claude-code/
```

## Note

Pour les releases actuelles, voir `project-docs/ROADMAP.md`.
