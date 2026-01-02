"""
Pipeline orchestrator for video processing.

Coordinates all pipeline steps and manages the workflow.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from .state import PipelineState, VideoStatus
from .naming import NamingConvention
from .steps import (
    DownloadStep,
    ExtractFramesStep,
    DetectObjectsStep,
    ComputeEmbeddingsStep,
    UploadStep,
)


class Pipeline:
    """Orchestrates the video processing pipeline."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize pipeline.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

    def process_video(
        self,
        video_name: str,
        source_type: str,
        source_url: str,
        steps: Optional[List[str]] = None,
        force: bool = False,
    ) -> bool:
        """Process a video through the pipeline.

        Args:
            video_name: Name for the video (will be sanitized)
            source_type: Type of source (youtube, drive, local)
            source_url: URL or path to source
            steps: Optional list of steps to run (default: all)
            force: If True, rerun even if already completed

        Returns:
            True if successful, False otherwise
        """
        # Sanitize video name
        video_name = NamingConvention.sanitize_video_name(video_name)

        print(f"\n{'='*60}")
        print(f"Processing: {video_name}")
        print(f"{'='*60}\n")

        # Load or create state
        state = PipelineState.load(video_name)
        if state:
            print(f"Resuming from status: {state.status.value}")
            if state.status == VideoStatus.COMPLETED and not force:
                print("Already completed. Use --force to reprocess.")
                return True
        else:
            state = PipelineState(
                video_name=video_name, source_type=source_type, source_url=source_url
            )
            state.save()
            print("Starting new processing")

        # Define all steps
        all_steps = [
            ("download", DownloadStep),
            ("extract_frames", ExtractFramesStep),
            ("detect_objects", DetectObjectsStep),
            ("compute_embeddings", ComputeEmbeddingsStep),
            ("upload", UploadStep),
        ]

        # Filter steps if specified
        if steps:
            all_steps = [(name, cls) for name, cls in all_steps if name in steps]

        # Run each step
        for step_name, step_class in all_steps:
            print(f"\n--- Step: {step_name} ---")

            step = step_class(state, self.config)
            success = step.run(force=force)

            if not success:
                print(f"\n✗ Pipeline failed at step: {step_name}")
                return False

        # Success!
        print(f"\n{'='*60}")
        print(f"✅ Pipeline complete for: {video_name}")
        print(f"{'='*60}")
        print(f"Status: {state.status.value}")
        print(f"Frames: {state.frame_count}")
        print(f"Objects: {state.object_count}")
        print(f"Steps: {', '.join(state.steps_completed)}")
        print()

        return True

    def list_videos(self, status: Optional[VideoStatus] = None) -> List[PipelineState]:
        """List all videos in the pipeline.

        Args:
            status: Optional status filter

        Returns:
            List of PipelineState instances
        """
        if status:
            return PipelineState.list_by_status(status)
        return PipelineState.list_all()

    def get_video_status(self, video_name: str) -> Optional[PipelineState]:
        """Get status of a specific video.

        Args:
            video_name: Name of the video

        Returns:
            PipelineState or None if not found
        """
        video_name = NamingConvention.sanitize_video_name(video_name)
        return PipelineState.load(video_name)

    def resume_video(self, video_name: str) -> bool:
        """Resume processing for a video.

        Args:
            video_name: Name of the video

        Returns:
            True if successful, False otherwise
        """
        video_name = NamingConvention.sanitize_video_name(video_name)
        state = PipelineState.load(video_name)

        if not state:
            print(f"No state found for video: {video_name}")
            return False

        if state.status == VideoStatus.COMPLETED:
            print(f"Video already completed: {video_name}")
            return True

        if state.status == VideoStatus.FAILED:
            print(f"Video failed. Starting from last successful step...")

        # Resume processing
        return self.process_video(
            video_name=state.video_name,
            source_type=state.source_type,
            source_url=state.source_url,
            force=False,
        )

    def validate_video(self, video_name: str) -> bool:
        """Validate all artifacts for a video.

        Args:
            video_name: Name of the video

        Returns:
            True if all artifacts are valid
        """
        video_name = NamingConvention.sanitize_video_name(video_name)
        state = PipelineState.load(video_name)

        if not state:
            print(f"✗ No state found for video: {video_name}")
            return False

        print(f"\nValidating: {video_name}")
        print(f"Status: {state.status.value}")

        # Check each step
        steps = [
            ("download", DownloadStep),
            ("extract_frames", ExtractFramesStep),
            ("detect_objects", DetectObjectsStep),
            ("compute_embeddings", ComputeEmbeddingsStep),
            ("upload", UploadStep),
        ]

        all_valid = True
        for step_name, step_class in steps:
            if not state.is_step_completed(step_name):
                print(f"  ⏭  {step_name}: not completed")
                continue

            step = step_class(state, self.config)
            is_valid, error = step.validate_output()

            if is_valid:
                print(f"  ✓ {step_name}: valid")
            else:
                print(f"  ✗ {step_name}: {error}")
                all_valid = False

        if all_valid:
            print(f"\n✅ All artifacts valid for {video_name}")
        else:
            print(f"\n✗ Some artifacts invalid for {video_name}")

        return all_valid
