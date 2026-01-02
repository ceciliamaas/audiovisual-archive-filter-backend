#!/usr/bin/env python3
"""
Migration script to unify two Storj buckets into one with homogeneous structure.

This script:
1. Lists all files from both source buckets
2. Reorganizes them according to the naming conventions in naming.py
3. Copies them to a unified target bucket

Usage:
    python scripts/migrate_storj_buckets.py \
        --source-bucket-1 old-bucket-1 \
        --source-bucket-2 old-bucket-2 \
        --target-bucket unified-bucket \
        --dry-run  # Remove this flag to actually perform the migration
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.pipeline.naming import NamingConvention
from src.config.settings import storage_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StorjMigration:
    """Handles migration between Storj buckets with structure normalization."""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str):
        """Initialize S3 client for Storj."""
        config = boto3.session.Config(
            read_timeout=60,
            connect_timeout=10,
            retries={"max_attempts": 5},
            signature_version="s3v4",
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            config=config,
        )
        logger.info(f"Initialized S3 client for {endpoint_url}")

    def list_all_objects(self, bucket_name: str) -> List[str]:
        """List all objects in a bucket."""
        logger.info(f"Listing objects in bucket: {bucket_name}")
        objects = []

        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket_name)

            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        objects.append(obj["Key"])

            logger.info(f"Found {len(objects)} objects in {bucket_name}")
            return objects

        except ClientError as e:
            logger.error(f"Error listing bucket {bucket_name}: {e}")
            return []

    def analyze_structure(self, objects: List[str]) -> Dict[str, List[str]]:
        """Analyze the structure of objects and categorize them."""
        structure = {
            "videos": [],
            "frames": [],
            "objects": [],
            "embeddings": [],
            "unknown": [],
        }

        for obj_key in objects:
            if obj_key.startswith("videos/") or obj_key.endswith(".mp4"):
                structure["videos"].append(obj_key)
            elif "frame" in obj_key.lower() and "_obj_" in obj_key.lower():
                structure["objects"].append(obj_key)
            elif "frame" in obj_key.lower():
                structure["frames"].append(obj_key)
            elif "embedding" in obj_key.lower() or obj_key.endswith(".pkl"):
                structure["embeddings"].append(obj_key)
            else:
                structure["unknown"].append(obj_key)

        return structure

    def normalize_key(
        self, old_key: str, video_name_mapping: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Normalize an S3 key to match naming conventions.

        Args:
            old_key: Original S3 key
            video_name_mapping: Optional mapping of old video names to new sanitized names

        Returns:
            Normalized S3 key or None if cannot be normalized
        """
        video_name_mapping = video_name_mapping or {}

        # Extract video name from various path formats
        parts = old_key.split("/")

        # Videos
        if old_key.endswith(".mp4"):
            video_name = Path(old_key).stem
            sanitized = NamingConvention.sanitize_video_name(video_name)
            return NamingConvention.video_s3_key(sanitized)

        # Frames: frames/video_name/frame_00042.jpg
        if "frame" in old_key.lower() and "_obj_" not in old_key.lower():
            # Try to extract video name and frame index
            if len(parts) >= 2:
                video_name = parts[-2] if len(parts) > 2 else parts[0]
                filename = parts[-1]

                # Map old video name to new name if provided
                sanitized_name = video_name_mapping.get(
                    video_name, NamingConvention.sanitize_video_name(video_name)
                )

                # Try to parse frame index from filename
                frame_idx = NamingConvention.parse_frame_index(filename)
                if frame_idx is not None:
                    return NamingConvention.frame_s3_key(sanitized_name, frame_idx)

                # Try to extract frame number from various formats
                import re

                match = re.search(r"(\d+)", filename)
                if match:
                    frame_idx = int(match.group(1))
                    return NamingConvention.frame_s3_key(sanitized_name, frame_idx)

        # Objects: objects/video_name/frame_00042_obj_003.jpg
        if "obj" in old_key.lower() or (
            "frame" in old_key.lower() and "object" in old_key.lower()
        ):
            if len(parts) >= 2:
                video_name = parts[-2] if len(parts) > 2 else parts[0]
                filename = parts[-1]

                sanitized_name = video_name_mapping.get(
                    video_name, NamingConvention.sanitize_video_name(video_name)
                )

                # Try to parse frame and object indices
                indices = NamingConvention.parse_object_indices(filename)
                if indices:
                    frame_idx, obj_idx = indices
                    return NamingConvention.object_s3_key(
                        sanitized_name, frame_idx, obj_idx
                    )

                # Try to extract numbers from various formats
                import re

                numbers = re.findall(r"(\d+)", filename)
                if len(numbers) >= 2:
                    frame_idx = int(numbers[0])
                    obj_idx = int(numbers[1])
                    return NamingConvention.object_s3_key(
                        sanitized_name, frame_idx, obj_idx
                    )

        # Embeddings
        if "embedding" in old_key.lower() or old_key.endswith(".pkl"):
            filename = parts[-1]
            if "frame_embedding" in filename.lower():
                return NamingConvention.frame_embeddings_s3_key()
            elif "frame_path" in filename.lower():
                return NamingConvention.frame_paths_s3_key()
            elif "object_embedding" in filename.lower():
                return NamingConvention.object_embeddings_s3_key()
            elif "object_path" in filename.lower():
                return NamingConvention.object_paths_s3_key()

        logger.warning(f"Could not normalize key: {old_key}")
        return None

    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in a bucket."""
        try:
            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                logger.error(f"Error checking if {key} exists: {e}")
                return False

    def copy_object(
        self,
        source_bucket: str,
        source_key: str,
        target_bucket: str,
        target_key: str,
        dry_run: bool = True,
        skip_existing: bool = True,
    ) -> Tuple[bool, str]:
        """Copy an object from source to target with new key.

        Args:
            source_bucket: Source bucket name
            source_key: Source object key
            target_bucket: Target bucket name
            target_key: Target object key
            dry_run: If True, only simulate the operation
            skip_existing: If True, skip objects that already exist in target

        Returns:
            Tuple of (success: bool, status: str) where status is 'copied', 'skipped', or 'failed'
        """
        try:
            # Check if object already exists in target
            if skip_existing and self.object_exists(target_bucket, target_key):
                logger.info(f"[SKIP] Already exists: {target_bucket}/{target_key}")
                return True, "skipped"

            if dry_run:
                logger.info(
                    f"[DRY RUN] Would copy: {source_bucket}/{source_key} -> {target_bucket}/{target_key}"
                )
                return True, "copied"

            copy_source = {"Bucket": source_bucket, "Key": source_key}
            self.s3_client.copy_object(
                CopySource=copy_source, Bucket=target_bucket, Key=target_key
            )
            logger.info(
                f"Copied: {source_bucket}/{source_key} -> {target_bucket}/{target_key}"
            )
            return True, "copied"

        except ClientError as e:
            logger.error(f"Error copying {source_key}: {e}")
            return False, "failed"

    def migrate_bucket(
        self,
        source_bucket: str,
        target_bucket: str,
        video_name_mapping: Optional[Dict[str, str]] = None,
        dry_run: bool = True,
        skip_existing: bool = True,
    ) -> Dict[str, int]:
        """
        Migrate all objects from source bucket to target bucket with normalized structure.

        Args:
            source_bucket: Source bucket name
            target_bucket: Target bucket name
            video_name_mapping: Optional mapping of old to new video names
            dry_run: If True, only simulate the operation
            skip_existing: If True, skip objects that already exist (enables resume)

        Returns:
            Statistics about the migration
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Migrating from {source_bucket} to {target_bucket}")
        logger.info(f"Dry run: {dry_run}")
        logger.info(f"Resume mode: {skip_existing} (skip existing files)")
        logger.info(f"{'='*80}\n")

        # List all objects
        objects = self.list_all_objects(source_bucket)
        
        # Deduplicate objects (some buckets may have duplicate entries)
        original_count = len(objects)
        objects = list(dict.fromkeys(objects))  # Preserves order, removes duplicates
        if original_count != len(objects):
            logger.warning(f"Found {original_count - len(objects)} duplicate entries in source bucket")

        # Analyze structure
        structure = self.analyze_structure(objects)
        logger.info(f"\nSource bucket structure:")
        for category, items in structure.items():
            logger.info(f"  {category}: {len(items)} items")

        # Statistics
        stats = {
            "total": len(objects),
            "copied": 0,
            "already_exists": 0,
            "failed": 0,
            "cannot_normalize": 0,
            "duplicates_removed": original_count - len(objects),
        }

        # Track processed target keys to avoid processing same target twice
        processed_targets = set()

        # Process each object
        for idx, obj_key in enumerate(objects, 1):
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{len(objects)} objects processed")

            normalized_key = self.normalize_key(obj_key, video_name_mapping)

            if normalized_key is None:
                logger.warning(f"Skipping (cannot normalize): {obj_key}")
                stats["cannot_normalize"] += 1
                continue
            
            # Skip if we've already processed this target key
            if normalized_key in processed_targets:
                logger.debug(f"Already processed target: {normalized_key}")
                stats["already_exists"] += 1
                continue
            
            processed_targets.add(normalized_key)

            if normalized_key == obj_key:
                logger.debug(f"Key already normalized: {obj_key}")

            success, status = self.copy_object(
                source_bucket,
                obj_key,
                target_bucket,
                normalized_key,
                dry_run,
                skip_existing,
            )

            if success:
                if status == "skipped":
                    stats["already_exists"] += 1
                else:
                    stats["copied"] += 1
            else:
                stats["failed"] += 1

        return stats

    def create_bucket_if_not_exists(
        self, bucket_name: str, dry_run: bool = True
    ) -> bool:
        """Create target bucket if it doesn't exist."""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket {bucket_name} already exists")
            return True
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                if dry_run:
                    logger.info(f"[DRY RUN] Would create bucket: {bucket_name}")
                    return True

                self.s3_client.create_bucket(Bucket=bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
                return True
            else:
                logger.error(f"Error checking bucket {bucket_name}: {e}")
                return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate and unify Storj buckets with homogeneous structure"
    )
    parser.add_argument(
        "--source-bucket-1", required=True, help="First source bucket name"
    )
    parser.add_argument(
        "--source-bucket-2",
        required=False,
        default=None,
        help="Second source bucket name (optional)",
    )
    parser.add_argument(
        "--target-bucket", required=True, help="Target unified bucket name"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Perform a dry run without actually copying files (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the migration (overrides --dry-run)",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-copy all files even if they exist in target (default: skip existing)",
    )
    parser.add_argument(
        "--endpoint-url", default=None, help="Storj endpoint URL (defaults to settings)"
    )
    parser.add_argument(
        "--access-key", default=None, help="Access key (defaults to settings)"
    )
    parser.add_argument(
        "--secret-key", default=None, help="Secret key (defaults to settings)"
    )

    args = parser.parse_args()

    # Determine dry_run mode
    dry_run = not args.execute
    skip_existing = not args.no_skip_existing

    # Get credentials from args or config
    endpoint_url = args.endpoint_url or storage_config.storj_endpoint
    access_key = args.access_key or storage_config.access_key
    secret_key = args.secret_key or storage_config.secret_key

    if not all([endpoint_url, access_key, secret_key]):
        logger.error(
            "Missing Storj credentials. Set them in .env or pass as arguments."
        )
        sys.exit(1)

    # Initialize migration
    migration = StorjMigration(endpoint_url, access_key, secret_key)

    # Create target bucket
    migration.create_bucket_if_not_exists(args.target_bucket, dry_run)

    # Migrate first bucket
    logger.info(f"\n\n{'#'*80}")
    logger.info(f"# MIGRATING SOURCE BUCKET: {args.source_bucket_1}")
    logger.info(f"{'#'*80}\n")
    stats1 = migration.migrate_bucket(
        args.source_bucket_1, args.target_bucket, dry_run=dry_run, skip_existing=skip_existing
    )

    # Migrate second bucket (if provided)
    stats2 = {"total": 0, "copied": 0, "already_exists": 0, "failed": 0, "cannot_normalize": 0}
    if args.source_bucket_2:
        logger.info(f"\n\n{'#'*80}")
        logger.info(f"# MIGRATING BUCKET 2: {args.source_bucket_2}")
        logger.info(f"{'#'*80}\n")
        stats2 = migration.migrate_bucket(
            args.source_bucket_2, args.target_bucket, dry_run=dry_run, skip_existing=skip_existing
        )

    # Print summary
    logger.info(f"\n\n{'='*80}")
    logger.info("MIGRATION SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Mode: {'DRY RUN (no changes made)' if dry_run else 'EXECUTED'}")
    logger.info(f"Resume: {'Enabled (skipped existing)' if skip_existing else 'Disabled (re-copy all)'}")
    logger.info(f"\nSource Bucket ({args.source_bucket_1}):")
    logger.info(f"  Total objects: {stats1['total']}")
    logger.info(f"  Copied: {stats1['copied']}")
    logger.info(f"  Already exists (skipped): {stats1['already_exists']}")
    logger.info(f"  Failed: {stats1['failed']}")
    logger.info(f"  Cannot normalize: {stats1['cannot_normalize']}")
    if args.source_bucket_2:
        logger.info(f"\nBucket 2 ({args.source_bucket_2}):")
        logger.info(f"  Total objects: {stats2['total']}")
        logger.info(f"  Copied: {stats2['copied']}")
        logger.info(f"  Already exists (skipped): {stats2['already_exists']}")
        logger.info(f"  Failed: {stats2['failed']}")
        logger.info(f"  Cannot normalize: {stats2['cannot_normalize']}")
    logger.info(f"\nTotal objects processed: {stats1['total'] + stats2['total']}")
    logger.info(f"Total copied: {stats1['copied'] + stats2['copied']}")
    logger.info(f"Total already existed: {stats1['already_exists'] + stats2['already_exists']}")
    logger.info(f"Total failed: {stats1['failed'] + stats2['failed']}")
    logger.info(f"Total cannot normalize: {stats1['cannot_normalize'] + stats2['cannot_normalize']}")

    if dry_run:
        logger.info(f"\n⚠️  This was a DRY RUN. No files were actually copied.")
        logger.info(f"To execute the migration, run with --execute flag")
    else:
        if stats1['failed'] + stats2['failed'] > 0:
            logger.info(f"\n⚠️  Migration completed with {stats1['failed'] + stats2['failed']} errors!")
        else:
            logger.info(f"\n✅ Migration completed successfully!")
    logger.info(f"{'='*80}\n")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    main()
