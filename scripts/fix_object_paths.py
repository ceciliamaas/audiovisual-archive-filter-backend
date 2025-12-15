#!/usr/bin/env python3
"""
Fix object paths in embeddings to match actual S3 structure
"""

import pickle
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage import get_storage_manager


def fix_object_paths():
    """Download, fix, and re-upload object_paths.pkl"""

    print("🔧 Fixing object paths in embeddings...")

    storage_manager = get_storage_manager()
    storage = storage_manager.get_storage()

    # Download current object_paths.pkl
    print("📥 Downloading object_paths.pkl from S3...")
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        tmp_path = tmp.name
        success = storage.download_file("embeddings/object_paths.pkl", tmp_path)

        if not success:
            print("❌ Failed to download object_paths.pkl")
            return False

    # Load the paths
    print("📂 Loading paths...")
    with open(tmp_path, "rb") as f:
        object_paths = pickle.load(f)

    print(f"Found {len(object_paths)} paths")
    print(f"Type: {type(object_paths)}")

    # Show some examples of current paths
    print("\n📋 Examples of current paths:")
    for i in range(min(5, len(object_paths))):
        print(f"  {object_paths[i]}")

    # Fix the paths
    fixed_paths = []

    if isinstance(object_paths, list):
        print("\n🔨 Fixing paths...")
        for path in object_paths:
            # Path format: cropped_objects/video_1_frame_00367_obj_2.jpg (old format)
            # Should be: objects/video_1/frame_00367_obj_2.jpg (new S3 structure)

            if path.startswith("cropped_objects/"):
                # Remove prefix
                filename = path.replace("cropped_objects/", "")

                # Extract video number from filename
                # Filename format: video_1_frame_00367_obj_2.jpg
                if filename.startswith("video_"):
                    parts = filename.split("_", 2)  # Split on first 2 underscores
                    if len(parts) >= 3:
                        video_num = parts[0] + "_" + parts[1]  # video_1, video_2, etc.
                        rest = parts[2]  # frame_00367_obj_2.jpg

                        # Construct correct path
                        correct_path = f"objects/{video_num}/{rest}"
                        fixed_paths.append(correct_path)
                    else:
                        # Keep original if format doesn't match
                        fixed_paths.append(path)
                else:
                    # Keep original if format doesn't match
                    fixed_paths.append(path)
            else:
                # Keep non-cropped-object paths as-is
                fixed_paths.append(path)

        print(f"✅ Fixed {len(fixed_paths)} paths")

        # Show some examples
        print("\n📋 Examples of fixed paths:")
        for i in range(min(5, len(fixed_paths))):
            print(f"  {fixed_paths[i]}")
    else:
        print("❌ Unexpected format, expected list")
        return False

    # Save fixed paths
    print("\n💾 Saving fixed paths...")
    fixed_tmp = tempfile.NamedTemporaryFile(suffix=".pkl", delete=False)
    fixed_tmp_path = fixed_tmp.name
    fixed_tmp.close()

    with open(fixed_tmp_path, "wb") as f:
        pickle.dump(fixed_paths, f)

    # Upload back to S3
    print("📤 Uploading fixed object_paths.pkl to S3...")
    success = storage.upload_file(fixed_tmp_path, "embeddings/object_paths.pkl")

    if success:
        print("✅ Successfully uploaded fixed object_paths.pkl!")
        print("\n🎉 Object paths have been fixed!")
        print("Restart the Streamlit app to see the changes.")
        return True
    else:
        print("❌ Failed to upload fixed paths")
        return False


if __name__ == "__main__":
    fix_object_paths()
