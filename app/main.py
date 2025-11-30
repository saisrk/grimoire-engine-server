"""
Grimoire Engine Backend - Main Application Entry Point.

This module creates and configures the FastAPI application instance,
including middleware, logging, and core endpoints.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import engine
from app.models.spell import Base

# Load environment variables from .env file
load_dotenv()


# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events:
    - Startup: Create database tables if they don't exist
    - Shutdown: Dispose of database engine
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None
    """
    # Startup: Create tables
    logger.info("Starting Grimoire Engine Backend")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown: Cleanup
    logger.info("Shutting down Grimoire Engine Backend")
    await engine.dispose()
    logger.info("Database engine disposed")


# Create FastAPI application instance
app = FastAPI(
    title="Grimoire Engine API",
    description="Backend API for capturing GitHub PR errors and matching solution spells",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Configure CORS middleware
# Allow all origins for development - restrict in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS configured with origins: {CORS_ORIGINS}")


@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns basic health status of the API. Used by Docker health checks
    and monitoring systems to verify the service is running.
    
    Returns:
        dict: Health status with service name and status
        
    Example:
        GET /health
        Response: {"status": "healthy", "service": "grimoire-engine-backend"}
    """
    return {
        "status": "healthy",
        "service": "grimoire-engine-backend",
    }


# Include API routers
from app.api import spells, webhook

app.include_router(spells.router)
app.include_router(webhook.router)


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn when executed directly
    # For production, use: uvicorn app.main:app --host 0.0.0.0 --port 8000
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level=LOG_LEVEL.lower(),
    )
