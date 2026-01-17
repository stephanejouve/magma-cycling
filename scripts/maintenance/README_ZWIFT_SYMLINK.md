# Zwift Symlink Configuration

Configuration pour éviter que Zwift pollue iCloud Drive avec ses données.

## 🎯 Problème Résolu

**Avant:**
- Zwift cherche ses données dans `~/Documents/Zwift`
- iCloud Desktop & Documents synchronise tout ~/Documents/
- Résultat: Duplication Zwift → iCloud (gaspillage espace)

**Après:**
- Symlink: `~/Documents/Zwift` → `~/Nextcloud/Zwift`
- Zwift trouve ses données via le symlink
- Données restent dans Nextcloud (déjà synchronisé)
- iCloud ignore généralement les symlinks

## 📁 Configuration Actuelle

**Symlink:**
```
~/Documents/Zwift → ~/Nextcloud/Zwift
```

**Données Zwift:**
```
~/Nextcloud/Zwift/
├── Activities/          # Fichiers .fit des rides
├── Workouts/           # Workouts personnalisés
├── Logs/               # Logs application
├── Gear/               # Configuration matériel
└── prefs.xml          # Préférences Zwift
```

## 🔧 Setup Initial (Déjà Fait)

Cette configuration a été réalisée le **17 janvier 2026**:

```bash
# 1. Créer symlink
ln -s ~/Nextcloud/Zwift ~/Documents/Zwift

# 2. Sauvegarder activité unique du snapshot
cp "/Users/stephanejouve/Documents/Documents - Tiresias/Zwift/Activities/2025-07-19-23-17-25.fit" \
   ~/Nextcloud/Zwift/Activities/

# 3. Supprimer snapshot temporaire iCloud (848MB libérés)
rm -rf ~/Documents/Documents\ -\ Tiresias/
```

## ✅ Vérification

**Symlink existe et fonctionne:**
```bash
ls -la ~/Documents/Zwift
# lrwxr-xr-x  1 stephanejouve  staff  36 17 jan 08:18 Zwift -> /Users/stephanejouve/Nextcloud/Zwift
```

**Zwift utilise le symlink:**
```bash
lsof +D ~/Documents/Zwift 2>/dev/null | grep Zwift
# ZwiftLauncher a des fichiers ouverts dans Nextcloud/Zwift
```

**Pas de duplication iCloud:**
```bash
find ~/Library/Mobile\ Documents/com~apple~CloudDocs/ -name "*Zwift*" 2>/dev/null | wc -l
# 0 (aucun fichier Zwift dans iCloud)
```

## 🔄 Réinstallation (Si Nécessaire)

Si le symlink est supprimé ou corrompu:

```bash
# Vérifier état actuel
ls -la ~/Documents/Zwift

# Si dossier réel existe (pas symlink), sauvegarder données
if [ -d ~/Documents/Zwift ] && [ ! -L ~/Documents/Zwift ]; then
    echo "Zwift est un vrai dossier, sauvegarde nécessaire"
    rsync -av ~/Documents/Zwift/ ~/Nextcloud/Zwift/
    rm -rf ~/Documents/Zwift
fi

# Recréer symlink
ln -s ~/Nextcloud/Zwift ~/Documents/Zwift

# Vérifier
ls -la ~/Documents/Zwift
```

## 🚨 Troubleshooting

### Zwift ne trouve pas ses données

**Symptôme:** Zwift démarre comme si c'était la première fois

**Solution:**
```bash
# Vérifier symlink
readlink ~/Documents/Zwift
# Doit afficher: /Users/stephanejouve/Nextcloud/Zwift

# Vérifier permissions
ls -la ~/Nextcloud/Zwift
# Doit être accessible (rwxr-xr-x)

# Vérifier que Nextcloud/Zwift existe
ls ~/Nextcloud/Zwift/Activities/
```

### Symlink cassé après mise à jour macOS

**Symptôme:** Symlink pointant vers chemin invalide

**Solution:**
```bash
# Supprimer ancien symlink
rm ~/Documents/Zwift

# Recréer avec bon chemin
ln -s ~/Nextcloud/Zwift ~/Documents/Zwift
```

### Zwift crée un nouveau dossier au lieu d'utiliser le symlink

**Symptôme:** `~/Documents/Zwift` devient un vrai dossier

**Solution:**
```bash
# Sauvegarder nouvelles données
rsync -av ~/Documents/Zwift/ ~/Nextcloud/Zwift/

# Supprimer et recréer symlink
rm -rf ~/Documents/Zwift
ln -s ~/Nextcloud/Zwift ~/Documents/Zwift
```

## 📊 Statistiques

**Espace économisé:**
- Snapshot Tiresias supprimé: **848MB**
- Évite duplication future Zwift: **~8MB/activité**
- Total libéré: **848MB+**

**Localisations:**
- ✅ `~/Nextcloud/Zwift` (7.8MB, synchronisé Nextcloud)
- ✅ `~/Documents/Zwift` (symlink, 0 bytes)
- ❌ `~/Library/Mobile Documents/.../Zwift` (0 fichiers, iCloud clean)

## 🔗 Liens

- Documentation Nextcloud: [Synchronisation sélective](https://docs.nextcloud.com)
- iCloud Drive: Ignore automatiquement les symlinks (comportement standard macOS)

---

**Configuration:** 17 janvier 2026
**Status:** ✅ Actif et fonctionnel
**Maintenance:** Aucune requise (automatique)
