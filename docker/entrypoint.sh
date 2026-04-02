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
# Config git si data repo present
# -----------------------------------------------------------------------
if [ -d "$TRAINING_LOGS_PATH/.git" ]; then
    echo "[entrypoint] Data repo git detecte dans $TRAINING_LOGS_PATH"
fi

# -----------------------------------------------------------------------
# Lancement de la commande
# -----------------------------------------------------------------------
echo "[entrypoint] Demarrage : $@"
exec "$@"
