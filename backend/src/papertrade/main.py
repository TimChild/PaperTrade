"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from papertrade.adapters.inbound.api.error_handlers import register_exception_handlers
from papertrade.adapters.inbound.api.analytics import router as analytics_router
from papertrade.adapters.inbound.api.portfolios import router as portfolios_router
from papertrade.adapters.inbound.api.prices import router as prices_router
from papertrade.adapters.inbound.api.transactions import router as transactions_router
from papertrade.infrastructure.database import init_db
from papertrade.infrastructure.scheduler import (
    SchedulerConfig,
    start_scheduler,
    stop_scheduler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[misc]  # AsyncGenerator return type is inferred correctly by FastAPI
    """Application lifespan manager - runs on startup and shutdown."""
    # Startup: Initialize database
    await init_db()

    # Startup: Initialize and start background scheduler
    # Configuration can be customized by creating SchedulerConfig instance
    # For now, using defaults (disabled in tests via config override)
    scheduler_config = SchedulerConfig(
        enabled=True,  # Set to False to disable scheduler
        refresh_cron="0 0 * * *",  # Midnight UTC daily
        batch_size=5,  # 5 calls/min rate limit
        batch_delay_seconds=12,  # ~5 calls/min (12 seconds between calls)
        active_stock_days=30,  # Consider stocks traded in last 30 days
    )
    await start_scheduler(scheduler_config)

    yield

    # Shutdown: Stop background scheduler
    await stop_scheduler()


app = FastAPI(
    title="PaperTrade API",
    description="Stock market emulation platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register exception handlers
register_exception_handlers(app)

# CORS configuration - will be made configurable later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(portfolios_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(prices_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """API root endpoint."""
    return {"message": "Welcome to PaperTrade API v1"}


@app.get("/api/v1/")
async def api_v1_root() -> dict[str, str]:
    """API v1 root endpoint."""
    return {"message": "Welcome to PaperTrade API v1"}
