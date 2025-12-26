#!/usr/bin/env python3
"""Check what's in S3 storage"""

import sys, os
sys.path.insert(0, '.')

# Load .env
from dotenv import load_dotenv
load_dotenv('.env')

print("Environment variables:")
print(f"  STORAGE_MODE: {os.getenv('STORAGE_MODE')}")
print(f"  STORJ_ACCESS_KEY: {'SET' if os.getenv('STORJ_ACCESS_KEY') else 'NOT SET'}")
print(f"  STORJ_SECRET_KEY: {'SET' if os.getenv('STORJ_SECRET_KEY') else 'NOT SET'}")
print(f"  STORJ_BUCKET_NAME: {os.getenv('STORJ_BUCKET_NAME')}")
print()

from src.storage import get_storage_manager

storage_mgr = get_storage_manager()
storage = storage_mgr.get_storage()

print(f"Storage type: {type(storage).__name__}")

if type(storage).__name__ == 'S3Storage':
    print("\n✓ Using S3 Storage")
    print(f"  Bucket: {storage.bucket_name}")
    print(f"  Endpoint: {storage.endpoint_url}")
    
    # Check what embeddings exist
    print("\nChecking embeddings in S3...")
    frame_paths = storage.download_pickle('embeddings/frame_paths.pkl')
    
    if frame_paths:
        print(f"  Frame paths: {len(frame_paths)}")
        
        # Get unique videos
        videos = {}
        for p in frame_paths:
            parts = p.split('/')
            if len(parts) >= 2:
                video = parts[1]
                videos[video] = videos.get(video, 0) + 1
        
        print("\n  Videos in S3:")
        for v, count in sorted(videos.items()):
            print(f"    - {v}: {count} frames")
        
        jonathan_count = sum(1 for p in frame_paths if 'jonathan' in p.lower())
        print(f"\n  Jonathan frames in S3: {jonathan_count}")
else:
    print(f"\n✗ Not using S3 storage (using {type(storage).__name__})")
