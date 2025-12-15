#!/usr/bin/env python3
"""
CLIP Embeddings Computation Script

Computes CLIP embeddings for any JPG images:
1. Processes frames from data/frames/
2. Processes objects from data/objects/
3. Stores embeddings and paths in S3

The script can process any JPG files and is designed to work with
the new data/ directory structure.

Usage:
    python compute_clip_embeddings.py [--frames-only] [--objects-only] [--force]
"""

import os
import sys
import pickle
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import time

import numpy as np
from PIL import Image
from dotenv import load_dotenv
import replicate

# Add src to path for storage imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.storage import get_storage_manager

# =============================================================================
# Configuration
# =============================================================================

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise RuntimeError("Missing REPLICATE_API_TOKEN in .env")

client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# Directories
DATA_DIR = PROJECT_ROOT / "data"
FRAMES_DIR = DATA_DIR / "frames"
OBJECTS_DIR = DATA_DIR / "objects"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

# Create directories
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# CLIP Embedding Functions
# =============================================================================


def compute_clip_embedding(image_path: Path) -> Optional[np.ndarray]:
    """
    Compute CLIP embedding for an image

    Args:
        image_path: Path to image file

    Returns:
        CLIP embedding as numpy array, or None if failed
    """
    try:
        with open(image_path, "rb") as f:
            output = client.run("openai/clip", input={"image": f, "model": "ViT-B/32"})

        if output and "embedding" in output:
            embedding = np.array(output["embedding"], dtype=np.float32)
            # Normalize embedding
            embedding = embedding / np.linalg.norm(embedding)
            return embedding
        else:
            print(f"❌ No embedding output for {image_path}")
            return None

    except Exception as e:
        print(f"❌ CLIP embedding failed for {image_path}: {e}")
        return None


def load_existing_embeddings(storage, embedding_type: str) -> Dict[str, np.ndarray]:
    """
    Load existing embeddings from S3

    Args:
        storage: Storage manager instance
        embedding_type: 'frame' or 'object'

    Returns:
        Dictionary of existing embeddings
    """
    embeddings_file = f"embeddings/{embedding_type}_embeddings.pkl"

    try:
        if storage.file_exists(embeddings_file):
            print(f"📥 Loading existing {embedding_type} embeddings from S3...")
            embeddings = storage.download_pickle(embeddings_file)
            if embeddings:
                print(
                    f"   Found {len(embeddings)} existing {embedding_type} embeddings"
                )
                return embeddings
    except Exception as e:
        print(f"⚠️  Could not load existing {embedding_type} embeddings: {e}")

    return {}


def save_embeddings_to_s3(
    storage, embeddings: Dict[str, np.ndarray], paths: List[str], embedding_type: str
) -> bool:
    """
    Save embeddings and paths to S3

    Args:
        storage: Storage manager instance
        embeddings: Dictionary of embeddings
        paths: List of file paths
        embedding_type: 'frame' or 'object'

    Returns:
        True if successful
    """
    try:
        # Save embeddings
        embeddings_file = f"embeddings/{embedding_type}_embeddings.pkl"
        paths_file = f"embeddings/{embedding_type}_paths.pkl"

        # Save to local temp files first
        temp_embeddings_file = EMBEDDINGS_DIR / f"{embedding_type}_embeddings.pkl"
        temp_paths_file = EMBEDDINGS_DIR / f"{embedding_type}_paths.pkl"

        with open(temp_embeddings_file, "wb") as f:
            pickle.dump(embeddings, f)

        with open(temp_paths_file, "wb") as f:
            pickle.dump(paths, f)

        print(f"📤 Uploading {embedding_type} embeddings to S3...")

        # Upload embeddings
        with open(temp_embeddings_file, "rb") as f:
            storage.put(embeddings_file, f.read())

        # Upload paths
        with open(temp_paths_file, "rb") as f:
            storage.put(paths_file, f.read())

        print(f"✅ Uploaded {embedding_type} embeddings ({len(embeddings)} items)")
        return True

    except Exception as e:
        print(f"❌ Failed to save {embedding_type} embeddings to S3: {e}")
        return False


# =============================================================================
# Processing Functions
# =============================================================================


