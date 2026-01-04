"""
Qdrant vector database storage for embeddings.
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

logger = logging.getLogger(__name__)


class QdrantStorage:
    """Manages embeddings in Qdrant vector database"""

    # Collection names
    FRAMES_COLLECTION = "frames"
    OBJECTS_COLLECTION = "objects"

    # Vector dimension for CLIP embeddings (768 for ViT-B/32 model)
    VECTOR_DIM = 768

    def __init__(self):
        """Initialize Qdrant client"""
        # Determine which Qdrant to use (local or cloud)
        qdrant_mode = os.getenv("QDRANT_MODE", "local").lower()

        if qdrant_mode == "cloud":
            qdrant_url = os.getenv("QDRANT_CLOUD")
            if not qdrant_url:
                logger.warning("QDRANT_CLOUD not set, falling back to local")
                qdrant_url = os.getenv("QDRANT_LOCAL", "http://localhost:6333")
        else:
            qdrant_url = os.getenv("QDRANT_LOCAL", "http://localhost:6333")

        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        logger.info(f"Connecting to Qdrant: {qdrant_url} (mode: {qdrant_mode})")
        if qdrant_api_key:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            self.client = QdrantClient(url=qdrant_url)

        # Ensure collections exist
        self._ensure_collections()

    def _ensure_collections(self):
        """Create collections if they don't exist"""
        collections = [self.FRAMES_COLLECTION, self.OBJECTS_COLLECTION]
        existing = [c.name for c in self.client.get_collections().collections]

        for collection in collections:
            if collection not in existing:
                logger.info(f"Creating Qdrant collection: {collection}")
                self.client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=self.VECTOR_DIM, distance=Distance.COSINE
                    ),
                )

    def store_frame_embeddings(
        self,
        embeddings: Dict[str, np.ndarray],
        paths: Dict[str, str],
        timestamps: Optional[Dict[str, float]] = None,
        batch_size: int = 100,
    ) -> int:
        """
        Store frame embeddings in Qdrant.

        Args:
            embeddings: Dict mapping frame keys to embedding vectors
            paths: Dict mapping frame keys to S3 storage paths
            timestamps: Dict mapping frame keys to timestamp in seconds
            batch_size: Number of vectors to upload per batch

        Returns:
            Number of embeddings stored
        """
        if timestamps is None:
            timestamps = {}

        points = []
        for idx, (key, embedding) in enumerate(embeddings.items()):
            # Extract video name and frame index from key (e.g., "reconstruccion_jonathan/frame_00001.jpg")
            video_name = key.split("/")[0] if "/" in key else "unknown"
            frame_name = key.split("/")[-1] if "/" in key else key

            # Parse frame index to potentially reconstruct timestamp
            from scripts.pipeline.naming import NamingConvention

            frame_index = NamingConvention.parse_frame_index(frame_name)

            point = PointStruct(
                id=idx,
                vector=embedding.tolist(),
                payload={
                    "key": key,
                    "path": paths.get(key, f"frames/{key}"),
                    "video_name": video_name,
                    "type": "frame",
                    "frame_index": frame_index,
                    "timestamp": timestamps.get(key, 0.0),
                },
            )
            points.append(point)

            # Upload in batches
            if len(points) >= batch_size:
                self.client.upsert(
                    collection_name=self.FRAMES_COLLECTION, points=points
                )
                logger.info(f"Uploaded {len(points)} frame embeddings to Qdrant")
                points = []

        # Upload remaining points
        if points:
            self.client.upsert(collection_name=self.FRAMES_COLLECTION, points=points)
            logger.info(f"Uploaded {len(points)} frame embeddings to Qdrant")

        return len(embeddings)

    def store_object_embeddings(
        self, embeddings: Dict[str, np.ndarray], paths: List[str], batch_size: int = 100
    ) -> int:
        """
        Store object embeddings in Qdrant.

        Args:
            embeddings: Dict mapping object keys to embedding vectors
            paths: List of S3 storage paths (parallel to embeddings dict keys)
            batch_size: Number of vectors to upload per batch

        Returns:
            Number of embeddings stored
        """
        points = []
        keys = list(embeddings.keys())

        for idx, key in enumerate(keys):
            embedding = embeddings[key]
            path = paths[idx] if idx < len(paths) else f"objects/{key}"

            # Extract video name from key
            video_name = key.split("/")[0] if "/" in key else "unknown"

            point = PointStruct(
                id=idx,
                vector=embedding.tolist(),
                payload={
                    "key": key,
                    "path": path,
                    "video_name": video_name,
                    "type": "object",
                },
            )
            points.append(point)

            # Upload in batches
            if len(points) >= batch_size:
                self.client.upsert(
                    collection_name=self.OBJECTS_COLLECTION, points=points
                )
                logger.info(f"Uploaded {len(points)} object embeddings to Qdrant")
                points = []

        # Upload remaining points
        if points:
            self.client.upsert(collection_name=self.OBJECTS_COLLECTION, points=points)
            logger.info(f"Uploaded {len(points)} object embeddings to Qdrant")

        return len(embeddings)

    def search_frames(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        video_name: Optional[str] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar frames.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            video_name: Optional filter by video name

        Returns:
            List of (path, similarity_score, metadata) tuples
        """
        query_filter = None
        if video_name:
            query_filter = Filter(
                must=[
                    FieldCondition(key="video_name", match=MatchValue(value=video_name))
                ]
            )

        results = self.client.query_points(
            collection_name=self.FRAMES_COLLECTION,
            query=query_vector.tolist(),
            limit=limit,
            query_filter=query_filter,
        ).points

        return [
            (
                hit.payload["path"],
                hit.score,
                {
                    "video_name": hit.payload.get("video_name"),
                    "frame_index": hit.payload.get("frame_index"),
                    "timestamp": hit.payload.get("timestamp", 0.0),
                },
            )
            for hit in results
        ]

    def search_objects(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        video_name: Optional[str] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar objects.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            video_name: Optional filter by video name

        Returns:
            List of (path, similarity_score, metadata) tuples
        """
        query_filter = None
        if video_name:
            query_filter = Filter(
                must=[
                    FieldCondition(key="video_name", match=MatchValue(value=video_name))
                ]
            )

        results = self.client.query_points(
            collection_name=self.OBJECTS_COLLECTION,
            query=query_vector.tolist(),
            limit=limit,
            query_filter=query_filter,
        ).points

        return [
            (
                hit.payload["path"],
                hit.score,
                {
                    "video_name": hit.payload.get("video_name"),
                    "frame_index": hit.payload.get("frame_index"),
                    "object_index": hit.payload.get("object_index"),
                    "timestamp": hit.payload.get("timestamp", 0.0),
                },
            )
            for hit in results
        ]

    def get_collection_info(self, collection: str) -> Dict:
        """Get information about a collection"""
        try:
            info = self.client.get_collection(collection_name=collection)
            return {
                "points_count": info.points_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}

    def delete_collection(self, collection: str) -> bool:
        """Delete a collection"""
        try:
            self.client.delete_collection(collection_name=collection)
            logger.info(f"Deleted collection: {collection}")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False

    def clear_all_data(self) -> bool:
        """Clear all embeddings (delete and recreate collections)"""
        try:
            for collection in [self.FRAMES_COLLECTION, self.OBJECTS_COLLECTION]:
                self.delete_collection(collection)
            self._ensure_collections()
            logger.info("Cleared all Qdrant data")
            return True
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            return False
