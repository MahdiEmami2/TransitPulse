"""Delay prediction service and API-facing prediction helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

import pickle
import statistics

import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.config import settings
from transitpulse.app.ml.features import build_prediction_features
from transitpulse.app.ml.model import DelayPredictionModel, train_model
from transitpulse.app.models.delay import DelayRecord
from transitpulse.app.schemas.prediction import PredictionResponse


class PredictionService:
    """Service for delay prediction using a trained ML model."""

    def __init__(self):
        self.model_name = "delay_predictor_v1"
        self.model_version = "1.0.0"
        self._model: Optional[DelayPredictionModel] = None

    @property
    def model(self) -> DelayPredictionModel:
        """Lazy-load the persisted model, training one if needed."""
        if self._model is None:
            try:
                self._model = DelayPredictionModel.load()
            except (FileNotFoundError, pickle.UnpicklingError, ValueError, EOFError):
                self._model = None
        if self._model is None:
            raise RuntimeError(
                "No trained model available. Run "
                "`python -m transitpulse.app.ml.train` first."
            )
        return self._model

    @model.setter
    def model(self, value: Optional[DelayPredictionModel]) -> None:
        self._model = value

    async def get_recent_delays(
        self,
        db: AsyncSession,
        stop_id: str,
        line: str,
        target_datetime: datetime,
        lookback_hours: int = 24 * 7,  # Last 7 days by default
    ) -> list[float]:
        """
        Get recent delay minutes for similar conditions.

        Similar conditions: same stop, line, and similar time of day/day of week.
        """
        start_time = target_datetime - timedelta(hours=lookback_hours)
        end_time = target_datetime

        target_time = target_datetime.time()
        target_weekday = target_datetime.weekday()

        query = select(
            DelayRecord.delay_minutes,
            DelayRecord.actual_time,
        ).where(
            and_(
                DelayRecord.stop_id == stop_id,
                DelayRecord.line == line,
                DelayRecord.actual_time >= start_time,
                DelayRecord.actual_time <= end_time,
            )
        )

        result = await db.execute(query)
        rows = result.fetchall()

        if not rows:
            return []

        similar_delays = []
        for delay, actual_time in rows:
            time_diff = abs(
                (actual_time.hour * 3600 + actual_time.minute * 60)
                - (target_time.hour * 3600 + target_time.minute * 60)
            )
            if actual_time.weekday() == target_weekday and time_diff <= 3600:
                similar_delays.append(delay)

        return similar_delays

    async def predict_delay(
        self,
        db: AsyncSession,
        stop_id: str,
        line: str,
        direction: str,
        scheduled_time: datetime,
        vehicle_id: Optional[str] = None,
    ) -> PredictionResponse:
        """
        Predict delay for given conditions using the trained model.

        Falls back to the historical average of similar time periods when no
        model has been trained yet.
        """
        try:
            model = self.model
        except RuntimeError:
            return await self._fallback_prediction(
                db, stop_id, line, direction, scheduled_time
            )

        # Gather the historical records needed to build features.
        window_start = scheduled_time - timedelta(hours=168)
        history_rows = await db.execute(
            select(
                DelayRecord.stop_id,
                DelayRecord.line,
                DelayRecord.scheduled_time,
                DelayRecord.delay_minutes,
            ).where(
                and_(
                    DelayRecord.stop_id == stop_id,
                    DelayRecord.line == line,
                    DelayRecord.scheduled_time >= window_start,
                    DelayRecord.scheduled_time < scheduled_time,
                )
            )
        )
        history = pd.DataFrame(
            [
                {
                    "stop_id": r.stop_id,
                    "line": r.line,
                    "scheduled_time": r.scheduled_time,
                    "delay_minutes": r.delay_minutes,
                }
                for r in history_rows.fetchall()
            ],
            # Keep the column schema even when no history rows exist, so
            # downstream feature building can rely on ``delay_minutes``.
            columns=["stop_id", "line", "scheduled_time", "delay_minutes"],
        )

        stop_rows = await db.execute(select(DelayRecord.stop_id).distinct())
        stop_ids = [r[0] for r in stop_rows.fetchall()]
        line_rows = await db.execute(select(DelayRecord.line).distinct())
        lines = [r[0] for r in line_rows.fetchall()]

        features_df = build_prediction_features(
            stop_ids,
            lines,
            history,
            pd.Timestamp(scheduled_time),
            stop_id,
            line,
        )
        prediction = float(model.predict(features_df)[0])
        std = float(model.metadata.get("rmse", 1.0))

        return PredictionResponse(
            stop_id=stop_id,
            line=line,
            direction=direction,
            scheduled_time=scheduled_time,
            predicted_delay_minutes=max(prediction, 0.0),
            confidence_lower=max(prediction - 1.96 * std, -60.0),
            confidence_upper=min(prediction + 1.96 * std, 180.0),
            model_name=self.model_name,
            model_version=self.model_version,
        )

    async def _fallback_prediction(
        self,
        db: AsyncSession,
        stop_id: str,
        line: str,
        direction: str,
        scheduled_time: datetime,
    ) -> PredictionResponse:
        """Predict using the historical average of similar conditions."""
        similar = await self.get_recent_delays(db, stop_id, line, scheduled_time)
        if not similar:
            predicted = 0.0
            margin = 0.0
        else:
            predicted = statistics.mean(similar)
            if len(similar) >= 2:
                margin = 1.96 * statistics.stdev(similar) / (len(similar) ** 0.5)
            else:
                margin = 0.0

        return PredictionResponse(
            stop_id=stop_id,
            line=line,
            direction=direction,
            scheduled_time=scheduled_time,
            predicted_delay_minutes=predicted,
            confidence_lower=max(predicted - margin, -60.0),
            confidence_upper=min(predicted + margin, 180.0),
            model_name="historical_average_v1",
            model_version="1.0.0",
        )

    async def train(self, db: AsyncSession) -> dict:
        """
        Train a fresh model on all delay records and persist it.

        Returns the model metadata including MAE, RMSE and R2.
        """
        rows = await db.execute(select(DelayRecord))
        records = rows.scalars().all()

        if not records:
            raise RuntimeError("No delay records in the database; cannot train")

        df = pd.DataFrame(
            [
                {
                    "stop_id": r.stop_id,
                    "line": r.line,
                    "scheduled_time": r.scheduled_time,
                    "actual_time": r.actual_time,
                    "delay_minutes": r.delay_minutes,
                    "service_date": r.service_date,
                    "direction": r.direction,
                }
                for r in records
            ]
        )

        model = train_model(df)
        model.dump()
        self.model = model

        metadata = dict(model.metadata)
        metadata["status"] = "trained"
        return metadata

    async def get_model_info(self) -> dict:
        """Return metadata about the current prediction model."""
        try:
            metadata = dict(self.model.metadata)
        except RuntimeError:
            metadata = {
                "note": "No trained model available. Run training first.",
            }

        return {
            "name": self.model_name,
            "version": self.model_version,
            "algorithm": metadata.get("algorithm", "untrained"),
            "trained_at": metadata.get("trained_at"),
            "metrics": {
                "mae": metadata.get("mae"),
                "rmse": metadata.get("rmse"),
                "r2": metadata.get("r2"),
            },
            "features": metadata.get("features", []),
        }


# Singleton instance
prediction_service = PredictionService()


async def predict_delay(
    db: AsyncSession,
    stop_id: str,
    line: str,
    direction: str,
    scheduled_time: datetime,
    vehicle_id: Optional[str] = None,
) -> PredictionResponse:
    """Convenience function for delay prediction."""
    return await prediction_service.predict_delay(
        db, stop_id, line, direction, scheduled_time, vehicle_id
    )


async def get_model_info() -> dict:
    """Convenience function to get model info."""
    return await prediction_service.get_model_info()


async def train_model_endpoint(db: AsyncSession) -> dict:
    """Convenience function to trigger model training."""
    return await prediction_service.train(db)
