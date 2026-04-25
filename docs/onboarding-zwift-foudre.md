# Magma Cycling MCP — Référence des Outils

**Version** : v3.21 (avril 2026)
**Public** : Beta testeurs Zwift Foudre, utilisateurs Claude Desktop
**Total** : 60 outils répartis sur 11 domaines fonctionnels

---

## Avant-propos

Magma Cycling est un MCP server cross-platform (Windows installer, macOS bundle, container Docker pour les déploiements NAS preprod/prod) qui pont entre **Claude Desktop**, **Intervals.icu** (planning + analyse), **Withings** (sommeil + composition corporelle) et un système de **fichiers planning locaux** (`.md` hebdomadaires). Cette doc liste l'ensemble des outils exposés au LLM, leur fonction, et les workflows critiques qui les enchaînent.

⚠️ **Important** : Ces outils ne sont accessibles que depuis Claude Desktop avec MCP configuré. Les interfaces Claude.ai (web/mobile) n'y ont pas accès.

---

## 🗓️ Planning local (gestion des semaines)

Fichiers `.md` hebdo dans `training-data/planning/`. Source de vérité pour la planification.

| Outil | Fonction |
|---|---|
| `list-weeks` | Liste les semaines disponibles avec dates et infos basiques |
| `get-week-details` | Détails complets d'une semaine et de ses 7 sessions |
| `validate-week-consistency` | Vérifie cohérence (conflits, TSS, format) |
| `export-week-to-json` | Backup JSON de la semaine |
| `restore-week-from-backup` | Restaure depuis backup (confirmation requise) |
| `weekly-planner` | Génération IA du plan hebdo |

---

## 🏃 Sessions (CRUD planning)

Manipulation des séances individuelles à l'intérieur d'une semaine.

| Outil | Fonction |
|---|---|
| `create-session` | Crée une nouvelle séance |
| `update-session` | MAJ statut (completed, cancelled, skipped, replaced…) |
| `modify-session-details` | Modifie nom, type, description, TSS, durée |
| `rename-session` | Renomme un session_id (avec sync remote) |
| `delete-session` | Supprime du planning local |
| `duplicate-session` | Duplique vers une autre date |
| `swap-sessions` | Échange dates de 2 sessions (local + remote en 1 appel) |

⚠️ `swap-sessions` et `modify-session-details` sont **mutuellement exclusifs** sur une même opération de swap — ne jamais chaîner.

---

## 📅 Calendrier remote (Intervals.icu)

Synchronisation et manipulation directe des events sur Intervals.icu.

| Outil | Fonction |
|---|---|
| `list-remote-events` | Liste events remote sur une plage de dates |
| `sync-week-to-calendar` | Sync planning local → remote |
| `sync-remote-to-local` | Sync inverse (fix désynchro) |
| `update-remote-event` | MAJ directe d'un event remote |
| `delete-remote-event` | Suppression directe (permanente) d'un event |
| `create-remote-note` | Crée une NOTE calendrier (annulation, info…) |
| `validate-local-remote-sync` | Détecte décalages local ↔ remote |

📝 **Notes pratiques** :
- `sync-week-to-calendar` **protège** les sessions `completed` et `cancelled` (`skipped_protected`) — pour nettoyer un workout remote d'une session annulée, passer par `delete-remote-event` puis `create-remote-note`.
- Les descriptions doivent être **plain text dès le premier appel** : du markdown dans `modify-session-details` laisse des résidus persistants même avec `force_update: True`.
- `validate-local-remote-sync` retourne par défaut `include_description_check: false` — les `DESCRIPTION_MISMATCH LOW` sont du bruit attendu.
- Depuis v3.20.4 : les notes Intervals dont le titre contient un session ID (ex. analyses libres) ne déclenchent plus de `cancelled` local au prochain `sync-remote-to-local`. Seules les notes avec `[ANNULÉE]` / `[SAUTÉE]` font basculer la session locale.

---

## 💪 Workouts structurés

Gestion des fichiers workout (`.zwo`, `.mrc`, `.erg`) et adaptation terrain.

| Outil | Fonction |
|---|---|
| `list-workout-catalog` | Catalogue des workouts disponibles |
| `get-workout` | Récupère le contenu workout d'une session |
| `attach-workout` | Attache un fichier `.zwo`/`.mrc`/`.erg` à une session |
| `validate-workout` | Validation syntaxique avec auto-fix optionnel |
| `apply-workout-intervals` | Applique des bornes d'intervalles à une activité réalisée |
| `adapt-workout-to-terrain` | Adapte un workout structuré à un circuit terrain |
| `extract-terrain-circuit` | Extrait le profil terrain (segments, pentes, braquets) |
| `list-terrain-circuits` | Liste les circuits terrain sauvegardés |
| `evaluate-outdoor-execution` | Évalue exécution outdoor vs prescription terrain-adaptée |

