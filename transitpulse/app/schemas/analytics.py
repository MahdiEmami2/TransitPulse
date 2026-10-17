"""Pydantic schemas for analytics responses."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DelayStatistics(BaseModel):
    """Statistical summary of delay data."""
    count: int = Field(..., example=100)
    mean: float = Field(..., example=5.2)
    median: float = Field(..., example=3.0)
    min: int = Field(..., example=-2)
    max: int = Field(..., example=45)
    std_dev: float = Field(..., example=6.1)
    p10: float = Field(..., example=1.0)
    p25: float = Field(..., example=2.0)
    p75: float = Field(..., example=6.0)
    p90: float = Field(..., example=10.0)


class DelayDistributionBin(BaseModel):
    """A single bin in a delay distribution histogram."""
    range_start: int = Field(..., example=-5)
    range_end: int = Field(..., example=5)
    count: int = Field(..., example=42)


class DelayDistribution(BaseModel):
    """Histogram of delay values."""
    bins: list[DelayDistributionBin] = Field(..., example=[
        {"range_start": -5, "range_end": 5, "count": 42},
        {"range_start": 5, "range_end": 15, "count": 28},
    ])


class DelayTrend(BaseModel):
    """A single time-series aggregate."""
    period: str = Field(..., example="2026-10-15")
    count: int = Field(..., example=100)
    mean_delay: float = Field(..., example=5.2)


class DelayTrends(BaseModel):
    """Time-series aggregates of delays."""
    trends: list[DelayTrend] = Field(..., example=[
        {"period": "2026-10-15", "count": 100, "mean_delay": 5.2},
        {"period": "2026-10-16", "count": 110, "mean_delay": 5.5},
    ])


class TopDelayedItem(BaseModel):
    """A single top delayed stop or line."""
    key: str = Field(..., example="STOP_123")
    name: str = Field(..., example="Central Station")
    count: int = Field(..., example=150)
    mean_delay: float = Field(..., example=8.5)
    max_delay: int = Field(..., example=45)


class TopDelayed(BaseModel):
    """Top N delayed stops or lines."""
    items: list[TopDelayedItem] = Field(..., example=[
        {"key": "STOP_123", "name": "Central Station", "count": 150, "mean_delay": 8.5, "max_delay": 45},
        {"key": "STOP_456", "name": "East Square", "count": 120, "mean_delay": 7.2, "max_delay": 38},
    ])
