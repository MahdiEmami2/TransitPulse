"""CLI for training the delay prediction model.

Usage:
    python -m transitpulse.app.ml.train [--days N] [--output PATH] [--evaluate]

Trains the model on the delay records stored in the database, persists the
fitted model to ``settings.model_path``, and prints the evaluation metrics.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
from typing import Optional

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine

from transitpulse.app.config import settings
from transitpulse.app.database import Base, init_db
from transitpulse.app.ml.model import DelayPredictionModel
from transitpulse.app.models.delay import DelayRecord

logger = logging.getLogger("transitpulse.train")


async def load_delay_records(
    engine_url: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Load delay records from the database into a DataFrame."""
    engine = create_async_engine(engine_url, echo=False)
    try:
        async with engine.begin() as conn:
            # Ensure tables exist (no-op if already created)
            await conn.run_sync(Base.metadata.create_all)

            query = select(
                DelayRecord.stop_id,
                DelayRecord.line,
                DelayRecord.scheduled_time,
                DelayRecord.actual_time,
                DelayRecord.delay_minutes,
                DelayRecord.service_date,
                DelayRecord.direction,
            )
            conditions = []
            if start_date:
                conditions.append(DelayRecord.service_date >= start_date)
            if end_date:
                conditions.append(DelayRecord.service_date <= end_date)
            if conditions:
                query = query.where(*conditions)

            result = await conn.execute(query)
            rows = [
                {
                    "stop_id": r.stop_id,
                    "line": r.line,
                    "scheduled_time": r.scheduled_time,
                    "actual_time": r.actual_time,
                    "delay_minutes": r.delay_minutes,
                    "service_date": r.service_date,
                    "direction": r.direction,
                }
                for r in result.fetchall()
            ]
    finally:
        await engine.dispose()

    return pd.DataFrame(rows)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Train the delay prediction model")
    parser.add_argument(
        "--days",
        type=int,
        default=settings.synthetic_data_days,
        help="Number of days of historical data to include",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to persist the trained model (default: settings.model_path)",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Print a per-day breakdown of the evaluation metrics",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of the data reserved for testing",
    )
    args = parser.parse_args()

    end = datetime.date.today()
    start = end - datetime.timedelta(days=args.days)

    logger.info("Loading delay records from %s to %s", start, end)
    df = await load_delay_records(
        settings.database_url, start_date=start.isoformat(), end_date=end.isoformat()
    )

    if df.empty:
        logger.warning("No delay records found in the database; training aborted")
        return 1

    logger.info("Loaded %d delay records", len(df))

    model = DelayPredictionModel.train(df, test_size=args.test_size)
    model.dump(args.output)

    metrics = model.metadata
    logger.info(
        "Trained %s on %d samples (test: %d)",
        metrics["algorithm"],
        metrics["n_train"],
        metrics["n_test"],
    )
    logger.info(
        "MAE=%.3f RMSE=%.3f R2=%.3f", metrics["mae"], metrics["rmse"], metrics["r2"]
    )

    if args.evaluate:
        breakdown = (
            df.assign(day=df["service_date"])
            .groupby("day")
            .size()
            .rename("records")
            .to_frame()
        )
        logger.info("Records per day:\n%s", breakdown.to_string())

    print(json.dumps(metrics, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
