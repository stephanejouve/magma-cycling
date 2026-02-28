intelligence - Training Intelligence & Feedback Loop
====================================================

Module pour intelligence multi-temporelle et feedback loop.

Résout problème silos temporels en créant mémoire partagée entre analyses quotidienne/hebdo/mensuelle.

.. toctree::
   :maxdepth: 4

   magma_cycling.intelligence.biomechanics
   magma_cycling.intelligence.biomechanics_intervals
   magma_cycling.intelligence.compensation_strategies
   magma_cycling.intelligence.discrete_pid_controller
   magma_cycling.intelligence.pid_controller
   magma_cycling.intelligence.training_intelligence
   magma_cycling.intelligence.workout_diversity

Module contents
---------------

.. automodule:: magma_cycling.intelligence
   :members:
   :show-inheritance:
   :undoc-members:

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
        print("Pattern détecté!")

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
