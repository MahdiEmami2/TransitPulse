"""Data ingestion API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.api.deps import get_db_session
from transitpulse.app.database import AsyncSession as AsyncSessionType
from transitpulse.app.services.ingestion import ingest_csv_data

router = APIRouter()


class IngestionResult(BaseModel):
    """Result of a CSV ingestion operation."""

    rows_processed: int
    rows_inserted: int
    errors: list[str]
    success: bool


@router.post("/", response_model=IngestionResult)
async def ingest_csv(
    file: UploadFile = File(...),
    db: AsyncSessionType = Depends(get_db_session),
):
    """
    Trigger CSV ingestion for delay data.

    Accepts a CSV file with columns:
    stop_id, stop_name, line, direction, scheduled_time, actual_time,
    delay_minutes, date, vehicle_id

    Returns the number of rows processed, inserted, and any errors.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file",
        )

    content = await file.read()

    try:
        rows_processed, rows_inserted, errors = await ingest_csv_data(
            content, db
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}",
        )

    return IngestionResult(
        rows_processed=rows_processed,
        rows_inserted=rows_inserted,
        errors=errors,
        success=len(errors) == 0,
    )