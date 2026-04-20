# ADR — Synchronisation training-logs (2026-04-20, v5)

**Statut** : Accepté sur le fond — PR Phase 1 portée par Leader dans `magma-cycling/docs/architecture/training-logs-sync.md`
**Contexte** : magma-cycling / infra data path
**Emplacement cible** : `magma-cycling/docs/architecture/training-logs-sync.md`
**Historique** :
- v1 — subdirs sémantiques → collisions temporelles
- v2 — subdirs opaques hash + `.operators.yaml`
- v3 — 4 amendements Leader (env var, `shared_root_files`, section 6 authority-per-file-type, timestamp UTC `Z`)
- v4 — section 7 **Upgrade path** pour déploiements existants (beta-testeurs), migration explicite via `setup_wizard`
- **v5 (ce document)** — 3 durcissements critiques Leader (msg 1139) : (a) Phase 1 ordonnancement révisé en 6 étapes avec **preflight obligatoire** pour récupérer les commits locaux non-pushed avant le flip filesystem, (b) déploiement **pull-rebase-push** positionné comme étape 1 (avant tout le reste), (c) **authority-per-file-type gated** derrière validation writer effectif (option 6.b : l'ADR documente la cible `nas-prod` pour `workouts-history.md` etc., mais le flip n'a lieu qu'après validation que le writer push réellement). Ajoute un risque résiduel + mitigation "writer avec commits orphelins au flip = perte silencieuse".

---

## 1. Contexte

Le repo `training-logs` est la source de données partagée par les LaunchAgents Mac (`stephanejouve` user) et le container NAS prod (`magma-cycling-cron-jobs-1`). Les deux écrivent dans des clones locaux de `origin/main` et font `git add -A && git commit && git push` sans pull préalable.

**Incidents observés** :
- Push container silencieusement rejetés en non-fast-forward depuis ~5 semaines (depuis la reprise des writes Mac). Les fichiers produits localement par le container (session-monitor, daily-sync, end-of-week) n'atteignent pas `origin/main`.
- Preprod (stack #39) a une data dir orpheline `/volume1/docker/magma-preprod/training-logs` non-cloner, jamais synchronisée. Claude Desktop connecté à preprod consomme des données potentiellement obsolètes.
- Symptôme caché : `weekly-reports/S088/*.md` du container n'ont été visibles qu'une fois (commit `c95e934` du 12/04), seule date où le clone NAS était aligné avec origin.

**Contraintes** :
- Deux environnements runtime très différents (Mac stephanejouve + NAS container) qui doivent écrire
- Preprod doit pouvoir lire des données fraîches sans pouvoir polluer prod
- Pas de push/pull bidirectionnel complexe entre preprod et prod (anti-pattern identifié)
- Migration incrémentale nécessaire (éviter du big-bang sur une infra en prod)

---

## 2. Options envisagées

### Option A — Single repo + pull-rebase-push côté container (proposée par Leader)

- Conserve la topologie actuelle : un repo `training-logs`, les deux writers partagent l'espace de chemins
- Ajouter `git pull --rebase origin main` avant commit dans `data_repo_sync.py` (container + admin-side)
- Preprod devient clone read-only avec pull `*/5` via cron container
- Alerting sur push rejected (Talk notif via nc-talk)

Pro : minimal, incrémental, pas de restructuration.
Con : writers se marchent potentiellement sur les mêmes chemins de fichiers ; ownership ambigu (qui a écrit `activities_tracking.json` aujourd'hui ?) ; la divergence reste invisible.

### Option B — Deux repos séparés (proposée initialement par Admin)

- `training-logs` (Mac only) + `training-logs-nas` (container only)
- Preprod read-only sur `training-logs` (Mac authoritative pour user-facing data)
- Pro : single-writer per repo, observabilité maximale via diff inter-repo, rollback isolé.
- Con : 2 remotes à maintenir (credentials, hooks, CI), clients multi-repo, dette de merge/sync si une vue "canonique" est requise.

### Option C — Single repo, subdirs opaques par operator (proposée par Stéphane)

- Un seul repo `training-logs`, structure interne : une subdir par writer, avec **nom opaque dérivé d'un hash** calculé une fois au provisioning :

  ```
  TRAINING_DATA_WRITER_ID = sha256("<timestamp_utc_iso8601_Z>#<writer_alias>")[:12]
  ```

  Exemple : `sha256("2026-04-20T08:00:00Z#nas-prod")[:12]` → `a3f7c1b2c4d5`
  Le dossier sur disque : `training-logs/a3f7c1b2c4d5/`

  **Format strict** : timestamp UTC ISO8601 avec suffixe `Z`, pas d'offset local, secondes sans fraction. Cela garantit que le hash est reproductible si un provisioning doit être rejoué (ex. restauration depuis backup), et que deux machines qui provisionnent au même instant génèrent le même ID pour le même alias si nécessaire.

- **Fichier d'index `.operators.yaml`** à la racine du repo (versionné), mappant hash → métadonnées lisibles + whitelist explicite des fichiers racine co-owned :

  ```yaml
  # .operators.yaml — répertoire des writers training-logs actifs et historiques
  #
  # Fichiers à la racine autorisés pour tous les writers (co-owned).
  # Tout autre write en racine est interdit (guard-rail côté DataRepoConfig).
  shared_root_files:
    - .gitignore
    - README.md
    - .operators.yaml          # auto-référentiel
    - docs/architecture/**     # ADRs (optionnel si le repo data héberge aussi des docs)

  # Writers actifs et décommissionnés (historique conservé pour rétro-compatibilité lecture).
  writers:
    a3f7c1b2c4d5:
      alias: nas-prod
      host: synology-penelope
      provisioned_at: 2026-04-20T08:00:00Z
      decommissioned_at: null
    9d4e2c117a8b:
      alias: nas-preprod
      host: synology-penelope
      provisioned_at: 2026-04-20T08:05:00Z
      decommissioned_at: null
    6b3fe892f01c:
      alias: mac
      host: tiresias
      provisioned_at: 2026-04-20T08:10:00Z
      decommissioned_at: null
  ```

- Subdir résolue via variable d'environnement `TRAINING_DATA_WRITER_ID`, set explicitement au provisioning. L'alias humain vit dans `.operators.yaml`, pas dans le path.
- Pull-rebase-push conservé (safety belt même si conflits fichiers quasi-nuls grâce à la séparation par subdir)
- Preprod = clone read-only pull-scheduled (comme A)

Pro :
- single repo, single remote (simplicité)
- writers disjoints par chemin (collisions quasi-impossibles)
- **unicité stable dans le temps** : décommissionner un operator puis en recréer un nouveau ne fusionne pas les deux historiques (hash différent par essence)
- **migration d'hôte transparente** : un MCP qui déménage (ex. Synology → QNAP cf. rescue-volume5) garde son ID, zéro renommage
- ownership explicite via `.operators.yaml` (parseable machine + lisible humain)
- observabilité divergence via diff sur fichiers homologues entre subdirs
- extensibilité triviale (nouveau writer = nouvelle entrée dans `.operators.yaml`, nouveau hash)

Con :
- refactoring des paths output dans les writers
- adaptation des consumers (email reports, MCP tools) pour résoudre multi-subdir
- migration des données existantes
- lisibilité filesystem moindre qu'un nom sémantique (mitigé par l'index `.operators.yaml` consultable en 1 grep)

**Variantes rejetées sur cette option** :
- Subdirs sémantiques pures (`mac/`, `nas-prod/`) : lisibles mais collision temporelle possible si un operator est décommissionné puis recréé avec le même alias
- Hybride `<alias>-<hash_short>` (ex. `nas-prod-a3f7/`) : compromis ergonomique mais double source de vérité (alias dans path ET dans `.operators.yaml`), donc dette de synchronisation

---

## 3. Décision recommandée : Option C avec migration incrémentale

### Phase 1 — Ordonnancement révisé en 6 étapes (durcissement v5)

L'ordre est **critique** : un flip filesystem prématuré sur un writer qui a des commits locaux non-pushed (cas observé sur NAS cron container, silent push-rejected depuis ~5 semaines) emporterait ces commits dans le nouveau layout sans qu'ils soient jamais visibles des autres writers = perte silencieuse. Les étapes ci-dessous préviennent ce scénario.

#### Étape 1 — Déployer `pull-rebase-push` sur **tous** les writers

Avant toute autre action, intégrer le fix `git pull --rebase origin main` avant commit dans `data_repo_sync.py` (module container + module admin-side) et vérifier que tous les writers l'utilisent. Cela garantit que les **prochains** writes réussissent et que les divergences futures sont résolues automatiquement.

PR idéalement dédiée, mergée et déployée sur les 3 writers avant de passer à l'étape 2.

#### Étape 2 — Preflight par writer (récupération des commits orphelins)

Pour chaque writer, **avant** le pivot filesystem :

```bash
git -C <clone> fetch origin
git -C <clone> rev-list @{u}..HEAD   # liste les commits locaux ahead d'origin
```

Si la liste est vide → writer clean, prêt pour le flip.

Si non-vide → diagnostic humain obligatoire. Pour chaque commit orphelin :
- Essayer `git pull --rebase origin main` pour intégrer proprement
- Si conflit ingérable : cherry-pick vers branche de sauvetage `writer/<alias>/pre-migration-backup`, push la branche, commit un résumé dans le rescue
- Ne PAS forcer un flip tant qu'un writer a encore des commits locaux non-résolus

Les commits orphelins du NAS cron container (identifiés en msg 1139 Leader) = à traiter explicitement ici. Probablement un `pull --rebase` simple réintègre tout, mais il faut vérifier avant le `git mv`.

#### Étape 3 — Générer les hash writer IDs + créer `.operators.yaml`

Pour les 3 writers actifs (Mac Stéphane, NAS prod, NAS preprod). Timestamp UTC strict avec `Z` :

```bash
printf '%s' "2026-04-20T08:00:00Z#nas-prod" | shasum -a 256 | cut -c1-12
```

Créer `.operators.yaml` à la racine du repo avec :
- `shared_root_files`: whitelist des fichiers racine autorisés
- `writers`: entrées (alias + host + timestamp UTC + decommissioned_at=null)
- `authority`: entrée initiale — **option 6.b retenue** : les authorities cibles sont déclarées (`nas-prod` pour `workouts-history.md`, `weekly-reports/**` ; `mac` pour `activities_tracking.json`, `data/week_planning/**`, `workouts/**`, etc.) MAIS leur activation effective côté consumer est **gated derrière la validation Étape 5** ci-dessous.

Commit unique initial sur origin.

#### Étape 4 — Pivot filesystem writer par writer

Ordre : **Mac d'abord, NAS ensuite**. Rationale : Mac est le writer dominant actif ; en pivotant Mac en premier, ses fichiers apparaissent à origin dans la nouvelle structure ; quand NAS pivote ensuite, il voit le nouveau layout et évite les conflits de `git mv`.

- Mac : `mkdir ~/training-logs/<hash_mac> && git mv <existants_hors_shared_root_files> <hash_mac>/`
- Container NAS prod : `mkdir <hash_nas_prod>/ && git mv <existants_hors_shared_root_files> <hash_nas_prod>/`

Puis modifier `.env` / `stack.env` :
- Mac : `TRAINING_DATA_REPO=/Users/stephanejouve/training-logs/<hash_mac>`
- NAS : `TRAINING_DATA_REPO=/data/training-logs/<hash_nas_prod>`

#### Étape 5 — Validation post-migration (test canari)

Pour chaque writer, après son pivot :

1. Créer un fichier canari `canary-<writer_alias>.txt` dans sa subdir avec le timestamp courant
2. Commit + push
3. Attendre 5 minutes, puis sur une autre machine (ou depuis origin GitHub UI) : vérifier que le canari est bien visible

**Si le canari d'un writer n'apparaît pas sur origin dans les 5 min** → le writer a un problème de push non-résolu (rebase fail, credential expirée, autre). **Ne pas passer à l'étape 6** tant que ce n'est pas résolu. Fixer d'abord, puis re-valider.

Si tous les canaris sont visibles : les 3 writers poussent effectivement, on peut passer à l'étape suivante.

#### Étape 6 — Flip des authorities (activation consumer-side)

Seulement après validation étape 5 passée pour tous les writers :
- Les consumers (Phase 3 PR D) peuvent commencer à utiliser `resolve_read_path()` pour résoudre via la section `authority` de `.operators.yaml`
- Le flip peut être graduel (consumer par consumer) ou big-bang selon préférence team

Si un writer pushe effectivement mais un autre encore pas, on peut ne flipper que les authorities du writer validé (ex. `mac` OK → flip les authorities `mac` seulement ; `nas-prod` pas encore validé → authorities `nas-prod` restent pointant vers `mac` temporairement dans `.operators.yaml`).

---

À l'issue des 6 étapes : tous les writers continuent de fonctionner, chacun dans sa subdir dédiée, zéro commit orphelin perdu, authorities flipped seulement après validation de chaque writer.

### Phase 2 — Abstraction code (ultérieure, PR dédiée)

1. Introduire `TRAINING_DATA_WRITER_ID` comme env var séparée (contient le hash 12-char)
2. Refactorer `magma_cycling.config.data_repo.DataRepoConfig` pour résoudre `TRAINING_DATA_ROOT + TRAINING_DATA_WRITER_ID` + lire `.operators.yaml` pour métadonnées (logs, diagnostics)
3. Migration des `.env` / `stack.env` : séparer à nouveau `TRAINING_DATA_REPO` (racine) de `TRAINING_DATA_WRITER_ID` (subdir hash)
4. Ajouter helper `provision-writer <alias>` qui :
   - Calcule `timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')` (format strict UTC avec `Z`)
   - Génère `hash = sha256(f"{timestamp}#{alias}").hexdigest()[:12]`
   - Ajoute l'entrée sous `writers:` dans `.operators.yaml`
   - Crée la subdir sur disque
   - Commit + push sur origin
5. Renaming `TRAINING_DATA_REPO` → `TRAINING_DATA_ROOT` dans `config.py` pour refléter la nouvelle sémantique (racine commune, pas le path applicatif)
6. **Guard-rails** dans `DataRepoConfig` :
   - fatal si `TRAINING_DATA_WRITER_ID` manquant en runtime prod (évite pollution racine)
   - refuse tout write en dehors de `TRAINING_DATA_ROOT/<writer_id>/` sauf si le path appartient à `shared_root_files` (whitelist chargée depuis `.operators.yaml`)

### Phase 3 — Consumers (PR suivante)

Résolution des reads selon la stratégie **authority-per-file-type** définie en **Section 6 — Consumer resolution strategy**. Chaque consumer (email reports, MCP tools, Claude Desktop) consulte la section `authority` de `.operators.yaml` pour déterminer la subdir à lire pour chaque pattern de fichier. Pas de multi-read + dédoublonnage — une seule source canonique par type de fichier, déclarative et versionnée.

### Fixes transverses retenus (repris de A)

- `pull --rebase origin main` ajouté avant commit dans `data_repo_sync.py` (même si conflit quasi-nul en C, reste une safety belt contre toute divergence imprévue)
- Alerting Talk sur push rejected (via nc-talk room `infra-alerts` ou `admin-leader`)
- Preprod = clone read-only avec `git pull --ff-only */5` via cron sidecar

---

## 4. Conséquences

### Bénéfices attendus
- Fin des 5 semaines de silent push-rejected : chaque writer pushe dans sa zone disjointe
- Ownership explicite via `.operators.yaml` (parseable + humain)
- **Unicité stable dans le temps** : décommission + recréation d'un operator = nouvelle identité, historique préservé sans fusion accidentelle
- **Migration d'hôte transparente** : changement de host physique (Synology → QNAP par ex.) conserve l'ID, zéro refactor de paths
- Divergence observable : diff sur fichiers homologues entre subdirs = diagnostic d'écart applicatif (via lookup `.operators.yaml` pour donner du sens au diff)
- Preprod Claude Desktop dispose toujours de données fraîches sans risque de pollution inverse
- Migration Phase 1 sans ligne de code changée

### Coûts assumés
- Refactor filesystem (move + commit) par writer + provisioning script pour générer hash
- Consumers (reports, tools) doivent résoudre multi-subdir → PR follow-up (Phase 3)
- Historique Git existant doit être assigné à un operator par défaut (décidé : operator Mac, puisque Mac est le writer dominant actuel et détient les writes user-facing)
- Lisibilité filesystem moindre qu'un nom sémantique (mitigé par consultation `.operators.yaml` en 1 grep)
- Complexité légèrement supérieure qu'A pour un nouveau contributeur (mais documentée ici + via l'index)

### Risques résiduels
- Si un writer oublie de set son `TRAINING_DATA_WRITER_ID` → écrit à la racine → pollue structure. **Mitigation** : guard-rail dans `DataRepoConfig` qui fatal si env var manquante en runtime prod (Phase 2) + refuse tout write hors subdir sauf whitelist `shared_root_files`.
- Fichiers racine co-owned : résolu explicitement par la liste `shared_root_files` dans `.operators.yaml` (chargée par `DataRepoConfig` comme whitelist de paths autorisés hors subdir). Tout autre write en racine est refusé par le guard-rail.
- Si `.operators.yaml` est perdu/corrompu : mapping hash → alias + whitelist disparaissent. Mitigation : le fichier est versionné git (récup via `git log`), et un sanity-check peut être ajouté au démarrage des writers (fatal si `.operators.yaml` absent ou malformé).
- Collision de hash : probabilité négligeable sur 12 hex chars (2^48 valeurs, collision attendue à ~16M provisioning) — acceptable. Incrémenter à 16 chars si paranoïa future.
- Si l'`authority` déclarée dans `.operators.yaml` (Section 6) ne correspond pas à ce que les writers produisent réellement, certains fichiers resteront "invisibles" aux consumers. **Mitigation** : linter CI qui scanne les subdirs et warn si des paths hors authority sont détectés (Phase 3).
- **Writer avec commits locaux non-pushed au moment du flip filesystem** (scénario observé sur NAS cron container, silent push-rejected cumulé depuis ~5 semaines) : si l'étape 4 `git mv` est exécutée avant résolution de ces commits orphelins, ils sont emportés dans la nouvelle structure sans jamais être visibles par les autres writers — **perte silencieuse**. **Mitigation** : étape 2 preflight obligatoire de la Phase 1 révisée (check `git rev-list @{u}..HEAD` par writer, résolution humaine explicite via rebase ou branche de sauvetage avant de passer à l'étape 4).
- **Flip d'authority prématuré sur un writer non-fonctionnel** : si on flip les consumers vers `nas-prod` alors que le push NAS est toujours cassé, les consumers liront un état figé/divergent. **Mitigation** : gating Étape 5 (test canari par writer) avant toute activation consumer-side (Étape 6). L'authority `nas-prod` dans `.operators.yaml` peut être déclarée sans être consommée tant que la validation canari n'est pas passée.

