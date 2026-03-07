# 🎯 Feature Request : Enrichir les prompts IA du coaching avec le contexte athlète

## Contexte du problème

Plusieurs workflows appellent un provider IA pour générer des analyses ou des prescriptions d'entraînement. Actuellement, **aucun de ces workflows ne transmet le contexte athlète** au provider. Seules les statistiques brutes sont envoyées.

**Résultat observé sur l'analyse mensuelle février 2026 :**
- Recommande un "tableau de bord Google Sheets" → l'athlète a déjà un système intégré
- Suggère de "consulter un coach" → le système EST le coach IA
- Propose un ratio 70-80% END sans tenir compte de la phase actuelle (reconstruction CTL)
- Ne comprend pas que S078 à 0 TSS et S081 à 67 TSS ont des causes spécifiques (maladie, contraintes pro)
- Ignore les contraintes récurrentes (dette de sommeil chronique, travail terrain, 54 ans)

**Ce problème affecte TOUS les workflows IA**, pas seulement l'analyse mensuelle.

## Principe d'architecture : 1 contexte athlète + N missions spécifiques

La mission du coach IA change selon le **moment du cycle** où il intervient. On ne demande pas la même chose selon qu'on analyse un mois écoulé, qu'on planifie une semaine, qu'on évalue une séance, ou qu'on fait un bilan hebdo.

### Architecture cible

```
config/
  └── athlete_context.yaml        → QUI : profil, contraintes, historique (commun à tous)

prompts/
  ├── base_system.txt             → Socle commun : rôle coach, consignes générales, interdictions
  ├── mesocycle_analysis.txt      → Mission : analyse macro mésocycle (tendances, périodisation)
  ├── weekly_planning.txt         → Mission : prescription semaine (tactique, séances concrètes)
  ├── daily_feedback.txt          → Mission : feedback post-séance (adhérence, qualité, ajustement J+1)
  └── weekly_review.txt           → Mission : bilan fin de semaine (compliance, recommandations S+1)
```

### Assemblage du prompt final

```
prompt_final = base_system.txt + athlete_context (formaté) + mission_spécifique.txt + données du workflow
```

Chaque workflow injecte ses données propres (stats mensuelles, métriques du jour, résultats de séance, etc.) après le contexte et la mission.

## Données du contexte athlète

### 1. Profil statique (athlete_context.yaml)

```yaml
athlete:
  name: "Stéphane Jouve"
  age: 54
  training_since: "2023-06"
  platform: "Home trainer (virtuel)"
  objectives: "Progression forme générale, pas de compétition"
  constraints:
    - "Dette de sommeil chronique (moyenne 5-6h/nuit)"
    - "Travail terrain (technicien télécom), fatigue physique variable selon chantiers"
    - "Horaires irréguliers impactant régularité entraînement"
    - "Récupération plus lente (54 ans) - adapter progressivité"
  progression:
    ftp_start: 201
    ftp_current: 223
    weight_start: 88.0
    weight_current: 84.7
  system_context: |
    L'athlète utilise un système intégré avec planification hebdomadaire
    automatisée, suivi santé (sommeil, poids, readiness) et coaching IA
    multi-provider. Ne JAMAIS recommander d'outils externes (Google Sheets,
    TrainingPeaks, coach humain, appli tierce) car le système actuel couvre
    ces besoins.
```

### 2. Données dynamiques (chargées à l'exécution)

Récupérées par le loader partagé depuis les APIs existantes :

```python
# Depuis get_athlete_profile()
- FTP, poids, FC repos, FC max, FTHR, W', zones puissance/FC

# Depuis get_metrics()
- CTL actuel, ATL actuel, TSB, ramp rate

# Depuis le health provider (optionnel, dégradation gracieuse)
- Sommeil moyen dernière semaine
- Poids moyen dernière semaine
- Readiness du jour (si pertinent)
```

## Missions spécifiques par workflow

### A. Analyse mésocycle (`mesocycle_analysis.txt`)

**Consommateur :** `monthly-analysis`
**Moment :** fin de mois ou à la demande
**Vision :** macro — le film du mois

