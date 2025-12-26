"""
Simple script to upload videos to Storj S3
Use this to add new videos to your archive
"""

import sys
from pathlib import Path
import argparse

# Add parent directory to path for S3 imports
sys.path.append(str(Path(__file__).parent.parent))
from s3_storage import get_s3_client


def upload_video(video_path: str):
    """Upload a single video to S3"""
    video_path = Path(video_path)

    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return False

    try:
        s3_client = get_s3_client()
        s3_key = f"input_videos/{video_path.name}"

        print(f"Uploading {video_path.name} to S3...")
        success = s3_client.upload_file(video_path, s3_key)

        if success:
            print(f"✅ Upload successful: s3://bucket/{s3_key}")
            return True
        else:
            print(f"❌ Upload failed")
            return False

    except Exception as e:
        print(f"❌ Error uploading video: {e}")
        return False


def list_videos():
    """List all videos currently in S3"""
    try:
        s3_client = get_s3_client()
        video_files = s3_client.list_files("input_videos/")

        if video_files:
            print("Videos in S3:")
            for i, video_file in enumerate(video_files, 1):
                video_name = Path(video_file).name
                print(f"  {i}. {video_name}")
        else:
            print("No videos found in S3")

    except Exception as e:
        print(f"❌ Error listing videos: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload videos to Storj S3")
    parser.add_argument("--upload", type=str, help="Path to video file to upload")
    parser.add_argument("--list", action="store_true", help="List videos in S3")

    args = parser.parse_args()

    if args.list:
        list_videos()
    elif args.upload:
        upload_video(args.upload)
    else:
        print("Usage:")
        print("  python upload_video.py --upload /path/to/video.mp4")
        print("  python upload_video.py --list")
