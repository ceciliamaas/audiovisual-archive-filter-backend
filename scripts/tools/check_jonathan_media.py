#!/usr/bin/env python3
"""
Check if frames and objects for video_reconstrucción_jonathan exist in S3
"""

import sys
import os
from pathlib import Path

# Change to script's parent directory
script_dir = Path(__file__).parent
os.chdir(script_dir.parent)

sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('.env')

from src.storage import get_storage_manager

def main():
    print("="*70)
    print("Check if video_reconstrucción_jonathan media files are in S3")
    print("="*70)
    
    storage_mgr = get_storage_manager()
    storage = storage_mgr.get_storage()
    
    print(f"\nStorage type: {type(storage).__name__}")
    if type(storage).__name__ != 'S3Storage':
        print("ERROR: Not using S3 storage.")
        return
    
    # Check for some sample frames and objects
    test_paths = [
        'frames/video_reconstrucción_jonathan/frame_00000.jpg',
        'frames/video_reconstrucción_jonathan/frame_00001.jpg',
        'frames/video_reconstrucción_jonathan/frame_00100.jpg',
        'objects/video_reconstrucción_jonathan/frame_00000_obj_0.jpg',
        'objects/video_reconstrucción_jonathan/frame_00044_obj_10.jpg',
    ]
    
    print("\nChecking sample files in S3:")
    found = 0
    not_found = 0
    
    for path in test_paths:
        exists = storage.file_exists(path)
        status = "✓" if exists else "✗"
        print(f"  {status} {path}")
        if exists:
            found += 1
        else:
            not_found += 1
    
    print(f"\nSummary:")
    print(f"  Found: {found}")
    print(f"  Not found: {not_found}")
    
    if not_found > 0:
        print("\n⚠ WARNING: Some media files are missing from S3!")
        print("  You need to upload the frames and objects to S3.")
        print("  Run: python scripts/data_migration/upload_frames_to_s3.py")
        print("  And: python scripts/data_migration/upload_objects_to_s3.py")
    else:
        print("\n✓ All sample media files found in S3!")
        print("  Your video should now be fully searchable.")

if __name__ == '__main__':
    main()
