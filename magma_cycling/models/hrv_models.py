"""HRV (Heart Rate Variability) models, provider-agnostic.

These models describe HRV readings consumed by the training pipeline,
independent of the source provider (Withings, Apple HealthKit, Garmin,
Polar, etc.). Providers translate their native payloads into HrvReading
instances. The pipeline never imports provider-specific code.
"""

from __future__ import annotations

from datetime import date as DateType
from datetime import datetime as DateTimeType
from typing import Literal

from pydantic import BaseModel, Field

MetricType = Literal["rmssd", "sdnn", "lnrmssd"]
Context = Literal["nocturnal_start", "nocturnal_end", "nocturnal_avg", "daytime_median"]
DataQuality = Literal["ok", "partial", "missing"]


class HrvReading(BaseModel):
    """One HRV measurement, provider-agnostic."""

    measurement_date: DateType = Field(description="Reference date of the measurement.")
    measurement_time: DateTimeType | None = Field(
        default=None,
        description="Timestamp of the measurement if known. Nocturnal readings use the "
        "morning of the ending night; daytime readings use the sample timestamp.",
    )
    metric_type: MetricType = Field(description="Which HRV metric this value represents.")
    value_ms: float = Field(description="HRV value in milliseconds.", gt=0)
    context: Context = Field(description="When/how the measurement was taken.")
    source_provider: str = Field(
        description="Provider name (withings, healthkit, …) — traceability only. "
        "Never consumed by domain logic.",
    )
    data_quality: DataQuality = Field(
        default="ok",
        description="ok = full confidence, partial = degraded but usable, "
        "missing = no data (typically wrapped as None upstream).",
    )
