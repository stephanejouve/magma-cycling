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

## 🌐 Méthode 3 : HTTP/SSE Transport (Recommandé pour Dev)

### Vue d'ensemble

Le transport HTTP/SSE résout le problème fondamental du stdio : **la reconnexion automatique**.

**Avantages vs Watchdog + stdio:**
- ✅ Claude Desktop reconnecte **automatiquement** (pas besoin de restart)
- ✅ Serveur peut redémarrer sans casser la connexion
- ✅ Watchdog fonctionne parfaitement avec HTTP
- ✅ Logs plus clairs (voir le serveur démarrer/arrêter)
- ✅ Debug plus facile (possibilité de tester avec curl)
- ✅ Compatible multi-client (plusieurs Claude Desktop peuvent se connecter)

### Configuration

**1. Activer HTTP dans `.env`:**

```bash
# Transport mode: "stdio" (default) or "http"
MCP_TRANSPORT=http
MCP_HTTP_HOST=localhost
MCP_HTTP_PORT=3000
MCP_DEV_MODE=1
```

**2. Claude Desktop config:**

```json
{
  "mcpServers": {
    "cyclisme-training": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

Exemple complet : voir `claude_desktop_config_http.json.example`

**3. Démarrer le serveur:**

Option A - **Manuel** (contrôle total):
```bash
poetry run mcp-server
# [MCP] Starting HTTP/SSE server on localhost:3000
```

Option B - **Automatique avec watchdog** (recommandé):
```json
{
  "mcpServers": {
    "cyclisme-training": {
      "command": "/path/to/mcp-server-wrapper.sh",
      "env": {
        "MCP_DEV_MODE": "1",
        "MCP_TRANSPORT": "http",
        "MCP_HTTP_HOST": "localhost",
        "MCP_HTTP_PORT": "3000"
      }
    }
  }
}
```

### Fonctionnement

**Architecture HTTP/SSE:**
- Serveur HTTP écoute sur `localhost:3000` (Uvicorn/Starlette)
- **GET `/sse`** → Établit connexion Server-Sent Events (stream persistant)
- **POST `/messages/`** → Reçoit les requêtes JSON-RPC du client
- Claude Desktop maintient une connexion SSE ouverte pour recevoir les réponses

**Flow de reconnexion automatique:**
1. Watchdog détecte changement dans `*.py`
2. Watchdog tue et redémarre le processus Python
3. Serveur HTTP redémarre sur le même port
4. Claude Desktop détecte la déconnexion
5. Claude Desktop reconnecte automatiquement à `/sse`
6. ✅ **Pas besoin de relancer Claude Desktop**

### Test manuel

**Vérifier que le serveur HTTP répond:**
```bash
# Test connexion SSE
curl http://localhost:3000/sse

# Devrait retourner un stream SSE (Ctrl+C pour quitter)
# Format: event: endpoint\ndata: {...}\n\n
```

**Vérifier l'endpoint messages:**
```bash
# Test POST endpoint (nécessite session_id valide)
curl -X POST http://localhost:3000/messages/
```

### Logs

**Démarrage du serveur:**
```
[MCP] Starting HTTP/SSE server on localhost:3000
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:3000 (Press CTRL+C to quit)
```

**Watchdog redémarre le serveur:**
```
[watchmedo] Restarting server on change: cyclisme_training_logs/mcp_server.py
[MCP] Starting HTTP/SSE server on localhost:3000
INFO:     Started server process [12346]
...
```

Claude Desktop affiche brièvement "Reconnecting..." puis se connecte automatiquement.

---

## 📊 Comparaison

| Aspect | HTTP/SSE + Watchdog | Stdio + Watchdog | reload-server |
|--------|---------------------|------------------|---------------|
| **Activation** | Automatique sur fichier modifié | Automatique sur fichier modifié | Manuel via MCP tool |
| **Reconnexion** | 🚧 **En développement** (incompatibilité mcp-remote) | ❌ Nécessite restart Claude | N/A |
| **Handlers MCP** | 🚧 Rechargés (si proxy compatible) | ✅ Rechargés | ❌ Non rechargés |
| **Tool definitions** | 🚧 Rechargés (si proxy compatible) | ✅ Rechargés | ❌ Non rechargés |
| **Modules métier** | ✅ Rechargés | ✅ Rechargés | ✅ Rechargés |
| **Stabilité** | 🚧 À valider | ✅ Stable et éprouvé | ✅ Stable |
| **Debug** | 🔧 Logs + curl/browser | 🔧 Via logs seulement | 🔧 Via logs |
| **Overhead** | Très faible | Minimal | Minimal |
| **Production** | ⚠️ Dev uniquement | ✅ **Recommandé** | ✅ OK |
| **Délai** | ~1-2s (théorique) | ✅ **~3-5s** (validé) | Instantané |
| **Statut** | 🚧 En développement | ✅ **Production ready** | ✅ Stable |

---

## 🎯 Cas d'usage

### HTTP/SSE + Watchdog (⭐ Recommandé pour Dev)
- ✅ **Développement intensif** avec modifications très fréquentes
- ✅ Modification des handlers MCP, tools, et tout le code
- ✅ **Zéro restart Claude Desktop** pendant le dev
- ✅ Changements structurels
- ✅ Expérience dev optimale (cycle test < 5s)
- ⚠️ Dev uniquement (pas production)

### Stdio + Watchdog (Production)
- ✅ Mode production (stable, minimal overhead)
- ✅ Intégration Claude Desktop standard
- ✅ Pas de port HTTP exposé
- ⚠️ Nécessite restart Claude Desktop après chaque changement (dev pénible)

### reload-server (Fallback)
- ✅ Petit fix dans un module métier sans changer handlers
- ✅ Mode production avec MCP_DEV_MODE=0
- ✅ Debug ponctuel sans relancer Claude Desktop
- ⚠️ Limité (ne recharge pas handlers ni tools)

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

### HTTP/SSE : Claude Desktop ne se connecte pas

**Cause** : Serveur HTTP pas démarré ou mauvais port

**Solution** :
```bash
# Vérifier si serveur écoute sur le port
lsof -ti:3000 || echo "Port 3000 libre (serveur pas démarré)"

