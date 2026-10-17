"""Delay history API endpoints."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.api.deps import get_db_session
from transitpulse.app.database import AsyncSession as AsyncSessionType
from transitpulse.app.models.delay import DelayRecord
from transitpulse.app.schemas.delay import (
    DelayRecordCreate,
    DelayRecordList,
    DelayRecord as DelayRecordResponse,
)
from transitpulse.app.schemas.analytics import DelayStatistics, DelayDistribution, DelayTrends, TopDelayed
from transitpulse.app.services.analytics import (
    get_delay_statistics,
    get_delay_distribution,
    get_delay_trends,
    get_top_delayed,
)

router = APIRouter()


@router.get("/", response_model=DelayRecordList)
async def list_delays(
    db: AsyncSessionType = Depends(get_db_session),
    stop_id: Optional[str] = Query(None),
    line: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
):
    """
    List delay records with optional filters and pagination.

    Returns paginated delay records matching the given filters.
    """
    query = select(DelayRecord)
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

    # Count total
    count_query = select(func.count(DelayRecord.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size).order_by(DelayRecord.created_at.desc())

    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + size - 1) // size if total else 0

    return DelayRecordList(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/stats", response_model=DelayStatistics)
async def delay_statistics(
    db: AsyncSessionType = Depends(get_db_session),
    stop_id: Optional[str] = Query(None),
    line: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """
    Return delay statistics (mean, median, min, max, std dev, percentiles)
    for a given stop/line/date range.
    """
    stats = await get_delay_statistics(db, stop_id, line, start_date, end_date)
    return DelayStatistics(**stats)


@router.get("/distribution", response_model=DelayDistribution)
async def delay_distribution(
    db: AsyncSessionType = Depends(get_db_session),
    stop_id: Optional[str] = Query(None),
    line: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    bin_size: int = Query(5, ge=1, le=60),
    range_min: int = Query(-20, ge=-100),
    range_max: int = Query(60, le=300),
):
    """
    Return delay distribution histogram data.
    """
    bins = await get_delay_distribution(
        db, stop_id, line, start_date, end_date, bin_size, range_min, range_max
    )
    return DelayDistribution(bins=bins)


@router.get("/trends", response_model=DelayTrends)
async def delay_trends(
    db: AsyncSessionType = Depends(get_db_session),
    stop_id: Optional[str] = Query(None),
    line: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    period: str = Query("day", pattern="^(day|week|month)$"),
):
    """
    Return delay trends over time (daily/weekly/monthly aggregates).
    """
    trends = await get_delay_trends(db, stop_id, line, start_date, end_date, period)
    return DelayTrends(trends=trends)


@router.get("/top", response_model=TopDelayed)
async def top_delayed(
    db: AsyncSessionType = Depends(get_db_session),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    group_by: str = Query("stop", pattern="^(stop|line)$"),
):
    """
    Return top N most delayed stops or lines for a period.
    """
    items = await get_top_delayed(db, start_date, end_date, limit, group_by)
    return TopDelayed(items=items)


@router.post("/", response_model=DelayRecordResponse, status_code=201)
async def create_delay(
    delay_in: DelayRecordCreate,
    db: AsyncSessionType = Depends(get_db_session),
):
    """Create a single delay record."""
    db_obj = DelayRecord(**delay_in.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
