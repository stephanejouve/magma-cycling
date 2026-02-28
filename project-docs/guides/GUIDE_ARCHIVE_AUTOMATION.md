# Guide - Automatisation des Archives Claude Code

## Vue d'ensemble

Le système d'archivage automatique permet de créer des archives complètes du projet (contexte Claude Code / MOA) uniquement lorsque nécessaire, via un mécanisme de contrôle par fichier flag.

## Mécanisme de Contrôle

### Fichier de Contrôle: `.archive_needed`

**Emplacement**: Racine du projet (`/Users/stephanejouve/magma-cycling/.archive_needed`)

**Valeurs possibles**:
- `TRUE` : Archive sera créée au prochain run du bot de nettoyage
- `FALSE` : Aucune archive ne sera créée (défaut)

**Note**: Ce fichier est gitignored (local seulement)

## Workflow d'Utilisation

### 1. Demander une Archive

Quand vous avez besoin d'une archive (requête MOA, livraison sprint, etc.):

```bash
cd ~/magma-cycling
./scripts/maintenance/request_archive.sh
```

**Effet**:
- Crée/met à jour `.archive_needed` avec `TRUE`
- Le bot de nettoyage créera l'archive au prochain run

### 2. Vérifier le Statut

Pour voir si une archive est demandée:

```bash
./scripts/maintenance/request_archive.sh status
```

**Réponse**:
- "📦 Archive REQUESTED" si TRUE
- "No archive requested" si FALSE

### 3. Annuler une Demande

Pour annuler une demande d'archive:

```bash
./scripts/maintenance/request_archive.sh cancel
```

### 4. Déclenchement Automatique

Le bot de nettoyage (`project-clean`) s'exécute:

1. **Automatiquement**: Une fois par jour via LaunchAgent (minuit)
2. **Manuellement**: `poetry run project-clean`

À chaque exécution:
- Vérifie `.archive_needed`
- Si `TRUE`: Crée archive + Reset à `FALSE`
- Si `FALSE`: Continue le nettoyage normal

## Quand Demander une Archive ?

### ✅ Cas d'Usage Recommandés

1. **Requête MOA**
   ```bash
   ./scripts/maintenance/request_archive.sh
   # Attendre le prochain run (ou forcer: poetry run project-clean)
   # Archive disponible dans: project-docs/archives/claude-code/
   ```

2. **Livraison de Sprint**
   ```bash
   # Juste avant la livraison
   ./scripts/maintenance/request_archive.sh
   poetry run project-clean  # Force immediate
   ```

3. **Session Claude Code Importante**
   ```bash
   # Avant une grande session de refactoring
   ./scripts/maintenance/request_archive.sh
   poetry run project-clean
   ```

### ❌ Quand NE PAS Demander

- Commits quotidiens normaux
- Petites modifications
- Tests en cours
- Travaux en brouillon

## Architecture Technique

### Script de Contrôle

**`scripts/maintenance/request_archive.sh`**
- Simple wrapper pour définir `.archive_needed = TRUE/FALSE`
- Commandes: `request`, `cancel`, `status`

### Bot de Nettoyage

**`scripts/maintenance/project_cleaner.py`**
- Fonction `check_and_run_claude_archive()` appelée au début de `main()`
- Lit `.archive_needed`
- Si `TRUE`: Exécute `scripts/backup/create_claude_code_archive.sh`
- Reset à `FALSE` après succès

### Script d'Archive

**`scripts/backup/create_claude_code_archive.sh`**
- Crée archive complète (code, docs, logs, exemples)
- Génère checksum SHA256 pour vérification d'intégrité
- Sauvegarde dans: `project-docs/archives/claude-code/`
- Format: `claude-code-context_YYYYMMDD_HHMMSS.tar.gz` + `.sha256`
- Taille: ~300KB

### LaunchAgent

**`com.cyclisme.project-cleaner.plist`**
- S'exécute quotidiennement (86400s)
- Lance: `poetry run project-clean`
- Logs: `~/Library/Logs/project-cleaner.log`

## Exemples Complets

### Exemple 1: Préparation Prompt MOA

