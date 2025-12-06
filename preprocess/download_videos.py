import os
from yt_dlp import YoutubeDL


def download_videos(video_urls, output_dir):
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


if __name__ == "__main__":
    # List of videos to download
    video_links = [
        "https://www.youtube.com/watch?v=CYfHg8L8cc8",
        #  "https://www.youtube.com/watch?v=1uwMvQ5z4L4",
        #  "https://www.youtube.com/watch?v=HNi6Anic2ew",
        # Add more links here
    ]

    # Destination folder
    destination_folder = (
        "/Users/Cecilia/Documents/Programación/archive_filter/input_videos"
    )

    download_videos(video_links, destination_folder)
