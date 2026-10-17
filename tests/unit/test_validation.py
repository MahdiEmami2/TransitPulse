"""Unit tests for data validation helpers."""
from datetime import datetime

from transitpulse.app.utils.validation import validate_delay_record


def _valid_record() -> dict:
    return {
        "stop_id": "STOP_001",
        "stop_name": "Central Station",
        "line": "U-Bahn U1",
        "direction": "North",
        "scheduled_time": datetime(2026, 10, 15, 8, 30),
        "actual_time": datetime(2026, 10, 15, 8, 35),
        "delay_minutes": 5,
        "date": datetime(2026, 10, 15).date(),
        "vehicle_id": "VEH_001",
    }


def test_valid_record_passes():
    is_valid, error = validate_delay_record(_valid_record())
    assert is_valid is True
    assert error is None


def test_missing_required_field_fails():
    record = _valid_record()
    del record["stop_id"]
    is_valid, error = validate_delay_record(record)
    assert is_valid is False
    assert "stop_id" in error


def test_empty_string_field_fails():
    record = _valid_record()
    record["line"] = ""
    is_valid, error = validate_delay_record(record)
    assert is_valid is False
    assert "line" in error


def test_delay_out_of_range_fails():
    record = _valid_record()
    record["delay_minutes"] = 500
    is_valid, error = validate_delay_record(record)
    assert is_valid is False
    assert "out of reasonable range" in error


def test_negative_delay_out_of_range_fails():
    record = _valid_record()
    record["delay_minutes"] = -120
    is_valid, error = validate_delay_record(record)
    assert is_valid is False


def test_actual_time_too_late_fails():
    record = _valid_record()
    record["actual_time"] = datetime(2026, 10, 15, 12, 0)
    is_valid, error = validate_delay_record(record)
    assert is_valid is False
    assert "3 hours" in error


def test_actual_time_too_early_fails():
    record = _valid_record()
    record["actual_time"] = datetime(2026, 10, 15, 7, 0)
    is_valid, error = validate_delay_record(record)
    assert is_valid is False
    assert "before scheduled_time" in error


def test_delay_not_integer_fails():
    record = _valid_record()
    record["delay_minutes"] = "five"
    is_valid, error = validate_delay_record(record)
    assert is_valid is False
    assert "integer" in error


def test_vehicle_id_optional():
    record = _valid_record()
    record["vehicle_id"] = None
    is_valid, error = validate_delay_record(record)
    assert is_valid is True