```
## Ta mission
Tu analyses un MÉSOCYCLE complet (4-5 semaines). Ton rôle :

1. **Évaluer la cohérence de la périodisation** : la progression de charge est-elle logique ?
   Les semaines de décharge sont-elles bien placées ?
2. **Identifier les patterns** : récurrence de sessions skipped, distribution volume/intensité,
   impact des contraintes de sommeil et travail sur l'exécution
3. **Évaluer la trajectoire** : le CTL progresse-t-il dans la bonne direction par rapport
   à la phase actuelle ? Le ramp rate est-il soutenable pour un athlète de 54 ans ?
4. **Recommander des ajustements macro** pour le mésocycle suivant : volume cible,
   ratio intensité/endurance, fréquence, gestion de la récupération

Ne descends PAS au niveau séance individuelle. Reste sur les tendances et la structure.
Si des semaines ont un TSS anormalement bas, cherche l'explication dans les contraintes
connues plutôt que de blâmer le manque de motivation.
```

### B. Planification hebdomadaire (`weekly_planning.txt`)

**Consommateur :** `weekly-planner`
**Moment :** début de semaine (lundi ou dimanche soir)
**Vision :** tactique — prescription des 7 jours

```
## Ta mission
Tu prescris les SÉANCES CONCRÈTES de la semaine à venir. Ton rôle :

1. **Évaluer l'état de forme** : CTL/ATL/TSB actuels, readiness du jour,
   qualité du sommeil récent, fatigue résiduelle de la semaine précédente
2. **Proposer un plan réaliste** : 4-6 séances adaptées à la phase actuelle,
   aux contraintes horaires et à l'état de fatigue. Chaque séance avec :
   - Type (END/INT/REC/TEC)
   - Durée estimée
   - TSS cible
   - Description structurée (warmup, corps, cooldown avec zones et cadences)
3. **Prévoir des alternatives** : si la dette de sommeil s'aggrave ou si le travail
   est particulièrement fatigant, proposer des versions allégées
4. **Respecter les principes de périodisation** : pas 2 séances INT consécutives,
   récupération après intensité, progressivité du TSS hebdo

Sois CONCRET : zones en %FTP, cadences en rpm, durées en minutes.
Pas de généralités du type "faites du fractionné". Prescris.
```

### C. Feedback post-séance (`daily_feedback.txt`)

**Consommateur :** `daily-sync` (avec ai_analysis=true)
**Moment :** après chaque séance complétée
**Vision :** micro — feedback immédiat

```
## Ta mission
Tu évalues UNE SÉANCE qui vient d'être réalisée. Ton rôle :

1. **Mesurer l'adhérence** : comparer planifié vs réalisé (TSS, IF, durée, puissance)
2. **Évaluer la qualité d'exécution** : régularité de puissance dans les intervalles,
   cadence tenue, découplage cardio, équilibre gauche/droite
3. **Contextualiser** : la performance est-elle cohérente avec le sommeil de la nuit,
   la fatigue accumulée (ATL), la position dans la semaine ?
4. **Suggérer pour J+1** : faut-il maintenir le plan, alléger, ou prendre un repos ?

Sois FACTUEL : appuie-toi sur les données (watts, bpm, cadence, découplage).
Une séance à -15% de TSS cible n'est pas un échec si le sommeil était de 4h.
Pas de jugement moral, des constatations et des ajustements.
```

### D. Bilan fin de semaine (`weekly_review.txt`)

**Consommateur :** `end_of_week`
**Moment :** dimanche soir / lundi matin
**Vision :** intermédiaire — rétrospective et recommandations

```
## Ta mission
Tu fais le BILAN d'une semaine écoulée. Ton rôle :

1. **Compliance** : taux de réalisation TSS, sessions complétées/skipped/cancelled,
   causes des écarts
2. **Qualité globale** : les séances réalisées étaient-elles bien exécutées ?
   Les intensités étaient-elles dans les zones prescrites ?
3. **Impact fitness** : évolution CTL/ATL sur la semaine, tendance par rapport
   au plan mésocycle
4. **Recommandations S+1** : ajustements concrets pour la semaine suivante
   en fonction de ce qui s'est passé (volume, intensité, récupération)

Compare toujours à la semaine PRÉCÉDENTE pour montrer la trajectoire.
Si le taux de compliance est bas, identifie les patterns (toujours les mêmes jours ?
toujours le même type de séance ?) et propose des adaptations structurelles.
```

## Implémentation technique

### 1. Loader partagé : `config/athlete_context.py`

