# Magma Cycling MCP — Référence des outils

**Public** : Beta-testeurs, utilisateurs Claude Desktop
**Plateformes** : Windows, macOS

---

## Avant-propos

Magma Cycling expose à Claude Desktop un ensemble d'outils qui te permettent, en langage naturel, de planifier ton entraînement, lire tes activités réalisées, suivre tes données santé et obtenir des analyses coach. Cette doc liste les outils par domaine, leur usage côté utilisateur, et les workflows fréquents.

⚠️ Ces outils ne sont accessibles que depuis Claude Desktop avec MCP configuré. Les interfaces Claude.ai (web/mobile) n'y ont pas accès.

---

## 🗓️ Planning de la semaine

Gérer les semaines d'entraînement et leurs séances.

| Outil | Ce qu'il fait |
|---|---|
| `list-weeks` | Liste les semaines disponibles |
| `get-week-details` | Détails d'une semaine et de ses séances |
| `validate-week-consistency` | Vérifie que la semaine est cohérente |
| `export-week-to-json` | Sauvegarde la semaine en JSON |
| `restore-week-from-backup` | Restaure une sauvegarde |
| `weekly-planner` | Génère un plan hebdomadaire |

---

## 🏃 Séances

Créer, modifier et organiser tes séances dans une semaine.

| Outil | Ce qu'il fait |
|---|---|
| `create-session` | Crée une nouvelle séance |
| `update-session` | Met à jour le statut (réalisée, annulée, sautée…) |
| `modify-session-details` | Modifie nom, type, description, TSS, durée |
| `rename-session` | Renomme une séance |
| `delete-session` | Supprime une séance |
| `duplicate-session` | Duplique vers une autre date |
| `swap-sessions` | Échange les dates de deux séances |

---

## 📅 Calendrier Intervals.icu

Synchroniser ton planning avec ton calendrier Intervals.icu.

| Outil | Ce qu'il fait |
|---|---|
| `list-remote-events` | Liste tes événements Intervals sur une période |
| `sync-week-to-calendar` | Pousse une semaine de planning sur Intervals |
| `sync-remote-to-local` | Récupère depuis Intervals vers le planning local |
| `update-remote-event` | Modifie un événement Intervals |
| `delete-remote-event` | Supprime un événement Intervals |
| `create-remote-note` | Crée une note (annulation, info) sur Intervals |
| `validate-local-remote-sync` | Vérifie que local et Intervals sont alignés |

📝 **Astuce** : préfère du texte simple (sans markdown) dans les descriptions de séances — certains rendus Intervals laissent du formatage parasite sinon.

---

## 💪 Workouts structurés

Gérer les fichiers de workout (`.zwo`, `.mrc`, `.erg`) et adapter à ton parcours.

| Outil | Ce qu'il fait |
|---|---|
| `list-workout-catalog` | Liste les workouts disponibles |
| `get-workout` | Récupère le contenu d'une séance |
| `attach-workout` | Attache un workout à une séance |
| `validate-workout` | Vérifie que le fichier est correct |
| `apply-workout-intervals` | Applique des bornes d'intervalles à une activité |
| `adapt-workout-to-terrain` | Adapte un workout à un parcours réel |
| `extract-terrain-circuit` | Extrait le profil d'un parcours |
| `list-terrain-circuits` | Liste les parcours sauvegardés |
| `evaluate-outdoor-execution` | Compare ton exécution outdoor à la prescription |

---

## 📊 Activités réalisées

Lire et analyser tes séances terminées.

| Outil | Ce qu'il fait |
|---|---|
| `list-activities` | Liste tes activités sur une période |
| `get-activity-details` | Détails complets d'une activité (TSS, IF, courbes) |
| `get-activity-intervals` | Intervalles agrégés (laps, puissance, FC) |
| `get-activity-streams` | Données temps-série brutes |
| `compare-activity-intervals` | Compare plusieurs activités |
| `analyze-session-adherence` | Compare prescription vs réalisé |
| `backfill-activities` | Recharge des séances anciennes manquantes |

---

## 🏥 Santé

