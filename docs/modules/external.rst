external - External Workout Data Sources
=========================================

Module Sprint Zwift Integration (S1 + S2) pour intégration sources externes de workouts.

Permet recherche, caching, et diversification des entraînements via whatsonzwift.com.

**Version :** 1.0.0

**Date :** 2026-02-10

**Sprint :** Zwift Integration S1 + S2

Architecture
------------

Le package external fournit:

- **Models** : Structures Pydantic pour workouts Zwift
- **Client** : Cache SQLite avec scoring multi-critères
- **Converter** : Conversion formats avec compatibilité Wahoo
- **Scraper** : Framework scraping HTML (foundation)
- **Seed Data** : Workouts curés pour bootstrap

zwift_models
------------

.. automodule:: magma_cycling.external.zwift_models
   :members:
   :undoc-members:
   :show-inheritance:

Enums
~~~~~

.. autoclass:: magma_cycling.external.zwift_models.ZwiftCategory
   :members:
   :undoc-members:

.. autoclass:: magma_cycling.external.zwift_models.SegmentType
   :members:
   :undoc-members:

Dataclasses
~~~~~~~~~~~

.. autoclass:: magma_cycling.external.zwift_models.ZwiftWorkoutSegment
   :members:
   :undoc-members:

.. autoclass:: magma_cycling.external.zwift_models.ZwiftWorkout
   :members:
   :undoc-members:

.. autoclass:: magma_cycling.external.zwift_models.WorkoutSearchCriteria
   :members:
   :undoc-members:

.. autoclass:: magma_cycling.external.zwift_models.WorkoutMatch
   :members:
   :undoc-members:

zwift_client
------------

.. automodule:: magma_cycling.external.zwift_client
   :members:
   :undoc-members:
   :show-inheritance:

Main Class
~~~~~~~~~~

.. autoclass:: magma_cycling.external.zwift_client.ZwiftWorkoutClient
   :members:
   :undoc-members:
   :special-members: __init__

zwift_converter
---------------

.. automodule:: magma_cycling.external.zwift_converter
   :members:
   :undoc-members:
   :show-inheritance:

Main Class
~~~~~~~~~~

.. autoclass:: magma_cycling.external.zwift_converter.ZwiftWorkoutConverter
   :members:
   :undoc-members:

zwift_scraper
-------------

.. automodule:: magma_cycling.external.zwift_scraper
   :members:
   :undoc-members:
   :show-inheritance:

Main Class
~~~~~~~~~~

.. autoclass:: magma_cycling.external.zwift_scraper.ZwiftWorkoutScraper
   :members:
   :undoc-members:

zwift_seed_data
---------------

.. automodule:: magma_cycling.external.zwift_seed_data
   :members:
   :undoc-members:
   :show-inheritance:

Exemples
--------

Recherche Workout
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from magma_cycling.external import (
        ZwiftWorkoutClient,
        WorkoutSearchCriteria
    )

    # Initialiser client
    client = ZwiftWorkoutClient()

    # Définir critères
    criteria = WorkoutSearchCriteria(
        session_type="FTP",
        tss_target=56,
        tss_tolerance=15,
        duration_min=40,
        duration_max=45,
        exclude_recent=True  # Diversité
    )

    # Rechercher
    matches = client.search_workouts(criteria)

    # Afficher résultats
    for match in matches[:3]:
        workout = match.workout
        print(f"{workout.name}")
        print(f"  Score: {match.score:.1f}/100")
        print(f"  TSS: {workout.tss} (Δ{match.tss_delta})")
        print(f"  Durée: {workout.duration_minutes}min")
        print(f"  URL: {workout.url}")

Conversion Format
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from magma_cycling.external import (
        ZwiftWorkoutConverter,
        ZwiftWorkout
    )

    converter = ZwiftWorkoutConverter()

    # Convertir en format Intervals.icu
    text_description = converter.workout_to_intervals_text(workout)
    print(text_description)

    # Valider compatibilité Wahoo
    is_valid, issues = converter.validate_wahoo_compatibility(
        text_description
    )

    if not is_valid:
        print("⚠️ Issues Wahoo:")
        for issue in issues:
            print(f"  - {issue}")

Seeding Cache
~~~~~~~~~~~~~

.. code-block:: python

    from magma_cycling.external.zwift_seed_data import (
        get_zwift_camp_baseline_2025
    )
    from magma_cycling.external import ZwiftWorkoutClient

    client = ZwiftWorkoutClient()

    # Charger workouts curés
    workouts = get_zwift_camp_baseline_2025()

    # Peupler cache
    for workout in workouts:
        client._save_workout_to_cache(workout)

    print(f"✅ {len(workouts)} workouts ajoutés au cache")

