# -*- coding: utf-8 -*-
"""
Withings Integration Package
Synchronisation Withings vers Intervals.icu pour entrainement cyclisme
"""

from withings_integration.core.withings_integration import (
    WithingsIntegration,
    sync_weight_to_intervals,
    sync_sleep_to_intervals
)

__version__ = "1.0.0"
__all__ = [
    'WithingsIntegration',
    'sync_weight_to_intervals',
    'sync_sleep_to_intervals'
]
