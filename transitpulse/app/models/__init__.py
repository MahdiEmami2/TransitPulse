"""Database models.

Importing this module registers every model with the SQLAlchemy Base,
so that Base.metadata.create_all creates all tables.
"""

from transitpulse.app.models.delay import DelayRecord, Line, Stop, TrainedModel  # noqa: F401

__all__ = ["DelayRecord", "Line", "Stop", "TrainedModel"]
