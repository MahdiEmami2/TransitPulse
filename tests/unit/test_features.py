"""Unit tests for ML feature engineering and the model wrapper."""
import numpy as np
import pandas as pd
import pytest

from transitpulse.app.ml.features import (
    build_features,
    build_prediction_features,
    encode_categorical,
)


def _sample_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.RandomState(42)
    return pd.DataFrame(
        {
            "stop_id": rng.choice(["S1", "S2"], n),
            "line": rng.choice(["L1", "L2"], n),
            "scheduled_time": pd.date_range("2026-01-01", periods=n, freq="h"),
            "delay_minutes": rng.randint(-5, 30, n),
        }
    )


def test_build_features_expected_columns():
    X, y = build_features(_sample_df())
    expected = [
        "hour",
        "day_of_week",
        "month",
        "is_weekend",
        "stop_id_encoded",
        "line_encoded",
        "rolling_avg_1h",
        "rolling_avg_24h",
        "rolling_avg_168h",
        "recent_trend",
    ]
    assert list(X.columns) == expected
    assert len(X) == len(y)
    assert X.isna().sum().sum() == 0


def test_build_features_target_is_float():
    _, y = build_features(_sample_df())
    assert y.dtype == float


def test_encode_categorical_unknown_maps_below_zero():
    series = encode_categorical(pd.Series(["a", "b", "a"]))
    assert set(series.unique()) <= {0, 1}


def test_build_prediction_features_matches_training_columns():
    df = _sample_df()
    X, _ = build_features(df)
    history = df[df["stop_id"] == "S1"].head(5)
    pred = build_prediction_features(
        ["S1", "S2"],
        ["L1", "L2"],
        history,
        pd.Timestamp("2026-01-10 08:00"),
        "S1",
        "L1",
    )
    assert list(pred.columns) == list(X.columns)


def test_build_prediction_features_unknown_stop_maps_to_minus_one():
    df = _sample_df()
    pred = build_prediction_features(
        ["S1", "S2"],
        ["L1", "L2"],
        df.head(5),
        pd.Timestamp("2026-01-10 08:00"),
        "UNKNOWN",
        "UNKNOWN",
    )
    assert pred["stop_id_encoded"].iloc[0] == -1
    assert pred["line_encoded"].iloc[0] == -1


def test_build_prediction_features_empty_history_is_zero():
    empty = pd.DataFrame(
        columns=["stop_id", "line", "scheduled_time", "delay_minutes"]
    )
    pred = build_prediction_features(
        ["S1"], ["L1"], empty, pd.Timestamp("2026-01-10 08:00"), "S1", "L1"
    )
    assert pred["rolling_avg_24h"].iloc[0] == 0.0
    assert pred["recent_trend"].iloc[0] == 0.0


def test_model_train_and_predict_roundtrip(tmp_path):
    from transitpulse.app.ml.model import DelayPredictionModel

    df = _sample_df(120)
    model = DelayPredictionModel.train(df, test_size=0.2)
    assert model.model is not None
    assert model.metadata["n_train"] > 0
    assert model.metadata["n_test"] > 0
    assert "mae" in model.metadata

    X, _ = build_features(df.head(5))
    predictions = model.predict(X)
    assert len(predictions) == 5

    path = tmp_path / "model.pkl"
    model.dump(path)
    loaded = DelayPredictionModel.load(path)
    assert list(loaded.feature_names) == list(model.feature_names)
    np.testing.assert_allclose(
        loaded.predict(X), model.predict(X), rtol=1e-6
    )


def test_model_train_on_empty_df_raises():
    from transitpulse.app.ml.model import DelayPredictionModel

    with pytest.raises(ValueError):
        DelayPredictionModel.train(pd.DataFrame())
