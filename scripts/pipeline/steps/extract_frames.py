"""
Extract frames step for the pipeline.

Extracts frames from video at specified FPS using OpenCV.
"""

import cv2
from pathlib import Path
from typing import Optional

from .base import PipelineStep
from ..state import VideoStatus
from ..naming import NamingConvention


class ExtractFramesStep(PipelineStep):
    """Extract frames from video."""

    @property
    def step_name(self) -> str:
        return "extract_frames"

    @property
    def step_status_in_progress(self) -> VideoStatus:
        return VideoStatus.EXTRACTING_FRAMES

    @property
    def step_status_completed(self) -> VideoStatus:
        return VideoStatus.FRAMES_EXTRACTED

    def validate_input(self) -> tuple[bool, Optional[str]]:
        """Validate that video file exists."""
        video_path = NamingConvention.video_local_path(self.video_name)

        if not video_path.exists():
            return False, f"Video file not found: {video_path}"

        return True, None

    def execute(self) -> bool:
        """Extract frames from video."""
        video_path = NamingConvention.video_local_path(self.video_name)
        frames_dir = NamingConvention.frames_dir_local(self.video_name)
        frames_dir.mkdir(parents=True, exist_ok=True)

        # Get FPS from config (default: 1 frame per second)
        target_fps = self._get_config("fps", 1)

        print(f"    Video: {video_path}")
        print(f"    Output: {frames_dir}")
        print(f"    Target FPS: {target_fps}")

        # Load video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"    Error: Could not open video")
            return False

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps == 0:
            print(f"    Error: Video FPS is zero (corrupted file?)")
            cap.release()
            return False

        # Calculate frame interval
        frame_interval = max(1, int(video_fps // target_fps))

        print(
            f"    Video FPS: {video_fps:.2f}, extracting every {frame_interval} frames"
        )

        frame_index = 0
        saved_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break  # End of video

                # Save frame at interval
                if frame_index % frame_interval == 0:
                    frame_path = NamingConvention.frame_local_path(
                        self.video_name, saved_count
                    )
                    cv2.imwrite(str(frame_path), frame)
                    saved_count += 1

                    # Progress indicator every 10 frames
                    if saved_count % 10 == 0:
                        print(f"    Extracted {saved_count} frames...", end="\r")

                frame_index += 1

            cap.release()

            # Update state with frame count
            self.state.frame_count = saved_count
            print(f"    Extracted {saved_count} frames                ")

            return True

        except Exception as e:
            cap.release()
            print(f"    Error during extraction: {e}")
            return False

    def validate_output(self) -> tuple[bool, Optional[str]]:
        """Validate that frames were extracted."""
        frames_dir = NamingConvention.frames_dir_local(self.video_name)

        if not frames_dir.exists():
            return False, f"Frames directory not created: {frames_dir}"

        # Count frames
        frame_files = list(frames_dir.glob("frame_*.jpg"))
        if len(frame_files) == 0:
            return False, "No frames extracted"

        # Verify frame count matches state
        if self.state.frame_count != len(frame_files):
            return (
                False,
                f"Frame count mismatch: expected {self.state.frame_count}, found {len(frame_files)}",
            )

        return True, None
