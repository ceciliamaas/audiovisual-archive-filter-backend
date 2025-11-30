import os
from yt_dlp import YoutubeDL


def download_videos(video_urls, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        # Use modern JS challenge solver
        "exec": {"js": "deno eval --unstable --print <SELF>"},
        # Download best available video+audio (even if WebM)
        "format": "bv*+ba/best",
        # Force MP4 output
        "merge_output_format": "mp4",
        # Output filename
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        # Show progress
        "quiet": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        for url in video_urls:
            print(f"\n📥 Downloading: {url}")
            try:
                ydl.download([url])
            except Exception as e:
                print(f"❌ Error downloading {url}: {e}")


if __name__ == "__main__":
    # List of videos to download
    video_links = [
        "https://www.youtube.com/watch?v=CYfHg8L8cc8",
        # Add more links here
    ]

    # Destination folder
    destination_folder = (
        "/Users/Cecilia/Documents/Programación/archive_filter/input_videos"
    )

    download_videos(video_links, destination_folder)
