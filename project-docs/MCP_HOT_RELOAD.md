# MCP Hot Reload - Guide Développeur

**Date**: 21 Février 2026
**Version**: 1.0

---

## 📋 Vue d'ensemble

Le système de hot reload permet de modifier le code du serveur MCP sans avoir à relancer Claude Desktop. Deux méthodes sont disponibles :

1. **Watchdog auto-restart** (Recommandé) - Rechargement automatique à chaque modification
2. **Outil `reload-server`** (Fallback) - Rechargement manuel via MCP

---

## 🚀 Méthode 1 : Watchdog Auto-Restart (Recommandé)

### Configuration

1. **Activer le mode dev** dans Claude Desktop config :

```bash
# Copier le fichier exemple
cp claude_desktop_config_dev.json.example ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Ou modifier manuellement :

```json
{
  "mcpServers": {
    "cyclisme-training": {
      "command": "/Users/stephanejouve/cyclisme-training-logs/mcp-server-wrapper.sh",
      "env": {
        "MCP_DEV_MODE": "1"
      }
    }
  }
}
```

2. **Relancer Claude Desktop** une seule fois

### Fonctionnement

- ✅ Watchdog surveille tous les fichiers `*.py` dans `cyclisme_training_logs/`
- ✅ À chaque modification détectée, le serveur MCP redémarre automatiquement
- ✅ Debounce de 0.5s pour éviter les redémarrages multiples
- ✅ Claude Desktop reste connecté (reconnexion transparente)

### Logs

```bash
# Surveiller les redémarrages
tail -f /tmp/mcp-server-debug.log
```

Exemple :
```
[MCP] Dev mode enabled - auto-reload on file changes
[watchmedo] Restarting server on change: cyclisme_training_logs/mcp_server.py
```

---

## 🔧 Méthode 2 : Outil reload-server (Fallback)

### Utilisation

Depuis Claude Desktop, appeler l'outil MCP :

```
Peux-tu recharger le serveur MCP ?
```

Ou directement :
```json
{
  "tool": "reload-server",
  "arguments": {}
}
```

### Réponse

```json
{
  "success": true,
  "reloaded_count": 5,
  "reloaded_modules": [
    "cyclisme_training_logs.config",
    "cyclisme_training_logs.planning.models",
    "cyclisme_training_logs.planning.control_tower",
    "cyclisme_training_logs.daily_sync",
    "cyclisme_training_logs.weekly_planner"
  ],
  "message": "✅ Reloaded 5 modules",
  "note": "MCP server handlers NOT reloaded (requires watchdog auto-restart or manual restart)"
}
```

### Limitations

⚠️ **L'outil `reload-server` ne recharge PAS** :
- Les handlers MCP (`handle_*` functions)
- Les Tool definitions
- L'initialisation du serveur MCP

Pour ces changements, utiliser **watchdog auto-restart** ou relancer Claude Desktop.

---

## 📊 Comparaison

| Aspect | Watchdog Auto-Restart | reload-server |
|--------|----------------------|---------------|
| **Activation** | Automatique sur fichier modifié | Manuel via MCP tool |
| **Handlers MCP** | ✅ Rechargés | ❌ Non rechargés |
| **Tool definitions** | ✅ Rechargés | ❌ Non rechargés |
| **Modules métier** | ✅ Rechargés | ✅ Rechargés |
| **Transparence** | ✅ Invisible pour Claude | ⚠️ Visible (appel outil) |
| **Délai** | ~1s après modif | Instantané après appel |

---

## 🎯 Cas d'usage

### Watchdog (Recommandé pour)
- ✅ Développement intensif avec modifications fréquentes
- ✅ Modification des handlers MCP
- ✅ Ajout/modification de tools
- ✅ Changements structurels

### reload-server (Utile pour)
- ✅ Petit fix dans un module métier
- ✅ Mode production avec MCP_DEV_MODE=0
- ✅ Debug ponctuel sans relancer Claude Desktop

---

## ⚙️ Configuration avancée

### Personnaliser watchdog

Modifier `mcp-server-wrapper.sh` :

```bash
exec $VENV_PYTHON -m watchdog.watchmedo auto-restart \
    -d cyclisme_training_logs \
    -p "*.py" \                        # Patterns à surveiller
    -R \                               # Récursif
    --interval 1.0 \                   # Vérification toutes les 1s
    --debounce-interval 0.5 \          # Attendre 0.5s après dernier changement
    --kill-after 3.0 \                 # Timeout kill process
    -- $VENV_PYTHON -m cyclisme_training_logs.mcp_server
```

### Ajouter modules à reload-server

Modifier `cyclisme_training_logs/mcp_server.py` :

```python
async def handle_reload_server(args: dict):
    modules_to_reload = [
        "cyclisme_training_logs.config",
        "cyclisme_training_logs.planning.models",
        # ... modules existants
        "cyclisme_training_logs.nouveau_module",  # ← Ajouter ici
    ]
```

---

## 🐛 Troubleshooting

### Watchdog ne détecte pas les changements

**Cause** : MCP_DEV_MODE non activé

**Solution** :
```bash
# Vérifier config Claude Desktop
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | grep MCP_DEV_MODE

# Doit afficher : "MCP_DEV_MODE": "1"
```

### Serveur plante après reload

**Cause** : Conflit d'état entre modules

**Solution** : Relancer Claude Desktop (restart complet)

### reload-server ne recharge pas les handlers

**Cause** : Limitation technique (fonctions async déjà enregistrées)

**Solution** : Utiliser watchdog auto-restart pour ces modifications

---

## 📚 Références

- **Watchdog documentation** : https://github.com/gorakhargosh/watchdog
- **MCP Protocol** : https://modelcontextprotocol.io/
- **Wrapper script** : `mcp-server-wrapper.sh`
- **Config exemple** : `claude_desktop_config_dev.json.example`

---

**Créé par** : Claude Code
**Dernière mise à jour** : 21 Février 2026
