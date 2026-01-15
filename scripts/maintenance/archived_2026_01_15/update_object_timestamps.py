#!/usr/bin/env python3
"""
Script to update object embeddings in Qdrant with timestamps.
This adds timestamp information to existing object embeddings based on their frame index.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import cv2
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Add src and scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from src.storage.qdrant import QdrantStorage
from scripts.pipeline.naming import NamingConvention


def get_video_fps(video_name: str) -> float:
    """Get FPS for a video."""
    video_path = NamingConvention.video_local_path(video_name)
    if not video_path.exists():
        print(f"Warning: Video file not found: {video_path}")
        return 1.0

    cap = cv2.VideoCapture(str(video_path))
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 1.0
    cap.release()
    return video_fps


def update_object_timestamps():
    """Update all object embeddings with timestamps based on frame index."""
    print("🔄 Updating object timestamps in Qdrant...")
    print("=" * 60)

    qdrant = QdrantStorage()

    # Get all objects from Qdrant
    print("\n1️⃣ Fetching objects from Qdrant...")
    try:
        # Scroll through all objects
        objects, _ = qdrant.client.scroll(
            collection_name=QdrantStorage.OBJECTS_COLLECTION,
            limit=10000,
        )

        print(f"   Found {len(objects)} objects")
    except Exception as e:
        print(f"❌ Failed to fetch objects: {e}")
        return False

    # Group objects by video name
    print("\n2️⃣ Grouping objects by video...")
    video_objects = {}
    for obj in objects:
        video_name = obj.payload.get("video_name", "unknown")
        if video_name not in video_objects:
            video_objects[video_name] = []
        video_objects[video_name].append(obj)

    print(f"   Found {len(video_objects)} videos")

    # Update timestamps for each video
    print("\n3️⃣ Updating timestamps...")
    total_updated = 0

    for video_name, objs in video_objects.items():
        print(f"\n   Processing: {video_name}")

        # Get video FPS
        video_fps = get_video_fps(video_name)
        target_fps = 1  # Default from pipeline config
        frame_interval = max(1, int(video_fps / target_fps))

        print(f"   Video FPS: {video_fps}, Frame interval: {frame_interval}")

        # Update each object
        points_to_update = []
        for obj in tqdm(objs, desc=f"   Updating {video_name}", leave=False):
            frame_index = obj.payload.get("frame_index")

            if frame_index is None:
                # Try to parse from key
                key = obj.payload.get("key", "")
                object_name = key.split("/")[-1] if "/" in key else key
                indices = NamingConvention.parse_object_indices(object_name)
                if indices:
                    frame_index = indices[0]
                    object_index = indices[1]
                    # Update payload with indices too
                    obj.payload["frame_index"] = frame_index
                    obj.payload["object_index"] = object_index

            if frame_index is not None:
                # Calculate timestamp
                timestamp = (frame_index * frame_interval) / video_fps
                obj.payload["timestamp"] = timestamp

                # Add to update list (just store id and payload, not vector)
                points_to_update.append(
                    type("Point", (), {"id": obj.id, "payload": obj.payload})()
                )

        # Batch update
        if points_to_update:
            try:
                # Update points using update method which only updates payload
                for point in points_to_update:
                    qdrant.client.set_payload(
                        collection_name=QdrantStorage.OBJECTS_COLLECTION,
                        payload=point.payload,
                        points=[point.id],
                    )
                total_updated += len(points_to_update)
                print(f"   ✅ Updated {len(points_to_update)} objects")
            except Exception as e:
                print(f"   ❌ Failed to update objects: {e}")

    print("\n" + "=" * 60)
    print(f"✅ Successfully updated {total_updated} object embeddings with timestamps!")
    print(f"   Objects from {len(video_objects)} videos were processed.")
    return True


def main():
    success = update_object_timestamps()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
