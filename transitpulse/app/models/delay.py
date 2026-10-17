"""SQLAlchemy models for delay data."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BIGINT,
    Boolean,
    Date,
    DateTime,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from transitpulse.app.database import Base

# BIGINT autoincrement primary keys do not work on SQLite (SQLite only
# auto-increments INTEGER primary keys). The variant keeps BIGINT on
# PostgreSQL while allowing the documented SQLite development fallback.
BigIntPK = BIGINT().with_variant(Integer(), "sqlite")


class DelayRecord(Base):
    """Delay observation record."""

    __tablename__ = "delays"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    stop_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    stop_name: Mapped[str] = mapped_column(String(200), nullable=False)
    line: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # Relationships (optional, for future extension)
    # ml_model: Mapped["TrainedModel"] = relationship(back_populates="delay_record")

    def __repr__(self) -> str:
        return (
            f"<DelayRecord id={self.id} stop={self.stop_id} line={self.line} "
            f"delay={self.delay_minutes}min date={self.service_date}>"
        )


class Stop(Base):
    """Transport stop/station."""

    __tablename__ = "stops"

    stop_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    stop_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    # For simplicity, we'll store lines as a string array; PostgreSQL supports arrays
    # Alternatively, we could use a many-to-many relationship with a lines table
    # But for now, we'll use a simple text array or JSON
    # Using String for now, can be changed to ARRAY or JSONB later
    lines: Mapped[str | None] = mapped_column(nullable=True)  # comma-separated or JSON

    def __repr__(self) -> str:
        return f"<Stop id={self.stop_id} name={self.stop_name}>"


class Line(Base):
    """Transport line/route."""

    __tablename__ = "lines"

    line_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    line_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Optional: color, operator, etc.
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<Line id={self.line_id} name={self.line_name}>"


class TrainedModel(Base):
    """Persisted ML model metadata and blob."""

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    # Store hyperparameters as JSON
    parameters: Mapped[str] = mapped_column(nullable=False)  # JSON string
    # Store metrics as JSON
    metrics: Mapped[str] = mapped_column(nullable=False)  # JSON string
    # Pickled model blob
    model_blob: Mapped[bytes] = mapped_column(nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("FALSE"), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TrainedModel id={self.id} name={self.name} algorithm={self.algorithm}>"
