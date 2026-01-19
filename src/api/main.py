"""
FastAPI application entry point.
Provides REST API for audiovisual archive search functionality.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .routers import search, status, storage, videos
from ..config.settings import app_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application"""
    logger.info("Starting FastAPI application...")

    # Startup: Initialize services
    try:
        from ..core.search import get_search_engine
        from ..storage import get_storage_manager

        # Initialize services
        storage_manager = get_storage_manager()
        search_engine = get_search_engine()

        # Preload embeddings
        search_engine.embeddings_manager.load_embeddings()

        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        # Continue anyway - errors will be reported through status endpoint

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")


# Create FastAPI app
app = FastAPI(
    title="Audiovisual Archive Search API",
    description="AI-powered search API for audiovisual archives using CLIP embeddings",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default dev server
        "http://localhost:5173",  # Vite default dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://audiovisual-archive-filter.pages.dev",  # Cloudflare Pages production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(storage.router, prefix="/api/storage", tags=["storage"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Audiovisual Archive Search API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "online",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred",
        },
    )
