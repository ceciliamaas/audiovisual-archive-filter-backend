#!/usr/bin/env python3
"""
Upload video frames to S3
"""

import os
from s3_storage import StorjS3Client
from tqdm import tqdm
import time

def upload_frames_to_s3():
    # Initialize S3 client
    s3_client = StorjS3Client()
    
    # Get all frame files
    frames_dir = "app/output_frames"
    
    if not os.path.exists(frames_dir):
        print(f"❌ Directory {frames_dir} does not exist")
        return
    
    # Find all .jpg files recursively
    jpg_files = []
    for root, dirs, files in os.walk(frames_dir):
        for file in files:
            if file.endswith('.jpg'):
                local_path = os.path.join(root, file)
                # Create S3 key maintaining directory structure
                relative_path = os.path.relpath(local_path, "app")
                jpg_files.append((local_path, relative_path))
    
    jpg_files.sort()  # Sort for consistent processing
    print(f"📁 Found {len(jpg_files)} frame images to upload")
    
    if len(jpg_files) == 0:
        print("❌ No .jpg files found in frames directory")
        return
    
    # Calculate total size
    total_size = sum(os.path.getsize(local_path) for local_path, _ in jpg_files)
    print(f"📊 Total size: {total_size / (1024**3):.2f} GB")
    
    # Show first few files as example
    print("\n📋 Examples of files to upload:")
    for i, (local_path, s3_key) in enumerate(jpg_files[:5]):
        size_mb = os.path.getsize(local_path) / (1024**2)
        print(f"  {i+1}. {s3_key} ({size_mb:.1f} MB)")
    if len(jpg_files) > 5:
        print(f"  ... and {len(jpg_files) - 5} more files")
    
    # Ask for confirmation
    response = input(f"\n❓ Upload {len(jpg_files)} frame files ({total_size / (1024**3):.2f} GB) to S3? (y/N): ")
    if response.lower() != 'y':
        print("❌ Upload cancelled by user")
        return
    
    # Upload files with progress tracking
    uploaded = 0
    failed = 0
    uploaded_size = 0
    
    print(f"\n🚀 Starting upload of {len(jpg_files)} files...")
    
    with tqdm(total=len(jpg_files), desc="Uploading frames", unit="file") as pbar:
        for local_path, s3_key in jpg_files:
            try:
                file_size = os.path.getsize(local_path)
                success = s3_client.upload_file(local_path, s3_key)
                
                if success:
                    uploaded += 1
                    uploaded_size += file_size
                    pbar.set_description(f"✅ {os.path.basename(s3_key)}")
                else:
                    failed += 1
                    pbar.set_description(f"❌ {os.path.basename(s3_key)}")
                    print(f"\n❌ Failed to upload: {s3_key}")
            except Exception as e:
                failed += 1
                pbar.set_description(f"❌ {os.path.basename(s3_key)}")
                print(f"\n❌ Error uploading {s3_key}: {str(e)}")
            
            pbar.update(1)
            
            # Small delay to avoid overwhelming S3
            time.sleep(0.1)
    
    print(f"\n📊 Upload Summary:")
    print(f"  ✅ Successfully uploaded: {uploaded:,} files ({uploaded_size / (1024**3):.2f} GB)")
    print(f"  ❌ Failed uploads: {failed:,} files")
    print(f"  📈 Success rate: {uploaded/(uploaded+failed)*100:.1f}%")
    
    if uploaded > 0:
        print(f"\n🎉 Upload completed! {uploaded:,} frame images are now available in S3.")
        print("🔄 The Streamlit app should now be able to display frame images from S3.")
    else:
        print(f"\n💥 No files were uploaded successfully.")

if __name__ == "__main__":
    upload_frames_to_s3()