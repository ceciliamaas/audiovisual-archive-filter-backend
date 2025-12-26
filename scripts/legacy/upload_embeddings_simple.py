#!/usr/bin/env python3
"""
Upload embeddings to S3 using the simple S3 client that works with Storj
"""

import sys
from pathlib import Path

# Add scripts/utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from test_simple_s3 import create_simple_s3_client

# Files to upload
embeddings_dir = Path("data/embeddings")
files_to_upload = [
    "frame_embeddings.pkl",
    "frame_paths.pkl",
    "object_embeddings.pkl",
    "object_paths.pkl",
]

print("🚀 Uploading embeddings to S3 using SimpleS3Client...")
print(f"📦 Source: {embeddings_dir}\n")

# Create S3 client
s3_client = create_simple_s3_client()

uploaded = 0
failed = 0

for filename in files_to_upload:
    local_path = embeddings_dir / filename
    s3_key = f"embeddings/{filename}"
    
    if local_path.exists():
        file_size_mb = local_path.stat().st_size / (1024 * 1024)
        print(f"📤 Uploading {filename} ({file_size_mb:.2f} MB)...")
        
        if s3_client.upload_file_simple(str(local_path), s3_key):
            uploaded += 1
            print(f"   ✅ Successfully uploaded {filename}\n")
        else:
            failed += 1
            print(f"   ❌ Failed to upload {filename}\n")
    else:
        print(f"⚠️  {filename} not found\n")
        failed += 1

print(f"\n📊 Summary:")
print(f"   ✅ Uploaded: {uploaded}")
print(f"   ❌ Failed: {failed}")

if uploaded == len(files_to_upload):
    print(f"\n🎉 All embeddings successfully uploaded to S3!")
elif uploaded > 0:
    print(f"\n⚠️  Some embeddings uploaded, but {failed} failed")
else:
    print(f"\n❌ No embeddings were uploaded")
