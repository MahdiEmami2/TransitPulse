"""Data ingestion and validation service."""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from typing import List, Tuple

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.models.delay import DelayRecord
from transitpulse.app.schemas.delay import DelayRecordCreate
from transitpulse.app.utils.validation import validate_delay_record


async def ingest_csv_data(
    csv_content: str | bytes,
    db: AsyncSession,
    batch_size: int = 1000,
) -> Tuple[int, int, List[str]]:
    """
    Ingest delay data from CSV content.

    Returns:
        Tuple of (rows_processed, rows_inserted, errors)
    """
    if isinstance(csv_content, bytes):
        csv_content = csv_content.decode("utf-8")

    # Use pandas for robust CSV parsing
    df = pd.read_csv(io.StringIO(csv_content))

    # Expected columns
    expected_columns = {
        "stop_id",
        "stop_name",
        "line",
        "direction",
        "scheduled_time",
        "actual_time",
        "delay_minutes",
        "date",
        "vehicle_id",
    }

    # Check for missing columns
    missing_columns = expected_columns - set(df.columns)
    if missing_columns:
        return 0, 0, [f"Missing columns: {missing_columns}"]

    # Convert date columns to datetime if needed. ``errors="coerce"`` turns
    # unparseable timestamps into NaT so the per-row validation reports a
    # useful error message instead of the whole ingestion failing with a 500.
    df["scheduled_time"] = pd.to_datetime(df["scheduled_time"], errors="coerce")
    df["actual_time"] = pd.to_datetime(df["actual_time"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    rows_processed = 0
    rows_inserted = 0
    errors: List[str] = []

    # Process in batches
    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i : i + batch_size]
        batch_records = []

        for _, row in batch_df.iterrows():
            rows_processed += 1
            try:
                # Validate record
                record_data = {
                    "stop_id": row["stop_id"],
                    "stop_name": row["stop_name"],
                    "line": row["line"],
                    "direction": row["direction"],
                    "scheduled_time": row["scheduled_time"].to_pydatetime(),
                    "actual_time": row["actual_time"].to_pydatetime(),
                    "delay_minutes": int(row["delay_minutes"]),
                    "date": row["date"],
                    "vehicle_id": (
                        row["vehicle_id"] if pd.notna(row["vehicle_id"]) else None
                    ),
                }

                # Use validation utility
                is_valid, error_msg = validate_delay_record(record_data)
                if not is_valid:
                    errors.append(f"Row {rows_processed}: {error_msg}")
                    continue

                # Create Pydantic model (optional, but ensures type safety)
                delay_record = DelayRecordCreate(**record_data)
                batch_records.append(delay_record)

            except Exception as e:
                errors.append(f"Row {rows_processed}: {str(e)}")

        # Insert batch into database
        if batch_records:
            try:
                db_objs = [
                    DelayRecord(**record.model_dump()) for record in batch_records
                ]
                db.add_all(db_objs)
                await db.flush()
                rows_inserted += len(batch_records)
            except Exception as e:
                await db.rollback()
                errors.append(f"Batch insert failed: {str(e)}")
                # Optionally, try inserting one by one to isolate bad rows
                # For simplicity, we skip the batch on error
                continue

    await db.commit()
    return rows_processed, rows_inserted, errors


async def ingest_from_file(
    file_path: str,
    db: AsyncSession,
    batch_size: int = 1000,
) -> Tuple[int, int, List[str]]:
    """
    Ingest delay data from a CSV file.

    Returns:
        Tuple of (rows_processed, rows_inserted, errors)
    """
    with open(file_path, "rb") as f:
        content = f.read()
    return await ingest_csv_data(content, db, batch_size)


def generate_sample_data(
    num_rows: int = 1000,
    start_date: str = "2026-01-01",
    end_date: str = "2026-12-31",
) -> str:
    """
    Generate synthetic delay data as CSV string.

    Returns:
        CSV string with synthetic data
    """
    import numpy as np

    np.random.seed(42)  # for reproducibility

    # Generate dates
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    dates = np.random.choice(date_range, size=num_rows)

    # Generate stops and lines
    stop_ids = [f"STOP_{i:03d}" for i in range(1, 21)]
    stop_names = {
        f"STOP_{i:03d}": f"Stop {i}"
        for i in range(1, 21)
    }
    line_ids = [f"LINE_{i:02d}" for i in range(1, 11)]
    directions = ["North", "South", "East", "West"]

    data = []
    for _ in range(num_rows):
        stop_id = np.random.choice(stop_ids)
        line = np.random.choice(line_ids)
        direction = np.random.choice(directions)
        scheduled = pd.Timestamp(np.random.choice(dates))
        # Add some delay (mostly small, occasional large delays)
        delay = int(np.random.normal(loc=2, scale=5))
        # Clip delay to reasonable range
        delay = max(-10, min(delay, 60))
        actual = scheduled + pd.Timedelta(minutes=delay)
        vehicle_id = f"VEH_{np.random.randint(1, 50):03d}" if np.random.rand() > 0.2 else None

        data.append(
            {
                "stop_id": stop_id,
                "stop_name": stop_names[stop_id],
                "line": line,
                "direction": direction,
                "scheduled_time": scheduled,
                "actual_time": actual,
                "delay_minutes": delay,
                "date": scheduled.date(),
                "vehicle_id": vehicle_id,
            }
        )

    df = pd.DataFrame(data)
    # Reorder columns
    df = df[
        [
            "stop_id",
            "stop_name",
            "line",
            "direction",
            "scheduled_time",
            "actual_time",
            "delay_minutes",
            "date",
            "vehicle_id",
        ]
    ]
    return df.to_csv(index=False)
