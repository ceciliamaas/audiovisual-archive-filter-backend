"""
Upload step for the pipeline.

Uploads all video artifacts to S3 storage:
- Original video
- Frames
- Objects
- Embeddings
"""

import sys
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .base import PipelineStep
from ..state import VideoStatus
from ..naming import NamingConvention


class UploadStep(PipelineStep):
    """Upload all artifacts to S3."""

    MAX_WORKERS = 10  # Number of concurrent uploads

    @property
    def step_name(self) -> str:
        return "upload"

    @property
    def step_status_in_progress(self) -> VideoStatus:
        return VideoStatus.UPLOADING

    @property
    def step_status_completed(self) -> VideoStatus:
        return VideoStatus.COMPLETED

    def validate_input(self) -> tuple[bool, Optional[str]]:
        """Validate that all artifacts exist locally."""
        # Video
        video_path = NamingConvention.video_local_path(self.video_name)
        if not video_path.exists():
            return False, f"Video not found: {video_path}"

        # Frames
        frames_dir = NamingConvention.frames_dir_local(self.video_name)
        if not frames_dir.exists():
            return False, f"Frames directory not found: {frames_dir}"

        # Embeddings are now stored in Qdrant, not pickle files
        return True, None

    def execute(self) -> bool:
        """Upload all artifacts to S3."""
        # Import storage manager
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from src.storage import get_storage_manager

        storage_manager = get_storage_manager()
        storage = storage_manager.get_storage()

        # Upload video
        print("    Uploading video...")
        video_path = NamingConvention.video_local_path(self.video_name)
        video_key = NamingConvention.video_s3_key(self.video_name)
        if not storage.upload_file(str(video_path), video_key):
            print(f"    Error uploading video")
            return False

        # Upload frames concurrently
        print("    Uploading frames...")
        frames_dir = NamingConvention.frames_dir_local(self.video_name)
        frame_files = list(frames_dir.glob("frame_*.jpg"))

        def upload_frame(frame_path):
            """Upload a single frame."""
            frame_index = NamingConvention.parse_frame_index(frame_path.name)
            if frame_index is None:
                return False
            frame_key = NamingConvention.frame_s3_key(self.video_name, frame_index)
            return storage.upload_file(str(frame_path), frame_key)

        failed_frames = 0
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {executor.submit(upload_frame, fp): fp for fp in frame_files}
            with tqdm(
                total=len(frame_files),
                desc="    Frames",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}",
            ) as pbar:
                for future in as_completed(futures):
                    if not future.result():
                        failed_frames += 1
                    pbar.update(1)

        if failed_frames > 0:
            print(f"    Warning: {failed_frames} frames failed to upload")

        # Upload objects concurrently (if they exist)
        objects_dir = NamingConvention.objects_dir_local(self.video_name)
        if objects_dir.exists():
            print("    Uploading objects...")
            object_files = list(objects_dir.glob("frame_*_obj_*.jpg"))

            def upload_object(obj_path):
                """Upload a single object."""
                indices = NamingConvention.parse_object_indices(obj_path.name)
                if indices is None:
                    return False
                frame_idx, obj_idx = indices
                obj_key = NamingConvention.object_s3_key(
                    self.video_name, frame_idx, obj_idx
                )
                return storage.upload_file(str(obj_path), obj_key)

            failed_objects = 0
            with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                futures = {
                    executor.submit(upload_object, op): op for op in object_files
                }
                with tqdm(
                    total=len(object_files),
                    desc="    Objects",
                    bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}",
                ) as pbar:
                    for future in as_completed(futures):
                        if not future.result():
                            failed_objects += 1
                        pbar.update(1)

            if failed_objects > 0:
                print(f"    Warning: {failed_objects} objects failed to upload")

        # Upload embeddings
        # Embeddings are now stored in Qdrant, no need to upload pickle files
        print("    Embeddings stored in Qdrant (no S3 upload needed)")
        print("    Upload complete")
        return True

    def validate_output(self) -> tuple[bool, Optional[str]]:
        """Validate that files were uploaded."""
        # Import storage manager
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from src.storage import get_storage_manager

        storage_manager = get_storage_manager()
        storage = storage_manager.get_storage()

        # Check video exists in S3
        video_key = NamingConvention.video_s3_key(self.video_name)
        if not storage.file_exists(video_key):
            return False, f"Video not found in S3: {video_key}"

        # Check at least one frame exists
        frame_key = NamingConvention.frame_s3_key(self.video_name, 0)
        if not storage.file_exists(frame_key):
            return False, f"Frames not found in S3"

        # Check embeddings exist
        if not storage.file_exists(NamingConvention.frame_embeddings_s3_key()):
            return False, "Frame embeddings not found in S3"

        return True, None