---

## 5. Alternatives rejetées

- **Option B (deux repos)** : trop lourd en infra pour la valeur ajoutée vs C, qui offre la même observabilité sans la charge opérationnelle.
- **Symlinks preprod → prod** : anti-pattern identifié (partage d'état, defeat le but d'isolation preprod).
- **Fork bidir training-logs-preprod** : dette de merge perpétuelle, risque de reverse-sync, rejeté.
- **Subdirs sémantiques pures** (`mac/`, `nas-prod/`) : lisibles mais pas stables dans le temps (recréation d'operator avec même alias fusionne l'historique) ; rejeté au profit des hash opaques + index `.operators.yaml`.
- **Subdirs hybrides** (`<alias>-<hash>/`) : double source de vérité (alias dans path ET dans index), dette de synchronisation ; rejeté au profit du full-hash + index séparé.
- **Consumer = lecture Mac-only (container observer-only)** : simpliste mais annule l'utilité des writes container (weekly-reports NAS jamais consommés) ; rejeté au profit d'authority-per-file-type qui permet à chaque writer d'avoir des domaines de responsabilité actifs.
- **Consumer = multi-read + dédoublonnage par date** : ambigu sur les conflits (quel fichier gagne si timestamps proches ?), dette de code non-triviale, non-déclaratif ; rejeté au profit de l'authority explicite dans `.operators.yaml`.

