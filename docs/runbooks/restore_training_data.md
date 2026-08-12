# Runbook — Restauration des données d'entraînement (Q2.5)

**Livrable Coach AI BT-025.** Ce runbook répond factuellement à la question Q2.5 de l'audit souveraineté :

> *Si Intervals.icu disparaît demain matin, que reste-t-il d'exploitable en local, et sur quelle profondeur d'historique ?*

Le runbook doit être **exécuté sur un environnement vierge**, pas sur la machine qui détient déjà les données. Un restore joué là où tout est déjà présent ne prouve rien.

---

## Conditions non négociables (spec Coach AI)

1. **Environnement vierge** : container Docker Ubuntu neuf (proxy NAS) ou machine utilisateur vierge (bundle beta-tester).
2. **Runbook exécuté sans connaissance implicite** : par un tiers, ou à la lettre par soi-même sans raccourci mental.
3. **Livrable = réponse chiffrée Q2.5** : un nombre concret de mois wellness restaurés + nombre d'activités streams restaurées. Pas un slogan, un chiffre mesuré.

---

## Prérequis

### Côté données

- Accès en lecture au repo git `stephanejouve/training-logs` (deploy key ou clone HTTPS avec token). Le repo est le **support de sauvegarde canonique**.
- Le repo doit être poussé à jour (sync auto 2×/jour côté NAS via daemon, ou push manuel côté bundle si BT-027 pas encore implémenté).

### Côté runtime

