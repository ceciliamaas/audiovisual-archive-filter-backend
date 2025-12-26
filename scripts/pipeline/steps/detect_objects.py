"""
Detect objects step for the pipeline.

Uses YOLO-World-XL via Replicate API to detect and crop objects from frames.
"""

import os
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
        classes = self._get_config("yolo_classes", ["person", "gun", "backpack", "hat", "building", "car"])
        confidence = self._get_config("confidence_threshold", 0.01)
        iou = self._get_config("iou_threshold", 0.3)
        
        print(f"    Frames: {frames_dir}")
        print(f"    Objects: {objects_dir}")
        print(f"    Classes: {', '.join(classes)}")
        
        # Get all frames
        frame_files = sorted(frames_dir.glob("frame_*.jpg"))
        total_frames = len(frame_files)
        total_objects = 0
        
        client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))
        
        for i, frame_path in enumerate(frame_files):
            frame_index = NamingConvention.parse_frame_index(frame_path.name)
            if frame_index is None:
                continue
            
            print(f"    Processing frame {i+1}/{total_frames}...", end="\r")
            
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
                
                if not output or "detections" not in output:
                    continue
                
                detections = output["detections"]
                if not detections:
                    continue
                
                # Crop and save each detection
                frame_img = cv2.imread(str(frame_path))
                for obj_idx, det in enumerate(detections):
                    bbox = det.get("bbox")
                    if not bbox or len(bbox) != 4:
                        continue
                    
                    x1, y1, x2, y2 = map(int, bbox)
                    
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
            return False, f"Object count mismatch: expected {self.state.object_count}, found {len(object_files)}"
        
        return True, None
