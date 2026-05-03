"""Non-regression tests: _is_low_effort_social_ride must accept None description.

Background
----------
On 2026-04-26 21:30, ``daily-sync`` started crashing with
``AttributeError: 'NoneType' object has no attribute 'lower'`` at
``servo_evaluation.py:218``. Root cause: Intervals.icu may return
``description: null`` in its activity payload. ``dict.get(key, default)``
returns ``default`` only when the key is absent — when the key is present
with value ``None``, ``.get()`` returns ``None``, and the chained
``.lower()`` then crashes.

These tests pin the fix: ``_is_low_effort_social_ride`` must tolerate a
``description=None`` value without crashing, and behave equivalently to
an empty/missing description (i.e. no keyword match → returns False).
"""

from unittest.mock import MagicMock

from magma_cycling.workflows.sync.servo_evaluation import ServoEvaluationMixin


class _FakeSync(ServoEvaluationMixin):
    def __init__(self):
        self.client = MagicMock()
        self.servo_criteria = {
            "decoupling_threshold": 7.5,
            "sleep_threshold_hours": 7.0,
            "feel_threshold": 4,
            "tsb_threshold": -10,
        }


def test_description_none_does_not_crash():
    """Regression: activity with description=None must not raise."""
    sync = _FakeSync()
    activity = {
        "icu_training_load": 20,
        "average_watts": 100,
        "np": 110,
        "description": None,
    }
    # Must not raise AttributeError — and since no keyword matches, returns False.
    assert sync._is_low_effort_social_ride(activity, metrics={}) is False


def test_description_missing_key_does_not_crash():
    """Coverage: missing key behaves like None (existing default-path).

    Different code path than `description=None`, but must give the same result.
    """
    sync = _FakeSync()
    activity = {
        "icu_training_load": 20,
        "average_watts": 100,
        "np": 110,
        # description key intentionally absent
    }
    assert sync._is_low_effort_social_ride(activity, metrics={}) is False


def test_description_with_keyword_still_detects_social_ride():
    """Positive: keyword detection still works after the fix."""
    sync = _FakeSync()
    activity = {
        "icu_training_load": 20,
        "average_watts": 100,
        "np": 110,
        "description": "Sortie d'accompagnement avec arrêts",
    }
    assert sync._is_low_effort_social_ride(activity, metrics={}) is True
