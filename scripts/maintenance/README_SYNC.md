# iCloud Documentation Sync

Synchronisation automatique des docs projet vers iCloud pour partage facile depuis iPhone.

## 🎯 Objectif

Rendre disponibles les docs MOA et techniques sur iPhone via iCloud Drive pour:
- Joindre facilement les LIVRAISON_MOA aux emails
- Consulter ROADMAP et CHANGELOG en déplacement
- Partager docs à jour avec la MOA depuis n'importe où

## 📁 Ce qui est synchronisé

**Source:** `project-docs/` (dans le projet)

**Destination:** `~/Documents/magma-cycling-docs/` (→ iCloud)

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
3. Dossier: **magma-cycling-docs**
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
du -sh ~/Documents/magma-cycling-docs

# Nettoyer les vieux fichiers (manuel)
rm -rf ~/Documents/magma-cycling-docs/sessions/OLD_*.md
```

### Conflits de fichiers
Le script utilise `--update` (skip si plus récent côté iCloud) et `--ignore-errors` pour éviter les conflits pendant le sync iCloud.

Si conflit manuel détecté:
```bash
# Forcer re-sync complet
rm -rf ~/Documents/magma-cycling-docs
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

## 🗑️ Nettoyage Archives iCloud

**Script:** `cleanup_old_archives.py`

**Objectif:** Libérer espace iCloud en supprimant anciennes archives MOA.

**Stratégie par défaut:** Garde les **3 archives les plus récentes**

### Commandes

**Nettoyage standard (garde 3 récentes):**
```bash
poetry run cleanup-archives
```

**Garde N archives:**
```bash
poetry run cleanup-archives --keep 5
```

**Garde archives de moins de N jours:**
```bash
poetry run cleanup-archives --keep-days 30
```

**Prévisualiser (dry-run):**
```bash
poetry run cleanup-archives --dry-run
```

### Où nettoie-t-il?

**✅ Nettoie:** `~/Documents/magma-cycling-archives/` (iCloud)

**❌ Préserve:** `releases/` (local, jamais touché)

### Automatisation (optionnelle)

**Option 1: Hebdomadaire (recommandé)**

Exécuter manuellement après chaque livraison MOA:
```bash
poetry run cleanup-archives
```

**Option 2: LaunchAgent hebdomadaire**

Si besoin d'automatisation (non implémenté par défaut):
```bash
# Créer LaunchAgent pour nettoyage le dimanche
# StartCalendarInterval: Day 0 (dimanche), Hour 23
```

### Exemple de sortie

```
🗑️  iCloud Archives Cleanup

Archives to keep (most recent 3):
  ✅ sprint-r9-v2.2.0-20260117.tar.gz (18.9 MB, 2026-01-17 07:45)
  ✅ sprint-r8-v2.2.0-20260111.tar.gz (17.2 MB, 2026-01-11 22:30)
  ✅ sprint-r7-v2.2.0-20260104.tar.gz (16.8 MB, 2026-01-04 18:15)

Archives to delete:
  ❌ sprint-r6-v2.2.0-20251228.tar.gz (15.3 MB, 2025-12-28 14:20)
  ❌ sprint-r5-v2.2.0-20251221.tar.gz (14.9 MB, 2025-12-21 09:45)

Summary:
  Mode: keeping 3 most recent
  Files deleted: 4 (2 archives + 2 checksums)
  Space freed: 30.2 MB

✅ Cleanup completed successfully!
```

### Sécurité

- ✅ Archives locales (`releases/`) **jamais touchées**
- ✅ Dry-run disponible pour prévisualiser
- ✅ Ne supprime que les `.tar.gz` et `.sha256` dans iCloud
- ✅ Garde toujours les N plus récentes

---

**Créé:** 17 janvier 2026
**Automatisation:** LaunchAgent macOS
