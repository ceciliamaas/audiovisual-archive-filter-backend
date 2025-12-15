"""
Modern migration script for uploading objects to S3 storage.
Replaces the original upload_objects_to_s3.py with improved architecture.
"""

import sys
import logging
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.storage import get_storage_manager
from migration_utils import discover_files, migrate_files, estimate_migration_size

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main migration function for objects"""

    # Configuration
    source_dir = Path("app/cropped_objects")
    target_prefix = "objects"
    extensions = [".jpg", ".jpeg", ".png"]

    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        return

    # Get storage manager
    try:
        storage_manager = get_storage_manager()
        target_storage = storage_manager.get_storage()
        logger.info(f"Using storage backend: {target_storage.__class__.__name__}")
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
        return

    # Discover files
    files = discover_files(source_dir, extensions)
    if not files:
        logger.warning("No files found to migrate")
        return

    # Estimate size
    size_info = estimate_migration_size(files)
    logger.info(
        f"Migration plan: {size_info['file_count']} files, "
        f"{size_info['mb']:.1f} MB total"
    )

    # Confirm migration
    response = input(f"Migrate {len(files)} objects to {target_prefix}? (y/N): ")
    if response.lower() != "y":
        logger.info("Migration cancelled")
        return

    # Perform migration
    progress = migrate_files(
        files=files,
        source_storage=None,  # Local files
        target_storage=target_storage,
        base_source_path=source_dir,
        target_prefix=target_prefix,
    )

    # Summary
    success_rate = progress.successful_uploads / progress.total_files * 100
    logger.info(f"Migration completed with {success_rate:.1f}% success rate")

    if progress.failed_files:
        logger.warning(f"Failed files: {len(progress.failed_files)}")
        failed_log = Path("migration_failures_objects.log")
        with open(failed_log, "w") as f:
            for failed_file in progress.failed_files:
                f.write(f"{failed_file}\n")
        logger.info(f"Failed files logged to: {failed_log}")


if __name__ == "__main__":
    main()
