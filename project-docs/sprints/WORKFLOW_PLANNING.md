# Workflow Planning Hebdomadaire (Corrigé)

**Date de correction :** 30 décembre 2025
**Problème résolu :** JSON planning non créé automatiquement

---

## 📋 Workflow Complet

### 1. Génération Planning (wp)

```bash
wp --week-id S075 --start-date 2026-01-05
```

**Ce qui se passe maintenant :**
- ✅ Collecte métriques actuelles (CTL/ATL/TSB)
- ✅ Charge bilan semaine précédente (S074)
- ✅ Génère prompt pour Claude
- ✅ **Crée automatiquement `week_planning_S075.json`** (NOUVEAU !)
- ✅ Copie prompt dans presse-papier

**Fichier créé :**
```
~/training-logs/data/week_planning/week_planning_S075.json
```

**Contenu JSON :**
```json
{
  "week_id": "S075",
  "start_date": "2026-01-05",
  "end_date": "2026-01-11",
  "created_at": "2026-01-05T10:00:00",
  "last_updated": "2026-01-05T10:00:00",
  "version": 1,
  "athlete_id": "i151223",
  "tss_target": 0,  // Sera mis à jour après upload
  "planned_sessions": [
    {
      "session_id": "S075-01",
      "date": "2026-01-05",
      "name": "Session1",
      "type": "END",
      "version": "V001",
      "tss_planned": 0,
      "duration_min": 0,
      "description": "À définir",
      "status": "planned"
    },
    // ... 7 séances au total
  ]
}
```

---

### 2. Génération Workouts (via Claude)

**Option A : Manuel (workflow actuel)**
```bash
# Le prompt est dans le presse-papier
# 1. Aller sur Claude.ai
# 2. Coller le prompt (Cmd+V)
# 3. Récupérer les 7 workouts générés
# 4. Uploader avec wu
wu --week-id S075 --start-date 2026-01-05
```

**Option B : Automatique (nouveau)**
```bash
# Utiliser le script d'auto-génération
python3 scripts/auto_generate_planning.py --week S075 --start-date 2026-01-05
# → Génère via API Claude + Upload + Met à jour JSON automatiquement
```

---

### 3. Mise à Jour Statuts Séances

#### Annuler une séance

```bash
python3 cyclisme_training_logs/update_session_status.py \
  --week S075 \
  --session S075-01 \
  --status cancelled \
  --reason "Contrainte extra-sportive"
```

**Résultat :**
```json
{
  "session_id": "S075-01",
  "status": "cancelled",
  "cancellation_reason": "Contrainte extra-sportive",
  "cancellation_date": "2026-01-05T14:30:00"
}
```

#### Marquer comme complétée

```bash
python3 cyclisme_training_logs/update_session_status.py \
  --week S075 \
  --session S075-02 \
  --status completed
```

#### Autres statuts possibles

```bash
# Séance sautée
--status skipped --reason "Fatigue excessive"

# Séance remplacée
--status replaced --reason "Remplacée par sortie longue route"

# Séance modifiée
--status modified --reason "Durée réduite à 45min au lieu de 60min"

# Jour de repos
--status rest_day --reason "Protocole repos hebdomadaire"
```

---

### 4. Réconciliation (trainr)

```bash
trainr --week-id S074
```

**Ce qui fonctionne maintenant :**
- ✅ Compare `week_planning_S074.json` (planifié)
- ✅ vs activités Intervals.icu (réalisé)
- ✅ Identifie écarts (séances manquées, TSS différents)
- ✅ Propose ajustements pour semaine suivante

**Output exemple :**
```
📊 Réconciliation S074
Planifié : 347 TSS (7 séances)
Réalisé  : 210 TSS (4 séances)
Écart    : -137 TSS (-39.5%)

Séances annulées :
  - S074-01 : Contrainte extra-sportive
  - S074-02 : Contrainte extra-sportive

Recommandations pour S075 :
  - Option 1 : Intensifier endurance longue (+22 TSS)
  - Option 2 : Remplacer repos par séance légère (+45 TSS)
  - Option 3 : Accepter déficit et rattraper progressivement
```

