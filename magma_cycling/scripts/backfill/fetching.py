"""Data fetching mixin for HistoryBackfiller."""

import logging
import time

from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)


class DataFetchMixin:
    """Fetch activities and estimate resources from Intervals.icu API."""

    def get_analyzed_activities(self) -> set[str]:
        """Get set of already analyzed activity IDs."""
        history = self.state.state.get("history", [])

        return {h["activity_id"] for h in history}

    def fetch_activities(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetch all activities from Intervals.icu in date range.

        IMPORTANT: Enrichit chaque activite avec details complets (TSS, IF, NP)
        car get_activities() ne retourne que les champs basiques.

        Gere rate limiting avec retry + backoff exponentiel.

        Returns list sorted chronologically (oldest first).
        """
        print(f"\n📥 Recuperation activites {start_date} → {end_date}...")

        # Fetch liste activites (donnees basiques)
        activities_basic = self.api.get_activities(oldest=start_date, newest=end_date)

        print(f"✅ {len(activities_basic)} activites trouvees")
        print("📊 Enrichissement avec details (TSS, IF, NP)...")

        # Enrichir chaque activite avec retry logic
        activities_detailed = []
        failed_permanent = []

        for i, activity in enumerate(activities_basic, 1):
            activity_id = activity.get("id")
            if not activity_id:
                activities_detailed.append(activity)
                continue

            # Retry avec backoff exponentiel
            max_retries = 3
            base_delay = 5  # secondes (5s, 10s, 20s)
            enriched = False

            for attempt in range(max_retries):
                try:
                    # Fetch details complets (inclut TSS, IF, NP)
                    detailed = self.api.get_activity(activity_id)
                    activities_detailed.append(detailed)
                    enriched = True

                    # Progress indicator every 50 activities
                    if i % 50 == 0:
                        print(f"   ... {i}/{len(activities_basic)} enrichies")

                    break  # Succes, sortir boucle retry

                except HTTPError as e:
                    if e.response.status_code == 429:  # Rate limit
                        if attempt < max_retries - 1:
                            # Backoff exponentiel: 2s, 4s, 8s
                            wait_time = base_delay * (2**attempt)
                            print(
                                f"   ⏸️  Rate limit {activity_id}, retry dans {wait_time}s (tentative {attempt + 2}/{max_retries})"
                            )
                            time.sleep(wait_time)
                        else:
                            # Echec apres 3 tentatives
                            print(
                                f"   ❌ Skip {activity_id}: rate limit persistant apres {max_retries} tentatives"
                            )
                            failed_permanent.append(activity_id)
                    else:
                        # Autre erreur HTTP (400, 404, 500, etc.)
                        print(f"   ⚠️  HTTP {e.response.status_code} pour {activity_id}")
                        failed_permanent.append(activity_id)
                        break  # Pas de retry pour erreurs non-429

                except Exception as e:
                    # Erreur reseau, timeout, etc.
                    print(f"   ⚠️  Exception {activity_id}: {type(e).__name__}")
                    failed_permanent.append(activity_id)
                    break  # Pas de retry pour exceptions inattendues

            # Si echec definitif apres retries, utiliser donnees basiques
            if not enriched:
                activities_detailed.append(activity)

        # Sort by date (oldest first for chronological backfill)
        activities_detailed.sort(key=lambda a: a.get("start_date_local", ""))

        print(f"✅ {len(activities_detailed)} activites enrichies")

        if failed_permanent:
            print(f"⚠️  {len(failed_permanent)} activites non enrichies (erreur definitive)")
            print("   → Ces activites seront probablement rejetees par is_valid_activity()")
            print("   → Conseil: Relancer backfill avec periode plus courte")

        return activities_detailed

    def estimate_resources(self, count: int) -> dict[str, float]:
        """
        Estimate time and cost for analyzing N activities.

        Returns:
            Dict with 'time_minutes' and 'cost_usd' estimates.
        """
        # Time estimates per provider (minutes per activity)

        time_per_activity = {
            "mistral_api": 1.0,
            "claude_api": 0.7,
            "openai": 0.8,
            "ollama": 4.0,
            "clipboard": 4.0,  # Manual
        }

        # Cost estimates per provider (USD per activity)
        cost_per_activity = {
            "mistral_api": 0.02,
            "claude_api": 0.08,
            "openai": 0.05,
            "ollama": 0.0,
            "clipboard": 0.0,
        }

        time_minutes = count * time_per_activity.get(self.provider, 1.0)
        cost_usd = count * cost_per_activity.get(self.provider, 0.0)

        return {"time_minutes": time_minutes, "time_hours": time_minutes / 60, "cost_usd": cost_usd}
