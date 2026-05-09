# syntax=docker/dockerfile:1.4
# Directive `syntax` requise pour `RUN --mount=type=secret` utilisé plus bas
# (BuildKit feature). Avec ça, le deploy key SSH outillages est monté tmpfs
# au build de l'étape pip install — jamais dans une layer image.

# =============================================================================
# Stage 1 : builder — export requirements via Poetry
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir poetry poetry-plugin-export \
    && poetry export -f requirements.txt -o requirements.txt --without-hashes

# =============================================================================
# Stage 2 : runtime — image legere sans Poetry
# =============================================================================
FROM python:3.12-slim

# Deps systeme : git (push data repo) + curl (healthcheck) +
# openssh-client (SSH deploy key pour git push vers training-logs, cf. bascule
# HTTPS→SSH du 18/04 suite expiration PAT — ephemere auparavant, pérennisé ici)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Supercronic (cron leger pour Docker) — multi-arch via TARGETARCH
ARG SUPERCRONIC_VERSION=v0.2.33
ARG TARGETARCH
RUN ARCH=$(case ${TARGETARCH} in arm64) echo "linux-arm64" ;; *) echo "linux-amd64" ;; esac) \
    && curl -fsSL "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-${ARCH}" \
       -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

WORKDIR /app

# Deps Python
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY magma_cycling/ magma_cycling/
COPY scripts/ scripts/

# Installer le package (entry points CLI)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

# Installer magma-cycling-tools (source of truth pour data_repo_sync et futurs
# adapters/ops, spin-off d'outillages). Repo public → pas d'auth nécessaire au
# build de magma-cycling-tools lui-même. Restaure l'entry point `data-repo-sync`
# invoqué par supercronic au tick 22:30 (cron quotidien) et 20:30 (dimanche),
# KO depuis le commit 8e01f8d (extraction des tools vers outillages sans mise
# à jour du Dockerfile).
#
# **Auth SSH outillages requise depuis magma-cycling-tools v0.2.0** :
# magma-cycling-tools v0.2.0 déclare `outillages` (repo PRIVÉ) comme dep
# transitive pour le safety net alerting Talk dans `data_repo_sync.py::_alert_talk()`.
# Sans la clé SSH, pip échouait silencieusement à résoudre cette dep, et le
# runtime container attrapait l'ImportError → bug 13 jours d'alertes infra-alerts
# muettes en prod. Cf. ADR v5 prérequis Étape 1 + msg admin id=2203 sur
# 1:1 admin-leader + PR magma-cycling-tools #1.
#
# Pattern Option 2 (validé Admin 2026-05-09) : BuildKit secret mount, key tmpfs
# disponible uniquement pendant le RUN, jamais dans une layer image. Le secret
# `outillages_deploy_key` est passé par le caller (GitHub Actions
# build-push-action ou `docker build --secret` en local).
RUN --mount=type=secret,id=outillages_deploy_key,target=/run/secrets/key \
    mkdir -p /root/.ssh && \
    ssh-keyscan -t ed25519 github.com >> /root/.ssh/known_hosts && \
    GIT_SSH_COMMAND="ssh -i /run/secrets/key -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes" \
    pip install --no-cache-dir \
        git+https://github.com/stephanejouve/magma-cycling-tools.git@main

# Crontab + entrypoint
COPY docker/crontab /app/crontab
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# User non-root
RUN useradd -m magma \
    && chown -R magma:magma /app
USER magma

# Env par defaut
ENV MCP_TRANSPORT=http \
    MCP_HTTP_HOST=0.0.0.0 \
    MCP_HTTP_PORT=3000

EXPOSE 3000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["mcp-server"]
