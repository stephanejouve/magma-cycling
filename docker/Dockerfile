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
# build. Restaure l'entry point `data-repo-sync` invoqué par supercronic au
# tick 22:30 (cron quotidien) et 20:30 (dimanche), KO depuis le commit
# 8e01f8d (extraction des tools vers outillages sans mise à jour du Dockerfile).
RUN pip install --no-cache-dir \
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