def process_frames(storage, force_recompute: bool = False) -> bool:
    """
    Process all frame images to compute embeddings

    Args:
        storage: Storage manager instance
        force_recompute: If True, recompute all embeddings

    Returns:
        True if successful
    """
    print("\n🖼️  Processing frame embeddings...")

    # Check if frames directory exists
    if not FRAMES_DIR.exists():
        print(f"⚠️  Frames directory not found: {FRAMES_DIR}")
        return False

    # Find all frame files
    frame_files = []
    for video_dir in FRAMES_DIR.glob("video_*"):
        if video_dir.is_dir():
            for frame_file in video_dir.glob("*.jpg"):
                frame_files.append(frame_file)

    if not frame_files:
        print(f"⚠️  No frame files found in {FRAMES_DIR}")
        return False

    print(f"   Found {len(frame_files)} frame files")

    # Load existing embeddings
    existing_embeddings = (
        {} if force_recompute else load_existing_embeddings(storage, "frame")
    )

    # Process frames
    frame_embeddings = existing_embeddings.copy()
    frame_paths = []
    processed = 0
    start_time = time.time()

    for i, frame_path in enumerate(frame_files):
        # Create relative path key
        relative_path = frame_path.relative_to(FRAMES_DIR)
        path_key = str(relative_path)

        # Skip if already computed and not forcing recompute
        if not force_recompute and path_key in existing_embeddings:
            frame_paths.append(f"frames/{relative_path}")
            continue

        # Compute embedding
        embedding = compute_clip_embedding(frame_path)
        if embedding is not None:
            frame_embeddings[path_key] = embedding
            frame_paths.append(f"frames/{relative_path}")
            processed += 1

        # Progress update
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            print(
                f"   Progress: {i+1}/{len(frame_files)} ({(i+1)/len(frame_files)*100:.1f}%) "
                f"- {processed} new embeddings - {elapsed:.1f}s"
            )

    elapsed_total = time.time() - start_time
    print(f"   ✅ Processed {processed} new frame embeddings in {elapsed_total:.1f}s")
    print(f"   📊 Total frame embeddings: {len(frame_embeddings)}")

    # Save to S3
    return save_embeddings_to_s3(storage, frame_embeddings, frame_paths, "frame")


def process_objects(storage, force_recompute: bool = False) -> bool:
    """
    Process all object images to compute embeddings

    Args:
        storage: Storage manager instance
        force_recompute: If True, recompute all embeddings

    Returns:
        True if successful
    """
    print("\n🎯 Processing object embeddings...")

    # Check if objects directory exists
    if not OBJECTS_DIR.exists():
        print(f"⚠️  Objects directory not found: {OBJECTS_DIR}")
        return False

    # Find all object files in video subdirectories
    object_files = []
    for video_dir in OBJECTS_DIR.glob("video_*"):
        if video_dir.is_dir():
            for object_file in video_dir.glob("*.jpg"):
                object_files.append(object_file)

    if not object_files:
        print(f"⚠️  No object files found in {OBJECTS_DIR}")
        return False

    print(f"   Found {len(object_files)} object files")

    # Load existing embeddings
    existing_embeddings = (
        {} if force_recompute else load_existing_embeddings(storage, "object")
    )

    # Process objects
    object_embeddings = existing_embeddings.copy()
    object_paths = []
    processed = 0
    start_time = time.time()

    for i, object_path in enumerate(object_files):
        # Create relative path key
        relative_path = object_path.relative_to(OBJECTS_DIR)
        path_key = str(relative_path)

        # Skip if already computed and not forcing recompute
        if not force_recompute and path_key in existing_embeddings:
            object_paths.append(f"objects/{relative_path}")
            continue

        # Compute embedding
        embedding = compute_clip_embedding(object_path)
        if embedding is not None:
            object_embeddings[path_key] = embedding
            object_paths.append(f"objects/{relative_path}")
            processed += 1

        # Progress update
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            print(
                f"   Progress: {i+1}/{len(object_files)} ({(i+1)/len(object_files)*100:.1f}%) "
                f"- {processed} new embeddings - {elapsed:.1f}s"
            )

    elapsed_total = time.time() - start_time
    print(f"   ✅ Processed {processed} new object embeddings in {elapsed_total:.1f}s")
    print(f"   📊 Total object embeddings: {len(object_embeddings)}")

    # Save to S3
    return save_embeddings_to_s3(storage, object_embeddings, object_paths, "object")


# =============================================================================
# Main Function
# =============================================================================


def main():
    """Main processing function"""
    parser = argparse.ArgumentParser(
        description="Compute CLIP embeddings for frames and objects"
    )
    parser.add_argument(
        "--frames-only", action="store_true", help="Process only frame embeddings"
    )
    parser.add_argument(
        "--objects-only", action="store_true", help="Process only object embeddings"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force recompute all embeddings"
    )

    args = parser.parse_args()

    print("🧠 Starting CLIP embeddings computation...")

    # Initialize storage manager
    storage = get_storage_manager()
    print(f"📦 Using storage: {storage.get_storage().get_info()['backend_type']}")

    success = True

    # Process frames (unless objects-only)
    if not args.objects_only:
        if not process_frames(storage, args.force):
            success = False

    # Process objects (unless frames-only)
    if not args.frames_only:
        if not process_objects(storage, args.force):
            success = False

    if success:
        print("\n🎉 Embeddings computation completed successfully!")
        print("   All embeddings are stored in S3 and ready for search")
    else:
        print("\n❌ Some embeddings computation failed")
        print("   Check error messages above")


if __name__ == "__main__":
    main()
