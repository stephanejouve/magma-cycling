# Withings OAuth — Réauthentification Docker

## Pourquoi cette procédure ?

Le flow OAuth Withings redirige vers `http://localhost:8080/callback` après autorisation.
Ce callback est **inaccessible depuis un container Docker** (le `localhost` du container ≠ celui du Mac).

Conséquence : quand le token Withings expire (access + refresh), le MCP server NAS
ne peut plus récupérer les données sommeil/poids. Il faut réautoriser **localement sur le Mac**
puis copier les credentials vers le NAS.

## Prérequis

- `WITHINGS_CLIENT_ID` et `WITHINGS_CLIENT_SECRET` dans `~/training-logs/.env`
- Application enregistrée sur [developer.withings.com/dashboard](https://developer.withings.com/dashboard)
  avec Callback URL : `http://localhost:8080/callback`
- Port 8080 disponible sur le Mac
- Accès SSH au NAS (192.168.1.78)

## Procédure pas-à-pas

### 1. Réauth locale (Mac)

Le script interactif `poetry run setup-withings` utilise `input()` + `webbrowser.open()`.
Pour un flow non-interactif (ex. depuis Claude Code), utiliser le script temporaire :

```bash
# Depuis le repo magma-cycling
cat > /tmp/withings_reauth.py << 'PYEOF'
import sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from magma_cycling.config import create_withings_client, get_withings_config

auth_code = None
server_done = threading.Event()

class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass
    def do_GET(self):
        global auth_code
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>OK</h1><p>Fermez cet onglet.</p>")
            server_done.set()
        else:
            self.send_response(400)
            self.end_headers()
            server_done.set()

config = get_withings_config()
client = create_withings_client()
auth_url = client.get_authorization_url(state="reauth_docker")
print(f"\nOuvrez dans Safari :\n{auth_url}\n")
print("Attente callback localhost:8080 (5 min timeout)...")
sys.stdout.flush()

httpd = HTTPServer(("", 8080), CallbackHandler)
t = threading.Thread(target=lambda: [httpd.handle_request() for _ in iter(lambda: server_done.is_set(), True)], daemon=True)
t.start()
server_done.wait(timeout=300)
httpd.server_close()

if not auth_code:
    print("ERREUR: timeout"); sys.exit(1)
tokens = client.exchange_code(auth_code)
print(f"OK — credentials sauvegardees ({config.credentials_path})")
print(f"User ID: {tokens['user_id']}, authenticated: {client.is_authenticated()}")
PYEOF

poetry run python /tmp/withings_reauth.py
```

Ou directement avec le script interactif (si terminal disponible) :

```bash
poetry run setup-withings
```

### 2. Copier les credentials vers le NAS

Depuis la v3.4, les credentials Withings sont externalisées dans un volume dédié
(hors du data repo git) via `WITHINGS_CREDENTIALS_PATH`.

Le volume Docker monte `WITHINGS_CREDENTIALS_DIR` → `/data/credentials` (bind mount).
Copier le fichier dans le répertoire hôte du NAS :

```bash
scp ~/training-logs/.withings_credentials.json \
  stephanejouve@192.168.1.78:/volume1/magma/credentials/withings.json
```

> **Note** : configurer `WITHINGS_CREDENTIALS_DIR=/volume1/magma/credentials` dans
> `stack.env` sur le NAS (Portainer). La valeur par défaut est `./credentials`.

**Important — ownership UID** : le process `magma` dans le container tourne en UID 1000.
Le fichier copié via `scp` aura l'UID de l'utilisateur NAS (ex. 1028). Il faut corriger :

```bash
# Sur le NAS (SSH ou Portainer console)
docker exec magma-cycling-mcp-server-1 \
  chown 1000:1000 /data/credentials/withings.json
```

Ou directement côté hôte NAS si le mapping UID est connu.

Le fichier est ensuite visible dans le container sans redémarrage.
Cependant, **redémarrer Claude Desktop** est nécessaire pour ré-établir le handshake MCP.

### 3. Vérification

**Local (Mac)** :
```bash
poetry run python -c "
from magma_cycling.config import create_withings_client
c = create_withings_client()
print(f'Authenticated: {c.is_authenticated()}')
"
```

**NAS (via MCP)** : utiliser l'outil `withings-auth-status` depuis Claude Desktop.

**Fonctionnel** : l'outil `withings-get-sleep` doit retourner des données.

## Dépannage

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| `Invalid clientid` | App Withings suspendue/supprimée | Vérifier [dashboard Withings](https://developer.withings.com/dashboard), recréer si besoin |
| `Port 8080 already in use` | Processus résiduel | `lsof -ti:8080 \| xargs kill` |
| `Permission denied` (scp) | Pas de clé SSH configurée | Ajouter clé SSH ou utiliser mot de passe |
| Token re-expire rapidement | Refresh token aussi expiré | Refaire la procédure complète |
| `exists()=True` mais credentials invalides | Ownership UID : fichier owned par UID NAS (1028), process magma = UID 1000 | `docker exec ... chown 1000:1000 /data/training-logs/.withings_credentials.json` |
| MCP toujours en erreur après scp + chown | Handshake MCP stale | Redémarrer Claude Desktop |

## Backlog — Solutions conteneurisées

| Option | Description | Faisabilité |
|--------|-------------|-------------|
| **A — Route MCP** | Ajouter `/withings/callback` sur le MCP server (port 3000 déjà exposé côté NAS). Configurer `redirect_uri` Withings vers `http://192.168.1.78:3000/withings/callback` | Meilleure piste — nécessite ajout route HTTP + enregistrement redirect_uri sur dashboard Withings |
| **B — Reverse proxy** | Le reverse proxy NAS redirige le callback vers le container | Plus complexe, dépend de l'infra NAS (DSM) |
| **C — Device flow** | Authorization flow par code PIN (pas de redirect) | Non supporté par Withings actuellement |

L'option A est la plus prometteuse : le port 3000 est déjà exposé, il suffit d'ajouter
une route HTTP dans le MCP server FastAPI/Starlette pour gérer le callback OAuth.
