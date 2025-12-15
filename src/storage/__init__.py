"""
Storage factory and management utilities.
Provides a unified interface for different storage backends.
"""

from typing import Union, Dict, Any, Optional
import logging

from .base import StorageBackend
from .s3 import S3Storage
from .local import LocalStorage
from ..config.storage import validate_storage_config
from ..config.settings import get_preferred_storage_mode

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages multiple storage backends with automatic fallback"""

    def __init__(self, primary_backend: str = "auto", fallback_enabled: bool = None):
        self.primary_backend = primary_backend
        self.storage_status = validate_storage_config()

        # Determine fallback setting based on storage mode
        preferred_mode = get_preferred_storage_mode()
        if fallback_enabled is None:
            self.fallback_enabled = preferred_mode not in ["s3-only", "local-only"]
        else:
            self.fallback_enabled = fallback_enabled

        self._primary_storage: Optional[StorageBackend] = None
        self._fallback_storage: Optional[StorageBackend] = None

        self._init_storage_backends()

    def _init_storage_backends(self) -> None:
        """Initialize storage backends based on availability and preferences"""
        preferred_mode = get_preferred_storage_mode()

        # Determine primary backend based on preferred mode
        if self.primary_backend == "auto":
            if (
                preferred_mode in ["s3-only", "s3-primary"]
                and self.storage_status["s3_available"]
            ):
                primary_type = "s3"
            elif (
                preferred_mode == "local-only"
                or not self.storage_status["s3_available"]
            ):
                primary_type = "local"
            elif self.storage_status["s3_available"]:
                primary_type = "s3"
            elif self.storage_status["local_available"]:
                primary_type = "local"
            else:
                raise RuntimeError("No storage backend available")
        else:
            primary_type = self.primary_backend

        # Initialize primary storage
        try:
            if primary_type == "s3":
                self._primary_storage = S3Storage()
                logger.info(
                    f"Initialized S3 as primary storage (mode: {preferred_mode})"
                )
            elif primary_type == "local":
                self._primary_storage = LocalStorage()
                logger.info(
                    f"Initialized local storage as primary (mode: {preferred_mode})"
                )
            else:
                raise ValueError(f"Unknown storage backend: {primary_type}")

        except Exception as e:
            logger.error(f"Failed to initialize primary storage ({primary_type}): {e}")
            if not self.fallback_enabled or preferred_mode in ["s3-only", "local-only"]:
                raise
            primary_type = "failed"

        # Initialize fallback if enabled and different from primary
        if self.fallback_enabled and preferred_mode not in ["s3-only", "local-only"]:
            try:
                if primary_type != "local" and self.storage_status["local_available"]:
                    self._fallback_storage = LocalStorage()
                    logger.info("Initialized local storage as fallback")
                elif primary_type != "s3" and self.storage_status["s3_available"]:
                    self._fallback_storage = S3Storage()
                    logger.info("Initialized S3 as fallback")
            except Exception as e:
                logger.warning(f"Failed to initialize fallback storage: {e}")

    def get_storage(self, prefer_fallback: bool = False) -> StorageBackend:
        """Get active storage backend"""
        if prefer_fallback and self._fallback_storage:
            return self._fallback_storage
        elif self._primary_storage:
            return self._primary_storage
        elif self._fallback_storage:
            logger.warning("Primary storage unavailable, using fallback")
            return self._fallback_storage
        else:
            raise RuntimeError("No storage backend available")

    def upload_file_with_fallback(self, local_path: str, remote_path: str) -> bool:
        """Upload file with automatic fallback on failure"""
        storage = self.get_storage()

        # Try primary storage
        if storage.upload_file(local_path, remote_path):
            return True

        # Try fallback if enabled and different from primary
        if (
            self.fallback_enabled
            and self._fallback_storage
            and storage != self._fallback_storage
        ):
            logger.warning("Primary upload failed, trying fallback storage")
            return self._fallback_storage.upload_file(local_path, remote_path)

        return False

    def download_file_with_fallback(self, remote_path: str, local_path: str) -> bool:
        """Download file with automatic fallback"""
        storage = self.get_storage()

        # Try primary storage
        if storage.file_exists(remote_path) and storage.download_file(
            remote_path, local_path
        ):
            return True

        # Try fallback
        if (
            self.fallback_enabled
            and self._fallback_storage
            and storage != self._fallback_storage
        ):
            if self._fallback_storage.file_exists(remote_path):
                logger.info("File not found in primary storage, trying fallback")
                return self._fallback_storage.download_file(remote_path, local_path)

        return False

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive storage status"""
        preferred_mode = get_preferred_storage_mode()

        status = {
            "primary_available": self._primary_storage is not None,
            "fallback_available": self._fallback_storage is not None,
            "primary_info": None,
            "fallback_info": None,
            "storage_status": self.storage_status,
            "preferred_mode": preferred_mode,
            "fallback_enabled": self.fallback_enabled,
        }

        if self._primary_storage:
            status["primary_info"] = self._primary_storage.get_info()

        if self._fallback_storage:
            status["fallback_info"] = self._fallback_storage.get_info()

        return status


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager(**kwargs) -> StorageManager:
    """Get or create global storage manager"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager(**kwargs)
    return _storage_manager


def get_storage(backend_type: Optional[str] = None) -> StorageBackend:
    """Get storage backend directly"""
    if backend_type == "s3":
        return S3Storage()
    elif backend_type == "local":
        return LocalStorage()
    else:
        manager = get_storage_manager()
        return manager.get_storage()
