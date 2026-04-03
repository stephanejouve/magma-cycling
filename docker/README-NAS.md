# Deploiement magma-cycling sur NAS via Portainer

## Pre-requis

- NAS avec Docker installe (Synology, QNAP, etc.)
- Portainer accessible via l'interface web du NAS
- Donnees athlete (training-logs) hebergees ou elles le souhaitent (voir ci-dessous)

## Separation application / donnees athlete

L'application magma-cycling et les donnees personnelles de l'athlete sont
volontairement separees. L'athlete choisit ou heberger ses donnees :

```
NAS (exemple)
├── /volume1/docker/magma-cycling/    ← application (stack Portainer)
└── /volume1/athlete-data/
    └── training-logs/                ← donnees athlete (repo git)
```

Le chemin vers les donnees est configure via la variable `TRAINING_DATA_PATH`.
Cela permet a chaque athlete de :
- Heberger ses donnees sur le meme NAS, un autre volume, ou un stockage distant
- Garder le controle total sur ses donnees personnelles
- Chiffrer le volume de donnees independamment de l'application

## 1. Preparer les donnees athlete

Cloner le data repo sur le NAS a l'emplacement de votre choix :

```bash
mkdir -p /volume1/athlete-data
cd /volume1/athlete-data
git clone https://github.com/<user>/<training-logs-repo>.git training-logs
```

## 2. Deployer via Portainer Stacks

1. Ouvrir Portainer → **Stacks** → **Add stack**
2. Nommer le stack : `magma-cycling`
3. Copier-coller le contenu de `docker-compose.yml`
4. Dans **Environment variables**, cliquer **Advanced mode** et coller
   les variables depuis `env.example` (remplir les secrets)
5. S'assurer que `TRAINING_DATA_PATH` pointe vers le bon chemin :
   ```
   TRAINING_DATA_PATH=/volume1/athlete-data/training-logs
   ```
6. Cliquer **Deploy the stack**

## 3. Verifier

### MCP Server

```bash
# Depuis le NAS ou le reseau local
curl http://<nas-ip>:3000/health
```

Le serveur MCP est accessible en SSE sur `http://<nas-ip>:3000/sse`.

### Cron Jobs

Dans Portainer → **Containers** → `cron-jobs` → **Logs** :
les taches periodiques s'affichent au fil de leur execution.

| Tache | Schedule | Description |
|-------|----------|-------------|
| session-monitor | Toutes les 20min, 6h-23h | Surveillance des seances |
| daily-sync | 21h30 | Sync quotidienne + email + analyse AI |
| check-workout-adherence | 22h00 | Verification adherence entrainement |
| pid-daily-evaluation | 23h00 | Evaluation PID quotidienne |
| end-of-week | Dimanche 20h00 | Bilan hebdomadaire automatique |
| project-clean | 03h00 | Nettoyage fichiers temporaires |

## 4. Configurer Claude Desktop

Dans la config MCP de Claude Desktop, ajouter le serveur distant :

```json
{
  "mcpServers": {
    "magma-cycling": {
      "url": "http://<nas-ip>:3000/sse"
    }
  }
}
```

## 5. Mise a jour

Quand une nouvelle version est poussee sur `ghcr.io` :

1. Portainer → **Stacks** → `magma-cycling`
2. Cliquer **Pull and redeploy**
3. Les containers sont recrees avec la nouvelle image

## Architecture

```
NAS
├── Portainer (UI web)
│   └── Stack magma-cycling
│       ├── mcp-server      (daemon permanent, port 3000)
│       └── cron-jobs        (supercronic, 6 taches periodiques)
│
├── /volume1/docker/magma-cycling/   ← application
│
└── /volume1/athlete-data/           ← donnees personnelles (chemin libre)
    └── training-logs/                (data repo git)
```

## Securite

- Les secrets (cles API, tokens) sont dans les env vars Portainer, jamais dans l'image
- Les donnees athlete sont separees de l'application
- Le volume de donnees peut etre chiffre independamment
- Les echanges MCP ne sont pas chiffres par defaut — pour une exposition
  au-dela du reseau local, prevoir un tunnel VPN ou reverse proxy HTTPS

## Notes

- L'image Docker est buildee par GitHub Actions et poussee sur `ghcr.io/stephanejouve/magma-cycling`
- Multi-arch : compatible x86_64 (DS918+, DS920+) et ARM64 (DS220+, DS223)
- Logs sur stdout/stderr — captures nativement par Portainer
- Le data repo fait des git push : le token Git doit etre configure dans les env vars
