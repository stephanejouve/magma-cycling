# Deploiement Docker — magma-cycling (NAS)

Conteneurisation de magma-cycling pour deploiement sur NAS Synology (ou tout hote Docker).

## Architecture

| Service | Role | Mode |
|---------|------|------|
| `mcp-server` | Serveur MCP pour Claude Desktop (SSE/HTTP) | Daemon permanent |
| `cron-jobs` | Taches periodiques (6 CLI via supercronic) | Daemon permanent |

## Pre-requis

- Docker + Docker Compose
- Fichier `.env` a la racine du projet avec les secrets (voir section ci-dessous)
- Repertoire `training-logs/` (data repo git)

## Configuration (.env)

```env
# Intervals.icu
INTERVALS_API_KEY=xxx
INTERVALS_ATHLETE_ID=i151223

# AI providers
MISTRAL_API_KEY=xxx

# Email (Brevo)
BREVO_API_KEY=xxx

# MCP transport
MCP_TRANSPORT=http
MCP_HTTP_HOST=0.0.0.0
MCP_HTTP_PORT=3000

# Data paths
TRAINING_LOGS_PATH=/data/training-logs
```

## Lancement

```bash
cd docker/

# Build + demarrage
docker compose build
docker compose up -d

# Verifier les logs
docker compose logs -f mcp-server
docker compose logs -f cron-jobs

# Test MCP server
curl http://localhost:3000/sse
```

## Arret

```bash
docker compose down
```

## Volumes

| Bind mount | Container path | Usage |
|-----------|----------------|-------|
| `training-logs/` | `/data/training-logs` | Data repo (planning, reports, tracking) |
| `.env` | via `env_file` | Secrets (jamais dans l'image) |

## Taches cron

| Tache | Schedule | Priorite |
|-------|----------|----------|
| session-monitor | Toutes les 20min, 6h-23h | Haute |
| daily-sync | 21h30 | Haute |
| check-workout-adherence | 22h00 | Moyenne |
| pid-daily-evaluation | 23h00 | Moyenne |
| end-of-week | Dimanche 20h00 | Haute |
| project-clean | 03h00 | Basse |

## Image Docker Hub

```bash
# Push
docker compose build
docker compose push

# Pull depuis un autre hote
docker pull stephanejouve/magma-cycling:latest
```

## Notes

- Base `python:3.12-slim` : compatible ARM64 (Synology DS920+) et x86
- Pas de Poetry dans l'image finale (poetry export → pip install)
- Git installe dans le container pour les push du data repo
- Healthcheck integre sur le MCP server (curl /sse toutes les 30s)
- Logs sur stdout/stderr (captures par Docker nativement)
