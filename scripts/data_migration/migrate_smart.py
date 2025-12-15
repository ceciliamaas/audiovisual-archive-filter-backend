"""
Simplified migration script with progress tracking and better error handling
Only uploads essential files (skips .DS_Store, __pycache__, etc.)
"""

import sys
from pathlib import Path
import time

# Add parent directory to path for S3 imports
sys.path.append(str(Path(__file__).parent))
from s3_storage import get_s3_client


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped during upload"""
    skip_patterns = {
        ".DS_Store",
        "__pycache__",
        ".pyc",
        ".git",
        "Thumbs.db",
        ".gitignore",
    }

    # Skip files matching patterns
    if file_path.name in skip_patterns:
        return True

    # Skip files with certain extensions
    skip_extensions = {".pyc", ".pyo", ".pyd", ".tmp"}
    if file_path.suffix in skip_extensions:
        return True

    return False


def upload_directory_smart(local_dir: Path, s3_prefix: str, s3_client) -> tuple:
    """Upload directory with progress tracking and smart filtering"""

    if not local_dir.exists():
        print(f"Directory not found: {local_dir}")
        return 0, 0

    # Get all files to upload (excluding skipped files)
    all_files = [
        f for f in local_dir.rglob("*") if f.is_file() and not should_skip_file(f)
    ]

    if not all_files:
        print(f"No files to upload in {local_dir}")
        return 0, 0

    total_files = len(all_files)
    success_count = 0

    print(f"Found {total_files} files to upload...")

    for i, file_path in enumerate(all_files, 1):
        # Create relative path for S3 key
        relative_path = file_path.relative_to(local_dir)
        s3_key = f"{s3_prefix}/{relative_path}".replace("\\", "/").strip("/")

        # Show progress
        if i % 10 == 0 or i == total_files:
            progress = (i / total_files) * 100
            print(f"Progress: {i}/{total_files} ({progress:.1f}%)")

        # Upload file
        if s3_client.upload_file(file_path, s3_key):
            success_count += 1
        else:
            print(f"Failed to upload: {file_path.name}")

        # Small delay to avoid overwhelming the API
        time.sleep(0.1)

    return success_count, total_files


def migrate_essential_data():
    """Upload only essential data - prioritize embeddings and small datasets first"""

    try:
        s3_client = get_s3_client()
        print("✅ S3 connection successful!")
    except Exception as e:
        print(f"❌ S3 connection failed: {e}")
        return False

    # Prioritize embeddings first (smallest, most important)
    priority_migrations = [
        {
            "local_dir": Path(__file__).parent / "app/embeddings",
            "s3_prefix": "embeddings",
            "description": "Embeddings (PRIORITY)",
        }
    ]

    # Then do the larger datasets
    other_migrations = [
        {
            "local_dir": Path(__file__).parent / "app/input_videos",
            "s3_prefix": "input_videos",
            "description": "Input videos",
        },
        {
            "local_dir": Path(__file__).parent / "app/output_frames",
            "s3_prefix": "output_frames",
            "description": "Output frames",
        },
        {
            "local_dir": Path(__file__).parent / "app/cropped_objects",
            "s3_prefix": "cropped_objects",
            "description": "Cropped objects",
        },
    ]

    all_migrations = priority_migrations + other_migrations

    print(f"\n{'='*50}")
    print("SMART S3 MIGRATION")
    print(f"{'='*50}")

    total_success = 0
    total_files = 0

    for migration in all_migrations:
        local_dir = migration["local_dir"]
        s3_prefix = migration["s3_prefix"]
        description = migration["description"]

        print(f"\n📁 Migrating {description}...")
        print(f"   Local:  {local_dir}")
        print(f"   S3:     s3://bucket/{s3_prefix}/")

        try:
            success, files = upload_directory_smart(local_dir, s3_prefix, s3_client)
            total_success += success
            total_files += files

            if files > 0:
                success_rate = (success / files) * 100
                print(f"   ✅ Uploaded {success}/{files} files ({success_rate:.1f}%)")
            else:
                print(f"   ⏭️  No files to upload")

        except KeyboardInterrupt:
            print(f"\n⚠️  Migration interrupted by user")
            break
        except Exception as e:
            print(f"   ❌ Migration error: {e}")

    print(f"\n{'='*50}")
    print("MIGRATION SUMMARY")
    print(f"{'='*50}")
    print(f"Total uploaded: {total_success}/{total_files} files")

    if total_files > 0:
        overall_success_rate = (total_success / total_files) * 100
        print(f"Success rate: {overall_success_rate:.1f}%")

    return total_success > 0


if __name__ == "__main__":
    print("Smart Storj S3 Migration Script")
    print("===============================")
    print("This script uploads essential data first, skips unnecessary files.")
    print()

    response = input("Do you want to proceed with smart migration? (y/N): ")
    if response.lower() != "y":
        print("Migration cancelled.")
        exit(0)

    success = migrate_essential_data()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test the app to ensure S3 integration works")
        print("2. Update .gitignore to exclude data directories")
        print("3. Commit the S3 integration code")
    else:
        print("\n❌ Migration completed with issues.")
        print("Some files may not have uploaded. Check the logs above.")
