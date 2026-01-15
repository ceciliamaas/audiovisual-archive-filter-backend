#!/usr/bin/env python3
"""
Create bbox JSON metadata files for existing detected objects.

This script:
1. Finds all existing object images
2. For each object, runs YOLO again on the corresponding frame to get bbox data
3. Saves bbox metadata as JSON files

Usage: python create_bbox_metadata.py <video_name>
"""

import sys
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.pipeline.naming import NamingConvention


def process_frame(
    frame_path: Path,
    video_name: str,
    frame_index: int,
    classes: list,
    confidence: float,
    iou: float,
    client,
) -> tuple:
    """Run YOLO on a frame and return bbox data for all detections"""
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

        # Parse the API response
        if not output or "json_str" not in output:
            return (frame_index, [], None)

        # Parse JSON string to get detections
        detections_dict = json.loads(output["json_str"])
        if not detections_dict:
            return (frame_index, [], None)

        # Filter detections to only include specified classes
        allowed_classes = set(classes)
        valid_detections = [
            det for det in detections_dict.values() if det.get("cls") in allowed_classes
        ]

        if not valid_detections:
            return (frame_index, [], None)

        # Extract bounding boxes
        bboxes = []
        for det in valid_detections:
            x1 = int(det.get("x0", 0))
            y1 = int(det.get("y0", 0))
            x2 = int(det.get("x1", 0))
            y2 = int(det.get("y1", 0))

            if x1 < x2 and y1 < y2:
                bboxes.append([x1, y1, x2, y2])

        return (frame_index, bboxes, None)

    except Exception as e:
        return (frame_index, [], str(e))


def main():
    if len(sys.argv) < 2:
        print("Usage: python create_bbox_metadata.py <video_name>")
        print(
            "Example: python create_bbox_metadata.py manifestacion_jubilados_12_de_marzo"
        )
        sys.exit(1)

    video_name = sys.argv[1]

    print(f"📦 Creating bbox metadata for: {video_name}")
    print("=" * 60)

    try:
        import replicate
    except ImportError:
        print("Installing replicate...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "replicate"])
        import replicate

    frames_dir = NamingConvention.frames_dir_local(video_name)
    objects_dir = NamingConvention.objects_dir_local(video_name)

    if not objects_dir.exists():
        print(f"❌ Objects directory not found: {objects_dir}")
        sys.exit(1)

    # Get all existing object files
    object_files = sorted(objects_dir.glob("frame_*_obj_*.jpg"))

    # Group by frame
    frames_to_process = {}
    for obj_file in object_files:
        frame_idx, obj_idx = NamingConvention.parse_object_indices(obj_file.name)
        if frame_idx is not None:
            if frame_idx not in frames_to_process:
                frames_to_process[frame_idx] = []
            frames_to_process[frame_idx].append((obj_file, obj_idx))

    print(f"Found {len(object_files)} objects across {len(frames_to_process)} frames")
    print(f"Frames dir: {frames_dir}")
    print(f"Objects dir: {objects_dir}")

    # YOLO config
    classes = ["person", "gun", "backpack", "hat", "building", "car"]
    confidence = 0.01
    iou = 0.3

    client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

    # Process frames concurrently
    print("\nRunning YOLO detection on frames...")

    bbox_data_by_frame = {}
    errors = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for frame_idx in frames_to_process.keys():
            frame_path = NamingConvention.frame_local_path(video_name, frame_idx)
            if frame_path.exists():
                future = executor.submit(
                    process_frame,
                    frame_path,
                    video_name,
                    frame_idx,
                    classes,
                    confidence,
                    iou,
                    client,
                )
                futures[future] = frame_idx

        with tqdm(total=len(futures), desc="Processing frames") as pbar:
            for future in as_completed(futures):
                frame_idx = futures[future]
                frame_idx_result, bboxes, error = future.result()

                if error:
                    errors += 1
                    if errors <= 5:
                        tqdm.write(f"Error processing frame {frame_idx}: {error}")
                else:
                    bbox_data_by_frame[frame_idx] = bboxes

                pbar.update(1)

    print(
        f"\nSuccessfully processed {len(bbox_data_by_frame)} frames ({errors} errors)"
    )

    # Now create JSON files for each object
    print("\nCreating JSON metadata files...")
    json_created = 0

    for frame_idx, objects in tqdm(
        frames_to_process.items(), desc="Creating JSON files"
    ):
        if frame_idx not in bbox_data_by_frame:
            continue

        bboxes = bbox_data_by_frame[frame_idx]

        # Match objects with bboxes (by object index order)
        for obj_file, obj_idx in objects:
            if obj_idx < len(bboxes):
                bbox = bboxes[obj_idx]

                # Create JSON metadata file
                json_path = obj_file.with_suffix(".json")
                bbox_data = {
                    "bbox": bbox,
                    "frame_index": frame_idx,
                    "object_index": obj_idx,
                }

                with open(json_path, "w") as f:
                    json.dump(bbox_data, f)

                json_created += 1

    print("\n" + "=" * 60)
    print(f"✅ Created {json_created} bbox JSON metadata files!")
    print(f"   Total objects: {len(object_files)}")
    print(f"   Objects with bbox data: {json_created}")
    print(f"\nNow run: python reindex_with_bbox.py {video_name}")
    print("to update Qdrant with the bbox data.")


if __name__ == "__main__":
    main()
