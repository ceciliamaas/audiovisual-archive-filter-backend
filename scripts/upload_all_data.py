#!/usr/bin/env python3
"""
Upload all available data (frames, objects, and embeddings) to S3

This script uploads:
- Video frames from data/frames/
- Cropped objects from data/objects/
- Embedding files from data/embeddings/
"""

import os
import sys
from pathlib import Path
from tqdm import tqdm
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for storage imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage import get_storage_manager


def upload_directory_to_s3(
    local_dir: Path, s3_prefix: str, storage_manager, file_extensions=None
):
    """
    Upload a directory to S3 with progress tracking

    Args:
        local_dir: Local directory to upload
        s3_prefix: S3 prefix for uploaded files
        storage_manager: Storage manager instance
        file_extensions: List of file extensions to upload (default: all files)
    """
    if not local_dir.exists():
        print(f"❌ Directory {local_dir} does not exist")
        return 0

    # Find all files to upload
    files_to_upload = []
    for file_path in local_dir.rglob("*"):
        if file_path.is_file():
            if file_extensions is None or any(
                str(file_path).endswith(ext) for ext in file_extensions
            ):
                relative_path = file_path.relative_to(local_dir)
                s3_key = f"{s3_prefix}/{relative_path}"
                files_to_upload.append((file_path, s3_key))

    if not files_to_upload:
        print(f"❌ No files found in {local_dir}")
        return 0

    print(f"📁 Found {len(files_to_upload)} files to upload from {local_dir}")

    # Check which files already exist (for resume functionality)
    files_to_skip = []
    files_needing_upload = []

    print(f"🔍 Checking for existing files to enable resume functionality...")

    # Get all existing files with the prefix in batch (much faster)
    try:
        print(f"📋 Fetching list of existing files with prefix '{s3_prefix}'...")
        existing_files = set(storage_manager.list_files(s3_prefix))
        print(
            f"📊 Found {len(existing_files)} existing files with prefix '{s3_prefix}'"
        )
        print(f"🔍 Comparing with {len(files_to_upload)} local files...")

        for file_path, s3_key in files_to_upload:
            if s3_key in existing_files:
                files_to_skip.append((file_path, s3_key))
            else:
                files_needing_upload.append((file_path, s3_key))

    except Exception as e:
        print(f"⚠️  Could not check existing files: {e}")
        print(f"🔄 Will upload all files (no resume functionality)")
        # If we can't check, upload all files
        files_needing_upload = files_to_upload

    if files_to_skip:
        print(f"⏩ Skipping {len(files_to_skip)} files that already exist")

    if not files_needing_upload:
        print(f"✅ All files already uploaded from {local_dir}")
        return len(files_to_upload)

    print(f"📤 Need to upload {len(files_needing_upload)} files")

    # Upload files with progress bar
    uploaded = 0
    failed = 0

    for file_path, s3_key in tqdm(files_needing_upload, desc=f"Uploading {s3_prefix}"):
        try:
            success = storage_manager.upload_file(file_path, s3_key)
            if success:
                uploaded += 1
            else:
                failed += 1
                print(f"❌ Failed to upload {file_path}")
        except Exception as e:
            failed += 1
            print(f"❌ Error uploading {file_path}: {e}")

    total_successful = uploaded + len(files_to_skip)
    print(
        f"✅ Total: {total_successful} successful ({len(files_to_skip)} already existed, {uploaded} newly uploaded), {failed} failed from {local_dir}"
    )
    return total_successful


def main():
    """Main upload function"""
    print("🚀 Starting data upload to S3...")

    # Use the proper storage configuration
    from src.storage.s3 import S3Storage
    from src.config.settings import storage_config

    # Validate that S3 credentials are available
    if not storage_config.validate():
        print("❌ S3 credentials not found in environment variables!")
        print("Please ensure the following are set in your .env file:")
        print("- STORJ_ACCESS_KEY")
        print("- STORJ_SECRET_KEY")
        print("- STORJ_BUCKET_NAME")
        return

    storage_backend = S3Storage()
    print(f"📦 Using S3 storage: {storage_backend.get_info()['backend_type']}")

    data_dir = PROJECT_ROOT / "data"
    total_uploaded = 0

    # Upload video frames
    frames_dir = data_dir / "frames"
    if frames_dir.exists():
        print(f"\n📸 Uploading frames...")
        uploaded = upload_directory_to_s3(
            frames_dir, "frames", storage_backend, [".jpg", ".png"]
        )
        total_uploaded += uploaded
    else:
        print(f"⚠️  Frames directory not found: {frames_dir}")

    # Upload cropped objects
    objects_dir = data_dir / "objects"
    if objects_dir.exists():
        print(f"\n🎯 Uploading objects...")
        uploaded = upload_directory_to_s3(
            objects_dir, "objects", storage_backend, [".jpg", ".png"]
        )
        total_uploaded += uploaded
    else:
        print(f"⚠️  Objects directory not found: {objects_dir}")

    # Upload embeddings
    embeddings_dir = data_dir / "embeddings"
    if embeddings_dir.exists():
        print(f"\n🧠 Uploading embeddings...")
        uploaded = upload_directory_to_s3(
            embeddings_dir, "embeddings", storage_backend, [".pkl", ".json", ".npy"]
        )
        total_uploaded += uploaded
    else:
        print(f"⚠️  Embeddings directory not found: {embeddings_dir}")

    # Upload videos if they exist
    videos_dir = data_dir / "videos"
    if videos_dir.exists():
        print(f"\n🎬 Uploading videos...")
        uploaded = upload_directory_to_s3(
            videos_dir, "videos", storage_backend, [".mp4", ".avi", ".mov", ".mkv"]
        )
        total_uploaded += uploaded
    else:
        print(f"⚠️  Videos directory not found: {videos_dir}")

    print(f"\n🎉 Upload complete!")
    print(f"📊 Total files uploaded: {total_uploaded}")


if __name__ == "__main__":
    main()
