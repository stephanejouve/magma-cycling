# Protocole VETO - Protection Surmenage Athlète Master

**Version:** 1.0
**Date:** 2026-01-01
**Cible:** Athlètes master (50+ ans), athlète principal Stéphane (54 ans)
**Priorité:** P0 (CRITIQUE - Sécurité athlète)

---

## 🎯 Objectif

Le protocole VETO protège les athlètes master contre le surmenage en **annulant automatiquement** les séances haute intensité quand les indicateurs de fatigue dépassent des seuils critiques.

**Principe:** Mieux vaut annuler 1 séance que risquer 2-3 semaines de surmenage.

---

## ⚠️ Quand le VETO s'Active

### Seuils CRITIQUES (Athlète Master 54 ans)

Le VETO s'active **automatiquement** si **UN OU PLUSIEURS** critères sont atteints:

| Critère | Seuil VETO | Signification |
|---------|------------|---------------|
| **TSB** | < -25 | Fatigue critique (forme très négative) |
| **ATL/CTL** | > 1.8 | Surcharge aiguë (fatigue >> forme) |
| **Sommeil** | < 5.5h | Récupération insuffisante (critique) |
| **Sommeil + TSB** | < 6h ET < -15 | Stress combiné (profil sleep-dependent) |

### Exemples VETO

**Cas 1: TSB Critique**
```
CTL: 65  |  ATL: 95  |  TSB: -30
Sommeil: 7h
→ VETO: TSB < -25 (fatigue critique)
```

**Cas 2: Surcharge Aiguë**
```
CTL: 50  |  ATL: 95  |  TSB: -45
Ratio ATL/CTL: 1.9 (> 1.8)
→ VETO: Surcharge aiguë critique
```

**Cas 3: Sommeil Insuffisant**
```
CTL: 65  |  ATL: 70  |  TSB: -5
Sommeil: 5.0h (< 5.5h)
→ VETO: Récupération insuffisante
```

**Cas 4: Stress Combiné**
```
CTL: 65  |  ATL: 82  |  TSB: -17
Sommeil: 5.8h (< 6h) + sleep_dependent: true
→ VETO: Sommeil < 6h ET TSB < -15
```

---

## 🚦 Niveaux de Risque

Le système évalue 4 niveaux de risque:

### 1. LOW (Faible) - Vert 🟢
**Conditions:**
- TSB > 0
- ATL/CTL < 1.0
- Sommeil ≥ 7h

**Action:** Aucune restriction, entraînement normal possible.

**Exemple:**
```
CTL: 65  |  ATL: 58  |  TSB: +7
Sommeil: 7.5h
→ Risque: LOW
→ Action: Séance haute intensité OK
```

---

### 2. MEDIUM (Modéré) - Jaune 🟡
**Conditions:**
- -10 < TSB < 0
- 1.0 ≤ ATL/CTL < 1.3
- Sommeil 6-7h

**Action:** Surveillance renforcée, éviter accumulation.

**Recommandations:**
- Limiter intensité: 85-90% FTP
- Durée: 60-75 min max
- Repos: 1 jour minimum cette semaine

**Exemple:**
```
CTL: 65  |  ATL: 73  |  TSB: -8
Ratio: 1.12
Sommeil: 6.5h
→ Risque: MEDIUM
→ Action: Séance possible mais vigilance
```

---

### 3. HIGH (Élevé) - Orange 🟠
**Conditions:**
- -15 < TSB < -10
- 1.3 ≤ ATL/CTL < 1.8
- Sommeil < 6h (si sleep_dependent)

**Action:** Réduction intensité fortement recommandée.

**Recommandations:**
- Limiter intensité: 70-80% FTP max
- Durée: 45-60 min max
- Repos: 2 jours minimum cette semaine
- Prioriser Z2 endurance

**Exemple:**
```
CTL: 65  |  ATL: 78  |  TSB: -13
Ratio: 1.20
Sommeil: 5.8h (sleep_dependent: true)
→ Risque: HIGH
→ Action: Réduire intensité, ajouter repos
```

---

### 4. CRITICAL (Critique) - Rouge ⛔
**Conditions:**
- TSB ≤ -15 (ou < -25 = VETO automatique)
- ATL/CTL ≥ 1.8 (VETO automatique)
- Sommeil < 5.5h (VETO automatique)

