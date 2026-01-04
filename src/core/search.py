"""
Core search functionality for the audiovisual archive.
Handles CLIP-based similarity search for both frames and objects using Qdrant.
"""

import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass

# Load environment variables early
from dotenv import load_dotenv

load_dotenv()

from ..config.settings import app_config
from ..storage import get_storage_manager
from ..storage.qdrant import QdrantStorage

logger = logging.getLogger(__name__)

# Initialize Replicate client
_replicate_client = None


def get_replicate_client():
    """Get or create Replicate client"""
    global _replicate_client
    if _replicate_client is None:
        try:
            import streamlit as st

            token = st.secrets.get("REPLICATE_API_TOKEN")
        except:
            token = os.getenv("REPLICATE_API_TOKEN")

        if not token:
            raise RuntimeError(
                "Missing Replicate API token. Set REPLICATE_API_TOKEN in environment or Streamlit secrets."
            )

        import replicate

        _replicate_client = replicate.Client(api_token=token)

    return _replicate_client


@dataclass
class SearchResult:
    """Data class for search results"""

    path: str
    similarity: float
    result_type: str  # "frame" or "object"
    metadata: Optional[Dict] = None


class EmbeddingsManager:
    """Manages embeddings using Qdrant vector database"""

    def __init__(self):
        self.storage_manager = get_storage_manager()
        self.qdrant = QdrantStorage()
        self._embeddings_loaded = False

    def load_embeddings(self, force_reload: bool = False) -> bool:
        """Check if embeddings are available in Qdrant"""
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

            if frames_info.get("points_count", 0) > 0:
                logger.info(
                    f"Using Qdrant: {frames_info['points_count']} frames, {objects_info.get('points_count', 0)} objects"
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
        """Get embeddings status information from Qdrant"""
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


class SearchEngine:
    """Main search engine for the audiovisual archive"""

    def __init__(self):
        self.embeddings_manager = EmbeddingsManager()
        self.replicate_client = get_replicate_client()
        self.model_name = app_config.embedding_model

    def compute_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Compute CLIP embedding for text query"""
        try:
            inputs = {"text": text}
            output = self.replicate_client.run(self.model_name, input=inputs)

            if output and "embedding" in output:
                embedding_list = output["embedding"]
                embedding = np.array(embedding_list)
                # Normalize embedding
                embedding = embedding / np.linalg.norm(embedding)
                return embedding
            else:
                logger.error("Empty output from CLIP model")
                return None

        except Exception as e:
            logger.error(f"Error computing text embedding: {e}")
            return None

    def compute_image_embedding(
        self, image_path: Union[str, Path]
    ) -> Optional[np.ndarray]:
        """Compute CLIP embedding for image query"""
        try:
            # Open image file and send to Replicate
            with open(image_path, "rb") as image_file:
                inputs = {"image": image_file, "model": "ViT-B/32"}
                output = self.replicate_client.run(self.model_name, input=inputs)

            if output and "embedding" in output:
                embedding_list = output["embedding"]
                embedding = np.array(embedding_list)
                # Normalize embedding
                embedding = embedding / np.linalg.norm(embedding)
                return embedding
            else:
                logger.error("Empty output from CLIP model")
                return None

        except Exception as e:
            logger.error(f"Error computing image embedding: {e}")
            return None

    def search_by_text(
        self,
        query: str,
        search_frames: bool = True,
        search_objects: bool = True,
        max_results: int = None,
    ) -> List[SearchResult]:
        """Search for similar content using text query"""

        if max_results is None:
            max_results = app_config.max_search_results

        # Ensure embeddings are loaded
        if not self.embeddings_manager.load_embeddings():
            logger.error("Failed to load embeddings")
            return []

        # Compute query embedding
        query_embedding = self.compute_text_embedding(query)
        if query_embedding is None:
            return []

        results = []

        # Search using Qdrant
        if search_frames:
            frame_results = self.embeddings_manager.qdrant.search_frames(
                query_embedding,
                limit=max_results // 2 if search_objects else max_results,
            )
            results.extend(
                [
                    SearchResult(
                        path=path,
                        similarity=score,
                        result_type="frame",
                        metadata=metadata,
                    )
                    for path, score, metadata in frame_results
                ]
            )

        if search_objects:
            object_results = self.embeddings_manager.qdrant.search_objects(
                query_embedding,
                limit=max_results // 2 if search_frames else max_results,
            )
            results.extend(
                [
                    SearchResult(
                        path=path,
                        similarity=score,
                        result_type="object",
                        metadata=metadata,
                    )
                    for path, score, metadata in object_results
                ]
            )

        # Sort by similarity and limit results
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:max_results]

    def search_by_image(
        self,
        image_path: Union[str, Path],
        search_frames: bool = True,
        search_objects: bool = True,
        max_results: int = None,
    ) -> List[SearchResult]:
        """Search for similar content using image query"""

        if max_results is None:
            max_results = app_config.max_search_results

        # Ensure embeddings are loaded
        if not self.embeddings_manager.load_embeddings():
            logger.error("Failed to load embeddings")
            return []

        # Compute query embedding
        query_embedding = self.compute_image_embedding(image_path)
        if query_embedding is None:
            return []

        results = []

        # Search using Qdrant
        if search_frames:
            frame_results = self.embeddings_manager.qdrant.search_frames(
                query_embedding,
                limit=max_results // 2 if search_objects else max_results,
            )
            results.extend(
                [
                    SearchResult(
                        path=path,
                        similarity=score,
                        result_type="frame",
                        metadata=metadata,
                    )
                    for path, score, metadata in frame_results
                ]
            )

        if search_objects:
            object_results = self.embeddings_manager.qdrant.search_objects(
                query_embedding,
                limit=max_results // 2 if search_frames else max_results,
            )
            results.extend(
                [
                    SearchResult(
                        path=path,
                        similarity=score,
                        result_type="object",
                        metadata=metadata,
                    )
                    for path, score, metadata in object_results
                ]
            )

        # Sort by similarity and limit results
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:max_results]

    # Convenience methods for specific search types
    def search_frames(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search only frames"""
        return self.search_by_text(
            query, search_frames=True, search_objects=False, max_results=limit
        )

    def search_objects(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search only objects"""
        return self.search_by_text(
            query, search_frames=False, search_objects=True, max_results=limit
        )

    def get_status(self) -> Dict[str, Any]:
        """Get search engine status"""
        return {
            "model": self.model_name,
            "embeddings_status": self.embeddings_manager.get_status(),
            "replicate_available": self.replicate_client is not None,
        }


# Global search engine instance
_search_engine: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    """Get or create global search engine"""
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine


def search(query: str, **kwargs) -> List[SearchResult]:
    """Convenience function for text search"""
    engine = get_search_engine()
    return engine.search_by_text(query, **kwargs)


def search_by_image(image_path: Union[str, Path], **kwargs) -> List[SearchResult]:
    """Convenience function for image search"""
    engine = get_search_engine()
    return engine.search_by_image(image_path, **kwargs)
