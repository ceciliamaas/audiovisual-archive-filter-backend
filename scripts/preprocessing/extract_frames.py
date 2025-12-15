import cv2
from pathlib import Path

# Get project root and data directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"
FRAMES_DIR = DATA_DIR / "frames"


def extract_frames(video_path: str = None, output_dir: str = None, fps: int = 1):
    """Extract frames from video to data/frames directory"""
    if output_dir is None:
        output_dir = FRAMES_DIR
    else:
        output_dir = Path(output_dir)
    """
    Extract frames from a video at the specified FPS rate.
    Saves them as JPG files in output_dir.

    Args:
        video_path (str): Path to the video file.
        output_dir (str): Folder where frames will be saved.
        fps (int): How many frames per second to extract.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Load video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps == 0:
        raise ValueError("The video FPS is zero. File may be corrupted.")

    # Extract frames at specified FPS
    frame_interval = int(video_fps // fps)

    frame_index = 0
    saved_index = 0

    print(f"Extracting frames from: {video_path}")
    print(f"Video FPS: {video_fps}, capturing every {frame_interval} frames")

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # End of video

        if frame_index % frame_interval == 0:
            frame_path = output / f"frame_{saved_index:05d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            print(f"Saved: {frame_path}")
            saved_index += 1

        frame_index += 1

    cap.release()
    print(f"Done. Extracted {saved_index} frames.")


def main():
    """Main function to extract frames from videos in data/videos/"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract frames from videos")
    parser.add_argument("--video", help="Specific video file to process")
    parser.add_argument(
        "--fps", type=int, default=1, help="Frames per second to extract (default: 1)"
    )

    args = parser.parse_args()

    print("🎬 Starting frame extraction...")
    print(f"📁 Videos directory: {VIDEOS_DIR}")
    print(f"📁 Output directory: {FRAMES_DIR}")

    # Create output directory
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    if args.video:
        # Process specific video
        video_path = VIDEOS_DIR / args.video
        if not video_path.exists():
            print(f"❌ Video not found: {video_path}")
            return

        video_name = video_path.stem
        output_dir = FRAMES_DIR / f"video_{video_name}"

        print(f"🎯 Processing: {video_path.name}")
        extract_frames(str(video_path), str(output_dir), args.fps)

    else:
        # Process all videos in videos directory
        if not VIDEOS_DIR.exists():
            print(f"❌ Videos directory not found: {VIDEOS_DIR}")
            print("   Please download videos first using download_videos.py")
            return

        video_files = list(VIDEOS_DIR.glob("*.mp4"))
        if not video_files:
            print(f"❌ No video files found in {VIDEOS_DIR}")
            return

        print(f"🎬 Found {len(video_files)} videos to process")

        for i, video_path in enumerate(video_files, 1):
            video_name = f"video_{i}"
            output_dir = FRAMES_DIR / video_name

            print(f"\n🎯 Processing {i}/{len(video_files)}: {video_path.name}")
            try:
                extract_frames(str(video_path), str(output_dir), args.fps)
            except Exception as e:
                print(f"❌ Error processing {video_path.name}: {e}")
                continue

    print("\n✅ Frame extraction completed!")


if __name__ == "__main__":
    main()
