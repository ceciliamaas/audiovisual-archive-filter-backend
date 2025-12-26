#!/usr/bin/env python3
"""
Upload cropped objects to S3
"""

import os
from s3_storage import StorjS3Client
from tqdm import tqdm
import time


def upload_objects_to_s3():
    # Initialize S3 client
    s3_client = StorjS3Client()

    # Get all cropped object files
    cropped_dir = "app/cropped_objects"

    if not os.path.exists(cropped_dir):
        print(f"❌ Directory {cropped_dir} does not exist")
        return

    # Get all .jpg files
    jpg_files = []
    for file in os.listdir(cropped_dir):
        if file.endswith(".jpg"):
            jpg_files.append(file)

    jpg_files.sort()  # Sort for consistent processing
    print(f"📁 Found {len(jpg_files)} cropped object images to upload")

    if len(jpg_files) == 0:
        print("❌ No .jpg files found in cropped_objects directory")
        return

    # Show first few files as example
    print("\n📋 Examples of files to upload:")
    for i, file in enumerate(jpg_files[:5]):
        print(f"  {i+1}. {file}")
    if len(jpg_files) > 5:
        print(f"  ... and {len(jpg_files) - 5} more files")

    # Ask for confirmation
    response = input(f"\n❓ Upload {len(jpg_files)} files to S3? (y/N): ")
    if response.lower() != "y":
        print("❌ Upload cancelled by user")
        return

    # Upload files with progress tracking
    uploaded = 0
    failed = 0

    print(f"\n🚀 Starting upload of {len(jpg_files)} files...")

    with tqdm(total=len(jpg_files), desc="Uploading") as pbar:
        for file in jpg_files:
            local_path = os.path.join(cropped_dir, file)
            s3_key = f"cropped_objects/{file}"

            try:
                success = s3_client.upload_file(local_path, s3_key)
                if success:
                    uploaded += 1
                    pbar.set_description(f"✅ {file}")
                else:
                    failed += 1
                    pbar.set_description(f"❌ {file}")
                    print(f"\n❌ Failed to upload: {file}")
            except Exception as e:
                failed += 1
                pbar.set_description(f"❌ {file}")
                print(f"\n❌ Error uploading {file}: {str(e)}")

            pbar.update(1)

            # Small delay to avoid overwhelming S3
            time.sleep(0.1)

    print(f"\n📊 Upload Summary:")
    print(f"  ✅ Successfully uploaded: {uploaded} files")
    print(f"  ❌ Failed uploads: {failed} files")
    print(f"  📈 Success rate: {uploaded/(uploaded+failed)*100:.1f}%")

    if uploaded > 0:
        print(
            f"\n🎉 Upload completed! {uploaded} cropped object images are now available in S3."
        )
        print("🔄 The Streamlit app should now be able to display object images.")
    else:
        print(f"\n💥 No files were uploaded successfully.")


if __name__ == "__main__":
    upload_objects_to_s3()
