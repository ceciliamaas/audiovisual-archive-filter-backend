#!/usr/bin/env python3
"""
Organize objects into video-specific directories

Reorganizes objects in data/objects/ into subdirectories matching
the video structure in data/frames/
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict

# Get project root and directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OBJECTS_DIR = DATA_DIR / "objects"


def organize_objects():
    """Organize objects into video-specific directories"""
    print("📁 Organizing objects into video directories...")

    if not OBJECTS_DIR.exists():
        print(f"❌ Objects directory not found: {OBJECTS_DIR}")
        return

    # Find all object files
    object_files = list(OBJECTS_DIR.glob("*.jpg"))

    if not object_files:
        print(f"⚠️  No object files found in {OBJECTS_DIR}")
        return

    print(f"🖼️  Found {len(object_files)} object files to organize")

    # Group files by video
    video_groups = defaultdict(list)

    for obj_file in object_files:
        filename = obj_file.name

        # Extract video identifier from filename
        # Examples:
        # - video_1_frame_00001_obj_0.jpg -> video_1
        # - video_CH27_frame_00001_obj_0.jpg -> video_CH27
        if filename.startswith("video_"):
            parts = filename.split("_")
            if len(parts) >= 2:
                if parts[1].startswith("CH") or parts[1].isdigit():
                    # video_CH27 or video_1
                    video_id = f"{parts[0]}_{parts[1]}"
                else:
                    # fallback to just video_X
                    video_id = parts[0]

                video_groups[video_id].append(obj_file)
            else:
                # Fallback - put in 'other' directory
                video_groups["other"].append(obj_file)
        else:
            # Non-standard filename - put in 'other'
            video_groups["other"].append(obj_file)

    print(f"📊 Found objects from {len(video_groups)} video groups:")
    for video_id, files in video_groups.items():
        print(f"   {video_id}: {len(files)} objects")

    # Create directories and move files
    moved_count = 0

    for video_id, files in video_groups.items():
        # Create video directory
        video_dir = OBJECTS_DIR / video_id
        video_dir.mkdir(exist_ok=True)

        print(f"\n📂 Moving {len(files)} objects to {video_id}/")

        for obj_file in files:
            try:
                new_path = video_dir / obj_file.name

                # Move file to video directory
                shutil.move(str(obj_file), str(new_path))
                moved_count += 1

                if moved_count % 100 == 0:
                    print(f"   Moved {moved_count} files...")

            except Exception as e:
                print(f"❌ Error moving {obj_file.name}: {e}")

    print(f"\n✅ Organization complete!")
    print(f"   📁 Moved {moved_count} objects into {len(video_groups)} directories")
    print(f"   📂 Directory structure:")

    # Show final structure
    for video_dir in sorted(OBJECTS_DIR.glob("video_*")):
        if video_dir.is_dir():
            count = len(list(video_dir.glob("*.jpg")))
            print(f"      {video_dir.name}/: {count} objects")


def main():
    """Main function"""
    print("🗂️  Starting object organization...")
    organize_objects()
    print("🎉 Object organization completed!")


if __name__ == "__main__":
    main()
