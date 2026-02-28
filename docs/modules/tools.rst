tools - CLI Tools
=================

Outils en ligne de commande pour la gestion des séances et du planning.

shift_sessions - Session Rescheduling Tool
-------------------------------------------

Outil pour décaler, échanger et réorganiser les séances d'entraînement planifiées.

.. automodule:: magma_cycling.shift_sessions
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Features
~~~~~~~~

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

- ✅ **Protection anti-completed**: Empêche la modification de sessions déjà réalisées
- ✅ **Validation des limites**: Vérifie que les sessions restent dans lundi-dimanche
- ✅ **Validation Pydantic**: Toutes les modifications sont validées
- ✅ **Dry-run mode**: Preview sans sauvegarder (``--dry-run``)
- ✅ **Sync optionnel**: Contrôle explicite de la synchronisation

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

Shell Aliases
~~~~~~~~~~~~~

Des alias shell sont fournis dans ``.zsh_aliases_shift_sessions`` :

.. code-block:: bash

    # Source les alias
    source ~/magma-cycling/.zsh_aliases_shift_sessions

    # Ou ajouter à ~/.zshrc de façon permanente
    echo 'source ~/magma-cycling/.zsh_aliases_shift_sessions' >> ~/.zshrc

**Alias disponibles:**

- ``shift`` - Commande de base
- ``swap-days`` - Échanger deux jours
- ``swap-sessions`` - Échanger deux sessions par ID
- ``shift-sync`` - Shift avec sync automatique
- ``swap-days-sync`` - Swap avec sync
- ``insert-rest`` - Insérer repos et décaler
- ``shift-preview`` - Preview (dry-run)

**Exemples avec alias:**

.. code-block:: bash

    # Échanger jeudi et vendredi avec sync
    swap-days-sync S081 4 5

    # Insérer repos mercredi
    insert-rest S081 3

    # Preview d'un shift
    shift-preview --week-id S081 --from-day 4 --shift-days 1

Architecture
~~~~~~~~~~~~

.. code-block:: python

    class SessionShifter:
        """Main class for session shifting operations."""

        def __init__(self, week_id: str, planning_dir: Path | None = None):
            """Initialize with week ID and planning directory."""

        def shift_sessions(
            self,
            from_session_id: str | None = None,
            from_day: int | None = None,
            shift_days: int = 1,
            renumber: bool = False,
            stop_at_completed: bool = True,
        ) -> list[Session]:
            """Shift sessions forward or backward."""

        def swap_sessions(
            self,
            session1_id: str | None = None,
            session2_id: str | None = None,
            day1: int | None = None,
            day2: int | None = None,
        ) -> tuple[Session, Session] | None:
            """Swap two sessions (exchange dates)."""

        def insert_rest_day(
            self,
            day: int,
            description: str = "Jour de repos"
        ) -> Session:
            """Insert rest day and shift subsequent sessions."""

        def sync_session_changes(
            self,
            client: IntervalsClient
        ) -> bool:
            """Sync changes with Intervals.icu."""

Workflow Example
~~~~~~~~~~~~~~~~

Scénario typique : fatigue jeudi, besoin de décaler toutes les séances d'un jour.

.. code-block:: python

    from magma_cycling.shift_sessions import SessionShifter

    # 1. Initialiser le shifter
    shifter = SessionShifter(week_id="S081")

    # 2. Afficher le planning actuel
    shifter.display_summary()

    # 3. Décaler sessions à partir de jeudi (+1 jour)
    shifter.shift_sessions(
        from_day=4,          # À partir de jeudi
        shift_days=1,        # Décaler de +1 jour
        renumber=True,       # Ajuster les session_id
    )

    # 4. Afficher le résultat
    shifter.display_summary()

    # 5. Sauvegarder avec sync
    shifter.save(dry_run=False, sync=True)

Error Handling
~~~~~~~~~~~~~~

**Session Already Completed**

.. code-block:: text

    ❌ Cannot swap S081-01: session already completed!
    Completed sessions must not be modified.

**Solution**: Ne pas modifier les sessions réalisées. Créer une nouvelle session si nécessaire.

**No Sessions Found**

.. code-block:: text

    ValueError: No sessions found on or after day 5

**Solution**: Aucune session à shifter après ce jour. Normal en fin de semaine.

**Sync Failed**

.. code-block:: text

    ⚠️  Warning: Sync with Intervals.icu failed: ...

**Solution**:
- Vérifier les credentials (``VITE_INTERVALS_API_KEY``)
- Vérifier que la session a un ``intervals_id``
- Le fichier JSON local est quand même sauvegardé

Testing
~~~~~~~

Suite de tests complète avec 16 tests:

.. code-block:: bash

    poetry run pytest tests/test_shift_sessions.py -v

**Couverture:**
- ✅ Shift avec/sans renumbering
- ✅ Swap par ID et par jour
- ✅ Protection sessions completed
- ✅ Insert rest day
- ✅ Remove session
- ✅ Dry-run mode
- ✅ Timestamp updates
- ✅ Tracking des modifications

Related Modules
~~~~~~~~~~~~~~~

- :doc:`planning` - Planning models and managers
- :doc:`magma_cycling.planning` - Pydantic models (Session, WeeklyPlan)
- ``update_session_status.py`` - Update individual session status
- ``weekly_planner.py`` - Generate weekly planning prompts

See Also
~~~~~~~~

- :doc:`../SHIFT_SESSIONS_ALIASES` - Guide complet avec exemples réels
- ``.zsh_aliases_shift_sessions`` - Fichier d'alias shell
