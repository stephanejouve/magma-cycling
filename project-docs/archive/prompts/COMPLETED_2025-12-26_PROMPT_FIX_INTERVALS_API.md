# MISSION: Fix Intervals.icu API Configuration with VITE_ Prefix

## CONTEXT

**Project:** cyclisme-training-logs
**Issue:** Weekly analysis workflow cannot initialize Intervals.icu API
**Root Cause:** config.py missing Intervals.icu configuration with VITE_ prefix
**Requirement:** ALL environment variables MUST use VITE_ prefix for React compatibility

**Current .env (correct):**
```
VITE_INTERVALS_ATHLETE_ID=i151223
VITE_INTERVALS_API_KEY=REDACTED_INTERVALS_KEY
```

**Current Error:**
```
WARNING: Failed to initialize Intervals API:
IntervalsAPI.__init__() missing 2 required positional arguments:
'athlete_id' and 'api_key'
```

---

## TASK 1: Add Intervals.icu Configuration to config.py

**File:** `cyclisme_training_logs/config.py`

**Location:** After AIProvidersConfig class (line ~325), before global instances

**Add this new configuration class:**
```python
# ============================================================================
# Intervals.icu API Configuration
# ============================================================================

class IntervalsConfig:
    """Configuration for Intervals.icu API.

    Manages athlete ID and API key for Intervals.icu integration.
    Uses VITE_ prefix for React compatibility.

    Attributes:
        athlete_id: Intervals.icu athlete ID (format: i123456)
        api_key: Intervals.icu API key
        base_url: API base URL (default: https://intervals.icu/api/v1)

    Examples:
        >>> config = get_intervals_config()
        >>> print(config.athlete_id)
        'i151223'
        >>> print(config.is_configured())
        True
    """

    def __init__(self):
        """Initialize Intervals.icu configuration from environment variables."""
        # Read from VITE_ prefixed variables (React compatibility)
        self.athlete_id = os.getenv('VITE_INTERVALS_ATHLETE_ID')
        self.api_key = os.getenv('VITE_INTERVALS_API_KEY')
        self.base_url = os.getenv('VITE_INTERVALS_BASE_URL', 'https://intervals.icu/api/v1')

    def is_configured(self) -> bool:
        """Check if Intervals.icu API is properly configured.

        Returns:
            True if both athlete_id and api_key are set

        Examples:
            >>> config = get_intervals_config()
            >>> if config.is_configured():
            ...     # Use API
            ...     pass
            ... else:
            ...     # Fallback mode
            ...     pass
        """
        return bool(self.athlete_id and self.api_key)

    def get_headers(self) -> dict:
        """Get authentication headers for Intervals.icu API.

        Returns:
            Dict with Authorization header using Basic auth

        Examples:
            >>> config = get_intervals_config()
            >>> headers = config.get_headers()
            >>> # Use with requests
            >>> import requests
            >>> response = requests.get(url, headers=headers)
        """
        if not self.is_configured():
            raise ValueError("Intervals.icu API not configured")

        import base64
        auth_string = f"API_KEY:{self.api_key}"
        auth_bytes = auth_string.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_string = base64_bytes.decode('ascii')

        return {
            'Authorization': f'Basic {base64_string}',
            'Content-Type': 'application/json'
        }


# Global Intervals config instance
_intervals_config_instance: Optional[IntervalsConfig] = None


def get_intervals_config() -> IntervalsConfig:
    """Get singleton instance of Intervals.icu config.

    Returns:
        IntervalsConfig instance

    Examples:
        >>> config = get_intervals_config()
        >>> print(config.athlete_id)
        'i151223'
    """
    global _intervals_config_instance
    if _intervals_config_instance is None:
        _intervals_config_instance = IntervalsConfig()
    return _intervals_config_instance


def reset_intervals_config():
    """Reset Intervals config singleton (useful for tests).

    Examples:
        >>> reset_intervals_config()
        >>> config = get_intervals_config()  # Creates new instance
    """
    global _intervals_config_instance
    _intervals_config_instance = None
```

---

## TASK 2: Update Module Exports

**File:** `cyclisme_training_logs/config.py`

**Location:** End of file, update __all__ or add if missing
```python
# Module exports
__all__ = [
    # Data repo config
    'DataRepoConfig',
    'get_data_config',
    'set_data_config',
    'reset_data_config',
    # AI providers config
    'AIProvidersConfig',
    'get_ai_config',
    'reset_ai_config',
    # Intervals.icu config (NEW)
    'IntervalsConfig',
    'get_intervals_config',
    'reset_intervals_config',
]
```

---

## TASK 3: Fix Weekly Workflow to Use Config

**File:** `cyclisme_training_logs/workflows/workflow_weekly.py`

**Find:** Import section (top of file)

**Add this import:**
```python
from cyclisme_training_logs.config import get_intervals_config
```

**Find:** Section where IntervalsAPI is initialized (likely in WeeklyWorkflow.__init__ or similar)

**Replace:**
```python
# OLD (broken)
self.api = IntervalsAPI(athlete_id, api_key)  # Missing args

# NEW (working)
intervals_config = get_intervals_config()
if intervals_config.is_configured():
    self.api = IntervalsAPI(
        athlete_id=intervals_config.athlete_id,
        api_key=intervals_config.api_key
    )
else:
    self.api = None  # Graceful degradation
```

---

## TASK 4: Update Gartner Tags in config.py

**File:** `cyclisme_training_logs/config.py`

**Update module docstring LAST_REVIEW date:**
```python
LAST_REVIEW: 2025-12-26  # Current date
```

---

## VALIDATION CHECKLIST

After changes, verify:
```bash
# 1. Test config import
poetry run python -c "
from cyclisme_training_logs.config import get_intervals_config
config = get_intervals_config()
print('✅ Athlete ID:', config.athlete_id)
print('✅ Configured:', config.is_configured())
print('✅ Headers:', 'Authorization' in config.get_headers())
"

# 2. Test weekly-analysis (should work without API warning)
poetry run weekly-analysis --week current

# 3. Verify no regression
poetry run pytest tests/ -v
```

**Expected Results:**
- ✅ Athlete ID: i151223
- ✅ Configured: True
- ✅ Headers: True
- ✅ No API initialization warning
- ✅ All tests passing

---

## GIT WORKFLOW
```bash
# 1. Commit changes
git add cyclisme_training_logs/config.py
git add cyclisme_training_logs/workflows/workflow_weekly.py
git commit -m "fix(config): add Intervals.icu configuration with VITE_ prefix

- Add IntervalsConfig class to config.py
- Support VITE_ prefixed environment variables (React compatibility)
- Update workflow_weekly.py to use get_intervals_config()
- Fix API initialization with proper athlete_id/api_key
- Add graceful degradation when API not configured

Resolves: Missing Intervals API configuration
GARTNER_TIME: I/P0 (config.py already I/P0)"

# 2. Push
git push origin main
```

---

## NOTES

**CRITICAL:**
- Use VITE_ prefix for ALL environment variables
- Maintain React/Python dual compatibility
- No changes to .env file (already correct)
- Graceful degradation if API not configured

**Files Modified:**
1. `cyclisme_training_logs/config.py` (add IntervalsConfig)
2. `cyclisme_training_logs/workflows/workflow_weekly.py` (use config)

**Estimated Time:** 15-20 minutes

**Complexity:** LOW (configuration addition + import update)