📝 `structured_file: null` retourné par `get-workout` est **normal** (pas de `.zwo` généré pour cette session).

---

## 📊 Activités réalisées

Lecture et analyse des activités terminées.

| Outil | Fonction |
|---|---|
| `list-activities` | Liste activités sur plage de dates (TSS, puissance, FC, cadence) |
| `get-activity-details` | Détails complets (TSS, IF, courbes puissance, streams) |
| `get-activity-intervals` | Intervalles agrégés (laps : avg power, HR, cadence) |
| `get-activity-streams` | Streams temps-série bruts (slicing optionnel) |
| `compare-activity-intervals` | Compare intervalles entre plusieurs activités (progression) |
| `analyze-session-adherence` | Analyse adhérence prescription ↔ réalisé (TSS, IF, durée) |
| `backfill-activities` | Reconstruit l'historique des sessions vides (lien remote↔local) |

📝 `backfill-activities` est la méthode fiable pour reconstruire des semaines où `get-week-details` retourne des valeurs vides.

---

## 🏥 Santé (Withings + Intervals.icu wellness)

Données sommeil, composition corporelle, HRV et évaluation readiness.

| Outil | Fonction |
|---|---|
| `health-auth-status` | Statut OAuth provider santé |
| `health-authorize` | Lance ou complète le flow OAuth |
| `get-sleep` | Données sommeil détaillées |
| `get-hrv` | HRV nocturne (rMSSD) — Withings Sleep Analyzer ou wellness Intervals.icu |
| `get-body-composition` | Poids + composition corporelle |
| `get-readiness` | Évalue readiness (sommeil + santé combinés) |
| `analyze-health-trends` | Tendances santé sur une période |
| `enrich-session-health` | Injecte les métriques santé dans une session |
| `pre-session-check` | **Veto sécurité pré-séance** (sommeil + TSB + risque surentraînement) |
| `sync-health-to-calendar` | Sync santé → calendrier wellness Intervals.icu |

📝 **Bascule provider automatique** : si Withings n'est pas configuré, le système lit la wellness Intervals.icu (poids, sommeil, FC repos via `hr_min`, HRV via le champ `hrv`). Aucune config supplémentaire pour les utilisateurs Garmin/Apple Watch/etc. qui poussent déjà vers Intervals.icu.

