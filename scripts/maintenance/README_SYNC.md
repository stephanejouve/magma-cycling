# iCloud Documentation Sync

Synchronisation automatique des docs projet vers iCloud pour partage facile depuis iPhone.

## 🎯 Objectif

Rendre disponibles les docs MOA et techniques sur iPhone via iCloud Drive pour:
- Joindre facilement les LIVRAISON_MOA aux emails
- Consulter ROADMAP et CHANGELOG en déplacement
- Partager docs à jour avec la MOA depuis n'importe où

## 📁 Ce qui est synchronisé

**Source:** `project-docs/` (dans le projet)

**Destination:** `~/Documents/cyclisme-training-logs-docs/` (→ iCloud)

**Contenu synchronisé:**
- ✅ `ROADMAP.md`, `CHANGELOG.md`, `README.md`
- ✅ `guides/` - Guides développeur
- ✅ `sprints/` - **Tous les sprints + LIVRAISON_MOA**
- ✅ `sessions/` - Session logs
- ✅ `architecture/` - Docs architecture
- ✅ `workflows/` - Docs workflows

**Contenu exclu:**
- ❌ `archives/` - Historique volumineux
- ❌ `logs/` - Logs techniques (transcripts)
- ❌ `audits/` - Audits techniques
- ❌ `prompts/` - Prompts IA

**Résultat:** ~924KB, 61 fichiers, 8 répertoires

## 🚀 Installation (première fois)

Si le LaunchAgent n'est pas encore installé:

```bash
# Copier le plist dans LaunchAgents
cp scripts/maintenance/com.cyclisme.sync-docs-icloud.plist ~/Library/LaunchAgents/

# Charger le LaunchAgent
launchctl load ~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist

# Vérifier qu'il tourne
launchctl list | grep cyclisme
```

Résultat attendu: `com.cyclisme.sync-docs-icloud` avec exit code 0

## 🤖 Synchronisation Automatique

**LaunchAgent actif:** `com.cyclisme.sync-docs-icloud`

**Fréquence:**
- ✅ Au démarrage système (RunAtLoad)
- ✅ Toutes les heures (StartInterval: 3600s)

**Logs:**
- Standard: `~/Library/Logs/sync-docs-icloud.log`
- Erreurs: `~/Library/Logs/sync-docs-icloud.error.log`

## 📱 Accès depuis iPhone

1. Ouvrir l'app **Files** (Fichiers)
2. Naviguer: **iCloud Drive → Documents**
3. Dossier: **cyclisme-training-logs-docs**
4. Tous les docs disponibles immédiatement!

**Partage depuis iPhone:**
- Ouvrir doc dans Files app
- Bouton Partager → Mail/Messages/AirDrop

## 🛠️ Commandes Manuelles

### Synchroniser immédiatement
```bash
scripts/maintenance/sync_docs_icloud.sh
```

### Prévisualiser (dry-run)
```bash
scripts/maintenance/sync_docs_icloud.sh --dry-run
```

### Voir statistiques détaillées
```bash
scripts/maintenance/sync_docs_icloud.sh --stats
```

### Mode verbose
```bash
scripts/maintenance/sync_docs_icloud.sh -v
```

## 🔧 Gestion LaunchAgent

### Voir le status
```bash
launchctl list | grep cyclisme
```

### Recharger après modification
```bash
launchctl unload ~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist
```

### Désactiver temporairement
```bash
launchctl unload ~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist
```

### Réactiver
```bash
launchctl load ~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist
```

### Voir les logs en temps réel
```bash
tail -f ~/Library/Logs/sync-docs-icloud.log
```

## ⚙️ Configuration

### Fichier LaunchAgent
`~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist`

### Changer la fréquence
Éditer le plist, modifier `StartInterval`:
```xml
<key>StartInterval</key>
<integer>3600</integer>  <!-- Secondes (3600 = 1h) -->
```

Valeurs courantes:
- 1800 = 30 minutes
- 3600 = 1 heure (actuel)
- 7200 = 2 heures
- 21600 = 6 heures

Puis recharger:
```bash
launchctl unload ~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist
launchctl load ~/Library/LaunchAgents/com.cyclisme.sync-docs-icloud.plist
```

## 🐛 Troubleshooting

### Le sync ne fonctionne pas
```bash
# Vérifier que le LaunchAgent tourne
launchctl list | grep cyclisme

# Vérifier les logs d'erreur
cat ~/Library/Logs/sync-docs-icloud.error.log

# Tester manuellement
scripts/maintenance/sync_docs_icloud.sh -v
```

### iCloud Drive plein
Le dossier fait ~1MB, très léger. Si problème de quota:
```bash
# Voir la taille
du -sh ~/Documents/cyclisme-training-logs-docs

# Nettoyer les vieux fichiers (manuel)
rm -rf ~/Documents/cyclisme-training-logs-docs/sessions/OLD_*.md
```

### Conflits de fichiers
Le script utilise `--update` (skip si plus récent côté iCloud) et `--ignore-errors` pour éviter les conflits pendant le sync iCloud.

Si conflit manuel détecté:
```bash
# Forcer re-sync complet
rm -rf ~/Documents/cyclisme-training-logs-docs
scripts/maintenance/sync_docs_icloud.sh
```

## 📝 Notes

- La synchro est **one-way** (projet → iCloud), pas de sync inverse
- Les modifications dans iCloud seront écrasées au prochain sync
- Utiliser iCloud uniquement pour **consultation et partage**, pas édition
- Les fichiers `.DS_Store`, `.json`, `.jsonl` sont exclus automatiquement

## 🧹 Project Cleaner Automation

**LaunchAgent:** `com.cyclisme.project-cleaner`

**Ce qu'il fait:**
- Nettoie fichiers temporaires (`__pycache__`, `.DS_Store`, `.pyc`, etc.)
- Identifie fichiers mal placés à la racine
- Vérifie standards pre-commit

**Fréquence:**
- ✅ Au démarrage système
- ✅ Une fois par jour (86400s)

**Logs:**
- Standard: `~/Library/Logs/project-cleaner.log`
- Erreurs: `~/Library/Logs/project-cleaner.error.log`

**Installation:**
```bash
# Copier le plist
cp scripts/maintenance/com.cyclisme.project-cleaner.plist ~/Library/LaunchAgents/

# Charger le LaunchAgent
launchctl load ~/Library/LaunchAgents/com.cyclisme.project-cleaner.plist

# Vérifier
launchctl list | grep project-cleaner
```

**Sécurité:** Safe, supprime seulement les fichiers temporaires standard.

---

**Créé:** 17 janvier 2026
**Automatisation:** LaunchAgent macOS