# Vérifier les logs serveur
tail -f /tmp/mcp-server-debug.log

# Tester la connexion manuellement
curl http://localhost:3000/sse
```

### HTTP/SSE : Port déjà utilisé

**Erreur** : `[Errno 48] address already in use`

**Solution** :
```bash
# Trouver et tuer le processus sur le port
lsof -ti:3000 | xargs kill -9

# Ou utiliser un autre port dans .env
MCP_HTTP_PORT=3001
```

### HTTP/SSE : Reconnexion lente après restart

**Cause** : Délai de retry SSE côté client

**Normal** : Claude Desktop attend 2-5s avant de reconnecter (comportement SSE standard)

**Solution** : Aucune action nécessaire, c'est le comportement attendu

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

**Solution** : Utiliser HTTP/SSE + watchdog pour hot reload complet

---

## 📚 Références

- **Watchdog documentation** : https://github.com/gorakhargosh/watchdog
- **MCP Protocol** : https://modelcontextprotocol.io/
- **Wrapper script** : `mcp-server-wrapper.sh`
- **Config exemple** : `claude_desktop_config_dev.json.example`

---

## 🔬 Statut HTTP/SSE (Février 2026)

### Résultats de tests

**✅ Ce qui fonctionne:**
- Transport HTTP/SSE implémenté (`mcp-http-transport` v0.1.0)
- Endpoint SSE `/sse` retourne session_id correctement
- Endpoint POST `/messages/` accepte requêtes (HTTP 202)
- Package publié sur PyPI

**❌ Incompatibilité actuelle:**
- `mcp-remote` (proxy Node.js officiel) : erreurs SSE headers
- Version Node.js v20.5.1 insuffisante (requis: v20.18.1+)
- Nécessite debugging approfondi du protocole SSE

**🎯 Recommandation actuelle (Février 2026):**

**Pour développement immédiat:** Utiliser **stdio + watchdog**
- ✅ Fonctionne 100%
- ✅ Cycle dev: 3-5 secondes (très acceptable)
- ⚠️ Nécessite restart Claude Desktop après modifications

**Pour la communauté:**
- Package `mcp-http-transport` disponible sur PyPI
- Package `mcp-stdio-proxy` (Python) en développement comme alternative à `mcp-remote`
- Contributions bienvenues pour fix compatibilité SSE

### Packages publiés

1. **mcp-http-transport** (PyPI)
   - Transport HTTP/SSE pour serveurs MCP
   - `pip install mcp-http-transport`
   - GitHub: https://github.com/stephanejouve/mcp-http-transport

2. **mcp-stdio-proxy** (en développement)
   - Proxy Python stdio ↔ HTTP/SSE
   - Alternative pure Python à `mcp-remote`
   - À venir sur PyPI

---

**Créé par** : Claude Code
**Dernière mise à jour** : 22 Février 2026 (tests HTTP/SSE, stdio+watchdog validé)
