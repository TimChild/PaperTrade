"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from papertrade.adapters.inbound.api.error_handlers import register_exception_handlers
from papertrade.adapters.inbound.api.portfolios import router as portfolios_router
from papertrade.adapters.inbound.api.transactions import router as transactions_router
from papertrade.infrastructure.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """Application lifespan manager - runs on startup and shutdown."""
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Clean up resources (if needed)


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
