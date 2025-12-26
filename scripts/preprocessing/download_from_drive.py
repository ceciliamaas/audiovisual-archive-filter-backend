#!/usr/bin/env python3
"""
Download video from Google Drive

Usage:
    python download_from_drive.py <drive_url> [--output-name video_name]
"""

import argparse
import sys
from pathlib import Path
import subprocess


# Get project root and data directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"


def extract_file_id(drive_url: str) -> str:
    """Extract file ID from Google Drive URL"""
    # Handle different Google Drive URL formats
    if "drive.google.com" in drive_url:
        if "/file/d/" in drive_url:
            # Format: https://drive.google.com/file/d/FILE_ID/view
            file_id = drive_url.split("/file/d/")[1].split("/")[0]
        elif "id=" in drive_url:
            # Format: https://drive.google.com/open?id=FILE_ID
            file_id = drive_url.split("id=")[1].split("&")[0]
        else:
            raise ValueError(f"Could not parse Google Drive URL: {drive_url}")
        return file_id
    else:
        raise ValueError("URL does not appear to be a Google Drive link")


def download_from_gdrive(file_id: str, output_path: Path):
    """Download file from Google Drive using gdown"""
    try:
        import gdown
    except ImportError:
        print("❌ gdown is not installed. Installing now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
        import gdown
    
    print(f"📥 Downloading file from Google Drive...")
    print(f"File ID: {file_id}")
    print(f"Output: {output_path}")
    
    url = f"https://drive.google.com/uc?id={file_id}"
    
    try:
        gdown.download(url, str(output_path), quiet=False)
        print(f"✅ Download completed: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        print("\n💡 If you're getting permission errors:")
        print("   1. Make sure the Google Drive link is set to 'Anyone with the link can view'")
        print("   2. Try downloading manually and placing the file in data/videos/")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Download video from Google Drive")
    parser.add_argument("drive_url", help="Google Drive URL of the video")
    parser.add_argument(
        "--output-name", 
        "-o", 
        help="Output filename (default: video.mp4)"
    )
    
    args = parser.parse_args()
    
    # Create videos directory
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Extract file ID from URL
    try:
        file_id = extract_file_id(args.drive_url)
    except ValueError as e:
        print(f"❌ {e}")
        return False
    
    # Determine output path
    if args.output_name:
        output_name = args.output_name
        if not output_name.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            output_name += '.mp4'
    else:
        output_name = "video.mp4"
    
    output_path = VIDEOS_DIR / output_name
    
    # Download the file
    success = download_from_gdrive(file_id, output_path)
    
    if success:
        print("\n🎉 Video downloaded successfully!")
        print(f"📁 Location: {output_path}")
        print("\n📋 Next steps:")
        print("   1. Extract frames: python extract_frames.py")
        print("   2. Or run full workflow: python process_workflow.py --skip-download")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
