external - External Workout Data Sources
=========================================

Module pour intégration sources externes de workouts (Zwift).

Permet recherche, caching, et diversification des entraînements via whatsonzwift.com.

.. toctree::
   :maxdepth: 4

   magma_cycling.external.zwift_client
   magma_cycling.external.zwift_converter
   magma_cycling.external.zwift_models
   magma_cycling.external.zwift_scraper
   magma_cycling.external.zwift_seed_data

Module contents
---------------

.. automodule:: magma_cycling.external
   :members:
   :show-inheritance:
   :undoc-members:

Architecture
------------

Le package external fournit:

- **Models** : Structures Pydantic pour workouts Zwift
- **Client** : Cache SQLite avec scoring multi-critères
- **Converter** : Conversion formats avec compatibilité Wahoo
- **Scraper** : Framework scraping HTML (foundation)
- **Seed Data** : Workouts curés pour bootstrap

Exemples
--------

Recherche Workout
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from magma_cycling.external import (
        ZwiftWorkoutClient,
        WorkoutSearchCriteria
    )

    client = ZwiftWorkoutClient()

    criteria = WorkoutSearchCriteria(
        session_type="FTP",
        tss_target=56,
        tss_tolerance=15,
        duration_min=40,
        duration_max=45,
        exclude_recent=True
    )

    matches = client.search_workouts(criteria)

    for match in matches[:3]:
        workout = match.workout
        print(f"{workout.name} - Score: {match.score:.1f}/100")

Conversion Format
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from magma_cycling.external import ZwiftWorkoutConverter

    converter = ZwiftWorkoutConverter()
    text_description = converter.workout_to_intervals_text(workout)

    is_valid, issues = converter.validate_wahoo_compatibility(text_description)

Scripts CLI
-----------

.. code-block:: bash

    # Recherche FTP ~56 TSS
    poetry run search-zwift-workouts --type FTP --tss 56

    # Seed workouts curés
    poetry run seed-zwift-workouts

    # Stats cache
    poetry run search-zwift-workouts --cache-stats

Algorithme Scoring
------------------

Le scoring multi-critères (0-100) évalue:

**TSS Accuracy (40 points)**
  Distance au TSS cible. Score maximum si TSS exact.

**Type Match (30 points)**
  Correspondance exacte du type de session.

**Duration Fit (20 points)**
  Respect des contraintes de durée min/max.

**Novelty (10 points)**
  Moins utilisé = score plus élevé.
