# -*- coding: utf-8 -*-
"""
Core module - API Withings et integration Intervals.icu
"""

from withings_integration.core.withings_integration import (
    WithingsIntegration,
    sync_weight_to_intervals,
    sync_sleep_to_intervals
)

__all__ = [
    'WithingsIntegration',
    'sync_weight_to_intervals',
    'sync_sleep_to_intervals'
]
