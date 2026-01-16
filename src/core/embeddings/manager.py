"""
Embeddings manager for Qdrant storage operations.

Manages loading and status checking of embeddings in Qdrant.
"""

import logging
from typing import Dict, Any

from ...storage import get_storage_manager
from ...storage.qdrant import QdrantStorage

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """Manages embeddings using Qdrant vector database."""

    def __init__(self):
        self.storage_manager = get_storage_manager()
        self.qdrant = QdrantStorage()
        self._embeddings_loaded = False

    def load_embeddings(self, force_reload: bool = False) -> bool:
        """
        Check if embeddings are available in Qdrant.

        Args:
            force_reload: Force recheck even if already loaded

        Returns:
            True if embeddings are available, False otherwise
        """
        if self._embeddings_loaded and not force_reload:
            return True

        try:
            # Check if collections have data
            frames_info = self.qdrant.get_collection_info(
                QdrantStorage.FRAMES_COLLECTION
            )
            objects_info = self.qdrant.get_collection_info(
                QdrantStorage.OBJECTS_COLLECTION
            )

            frames_count = frames_info.get("points_count", 0)
            objects_count = objects_info.get("points_count", 0)

            if frames_count > 0:
                logger.info(
                    f"Using Qdrant: {frames_count} frames, {objects_count} objects"
                )
                self._embeddings_loaded = True
                return True
            else:
                logger.error(
                    "Qdrant collections are empty. Please run the pipeline to generate embeddings."
                )
                return False

        except Exception as e:
            logger.error(f"Error checking Qdrant collections: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get status of embeddings in Qdrant.

        Returns:
            Dictionary with status information
        """
        try:
            frames_info = self.qdrant.get_collection_info(
                QdrantStorage.FRAMES_COLLECTION
            )
            objects_info = self.qdrant.get_collection_info(
                QdrantStorage.OBJECTS_COLLECTION
            )

            return {
                "loaded": self._embeddings_loaded,
                "frame_count": frames_info.get("points_count", 0),
                "object_count": objects_info.get("points_count", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                "loaded": False,
                "frame_count": 0,
                "object_count": 0,
            }
