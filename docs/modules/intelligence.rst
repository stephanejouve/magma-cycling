intelligence - Training Intelligence & Feedback Loop
====================================================

Module Sprint R4 pour intelligence multi-temporelle et feedback loop.

Résout problème silos temporels en créant mémoire partagée entre analyses quotidienne/hebdo/mensuelle.

**Version :** 2.1.0

**Date :** 2026-01-01

training_intelligence
---------------------

.. automodule:: magma_cycling.intelligence.training_intelligence
   :members:
   :undoc-members:
   :show-inheritance:

Enums
~~~~~

.. autoclass:: magma_cycling.intelligence.training_intelligence.AnalysisLevel
   :members:
   :undoc-members:

.. autoclass:: magma_cycling.intelligence.training_intelligence.ConfidenceLevel
   :members:
   :undoc-members:

Dataclasses
~~~~~~~~~~~

.. autoclass:: magma_cycling.intelligence.training_intelligence.TrainingLearning
   :members:
   :undoc-members:

.. autoclass:: magma_cycling.intelligence.training_intelligence.Pattern
   :members:
   :undoc-members:

.. autoclass:: magma_cycling.intelligence.training_intelligence.ProtocolAdaptation
   :members:
   :undoc-members:

Main Class
~~~~~~~~~~

.. autoclass:: magma_cycling.intelligence.training_intelligence.TrainingIntelligence
   :members:
   :undoc-members:
   :special-members: __init__

Exemples
--------

Ajouter Learning
~~~~~~~~~~~~~~~~

.. code-block:: python

    from magma_cycling.intelligence import (
        TrainingIntelligence,
        AnalysisLevel
    )

    intelligence = TrainingIntelligence()

    learning = intelligence.add_learning(
        category="sweet-spot",
        description="88-90% FTP sustainable 2x10min",
        evidence=["S024-04: 2x10@88% FTP, découplage 5.2%"],
        level=AnalysisLevel.DAILY
    )

    print(f"Confidence: {learning.confidence.value}")  # LOW

Identifier Pattern
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from datetime import date

    pattern = intelligence.identify_pattern(
        name="sleep_debt_vo2_failure",
        trigger_conditions={"sleep": "<6h", "workout_type": "VO2"},
        observed_outcome="Incapacité finir intervalles",
        observation_date=date.today()
    )

    # Vérifier si conditions matchent
    if pattern.matches({"sleep": 5.5, "workout_type": "VO2"}):
        print("⚠️ Pattern détecté!")

Insights Quotidiens
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    insights = intelligence.get_daily_insights({
        "workout_type": "sweet-spot",
        "planned_intensity": 89
    })

    print("Recommandations:")
    for rec in insights["recommendations"]:
        print(f"  - {rec}")

Persistance
~~~~~~~~~~~

.. code-block:: python

    from pathlib import Path

    # Sauvegarder
    intelligence.save_to_file(Path("~/data/intelligence.json").expanduser())

    # Charger
    intelligence = TrainingIntelligence.load_from_file(
        Path("~/data/intelligence.json").expanduser()
    )

discrete_pid_controller
-----------------------

.. automodule:: magma_cycling.intelligence.discrete_pid_controller
   :members:
   :undoc-members:
   :show-inheritance:

Contrôleur PID Discret adapté aux mesures sporadiques FTP (tous les 6-8 semaines).

biomechanics
------------

.. automodule:: magma_cycling.intelligence.biomechanics
   :members:
   :undoc-members:
   :show-inheritance:

Module intégration recherche Grappe (2000) - cadence optimale et coefficients PID adaptatifs.

biomechanics_intervals
----------------------

.. automodule:: magma_cycling.intelligence.biomechanics_intervals
   :members:
   :undoc-members:
   :show-inheritance:

Extraction métriques biomécaniques depuis API Intervals.icu.

workout_diversity
-----------------

.. automodule:: magma_cycling.intelligence.workout_diversity
   :members:
   :undoc-members:
   :show-inheritance:

Module Sprint Zwift Integration S2 pour tracking diversité workouts externes.

Dataclasses
~~~~~~~~~~~

.. autoclass:: magma_cycling.intelligence.workout_diversity.WorkoutUsage
   :members:
   :undoc-members:

Main Class
~~~~~~~~~~

.. autoclass:: magma_cycling.intelligence.workout_diversity.WorkoutDiversityTracker
   :members:
   :undoc-members:
   :special-members: __init__

Exemples
~~~~~~~~

Enregistrer Usage
^^^^^^^^^^^^^^^^^

.. code-block:: python

    from magma_cycling.intelligence.workout_diversity import (
        WorkoutDiversityTracker,
        WorkoutUsage
    )
    from datetime import date

    tracker = WorkoutDiversityTracker()

    usage = WorkoutUsage(
        workout_url="https://whatsonzwift.com/workouts/flat-out-fast",
        workout_name="Flat Out Fast",
        date_used=date.today().isoformat(),
        session_id="S081-02",
        source="whatsonzwift.com",
        category="FTP",
        tss=56
    )

    tracker.record_workout_usage(usage)

Vérifier Diversité
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Vérifier si récemment utilisé (21 jours)
    is_recent = tracker.is_recently_used(
        "https://whatsonzwift.com/workouts/flat-out-fast"
    )

    if is_recent:
        print("⚠️ Workout utilisé récemment - éviter pour diversité")

Rapport Diversité
^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Générer rapport sur 30 jours
    report = tracker.get_diversity_report(days=30)

    print(f"Sessions: {report['total_sessions']}")
    print(f"Workouts uniques: {report['unique_workouts']}")
    print(f"Taux répétition: {report['repetition_rate']:.1%}")
    print(f"Diversité OK: {report['diversity_ok']}")  # <= 40%

    # Workouts les plus utilisés
    for workout in report['most_used']:
        print(f"  - {workout['name']}: {workout['count']}x")

Voir Aussi
----------

- :doc:`external` - Zwift Workout Integration (Sprint S2)
- :doc:`planning` - Planning Manager (Sprint R3)
- :doc:`utils` - Metrics Advanced (Sprint R2)
- `GUIDE_INTELLIGENCE.md <../../project-docs/guides/GUIDE_INTELLIGENCE.md>`_ - Guide complet