### Alternatives rejetées — upgrade path chez beta-testeurs

- **Migration automatique au premier run post-upgrade** : risque de corruption si push rejected ou conflit git pendant migration silencieuse. Une structure cassée en prod chez un beta-tester = incident coûteux en support. Rejeté au profit d'une migration explicite déclenchée par erreur fatale et commande utilisateur.
- **Fallback lecture multi-source (racine + subdirs)** pendant la fenêtre de transition : dette de code permanente, ambiguïté sur le writer canonique, complexifie la section 6 (authority + fallback = deux sources de vérité). Rejeté au profit d'une migration franche one-shot.

---

## 6. Consumer resolution strategy — authority-per-file-type

### Principe

Chaque type de fichier dans le repo a **un seul writer autoritatif** déclaré dans `.operators.yaml`. Les consumers lisent le fichier depuis la subdir de cet operator, point. Pas de merge, pas de dédoublonnage, pas de heuristique temporelle.

### Déclaration dans `.operators.yaml`

```yaml
# .operators.yaml (extrait — suite de la section writers + shared_root_files)
authority:
  # Fichiers user-facing gérés par les LaunchAgents Mac
  activities_tracking.json:          mac
  data/activities_tracking.json:     mac
  workouts/**:                       mac      # .zwo files créés manuellement
  data/week_planning/**:             mac      # planning user-edited
  data/backups/**:                   mac      # backups user-triggered

  # Fichiers générés par les crons container NAS (cible — gated, cf. Étape 6 Phase 1)
  weekly-reports/**:                 nas-prod # bilans end-of-week server-side
  workouts-history.md:               nas-prod # historique auto-agrégé

  # Fichiers explicitement co-owned (dernier writer gagne — risque assumé)
  # Aucun à ce jour ; si nécessaire, ajouter sous `authority` avec valeur liste : [mac, nas-prod]
```

