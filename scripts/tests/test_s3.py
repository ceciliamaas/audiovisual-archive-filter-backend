"""
Test script to upload just embeddings first
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from s3_storage import get_s3_client


def test_embeddings_upload():
    """Test uploading just the embeddings files"""

    try:
        s3_client = get_s3_client()
        print("✅ S3 connection successful!")
    except Exception as e:
        print(f"❌ S3 connection failed: {e}")
        return

    embeddings_dir = Path(__file__).parent / "app/embeddings"

    if not embeddings_dir.exists():
        print(f"❌ Embeddings directory not found: {embeddings_dir}")
        return

    # Get all .pkl files
    pkl_files = list(embeddings_dir.glob("*.pkl"))

    print(f"Found {len(pkl_files)} embedding files:")
    for f in pkl_files:
        print(f"  - {f.name} ({f.stat().st_size / (1024*1024):.1f} MB)")

    if not pkl_files:
        print("No .pkl files found")
        return

    success_count = 0

    for pkl_file in pkl_files:
        s3_key = f"embeddings/{pkl_file.name}"
        print(f"\nUploading {pkl_file.name}...")

        if s3_client.upload_file(pkl_file, s3_key):
            print(f"  ✅ Success")
            success_count += 1
        else:
            print(f"  ❌ Failed")

    print(f"\nUploaded {success_count}/{len(pkl_files)} files")

    # Test download
    if success_count > 0:
        print("\nTesting download...")
        test_data = s3_client.download_pickle("embeddings/frame_embeddings.pkl")
        if test_data is not None:
            print(f"✅ Download test successful - loaded {len(test_data)} embeddings")
        else:
            print("❌ Download test failed")


if __name__ == "__main__":
    test_embeddings_upload()
