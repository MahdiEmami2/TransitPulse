"""Pydantic schemas for prediction requests and responses."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Request for delay prediction."""
    stop_id: str = Field(..., example="STOP_123")
    line: str = Field(..., example="U-Bahn U1")
    direction: str = Field(..., example="North")
    scheduled_time: datetime = Field(..., example="2026-10-16T08:30:00")
    vehicle_id: Optional[str] = Field(None, example="VEH_456")


class PredictionResponse(BaseModel):
    """Response with predicted delay and confidence interval."""
    stop_id: str = Field(..., example="STOP_123")
    line: str = Field(..., example="U-Bahn U1")
    direction: str = Field(..., example="North")
    scheduled_time: datetime = Field(..., example="2026-10-16T08:30:00")
    predicted_delay_minutes: float = Field(..., example=4.5)
    confidence_lower: float = Field(..., example=2.0)
    confidence_upper: float = Field(..., example=7.0)
    model_name: str = Field(..., example="delay_predictor_v1")
    model_version: str = Field(..., example="1.0.0")


class ModelInfo(BaseModel):
    """Metadata about the currently active model."""
    name: str = Field(..., example="delay_predictor_v1")
    version: str = Field(..., example="1.0.0")
    algorithm: str = Field(..., example="HistGradientBoostingRegressor")
    trained_at: Optional[datetime] = Field(None, example="2026-10-15T12:00:00")
    metrics: dict = Field(..., example={
        "mae": 2.5,
        "rmse": 4.2,
        "r2": 0.75,
    })
    features: list[str] = Field(..., example=[
        "hour", "day_of_week", "month", "is_weekend",
        "stop_id_encoded", "line_encoded",
        "rolling_avg_1h", "rolling_avg_24h", "rolling_avg_7d",
        "recent_trend"
    ])