Les valeurs côté droit sont les **alias** des writers (pas les hashes), résolus via la section `writers` de `.operators.yaml`. Cela rend la config lisible ; le hash est résolu transparent par le loader.

### Gating de l'authority (option 6.b — durcissement v5)

L'authority déclarée ci-dessus est la **cible architecturale** (principe de responsabilité : c'est au server-side de produire et d'agréger `workouts-history.md` et `weekly-reports/**`, puisqu'il a une vue complète des activités côté container). Mais tant qu'un writer n'a pas été **validé** comme effectivement fonctionnel via le canari Étape 5 de la Phase 1, les consumers ne doivent pas pointer vers lui.

Mécanisme concret :
- L'entrée `authority:` dans `.operators.yaml` reste en état-cible dès Phase 1 Étape 3 (pour que l'ADR reflète le principe architectural)
- **MAIS** l'activation côté consumer (Phase 1 Étape 6 + Phase 3 PR D) peut désactiver des authorities individuellement : ex. tant que le push NAS n'est pas validé, les consumers fallback sur un writer réputé fonctionnel (typiquement `mac`) pour les paths normalement autorités à `nas-prod`
- Une fois validation NAS réussie : flip dans un commit atomique qui active les authorities `nas-prod` côté consumer

Cela évite de figer un état cassé où `workouts-history.md` serait lu depuis une subdir NAS figée depuis 5 semaines alors que Mac produit la version vivante à l'origin.