```python
"""Chargement du contexte athlète pour tous les workflows IA."""

from pathlib import Path
from typing import Optional
import yaml

ATHLETE_CONTEXT_PATH = Path(__file__).parent / "athlete_context.yaml"

def load_athlete_context(path: Optional[Path] = None) -> dict:
    """Charge le contexte athlète statique depuis YAML.

    Returns:
        dict avec le contexte athlète, ou dict vide si fichier absent (dégradation gracieuse)
    """
    context_path = path or ATHLETE_CONTEXT_PATH
    if not context_path.exists():
        logger.warning(f"Athlete context not found at {context_path}, using empty context")
        return {}
    with open(context_path) as f:
        return yaml.safe_load(f).get("athlete", {})
```

### 2. Builder de prompt : `prompts/prompt_builder.py`

```python
"""Assemblage des prompts IA par workflow."""

from pathlib import Path
from config.athlete_context import load_athlete_context

PROMPTS_DIR = Path(__file__).parent

def build_prompt(
    mission: str,  # "mesocycle_analysis", "weekly_planning", "daily_feedback", "weekly_review"
    current_metrics: dict,  # CTL, ATL, FTP, poids... depuis APIs
    workflow_data: str,  # Données spécifiques au workflow (stats, séance, etc.)
    athlete_context: Optional[dict] = None,
) -> tuple[str, str]:
    """Construit le prompt (system, user) pour un workflow donné.

    Returns:
        (system_prompt, user_prompt)
    """
    context = athlete_context or load_athlete_context()

    # Charger les fichiers texte
    base = (PROMPTS_DIR / "base_system.txt").read_text()
    mission_text = (PROMPTS_DIR / f"{mission}.txt").read_text()

    # Assembler le system prompt
    system_prompt = f"""{base}

## Profil athlète
{format_athlete_profile(context, current_metrics)}

{mission_text}
"""

    # Le user prompt contient les données du workflow
    user_prompt = workflow_data

    return system_prompt, user_prompt


def format_athlete_profile(context: dict, metrics: dict) -> str:
    """Formate le profil athlète pour injection dans le prompt."""
    if not context:
        return "(Contexte athlète non disponible)"

    ftp = metrics.get('ftp', '?')
    weight = metrics.get('weight', '?')
    w_per_kg = f"{ftp/weight:.2f}" if isinstance(ftp, (int,float)) and isinstance(weight, (int,float)) else "?"

    lines = [
        f"- {context.get('name', 'Athlète')}, {context.get('age', '?')} ans",
        f"- FTP: {ftp}W ({w_per_kg} W/kg) - Poids: {weight}kg",
        f"- Entraînement structuré depuis {context.get('training_since', '?')}",
        f"- Plateforme: {context.get('platform', '?')}",
        f"- Objectifs: {context.get('objectives', 'Non définis')}",
        f"- CTL: {metrics.get('ctl', '?'):.1f} | ATL: {metrics.get('atl', '?'):.1f} | Ramp: {metrics.get('ramp_rate', '?')}",
        "",
        "Contraintes connues:",
    ]
    for c in context.get('constraints', []):
        lines.append(f"  - {c}")

    lines.append("")
    lines.append(context.get('system_context', ''))

    return "\n".join(lines)
```

### 3. Prompt socle commun : `prompts/base_system.txt`

```
Tu es un coach cyclisme IA intégré à un système d'entraînement structuré.

## Principes fondamentaux
- Sois FACTUEL : appuie-toi sur les données, pas sur des généralités
- Sois CONTEXTUEL : tiens compte des contraintes connues de l'athlète
- Sois RÉALISTE : adapte tes recommandations à l'âge, au mode de vie et aux contraintes de l'athlète
- Sois ACTIONNABLE : chaque recommandation doit être applicable dans le système d'entraînement

## Interdictions absolues
- Ne recommande JAMAIS d'outils externes (Google Sheets, TrainingPeaks, Strava, coach humain, appli tierce)
- Ne blâme JAMAIS le manque de motivation — cherche les causes dans les contraintes
- Ne propose JAMAIS de plans irréalistes (>6 séances/semaine, >90min en semaine)
- N'utilise JAMAIS de formulations condescendantes ou infantilisantes

## Format de réponse
- Réponds en français
- Structure ton analyse avec des sections claires
- Utilise les données concrètes (watts, TSS, %FTP, bpm, minutes)
- Termine toujours par des recommandations actionnables numérotées par priorité
```

