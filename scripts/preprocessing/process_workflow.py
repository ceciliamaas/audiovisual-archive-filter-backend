#!/usr/bin/env python3
"""
Complete Processing Workflow

Orchestrates the full processing pipeline:
1. Download videos (optional)
2. Extract frames from videos
3. Detect and crop objects with YOLO
4. Compute CLIP embeddings for all images
5. Upload everything to S3

Usage:
    python process_workflow.py [--skip-download] [--skip-frames] [--skip-objects] [--skip-embeddings]
"""

import sys
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def run_step(step_name: str, func, *args, **kwargs):
    """Run a processing step with error handling"""
    print(f"\n{'='*60}")
    print(f"🚀 {step_name}")
    print(f"{'='*60}")

    try:
        result = func(*args, **kwargs)
        if result is False:
            print(f"❌ {step_name} failed")
            return False
        print(f"✅ {step_name} completed successfully")
        return True
    except Exception as e:
        print(f"❌ {step_name} failed with error: {e}")
        return False


def main():
    """Main workflow function"""
    parser = argparse.ArgumentParser(
        description="Run complete video processing workflow"
    )
    parser.add_argument(
        "--skip-download", action="store_true", help="Skip video download step"
    )
    parser.add_argument(
        "--skip-frames", action="store_true", help="Skip frame extraction step"
    )
    parser.add_argument(
        "--skip-objects",
        action="store_true",
        help="Skip object detection/cropping step",
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embeddings computation step",
    )
    parser.add_argument(
        "--force-embeddings", action="store_true", help="Force recompute all embeddings"
    )

    args = parser.parse_args()

    print("🎬 Starting Complete Video Processing Workflow")
    print("=" * 60)

    # Step 1: Download videos (optional)
    if not args.skip_download:
        from download_videos import main as download_main

        if not run_step("STEP 1: Download Videos", download_main):
            print("⚠️  Video download failed, but continuing with existing videos...")
    else:
        print("\n⏭️  Skipping video download")

    # Step 2: Extract frames
    if not args.skip_frames:
        from extract_frames import main as frames_main

        if not run_step("STEP 2: Extract Frames", frames_main):
            print("❌ Cannot continue without frames")
            return False
    else:
        print("\n⏭️  Skipping frame extraction")

    # Step 3: Detect and crop objects
    if not args.skip_objects:
        from process_objects_yolo import main as objects_main

        if not run_step("STEP 3: Detect and Crop Objects", objects_main):
            print(
                "⚠️  Object detection failed, but continuing with frame embeddings only..."
            )
    else:
        print("\n⏭️  Skipping object detection")

    # Step 4: Compute embeddings
    if not args.skip_embeddings:
        from compute_clip_embeddings import main as embeddings_main

        # Override sys.argv to pass force flag
        original_argv = sys.argv.copy()
        sys.argv = ["compute_clip_embeddings.py"]
        if args.force_embeddings:
            sys.argv.append("--force")

        try:
            if not run_step("STEP 4: Compute CLIP Embeddings", embeddings_main):
                print("❌ Embeddings computation failed")
                return False
        finally:
            sys.argv = original_argv
    else:
        print("\n⏭️  Skipping embeddings computation")

    print("\n" + "=" * 60)
    print("🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("📊 All data has been processed and stored in S3")
    print("🔍 The search application is ready to use")
    print("🚀 You can now start the Streamlit app: python main.py")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
