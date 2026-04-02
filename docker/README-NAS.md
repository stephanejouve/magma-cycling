# Deploiement magma-cycling sur NAS via Portainer

## Pre-requis

- NAS avec Docker installe (Synology, QNAP, etc.)
- Portainer accessible via l'interface web du NAS
- Repertoire de donnees cree sur le NAS : `/volume1/docker/magma/training-logs`

## 1. Preparer l'environnement

Creer le fichier `.env` sur le NAS (ex: `/volume1/docker/magma/.env`) a partir de `env.example`.
Remplir les secrets : cles API, token Git, etc.

## 2. Deployer via Portainer Stacks

1. Ouvrir Portainer → **Stacks** → **Add stack**
2. Nommer le stack : `magma-cycling`
3. Copier-coller le contenu de `docker-compose.yml`
4. Dans **Environment variables**, charger le fichier `.env` ou saisir les variables
5. Cliquer **Deploy the stack**

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
│       ├── mcp-server     (daemon permanent, port 3000)
│       └── cron-jobs       (supercronic, 6 taches periodiques)
├── /volume1/docker/magma/
│   ├── .env                (secrets, jamais dans l'image)
│   └── training-logs/      (data repo git)
```

## Notes

- L'image Docker est buildee par GitHub Actions et poussee sur `ghcr.io/stephanejouve/magma-cycling`
- Multi-arch : compatible x86_64 (DS918+, DS920+) et ARM64 (DS220+, DS223)
- Logs sur stdout/stderr — captures nativement par Portainer
- Le data repo fait des git push : le token Git doit etre configure dans `.env`
