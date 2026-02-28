planning - Planning Manager & Calendar
=======================================

Module pour planification d'entraînement (4-12 semaines).

.. toctree::
   :maxdepth: 4

   magma_cycling.planning.alert_messages
   magma_cycling.planning.audit_log
   magma_cycling.planning.backup
   magma_cycling.planning.calendar
   magma_cycling.planning.control_tower
   magma_cycling.planning.intervals_sync
   magma_cycling.planning.models
   magma_cycling.planning.outdoor_discipline
   magma_cycling.planning.peaks_phases
   magma_cycling.planning.planning_manager
   magma_cycling.planning.session_formatter
   magma_cycling.planning.workout_validation

Module contents
---------------

.. automodule:: magma_cycling.planning
   :members:
   :show-inheritance:
   :undoc-members:

Exemples
--------

Créer un plan d'entraînement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from magma_cycling.planning import (
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

Calendrier hebdomadaire
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from magma_cycling.planning import (
        TrainingCalendar, WorkoutType
    )

    calendar = TrainingCalendar(year=2026)

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
