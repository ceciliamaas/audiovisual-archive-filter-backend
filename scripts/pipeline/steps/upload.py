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

from .base import PipelineStep
from ..state import VideoStatus
from ..naming import NamingConvention


class UploadStep(PipelineStep):
    """Upload all artifacts to S3."""

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

        # Embeddings
        frame_emb_path = NamingConvention.frame_embeddings_local()
        if not frame_emb_path.exists():
            return False, f"Frame embeddings not found: {frame_emb_path}"

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

        # Upload frames
        print("    Uploading frames...")
        frames_dir = NamingConvention.frames_dir_local(self.video_name)
        frame_files = list(frames_dir.glob("frame_*.jpg"))
        for i, frame_path in enumerate(frame_files):
            frame_index = NamingConvention.parse_frame_index(frame_path.name)
            if frame_index is None:
                continue

            frame_key = NamingConvention.frame_s3_key(self.video_name, frame_index)
            if not storage.upload_file(str(frame_path), frame_key):
                print(f"    Warning: Failed to upload {frame_path.name}")

            if (i + 1) % 10 == 0:
                print(f"    Uploaded {i+1}/{len(frame_files)} frames...", end="\r")

        print(f"    Uploaded {len(frame_files)} frames                ")

        # Upload objects (if they exist)
        objects_dir = NamingConvention.objects_dir_local(self.video_name)
        if objects_dir.exists():
            print("    Uploading objects...")
            object_files = list(objects_dir.glob("frame_*_obj_*.jpg"))
            for i, obj_path in enumerate(object_files):
                indices = NamingConvention.parse_object_indices(obj_path.name)
                if indices is None:
                    continue

                frame_idx, obj_idx = indices
                obj_key = NamingConvention.object_s3_key(
                    self.video_name, frame_idx, obj_idx
                )
                if not storage.upload_file(str(obj_path), obj_key):
                    print(f"    Warning: Failed to upload {obj_path.name}")

                if (i + 1) % 10 == 0:
                    print(
                        f"    Uploaded {i+1}/{len(object_files)} objects...", end="\r"
                    )

            print(f"    Uploaded {len(object_files)} objects                ")

        # Upload embeddings
        print("    Uploading embeddings...")

        # Frame embeddings
        frame_emb_path = NamingConvention.frame_embeddings_local()
        frame_paths_path = NamingConvention.frame_paths_local()
        storage.upload_file(
            str(frame_emb_path), NamingConvention.frame_embeddings_s3_key()
        )
        storage.upload_file(
            str(frame_paths_path), NamingConvention.frame_paths_s3_key()
        )

        # Object embeddings (if they exist)
        obj_emb_path = NamingConvention.object_embeddings_local()
        obj_paths_path = NamingConvention.object_paths_local()
        if obj_emb_path.exists() and obj_paths_path.exists():
            storage.upload_file(
                str(obj_emb_path), NamingConvention.object_embeddings_s3_key()
            )
            storage.upload_file(
                str(obj_paths_path), NamingConvention.object_paths_s3_key()
            )

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
