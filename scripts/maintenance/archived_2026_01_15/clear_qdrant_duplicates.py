#!/usr/bin/env python3
"""
Script to clear all Qdrant data and remove duplicates.
Run this script, then re-run the embeddings computation step.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.storage.qdrant import QdrantStorage


def main():
    print("🗑️  Clearing Qdrant collections...")

    qdrant = QdrantStorage()

    # Get current counts
    frames_info = qdrant.get_collection_info(QdrantStorage.FRAMES_COLLECTION)
    objects_info = qdrant.get_collection_info(QdrantStorage.OBJECTS_COLLECTION)

    print(f"   Current frames: {frames_info.get('points_count', 0)}")
    print(f"   Current objects: {objects_info.get('points_count', 0)}")

    response = input("\n⚠️  This will delete all embeddings. Continue? (yes/no): ")

    if response.lower() != "yes":
        print("❌ Cancelled")
        return

    # Clear all data
    if qdrant.clear_all_data():
        print("✅ Successfully cleared all Qdrant data")
        print("\n📝 Next steps:")
        print("   1. Run the pipeline again to recompute embeddings:")
        print(
            "      python -m scripts.pipeline <video_name> --steps compute_embeddings"
        )
        print("   2. Or run the full pipeline for a new video:")
        print("      python -m scripts.pipeline <video_name>")
    else:
        print("❌ Failed to clear Qdrant data")
        sys.exit(1)


if __name__ == "__main__":
    main()
