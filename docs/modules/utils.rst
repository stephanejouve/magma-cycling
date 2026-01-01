utils - Metrics Advanced
=========================

Module Sprint R2 pour calculs métriques avancés.

metrics_advanced
----------------

.. automodule:: cyclisme_training_logs.utils.metrics_advanced
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Fonctions Principales
~~~~~~~~~~~~~~~~~~~~~

**calculate_ctl()**
   Calcule Chronic Training Load (fitness 42 jours).

**calculate_tsb()**
   Calcule Training Stress Balance (forme vs fatigue).

**calculate_ramp_rate()**
   Calcule rampe CTL avec validation limites.

**assess_overtraining_risk()**
   Évalue risque surentraînement (LOW/MEDIUM/HIGH).
   Intègre VETO logic pour sommeil insuffisant.

Exemples
~~~~~~~~

.. code-block:: python

    from cyclisme_training_logs.utils.metrics_advanced import (
        calculate_ctl,
        calculate_tsb,
        assess_overtraining_risk
    )

    # Calculer CTL sur 42 jours
    ctl = calculate_ctl(tss_values=[50, 60, 0, 75, 80, ...])

    # Calculer TSB
    tsb = calculate_tsb(ctl=65.0, atl=45.0)

    # Évaluer risque
    risk = assess_overtraining_risk(
        tsb=-25.0,
        ctl=70.0,
        recent_sleep_hours=[6.5, 5.0, 6.0],  # VETO si < 5.5h
        athlete_profile=profile
    )
    print(f"Risque : {risk['level']}")
    print(f"VETO : {risk['veto_triggered']}")