---

### 5. Servo-Mode (trains)

```bash
trains --week-id S074
```

**Ajustements dynamiques :**
- Analyse état forme post-séance (CTL/ATL/TSB, RPE)
- Compare avec planning JSON
- Propose modifications séances restantes
- Met à jour JSON automatiquement

---

## 🔧 Commandes Utiles

### Voir le planning JSON

```bash
cat ~/training-logs/data/week_planning/week_planning_S074.json
```

### Lister tous les plannings

```bash
ls -lh ~/training-logs/data/week_planning/
```

### Vérifier statut des séances

```bash
jq '.planned_sessions[] | {id: .session_id, status: .status}' \
  ~/training-logs/data/week_planning/week_planning_S074.json
```

### Compter séances par statut

```bash
jq '.planned_sessions | group_by(.status) | map({status: .[0].status, count: length})' \
  ~/training-logs/data/week_planning/week_planning_S074.json
```

---

## 📁 Structure Fichiers

```
~/training-logs/
├── data/
│   └── week_planning/
│       ├── week_planning_S073.json  ✅ Existant
│       ├── week_planning_S074.json  ✅ Créé automatiquement maintenant
│       └── week_planning_S075.json  ✅ Sera créé par wp
└── weekly-reports/
    ├── S073/
    │   ├── bilan_final_s073.md
    │   └── ...
    └── S074/
        ├── analyse_impact_annulations.md
        └── ...
```

---

## 🆕 Nouveautés vs Ancien Workflow

### AVANT (Problème)

```
wp S074
  → Génère prompt
  → Copie dans presse-papier
  → ❌ AUCUN JSON créé
  → ❌ Réconciliation impossible
  → ❌ Pas de trace des annulations
```

### APRÈS (Corrigé)

```
wp S074
  → Génère prompt
  → ✅ Crée week_planning_S074.json automatiquement
  → Copie dans presse-papier

Annulation :
  update_session_status.py --week S074 --session S074-01 --status cancelled
  → ✅ JSON mis à jour avec raison + timestamp

Réconciliation :
  trainr --week-id S074
  → ✅ Compare JSON vs Intervals.icu
  → ✅ Analyse écarts et propose ajustements
```

---

## ✅ Checklist Workflow Complet

- [ ] **Lundi matin** : `wa --week-id S073` (analyse semaine passée)
- [ ] **Lundi matin** : `wp --week-id S074` (planning semaine courante)
  - ✅ JSON créé automatiquement
- [ ] **Si annulation** : `update_session_status.py` pour chaque séance annulée
- [ ] **Pendant la semaine** : `trains --week-id S074` (servo-mode pour ajustements)
- [ ] **Dimanche soir** : `trainr --week-id S074` (réconciliation finale)
- [ ] **Recommencer** pour S075

---

## 🐛 Dépannage

### JSON non créé

```bash
# Vérifier que le répertoire existe
ls -la ~/training-logs/data/week_planning/

# Créer manuellement si besoin
mkdir -p ~/training-logs/data/week_planning/

# Relancer wp
wp --week-id S075 --start-date 2026-01-05
```

### Erreur update_session_status

```bash
# Vérifier que le JSON existe
cat ~/training-logs/data/week_planning/week_planning_S074.json

# Si non trouvé, le créer d'abord avec wp
wp --week-id S074 --start-date 2025-12-29
```

### Session ID invalide

```bash
# Lister tous les IDs de séances
jq '.planned_sessions[].session_id' \
  ~/training-logs/data/week_planning/week_planning_S074.json
```

---

## 📚 Références

- **Code source** : `cyclisme_training_logs/weekly_planner.py`
- **Helper script** : `cyclisme_training_logs/update_session_status.py`
- **Validations** : `cyclisme_training_logs/rest_and_cancellations.py`
- **Config** : `cyclisme_training_logs/config.py` (get_data_config)

---

**Dernière mise à jour :** 30 décembre 2025
**Commit de correction :** 4bc97e3
