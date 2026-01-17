"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zebu.adapters.inbound.api.analytics import (
    admin_router as analytics_admin_router,
)
from zebu.adapters.inbound.api.analytics import router as analytics_router
from zebu.adapters.inbound.api.debug import router as debug_router
from zebu.adapters.inbound.api.error_handlers import register_exception_handlers
from zebu.adapters.inbound.api.portfolios import router as portfolios_router
from zebu.adapters.inbound.api.prices import router as prices_router
from zebu.adapters.inbound.api.transactions import router as transactions_router
from zebu.infrastructure.database import init_db
from zebu.infrastructure.scheduler import (
    SchedulerConfig,
    start_scheduler,
    stop_scheduler,
)

# Configure logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[misc]  # AsyncGenerator return type is inferred correctly by FastAPI
    """Application lifespan manager - runs on startup and shutdown."""
    logger.info("=== APPLICATION STARTUP ===")
    
    # Startup: Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Startup: Initialize and start background scheduler
    # Configuration can be customized by creating SchedulerConfig instance
    # For now, using defaults (disabled in tests via config override)
    logger.info("Preparing scheduler configuration...")
    scheduler_config = SchedulerConfig(
        enabled=True,  # Set to False to disable scheduler
        refresh_cron="0 0 * * *",  # Midnight UTC daily
        batch_size=5,  # 5 calls/min rate limit
        batch_delay_seconds=12,  # ~5 calls/min (12 seconds between calls)
        active_stock_days=30,  # Consider stocks traded in last 30 days
    )
    logger.info(f"Scheduler config: enabled={scheduler_config.enabled}, cron={scheduler_config.refresh_cron}")
    
    logger.info("Starting background scheduler...")
    try:
        await start_scheduler(scheduler_config)
        logger.info("Scheduler startup completed")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
    
    logger.info("=== APPLICATION STARTUP COMPLETE ===")

    yield

    # Shutdown: Stop background scheduler
    logger.info("=== APPLICATION SHUTDOWN ===")
    await stop_scheduler()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Zebu API",
    description="Stock market emulation platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register exception handlers
register_exception_handlers(app)

# CORS configuration
# Allow specific origins from environment variable
# Defaults to localhost for development
allowed_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(portfolios_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(prices_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(analytics_admin_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """API root endpoint."""
    return {"message": "Welcome to Zebu API v1"}


@app.get("/api/v1/")
async def api_v1_root() -> dict[str, str]:
    """API v1 root endpoint."""
    return {"message": "Welcome to Zebu API v1"}