```bash
# Stéphane a besoin de l'archive pour un prompt MOA

# 1. Demander l'archive
cd ~/magma-cycling
./scripts/maintenance/request_archive.sh
# ✅ Archive requested

# 2. Forcer la création immédiate (optionnel, sinon attendre minuit)
poetry run project-clean
# 🎯 Claude Code archive requested (.archive_needed = TRUE)
# Creating archive...
# ✅ Archive créée: project-docs/archives/claude-code/claude-code-context_20260118_153022.tar.gz
# 🔐 SHA256: 5145debaa7271765b4227dc1487ec1d47e4910ca3d124b691d668d768c13196f

# 3. Vérifier l'intégrité (optionnel mais recommandé)
cd project-docs/archives/claude-code
shasum -a 256 -c claude-code-context_20260118_153022.tar.gz.sha256
# claude-code-context_20260118_153022.tar.gz: OK

# 4. Utiliser l'archive dans le prompt MOA
# Chemin: ~/magma-cycling/project-docs/archives/claude-code/claude-code-context_20260118_153022.tar.gz
# Checksum disponible pour vérification si transfert réseau
```

### Exemple 2: Livraison Sprint

```bash
# Livraison Sprint R9.E

# 1. Finaliser les commits
git add .
git commit -m "feat: Complete Sprint R9.E"
git push

# 2. Demander archive pour MOA
./scripts/maintenance/request_archive.sh

# 3. Créer immédiatement
poetry run project-clean

# 4. Archive disponible pour validation MOA
# project-docs/archives/claude-code/claude-code-context_20260118_154530.tar.gz
```

### Exemple 3: Vérification Quotidienne

```bash
# Le bot s'exécute automatiquement chaque jour
# Logs disponibles:
tail -f ~/Library/Logs/project-cleaner.log

# Si archive demandée, le log contiendra:
# 🎯 Claude Code archive requested (.archive_needed = TRUE)
# Creating archive...
# ✅ Claude Code archive created successfully
# ✅ Reset .archive_needed = FALSE
```

## Avantages du Système

1. **Contrôle Explicite**: Archives créées uniquement sur demande
2. **Automatisation**: Pas besoin d'exécuter manuellement (LaunchAgent)
3. **Traçabilité**: Status visible avec `request_archive.sh status`
4. **Simplicité**: Un seul fichier flag (.archive_needed)
5. **Intégration**: S'intègre au bot de nettoyage existant
6. **Pas de Pollution**: Archives créées uniquement quand pertinent

## Dépannage

### L'archive n'est pas créée

```bash
# 1. Vérifier le flag
./scripts/maintenance/request_archive.sh status

# 2. Vérifier les logs LaunchAgent
tail -20 ~/Library/Logs/project-cleaner.log

# 3. Forcer manuellement
poetry run project-clean

# 4. Vérifier l'existence de l'archive
ls -lh project-docs/archives/claude-code/
```

### Le LaunchAgent ne s'exécute pas

```bash
# Vérifier le statut
launchctl list | grep project-cleaner

# Recharger le LaunchAgent
launchctl unload ~/Library/LaunchAgents/com.cyclisme.project-cleaner.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.project-cleaner.plist
```

### Le script request_archive.sh n'est pas exécutable

```bash
chmod +x scripts/maintenance/request_archive.sh
```

## Référence Rapide

```bash
# Demander archive
./scripts/maintenance/request_archive.sh

# Vérifier statut
./scripts/maintenance/request_archive.sh status

# Annuler demande
./scripts/maintenance/request_archive.sh cancel

# Forcer création immédiate
poetry run project-clean

# Voir dernière archive
ls -lhtr project-docs/archives/claude-code/ | tail -2

# Vérifier intégrité d'une archive
cd project-docs/archives/claude-code
shasum -a 256 -c <archive>.tar.gz.sha256

# Logs du bot
tail -f ~/Library/Logs/project-cleaner.log
```

## Fichiers Concernés

- `.archive_needed` - Fichier flag (gitignored)
- `scripts/maintenance/request_archive.sh` - Script de contrôle
- `scripts/maintenance/project_cleaner.py` - Bot de nettoyage (modifié)
- `scripts/backup/create_claude_code_archive.sh` - Script d'archivage
- `project-docs/archives/claude-code/` - Destination des archives
- `~/Library/LaunchAgents/com.cyclisme.project-cleaner.plist` - Automation

## Voir Aussi

- [project-docs/archives/README.md](../archives/README.md) - Organisation des archives
- [project-docs/archives/claude-code/README.md](../archives/claude-code/README.md) - Format des archives
- [ROADMAP.md](../ROADMAP.md) - Planification sprints
