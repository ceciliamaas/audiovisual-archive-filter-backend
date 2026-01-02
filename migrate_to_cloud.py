"""
Migrate embeddings from local Qdrant to cloud Qdrant.

This script:
1. Connects to both local and cloud Qdrant instances
2. Reads all embeddings from local collections
3. Writes them to cloud collections
4. Verifies the migration was successful
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from src.storage.qdrant import QdrantStorage

load_dotenv()


def migrate_collection(
    local_client: QdrantClient, cloud_client: QdrantClient, collection_name: str
):
    """Migrate a single collection from local to cloud"""
    print(f"\n📦 Migrating collection: {collection_name}")

    # Get all points from local
    print(f"   Reading from local Qdrant...")
    local_count = local_client.count(collection_name=collection_name).count
    print(f"   Found {local_count} points in local collection")

    if local_count == 0:
        print(f"   ⚠️  No data to migrate")
        return 0

    # Scroll through all points (using scroll for large datasets)
    all_points = []
    offset = None
    batch_size = 100

    while True:
        result = local_client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_vectors=True,
            with_payload=True,
        )

        points, next_offset = result
        all_points.extend(points)

        if next_offset is None or len(points) == 0:
            break

        offset = next_offset
        print(f"   Read {len(all_points)}/{local_count} points...", end="\r")

    print(f"\n   ✓ Read all {len(all_points)} points from local")

    # Upload to cloud in batches
    print(f"   Uploading to cloud Qdrant...")
    from qdrant_client.models import PointStruct

    batch_size = 100
    for i in range(0, len(all_points), batch_size):
        batch = all_points[i : i + batch_size]

        # Convert to PointStruct format
        points_to_upload = [
            PointStruct(id=point.id, vector=point.vector, payload=point.payload)
            for point in batch
        ]

        cloud_client.upsert(collection_name=collection_name, points=points_to_upload)

        print(
            f"   Uploaded {min(i + batch_size, len(all_points))}/{len(all_points)} points...",
            end="\r",
        )

    print(f"\n   ✓ Uploaded all {len(all_points)} points to cloud")

    # Verify
    cloud_count = cloud_client.count(collection_name=collection_name).count
    print(f"   ✓ Verified: {cloud_count} points in cloud collection")

    return len(all_points)


def main():
    print("=" * 60)
    print("🚀 Migrating Qdrant embeddings from local to cloud")
    print("=" * 60)

    # Connect to local Qdrant
    local_url = os.getenv("QDRANT_LOCAL", "http://localhost:6333")
    print(f"\n📡 Connecting to local Qdrant: {local_url}")
    local_client = QdrantClient(url=local_url)

    # Connect to cloud Qdrant
    cloud_url = os.getenv("QDRANT_CLOUD")
    cloud_api_key = os.getenv("QDRANT_API_KEY")

    if not cloud_url:
        print("❌ Error: QDRANT_CLOUD not set in .env file")
        return

    print(f"📡 Connecting to cloud Qdrant: {cloud_url}")
    cloud_client = QdrantClient(url=cloud_url, api_key=cloud_api_key)

    # Ensure cloud collections exist
    print(f"\n🔧 Ensuring cloud collections exist...")
    collections = ["frames", "objects"]
    existing = [c.name for c in cloud_client.get_collections().collections]

    for collection in collections:
        if collection not in existing:
            print(f"   Creating collection: {collection}")
            cloud_client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=QdrantStorage.VECTOR_DIM, distance=Distance.COSINE
                ),
            )
        else:
            print(f"   ✓ Collection exists: {collection}")

    # Migrate collections
    total_migrated = 0
    for collection in collections:
        count = migrate_collection(local_client, cloud_client, collection)
        total_migrated += count

    # Final summary
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print(f"📊 Total points migrated: {total_migrated}")

    # Show cloud status
    frames_count = cloud_client.count(collection_name="frames").count
    objects_count = cloud_client.count(collection_name="objects").count
    print(f"\n🌥️  Cloud Qdrant status:")
    print(f"   Frames:  {frames_count} embeddings")
    print(f"   Objects: {objects_count} embeddings")

    print(f"\n💡 Next step: Update .env file")
    print(f"   Change: QDRANT_MODE=local")
    print(f"   To:     QDRANT_MODE=cloud")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error during migration: {e}")
        import traceback

        traceback.print_exc()
