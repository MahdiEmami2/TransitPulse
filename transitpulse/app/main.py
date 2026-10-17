"""TransitPulse FastAPI application factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from transitpulse.app.config import settings
from transitpulse.app.database import engine, init_db

# Configure logging
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("transitpulse")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting TransitPulse application...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't fail startup if DB is not available (e.g., during testing)
        logger.warning("Continuing without database connection")

    yield

    # Shutdown
    logger.info("Shutting down TransitPulse application...")
    await engine.dispose()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="TransitPulse API",
        description="Public transport delay analysis and prediction API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint for monitoring and orchestration."""
        from transitpulse.app.database import check_db_connection

        db_healthy = await check_db_connection()

        return {
            "status": "healthy" if db_healthy else "degraded",
            "service": "transitpulse",
            "version": "0.1.0",
            "database": "connected" if db_healthy else "disconnected",
        }

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "Welcome to TransitPulse API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    # Include API routers
    from transitpulse.app.api.v1.delays import router as delays_router
    from transitpulse.app.api.v1.patterns import router as patterns_router
    from transitpulse.app.api.v1.predict import router as predict_router
    from transitpulse.app.api.v1.ingestion import router as ingestion_router

    app.include_router(delays_router, prefix="/api/v1/delays", tags=["delays"])
    app.include_router(patterns_router, prefix="/api/v1/patterns", tags=["patterns"])
    app.include_router(predict_router, prefix="/api/v1/predict", tags=["predict"])
    app.include_router(ingestion_router, prefix="/api/v1/ingest", tags=["ingestion"])

    # Simple server-rendered dashboard (single static HTML file)
    template_path = Path(__file__).parent / "templates" / "dashboard.html"

    @app.get("/dashboard", tags=["dashboard"], include_in_schema=False)
    async def dashboard():
        """Serve the statistics and prediction dashboard."""
        return HTMLResponse(template_path.read_text(encoding="utf-8"))

    logger.info("TransitPulse application created successfully")
    return app


# Create app instance for uvicorn
app = create_app()