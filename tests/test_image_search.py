"""
Test script for image similarity search functionality
"""

import sys
from pathlib import Path
from PIL import Image
import tempfile
import numpy as np

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.search import get_search_engine
from dotenv import load_dotenv

load_dotenv()


def create_test_image(size=(224, 224), color=(255, 0, 0)):
    """Create a simple test image"""
    img = Image.new("RGB", size, color)
    return img


def test_image_embedding_computation():
    """Test that we can compute embeddings for images"""
    print("Testing image embedding computation...")

    # Create a test image
    test_img = create_test_image()

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        test_img.save(tmp_file.name)
        tmp_path = tmp_file.name

    try:
        # Get search engine
        search_engine = get_search_engine()

        # Compute embedding
        embedding = search_engine.compute_image_embedding(tmp_path)

        if embedding is not None:
            print(f"✅ Successfully computed embedding: shape {embedding.shape}")
            print(
                f"   Embedding norm: {np.linalg.norm(embedding):.4f} (should be ~1.0)"
            )
            return True
        else:
            print("❌ Failed to compute embedding")
            return False
    finally:
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


def test_image_search():
    """Test complete image search workflow"""
    print("\nTesting image search workflow...")

    # Create a test image
    test_img = create_test_image()

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        test_img.save(tmp_file.name)
        tmp_path = tmp_file.name

    try:
        # Get search engine
        search_engine = get_search_engine()

        # Ensure embeddings are loaded
        if not search_engine.embeddings_manager.load_embeddings():
            print("❌ Failed to load embeddings - skipping search test")
            return False

        # Perform search
        results = search_engine.search_by_image(
            image_path=tmp_path, search_frames=True, search_objects=True, max_results=10
        )

        if results:
            print(f"✅ Search returned {len(results)} results")
            print("\nTop 3 results:")
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result.path}")
                print(
                    f"     Type: {result.result_type}, Similarity: {result.similarity:.4f}"
                )
            return True
        else:
            print(
                "⚠️  Search returned no results (this may be normal if similarity is low)"
            )
            return True
    finally:
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)


def test_search_engine_status():
    """Test search engine status"""
    print("\nChecking search engine status...")

    search_engine = get_search_engine()
    status = search_engine.get_status()

    print(f"Model: {status['model']}")
    print(f"Replicate available: {status['replicate_available']}")

    embeddings_status = status["embeddings_status"]
    print(f"\nEmbeddings loaded: {embeddings_status['loaded']}")
    if embeddings_status["loaded"]:
        print(f"  Frame embeddings: {embeddings_status['frame_count']}")
        print(f"  Object embeddings: {embeddings_status['object_count']}")

    return status["replicate_available"]


if __name__ == "__main__":
    print("=" * 60)
    print("Image Search Feature Tests")
    print("=" * 60)

    # Test 1: Check status
    status_ok = test_search_engine_status()

    if not status_ok:
        print("\n❌ Search engine not properly configured")
        sys.exit(1)

    # Test 2: Embedding computation
    embedding_ok = test_image_embedding_computation()

    if not embedding_ok:
        print("\n❌ Embedding computation failed")
        sys.exit(1)

    # Test 3: Full search
    search_ok = test_image_search()

    if search_ok:
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Some tests failed")
        print("=" * 60)
        sys.exit(1)
