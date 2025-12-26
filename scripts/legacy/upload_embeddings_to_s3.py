#!/usr/bin/env python3
"""
Quick script to upload embeddings to S3/Storj
"""

import os
import boto3
from botocore.config import Config
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# S3 Configuration
STORJ_ENDPOINT_URL = os.getenv("STORJ_ENDPOINT_URL")
STORJ_ACCESS_KEY = os.getenv("STORJ_ACCESS_KEY")
STORJ_SECRET_KEY = os.getenv("STORJ_SECRET_KEY")
STORJ_BUCKET_NAME = os.getenv("STORJ_BUCKET_NAME")

# Initialize S3 client with custom config for Storj
config = Config(
    signature_version='s3v4',
    s3={'addressing_style': 'path'}
)

s3_client = boto3.client(
    "s3",
    endpoint_url=STORJ_ENDPOINT_URL,
    aws_access_key_id=STORJ_ACCESS_KEY,
    aws_secret_access_key=STORJ_SECRET_KEY,
    region_name="us-east-1",
    config=config
)

print(f"📦 Uploading embeddings to S3 bucket: {STORJ_BUCKET_NAME}")

# Files to upload
embeddings_dir = Path("data/embeddings")
files_to_upload = [
    "frame_embeddings.pkl",
    "frame_paths.pkl",
    "object_embeddings.pkl",
    "object_paths.pkl",
]

uploaded = 0
failed = 0

for filename in files_to_upload:
    local_path = embeddings_dir / filename
    s3_key = f"embeddings/{filename}"
    
    if local_path.exists():
        try:
            file_size_bytes = local_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)  # MB
            print(f"📤 Uploading {filename} ({file_size_mb:.2f} MB)...")
            
            # Use upload_fileobj
            with open(local_path, 'rb') as f:
                s3_client.upload_fileobj(f, STORJ_BUCKET_NAME, s3_key)
            
            print(f"   ✅ Uploaded {s3_key}")
            uploaded += 1
            
        except Exception as e:
            print(f"   ❌ Failed to upload {filename}: {e}")
            failed += 1
    else:
        print(f"   ⚠️  {filename} not found locally")
        failed += 1

print(f"\n📊 Summary:")
print(f"   ✅ Uploaded: {uploaded}")
print(f"   ❌ Failed: {failed}")

if uploaded > 0:
    print(f"\n🎉 Embeddings successfully uploaded to S3!")
