"""
Detect objects step for the pipeline.

Uses YOLO-World-XL via Replicate API to detect and crop objects from frames.
"""

import os
import json
import cv2
from pathlib import Path
from typing import Optional, List, Dict
from dotenv import load_dotenv

from .base import PipelineStep
from ..state import VideoStatus
from ..naming import NamingConvention

load_dotenv()


class DetectObjectsStep(PipelineStep):
    """Detect objects in frames using YOLO."""

    @property
    def step_name(self) -> str:
        return "detect_objects"

    @property
    def step_status_in_progress(self) -> VideoStatus:
        return VideoStatus.DETECTING_OBJECTS

    @property
    def step_status_completed(self) -> VideoStatus:
        return VideoStatus.OBJECTS_DETECTED

    def validate_input(self) -> tuple[bool, Optional[str]]:
        """Validate that frames exist."""
        frames_dir = NamingConvention.frames_dir_local(self.video_name)

        if not frames_dir.exists():
            return False, f"Frames directory not found: {frames_dir}"

        frame_files = list(frames_dir.glob("frame_*.jpg"))
        if len(frame_files) == 0:
            return False, "No frames found"

        # Check for Replicate API token
        if not os.getenv("REPLICATE_API_TOKEN"):
            return False, "REPLICATE_API_TOKEN not set in environment"

        return True, None

    def execute(self) -> bool:
        """Detect objects in all frames."""
        try:
            import replicate
        except ImportError:
            print("    Installing replicate...")
            import subprocess, sys

            subprocess.check_call([sys.executable, "-m", "pip", "install", "replicate"])
            import replicate

        frames_dir = NamingConvention.frames_dir_local(self.video_name)
        objects_dir = NamingConvention.objects_dir_local(self.video_name)
        objects_dir.mkdir(parents=True, exist_ok=True)

        # Get classes from config (default: person, gun, backpack, hat)
        classes = self._get_config(
            "yolo_classes", ["person", "gun", "backpack", "hat", "building", "car"]
        )
        # Handle None case (when no classes provided)
        if classes is None:
            classes = ["person", "gun", "backpack", "hat", "building", "car"]

        confidence = self._get_config("confidence_threshold", 0.01)
        iou = self._get_config("iou_threshold", 0.3)

        print(f"    Frames: {frames_dir}")
        print(f"    Objects: {objects_dir}")
        print(f"    Classes: {', '.join(classes)}")

        # Get all frames
        frame_files = sorted(frames_dir.glob("frame_*.jpg"))
        total_frames = len(frame_files)

        # Count existing objects
        existing_objects = list(objects_dir.glob("frame_*_obj_*.jpg"))
        total_objects = len(existing_objects)

        # Find frames that already have objects detected
        processed_frame_indices = set()
        for obj_file in existing_objects:
            frame_idx, _ = NamingConvention.parse_object_indices(obj_file.name)
            if frame_idx is not None:
                processed_frame_indices.add(frame_idx)

        client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

        frames_to_process = 0
        for frame_path in frame_files:
            frame_index = NamingConvention.parse_frame_index(frame_path.name)
            if frame_index not in processed_frame_indices:
                frames_to_process += 1

        if frames_to_process == 0:
            print(
                f"    All frames already processed ({len(processed_frame_indices)} frames)"
            )
            print(f"    Total objects: {total_objects}")
            return True

        print(
            f"    Processing {frames_to_process} remaining frames (skipping {len(processed_frame_indices)} already done)"
        )

        processed = 0
        for i, frame_path in enumerate(frame_files):
            frame_index = NamingConvention.parse_frame_index(frame_path.name)
            if frame_index is None:
                continue

            # Skip if already processed
            if frame_index in processed_frame_indices:
                continue

            processed += 1
            print(
                f"    Processing frame {processed}/{frames_to_process} (total: {i+1}/{total_frames})...",
                end="\r",
            )

            try:
                # Run YOLO detection
                with open(frame_path, "rb") as f:
                    output = client.run(
                        "franz-biz/yolo-world-xl:fd1305d3fc19e81540542f51c2530cf8f393e28cc6ff4976337c3e2b75c7c292",
                        input={
                            "input_media": f,
                            "classes": ",".join(classes),
                            "confidence_threshold": confidence,
                            "iou_threshold": iou,
                            "return_json": True,
                        },
                    )

                # Parse the new API response format
                if not output or "json_str" not in output:
                    continue

                # Parse JSON string to get detections
                detections_dict = json.loads(output["json_str"])
                if not detections_dict:
                    continue

                # Filter detections to only include specified classes
                allowed_classes = set(classes)
                valid_detections = [
                    det
                    for det in detections_dict.values()
                    if det.get("cls") in allowed_classes
                ]

                if not valid_detections:
                    continue

                # Crop and save each detection
                frame_img = cv2.imread(str(frame_path))
                for obj_idx, det in enumerate(valid_detections):
                    # Extract bounding box coordinates
                    x1 = int(det.get("x0", 0))
                    y1 = int(det.get("y0", 0))
                    x2 = int(det.get("x1", 0))
                    y2 = int(det.get("y1", 0))

                    if x1 >= x2 or y1 >= y2:
                        continue

                    # Crop object
                    cropped = frame_img[y1:y2, x1:x2]
                    if cropped.size == 0:
                        continue

                    # Save object
                    object_path = NamingConvention.object_local_path(
                        self.video_name, frame_index, obj_idx
                    )
                    cv2.imwrite(str(object_path), cropped)
                    total_objects += 1

            except Exception as e:
                print(f"    Error processing frame {frame_index}: {e}")
                continue

        # Update state
        self.state.object_count = total_objects
        print(f"    Detected {total_objects} objects in {total_frames} frames")

        return True

    def validate_output(self) -> tuple[bool, Optional[str]]:
        """Validate that objects were detected."""
        objects_dir = NamingConvention.objects_dir_local(self.video_name)

        if not objects_dir.exists():
            return False, f"Objects directory not created: {objects_dir}"

        # Count objects
        object_files = list(objects_dir.glob("frame_*_obj_*.jpg"))

        # It's okay if no objects were detected (some frames may have no objects)
        # Just verify the count matches state
        if self.state.object_count != len(object_files):
            return (
                False,
                f"Object count mismatch: expected {self.state.object_count}, found {len(object_files)}",
            )

        return True, None
