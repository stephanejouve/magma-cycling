intelligence - Training Intelligence & Feedback Loop
====================================================

Module Sprint R4 pour intelligence multi-temporelle et feedback loop.

Résout problème silos temporels en créant mémoire partagée entre analyses quotidienne/hebdo/mensuelle.

**Version :** 2.1.0

**Date :** 2026-01-01

training_intelligence
---------------------

.. automodule:: cyclisme_training_logs.intelligence.training_intelligence
   :members:
   :undoc-members:
   :show-inheritance:

Enums
~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.AnalysisLevel
   :members:
   :undoc-members:

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.ConfidenceLevel
   :members:
   :undoc-members:

Dataclasses
~~~~~~~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.TrainingLearning
   :members:
   :undoc-members:

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.Pattern
   :members:
   :undoc-members:

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.ProtocolAdaptation
   :members:
   :undoc-members:

Main Class
~~~~~~~~~~

.. autoclass:: cyclisme_training_logs.intelligence.training_intelligence.TrainingIntelligence
   :members:
   :undoc-members:
   :special-members: __init__

Exemples
--------

Ajouter Learning
~~~~~~~~~~~~~~~~

.. code-block:: python

    from cyclisme_training_logs.intelligence import (
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

.. automodule:: cyclisme_training_logs.intelligence.discrete_pid_controller
   :members:
   :undoc-members:
   :show-inheritance:

Contrôleur PID Discret adapté aux mesures sporadiques FTP (tous les 6-8 semaines).

biomechanics
------------

.. automodule:: cyclisme_training_logs.intelligence.biomechanics
   :members:
   :undoc-members:
   :show-inheritance:

Module intégration recherche Grappe (2000) - cadence optimale et coefficients PID adaptatifs.

biomechanics_intervals
----------------------

.. automodule:: cyclisme_training_logs.intelligence.biomechanics_intervals
   :members:
   :undoc-members:
   :show-inheritance:

Extraction métriques biomécaniques depuis API Intervals.icu.

Voir Aussi
----------

- :doc:`planning` - Planning Manager (Sprint R3)
- :doc:`utils` - Metrics Advanced (Sprint R2)
- `GUIDE_INTELLIGENCE.md <../../project-docs/guides/GUIDE_INTELLIGENCE.md>`_ - Guide complet
