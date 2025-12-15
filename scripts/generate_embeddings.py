#!/usr/bin/env python3
"""
Generate embeddings for existing frames and objects using the new storage system
"""

import os
import sys
import time
import pickle
from pathlib import Path
from dotenv import load_dotenv
import replicate
from PIL import Image
import numpy as np

# Load environment variables
load_dotenv()

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.storage import get_storage_manager
from src.core.embeddings import EmbeddingsManager


def setup_replicate():
    """Initialize Replicate client"""
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        raise RuntimeError("Missing REPLICATE_API_TOKEN in .env")

    return replicate.Client(api_token=api_token)


def compute_image_embedding(client, image_path):
    """Compute CLIP embedding for an image"""
    try:
        with open(image_path, "rb") as f:
            result = client.run("openai/clip", input={"image": f, "model": "ViT-B/32"})
        return np.array(result)
    except Exception as e:
        print(f"Error computing embedding for {image_path}: {e}")
        return None


def main():
    print("🚀 Starting embeddings generation...")

    # Initialize components
    client = setup_replicate()
    storage = get_storage_manager()

    # Check local data directory
    data_dir = PROJECT_ROOT / "data"
    frames_dir = data_dir / "frames"
    objects_dir = data_dir / "objects"

    if not frames_dir.exists():
        print("❌ No frames directory found. Please extract frames first.")
        return

    print(f"📁 Processing frames from: {frames_dir}")
    print(f"📁 Processing objects from: {objects_dir}")

    # Collect frame files
    frame_files = []
    for video_dir in frames_dir.glob("video_*"):
        if video_dir.is_dir():
            for frame_file in video_dir.glob("*.jpg"):
                frame_files.append(frame_file)

    print(f"🖼️  Found {len(frame_files)} frame files")

    # Compute frame embeddings
    frame_embeddings = {}
    frame_paths = {}

    print("🧠 Computing frame embeddings...")
    start_time = time.time()

    for i, frame_path in enumerate(frame_files):
        if i % 50 == 0:
            print(
                f"   Progress: {i}/{len(frame_files)} ({i/len(frame_files)*100:.1f}%)"
            )

        # Create storage key (relative path from frames directory)
        relative_path = frame_path.relative_to(frames_dir)
        storage_key = f"frames/{relative_path}"

        # Compute embedding
        embedding = compute_image_embedding(client, frame_path)
        if embedding is not None:
            frame_embeddings[str(relative_path)] = embedding
            frame_paths[str(relative_path)] = storage_key

    elapsed_time = time.time() - start_time
    print(
        f"✅ Computed {len(frame_embeddings)} frame embeddings in {elapsed_time:.1f}s"
    )

    # Compute object embeddings if objects exist
    object_embeddings = {}
    object_paths = {}

    if objects_dir.exists():
        object_files = list(objects_dir.glob("**/*.jpg"))
        print(f"🎯 Found {len(object_files)} object files")

        print("🧠 Computing object embeddings...")
        start_time = time.time()

        for i, object_path in enumerate(object_files):
            if i % 50 == 0:
                print(
                    f"   Progress: {i}/{len(object_files)} ({i/len(object_files)*100:.1f}%)"
                )

            # Create storage key
            relative_path = object_path.relative_to(objects_dir)
            storage_key = f"objects/{relative_path}"

            # Compute embedding
            embedding = compute_image_embedding(client, object_path)
            if embedding is not None:
                object_embeddings[str(relative_path)] = embedding
                object_paths[str(relative_path)] = storage_key

        elapsed_time = time.time() - start_time
        print(
            f"✅ Computed {len(object_embeddings)} object embeddings in {elapsed_time:.1f}s"
        )

    # Save embeddings locally
    embeddings_dir = data_dir / "embeddings"
    embeddings_dir.mkdir(exist_ok=True)

    print("💾 Saving embeddings locally...")

    # Save frame embeddings
    with open(embeddings_dir / "frame_embeddings.pkl", "wb") as f:
        pickle.dump(frame_embeddings, f)

    with open(embeddings_dir / "frame_paths.pkl", "wb") as f:
        pickle.dump(frame_paths, f)

    # Save object embeddings
    with open(embeddings_dir / "object_embeddings.pkl", "wb") as f:
        pickle.dump(object_embeddings, f)

    with open(embeddings_dir / "object_paths.pkl", "wb") as f:
        pickle.dump(object_paths, f)

    print("📤 Uploading embeddings to storage...")

    # Upload to storage
    try:
        for embedding_file in embeddings_dir.glob("*.pkl"):
            storage_key = f"embeddings/{embedding_file.name}"
            with open(embedding_file, "rb") as f:
                storage.put(storage_key, f.read())
            print(f"   ✅ Uploaded {storage_key}")
    except Exception as e:
        print(f"❌ Error uploading to storage: {e}")
        print("💡 Embeddings saved locally in data/embeddings/")

    print("🎉 Embeddings generation complete!")
    print(f"   📊 Frame embeddings: {len(frame_embeddings)}")
    print(f"   🎯 Object embeddings: {len(object_embeddings)}")


if __name__ == "__main__":
    main()
