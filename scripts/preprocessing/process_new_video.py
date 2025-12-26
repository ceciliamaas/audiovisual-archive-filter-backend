#!/usr/bin/env python3
"""
Process a New Video - Complete Pipeline

Downloads a video (from Drive or other source), processes it through
the complete pipeline, and uploads everything to S3.

Usage:
    # From Google Drive:
    python process_new_video.py --drive-url "<google_drive_link>" --video-name "video_5"
    
    # From local file:
    python process_new_video.py --local-file "/path/to/video.mp4" --video-name "video_5"
    
    # From YouTube:
    python process_new_video.py --youtube-url "<youtube_link>" --video-name "video_5"
"""

import argparse
import sys
import subprocess
from pathlib import Path
import shutil


# Get project root and data directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"
FRAMES_DIR = DATA_DIR / "frames"
OBJECTS_DIR = DATA_DIR / "objects"


def print_step(step_num: int, title: str):
    """Print a formatted step header"""
    print(f"\n{'='*70}")
    print(f"  STEP {step_num}: {title}")
    print(f"{'='*70}")


def run_command(description: str, command: list, cwd=None) -> bool:
    """Run a command with error handling"""
    print(f"\n🚀 {description}")
    print(f"   Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd or PROJECT_ROOT,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"   Error: {e}")
        return False


def download_from_drive(drive_url: str, video_name: str) -> Path:
    """Download video from Google Drive"""
    print_step(1, "Download Video from Google Drive")
    
    output_path = VIDEOS_DIR / f"{video_name}.mp4"
    
    script_path = Path(__file__).parent / "download_from_drive.py"
    command = [
        sys.executable,
        str(script_path),
        drive_url,
        "--output-name", f"{video_name}.mp4"
    ]
    
    if run_command("Downloading from Google Drive", command):
        return output_path
    return None


def download_from_youtube(youtube_url: str, video_name: str) -> Path:
    """Download video from YouTube"""
    print_step(1, "Download Video from YouTube")
    
    output_path = VIDEOS_DIR / f"{video_name}.mp4"
    
    script_path = Path(__file__).parent / "download_videos.py"
    command = [
        sys.executable,
        str(script_path),
        youtube_url,
        "--output", str(VIDEOS_DIR)
    ]
    
    if run_command("Downloading from YouTube", command):
        # Rename downloaded file to match video_name
        # yt-dlp uses video title, so we need to find and rename it
        downloaded_files = list(VIDEOS_DIR.glob("*.mp4"))
        if downloaded_files:
            latest_file = max(downloaded_files, key=lambda p: p.stat().st_mtime)
            if latest_file != output_path:
                latest_file.rename(output_path)
        return output_path
    return None


def copy_local_file(local_path: str, video_name: str) -> Path:
    """Copy local video file to videos directory"""
    print_step(1, "Copy Local Video File")
    
    source = Path(local_path)
    if not source.exists():
        print(f"❌ File not found: {source}")
        return None
    
    # Keep original extension or use .mp4
    extension = source.suffix if source.suffix else ".mp4"
    output_path = VIDEOS_DIR / f"{video_name}{extension}"
    
    print(f"📁 Copying: {source}")
    print(f"   To: {output_path}")
    
    try:
        shutil.copy2(source, output_path)
        print(f"✅ Video copied successfully")
        return output_path
    except Exception as e:
        print(f"❌ Failed to copy file: {e}")
        return None


def extract_frames(video_name: str) -> bool:
    """Extract frames from video"""
    print_step(2, "Extract Frames")
    
    script_path = Path(__file__).parent / "extract_frames.py"
    video_path = VIDEOS_DIR / f"{video_name}.mp4"
    
    command = [
        sys.executable,
        str(script_path),
        "--video", video_path.name
    ]
    
    return run_command("Extracting frames", command, cwd=script_path.parent)


def detect_objects(video_name: str) -> bool:
    """Detect and crop objects using YOLO"""
    print_step(3, "Detect and Crop Objects with YOLO")
    
    script_path = Path(__file__).parent / "process_objects_yolo.py"
    
    # We need to process only frames from this video
    frames_path = FRAMES_DIR / video_name
    
    command = [
        sys.executable,
        str(script_path)
    ]
    
    return run_command("Detecting objects", command, cwd=script_path.parent)


def compute_embeddings(video_name: str) -> bool:
    """Compute CLIP embeddings"""
    print_step(4, "Compute CLIP Embeddings")
    
    script_path = Path(__file__).parent / "compute_clip_embeddings.py"
    
    command = [
        sys.executable,
        str(script_path)
    ]
    
    return run_command("Computing embeddings", command, cwd=script_path.parent)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Process a new video through the complete pipeline"
    )
    
    # Video source options (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--drive-url",
        help="Google Drive URL of the video"
    )
    source_group.add_argument(
        "--youtube-url",
        help="YouTube URL of the video"
    )
    source_group.add_argument(
        "--local-file",
        help="Path to local video file"
    )
    
    # Required video name
    parser.add_argument(
        "--video-name",
        required=True,
        help="Name for the video (e.g., 'video_5', 'video_CH28')"
    )
    
    # Optional processing flags
    parser.add_argument(
        "--skip-frames",
        action="store_true",
        help="Skip frame extraction (if already done)"
    )
    parser.add_argument(
        "--skip-objects",
        action="store_true",
        help="Skip object detection"
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embeddings computation"
    )
    
    args = parser.parse_args()
    
    print("🎬 PROCESSING NEW VIDEO")
    print("=" * 70)
    print(f"Video name: {args.video_name}")
    
    # Create necessary directories
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    OBJECTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Get the video
    video_path = None
    
    if args.drive_url:
        video_path = download_from_drive(args.drive_url, args.video_name)
    elif args.youtube_url:
        video_path = download_from_youtube(args.youtube_url, args.video_name)
    elif args.local_file:
        video_path = copy_local_file(args.local_file, args.video_name)
    
    if not video_path or not video_path.exists():
        print("\n❌ Failed to get video file. Exiting.")
        return False
    
    print(f"\n✅ Video ready: {video_path}")
    
    # Step 2: Extract frames
    if not args.skip_frames:
        if not extract_frames(args.video_name):
            print("\n❌ Frame extraction failed. Exiting.")
            return False
    else:
        print("\n⏭️  Skipping frame extraction")
    
    # Step 3: Detect objects
    if not args.skip_objects:
        if not detect_objects(args.video_name):
            print("\n⚠️  Object detection failed, continuing anyway...")
    else:
        print("\n⏭️  Skipping object detection")
    
    # Step 4: Compute embeddings and upload to S3
    if not args.skip_embeddings:
        if not compute_embeddings(args.video_name):
            print("\n❌ Embeddings computation failed. Exiting.")
            return False
    else:
        print("\n⏭️  Skipping embeddings computation")
    
    # Success!
    print("\n" + "=" * 70)
    print("🎉 VIDEO PROCESSING COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print(f"✅ Video: {video_path}")
    print(f"✅ Frames: {FRAMES_DIR / args.video_name}")
    print(f"✅ Objects: {OBJECTS_DIR / args.video_name}")
    print(f"✅ All data uploaded to S3")
    print("\n🔍 The new video is now searchable in the application!")
    print("🚀 Start the app: python main.py")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
