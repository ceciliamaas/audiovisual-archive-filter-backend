"""
Download step for the pipeline.

Supports downloading from:
- YouTube (using yt-dlp)
- Google Drive (using gdown)
- Local file path (copy)
"""

import shutil
import sys
import subprocess
from pathlib import Path
from typing import Optional

from .base import PipelineStep
from ..state import VideoStatus
from ..naming import NamingConvention


class DownloadStep(PipelineStep):
    """Download video from YouTube, Drive, or local path."""

    @property
    def step_name(self) -> str:
        return "download"

    @property
    def step_status_in_progress(self) -> VideoStatus:
        return VideoStatus.DOWNLOADING

    @property
    def step_status_completed(self) -> VideoStatus:
        return VideoStatus.DOWNLOADED

    def validate_input(self) -> tuple[bool, Optional[str]]:
        """Validate that source information is available."""
        if not self.state.source_type:
            return False, "No source_type specified"

        if not self.state.source_url:
            return False, "No source_url specified"

        source_type = self.state.source_type.lower()
        if source_type not in ["youtube", "drive", "local"]:
            return (
                False,
                f"Invalid source_type: {source_type} (must be youtube, drive, or local)",
            )

        # Validate local path exists
        if source_type == "local":
            local_path = Path(self.state.source_url)
            if not local_path.exists():
                return False, f"Local file not found: {local_path}"
            if not local_path.is_file():
                return False, f"Path is not a file: {local_path}"

        return True, None

    def execute(self) -> bool:
        """Execute the download."""
        source_type = self.state.source_type.lower()

        if source_type == "youtube":
            return self._download_youtube()
        elif source_type == "drive":
            return self._download_drive()
        elif source_type == "local":
            return self._copy_local()

        return False

    def validate_output(self) -> tuple[bool, Optional[str]]:
        """Validate that video file exists and has video stream."""
        video_path = NamingConvention.video_local_path(self.video_name)

        if not video_path.exists():
            # Check if file exists without extension (yt-dlp might not add .mp4)
            video_path_no_ext = video_path.with_suffix("")
            if video_path_no_ext.exists():
                # Rename to add .mp4 extension
                video_path_no_ext.rename(video_path)
                print(f"    ✓ Renamed {video_path_no_ext.name} to {video_path.name}")
            else:
                return False, f"Video file not created: {video_path}"

        if video_path.stat().st_size == 0:
            return False, f"Video file is empty: {video_path}"

        # Check that file has video stream using ffprobe
        has_video = self._check_video_stream(video_path)
        if not has_video:
            return (
                False,
                f"Downloaded file has no video stream (audio-only). This video only has audio available, possibly due to YouTube restrictions or age/region restrictions. Try a different video URL.",
            )

        return True, None

    def _check_video_stream(self, video_path: Path) -> bool:
        """Check if video file has a video stream using ffprobe."""
        try:
            import json

            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_streams",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                print(f"    Warning: Could not probe video file with ffprobe")
                return True  # Assume valid if we can't check

            probe_data = json.loads(result.stdout)
            streams = probe_data.get("streams", [])

            # Check if any stream is video
            has_video = any(stream.get("codec_type") == "video" for stream in streams)

            if not has_video:
                print(f"    ✗ Downloaded file has no video stream (audio-only)")
                print(
                    f"    Available streams: {[s.get('codec_type') for s in streams]}"
                )
            else:
                video_streams = [s for s in streams if s.get("codec_type") == "video"]
                print(
                    f"    ✓ Video stream found: {video_streams[0].get('codec_name', 'unknown')}"
                )

            return has_video

        except subprocess.TimeoutExpired:
            print(f"    Warning: ffprobe timeout")
            return True  # Assume valid if timeout
        except Exception as e:
            print(f"    Warning: Could not check video streams: {e}")
            return True  # Assume valid if we can't check

    def _download_youtube(self) -> bool:
        """Download from YouTube using yt-dlp."""
        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            print("    Installing yt-dlp...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
            from yt_dlp import YoutubeDL

        video_path = NamingConvention.video_local_path(self.video_name)
        video_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing file if it exists (for force re-download)
        if video_path.exists():
            print(f"    Removing existing file: {video_path}")
            video_path.unlink()

        print(f"    Downloading from YouTube: {self.state.source_url}")
        print(f"    Saving to: {video_path}")

        # First, list available formats to find one with video
        print(f"    Checking available formats...")
        list_opts = {"quiet": True, "listformats": True}

        video_format_id = None
        try:
            with YoutubeDL(list_opts) as ydl:
                info = ydl.extract_info(self.state.source_url, download=False)
                formats = info.get("formats", [])

                # Find best format with video codec
                video_formats = [
                    f
                    for f in formats
                    if f.get("vcodec") != "none" and f.get("vcodec") != None
                ]

                if video_formats:
                    # Sort by resolution and prefer mp4
                    video_formats.sort(
                        key=lambda f: (
                            f.get("height", 0),
                            1 if f.get("ext") == "mp4" else 0,
                        ),
                        reverse=True,
                    )
                    video_format_id = video_formats[0]["format_id"]
                    print(
                        f"    Found video format: {video_format_id} ({video_formats[0].get('height', '?')}p)"
                    )
                else:
                    print(
                        f"    Warning: No video formats found, trying default selection"
                    )
        except Exception as e:
            print(f"    Warning: Could not list formats: {e}")

        # Download with explicit format selection
        ydl_opts = {
            "format": (
                video_format_id
                if video_format_id
                else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            ),
            "merge_output_format": "mp4",
            "outtmpl": str(video_path.with_suffix("")),  # Remove .mp4, yt-dlp adds it
            "quiet": False,
            "no_warnings": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([self.state.source_url])

                # yt-dlp might use the video title, rename if needed
                if not video_path.exists():
                    # Look for any .mp4 file in the directory
                    for file in video_path.parent.glob("*.mp4"):
                        if file.name != video_path.name:
                            file.rename(video_path)
                            print(f"    Renamed: {file.name} -> {video_path.name}")
                            break

                return True
            except Exception as e:
                print(f"    Download failed: {e}")
                return False

    def _download_drive(self) -> bool:
        """Download from Google Drive using gdown."""
        try:
            import gdown
        except ImportError:
            print("    Installing gdown...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
            import gdown

        video_path = NamingConvention.video_local_path(self.video_name)
        video_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract file ID from URL
        file_id = self._extract_drive_file_id(self.state.source_url)
        if not file_id:
            print(
                f"    Error: Could not extract file ID from URL: {self.state.source_url}"
            )
            print(f"    Supported formats:")
            print(f"      - https://drive.google.com/file/d/FILE_ID/view")
            print(f"      - https://drive.google.com/open?id=FILE_ID")
            print(f"      - https://drive.google.com/uc?id=FILE_ID")
            print(f"      - Just the FILE_ID")
            return False

        url = f"https://drive.google.com/uc?id={file_id}"

        print(f"    Downloading from Google Drive")
        print(f"    File ID: {file_id}")
        print(f"    Saving to: {video_path}")

        try:
            gdown.download(url, str(video_path), quiet=False)
            return True
        except Exception as e:
            print(f"    Error: {e}")
            print(f"    Make sure the file is shared with 'Anyone with the link'")
            return False

    def _copy_local(self) -> bool:
        """Copy from local path."""
        source_path = Path(self.state.source_url)
        video_path = NamingConvention.video_local_path(self.video_name)
        video_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"    Copying from: {source_path}")
        print(f"    Copying to: {video_path}")

        try:
            shutil.copy2(source_path, video_path)
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False

    def _extract_drive_file_id(self, drive_url: str) -> Optional[str]:
        """Extract file ID from Google Drive URL.

        Supports formats:
        - https://drive.google.com/file/d/FILE_ID/view
        - https://drive.google.com/open?id=FILE_ID
        - https://drive.google.com/uc?id=FILE_ID
        - Just the FILE_ID itself
        """
        import re

        if "drive.google.com" not in drive_url:
            # Maybe it's just the file ID
            if re.match(r"^[a-zA-Z0-9_-]{20,}$", drive_url):
                return drive_url
            return None

        # Format: https://drive.google.com/file/d/FILE_ID/view
        if "/file/d/" in drive_url:
            return drive_url.split("/file/d/")[1].split("/")[0].split("?")[0]

        # Format: https://drive.google.com/open?id=FILE_ID
        # Format: https://drive.google.com/uc?id=FILE_ID
        elif "id=" in drive_url:
            return drive_url.split("id=")[1].split("&")[0]

        return None
