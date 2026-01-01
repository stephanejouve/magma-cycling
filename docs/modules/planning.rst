planning - Planning Manager & Calendar
=======================================

Module Sprint R3 pour planification d'entraînement (4-12 semaines).

planning_manager
----------------

.. automodule:: cyclisme_training_logs.planning.planning_manager
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Classes Principales
~~~~~~~~~~~~~~~~~~~

**PlanningManager**
   Gestionnaire de plans d'entraînement avec validation faisabilité.

**TrainingPlan**
   Dataclass représentant un plan (4-12 semaines).

**TrainingObjective**
   Dataclass représentant un objectif/échéance.

Enums
~~~~~

**PriorityLevel**
   - LOW
   - MEDIUM
   - HIGH
   - CRITICAL

**ObjectiveType**
   - EVENT
   - FTP_TARGET
   - CTL_TARGET
   - WEIGHT_TARGET
   - MILESTONE

Exemples
~~~~~~~~

.. code-block:: python

    from cyclisme_training_logs.planning import (
        PlanningManager, PriorityLevel, ObjectiveType
    )

    # Créer plan
    manager = PlanningManager()
    plan = manager.create_training_plan(
        name="Build Printemps",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 4, 26),  # 8 semaines
        weekly_tss_targets=[250, 270, 290, 310, 320, 300, 280, 250]
    )

    # Ajouter objectif
    manager.add_deadline(
        plan_name="Build Printemps",
        deadline_date=date(2026, 5, 10),
        event_name="Gran Fondo",
        priority=PriorityLevel.HIGH
    )

    # Valider faisabilité
    validation = manager.validate_plan_feasibility(
        "Build Printemps",
        current_ctl=55.0
    )


calendar
--------

.. automodule:: cyclisme_training_logs.planning.calendar
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Classes Principales
~~~~~~~~~~~~~~~~~~~

**TrainingCalendar**
   Calendrier hebdomadaire ISO avec gestion séances et repos.

**TrainingSession**
   Dataclass représentant une séance (TSS planifié/réel).

**WeeklySummary**
   Dataclass résumé hebdomadaire (TSS total, breakdown).

Enum
~~~~

**WorkoutType**
   - ENDURANCE (Z2)
   - TEMPO (Z3)
   - THRESHOLD (Z4/FTP)
   - VO2MAX (Z5)
   - RECOVERY (Z1)
   - REST

Exemples
~~~~~~~~

.. code-block:: python

    from cyclisme_training_logs.planning import (
        TrainingCalendar, WorkoutType
    )

    # Initialiser calendrier
    calendar = TrainingCalendar(year=2026)

    # Générer semaine 3
    week_dates = calendar.generate_weekly_calendar(week_num=3)

    # Ajouter séance
    session = calendar.add_session(
        session_date=date(2026, 1, 12),
        workout_type=WorkoutType.THRESHOLD,
        planned_tss=85.0,
        duration_min=90,
        intensity_pct=95.0
    )

    # Résumé hebdomadaire
    summary = calendar.get_week_summary(week_num=3)
    print(f"TSS total : {summary.total_tss}")


Contraintes Master Athletes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **TSS max** : 380/semaine (vs 450 senior)
- **CTL ramp max** : 7 points/semaine (vs 10 senior)
- **Repos obligatoire** : Dimanche (jour 6)
- **Validation** : Automatique via ``validate_plan_feasibility()``