**Action:** VETO automatique si seuils franchis.

**Recommandations VETO:**
- **Athlète Master:** "Cancel ALL training OR Z1 only (max 45min, <55% FTP)"
- **Athlète Senior:** "Rest day or very light Z1 only (max 60min)"

**Exemple:**
```
CTL: 65  |  ATL: 95  |  TSB: -30
Ratio: 1.46
Sommeil: 7h
→ Risque: CRITICAL
→ VETO: TSB < -25 (fatigue critique)
→ Action: ANNULER séance ou Z1 uniquement
```

---

## 💻 Utilisation Technique

### Vérification Pré-Séance

```python
from cyclisme_training_logs.rest_and_cancellations import check_pre_session_veto
from cyclisme_training_logs.config import AthleteProfile
from cyclisme_training_logs.api.intervals_client import IntervalsClient

# 1. Charger données wellness Intervals.icu
api = IntervalsClient(athlete_id="i151223", api_key=API_KEY)
wellness = api.get_wellness(oldest="2026-01-01", newest="2026-01-01")[0]

# 2. Charger profil athlète (.env)
profile = AthleteProfile.from_env()

# 3. Vérifier VETO avant séance haute intensité
result = check_pre_session_veto(
    wellness_data=wellness,
    athlete_profile=profile.dict(),
    session_intensity=95.0  # % FTP
)

# 4. Décision
if result['cancel']:
    print(f"⚠️  VETO ACTIVÉ")
    print(f"Niveau risque: {result['risk_level']}")
    print(f"Recommandation: {result['recommendation']}")
    print(f"Facteurs: {', '.join(result['factors'])}")

    # Actions:
    # - Annuler séance haute intensité
    # - Remplacer par Z1 (<55% FTP) max 45min
    # - Ou repos complet
    # - Logger dans week_planning.json (status: cancelled)
else:
    print(f"✅ Séance autorisée")
    print(f"Niveau risque: {result['risk_level']}")
    # Procéder avec séance planifiée
```

---

## 📋 FAQ Athlète

### Q1: Pourquoi un VETO même si je me sens bien?

**R:** Les métriques objectives (CTL/ATL/TSB) détectent la fatigue **avant** les symptômes subjectifs. Le surmenage se manifeste quand il est déjà trop tard. Le VETO prévient 1-2 séances en avance.

**Exemple vécu:** TSB -28, athlète se sentait "juste un peu fatigué", a continué → surmenage 3 semaines. Le VETO aurait évité.

---

### Q2: Puis-je ignorer un VETO?

**R:** **Non recommandé** pour athlète master (54 ans). Risques:
- Surmenage prolongé (2-4 semaines récupération)
- Baisse performances durée
- Risque blessure accru
- Système immunitaire affaibli

**Cas d'exception:** Compétition importante avec repos programmé après. Discuter avec coach.

---

### Q3: Que faire quand VETO activé?

**Options par ordre de priorité:**

1. **Repos complet** (recommandé si TSB < -25 ou sommeil < 5.5h)
2. **Z1 très light** (< 55% FTP, max 45min, RPE 1-2)
   - Pédalage facile, conversation normale
   - Objectif: circulation sanguine, pas entraînement
