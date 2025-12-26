"""
Modern migration script for uploading frame embeddings to S3 storage.
Replaces the original migration scripts with improved architecture.
"""

import sys
import logging
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.storage import get_storage_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main migration function for embeddings"""

    # Configuration
    embeddings_dir = Path("app/embeddings")  # or wherever your embeddings are
    target_prefix = "embeddings"

    embedding_files = [
        "frame_embeddings.pkl",
        "object_embeddings.pkl",
        "frame_paths.pkl",
        "object_paths.pkl",
    ]

    if not embeddings_dir.exists():
        logger.error(f"Embeddings directory not found: {embeddings_dir}")
        return

    # Get storage manager
    try:
        storage_manager = get_storage_manager()
        target_storage = storage_manager.get_storage()
        logger.info(f"Using storage backend: {target_storage.__class__.__name__}")
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
        return

    # Check which files exist
    existing_files = []
    for filename in embedding_files:
        file_path = embeddings_dir / filename
        if file_path.exists():
            existing_files.append(file_path)
            logger.info(f"Found: {filename}")
        else:
            logger.warning(f"Missing: {filename}")

    if not existing_files:
        logger.error("No embedding files found")
        return

    # Confirm migration
    response = input(f"Migrate {len(existing_files)} embedding files? (y/N): ")
    if response.lower() != "y":
        logger.info("Migration cancelled")
        return

    # Perform migration
    successful = 0
    failed = 0

    for file_path in existing_files:
        try:
            target_key = f"{target_prefix}/{file_path.name}"

            if target_storage.upload_file(str(file_path), target_key):
                logger.info(f"✅ Uploaded: {file_path.name}")
                successful += 1
            else:
                logger.error(f"❌ Failed: {file_path.name}")
                failed += 1

        except Exception as e:
            logger.error(f"❌ Error uploading {file_path.name}: {e}")
            failed += 1

    # Summary
    total = successful + failed
    success_rate = (successful / total * 100) if total > 0 else 0
    logger.info(
        f"Migration completed: {successful}/{total} files ({success_rate:.1f}% success)"
    )


if __name__ == "__main__":
    main()
