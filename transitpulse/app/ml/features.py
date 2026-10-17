"""Feature engineering for the delay prediction model.

All feature engineering happens on pandas DataFrames so that the same
transformations can be applied during training and at inference time.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _time_features(timestamp: pd.Series) -> pd.DataFrame:
    """Split a datetime series into temporal components."""
    return pd.DataFrame(
        {
            "hour": timestamp.dt.hour,
            "day_of_week": timestamp.dt.dayofweek,
            "month": timestamp.dt.month,
            "is_weekend": timestamp.dt.dayofweek.isin([5, 6]).astype(int),
        },
        index=timestamp.index,
    )


def encode_categorical(series: pd.Series) -> pd.Series:
    """Encode a categorical column as integer codes, unknown -> -1."""
    return series.astype("category").cat.codes.astype(int)


def build_features(
    df: pd.DataFrame,
    *,
    target: str = "delay_minutes",
    rolling_windows: tuple[int, ...] = (1, 24, 168),
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Build the feature matrix and target vector from raw delay records.

    Features
    --------
    hour, day_of_week, month, is_weekend : temporal
    stop_id_encoded, line_encoded : integer categorical encodings
    rolling_avg_<window>h : rolling mean delay over the last <window> hours
        computed per (stop_id, line) using only preceding rows, so the
        feature is available at prediction time without leaking the future.
    recent_trend : mean delay over the last 3 records for the same stop/line

    Parameters
    ----------
    df : pd.DataFrame
        Columns must include ``stop_id``, ``line``, ``scheduled_time`` and
        ``delay_minutes``. Rows should be sorted by ``scheduled_time``.
    target : str
        Column name to use as the regression target.
    rolling_windows : tuple of int
        Window sizes in hours for the rolling-average features.

    Returns
    -------
    (features, target) : tuple of (pd.DataFrame, pd.Series)
    """
    df = df.sort_values("scheduled_time").reset_index(drop=True)

    # NOTE: DataFrame.update() never adds new columns, so the temporal
    # features must be concatenated, not updated in.
    features = pd.concat([_time_features(df["scheduled_time"]), pd.DataFrame(index=df.index)], axis=1)
    features["stop_id_encoded"] = encode_categorical(df["stop_id"])
    features["line_encoded"] = encode_categorical(df["line"])

    # Rolling averages are computed per (stop, line) group over a time-based
    # window. ``min_periods=1`` keeps the first rows usable. The rolling is
    # taken on the grouped DataFrame (not a SeriesGroupBy) so that the
    # time-based ``on`` column is accepted, then shifted within each group so
    # the current row never leaks into its own feature.
    for window in rolling_windows:
        col = f"rolling_avg_{window}h"
        rolled = (
            df.groupby(["stop_id", "line"])
            .rolling(f"{window}h", on="scheduled_time", min_periods=1)["delay_minutes"]
            .mean()
        )
        features[col] = (
            rolled.groupby(level=[0, 1])
            .transform(lambda s: s.shift(1).ffill().fillna(0.0))
            .to_numpy()
        )

    # Recent trend: mean of the last 3 delays for the same stop/line.
    features["recent_trend"] = (
        df.groupby(["stop_id", "line"])["delay_minutes"]
        .rolling(3, min_periods=1)
        .mean()
        .groupby(level=[0, 1])
        .transform(lambda s: s.shift(1).ffill().fillna(0.0))
        .to_numpy()
    )

    return features, df[target].astype(float)


def build_prediction_features(
    stop_ids: list[str],
    lines: list[str],
    recent_history: pd.DataFrame,
    target_datetime: pd.Timestamp,
    target_stop_id: str,
    target_line: str,
) -> pd.DataFrame:
    """
    Build features for a single prediction request.

    ``stop_ids`` and ``lines`` are the distinct stop/line values present in the
    database; they are used to derive the categorical encodings so an unseen
    stop/line maps to the same -1 the model saw during training.
    ``recent_history`` is the recent delay history for the requested stop/line,
    used for rolling features.
    """
    row = {
        "hour": target_datetime.hour,
        "day_of_week": target_datetime.dayofweek,
        "month": target_datetime.month,
        "is_weekend": int(target_datetime.dayofweek in (5, 6)),
    }

    row["stop_id_encoded"] = _encode_known(stop_ids, target_stop_id)
    row["line_encoded"] = _encode_known(lines, target_line)

    for window in (1, 24, 168):
        row[f"rolling_avg_{window}h"] = _rolling_mean(
            recent_history, window, target_datetime
        )
    # An empty history has no trailing records; fall back to 0.0 so the
    # feature row never contains NaN (sklearn rejects NaN input).
    row["recent_trend"] = (
        float(recent_history["delay_minutes"].tail(3).mean())
        if not recent_history.empty
        else 0.0
    )

    return pd.DataFrame([row])


def _encode_known(values: list, target: str) -> int:
    """Encode a value using the categories present in the training data."""
    if not values:
        return -1
    series = pd.Series(values).astype("category")
    if target not in series.cat.categories:
        return -1
    return int(series.cat.categories.get_loc(target))


def _rolling_mean(history: pd.DataFrame, window_hours: int, target: pd.Timestamp) -> float:
    """Mean delay within the trailing time window."""
    if history.empty:
        return 0.0
    cutoff = target - pd.Timedelta(hours=window_hours)
    recent = history[(history["scheduled_time"] >= cutoff) & (history["scheduled_time"] < target)]
    if recent.empty:
        return 0.0
    return float(recent["delay_minutes"].mean())
