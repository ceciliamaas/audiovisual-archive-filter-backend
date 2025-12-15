"""
Storage-specific configuration and validation utilities.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from .settings import storage_config, get_data_dir

logger = logging.getLogger(__name__)


def validate_storage_config() -> Dict[str, Any]:
    """
    Validate storage configuration and return status information.

    Returns:
        Dict containing validation status and configuration details
    """
    status = {
        "s3_available": False,
        "local_available": False,
        "recommended_backend": "local",
        "issues": [],
    }

    # Check S3/Storj configuration
    try:
        if storage_config.validate():
            status["s3_available"] = True
            status["recommended_backend"] = "s3"
            logger.info("S3 storage configuration validated successfully")
        else:
            status["issues"].append("S3 credentials missing")
    except Exception as e:
        status["issues"].append(f"S3 validation error: {str(e)}")
        logger.warning(f"S3 storage validation failed: {e}")

    # Check local storage availability
    data_dir = get_data_dir()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        if data_dir.exists() and data_dir.is_dir():
            status["local_available"] = True
            logger.info(f"Local storage available at: {data_dir}")
        else:
            status["issues"].append(f"Cannot access local data directory: {data_dir}")
    except Exception as e:
        status["issues"].append(f"Local storage error: {str(e)}")
        logger.error(f"Local storage validation failed: {e}")

    # Determine recommended backend
    if status["s3_available"] and status["local_available"]:
        status["recommended_backend"] = "hybrid"
    elif status["s3_available"]:
        status["recommended_backend"] = "s3"
    elif status["local_available"]:
        status["recommended_backend"] = "local"
    else:
        status["recommended_backend"] = "none"
        status["issues"].append("No storage backend available")

    return status


def get_local_storage_paths() -> Dict[str, Path]:
    """Get local storage paths for different data types"""
    base_dir = get_data_dir()

    return {
        "videos": base_dir / "videos",
        "frames": base_dir / "frames",
        "objects": base_dir / "objects",
        "embeddings": base_dir / "embeddings",
    }


def ensure_local_directories() -> None:
    """Ensure all required local directories exist"""
    paths = get_local_storage_paths()

    for path_type, path in paths.items():
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            raise


def get_storage_info() -> Dict[str, Any]:
    """Get comprehensive storage information for debugging/status"""
    info = validate_storage_config()

    # Add path information
    info["local_paths"] = {str(k): str(v) for k, v in get_local_storage_paths().items()}

    # Add S3 configuration (without credentials)
    info["s3_config"] = {
        "endpoint": storage_config.storj_endpoint,
        "bucket": storage_config.bucket_name,
        "has_credentials": bool(
            storage_config.access_key and storage_config.secret_key
        ),
    }

    return info