### Résolution côté consumer

Un helper central (Phase 3) :
```python
def resolve_read_path(file_pattern: str) -> Path:
    authority = load_operators_yaml().authority
    writer_alias = authority.match(file_pattern)
    writer_hash = resolve_alias_to_hash(writer_alias)
    return TRAINING_DATA_ROOT / writer_hash / file_pattern
```

Tous les consumers (email reports, MCP tools, Claude Desktop context loaders, data analytics ad-hoc) appellent ce helper. Zéro logique multi-read.

### Règles d'évolution

- **Ajout d'un nouveau type de fichier** : déclarer l'authority dans `.operators.yaml` en même temps que le code qui le produit (règle CI-enforceable via linter).
- **Changement d'authority** (ex. migration d'un type de fichier du container Mac) : commit qui met à jour `.operators.yaml` + `git mv` des fichiers existants de l'ancienne vers la nouvelle subdir, dans un commit atomique.
- **Fichier produit par plusieurs writers malgré l'authority** : détecté par le linter Phase 3 qui scanne les subdirs et warn sur les paths non-authorités.

### Cas edge : fichier introuvable dans l'authority déclarée

Si le consumer demande un path qui devrait être dans `mac/` mais le fichier n'y est pas :
- Log warning explicite (pas fatal — les données peuvent être partiellement disponibles)
- Retour `FileNotFoundError` au caller, qui décide de la stratégie (fail loud, skip, fallback)
- Pas de fallback automatique sur une autre subdir (évite les silencieuses lectures croisées qu'on cherche à éliminer)

---

## 7. Upgrade path — déploiements existants

### 7.1. Problème

Chaque déploiement client (Georges aujourd'hui, autres beta-testeurs à venir) a son propre clone local de `training-logs` avec tout l'historique à la racine du repo (structure legacy pré-Phase 1). Une fois la Phase 2 déployée côté code, `DataRepoConfig` cherche les données dans `<TRAINING_DATA_WRITER_ID>/` qui n'existe pas chez eux → leur historique reste orphelin, invisible pour les consumers.

Notre Phase 1 (Section 3) décrit la migration manuelle des **3 writers que nous contrôlons directement** (Mac Stéphane, NAS prod, NAS preprod). Ce mode manuel n'est pas applicable aux déploiements clients : impossible d'aller faire `git mv` à la main chez chaque beta-tester.

### 7.2. Contraintes

- **Zéro perte de données** : l'historique training-logs d'un beta-tester contient son planning, ses workouts, ses rapports EOW — intangibles.
- **Zéro migration silencieuse** : une migration qui se lance seule au premier run pose un risque de corruption partielle en cas d'échec (push rejected, conflit git imprévu, mauvaise détection de writer local). Un dépôt à moitié migré = incident coûteux en support client.
- **Action utilisateur explicite** : le beta-tester doit être informé, exécuter une commande consciente, voir les logs de migration, pouvoir rollback.

### 7.3. Stratégie retenue — migration explicite via `setup_wizard`

**Détection legacy au démarrage** (implémentée en Phase 2 dans `DataRepoConfig`) :

Si `.operators.yaml` est absent à la racine du repo **ET** si des fichiers sont présents à la racine hors `shared_root_files` (indice d'un layout flat legacy), `DataRepoConfig` lève une `FatalConfigError` au démarrage du code :

```
Training logs repo detected in legacy layout (flat structure).
Run: poetry run setup --migrate-training-logs
See: docs/architecture/training-logs-sync.md#upgrade-path
```

Pas de démarrage silencieux, pas de migration automatique. Le code refuse explicitement de tourner avant migration.

**Script `migrate-training-logs`** (entry point intégré à `setup_wizard`, invocation `poetry run setup --migrate-training-logs`) :

1. Détecte le repo legacy (présence de fichiers à la racine hors whitelist, absence de `.operators.yaml`).
2. Invite interactivement l'utilisateur à choisir un **alias** pour son writer local (default = hostname ou `local`).
3. Appelle le helper `provision-writer <alias>` (Phase 2) :
   - Timestamp UTC strict avec `Z` : `datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')`
   - Hash 12-char : `sha256(f"{timestamp}#{alias}").hexdigest()[:12]`
   - Ajoute l'entrée sous `writers:` dans `.operators.yaml` (crée le fichier si absent, avec la section `shared_root_files` par défaut + la section `authority` par défaut — tous les fichiers pointant vers l'alias de ce writer).
4. Génère/initialise `.operators.yaml` si absent.
5. `git mv` de tous les fichiers hors whitelist vers `<hash>/`.
6. Met à jour `.env` avec `TRAINING_DATA_ROOT=<chemin_repo>` et `TRAINING_DATA_WRITER_ID=<hash>`.
7. Commit atomique : `[migrate] training-logs: flat → writer <alias>/<hash>`.
8. Push avec retry/backoff (réutilise la logique pull-rebase-push de Phase 2). Alerte claire si push échoue (rare : conflit possible si plusieurs clients tentent migration simultanée).

### 7.4. Cas particulier — beta-tester multi-writers

Un beta-tester peut avoir plusieurs environnements writers (ex. Mac + MCP NAS personnel), rare mais possible. Le script tourne alors une fois par environnement : chaque instance provisionne son propre writer distinct. La section `authority` de `.operators.yaml` doit ensuite être éditée manuellement par le beta-tester pour assigner les différents types de fichiers aux bons writers, ou laissée au défaut (tous pointant vers son alias principal) avec migration ultérieure à la granularité plus fine.

### 7.5. Rollback

La migration est committée en un seul commit atomique. En cas de problème immédiat (push qui refuse, incohérence détectée) :
- `git reset --hard HEAD~1` ramène l'état pré-migration côté working tree.
- Restauration du `.env` précédent (`TRAINING_DATA_REPO` sans subdir).
- Signalement remonté (Talk alert via nc-talk ou simple log).

Une fois le push accepté sur origin, le rollback devient plus coûteux (il faudrait revert le commit côté remote — opération destructive possible mais traçable).

### 7.6. Communication beta-testeurs

Release notes explicites sur le release qui introduit Phase 2 :

> Cette version introduit une nouvelle structure du repo `training-logs` (subdirs par writer, cf. ADR `training-logs-sync`). Au premier lancement après upgrade, un message d'erreur vous invitera à lancer :
>
> `poetry run setup --migrate-training-logs`
>
> Ce script migre votre historique existant vers la nouvelle structure en un commit git atomique. **Rollback possible** dans les 24h si le push n'a pas encore été répliqué sur origin. Aucune donnée n'est perdue — l'historique est préservé intégralement sous votre writer local.

---

## 8. Décision

**Accepté sur le fond** — Leader porte la PR Phase 1 dans `magma-cycling/docs/architecture/training-logs-sync.md` dès que v4 est signalée prête.

Séquencement des PRs (non-bloquantes les unes par rapport aux autres, sauf dépendance naturelle) :

1. **PR A — Phase 1 & ADR** : filesystem migration pour nos 3 writers (Mac Stéphane / NAS prod / NAS preprod) + création `.operators.yaml` initial (avec `shared_root_files` + `writers` + `authority` par défaut) + pull-rebase-push dans `data_repo_sync.py` + ADR committé. Scope Leader.
2. **PR B — Alerting push-rejected** : Talk notif via nc-talk quand `data-repo-sync` échoue en non-ff. Scope Leader ou Junior (outillages).
3. **PR C — Phase 2 code** : env var `TRAINING_DATA_WRITER_ID` + refacto `DataRepoConfig` + helper `provision-writer <alias>` + guard-rails (fatal si env var manquante, whitelist write racine). Scope Junior.
4. **PR D — Phase 3 consumers** : helper `resolve_read_path` lisant l'`authority`, adaptation des consumers (email reports, MCP tools), linter authority-coherence. Scope Junior.
5. **PR E — Upgrade path** (dépend de PR C) : détection legacy + `setup --migrate-training-logs` + release notes beta. Scope Junior.

Une fois PR A mergée : la chaîne de sync prod est stabilisée (fin des silent push-rejected). Les autres PRs améliorent l'infra sans urgence.
