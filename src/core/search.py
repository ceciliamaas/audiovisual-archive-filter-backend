"""
Core search functionality for the audiovisual archive.
Handles CLIP-based similarity search for both frames and objects.
"""

import os
import pickle
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
    """Manages loading and caching of embeddings from storage"""

    def __init__(self):
        self.storage_manager = get_storage_manager()
        self._frame_embeddings: Optional[np.ndarray] = None
        self._object_embeddings: Optional[np.ndarray] = None
        self._frame_paths: Optional[List[str]] = None
        self._object_paths: Optional[List[str]] = None
        self._embeddings_loaded = False

    def load_embeddings(self, force_reload: bool = False) -> bool:
        """Load embeddings from storage"""
        if self._embeddings_loaded and not force_reload:
            return True

        try:
            storage = self.storage_manager.get_storage()

            # Try to download embeddings files
            embedding_files = {
                "frame_embeddings": "embeddings/frame_embeddings.pkl",
                "object_embeddings": "embeddings/object_embeddings.pkl",
                "frame_paths": "embeddings/frame_paths.pkl",
                "object_paths": "embeddings/object_paths.pkl",
            }

            data = {}
            for key, remote_path in embedding_files.items():
                if storage.file_exists(remote_path):
                    data[key] = storage.download_pickle(remote_path)
                    if data[key] is None:
                        logger.error(f"Failed to load {key} from {remote_path}")
                        return False
                else:
                    logger.error(f"Embedding file not found: {remote_path}")
                    return False

            # Convert dictionary format to array format if needed
            frame_embeddings_dict = data["frame_embeddings"]
            object_embeddings_dict = data["object_embeddings"]
            frame_paths_dict = data["frame_paths"]
            object_paths_dict = data["object_paths"]

            if isinstance(frame_embeddings_dict, dict):
                # Convert dict format to arrays
                # Use the storage keys from frame_paths_dict, not the dict keys
                frame_keys = list(frame_embeddings_dict.keys())
                frame_embeddings = np.vstack(
                    [frame_embeddings_dict[path] for path in frame_keys]
                )

                # Map to storage paths - if frame_paths_dict is a dict, use its values
                if isinstance(frame_paths_dict, dict):
                    frame_paths = [frame_paths_dict[key] for key in frame_keys]
                else:
                    # Fallback: add frames/ prefix
                    frame_paths = [f"frames/{key}" for key in frame_keys]

                self._frame_embeddings = frame_embeddings
                self._frame_paths = frame_paths
            else:
                # Already in array format
                self._frame_embeddings = frame_embeddings_dict
                self._frame_paths = (
                    frame_paths_dict
                    if isinstance(frame_paths_dict, list)
                    else list(frame_paths_dict.values())
                )

            if isinstance(object_embeddings_dict, dict):
                # Convert dict format to arrays
                logger.info("Object embeddings are in dict format")
                # Use the storage keys from object_paths_dict, not the dict keys
                object_keys = list(object_embeddings_dict.keys())
                object_embeddings = np.vstack(
                    [object_embeddings_dict[path] for path in object_keys]
                )

                # Map to storage paths - if object_paths_dict is a dict, use its values
                # If it's already a list, use it directly (it's already in the correct format)
                if isinstance(object_paths_dict, dict):
                    object_paths = [object_paths_dict[key] for key in object_keys]
                elif isinstance(object_paths_dict, list):
                    # Already in correct list format
                    object_paths = object_paths_dict
                    logger.info(f"Using pre-formatted object paths list with {len(object_paths)} items")
                else:
                    # Fallback: construct correct object paths
                    # Object keys might be: video_1/video_1_frame_00367_obj_2.jpg
                    # OR just: video_1_frame_00367_obj_2.jpg
                    # S3 paths should be: objects/video_1/frame_00367_obj_2.jpg
                    object_paths = []
                    for key in object_keys:
                        parts = key.split("/")
                        if len(parts) == 2:
                            video_dir = parts[0]  # e.g., video_1
                            filename = parts[1]  # e.g., video_1_frame_00367_obj_2.jpg
                            # Remove video_X_ prefix from filename
                            if filename.startswith(f"{video_dir}_"):
                                filename = filename[
                                    len(video_dir) + 1 :
                                ]  # Remove "video_1_"
                            object_paths.append(f"objects/{video_dir}/{filename}")
                        else:
                            # Key format: video_1_frame_00367_obj_2.jpg (no directory prefix)
                            # Need to extract video_X from filename
                            filename = key
                            # Extract video number: video_1, video_2, etc.
                            if filename.startswith("video_") and "_frame_" in filename:
                                # Split to get video_X part
                                video_part = filename.split("_frame_")[
                                    0
                                ]  # e.g., video_1
                                frame_part = filename.split("_frame_")[
                                    1
                                ]  # e.g., 00367_obj_2.jpg
                                # Construct proper path
                                object_paths.append(
                                    f"objects/{video_part}/frame_{frame_part}"
                                )
                            else:
                                # Last resort fallback
                                logger.warning(f"Unexpected object key format: {key}")
                                object_paths.append(f"objects/{key}")

                self._object_embeddings = object_embeddings
                self._object_paths = object_paths
            else:
                # Already in array format
                logger.info("Object embeddings are in array format")
                logger.info(f"Object paths type: {type(object_paths_dict)}")
                self._object_embeddings = object_embeddings_dict
                # Use paths as-is since they should already be fixed
                if isinstance(object_paths_dict, list):
                    self._object_paths = object_paths_dict
                    logger.info(f"Loaded {len(self._object_paths)} object paths")
                    logger.info(f"Sample object paths: {self._object_paths[:3]}")
                else:
                    logger.info("Object paths are not a list, converting...")
                    self._object_paths = list(object_paths_dict.values())
                    logger.info(f"Converted {len(self._object_paths)} object paths")
                    logger.info(f"Sample object paths: {self._object_paths[:3]}")

            self._embeddings_loaded = True
            logger.info("Successfully loaded embeddings from storage")
            return True

        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            return False

    @property
    def frame_embeddings(self) -> Optional[np.ndarray]:
        """Get frame embeddings, loading if necessary"""
        if not self._embeddings_loaded:
            self.load_embeddings()
        return self._frame_embeddings

    @property
    def object_embeddings(self) -> Optional[np.ndarray]:
        """Get object embeddings, loading if necessary"""
        if not self._embeddings_loaded:
            self.load_embeddings()
        return self._object_embeddings

    @property
    def frame_paths(self) -> Optional[List[str]]:
        """Get frame paths, loading if necessary"""
        if not self._embeddings_loaded:
            self.load_embeddings()
        return self._frame_paths

    @property
    def object_paths(self) -> Optional[List[str]]:
        """Get object paths, loading if necessary"""
        if not self._embeddings_loaded:
            self.load_embeddings()
        return self._object_paths

    def get_status(self) -> Dict[str, Any]:
        """Get embeddings status information"""
        return {
            "loaded": self._embeddings_loaded,
            "frame_count": (
                len(self._frame_embeddings) if self._frame_embeddings is not None else 0
            ),
            "object_count": (
                len(self._object_embeddings)
                if self._object_embeddings is not None
                else 0
            ),
            "frame_paths_count": (
                len(self._frame_paths) if self._frame_paths is not None else 0
            ),
            "object_paths_count": (
                len(self._object_paths) if self._object_paths is not None else 0
            ),
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

        # Search frames
        if search_frames and self.embeddings_manager.frame_embeddings is not None:
            frame_results = self._search_embeddings_array(
                self.embeddings_manager.frame_embeddings,
                self.embeddings_manager.frame_paths,
                query_embedding,
                "frame",
                max_results // 2 if search_objects else max_results,
            )
            results.extend(frame_results)

        # Search objects
        if search_objects and self.embeddings_manager.object_embeddings is not None:
            object_results = self._search_embeddings_array(
                self.embeddings_manager.object_embeddings,
                self.embeddings_manager.object_paths,
                query_embedding,
                "object",
                max_results // 2 if search_frames else max_results,
            )
            results.extend(object_results)

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

        # Search frames
        if search_frames and self.embeddings_manager.frame_embeddings is not None:
            frame_results = self._search_embeddings_array(
                self.embeddings_manager.frame_embeddings,
                self.embeddings_manager.frame_paths,
                query_embedding,
                "frame",
                max_results // 2 if search_objects else max_results,
            )
            results.extend(frame_results)

        # Search objects
        if search_objects and self.embeddings_manager.object_embeddings is not None:
            object_results = self._search_embeddings_array(
                self.embeddings_manager.object_embeddings,
                self.embeddings_manager.object_paths,
                query_embedding,
                "object",
                max_results // 2 if search_frames else max_results,
            )
            results.extend(object_results)

        # Sort by similarity and limit results
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:max_results]

    def _search_embeddings_array(
        self,
        embeddings: np.ndarray,
        paths: List[str],
        query_embedding: np.ndarray,
        result_type: str,
        max_results: int,
    ) -> List[SearchResult]:
        """Search embeddings array and return sorted results"""
        if embeddings is None or paths is None:
            return []

        # Compute similarities using vectorized operations
        similarities = np.dot(embeddings, query_embedding)

        # Get top results
        indices = np.argsort(similarities)[::-1][:max_results]

        # Filter by similarity threshold
        threshold = app_config.similarity_threshold

        results = []
        for idx in indices:
            similarity = float(similarities[idx])
            if similarity >= threshold:
                path = paths[idx]
                if result_type == "object":
                    logger.info(
                        f"Returning object result: {path}, similarity: {similarity:.3f}"
                    )
                results.append(
                    SearchResult(
                        path=path,
                        similarity=similarity,
                        result_type=result_type,
                    )
                )

        return results

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