### 4. Intégration dans les workflows existants

Chaque workflow remplace son appel IA actuel par :

```python
from prompts.prompt_builder import build_prompt

# Exemple dans monthly_analysis
system, user = build_prompt(
    mission="mesocycle_analysis",
    current_metrics=self.get_current_metrics(),  # CTL, ATL, FTP, poids
    workflow_data=monthly_stats_formatted,        # Les stats du mois
)
response = self.ai_provider.generate(system_prompt=system, user_prompt=user)
```

## Tests à écrire

```python
# --- Tests du loader ---
def test_load_athlete_context_returns_profile():
    """Le loader retourne le profil athlète depuis YAML."""

def test_load_athlete_context_missing_file_returns_empty():
    """Si YAML absent, retourne dict vide sans crash."""

def test_load_athlete_context_custom_path():
    """Le loader accepte un chemin personnalisé."""

# --- Tests du builder ---
def test_build_prompt_includes_base_system():
    """Le prompt contient le socle commun."""

def test_build_prompt_includes_athlete_profile():
    """Le prompt contient FTP, poids, CTL, contraintes."""

def test_build_prompt_includes_mission_text():
    """Le prompt contient la mission spécifique au workflow."""

def test_build_prompt_mesocycle_analysis():
    """Le prompt mésocycle contient les consignes macro."""

def test_build_prompt_weekly_planning():
    """Le prompt weekly contient les consignes de prescription."""

def test_build_prompt_daily_feedback():
    """Le prompt daily contient les consignes d'évaluation séance."""

def test_build_prompt_weekly_review():
    """Le prompt weekly review contient les consignes bilan."""

def test_build_prompt_no_athlete_context_graceful():
    """Sans contexte athlète, le prompt fonctionne avec fallback."""

def test_build_prompt_no_external_tools_in_base():
    """Le socle interdit les recommandations d'outils externes."""

def test_format_athlete_profile_computes_w_per_kg():
    """Le formateur calcule correctement le ratio W/kg."""

# --- Tests d'intégration ---
def test_monthly_analysis_uses_prompt_builder():
    """L'analyse mensuelle utilise le builder (mock provider)."""

def test_weekly_planner_uses_prompt_builder():
    """Le planner hebdo utilise le builder (mock provider)."""

def test_daily_sync_ai_uses_prompt_builder():
    """Le daily sync IA utilise le builder (mock provider)."""
```

## Critères d'acceptation

1. ✅ `athlete_context.yaml` créé avec profil complet et documenté
2. ✅ `load_athlete_context()` partagé par tous les workflows, avec dégradation gracieuse
3. ✅ `build_prompt()` assemble correctement : socle + contexte + mission + données
4. ✅ 4 fichiers de mission créés (mésocycle, weekly plan, daily feedback, weekly review)
5. ✅ `monthly-analysis` migré sur le nouveau système de prompts
6. ✅ Tests unitaires couvrent loader, builder, et chaque mission
7. ✅ Tous les tests existants passent (1809+)
8. ✅ Le fichier `athlete_context.yaml` est facilement modifiable par l'utilisateur

## Ordre d'implémentation suggéré

1. **Phase 1** : Créer `athlete_context.yaml` + `load_athlete_context()` + tests
2. **Phase 2** : Créer `prompts/base_system.txt` + 4 missions + `prompt_builder.py` + tests
3. **Phase 3** : Migrer `monthly-analysis` sur le nouveau système + test intégration
4. **Phase 4** (ultérieur) : Migrer `weekly-planner`, `daily-sync`, `end_of_week`

## Notes d'architecture

- Le pattern `athlete_context.yaml` est pensé pour la **généralisation multi-athlète** :
  si d'autres utilisateurs utilisent Magma, chacun aura son propre fichier de contexte
- Les fichiers `.txt` des missions sont éditables sans toucher au code Python
- Le builder est découplé des providers IA : il produit des strings,
  le provider les consomme comme il veut (system/user, message unique, etc.)
- `config_base.py` (1158 lignes, candidat refactoring) pourrait à terme absorber
  le chargement du contexte athlète, mais pour l'instant un module séparé est plus sûr
