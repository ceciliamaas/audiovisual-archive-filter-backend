"""
Pipeline orchestrator for video processing.

Coordinates all pipeline steps and manages the workflow.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from tqdm import tqdm
import time

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
            print(f"Existing state found: {state.status.value}")
            
            # If force is True, reset the state to start fresh
            if force:
                print("Force flag enabled - resetting state")
                state = PipelineState(
                    video_name=video_name, source_type=source_type, source_url=source_url
                )
                state.save()
                print("Starting fresh processing")
            elif state.status == VideoStatus.COMPLETED:
                print("Already completed. Use --force to reprocess.")
                return True
            else:
                print("Resuming from last state")
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

        # Track timing for each step
        step_times = {}
        total_start = time.time()

        # Run each step with progress bar
        with tqdm(
            total=len(all_steps),
            desc=f"Pipeline: {video_name}",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} steps",
        ) as pbar:
            for step_name, step_class in all_steps:
                pbar.set_description(f"Pipeline: {video_name} [{step_name}]")

                print(f"\n--- Step: {step_name} ---")

                step = step_class(state, self.config)

                # Time the step execution
                step_start = time.time()
                success = step.run(force=force)
                step_duration = time.time() - step_start
                step_times[step_name] = step_duration

                if not success:
                    print(f"\n✗ Pipeline failed at step: {step_name}")
                    pbar.close()
                    return False

                # Display step timing
                minutes = int(step_duration // 60)
                seconds = int(step_duration % 60)
                print(f"⏱️  Step completed in: {minutes}m {seconds}s")

                pbar.update(1)

        # Calculate total time
        total_duration = time.time() - total_start
        total_minutes = int(total_duration // 60)
        total_seconds = int(total_duration % 60)

        # Success!
        print(f"\n{'='*60}")
        print(f"✅ Pipeline complete for: {video_name}")
        print(f"{'='*60}")
        print(f"Status: {state.status.value}")
        print(f"Frames: {state.frame_count}")
        print(f"Objects: {state.object_count}")
        print(f"Steps: {', '.join(state.steps_completed)}")
        print(f"\n⏱️  Timing Summary:")
        for step_name, duration in step_times.items():
            mins = int(duration // 60)
            secs = int(duration % 60)
            print(f"   {step_name:20s}: {mins}m {secs}s")
        print(f"   {'Total':20s}: {total_minutes}m {total_seconds}s")
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
