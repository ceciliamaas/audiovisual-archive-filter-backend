"""
Status endpoints for the API.
Provides information about system status and health.
"""

import logging
from fastapi import APIRouter, HTTPException

from ..models import StatusResponse, EmbeddingsStatusResponse
from ...core.search import get_search_engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=StatusResponse)
async def get_status():
    """
    Get overall system status including search engine and embeddings.
    
    Returns:
        StatusResponse with system status information
    
    Raises:
        HTTPException: If status check fails
    """
    try:
        search_engine = get_search_engine()
        status = search_engine.get_status()
        
        return StatusResponse(
            replicate_available=status["replicate_available"],
            model=status["model"],
            embeddings_status=status["embeddings_status"],
        )
        
    except Exception as e:
        logger.error(f"Status check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/embeddings", response_model=EmbeddingsStatusResponse)
async def get_embeddings_status():
    """
    Get detailed embeddings status.
    
    Returns:
        EmbeddingsStatusResponse with embeddings information
    
    Raises:
        HTTPException: If status check fails
    """
    try:
        search_engine = get_search_engine()
        embeddings_status = search_engine.embeddings_manager.get_status()
        
        return EmbeddingsStatusResponse(
            loaded=embeddings_status["loaded"],
            frame_count=embeddings_status["frame_count"],
            object_count=embeddings_status["object_count"],
            source=embeddings_status.get("source", "qdrant"),
        )
        
    except Exception as e:
        logger.error(f"Embeddings status check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get embeddings status: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "service": "audiovisual-archive-search-api"
    }
