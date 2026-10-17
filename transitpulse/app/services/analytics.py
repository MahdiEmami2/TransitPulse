"""Delay analytics service."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.models.delay import DelayRecord


async def get_delay_statistics(
    db: AsyncSession,
    stop_id: Optional[str] = None,
    line: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """
    Calculate delay statistics for given filters.

    Returns:
        Dictionary with count, mean, median, min, max, std_dev, percentiles
    """
    # Build query
    query = select(DelayRecord.delay_minutes)
    conditions = []

    if stop_id:
        conditions.append(DelayRecord.stop_id == stop_id)
    if line:
        conditions.append(DelayRecord.line == line)
    if start_date:
        conditions.append(DelayRecord.service_date >= start_date)
    if end_date:
        conditions.append(DelayRecord.service_date <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    # Execute query
    result = await db.execute(query)
    delays = [row[0] for row in result.fetchall()]

    if not delays:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "min": 0,
            "max": 0,
            "std_dev": 0.0,
            "p10": 0.0,
            "p25": 0.0,
            "p75": 0.0,
            "p90": 0.0,
        }

    delays_array = np.array(delays)
    return {
        "count": int(len(delays)),
        "mean": float(np.mean(delays_array)),
        "median": float(np.median(delays_array)),
        "min": int(np.min(delays_array)),
        "max": int(np.max(delays_array)),
        "std_dev": float(np.std(delays_array)),
        "p10": float(np.percentile(delays_array, 10)),
        "p25": float(np.percentile(delays_array, 25)),
        "p75": float(np.percentile(delays_array, 75)),
        "p90": float(np.percentile(delays_array, 90)),
    }


async def get_delay_distribution(
    db: AsyncSession,
    stop_id: Optional[str] = None,
    line: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    bin_size: int = 5,
    range_min: int = -20,
    range_max: int = 60,
) -> List[dict]:
    """
    Get delay distribution histogram data.

    Returns:
        List of bins with range_start, range_end, count
    """
    # Build query
    query = select(DelayRecord.delay_minutes)
    conditions = []

    if stop_id:
        conditions.append(DelayRecord.stop_id == stop_id)
    if line:
        conditions.append(DelayRecord.line == line)
    if start_date:
        conditions.append(DelayRecord.service_date >= start_date)
    if end_date:
        conditions.append(DelayRecord.service_date <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    # Execute query
    result = await db.execute(query)
    delays = [row[0] for row in result.fetchall()]

    if not delays:
        return []

    # Create histogram bins
    bins = []
    current = range_min
    while current < range_max:
        bin_start = current
        bin_end = current + bin_size
        count = sum(1 for d in delays if bin_start <= d < bin_end)
        bins.append(
            {
                "range_start": bin_start,
                "range_end": bin_end,
                "count": count,
            }
        )
        current = bin_end

    return bins


async def get_delay_trends(
    db: AsyncSession,
    stop_id: Optional[str] = None,
    line: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period: str = "day",  # day, week, month
) -> List[dict]:
    """
    Get delay trends over time.

    Returns:
        List of periods with count and mean_delay
    """
    # Build query
    query = select(
        DelayRecord.service_date,
        func.count(DelayRecord.id).label("count"),
        func.avg(DelayRecord.delay_minutes).label("mean_delay"),
    )
    conditions = []

    if stop_id:
        conditions.append(DelayRecord.stop_id == stop_id)
    if line:
        conditions.append(DelayRecord.line == line)
    if start_date:
        conditions.append(DelayRecord.service_date >= start_date)
    if end_date:
        conditions.append(DelayRecord.service_date <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    # Group by period. ``to_char`` is PostgreSQL-only, so the grouping
    # expression is chosen per-dialect to keep the documented SQLite
    # development fallback working.
    is_sqlite = db.bind is not None and db.bind.dialect.name == "sqlite"
    if period == "day":
        group_by = DelayRecord.service_date
    elif period == "week":
        group_by = (
            func.strftime("%Y-%W", DelayRecord.service_date)
            if is_sqlite
            else func.to_char(DelayRecord.service_date, "IYYY-IW")
        )
    elif period == "month":
        group_by = (
            func.strftime("%Y-%m", DelayRecord.service_date)
            if is_sqlite
            else func.to_char(DelayRecord.service_date, "YYYY-MM")
        )
    else:
        group_by = DelayRecord.service_date

    query = query.group_by(group_by).order_by(group_by)

    # Execute query
    result = await db.execute(query)
    trends = []
    for row in result.fetchall():
        trends.append(
            {
                "period": str(row[0]),
                "count": int(row[1]),
                "mean_delay": float(row[2]) if row[2] is not None else 0.0,
            }
        )

    return trends


async def get_top_delayed(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 10,
    group_by: str = "stop",  # stop or line
) -> List[dict]:
    """
    Get top N most delayed stops or lines.

    Returns:
        List of items with key, name, count, mean_delay, max_delay
    """
    # Determine grouping column
    if group_by == "stop":
        group_col = DelayRecord.stop_id
        name_col = DelayRecord.stop_name
    else:  # line
        group_col = DelayRecord.line
        name_col = DelayRecord.line  # line name is same as line ID for simplicity

    # Build query
    query = select(
        group_col.label("key"),
        name_col.label("name"),
        func.count(DelayRecord.id).label("count"),
        func.avg(DelayRecord.delay_minutes).label("mean_delay"),
        func.max(DelayRecord.delay_minutes).label("max_delay"),
    )
    conditions = []

    if start_date:
        conditions.append(DelayRecord.service_date >= start_date)
    if end_date:
        conditions.append(DelayRecord.service_date <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.group_by(group_col, name_col)
    query = query.order_by(func.avg(DelayRecord.delay_minutes).desc())
    query = query.limit(limit)

    # Execute query
    result = await db.execute(query)
    top_items = []
    for row in result.fetchall():
        top_items.append(
            {
                "key": str(row[0]),
                "name": str(row[1]),
                "count": int(row[2]),
                "mean_delay": float(row[3]) if row[3] is not None else 0.0,
                "max_delay": int(row[4]) if row[4] is not None else 0.0,
            }
        )

    return top_items