⚠️ **Pattern Withings critique** :
- Withings tronque parfois le sommeil (fausses détections d'éveil, siestes non détectées, sommeil canapé non capté).
- Workflow correction : demander à l'athlète bedtime/wake réels → utiliser `extra_sleep_hours` dans `pre-session-check` (cap à 6.0h).
- ⚠️ La correction **ne se propage pas** à `enrich-session-health` ni `daily-sync` — patcher après coup avec `patch-coach-analysis(sleep_hours=…)`.

---

## 📈 Métriques athlète

Profil athlète et statistiques de charge.

| Outil | Fonction |
|---|---|
| `get-athlete-profile` | Profil complet (FTP, poids, FC max/repos, zones) |
| `update-athlete-profile` | MAJ du profil (FTP, poids, FC, etc.) |
| `get-metrics` | Métriques actuelles (CTL, ATL, TSB, FTP) |
| `get-training-statistics` | Statistiques agrégées sur une période (TSS, compliance, intensité) |

---

## 🤖 Analyse coach IA

Analyse intelligente, recommandations et historique des analyses passées.

| Outil | Fonction |
|---|---|
| `get-coach-analysis` | Récupère analyse IA passée (par activity_id, session_id, ou date) |
| `patch-coach-analysis` | Patch d'une analyse sans re-générer (append, préserve original) |
| `analyze-training-patterns` | **Méta-tool** : analyse globale (planning + activités + métriques) |
| `monthly-analysis` | Analyse mensuelle complète + insights IA |
| `get-recommendations` | Recommandations système PID & Peaks |

📝 `patch-coach-analysis` **ajoute** sans remplacer — toute correction est traçable.

---

## 🔄 Sync & maintenance

| Outil | Fonction |
|---|---|
| `daily-sync` | Sync activités du jour + MAJ statuts sessions |

📝 `daily-sync` avec `ai_analysis: False` est **requis** pour récupérer un `activity_id` avant `get-activity-details` ou `get-activity-intervals`.

---

## 💾 Contexte conversationnel

Persistance d'éléments non encore figés en planning.

| Outil | Fonction |
|---|---|
| `context-handoff-save` | Snapshot du contexte non-persisté (décisions en cours, hypothèses) |
| `context-handoff-resume` | Reprend le dernier snapshot non consommé |

---

## ⚙️ Système / dev

| Outil | Fonction |
|---|---|
| `system-info` | Providers actifs + métadonnées système |
| `reload-server` | [DEV] Reload des modules sans redémarrer Claude |

---

## 🎯 Workflows critiques

### Pré-séance standard

```
pre-session-check(date, week_id)         # veto sécurité
       ↓ (si GO)
enrich-session-health(session_id)        # injection métriques
```

⚠️ **Omettre `enrich-session-health` est une erreur** — la session restera sans contexte santé pour l'analyse post-séance.

### Post-séance standard

```
daily-sync(date, ai_analysis=False)      # récupère activity_id
       ↓
get-activity-details(activity_id)        # données brutes
       ↓
get-activity-intervals(activity_id)      # intervalles agrégés
       ↓
analyze-session-adherence(session_id)    # comparaison vs prescription
       ↓ (si correction Withings nécessaire)
patch-coach-analysis(session_id, sleep_hours=...)
```

### Annulation de séance

```
update-session(session_id, status=cancelled, reason=...)
       ↓ (si workout remote toujours présent)
delete-remote-event(event_id, confirm=True)
       ↓
create-remote-note(date, name="Sxxx-yy annulée", description=...)
```

📝 Le pipeline auto-nettoie parfois l'event remote lors du `update-session(cancelled)` — vérifier avec `list-remote-events` avant d'enchaîner.

### Swap de séances

```
swap-sessions(session_a, session_b, week_id)
       ↓
validate-local-remote-sync(week_id)      # confirme IN_SYNC
```

⚠️ **Ne jamais** chaîner `swap-sessions` + `modify-session-details` sur les mêmes sessions.

---

## 📐 Conventions et règles

### Nommage des sessions
Format : `Sxxx-yy[a-z]?`
- `Sxxx` = numéro de semaine (ex. `S090`)
- `yy` = jour ordinal (01 = lundi, 07 = dimanche)
- `[a-z]` = sous-séance optionnelle (ex. `S090-06a`, `S090-06b` pour 2 séances le même jour)

### Statuts de session

| Statut | Signification |
|---|---|
| `pending` | Planifiée, non statuée |
| `planned` | Validée, prête à exécuter |
| `uploaded` | Activité uploadée, statut intermédiaire |
| `completed` | Réalisée et analysée |
| `skipped` | Sautée (motif requis) |
| `cancelled` | Annulée (motif requis) |
| `rest_day` | Jour de repos |
| `replaced` | Remplacée par une autre séance |
| `modified` | Modifiée par rapport au plan initial |

### Types de session

| Code | Type |
|---|---|
| `END` | Endurance |
| `INT` | Intervalles / intensité |
| `REC` | Récupération |
| `RACE` | Course |

### Codes workout étendus (nommage `.zwo`)

Format : `SSSS-JJ-TYPE-NomExercice-VVVV.zwo`
Codes TYPE : `END`, `INT`, `FTP`, `SPR`, `CLM`, `REC`, `FOR`, `CAD`, `TEC`, `MIX`, `PDC`, `TST`

---

## 🔧 Bugs et limitations connus (v3.21)

| ID | Description | Priorité |
|---|---|---|
| **SYNC-001** | `remote_modification_detected` heuristique trop agressive (faux positifs depuis remote stale) | Haute |
| **VALID-001** | Gap validation sémantique type↔contenu dans `validate-local-remote-sync` | Basse |
| Withings | Fausse détection de fenêtres de sommeil (sleep canapé non détecté) | Moyenne |
| `sync-week-to-calendar` | Comportement non-déterministe sur l'auto-nettoyage des workouts remote lors d'un statut `cancelled` | À investiguer |

---

## 📚 Ressources externes

- **GitHub** : `stephanejouve/magma-cycling` (public)
- **Plateformes intégrées** : Intervals.icu, Withings Sleep Analyzer, Zwift, Wahoo ELEMNT ROAM V2
- **Dépendances** : Poetry pour la gestion Python
- **Pipelines indépendants** :
  - `poetry run end-of-week` (utilise Mistral API directement, hors Claude)
  - `poetry run withings-presync` (LaunchAgent macOS, sync wellness Withings → Intervals.icu)
  - `poetry run data-repo-sync` (LaunchAgent macOS + cron container NAS, push training-logs → GitHub)

---

*Référence générée le 25/04/2026 — Maintenue dans le repo `magma-cycling/docs/`*
