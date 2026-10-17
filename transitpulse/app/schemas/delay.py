"""Pydantic schemas for delay data."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class DelayRecordBase(BaseModel):
    """Base delay record schema."""

    stop_id: str = Field(..., example="STOP_123")
    stop_name: str = Field(..., example="Central Station")
    line: str = Field(..., example="U-Bahn U1")
    direction: str = Field(..., example="North")
    scheduled_time: datetime = Field(..., example="2026-10-15T08:30:00")
    actual_time: datetime = Field(..., example="2026-10-15T08:35:00")
    delay_minutes: int = Field(..., example=5)
    # The field is named ``service_date`` rather than ``date``: a field named
    # ``date`` shadows the ``datetime.date`` import in the module namespace,
    # which breaks annotation resolution under Pydantic v2. ``alias="date"``
    # keeps the CSV/API payload name stable.
    service_date: date = Field(..., example="2026-10-15", alias="date")
    vehicle_id: Optional[str] = Field(None, example="VEH_456")


class DelayRecordCreate(DelayRecordBase):
    """Schema for creating a new delay record."""

    # Accept the CSV column name ``date`` as an alias for ``service_date``.
    model_config = ConfigDict(populate_by_name=True)


class DelayRecordUpdate(DelayRecordBase):
    """Schema for updating a delay record."""
    stop_id: Optional[str] = None
    stop_name: Optional[str] = None
    line: Optional[str] = None
    direction: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    actual_time: Optional[datetime] = None
    delay_minutes: Optional[int] = None
    date: Optional[date] = None
    vehicle_id: Optional[str] = None


class DelayRecordInDBBase(DelayRecordBase):
    """Base schema for delay record stored in DB."""
    id: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        # ORM objects expose the attribute as ``service_date``; without this
        # flag the ``alias="date"`` on DelayRecordBase would make validation
        # from attributes fail with a missing-field error.
        populate_by_name=True,
    )


class DelayRecord(DelayRecordInDBBase):
    """Schema for delay record returned in API."""
    pass


class DelayRecordList(BaseModel):
    """Schema for paginated list of delay records."""
    items: list[DelayRecord]
    total: int
    page: int
    size: int
    pages: int
