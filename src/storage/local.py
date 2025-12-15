"""
Local filesystem storage backend.
Provides local storage with same interface as cloud storage for development and fallback.
"""

import shutil
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import logging

from .base import StorageBackend
from ..config.settings import get_data_dir

logger = logging.getLogger(__name__)


class LocalStorage(StorageBackend):
    """Local filesystem storage backend"""

    def __init__(self, **config):
        self.base_path = Path(config.get("base_path", get_data_dir()))
        super().__init__(**config)

    def _validate_config(self) -> None:
        """Validate local storage configuration"""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            if not self.base_path.exists() or not self.base_path.is_dir():
                raise ValueError(f"Cannot access base path: {self.base_path}")
        except Exception as e:
            raise ValueError(f"Local storage validation failed: {e}")

    def _get_local_path(self, remote_path: str) -> Path:
        """Convert remote path to local filesystem path"""
        # Remove leading slash and ensure relative path
        clean_path = remote_path.lstrip("/")
        return self.base_path / clean_path

    def upload_file(self, local_path: Union[str, Path], remote_path: str) -> bool:
        """Copy file to local storage location"""
        try:
            local_path = Path(local_path)
            if not local_path.exists():
                logger.error(f"Source file not found: {local_path}")
                return False

            destination = self._get_local_path(remote_path)
            destination.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(local_path, destination)
            logger.info(f"Copied {local_path} to {destination}")
            return True

        except Exception as e:
            logger.error(f"Error copying file {local_path} to {remote_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: Union[str, Path]) -> bool:
        """Copy file from storage location to specified path"""
        try:
            source = self._get_local_path(remote_path)
            local_path = Path(local_path)

            if not source.exists():
                logger.error(f"Source file not found: {source}")
                return False

            local_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, local_path)
            logger.info(f"Copied {source} to {local_path}")
            return True

        except Exception as e:
            logger.error(f"Error copying file {remote_path} to {local_path}: {e}")
            return False

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in local storage"""
        return self._get_local_path(remote_path).exists()

    def list_files(self, prefix: str = "") -> List[str]:
        """List files in local storage with optional prefix"""
        try:
            if prefix:
                search_path = self._get_local_path(prefix)
                if search_path.is_file():
                    return [prefix]
                elif search_path.is_dir():
                    files = []
                    for file_path in search_path.rglob("*"):
                        if file_path.is_file():
                            # Convert back to relative path with prefix
                            rel_path = file_path.relative_to(self.base_path)
                            files.append(str(rel_path).replace("\\", "/"))
                    return files
                else:
                    # Pattern matching
                    files = []
                    for file_path in self.base_path.rglob("*"):
                        if file_path.is_file():
                            rel_path = str(
                                file_path.relative_to(self.base_path)
                            ).replace("\\", "/")
                            if rel_path.startswith(prefix):
                                files.append(rel_path)
                    return files
            else:
                files = []
                for file_path in self.base_path.rglob("*"):
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(self.base_path)).replace(
                            "\\", "/"
                        )
                        files.append(rel_path)
                return files

        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            return []

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from local storage"""
        try:
            file_path = self._get_local_path(remote_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {remote_path}: {e}")
            return False

    def get_file_url(self, remote_path: str) -> Optional[str]:
        """Get file path as URL (file:// protocol)"""
        file_path = self._get_local_path(remote_path)
        if file_path.exists():
            return file_path.as_uri()
        return None

    def get_info(self) -> Dict[str, Any]:
        """Get local storage information"""
        info = super().get_info()

        # Calculate storage usage
        total_size = 0
        file_count = 0

        try:
            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
        except Exception as e:
            logger.error(f"Error calculating storage usage: {e}")

        info.update(
            {
                "base_path": str(self.base_path),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "file_count": file_count,
                "available": self.base_path.exists() and self.base_path.is_dir(),
            }
        )

        return info
