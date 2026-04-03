#!/bin/sh
set -e

# -----------------------------------------------------------------------
# Verification des variables d'environnement critiques
# -----------------------------------------------------------------------
MISSING=""

for VAR in INTERVALS_API_KEY INTERVALS_ATHLETE_ID TRAINING_LOGS_PATH; do
    eval VALUE=\$$VAR
    if [ -z "$VALUE" ]; then
        MISSING="$MISSING $VAR"
    fi
done

if [ -n "$MISSING" ]; then
    echo "[entrypoint] ERREUR : variables manquantes :$MISSING" >&2
    exit 1
fi

# -----------------------------------------------------------------------
# Config git pour le data repo (push planning, reports, etc.)
# -----------------------------------------------------------------------
if [ -n "$GIT_USER_NAME" ]; then
    git config --global user.name "$GIT_USER_NAME"
fi

if [ -n "$GIT_USER_EMAIL" ]; then
    git config --global user.email "$GIT_USER_EMAIL"
fi

if [ -n "$GIT_TOKEN" ]; then
    git config --global credential.helper \
        '!f() { echo "username='"$GIT_USER_NAME"'"; echo "password='"$GIT_TOKEN"'"; }; f'
fi

if [ -d "$TRAINING_LOGS_PATH" ]; then
    git config --global --add safe.directory "$TRAINING_LOGS_PATH"
fi

# -----------------------------------------------------------------------
# Lancement de la commande
# -----------------------------------------------------------------------
echo "[entrypoint] Demarrage : $@"
exec "$@"
