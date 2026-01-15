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
        """Create collections if they don't exist and ensure payload indexes"""
        from qdrant_client.models import PayloadSchemaType

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

            # Create payload index on video_name field for efficient filtering
            try:
                self.client.create_payload_index(
                    collection_name=collection,
                    field_name="video_name",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                logger.info(f"Created payload index on video_name for {collection}")
            except Exception as e:
                # Index might already exist, that's okay
                logger.debug(f"Payload index may already exist for {collection}: {e}")

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
        import hashlib

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

            # Use deterministic ID based on path to enable proper upsert behavior
            point_id = hashlib.md5(paths.get(key, key).encode()).hexdigest()

            point = PointStruct(
                id=point_id,
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
        self,
        embeddings: Dict[str, np.ndarray],
        paths: Dict[str, str],
        timestamps: Optional[Dict[str, float]] = None,
        batch_size: int = 100,
    ) -> int:
        """
        Store object embeddings in Qdrant.

        Args:
            embeddings: Dict mapping object keys to embedding vectors
            paths: Dict mapping object keys to S3 storage paths
            timestamps: Dict mapping object keys to timestamp in seconds (optional)
            batch_size: Number of vectors to upload per batch

        Returns:
            Number of embeddings stored
        """
        import hashlib

        if timestamps is None:
            timestamps = {}

        points = []

        for key, embedding in embeddings.items():
            path = paths.get(key, f"objects/{key}")

            # Extract video name and object name from key
            video_name = key.split("/")[0] if "/" in key else "unknown"
            object_name = key.split("/")[-1] if "/" in key else key

            # Parse frame and object indices from object filename
            from scripts.pipeline.naming import NamingConvention

            indices = NamingConvention.parse_object_indices(object_name)
            frame_index = indices[0] if indices else None
            object_index = indices[1] if indices else None

            # Try to load bounding box metadata
            bbox = None
            if frame_index is not None and object_index is not None:
                bbox_metadata_path = NamingConvention.object_local_path(
                    video_name, frame_index, object_index
                ).with_suffix(".json")
                if bbox_metadata_path.exists():
                    import json

                    try:
                        with open(bbox_metadata_path, "r") as f:
                            bbox_data = json.load(f)
                            bbox = bbox_data.get("bbox")
                    except Exception as e:
                        logger.warning(f"Failed to read bbox metadata for {key}: {e}")

            # Use deterministic ID based on path to enable proper upsert behavior
            point_id = hashlib.md5(path.encode()).hexdigest()

            payload = {
                "key": key,
                "path": path,
                "video_name": video_name,
                "type": "object",
                "frame_index": frame_index,
                "object_index": object_index,
                "timestamp": timestamps.get(key, 0.0),
            }

            # Add bbox if available
            if bbox:
                payload["bbox"] = bbox

            # Add corresponding frame path for displaying full frame with bbox
            if frame_index is not None:
                frame_key = f"{video_name}/frame_{frame_index:05d}.jpg"
                frame_path = f"frames/{frame_key}"
                payload["frame_path"] = frame_path

            point = PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload,
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

        result_list = []
        for hit in results:
            video_name = hit.payload.get("video_name")
            frame_index = hit.payload.get("frame_index")

            # Get frame_path from payload, or construct it if not present (for backward compatibility)
            frame_path = hit.payload.get("frame_path")
            if not frame_path and video_name and frame_index is not None:
                frame_path = f"frames/{video_name}/frame_{frame_index:05d}.jpg"

            metadata = {
                "video_name": video_name,
                "frame_index": frame_index,
                "object_index": hit.payload.get("object_index"),
                "timestamp": hit.payload.get("timestamp", 0.0),
                "bbox": hit.payload.get("bbox"),
                "frame_path": frame_path,
            }

            result_list.append((hit.payload["path"], hit.score, metadata))

        return result_list

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
