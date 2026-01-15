"""
Core search functionality for the audiovisual archive.
Handles CLIP-based similarity search for both frames and objects using Qdrant.
"""

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
from .embeddings import EmbeddingService, EmbeddingsManager

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Data class for search results"""

    path: str
    similarity: float
    result_type: str  # "frame" or "object"
    metadata: Optional[Dict] = None


class SearchEngine:
    """Main search engine for the audiovisual archive"""

    def __init__(self):
        self.embeddings_manager = EmbeddingsManager()
        self.embedding_service = EmbeddingService()
        self.model_name = app_config.embedding_model

    def compute_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Compute CLIP embedding for text query"""
        return self.embedding_service.compute_text_embedding(text)

    def compute_image_embedding(
        self, image_path: Union[str, Path]
    ) -> Optional[np.ndarray]:
        """Compute CLIP embedding for image query"""
        return self.embedding_service.compute_image_embedding(image_path, retry=False)

    def search_by_text(
        self,
        query: str,
        search_frames: bool = True,
        search_objects: bool = True,
        max_results: int = None,
        video_names: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Search for similar content using text query

        Args:
            query: Text query for search
            search_frames: Whether to search in frames
            search_objects: Whether to search in objects
            max_results: Maximum number of results
            video_names: Optional list of video names to filter by
        """

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

        # Search using Qdrant with optional video filtering
        if search_frames:
            # If video_names is provided, search each video separately
            if video_names:
                for video_name in video_names:
                    frame_results = self.embeddings_manager.qdrant.search_frames(
                        query_embedding,
                        limit=max_results,
                        video_name=video_name,
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
            else:
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
            # If video_names is provided, search each video separately
            if video_names:
                for video_name in video_names:
                    object_results = self.embeddings_manager.qdrant.search_objects(
                        query_embedding,
                        limit=max_results,
                        video_name=video_name,
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
            else:
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
        video_names: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Search for similar content using image query

        Args:
            image_path: Path to the query image
            search_frames: Whether to search in frames
            search_objects: Whether to search in objects
            max_results: Maximum number of results
            video_names: Optional list of video names to filter by
        """

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

        # Search using Qdrant with optional video filtering
        if search_frames:
            # If video_names is provided, search each video separately
            if video_names:
                for video_name in video_names:
                    frame_results = self.embeddings_manager.qdrant.search_frames(
                        query_embedding,
                        limit=max_results,
                        video_name=video_name,
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
            else:
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
            # If video_names is provided, search each video separately
            if video_names:
                for video_name in video_names:
                    object_results = self.embeddings_manager.qdrant.search_objects(
                        query_embedding,
                        limit=max_results,
                        video_name=video_name,
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
            else:
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
