"""
Abstract base class for storage backends.
Defines the interface that all storage implementations must follow.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    def __init__(self, **config):
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate backend-specific configuration"""
        pass

    @abstractmethod
    def upload_file(self, local_path: Union[str, Path], remote_path: str) -> bool:
        """
        Upload a file to the storage backend.

        Args:
            local_path: Path to local file
            remote_path: Destination path in storage

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: Union[str, Path]) -> bool:
        """
        Download a file from the storage backend.

        Args:
            remote_path: Path in storage
            local_path: Destination local path

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in storage"""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in storage with optional prefix filter"""
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from storage"""
        pass

    @abstractmethod
    def get_file_url(self, remote_path: str) -> Optional[str]:
        """Get a URL to access the file (if supported)"""
        pass

    # Convenience methods with default implementations

    def upload_pickle(self, obj: Any, remote_path: str) -> bool:
        """Upload a Python object as pickle"""
        import pickle
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as tmp_file:
                pickle.dump(obj, tmp_file)
                tmp_file.flush()

                success = self.upload_file(tmp_file.name, remote_path)

                # Clean up temp file
                Path(tmp_file.name).unlink()
                return success

        except Exception as e:
            logger.error(f"Failed to upload pickle to {remote_path}: {e}")
            return False

    def download_pickle(self, remote_path: str) -> Optional[Any]:
        """Download and deserialize a pickle object"""
        import pickle
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as tmp_file:
                if self.download_file(remote_path, tmp_file.name):
                    with open(tmp_file.name, "rb") as f:
                        obj = pickle.load(f)

                    # Clean up temp file
                    Path(tmp_file.name).unlink()
                    return obj
                else:
                    Path(tmp_file.name).unlink()
                    return None

        except Exception as e:
            logger.error(f"Failed to download pickle from {remote_path}: {e}")
            return None

    def get_info(self) -> Dict[str, Any]:
        """Get information about the storage backend"""
        return {
            "backend_type": self.__class__.__name__,
            "config": {k: v for k, v in self.config.items() if "key" not in k.lower()},
        }
