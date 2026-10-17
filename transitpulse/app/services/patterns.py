"""Delay pattern detection service."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import List, Optional

import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.models.delay import DelayRecord


async def detect_rush_hour_patterns(
    db: AsyncSession,
    stop_id: Optional[str] = None,
    line: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """
    Detect rush hour patterns (morning and evening peaks).

    Returns:
        Dict with pattern info and confidence score (0.0-1.0)
    """
    query = select(DelayRecord.delay_minutes, DelayRecord.actual_time)
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

    result = await db.execute(query)
    rows = result.fetchall()

    if not rows:
        return {
            "pattern_type": "rush_hour",
            "description": "No data available for rush hour analysis",
            "confidence": 0.0,
            "details": {},
        }

    delays = [r[0] for r in rows]
    times = [r[1] for r in rows]

    # Extract hour from actual_time
    hours = [t.hour for t in times]

    # Define rush hour periods (7-9 AM, 5-7 PM)
    rush_hour_mask = np.array([(7 <= h <= 9) or (17 <= h <= 19) for h in hours])
    off_peak_mask = ~rush_hour_mask

    if not np.any(rush_hour_mask) or not np.any(off_peak_mask):
        return {
            "pattern_type": "rush_hour",
            "description": "Insufficient data for rush hour comparison",
            "confidence": 0.0,
            "details": {
                "total_samples": len(delays),
                "rush_hour_samples": int(np.sum(rush_hour_mask)),
                "off_peak_samples": int(np.sum(off_peak_mask)),
            },
        }

    rush_hour_delays = np.array(delays)[rush_hour_mask]
    off_peak_delays = np.array(delays)[off_peak_mask]

    rush_hour_mean = np.mean(rush_hour_delays)
    off_peak_mean = np.mean(off_peak_delays)

    # Calculate confidence based on relative increase
    if off_peak_mean > 0:
        relative_increase = (rush_hour_mean - off_peak_mean) / off_peak_mean
        confidence = min(0.95, max(0.0, relative_increase / 2.0))  # Cap at 95%
    else:
        confidence = 0.0

    return {
        "pattern_type": "rush_hour",
        "description": f"Rush hour delays are {rush_hour_mean:.1f} min vs {off_peak_mean:.1f} min off-peak",
        "confidence": float(confidence),
        "details": {
            "rush_hour_mean": float(rush_hour_mean),
            "off_peak_mean": float(off_peak_mean),
            "difference": float(rush_hour_mean - off_peak_mean),
            "rush_hour_count": int(len(rush_hour_delays)),
            "off_peak_count": int(len(off_peak_delays)),
        },
    }


async def detect_weekend_weekday_patterns(
    db: AsyncSession,
    stop_id: Optional[str] = None,
    line: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """
    Detect weekend vs weekday delay patterns.

    Returns:
        Dict with pattern info and confidence score (0.0-1.0)
    """
    query = select(DelayRecord.delay_minutes, DelayRecord.actual_time)
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

    result = await db.execute(query)
    rows = result.fetchall()

    if not rows:
        return {
            "pattern_type": "weekend_vs_weekday",
            "description": "No data available for weekend/weekday analysis",
            "confidence": 0.0,
            "details": {},
        }

    delays = [r[0] for r in rows]
    dates = [r[1].date() for r in rows]  # Extract date from datetime

    # Separate weekend (Sat=5, Sun=6) vs weekday (Mon-Fri=0-4)
    weekend_mask = np.array([d.weekday() >= 5 for d in dates])
    weekday_mask = ~weekend_mask

    if not np.any(weekend_mask) or not np.any(weekday_mask):
        return {
            "pattern_type": "weekend_vs_weekday",
            "description": "Insufficient data for weekend/weekday comparison",
            "confidence": 0.0,
            "details": {
                "total_samples": len(delays),
                "weekend_samples": int(np.sum(weekend_mask)),
                "weekday_samples": int(np.sum(weekday_mask)),
            },
        }

    weekend_delays = np.array(delays)[weekend_mask]
    weekday_delays = np.array(delays)[weekday_mask]

    weekend_mean = np.mean(weekend_delays)
    weekday_mean = np.mean(weekday_delays)

    # Calculate confidence based on difference
    if weekday_mean > 0:
        relative_difference = abs(weekend_mean - weekday_mean) / weekday_mean
        confidence = min(0.95, max(0.0, relative_difference / 2.0))  # Cap at 95%
    else:
        confidence = 0.0

    return {
        "pattern_type": "weekend_vs_weekday",
        "description": f"Weekend delays: {weekend_mean:.1f} min, Weekday delays: {weekday_mean:.1f} min",
        "confidence": float(confidence),
        "details": {
            "weekend_mean": float(weekend_mean),
            "weekday_mean": float(weekday_mean),
            "difference": float(weekend_mean - weekday_mean),
            "weekend_count": int(len(weekend_delays)),
            "weekday_count": int(len(weekday_delays)),
        },
    }


async def detect_line_chronic_patterns(
    db: AsyncSession,
    stop_id: Optional[str] = None,
    line: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_samples: int = 10,
) -> dict:
    """
    Detect lines with chronic (consistently high) delays.

    Returns:
        Dict with pattern info and confidence score (0.0-1.0)
    """
    query = select(DelayRecord.delay_minutes, DelayRecord.line)
    conditions = []

    if line:
        conditions.append(DelayRecord.line == line)

    if stop_id:
        conditions.append(DelayRecord.stop_id == stop_id)
    if start_date:
        conditions.append(DelayRecord.service_date >= start_date)
    if end_date:
        conditions.append(DelayRecord.service_date <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    rows = result.fetchall()

    if not rows:
        return {
            "pattern_type": "line_chronic",
            "description": "No data available for line chronic analysis",
            "confidence": 0.0,
            "details": {},
        }

    delays = [r[0] for r in rows]
    lines = [r[1] for r in rows]

    # Group by line to find worst offender
    line_groups: dict[str, List[float]] = {}
    for delay, line_id in zip(delays, lines):
        if line_id not in line_groups:
            line_groups[line_id] = []
        line_groups[line_id].append(delay)

    # Find line with highest average delay (minimum samples)
    worst_line = None
    worst_avg = -float("inf")
    worst_count = 0

    for line_id, line_delays in line_groups.items():
        if len(line_delays) >= min_samples:
            avg_delay = np.mean(line_delays)
            if avg_delay > worst_avg:
                worst_avg = avg_delay
                worst_line = line_id
                worst_count = len(line_delays)

    if worst_line is None:
        return {
            "pattern_type": "line_chronic",
            "description": f"No line with sufficient samples (min {min_samples})",
            "confidence": 0.0,
            "details": {
                "lines_analyzed": list(line_groups.keys()),
                "min_samples_required": min_samples,
            },
        }

    line_delays = np.array(line_groups[worst_line])
    other_lines_delays = np.concatenate(
        [np.array(line_groups[l]) for l in line_groups if l != worst_line]
    )

    if len(other_lines_delays) < 2:
        # No other lines to compare against
        return {
            "pattern_type": "line_chronic",
            "description": f"Line '{worst_line}' has highest delay {worst_avg:.1f} min but no other lines to compare",
            "confidence": 0.5,
            "details": {
                "line_id": worst_line,
                "line_mean": float(np.mean(line_delays)),
                "line_sample_count": len(line_delays),
                "other_sample_count": 0,
            },
        }

    line_mean = np.mean(line_delays)
    other_mean = np.mean(other_lines_delays)

    if other_mean > 0:
        relative_increase = (line_mean - other_mean) / other_mean
        confidence = min(0.95, max(0.0, relative_increase / 3.0))  # More conservative
    else:
        confidence = 0.0

    return {
        "pattern_type": "line_chronic",
        "description": f"Line '{worst_line}' shows chronic delays: {line_mean:.1f} min vs {other_mean:.1f} min average",
        "confidence": float(confidence),
        "details": {
            "line_id": worst_line,
            "line_mean": float(line_mean),
            "other_lines_mean": float(other_mean),
            "difference": float(line_mean - other_mean),
            "line_sample_count": len(line_delays),
            "other_sample_count": len(other_lines_delays),
        },
    }


async def get_all_patterns(
    db: AsyncSession,
    stop_id: Optional[str] = None,
    line: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[dict]:
    """
    Run all pattern detection algorithms and return results.

    Returns:
        List of pattern detection results
    """
    patterns = []

    # Run all three pattern detectors
    rush_hour = await detect_rush_hour_patterns(db, stop_id, line, start_date, end_date)
    patterns.append(rush_hour)

    weekend_weekday = await detect_weekend_weekday_patterns(
        db, stop_id, line, start_date, end_date
    )
    patterns.append(weekend_weekday)

    line_chronic = await detect_line_chronic_patterns(
        db, stop_id, line, start_date, end_date
    )
    patterns.append(line_chronic)

    return patterns