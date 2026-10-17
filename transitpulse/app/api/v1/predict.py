"""Prediction API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.api.deps import get_db_session
from transitpulse.app.database import AsyncSession as AsyncSessionType
from transitpulse.app.schemas.prediction import PredictionRequest, PredictionResponse, ModelInfo
from transitpulse.app.services.prediction import (
    get_model_info,
    predict_delay,
    train_model_endpoint,
)

router = APIRouter()


class ModelInfoResponse(BaseModel):
    """Metadata about the currently active model."""

    name: str
    version: str
    algorithm: str
    trained_at: Optional[datetime] = None
    metrics: dict = {}
    features: list[str] = []


class TrainResponse(BaseModel):
    """Response from the model retraining endpoint."""

    status: str
    algorithm: str
    mae: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None
    n_train: Optional[int] = None
    n_test: Optional[int] = None


@router.post("/", response_model=PredictionResponse)
async def predict_delay_endpoint(
    request: PredictionRequest,
    db: AsyncSessionType = Depends(get_db_session),
):
    """
    Predict delay for a given stop/line/time.

    Returns predicted delay in minutes with confidence interval.
    """
    return await predict_delay(
        db,
        request.stop_id,
        request.line,
        request.direction,
        request.scheduled_time,
        request.vehicle_id,
    )


@router.post("/train", response_model=TrainResponse)
async def retrain_model(
    db: AsyncSessionType = Depends(get_db_session),
):
    """
    Trigger retraining of the prediction model on all stored delay records.

    Persists the newly trained model and updates the active model used by
    ``POST /api/v1/predict``.
    """
    try:
        metadata = await train_model_endpoint(db)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TrainResponse(
        status=metadata.get("status", "trained"),
        algorithm=metadata.get("algorithm", "unknown"),
        mae=metadata.get("mae"),
        rmse=metadata.get("rmse"),
        r2=metadata.get("r2"),
        n_train=metadata.get("n_train"),
        n_test=metadata.get("n_test"),
    )


@router.get("/model/info", response_model=ModelInfoResponse)
async def model_info():
    """
    Return metadata about the currently active prediction model, including
    the evaluation metrics (MAE, RMSE, R2) from its holdout test set.
    """
    info = await get_model_info()
    return ModelInfoResponse(
        name=info["name"],
        version=info["version"],
        algorithm=info["algorithm"],
        trained_at=info.get("trained_at"),
        metrics=info.get("metrics", {}),
        features=info.get("features", []),
    )