"""
Storage endpoints for the API.
Provides information about storage configuration and status.
"""

import logging
from fastapi import APIRouter, HTTPException

from ..models import StorageStatusResponse
from ...config.storage import validate_storage_config
from ...storage import get_storage_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=StorageStatusResponse)
async def get_storage_status():
    """
    Get storage system status and configuration.
    
    Returns:
        StorageStatusResponse with storage information
    
    Raises:
        HTTPException: If status check fails
    """
    try:
        status = validate_storage_config()
        
        # Get current mode information
        current_mode = None
        fallback_enabled = False
        
        try:
            storage_manager = get_storage_manager()
            manager_status = storage_manager.get_status()
            current_mode = manager_status.get("preferred_mode")
            fallback_enabled = manager_status.get("fallback_enabled", False)
        except Exception as e:
            logger.warning(f"Could not get storage manager status: {e}")
        
        return StorageStatusResponse(
            s3_available=status["s3_available"],
            local_available=status["local_available"],
            recommended_backend=status["recommended_backend"],
            current_mode=current_mode,
            fallback_enabled=fallback_enabled,
            issues=status.get("issues", []),
        )
        
    except Exception as e:
        logger.error(f"Storage status check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get storage status: {str(e)}"
        )