- Python 3.11+ (compatible bundle magma-cycling).
- Poetry OU `pip install magma-cycling` selon environnement.
- Aucune credentials Intervals.icu requis pour la restauration (on lit uniquement l'archive locale).

---

## Scénario A — Environnement Ubuntu vierge (proxy NAS prod)

### Étape 1 — Container vierge

```bash
docker run --rm -it -v $PWD:/work -w /work ubuntu:22.04 bash
apt-get update && apt-get install -y python3.11 python3-pip git
```

### Étape 2 — Clone du support de sauvegarde

```bash
git clone https://github.com/stephanejouve/training-logs.git /root/training-logs
export TRAINING_DATA_ROOT=/root/training-logs
```

### Étape 3 — Install magma-cycling (mode dev, ou wheel pré-buildée)

```bash
git clone https://github.com/stephanejouve/magma-cycling.git /root/magma-cycling
cd /root/magma-cycling
pip install poetry && poetry install --no-interaction
```

### Étape 4 — Mesure de couverture

```bash
poetry run python -c "
from magma_cycling.wellness import read_wellness_range
from magma_cycling.streams import load_manifest
from pathlib import Path

# Wellness
import os
wellness_dir = Path(os.environ['TRAINING_DATA_ROOT']) / 'data' / 'wellness'
files = sorted(wellness_dir.glob('*.json'))
if files:
    oldest = files[0].stem
    newest = files[-1].stem
    print(f'WELLNESS: {len(files)} jours archivés de {oldest} à {newest}')
else:
    print('WELLNESS: 0 jour (archive vide)')

# Streams
manifest = load_manifest()
activities = manifest.get('activities', {})
print(f'STREAMS: {len(activities)} activités archivées')
if activities:
    dates = sorted(a['start_date_local'] for a in activities.values())
    print(f'         période: {dates[0]} → {dates[-1]}')
"
```

### Étape 5 — Vérification d'intégrité (checksums)

```bash
poetry run python -c "
from magma_cycling.streams import load_manifest, verify_checksum
manifest = load_manifest()
activities = manifest.get('activities', {})
ok = sum(1 for aid in activities if verify_checksum(manifest, aid))
print(f'INTÉGRITÉ streams: {ok}/{len(activities)} checksums SHA-256 valides')
"
```

### Étape 6 — Test fonctionnel : CTL/ATL/TSB depuis cache

Simuler une panne Intervals via env var (ou juste vérifier que `read_wellness_range` retourne bien les données) :

```bash
poetry run python -c "
from magma_cycling.wellness import read_wellness_range
sample = read_wellness_range('2026-05-01', '2026-05-24')
if sample:
    latest = sample[-1]
    print(f'CTL={latest.get(\"ctl\"):.2f} ATL={latest.get(\"atl\"):.2f} TSB={latest.get(\"tsb\"):.2f} @ {latest[\"id\"]}')
else:
    print('AUCUNE DONNÉE wellness dans la fenêtre demandée')
"
```

**Attendu** : les CTL/ATL/TSB s'affichent sans erreur réseau. Le fallback read-through BT-023 sert exclusivement le cache local (aucun call Intervals nécessaire — on n'a d'ailleurs pas configuré de credentials).

---

## Scénario B — macOS user vierge (bundle beta-tester)

### Étape 1 — Machine utilisateur vierge

Une machine macOS sans aucune donnée `~/data/`, `~/training-logs/`, `~/Library/Application Support/magma-cycling/`.

### Étape 2 — Récupération de l'archive

Trois options selon la voie de distribution :

- **Voie git (préconisée si beta-tester a git installé)** : `git clone https://github.com/stephanejouve/training-logs.git ~/training-logs && export TRAINING_DATA_ROOT=$HOME/training-logs`.
- **Voie archive zip** : télécharger un snapshot `training-logs-YYYY-MM-DD.tar.gz` fourni par ops.
- **Voie sync symétrique** : non disponible (chantier BT-027 successor, pas encore implémenté). C'est le trou principal actuel côté beta.

### Étape 3 — Install bundle magma-cycling.app

Si le beta-tester a déjà le `.app` installé (voie nominale de distribution), le runtime Python et magma-cycling sont déjà présents. Sinon suivre le canal beta habituel.

### Étape 4 — Configurer TRAINING_DATA_ROOT dans le contexte du bundle

```bash
launchctl setenv TRAINING_DATA_ROOT $HOME/training-logs
```

Puis relancer le bundle depuis Finder pour prise en compte.

### Étape 5 — Mêmes commandes de mesure et vérification qu'en scénario A

(Adaptées : le CLI est via `/Applications/magma-cycling.app/Contents/Resources/…` ou une entrée menu bar dédiée si présente.)

---

## Scénario C — Windows user vierge (bundle beta-tester)

Symétrique du scénario B, avec adaptations :

- Path : `%USERPROFILE%\training-logs\` au lieu de `~/training-logs/`.
- Env var : `setx TRAINING_DATA_ROOT "%USERPROFILE%\training-logs"` (persistant) puis nouvelle console pour prise en compte.
- Bundle .exe magma-cycling installé via `magma-cycling.exe setup`.

Les mêmes commandes Python fonctionnent (le CI teste déjà `windows-latest`).

---

## Rapport chiffré actuel — état 2026-08-12

**Mesure effectuée sur poste dev Stéphane** (proxy raisonnable pour l'attendu Q2.5, à re-mesurer en Scénario A/B/C pour la validation formelle) :

| Métrique | Valeur mesurée |
|---|---|
| Wellness — jours archivés | **101 fichiers** JSON |
| Wellness — profondeur | 2026-02-13 → 2026-05-24 = **~3,3 mois** (100 jours pleins) |
| Streams — activités archivées | **0** (archive greenfield, à alimenter via `backfill-streams --since 2026-02-13 --to 2026-08-12`) |
| Streams — profondeur potentielle post-backfill | ~6 mois si backfill sur la même fenêtre que wellness |

### Réponse Q2.5 opérationnelle (à date)

> **Si Intervals disparaît demain matin** :
> - CTL/ATL/TSB restent **exploitables sur ~3,3 mois d'historique** via BT-023 wellness cache fallback (déjà en prod depuis v3.68.0, write-through observé).
> - Streams (watts/HR/cadence par activité) : **0 activité restaurable** aujourd'hui (BT-025 est le premier chantier qui met en place cette voie). Un backfill immédiat sur la même fenêtre wellness produirait ~6 mois de streams exploitables.

### Trou de couverture identifié

- **Sync symétrique training-logs 3 OS** : côté bundle beta-tester (macOS/Windows), aucun mécanisme automatique de push/pull du repo `training-logs`. Un beta-tester déconnecté perd sa souveraineté à moins de faire les git commands manuellement. **Chantier BT-027 successor** — à ouvrir si ce trou devient bloquant.

---

## Cadence de re-mesure recommandée

- Après chaque release majeure touchant `wellness` ou `streams` (validation régression du chiffre).
- Trimestriel en régime nominal (dérive du chiffre = signal d'un problème de sync).
- **Test réel** sur scénario A minimum 1×/an (juillet ou août, période creuse Coach AI).

## Rapporteur

Coach AI (spec BT-025 D3, conditions non négociables). Exécution + mesures Dev Leader (12/08/2026).
