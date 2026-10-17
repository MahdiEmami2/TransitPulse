"""Data validation helpers for delay records."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional


def validate_delay_record(record: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate a delay record dict before ingestion.

    Checks required fields, data types, and reasonable value ranges.

    Returns:
        (is_valid, error_message). If valid, error_message is None.
    """
    required_fields = [
        "stop_id",
        "stop_name",
        "line",
        "direction",
        "scheduled_time",
        "actual_time",
        "delay_minutes",
        "date",
    ]

    # Check required fields present and non-empty
    for field in required_fields:
        value = record.get(field)
        if value is None or value == "":
            return False, f"Missing required field: {field}"

    # Type checks
    if not isinstance(record["stop_id"], str):
        return False, "stop_id must be a string"
    if not isinstance(record["stop_name"], str):
        return False, "stop_name must be a string"
    if not isinstance(record["line"], str):
        return False, "line must be a string"
    if not isinstance(record["direction"], str):
        return False, "direction must be a string"
    if not isinstance(record["scheduled_time"], datetime):
        return False, "scheduled_time must be a datetime"
    if not isinstance(record["actual_time"], datetime):
        return False, "actual_time must be a datetime"
    if not isinstance(record["delay_minutes"], int) or isinstance(
        record["delay_minutes"], bool
    ):
        return False, "delay_minutes must be an integer"
    if not isinstance(record["date"], date):
        return False, "date must be a date"

    # Optional vehicle_id
    vehicle_id = record.get("vehicle_id")
    if vehicle_id is not None and not isinstance(vehicle_id, str):
        return False, "vehicle_id must be a string or None"

    # Reasonable ranges
    delay = record["delay_minutes"]
    if delay < -60 or delay > 180:
        return False, f"delay_minutes {delay} out of reasonable range [-60, 180]"

    # actual_time should not be unreasonably far from scheduled_time
    scheduled = record["scheduled_time"]
    actual = record["actual_time"]
    diff_minutes = (actual - scheduled).total_seconds() / 60
    if diff_minutes > 180:
        return False, "actual_time is more than 3 hours after scheduled_time"
    if diff_minutes < -30:
        return False, "actual_time is more than 30 minutes before scheduled_time"

    return True, None
