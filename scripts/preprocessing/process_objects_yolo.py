"""
YOLO Object Detection and Cropping Script

Processes video frames to:
1. Detect objects using YOLO-World-XL
2. Crop detected objects
3. Store cropped objects in data/objects/
4. Upload results to S3 storage

Usage:
    python process_objects_yolo.py
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
import tempfile

import cv2
import numpy as np
from PIL import Image
from dotenv import load_dotenv
import replicate

# Add src to path for storage imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.storage import get_storage_manager

# =============================================================================
# Configuration
# =============================================================================

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise RuntimeError("Missing REPLICATE_API_TOKEN in .env")

client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# Directories
DATA_DIR = PROJECT_ROOT / "data"
FRAMES_DIR = DATA_DIR / "frames"
OBJECTS_DIR = DATA_DIR / "objects"

# Create directories
OBJECTS_DIR.mkdir(parents=True, exist_ok=True)

# Target video directories to process
# Set to None to process all video directories, or specify one or more:
# TARGET_VIDEOS = None                    # Process all videos
# TARGET_VIDEOS = ["video_CH27"]          # Process only CH27
# TARGET_VIDEOS = ["video_1", "video_2"]  # Process specific videos
TARGET_VIDEOS = ["video_CH205"]  # Currently targeting video 1

# YOLO classes to detect (can be customized)
# Try with most common YOLO classes
YOLO_CLASSES = ["person", "car", "building"]

# =============================================================================
# YOLO Detection Functions
# =============================================================================


def detect_objects_yolo(image_path: Path, classes: List[str]) -> List[Dict]:
    """
    Detect objects in image using YOLO-World-XL

    Args:
        image_path: Path to image file
        classes: List of object classes to detect

    Returns:
        List of detection dictionaries with bbox coordinates
    """
    try:
        with open(image_path, "rb") as f:
            output = client.run(
                "franz-biz/yolo-world-xl:fd1305d3fc19e81540542f51c2530cf8f393e28cc6ff4976337c3e2b75c7c292",
                input={
                    "input_media": f,
                    "classes": ",".join(classes),
                    "confidence_threshold": 0.01,  # Extremely low threshold
                    "iou_threshold": 0.3,  # Low IOU threshold
                },
            )

        if not output:
            print(f"  Debug: No output for {image_path.name}")
            return []

        print(f"  Debug: Raw output keys: {list(output.keys())}")

        # Check for different possible output formats
        if "detections" in output:
            return parse_yolo_output(output["detections"])
        elif "json_str" in output and output["json_str"]:
            return parse_yolo_output(output["json_str"])
        else:
            print(f"  Debug: No detections found in output")
            return []

    except Exception as e:
        print(f"YOLO detection failed for {image_path}: {e}")
        return []


def parse_yolo_output(detections_raw) -> List[Dict]:
    """Parse YOLO output to extract bounding boxes"""
    detections = []

    try:
        if isinstance(detections_raw, str):
            detections_data = json.loads(detections_raw)
        else:
            detections_data = detections_raw

        if isinstance(detections_data, dict):
            # Handle format: {"Det-0": {...}, "Det-1": {...}}
            for det in detections_data.values():
                if isinstance(det, str):
                    det = json.loads(det)

                if not isinstance(det, dict):
                    continue

                x0, y0, x1, y1 = (
                    det.get("x0"),
                    det.get("y0"),
                    det.get("x1"),
                    det.get("y1"),
                )
                if None in (x0, y0, x1, y1):
                    continue

                detections.append(
                    {
                        "bbox": [
                            int(round(x0)),
                            int(round(y0)),
                            int(round(x1)),
                            int(round(y1)),
                        ],
                        "score": det.get("score", 0.0),
                        "class": det.get("cls", "unknown"),
                    }
                )

    except Exception as e:
        print(f"Error parsing YOLO output: {e}")

    return detections


def crop_objects(image_path: Path, detections: List[Dict]) -> List[Path]:
    """
    Crop detected objects from image and save them

    Args:
        image_path: Path to original image
        detections: List of detection dictionaries

    Returns:
        List of paths to cropped object images
    """
    if not detections:
        return []

    cropped_paths = []

    try:
        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            return []

        img_height, img_width = img.shape[:2]

        # Extract video name from frame path
        # e.g., data/frames/video_1/frame_00001.jpg -> video_1
        video_name = image_path.parent.name
        frame_stem = image_path.stem  # e.g., "frame_00001"

        # Create video-specific objects directory
        video_objects_dir = OBJECTS_DIR / video_name
        video_objects_dir.mkdir(exist_ok=True)

        for i, det in enumerate(detections):
            bbox = det["bbox"]
            x0, y0, x1, y1 = bbox

            # Validate bbox
            x0 = max(0, min(x0, img_width))
            y0 = max(0, min(y0, img_height))
            x1 = max(x0, min(x1, img_width))
            y1 = max(y0, min(y1, img_height))

            if x1 - x0 < 10 or y1 - y0 < 10:  # Skip very small objects
                continue

            # Crop object
            cropped = img[y0:y1, x0:x1]

            # Save cropped object in video directory
            obj_filename = f"{frame_stem}_obj_{i}.jpg"
            obj_path = video_objects_dir / obj_filename

            cv2.imwrite(str(obj_path), cropped)
            cropped_paths.append(obj_path)

    except Exception as e:
        print(f"Error cropping objects from {image_path}: {e}")

    return cropped_paths


# =============================================================================
# Main Processing Function
# =============================================================================


def process_frame_objects(frame_path: Path) -> int:
    """
    Process a single frame to detect and crop objects

    Args:
        frame_path: Path to frame image

    Returns:
        Number of objects cropped
    """
    print(f"Processing: {frame_path.name}")

    # Detect objects
    detections = detect_objects_yolo(frame_path, YOLO_CLASSES)

    if not detections:
        print(f"  No objects detected")
        return 0

    print(f"  Found {len(detections)} objects")

    # Crop objects
    cropped_paths = crop_objects(frame_path, detections)

    print(f"  Cropped {len(cropped_paths)} objects")
    return len(cropped_paths)


def main():
    """Main processing function"""
    print("🎯 Starting YOLO object detection and cropping...")

    # Initialize storage manager
    storage = get_storage_manager()
    print(f"📦 Using storage: {storage.get_storage().get_info()['backend_type']}")

    # Find frame images based on target configuration
    if not FRAMES_DIR.exists():
        print(f"❌ Frames directory not found: {FRAMES_DIR}")
        print("   Please extract frames first using extract_frames.py")
        return

    frame_files = []
    processed_videos = []

    if TARGET_VIDEOS is None:
        # Process all video directories
        video_dirs = [d for d in FRAMES_DIR.glob("video_*") if d.is_dir()]
        print(f"🎯 Processing all video directories...")
    else:
        # Process specific video directories
        video_dirs = []
        for target in TARGET_VIDEOS:
            video_dir = FRAMES_DIR / target
            if video_dir.exists() and video_dir.is_dir():
                video_dirs.append(video_dir)
            else:
                print(f"⚠️  Warning: Video directory not found: {target}")
        print(f"🎯 Processing target video directories: {TARGET_VIDEOS}")

    for video_dir in video_dirs:
        video_frames = list(video_dir.glob("*.jpg"))
        frame_files.extend(video_frames)
        processed_videos.append(video_dir.name)
        print(f"   📁 {video_dir.name}: {len(video_frames)} frames")

    if not frame_files:
        print(f"❌ No frame files found in specified directories")
        return

    print(
        f"🖼️  Found {len(frame_files)} total frames to process across {len(processed_videos)} videos"
    )

    # Process frames
    total_objects = 0
    start_time = time.time()

    for i, frame_path in enumerate(frame_files, 1):
        objects_cropped = process_frame_objects(frame_path)
        total_objects += objects_cropped

        if i % 10 == 0:
            elapsed = time.time() - start_time
            print(
                f"📊 Progress: {i}/{len(frame_files)} frames ({i/len(frame_files)*100:.1f}%)"
            )
            print(f"   Total objects cropped: {total_objects}")
            print(f"   Time elapsed: {elapsed:.1f}s")

    print(f"\n✅ Object detection and cropping complete!")
    print(f"   📸 Processed {len(frame_files)} frames")
    print(f"   🎯 Cropped {total_objects} objects")
    print(f"   💾 Objects stored in: {OBJECTS_DIR}")

    # Upload objects to S3
    print(f"\n📤 Uploading objects to S3...")
    try:
        uploaded = 0
        for obj_file in OBJECTS_DIR.glob("**/*.jpg"):
            # Use relative path from objects directory for storage key
            relative_path = obj_file.relative_to(OBJECTS_DIR)
            storage_key = f"objects/{relative_path}"
            with open(obj_file, "rb") as f:
                success = storage.put(storage_key, f.read())
                if success:
                    uploaded += 1

        print(f"✅ Uploaded {uploaded} objects to S3")

    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")
        print("💾 Objects remain available locally in data/objects/")


if __name__ == "__main__":
    main()
