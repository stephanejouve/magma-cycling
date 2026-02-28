shift\_sessions - Session Rescheduling Tool
===========================================

Outil pour décaler, échanger et réorganiser les séances d'entraînement planifiées.

.. automodule:: magma_cycling.shift_sessions
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Features
--------

**Shift (Décalage)**
   Décale des sessions de N jours en avant ou en arrière.

**Swap/Rotate (Échange)**
   Échange les dates de deux sessions (rotation).

**Insert Rest Day**
   Insère un jour de repos et décale automatiquement les sessions suivantes.

**Remove Session**
   Supprime une session du planning.

**Renumber**
   Ajuste les ``session_id`` pour correspondre aux jours de la semaine.

**Sync avec Intervals.icu**
   Option ``--sync`` pour mettre à jour les dates d'événements sur Intervals.icu.

Safety Features
~~~~~~~~~~~~~~~

- **Protection anti-completed**: Empêche la modification de sessions déjà réalisées
- **Validation des limites**: Vérifie que les sessions restent dans lundi-dimanche
- **Validation Pydantic**: Toutes les modifications sont validées
- **Dry-run mode**: Preview sans sauvegarder (``--dry-run``)
- **Sync optionnel**: Contrôle explicite de la synchronisation

Usage Examples
~~~~~~~~~~~~~~

**Décaler des sessions**

.. code-block:: bash

    # Décaler toutes les sessions à partir de jeudi (+1 jour)
    poetry run shift-sessions --week-id S081 --from-day 4 --shift-days 1

    # Avec renumérotation et sync
    poetry run shift-sessions --week-id S081 --from-day 4 --shift-days 1 --renumber --sync

    # Preview avant de faire le changement
    poetry run shift-sessions --week-id S081 --from-day 4 --shift-days 1 --dry-run

**Échanger/Inverser deux jours**

.. code-block:: bash

    # Échanger jeudi et vendredi (jours 4 et 5)
    poetry run shift-sessions --week-id S081 --swap-days 4 5

    # Avec sync Intervals.icu
    poetry run shift-sessions --week-id S081 --swap-days 4 5 --sync

    # Échanger deux sessions spécifiques par ID
    poetry run shift-sessions --week-id S081 --swap S081-04 S081-05

**Insérer un jour de repos**

.. code-block:: bash

    # Insérer repos jeudi et décaler automatiquement le reste
    poetry run shift-sessions --week-id S081 --insert-rest-day 4

**Supprimer une session**

.. code-block:: bash

    # Supprimer une session du planning
    poetry run shift-sessions --week-id S081 --remove-session S081-07

Related Modules
~~~~~~~~~~~~~~~

- :doc:`magma_cycling.planning` - Planning models and managers
- ``update_session_status.py`` - Update individual session status
- ``weekly_planner.py`` - Generate weekly planning prompts