3. **Étirements + mobilité** (30min, pas d'intensité)
4. **Report séance** à date ultérieure (après TSB > -15)

**À NE PAS FAIRE:**
- ❌ Séance haute intensité quand même
- ❌ "Juste une petite séance" (> 60min ou > 70% FTP)
- ❌ Ignorer sommeil insuffisant

---

### Q4: Comment éviter futurs VETO?

**Stratégies prévention:**

1. **Gestion charge progressive**
   - Augmentation CTL: max 5-7 points/semaine (master)
   - Ratio ATL/CTL: garder < 1.3 en général
   - Périodes intensité alternées avec récupération

2. **Sommeil prioritaire**
   - Cible: ≥ 7h minimum (idéal 7.5-8h)
   - Sleep-dependent: ≥ 7h requis pour VO2 max
   - Tracker avec Garmin/Oura/Whoop

3. **Surveillance TSB**
   - TSB optimal: -5 à +10 (zone entraînement)
   - TSB < -10: réduire volume
   - TSB < -15: priorité récupération

4. **Récupération active**
   - 1-2 repos/semaine minimum (master)
   - Semaine récupération toutes 3-4 semaines
   - Z2 endurance si TSB -5 à -10

---

### Q5: Différence VETO master vs senior?

**Athlète Master (50+ ans):**
- Seuils plus stricts: TSB -25, ATL/CTL 1.8, sleep 5.5h
- Récupération 20-30% plus longue
- Sommeil plus critique (sleep-dependent)
- Risque surmenage accru

**Athlète Senior (20-40 ans):**
- Seuils plus permissifs: TSB -30, ATL/CTL 2.0, sleep 5.0h
- Récupération plus rapide
- Tolérance charge aiguë supérieure
- Marge erreur plus grande

**Pourquoi?** Capacité récupération diminue avec âge. Master = prudence accrue.

---

### Q6: Le VETO peut-il se tromper?

**Faux positifs (rares):**
- Données wellness Intervals.icu incorrectes
- Profil athlète mal configuré (.env)
- Événement exceptionnel (stress non-sportif)

**Faux négatifs (très rares):**
- Données wellness manquantes (sommeil)
- Fatigue non-musculaire (maladie débutante)
- Cumul stress pro + sport

**En cas de doute:** Préférer prudence (respecter VETO). Coût 1 séance << coût surmenage.

---

### Q7: Combien de VETO par mois est normal?

**Fréquence attendue (athlète master bien géré):**
- **0-1 VETO/mois:** Excellent (gestion optimale)
- **2-3 VETO/mois:** Normal (périodes intensité + récup)
- **4+ VETO/mois:** Alerte (revoir planification charge)

**Si VETO fréquents:** Réviser planning avec coach, réduire volume global, augmenter récupération.

---

### Q8: Puis-je customizer les seuils VETO?

**Oui**, mais **déconseillé** sans avis coach. Thresholds configurables dans `.env`:

```bash
# Master athlete defaults (54 ans)
TSB_CRITICAL=-25.0
ATL_CTL_RATIO_CRITICAL=1.8
RECOVERY_SLEEP_VETO=5.5

# Senior athlete (custom, plus permissif)
TSB_CRITICAL=-30.0
ATL_CTL_RATIO_CRITICAL=2.0
RECOVERY_SLEEP_VETO=5.0
```

**Attention:** Seuils plus permissifs = risque surmenage accru.

---

## 📊 Historique VETO (Tracking Recommandé)

Logger chaque VETO pour analyse tendances:

```json
{
  "date": "2026-01-01",
  "veto": true,
  "factors": ["TSB < -25 (critical fatigue)"],
  "metrics": {
    "ctl": 65,
    "atl": 95,
    "tsb": -30,
    "sleep_hours": 7.0
  },
  "action_taken": "rest_day",
  "session_cancelled": "S074-05-FTP"
}
```

**Analyse mensuelle:**
- Nombre VETO
- Facteurs principaux
- Corrélations (ex: sommeil insuffisant récurrent)
- Ajustements planning nécessaires

---

## 🔗 Liens Utiles

**Documentation Sprint R2.1:**
- [SPRINT_R2.1_DOCUMENTATION.md](../project-docs/sprints/R2/SPRINT_R2.1_DOCUMENTATION.md)
- [GUIDE_INSTALLATION_R2.1.md](../project-docs/sprints/R2/GUIDE_INSTALLATION_R2.1.md)
- [RECAPITULATIF_SPRINT_R2.1.md](../project-docs/sprints/R2/RECAPITULATIF_SPRINT_R2.1.md)

**Code Source:**
- `detect_overtraining_risk()`: [cyclisme_training_logs/utils/metrics_advanced.py](../cyclisme_training_logs/utils/metrics_advanced.py)
- `check_pre_session_veto()`: [cyclisme_training_logs/rest_and_cancellations.py](../cyclisme_training_logs/rest_and_cancellations.py)
- Tests: [tests/test_veto_integration.py](../tests/test_veto_integration.py)

**Références Scientifiques:**
- Training Stress Balance (Coggan)
- ATL/CTL Ratio Analysis
- Master Athlete Recovery (Tanaka et al.)

---

**Version:** 1.0
**Dernière mise à jour:** 2026-01-01
**Auteur:** Cyclisme Training Logs Team
**Validation:** MOA (Score 95/100)
