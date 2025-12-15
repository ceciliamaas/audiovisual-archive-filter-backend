"""
Migration script to upload existing local data to Storj S3
This script will upload:
- Input videos
- Output frames
- Cropped objects
- Embeddings

Run this once to migrate from local storage to S3
"""

import sys
from pathlib import Path

# Add parent directory to path for S3 imports
sys.path.append(str(Path(__file__).parent.parent))
from s3_storage import get_s3_client, upload_directory_to_s3


def migrate_to_s3():
    """Upload all existing data directories to S3"""

    try:
        s3_client = get_s3_client()
        print("✅ S3 connection successful!")
    except Exception as e:
        print(f"❌ S3 connection failed: {e}")
        return False

    # Define local directories and their S3 prefixes
    migrations = [
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
        {
            "local_dir": Path(__file__).parent / "app/embeddings",
            "s3_prefix": "embeddings",
            "description": "Embeddings",
        },
    ]

    print(f"\n{'='*50}")
    print("STARTING DATA MIGRATION TO S3")
    print(f"{'='*50}")

    total_success = 0
    total_attempted = 0

    for migration in migrations:
        local_dir = migration["local_dir"]
        s3_prefix = migration["s3_prefix"]
        description = migration["description"]

        print(f"\n📁 Migrating {description}...")
        print(f"   Local:  {local_dir}")
        print(f"   S3:     s3://bucket/{s3_prefix}/")

        if not local_dir.exists():
            print(f"   ⏭️  Directory not found, skipping")
            continue

        total_attempted += 1

        try:
            success = upload_directory_to_s3(local_dir, s3_prefix)
            if success:
                total_success += 1
                print(f"   ✅ Migration successful")
            else:
                print(f"   ❌ Migration failed")

        except Exception as e:
            print(f"   ❌ Migration error: {e}")

    print(f"\n{'='*50}")
    print("MIGRATION COMPLETE")
    print(f"{'='*50}")
    print(f"Successful: {total_success}/{total_attempted} directories")

    if total_success == total_attempted and total_attempted > 0:
        print("\n🎉 All data successfully migrated to S3!")
        print("\nYou can now:")
        print("1. Add data directories to .gitignore")
        print("2. Remove local data directories to save space")
        print("3. Use the S3-enabled compute_embeddings_s3.py script")
        return True
    else:
        print("\n⚠️  Some migrations failed. Check the errors above.")
        return False


def verify_migration():
    """Verify that data was uploaded correctly"""
    try:
        s3_client = get_s3_client()

        print(f"\n{'='*50}")
        print("VERIFYING MIGRATION")
        print(f"{'='*50}")

        prefixes = ["input_videos", "output_frames", "cropped_objects", "embeddings"]

        for prefix in prefixes:
            files = s3_client.list_files(prefix + "/")
            print(f"{prefix:20}: {len(files):4d} files")

            # Show first few files as examples
            if files:
                print(f"                     Examples:")
                for file in files[:3]:
                    print(f"                       - {file}")
                if len(files) > 3:
                    print(f"                       ... and {len(files)-3} more")
            print()

    except Exception as e:
        print(f"❌ Verification failed: {e}")


if __name__ == "__main__":
    print("Storj S3 Migration Script")
    print("=========================")
    print("This script will upload your local data to Storj S3 storage.")
    print()

    # Check for required environment variables
    import os

    required_vars = [
        "STORJ_ENDPOINT_URL",
        "STORJ_ACCESS_KEY",
        "STORJ_SECRET_KEY",
        "STORJ_BUCKET_NAME",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease add these to your .env file or environment.")
        exit(1)

    response = input("Do you want to proceed with the migration? (y/N): ")
    if response.lower() != "y":
        print("Migration cancelled.")
        exit(0)

    # Perform migration
    success = migrate_to_s3()

    if success:
        # Verify migration
        verify_migration()

        print("\n" + "=" * 50)
        print("NEXT STEPS")
        print("=" * 50)
        print("1. The data has been uploaded to S3")
        print("2. Update your .gitignore to exclude data directories")
        print("3. You can now safely delete local data directories")
        print("4. Use compute_embeddings_s3.py for future processing")
        print("5. The Streamlit app will now load data from S3")
    else:
        print("\n❌ Migration failed. Please check the errors and try again.")
