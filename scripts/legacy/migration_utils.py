"""
Utilities for data migration between storage backends.
Common functions used by migration scripts.
"""

import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import time

from ...storage import get_storage_manager, StorageBackend

logger = logging.getLogger(__name__)


class MigrationProgress:
    """Track migration progress and statistics"""

    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.successful_uploads = 0
        self.failed_uploads = 0
        self.start_time = None
        self.failed_files: List[str] = []

    def start(self, total_files: int):
        """Start migration tracking"""
        self.total_files = total_files
        self.start_time = time.time()
        logger.info(f"Starting migration of {total_files} files")

    def update(self, file_path: str, success: bool):
        """Update progress with file result"""
        self.processed_files += 1
        if success:
            self.successful_uploads += 1
        else:
            self.failed_uploads += 1
            self.failed_files.append(file_path)

        # Log progress every 100 files
        if self.processed_files % 100 == 0:
            self.log_progress()

    def log_progress(self):
        """Log current progress"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            rate = self.processed_files / elapsed if elapsed > 0 else 0
            estimated_remaining = (
                (self.total_files - self.processed_files) / rate if rate > 0 else 0
            )

            logger.info(
                f"Progress: {self.processed_files}/{self.total_files} "
                f"({self.processed_files/self.total_files*100:.1f}%) "
                f"Success: {self.successful_uploads}, Failed: {self.failed_uploads}, "
                f"Rate: {rate:.1f} files/sec, ETA: {estimated_remaining/60:.1f} min"
            )

    def finish(self):
        """Finish migration and log final stats"""
        if self.start_time:
            total_time = time.time() - self.start_time
            success_rate = (
                self.successful_uploads / self.total_files * 100
                if self.total_files > 0
                else 0
            )

            logger.info(
                f"Migration completed in {total_time/60:.1f} minutes. "
                f"Success rate: {success_rate:.1f}% "
                f"({self.successful_uploads}/{self.total_files})"
            )

            if self.failed_files:
                logger.warning(f"Failed to migrate {len(self.failed_files)} files")
                for failed_file in self.failed_files[:10]:  # Log first 10 failures
                    logger.warning(f"Failed: {failed_file}")
                if len(self.failed_files) > 10:
                    logger.warning(f"... and {len(self.failed_files) - 10} more")


def discover_files(directory: Path, extensions: List[str]) -> List[Path]:
    """
    Discover files in directory with given extensions.

    Args:
        directory: Directory to search
        extensions: List of file extensions (e.g. ['.jpg', '.png'])

    Returns:
        List of file paths
    """
    files = []
    for ext in extensions:
        files.extend(directory.rglob(f"*{ext}"))

    logger.info(
        f"Discovered {len(files)} files with extensions {extensions} in {directory}"
    )
    return files


def migrate_files(
    files: List[Path],
    source_storage: Optional[StorageBackend],
    target_storage: StorageBackend,
    base_source_path: Path,
    target_prefix: str = "",
) -> MigrationProgress:
    """
    Migrate files from source to target storage.

    Args:
        files: List of file paths to migrate
        source_storage: Source storage backend (None for local files)
        target_storage: Target storage backend
        base_source_path: Base path for calculating relative paths
        target_prefix: Prefix for target paths

    Returns:
        MigrationProgress object with results
    """
    progress = MigrationProgress()
    progress.start(len(files))

    for file_path in files:
        try:
            # Calculate relative path and target key
            relative_path = file_path.relative_to(base_source_path)
            target_key = f"{target_prefix}/{relative_path}".replace("\\", "/").strip(
                "/"
            )

            # Upload file
            if source_storage is None:
                # Local file
                success = target_storage.upload_file(str(file_path), target_key)
            else:
                # Storage to storage migration (not implemented in this basic version)
                logger.error("Storage-to-storage migration not implemented")
                success = False

            progress.update(str(file_path), success)

        except Exception as e:
            logger.error(f"Error migrating {file_path}: {e}")
            progress.update(str(file_path), False)

    progress.finish()
    return progress


def check_migration_status(
    files: List[Path],
    storage: StorageBackend,
    base_source_path: Path,
    target_prefix: str = "",
) -> Dict[str, List[str]]:
    """
    Check which files have been successfully migrated.

    Returns:
        Dict with 'migrated', 'missing', and 'failed' lists
    """
    status = {"migrated": [], "missing": [], "failed": []}

    for file_path in files:
        try:
            relative_path = file_path.relative_to(base_source_path)
            target_key = f"{target_prefix}/{relative_path}".replace("\\", "/").strip(
                "/"
            )

            if storage.file_exists(target_key):
                status["migrated"].append(str(file_path))
            else:
                status["missing"].append(str(file_path))

        except Exception as e:
            logger.error(f"Error checking status for {file_path}: {e}")
            status["failed"].append(str(file_path))

    logger.info(
        f"Migration status: {len(status['migrated'])} migrated, "
        f"{len(status['missing'])} missing, {len(status['failed'])} failed"
    )

    return status


def estimate_migration_size(files: List[Path]) -> Dict[str, float]:
    """
    Estimate total size of files to migrate.

    Returns:
        Dict with size information in various units
    """
    total_bytes = 0

    for file_path in files:
        try:
            total_bytes += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Could not get size for {file_path}: {e}")

    return {
        "bytes": total_bytes,
        "kb": total_bytes / 1024,
        "mb": total_bytes / (1024 * 1024),
        "gb": total_bytes / (1024 * 1024 * 1024),
        "file_count": len(files),
    }
