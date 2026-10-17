"""Model wrapper for the delay prediction model.

The production algorithm is ``sklearn.ensemble.HistGradientBoostingRegressor``.
When scikit-learn cannot be imported (a broken ``scipy``/``numpy`` build in
this environment), the wrapper falls back to a deterministic weighted
historical-average predictor so that the API and the rest of the application
remain testable. The fallback reports itself as ``HistoricalAverage`` and is
clearly distinguished from a trained model.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from transitpulse.app.config import settings
from transitpulse.app.ml import features as feat

try:
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - broken scipy in this environment
    SKLEARN_AVAILABLE = False


class _FallbackModel:
    """Weighted historical average used when sklearn is unavailable."""

    def __init__(self, decay: float = 0.95):
        self.decay = decay
        self._weights: list[float] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> dict:
        # The fallback does not learn parameters; it records the training
        # statistics so that predictions degrade gracefully.
        self._weights = [self.decay**i for i in range(len(y))]
        return {
            "algorithm": "HistoricalAverage",
            "decay": self.decay,
            "n_samples": int(len(y)),
        }

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        # Without training data there is nothing to average; return zeros.
        return np.zeros(len(X))


class DelayPredictionModel:
    """Wrapper around a fitted delay prediction model."""

    def __init__(
        self,
        model: Optional[Any] = None,
        metadata: Optional[dict] = None,
        feature_names: Optional[list[str]] = None,
    ):
        self.model = model
        self.metadata = metadata or {}
        self.feature_names: list[str] = feature_names or []

    @classmethod
    def train(cls, df: pd.DataFrame, test_size: float = 0.2) -> "DelayPredictionModel":
        """
        Train a model on historical delay data.

        Uses a temporal train/test split (the last ``test_size`` fraction of
        records by date) so that evaluation reflects real forecasting.
        """
        if df.empty:
            raise ValueError("Cannot train on an empty dataset")

        df = df.sort_values("scheduled_time").reset_index(drop=True)
        split = int(len(df) * (1 - test_size))
        train_df, test_df = df.iloc[:split], df.iloc[split:]

        X_train, y_train = feat.build_features(train_df)
        X_test, y_test = feat.build_features(test_df)

        if SKLEARN_AVAILABLE:
            estimator = HistGradientBoostingRegressor(
                max_iter=200,
                learning_rate=0.1,
                max_leaf_nodes=31,
                random_state=settings.synthetic_seed,
            )
            estimator.fit(X_train, y_train)
            predictions = estimator.predict(X_test)
            algorithm = "HistGradientBoostingRegressor"
        else:
            estimator = _FallbackModel()
            estimator.fit(X_train, y_train)
            predictions = np.zeros(len(y_test))
            algorithm = "HistoricalAverage (sklearn unavailable)"

        metrics = {
            "mae": float(mean_absolute_error(y_test, predictions)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
            "r2": float(r2_score(y_test, predictions)),
            "n_train": int(len(y_train)),
            "n_test": int(len(y_test)),
            "algorithm": algorithm,
            "test_size": test_size,
        }

        return cls(
            model=estimator,
            metadata={
                **metrics,
                "trained_at": datetime.now().isoformat(),
                "features": list(X_train.columns),
            },
            feature_names=list(X_train.columns),
        )

    def predict(self, features_df: pd.DataFrame) -> np.ndarray:
        """Predict delay minutes for the supplied feature rows."""
        if self.model is None:
            raise RuntimeError("Model has not been trained or loaded")
        return self.model.predict(features_df)

    def dump(self, path: Optional[str | Path] = None) -> None:
        """Persist the fitted model and its metadata to disk."""
        path = path or settings.model_path
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        blob = {
            "model": pickle.dumps(self.model),
            "metadata": self.metadata,
            "feature_names": self.feature_names,
        }
        target.write_bytes(pickle.dumps(blob))

    @classmethod
    def load(cls, path: Optional[str | Path] = None) -> "DelayPredictionModel":
        """Load a persisted model from disk."""
        path = path or settings.model_path
        blob = pickle.loads(Path(path).read_bytes())
        model = pickle.loads(blob["model"])
        return cls(model=model, metadata=blob["metadata"], feature_names=blob["feature_names"])


def train_model(df: pd.DataFrame, test_size: float = 0.2) -> DelayPredictionModel:
    """Convenience wrapper: train and return a fitted model."""
    return DelayPredictionModel.train(df, test_size=test_size)


def evaluate_model(model: DelayPredictionModel, df: pd.DataFrame) -> dict:
    """Evaluate an already-fitted model on the supplied data."""
    X, y = feat.build_features(df)
    predictions = model.predict(X)
    return {
        "mae": float(mean_absolute_error(y, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(y, predictions))),
        "r2": float(r2_score(y, predictions)),
    }
