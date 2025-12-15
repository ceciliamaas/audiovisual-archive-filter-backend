#!/usr/bin/env python3
"""
Rename object files to remove video prefix

Removes the video identifier from object filenames since they're now
organized in video-specific directories.

Example:
- video_1_frame_00001_obj_0.jpg -> frame_00001_obj_0.jpg
- video_CH27_frame_00001_obj_0.jpg -> frame_00001_obj_0.jpg
"""

import os
from pathlib import Path

# Get project root and directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OBJECTS_DIR = DATA_DIR / "objects"


def rename_objects_in_directory(video_dir):
    """Rename object files in a video directory to remove video prefix"""

    if not video_dir.is_dir():
        return 0

    object_files = list(video_dir.glob("*.jpg"))

    if not object_files:
        return 0

    print(f"📂 Processing {video_dir.name}: {len(object_files)} files")

    renamed_count = 0

    for obj_file in object_files:
        old_name = obj_file.name

        # Extract new name by removing video prefix
        # Examples:
        # video_1_frame_00001_obj_0.jpg -> frame_00001_obj_0.jpg
        # video_CH27_frame_00001_obj_0.jpg -> frame_00001_obj_0.jpg

        if old_name.startswith("video_"):
            parts = old_name.split("_", 2)  # Split into max 3 parts

            if len(parts) >= 3:
                # Skip first two parts (video_X), keep the rest
                new_name = parts[2]  # frame_00001_obj_0.jpg
            else:
                # Fallback - keep original name
                continue

        else:
            # File doesn't have video prefix - skip
            continue

        # Create new path
        new_path = video_dir / new_name

        # Check if new name already exists
        if new_path.exists():
            print(f"   ⚠️  Skipping {old_name} - {new_name} already exists")
            continue

        try:
            # Rename the file
            obj_file.rename(new_path)
            renamed_count += 1

            if renamed_count % 500 == 0:
                print(f"   Renamed {renamed_count} files...")

        except Exception as e:
            print(f"   ❌ Error renaming {old_name}: {e}")

    return renamed_count


def main():
    """Main function to rename all object files"""
    print("🏷️  Starting object file renaming...")

    if not OBJECTS_DIR.exists():
        print(f"❌ Objects directory not found: {OBJECTS_DIR}")
        return

    # Find all video directories
    video_dirs = [
        d for d in OBJECTS_DIR.iterdir() if d.is_dir() and d.name.startswith("video_")
    ]

    if not video_dirs:
        print(f"⚠️  No video directories found in {OBJECTS_DIR}")
        return

    print(f"📁 Found {len(video_dirs)} video directories")

    total_renamed = 0

    for video_dir in sorted(video_dirs):
        renamed_count = rename_objects_in_directory(video_dir)
        total_renamed += renamed_count

        if renamed_count > 0:
            print(f"   ✅ Renamed {renamed_count} files in {video_dir.name}")

    print(f"\n✅ Renaming complete!")
    print(f"   📁 Processed {len(video_dirs)} directories")
    print(f"   🏷️  Renamed {total_renamed} files")

    # Show sample of new structure
    print(f"\n📂 Sample of new file structure:")
    for video_dir in sorted(video_dirs[:3]):  # Show first 3 directories
        sample_files = list(video_dir.glob("*.jpg"))[:3]  # Show 3 files per directory
        if sample_files:
            print(f"   {video_dir.name}/:")
            for sample_file in sample_files:
                print(f"     - {sample_file.name}")


if __name__ == "__main__":
    main()
