# Prompt Dev — Abstraction du Provider Santé (Health Provider Agnostic)

## Contexte

Le projet Entraineur Cycliste est déjà agnostique sur le provider IA (Claude, Mistral, OpenAI, Ollama). Le même principe doit s'appliquer au système de données santé : aujourd'hui Withings, demain potentiellement Garmin Connect, Oura, Whoop, Apple Health, ou aucun.

Le système de santé doit être **pluggable et débrayable**.

## Objectif

Créer une couche d'abstraction `HealthProvider` qui :

1. **Définit une interface commune** pour les données santé utilisées par le système d'entraînement
2. **Isole l'implémentation Withings** comme un provider parmi d'autres possibles
3. **Fonctionne en mode dégradé** quand aucun provider n'est configuré (pas d'erreur, pas de blocage)

## Interface commune attendue

Les données santé consommées par le système se résument à :

- **Sommeil** : durée totale, score, durée sommeil profond, heure coucher/lever
- **Poids / Composition** : poids (kg), masse grasse (%), masse musculaire (kg)
- **Readiness** : évaluation aptitude à l'entraînement (dérivée des métriques ci-dessus)
- **Tendances** : évolution sur une période (semaine, mois, custom)

## Architecture cible

```
health/
├── base.py              # Classe abstraite HealthProvider + dataclasses communes
├── withings_provider.py # Implémentation Withings (code existant refactoré)
├── null_provider.py     # Provider "aucun" — retourne None/valeurs neutres, jamais d'erreur
└── factory.py           # Factory qui instancie le bon provider selon la config
```

### Classe abstraite `HealthProvider`

```python
class HealthProvider(ABC):
    @abstractmethod
    def get_sleep(self, start_date, end_date=None, last_night_only=False) -> SleepData | None

    @abstractmethod
    def get_weight(self, start_date=None, end_date=None, latest_only=False) -> WeightData | None

    @abstractmethod
    def get_readiness(self, date=None) -> ReadinessData | None

    @abstractmethod
    def analyze_trends(self, period, start_date=None, end_date=None) -> TrendsData | None

    @abstractmethod
    def sync_to_intervals(self, start_date, end_date=None, data_types=None) -> SyncResult | None

    @abstractmethod
    def enrich_session(self, session_id, week_id, auto_readiness=True) -> EnrichResult | None

    @abstractmethod
    def auth_status(self) -> AuthStatus
```

### `NullProvider` (mode sans provider santé)

- Toutes les méthodes retournent `None` ou un objet neutre
- `auth_status()` retourne `{"status": "disabled", "message": "Aucun provider santé configuré"}`
- Aucune exception levée, jamais
- Les outils MCP qui appellent le health provider fonctionnent normalement : ils retournent un message clair du type "Données santé non disponibles — aucun provider configuré"

### Factory

```python
def create_health_provider(config) -> HealthProvider:
    provider_type = config.get("health_provider", "none")
    if provider_type == "withings":
        return WithingsProvider(config)
    elif provider_type == "none":
        return NullProvider()
    else:
        raise ValueError(f"Provider santé inconnu : {provider_type}")
```

## Contraintes

- **Pas de breaking change** sur les outils MCP existants (`withings-*`). Les outils actuels doivent continuer à fonctionner exactement pareil via le provider Withings
- **Nommage MCP** : les outils `withings-*` restent pour la rétrocompatibilité. À terme on pourrait exposer des outils génériques `health-*` qui délèguent au provider actif, mais ce n'est pas dans le scope immédiat
- **Config** : le provider santé est défini dans la config projet (même pattern que le provider IA). Par défaut = `"none"`
- **Tests** : le `NullProvider` doit avoir une couverture complète. Chaque méthode testée pour vérifier qu'elle retourne proprement sans erreur
- **Dataclasses communes** : les structures de données (`SleepData`, `WeightData`, etc.) sont dans `base.py`, indépendantes de tout provider. Le `WithingsProvider` convertit les réponses API Withings vers ces structures communes

## Ce qui est hors scope (pour l'instant)

- Implémentation d'un second provider (Garmin, Oura, etc.)
- Migration des noms d'outils MCP de `withings-*` vers `health-*`
- UI de sélection du provider

## Priorité

Ce refactoring est un **P2** — à intégrer proprement mais pas en urgence. L'objectif est de poser l'architecture correcte maintenant pour ne pas accumuler de dette technique sur un couplage Withings en dur.
