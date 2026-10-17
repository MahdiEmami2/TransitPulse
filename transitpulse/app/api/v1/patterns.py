"""Pattern detection API endpoints."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.api.deps import get_db_session
from transitpulse.app.database import AsyncSession as AsyncSessionType
from transitpulse.app.services.patterns import get_all_patterns

router = APIRouter()


class PatternResult(BaseModel):
    """A single detected pattern."""

    pattern_type: str  # e.g., "rush_hour", "weekend_vs_weekday", "line_chronic"
    description: str
    confidence: float  # 0.0 to 1.0
    details: dict


class PatternsResponse(BaseModel):
    """Response containing detected patterns."""

    patterns: list[PatternResult]
    analyzed_at: str  # ISO timestamp
    filters_applied: dict


@router.get("/", response_model=PatternsResponse)
async def get_patterns(
    db: AsyncSessionType = Depends(get_db_session),
    stop_id: Optional[str] = Query(None),
    line: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """
    Detect delay patterns for given filters.

    Returns detected patterns with confidence scores.
    Pattern types include:
    - rush_hour: delays during morning/evening peaks
    - weekend_vs_weekday: difference between weekend and weekday delays
    - line_chronic: lines with consistently high delays
    """
    patterns = await get_all_patterns(db, stop_id, line, start_date, end_date)

    filters_applied = {
        "stop_id": stop_id,
        "line": line,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }

    return PatternsResponse(
        patterns=patterns,
        analyzed_at=datetime.now().isoformat(),
        filters_applied=filters_applied,
    )