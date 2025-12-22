#!/usr/bin/env python3
"""
Upload Example Images to S3

This script uploads example images for the image search feature to S3.
These images will be available in the deployed application's example selector.

Directory structure:
- Local: data/example_images/ (add your sample images here)
- S3: example_images/ (where they'll be stored in S3)

Usage:
    python scripts/data_migration/upload_example_images.py
"""

import os
import sys
from pathlib import Path
from typing import List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage import get_storage_manager
from dotenv import load_dotenv

load_dotenv()

# Directories
LOCAL_EXAMPLE_IMAGES_DIR = PROJECT_ROOT / "data" / "example_images"
S3_PREFIX = "example_images"


def get_image_files(directory: Path) -> List[Path]:
    """Get all image files from directory"""
    if not directory.exists():
        return []
    
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
        image_files.extend(directory.glob(ext))
    
    return sorted(image_files)


def upload_example_images():
    """Upload example images to S3"""
    
    # Check if local directory exists
    if not LOCAL_EXAMPLE_IMAGES_DIR.exists():
        print(f"❌ Example images directory not found: {LOCAL_EXAMPLE_IMAGES_DIR}")
        print(f"\nTo add example images:")
        print(f"1. Create directory: mkdir -p {LOCAL_EXAMPLE_IMAGES_DIR}")
        print(f"2. Add your sample images (JPG, JPEG, PNG)")
        print(f"3. Run this script again")
        return False
    
    # Get image files
    image_files = get_image_files(LOCAL_EXAMPLE_IMAGES_DIR)
    
    if not image_files:
        print(f"⚠️  No image files found in {LOCAL_EXAMPLE_IMAGES_DIR}")
        print(f"\nSupported formats: JPG, JPEG, PNG")
        return False
    
    print(f"Found {len(image_files)} example images to upload")
    print("=" * 60)
    
    # Get storage manager
    storage_manager = get_storage_manager()
    storage = storage_manager.get_storage()
    
    # Upload each image
    uploaded_count = 0
    failed_count = 0
    
    for image_file in image_files:
        # Construct S3 path
        s3_path = f"{S3_PREFIX}/{image_file.name}"
        
        print(f"\nUploading: {image_file.name}")
        print(f"  Local:  {image_file}")
        print(f"  S3:     {s3_path}")
        
        try:
            # Check if already exists
            if storage.file_exists(s3_path):
                print(f"  ⚠️  Already exists in S3, skipping...")
                continue
            
            # Upload file
            if storage.upload_file(str(image_file), s3_path):
                print(f"  ✅ Uploaded successfully")
                uploaded_count += 1
            else:
                print(f"  ❌ Upload failed")
                failed_count += 1
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Upload complete!")
    print(f"  ✅ Uploaded: {uploaded_count}")
    print(f"  ⏭️  Skipped:  {len(image_files) - uploaded_count - failed_count}")
    print(f"  ❌ Failed:   {failed_count}")
    
    return failed_count == 0


def list_example_images_in_s3():
    """List example images currently in S3"""
    
    storage_manager = get_storage_manager()
    storage = storage_manager.get_storage()
    
    print("\nExample images in S3:")
    print("=" * 60)
    
    # This is a simplified version - you may need to implement list_files in storage
    # For now, just check if the directory exists
    print(f"Path: {S3_PREFIX}/")
    print("Note: Use AWS CLI or console to list all files:")
    print(f"  aws s3 ls s3://YOUR_BUCKET/{S3_PREFIX}/")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload example images to S3")
    parser.add_argument(
        "--list", 
        action="store_true", 
        help="List example images in S3"
    )
    
    args = parser.parse_args()
    
    print("Example Images Upload Script")
    print("=" * 60)
    
    if args.list:
        list_example_images_in_s3()
    else:
        success = upload_example_images()
        sys.exit(0 if success else 1)
