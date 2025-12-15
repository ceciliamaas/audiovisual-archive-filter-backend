"""
Download videos from youtube and store it in data directory
"""

import os
from pathlib import Path
from yt_dlp import YoutubeDL

# Get project root and data directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"


def download_videos(video_urls, output_dir=None):
    """Download videos to data/videos directory"""
    if output_dir is None:
        output_dir = VIDEOS_DIR
    else:
        output_dir = Path(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        # Use modern JS challenge solver
        "exec": {"js": "deno eval --unstable --print <SELF>"},
        # Select best video + audio
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        # Force merged output to MP4
        "merge_output_format": "mp4",
        # Ensure ffmpeg is used to merge streams
        "postprocessors": [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
            {"key": "FFmpegEmbedSubtitle"},
        ],
        # Output filename
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "quiet": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        for url in video_urls:
            print(f"\n📥 Downloading: {url}")
            try:
                ydl.download([url])
            except Exception as e:
                print(f"❌ Error downloading {url}: {e}")


def main():
    """Main function to download videos"""
    import argparse

    parser = argparse.ArgumentParser(description="Download videos from YouTube URLs")
    parser.add_argument("urls", nargs="*", help="Video URLs to download")
    parser.add_argument(
        "--output", "-o", help="Output directory (default: data/videos)"
    )

    args = parser.parse_args()

    print("📥 Starting video download...")

    # Create videos directory
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    if args.urls:
        # Use URLs from command line
        video_urls = args.urls
    else:
        # Use default URLs
        video_urls = [
            "https://www.youtube.com/watch?v=CYfHg8L8cc8",
            # Add more default URLs here if needed
        ]

    if not video_urls:
        print("❌ No video URLs provided")
        print("Usage: python download_videos.py <url1> <url2> ...")
        return

    output_dir = args.output if args.output else VIDEOS_DIR

    print(f"📁 Output directory: {output_dir}")
    print(f"🎬 Downloading {len(video_urls)} videos...")

    download_videos(video_urls, output_dir)

    print("\n✅ Video download completed!")


if __name__ == "__main__":
    main()