Statistiques Cache
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    client = ZwiftWorkoutClient()
    stats = client.get_cache_stats()

    print(f"Total workouts: {stats['total_workouts']}")
    print(f"Cache path: {stats['cache_path']}")

    if stats.get('by_category'):
        print("\\nPar catégorie:")
        for category, count in stats['by_category'].items():
            print(f"  {category}: {count}")

Marquer Usage
~~~~~~~~~~~~~

.. code-block:: python

    from datetime import date

    client = ZwiftWorkoutClient()

    # Marquer workout comme utilisé
    client.mark_workout_used(
        workout=workout,
        used_date=date.today().isoformat()
    )

    # Stats mis à jour pour diversité
    stats = client.get_workout_stats(workout.url)
    print(f"Usage total: {stats['total_uses']}")
    print(f"Dernier usage: {stats['last_used']}")

Scripts CLI
-----------

Le package fournit 3 scripts CLI:

search-zwift-workouts
~~~~~~~~~~~~~~~~~~~~~

Recherche workouts dans le cache.

.. code-block:: bash

    # Recherche FTP ~56 TSS
    poetry run search-zwift-workouts --type FTP --tss 56

    # Avec contraintes durée
    poetry run search-zwift-workouts --type INT --tss 80 \\
        --duration-min 45 --duration-max 60

    # Statistiques cache
    poetry run search-zwift-workouts --cache-stats

    # Workout exemple
    poetry run search-zwift-workouts --sample

seed-zwift-workouts
~~~~~~~~~~~~~~~~~~~

Charge workouts curés dans le cache.

.. code-block:: bash

    # Lister collections disponibles
    poetry run seed-zwift-workouts --list

    # Seed toutes les collections
    poetry run seed-zwift-workouts

    # Seed collection spécifique
    poetry run seed-zwift-workouts --collection zwift-camp-baseline-2025

populate-zwift-cache
~~~~~~~~~~~~~~~~~~~~

Framework scraping web (foundation pour expansion future).

.. code-block:: bash

    # Scraper collection (placeholder)
    poetry run populate-zwift-cache --collection zwift-camp-baseline --dry-run

Algorithme Scoring
------------------

Le scoring multi-critères (0-100) évalue:

**TSS Accuracy (40 points)**
  Distance au TSS cible. Score maximum si TSS exact, décroissance linéaire dans la tolérance.

**Type Match (30 points)**
  Correspondance exacte du type de session (FTP, INT, END, etc.).

**Duration Fit (20 points)**
  Respect des contraintes de durée min/max.

**Novelty (10 points)**
  Moins utilisé = score plus élevé. Max 10 usages comptabilisés.

Architecture Cache
------------------

**Database**: SQLite (~/.../data/cache/zwift_workouts.db)

**Schema**:

.. code-block:: sql

    CREATE TABLE workouts (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        tss INTEGER NOT NULL,
        url TEXT UNIQUE NOT NULL,
        description TEXT,
        segments_json TEXT,
        cached_at TEXT NOT NULL,
        last_used_date TEXT,
        usage_count INTEGER DEFAULT 0
    );

**Indexes**:
  - idx_category_tss: (category, tss) - Recherche rapide
  - idx_cached_at: (cached_at) - Cleanup TTL

**TTL**: 60 jours (configurable)

**Cleanup**: Automatique à chaque recherche

Diversité
---------

Intégré avec :doc:`intelligence` module workout_diversity:

- Fenêtre rotation: 21 jours
- Max répétition: 40%
- Tracking dans intelligence.json
- Filtrage automatique recherches

Compatibilité Wahoo
-------------------

Toutes les conversions garantissent:

✅ Power % explicite sur chaque ligne
✅ Format Intervals.icu valide
✅ Pas de markdown dans descriptions
✅ Segments standard (Warmup, Main set, Cooldown)

Format validé pour export direct vers Wahoo ELEMNT.

Intégration Weekly Planner
---------------------------

Le weekly planner affiche automatiquement les workouts disponibles:

.. code-block:: text

    ## 🎨 Workouts Externes Disponibles (Diversité)

    **Source:** Cache Zwift (whatsonzwift.com)
    **Total disponible:** 4 workouts

    **Par catégorie:**
      - FTP: 1 workout(s)
      - VO2 Max: 1 workout(s)
      - Sprint: 1 workout(s)
      - Intervals: 1 workout(s)

    **Instructions:**
    - Ces workouts peuvent être utilisés pour introduire de la DIVERSITÉ
    - Utiliser: poetry run search-zwift-workouts --type [TYPE] --tss [TSS]
    - Tracking automatique pour éviter répétitions (fenêtre 21 jours)

Tests
-----

Couverture complète avec 10 tests unitaires dans:

- ``tests/intelligence/test_workout_diversity.py``

Voir Aussi
----------

- :doc:`intelligence` - Workout Diversity Tracking
- :doc:`planning` - Weekly Planner Integration
- `Zwift Camp Baseline <https://whatsonzwift.com/workouts/zwift-camp-baseline>`_ - Source officielle
