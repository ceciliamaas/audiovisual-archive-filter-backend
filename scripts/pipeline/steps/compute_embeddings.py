"""
Compute embeddings step for the pipeline.

Computes CLIP embeddings for frames and objects using Replicate API.
Stores embeddings in Qdrant vector database.
Supports concurrent processing for faster execution.
"""

import os
import sys
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from tqdm import tqdm
import time

from .base import PipelineStep
from ..state import VideoStatus
from ..naming import NamingConvention

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.storage.qdrant import QdrantStorage

load_dotenv()


class ComputeEmbeddingsStep(PipelineStep):
    """Compute CLIP embeddings for frames and objects with concurrent processing."""

    # Number of concurrent API requests (with sufficient credit, higher limits apply)
    MAX_WORKERS = 10  # Process 10 images in parallel
    RETRY_DELAYS = [5, 10, 15]  # Retry delays in seconds for rate limit errors

    @property
    def step_name(self) -> str:
        return "compute_embeddings"

    @property
    def step_status_in_progress(self) -> VideoStatus:
        return VideoStatus.COMPUTING_EMBEDDINGS

    @property
    def step_status_completed(self) -> VideoStatus:
        return VideoStatus.EMBEDDINGS_COMPUTED

    def validate_input(self) -> tuple[bool, Optional[str]]:
        """Validate that frames exist."""
        frames_dir = NamingConvention.frames_dir_local(self.video_name)

        if not frames_dir.exists():
            return False, f"Frames directory not found: {frames_dir}"

        frame_files = list(frames_dir.glob("frame_*.jpg"))
        if len(frame_files) == 0:
            return False, "No frames found"

        # Check for Replicate API token
        if not os.getenv("REPLICATE_API_TOKEN"):
            return False, "REPLICATE_API_TOKEN not set in environment"

        return True, None

    def execute(self) -> bool:
        """Compute embeddings for frames and objects."""
        try:
            import replicate
        except ImportError:
            print("    Installing replicate...")
            import subprocess, sys

            subprocess.check_call([sys.executable, "-m", "pip", "install", "replicate"])
            import replicate

        client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

        # Compute frame embeddings
        print("    Computing frame embeddings...")
        if not self._compute_frame_embeddings(client):
            return False

        # Compute object embeddings (if objects exist)
        objects_dir = NamingConvention.objects_dir_local(self.video_name)
        if objects_dir.exists() and list(objects_dir.glob("frame_*_obj_*.jpg")):
            print("    Computing object embeddings...")
            if not self._compute_object_embeddings(client):
                return False
        else:
            print("    No objects to process, skipping object embeddings")

        return True

    def _compute_frame_embeddings(self, client) -> bool:
        """Compute embeddings for frames using concurrent processing and store in Qdrant."""
        frames_dir = NamingConvention.frames_dir_local(self.video_name)
        frame_files = sorted(frames_dir.glob("frame_*.jpg"))

        # Get video FPS to calculate timestamps
        video_path = NamingConvention.video_local_path(self.video_name)
        import cv2

        cap = cv2.VideoCapture(str(video_path))
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 1.0  # Default to 1 if unable to read
        cap.release()

        # Get target FPS from config to calculate actual frame timestamps
        target_fps = self._get_config("fps", 1)
        frame_interval = max(1, int(video_fps / target_fps))

        # Check what's already in Qdrant
        try:
            qdrant = QdrantStorage()
            # Query Qdrant to see what frames we already have for this video
            existing_frames = set()
            # Note: This is a simple check - in production you might want to query Qdrant directly
        except Exception as e:
            print(f"    Warning: Could not connect to Qdrant: {e}")
            existing_frames = set()

        embeddings = {}
        paths = {}
        timestamps = {}

        # Process all frames (Qdrant will handle duplicates via upsert)
        frames_to_process = [(i, f) for i, f in enumerate(frame_files)]

        if not frames_to_process:
            print(f"    No frames to process")
            return True

        print(
            f"    Processing {len(frames_to_process)} frames with {self.MAX_WORKERS} concurrent workers..."
        )

        new_count = 0
        errors = 0

        def process_frame(idx_and_path):
            """Process a single frame with retry logic (runs in thread pool)."""
            i, frame_path = idx_and_path
            frame_key = f"{self.video_name}/{frame_path.name}"

            for retry_count, delay in enumerate([0] + self.RETRY_DELAYS):
                if delay > 0:
                    time.sleep(delay)

                try:
                    with open(frame_path, "rb") as f:
                        output = client.run(
                            "andreasjansson/clip-features:75b33f253f7714a281ad3e9b28f63e3232d583716ef6718f2e46641077ea040a",
                            input={"inputs": f},
                        )

                    if output and len(output) > 0:
                        embedding_data = (
                            output[0].get("embedding")
                            if isinstance(output[0], dict)
                            else output[0]
                        )
                        embedding = np.array(embedding_data, dtype=np.float32).copy()

                        s3_key = NamingConvention.frame_s3_key(
                            self.video_name,
                            NamingConvention.parse_frame_index(frame_path.name),
                        )

                        # Calculate timestamp for this frame
                        frame_index = NamingConvention.parse_frame_index(
                            frame_path.name
                        )
                        timestamp_seconds = (
                            (frame_index * frame_interval) / video_fps
                            if frame_index is not None
                            else 0.0
                        )

                        return (frame_key, embedding, s3_key, timestamp_seconds, None)
                    else:
                        return (frame_key, None, None, 0.0, "Empty response from API")

                except Exception as e:
                    error_str = str(e)
                    # Check if it's a rate limit error (429)
                    if "429" in error_str or "throttled" in error_str.lower():
                        if retry_count < len(self.RETRY_DELAYS):
                            continue  # Retry with next delay
                    # For other errors or exhausted retries, return error
                    return (frame_key, None, None, 0.0, error_str)

            return (frame_key, None, None, 0.0, "Max retries exceeded")

        # Process frames concurrently with progress bar
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {
                executor.submit(process_frame, item): item for item in frames_to_process
            }

            with tqdm(
                total=len(frames_to_process),
                desc="    Frame embeddings",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            ) as pbar:
                for future in as_completed(futures):
                    frame_key, embedding, s3_key, timestamp, error = future.result()

                    if error:
                        errors += 1
                        if errors <= 5:  # Only print first 5 errors
                            tqdm.write(f"    Error processing {frame_key}: {error}")
                    else:
                        embeddings[frame_key] = embedding
                        paths[frame_key] = s3_key
                        timestamps[frame_key] = timestamp
                        new_count += 1

                    pbar.set_postfix(success=new_count, errors=errors, refresh=False)
                    pbar.update(1)

                    # Save progress to Qdrant every 50 frames
                    total_processed = new_count + errors
                    if total_processed % 50 == 0 and len(embeddings) > 0:
                        try:
                            qdrant = QdrantStorage()
                            qdrant.store_frame_embeddings(embeddings, paths, timestamps)
                        except Exception as e:
                            print(f"    Warning: Failed to update Qdrant: {e}")

        # Save final embeddings to Qdrant
        print("    Storing frame embeddings in Qdrant...")
        try:
            qdrant = QdrantStorage()
            qdrant.store_frame_embeddings(embeddings, paths, timestamps)
            print(f"    ✅ Stored {new_count} frame embeddings to Qdrant")
        except Exception as e:
            print(f"    ❌ Failed to save embeddings to Qdrant: {e}")
            return False

        print(
            f"    Computed {new_count} new frame embeddings (total: {len(embeddings)}, {errors} errors)"
        )
        return errors < len(frames_to_process) * 0.5  # Fail if >50% errors

    def _compute_object_embeddings(self, client) -> bool:
        """Compute embeddings for objects using concurrent processing and store in Qdrant."""
        objects_dir = NamingConvention.objects_dir_local(self.video_name)
        object_files = sorted(objects_dir.glob("frame_*_obj_*.jpg"))

        # Check what's already in Qdrant
        try:
            qdrant = QdrantStorage()
            existing_objects = set()
        except Exception as e:
            print(f"    Warning: Could not connect to Qdrant: {e}")
            existing_objects = set()

        embeddings = {}
        paths = {}

        # Process all objects (Qdrant will handle duplicates via upsert)
        objects_to_process = [(i, f) for i, f in enumerate(object_files)]

        if not objects_to_process:
            print(f"    No objects to process")
            return True

        print(
            f"    Processing {len(objects_to_process)} objects with {self.MAX_WORKERS} concurrent workers..."
        )

        new_count = 0
        errors = 0

        def process_object(idx_and_path):
            """Process a single object with retry logic (runs in thread pool)."""
            i, obj_path = idx_and_path
            obj_key = f"{self.video_name}/{obj_path.name}"

            for retry_count, delay in enumerate([0] + self.RETRY_DELAYS):
                if delay > 0:
                    time.sleep(delay)

                try:
                    with open(obj_path, "rb") as f:
                        output = client.run(
                            "andreasjansson/clip-features:75b33f253f7714a281ad3e9b28f63e3232d583716ef6718f2e46641077ea040a",
                            input={"inputs": f},
                        )

                    if output and len(output) > 0:
                        embedding_data = (
                            output[0].get("embedding")
                            if isinstance(output[0], dict)
                            else output[0]
                        )
                        embedding = np.array(embedding_data, dtype=np.float32).copy()

                        indices = NamingConvention.parse_object_indices(obj_path.name)
                        s3_key = None
                        if indices:
                            frame_idx, obj_idx = indices
                            s3_key = NamingConvention.object_s3_key(
                                self.video_name, frame_idx, obj_idx
                            )

                        return (obj_key, embedding, s3_key, None)
                    else:
                        return (obj_key, None, None, "Empty response from API")

                except Exception as e:
                    error_str = str(e)
                    # Check if it's a rate limit error (429)
                    if "429" in error_str or "throttled" in error_str.lower():
                        if retry_count < len(self.RETRY_DELAYS):
                            continue  # Retry with next delay
                    # For other errors or exhausted retries, return error
                    return (obj_key, None, None, error_str)

            return (obj_key, None, None, "Max retries exceeded")

        # Process objects concurrently with progress bar
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {
                executor.submit(process_object, item): item
                for item in objects_to_process
            }

            with tqdm(
                total=len(objects_to_process),
                desc="    Object embeddings",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            ) as pbar:
                for future in as_completed(futures):
                    obj_key, embedding, s3_key, error = future.result()

                    if error:
                        errors += 1
                        if errors <= 5:  # Only print first 5 errors
                            tqdm.write(f"    Error processing {obj_key}: {error}")
                    else:
                        embeddings[obj_key] = embedding
                        if s3_key:
                            paths[obj_key] = s3_key
                        new_count += 1

                    pbar.set_postfix(success=new_count, errors=errors, refresh=False)
                    pbar.update(1)

                    # Save progress to Qdrant every 100 objects
                    total_processed = new_count + errors
                    if total_processed % 100 == 0 and len(embeddings) > 0:
                        try:
                            qdrant = QdrantStorage()
                            qdrant.store_object_embeddings(embeddings, paths)
                        except Exception as e:
                            print(f"    Warning: Failed to update Qdrant: {e}")

        # Save final embeddings to Qdrant
        print("    Storing object embeddings in Qdrant...")
        try:
            qdrant = QdrantStorage()
            count = qdrant.store_object_embeddings(embeddings, paths)
            print(f"    ✅ Stored {new_count} object embeddings to Qdrant")
        except Exception as e:
            print(f"    ❌ Failed to save embeddings to Qdrant: {e}")
            return False

        print(
            f"    Computed {new_count} new object embeddings (total: {len(embeddings)}, {errors} errors)"
        )
        return errors < len(objects_to_process) * 0.5  # Fail if >50% errors

    def validate_output(self) -> tuple[bool, Optional[str]]:
        """Validate that embeddings were computed and stored in Qdrant."""
        try:
            qdrant = QdrantStorage()
            # Check if we have frame embeddings for this video in Qdrant
            frame_count = qdrant.client.count(
                collection_name="frames",
                count_filter={
                    "must": [{"key": "video_name", "match": {"value": self.video_name}}]
                },
            )

            if frame_count.count == 0:
                return (
                    False,
                    f"No frame embeddings found in Qdrant for video: {self.video_name}",
                )

            print(f"    ✅ Validated {frame_count.count} frame embeddings in Qdrant")
            return True, None

        except Exception as e:
            return False, f"Failed to validate embeddings in Qdrant: {e}"
