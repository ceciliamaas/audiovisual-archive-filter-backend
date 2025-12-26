"""
Command-line interface for the video processing pipeline.

Usage:
    # Process a new video
    python -m scripts.pipeline process VIDEO_NAME --source youtube URL
    python -m scripts.pipeline process VIDEO_NAME --source drive URL
    python -m scripts.pipeline process VIDEO_NAME --source local PATH
    
    # Resume processing
    python -m scripts.pipeline resume VIDEO_NAME
    
    # Check status
    python -m scripts.pipeline status VIDEO_NAME
    python -m scripts.pipeline list [--status STATUS]
    
    # Validate artifacts
    python -m scripts.pipeline validate VIDEO_NAME
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.state import VideoStatus


def cmd_process(args):
    """Process a video through the pipeline."""
    pipeline = Pipeline(config={
        "fps": args.fps,
        "yolo_classes": args.yolo_classes.split(",") if args.yolo_classes else None,
        "confidence_threshold": args.confidence,
        "iou_threshold": args.iou,
    })
    
    success = pipeline.process_video(
        video_name=args.video_name,
        source_type=args.source,
        source_url=args.url,
        steps=args.steps.split(",") if args.steps else None,
        force=args.force
    )
    
    sys.exit(0 if success else 1)


def cmd_resume(args):
    """Resume processing a video."""
    pipeline = Pipeline()
    success = pipeline.resume_video(args.video_name)
    sys.exit(0 if success else 1)


def cmd_status(args):
    """Show status of a video."""
    pipeline = Pipeline()
    state = pipeline.get_video_status(args.video_name)
    
    if not state:
        print(f"No state found for video: {args.video_name}")
        sys.exit(1)
    
    print(f"\nVideo: {state.video_name}")
    print(f"Status: {state.status.value}")
    print(f"Source: {state.source_type} - {state.source_url}")
    print(f"Created: {state.created_at}")
    print(f"Updated: {state.updated_at}")
    
    if state.frame_count:
        print(f"Frames: {state.frame_count}")
    if state.object_count:
        print(f"Objects: {state.object_count}")
    
    if state.steps_completed:
        print(f"Steps completed: {', '.join(state.steps_completed)}")
    
    if state.error_message:
        print(f"Error: {state.error_message}")
    
    print()


def cmd_list(args):
    """List all videos."""
    pipeline = Pipeline()
    
    # Parse status filter if provided
    status_filter = None
    if args.status:
        try:
            status_filter = VideoStatus(args.status)
        except ValueError:
            print(f"Invalid status: {args.status}")
            print(f"Valid values: {', '.join(s.value for s in VideoStatus)}")
            sys.exit(1)
    
    states = pipeline.list_videos(status=status_filter)
    
    if not states:
        print("No videos found.")
        return
    
    print(f"\nFound {len(states)} video(s):\n")
    print(f"{'Video Name':<30} {'Status':<20} {'Frames':<8} {'Objects':<8}")
    print("-" * 70)
    
    for state in states:
        status_emoji = "✅" if state.status == VideoStatus.COMPLETED else "⏳" if state.status.is_processing() else "✗" if state.status == VideoStatus.FAILED else "⏸"
        print(
            f"{status_emoji} {state.video_name:<28} "
            f"{state.status.value:<20} "
            f"{state.frame_count or 0:<8} "
            f"{state.object_count or 0:<8}"
        )
    
    print()


def cmd_validate(args):
    """Validate artifacts for a video."""
    pipeline = Pipeline()
    success = pipeline.validate_video(args.video_name)
    sys.exit(0 if success else 1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Video processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    subparsers.required = True
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process a new video")
    process_parser.add_argument("video_name", help="Name for the video")
    process_parser.add_argument("--source", required=True, choices=["youtube", "drive", "local"], help="Source type")
    process_parser.add_argument("--url", required=True, help="URL or path to video")
    process_parser.add_argument("--steps", help="Comma-separated list of steps to run (default: all)")
    process_parser.add_argument("--force", action="store_true", help="Reprocess even if already completed")
    process_parser.add_argument("--fps", type=int, default=1, help="Frames per second to extract (default: 1)")
    process_parser.add_argument("--yolo-classes", help="Comma-separated YOLO classes to detect")
    process_parser.add_argument("--confidence", type=float, default=0.01, help="YOLO confidence threshold (default: 0.01)")
    process_parser.add_argument("--iou", type=float, default=0.3, help="YOLO IOU threshold (default: 0.3)")
    process_parser.set_defaults(func=cmd_process)
    
    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume processing a video")
    resume_parser.add_argument("video_name", help="Name of the video")
    resume_parser.set_defaults(func=cmd_resume)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show status of a video")
    status_parser.add_argument("video_name", help="Name of the video")
    status_parser.set_defaults(func=cmd_status)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all videos")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.set_defaults(func=cmd_list)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate artifacts for a video")
    validate_parser.add_argument("video_name", help="Name of the video")
    validate_parser.set_defaults(func=cmd_validate)
    
    # Parse and run
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