Sommeil, poids, HRV, et évaluation de ta forme du jour.

| Outil | Ce qu'il fait |
|---|---|
| `health-auth-status` | Statut de connexion à ton fournisseur santé |
| `health-authorize` | Connecte ton compte santé |
| `get-sleep` | Tes données de sommeil |
| `get-hrv` | Ta variabilité cardiaque (rMSSD) |
| `get-body-composition` | Poids et composition corporelle |
| `get-readiness` | Évalue si tu es en forme pour t'entraîner |
| `analyze-health-trends` | Tendances santé sur une période |
| `enrich-session-health` | Ajoute tes métriques santé à une séance |
| `pre-session-check` | **Veto sécurité avant séance** (sommeil + forme + risque) |
| `sync-health-to-calendar` | Pousse tes données santé sur Intervals |

📝 **Astuce sommeil** : si ton tracker a mal détecté la nuit (siestes ratées, sommeil canapé non capté), tu peux dire à Claude « j'ai dormi X heures » et il ajustera l'évaluation.

---

## 📈 Profil et métriques

| Outil | Ce qu'il fait |
|---|---|
| `get-athlete-profile` | Ton profil (FTP, poids, FC max/repos, zones) |
| `update-athlete-profile` | Met à jour ton profil |
| `get-metrics` | Tes métriques actuelles (CTL, ATL, TSB) |
| `get-training-statistics` | Statistiques agrégées (TSS, compliance, intensité) |

---

## 🤖 Analyses coach IA

| Outil | Ce qu'il fait |
|---|---|
| `get-coach-analysis` | Récupère une analyse passée |
| `patch-coach-analysis` | Ajoute des notes à une analyse existante |
| `analyze-training-patterns` | Analyse globale (planning + activités + métriques) |
| `monthly-analysis` | Analyse mensuelle complète |
| `get-recommendations` | Recommandations d'entraînement |

📝 `patch-coach-analysis` ne remplace jamais ton analyse — elle ajoute des éléments traçables.

---

## 🔄 Sync quotidienne

| Outil | Ce qu'il fait |
|---|---|
| `daily-sync` | Synchronise tes activités du jour et met à jour les statuts |

---

## 💾 Mémoire de conversation

| Outil | Ce qu'il fait |
|---|---|
| `context-handoff-save` | Sauvegarde le contexte (décisions en cours, hypothèses) avant fin de session |
| `context-handoff-resume` | Reprend le dernier contexte sauvegardé |

---

## ⚙️ Système

| Outil | Ce qu'il fait |
|---|---|
| `system-info` | État du système et des connexions |
| `reload-server` | [Dev] Recharge sans redémarrer Claude |

---

## 🎯 Workflows usuels

### Avant une séance

1. Demande à Claude un **pré-check** de la journée — il évalue ta forme à partir de ton sommeil et de ta charge récente.
2. Si feu vert : il enrichit ta séance avec tes métriques santé du jour.

### Après une séance

1. Lance la **sync du jour** pour récupérer ton activité Intervals.
2. Demande l'**analyse d'adhérence** : Claude compare ta séance prescrite à ce que tu as réalisé.
3. Si tu vois quelque chose à corriger (sommeil mal capté, contexte inhabituel), dis-le-lui — il patche l'analyse en conséquence.

### Annuler une séance

Dis simplement à Claude « annule la séance Sxxx-yy parce que [raison] ». Il met à jour le statut local + nettoie le calendrier Intervals si l'événement y est encore.

### Échanger deux séances

« Échange ma séance de mardi avec celle de jeudi » — Claude swappe les dates côté local et côté Intervals en une opération.

---

## 📚 Comment ça marche

Magma Cycling se branche entre Claude Desktop, ton compte Intervals.icu et ton tracker santé (Withings, ou alimentation par ta montre via Intervals). Toutes les données restent sous ton contrôle.

- **GitHub** : `stephanejouve/magma-cycling`
- **Plateformes connectées** : Intervals.icu, Withings, Zwift, Wahoo

---

*Doc maintenue dans `docs/` du repo magma-cycling.*
