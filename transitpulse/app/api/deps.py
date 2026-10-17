"""FastAPI dependencies."""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from transitpulse.app.database import async_session, get_db


# Re-export get_db for convenience
# Alternatively, we can define a dependency that provides the session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with async_session() as session:
        yield session
