"""
Compute embeddings step for the pipeline.

Computes CLIP embeddings for frames and objects using Replicate API.
Supports concurrent processing for faster execution.
"""

import os
import pickle
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from .base import PipelineStep
from ..state import VideoStatus
from ..naming import NamingConvention

load_dotenv()


class ComputeEmbeddingsStep(PipelineStep):
    """Compute CLIP embeddings for frames and objects with concurrent processing."""

    # Number of concurrent API requests (adjust based on API rate limits)
    MAX_WORKERS = 10  # Process 10 images in parallel

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
        """Compute embeddings for frames using concurrent processing."""
        frames_dir = NamingConvention.frames_dir_local(self.video_name)
        frame_files = sorted(frames_dir.glob("frame_*.jpg"))

        # Load existing embeddings
        frame_emb_path = NamingConvention.frame_embeddings_local()
        frame_paths_path = NamingConvention.frame_paths_local()

        if frame_emb_path.exists() and frame_paths_path.exists():
            with open(frame_emb_path, "rb") as f:
                embeddings = pickle.load(f)
            with open(frame_paths_path, "rb") as f:
                paths = pickle.load(f)
        else:
            embeddings = {}
            paths = []

        # Filter out already processed frames
        frames_to_process = [
            (i, f) for i, f in enumerate(frame_files)
            if f"{self.video_name}/{f.name}" not in embeddings
        ]
        
        if not frames_to_process:
            print(f"    All {len(frame_files)} frames already have embeddings")
            return True

        print(f"    Processing {len(frames_to_process)} frames with {self.MAX_WORKERS} concurrent workers...")
        
        new_count = 0
        errors = 0
        
        def process_frame(idx_and_path):
            """Process a single frame (runs in thread pool)."""
            i, frame_path = idx_and_path
            frame_key = f"{self.video_name}/{frame_path.name}"
            
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
                    
                    return (frame_key, embedding, s3_key, None)
                else:
                    return (frame_key, None, None, "Empty response from API")
                    
            except Exception as e:
                return (frame_key, None, None, str(e))
        
        # Process frames concurrently
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {executor.submit(process_frame, item): item for item in frames_to_process}
            
            for future in as_completed(futures):
                frame_key, embedding, s3_key, error = future.result()
                
                if error:
                    errors += 1
                    if errors <= 5:  # Only print first 5 errors
                        print(f"    Error processing {frame_key}: {error}")
                else:
                    embeddings[frame_key] = embedding
                    if s3_key not in paths:
                        paths.append(s3_key)
                    new_count += 1
                
                # Progress update
                total_processed = new_count + errors
                print(f"    Progress: {total_processed}/{len(frames_to_process)} ({new_count} success, {errors} errors)", end="\r")
                
                # Save progress every 50 frames
                if total_processed % 50 == 0:
                    frame_emb_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(frame_emb_path, "wb") as f:
                        pickle.dump(embeddings, f)
                    with open(frame_paths_path, "wb") as f:
                        pickle.dump(paths, f)

        print()  # New line after progress
        
        # Save final embeddings
        frame_emb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(frame_emb_path, "wb") as f:
            pickle.dump(embeddings, f)
        with open(frame_paths_path, "wb") as f:
            pickle.dump(paths, f)

        print(
            f"    Computed {new_count} new frame embeddings (total: {len(embeddings)}, {errors} errors)"
        )
        return errors < len(frames_to_process) * 0.5  # Fail if >50% errors

    def _compute_object_embeddings(self, client) -> bool:
        """Compute embeddings for objects using concurrent processing."""
        objects_dir = NamingConvention.objects_dir_local(self.video_name)
        object_files = sorted(objects_dir.glob("frame_*_obj_*.jpg"))

        # Load existing embeddings
        obj_emb_path = NamingConvention.object_embeddings_local()
        obj_paths_path = NamingConvention.object_paths_local()

        if obj_emb_path.exists() and obj_paths_path.exists():
            with open(obj_emb_path, "rb") as f:
                embeddings = pickle.load(f)
            with open(obj_paths_path, "rb") as f:
                paths = pickle.load(f)
        else:
            embeddings = {}
            paths = []

        # Filter out already processed objects
        objects_to_process = [
            (i, f) for i, f in enumerate(object_files)
            if f"{self.video_name}/{f.name}" not in embeddings
        ]
        
        if not objects_to_process:
            print(f"    All {len(object_files)} objects already have embeddings")
            return True

        print(f"    Processing {len(objects_to_process)} objects with {self.MAX_WORKERS} concurrent workers...")
        
        new_count = 0
        errors = 0
        
        def process_object(idx_and_path):
            """Process a single object (runs in thread pool)."""
            i, obj_path = idx_and_path
            obj_key = f"{self.video_name}/{obj_path.name}"
            
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
                return (obj_key, None, None, str(e))
        
        # Process objects concurrently
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {executor.submit(process_object, item): item for item in objects_to_process}
            
            for future in as_completed(futures):
                obj_key, embedding, s3_key, error = future.result()
                
                if error:
                    errors += 1
                    if errors <= 5:  # Only print first 5 errors
                        print(f"    Error processing {obj_key}: {error}")
                else:
                    embeddings[obj_key] = embedding
                    if s3_key and s3_key not in paths:
                        paths.append(s3_key)
                    new_count += 1
                
                # Progress update
                total_processed = new_count + errors
                print(f"    Progress: {total_processed}/{len(objects_to_process)} ({new_count} success, {errors} errors)", end="\r")
                
                # Save progress every 100 objects
                if total_processed % 100 == 0:
                    obj_emb_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(obj_emb_path, "wb") as f:
                        pickle.dump(embeddings, f)
                    with open(obj_paths_path, "wb") as f:
                        pickle.dump(paths, f)

        print()  # New line after progress
        
        # Save final embeddings
        obj_emb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(obj_emb_path, "wb") as f:
            pickle.dump(embeddings, f)
        with open(obj_paths_path, "wb") as f:
            pickle.dump(paths, f)

        print(
            f"    Computed {new_count} new object embeddings (total: {len(embeddings)}, {errors} errors)"
        )
        return errors < len(objects_to_process) * 0.5  # Fail if >50% errors

    def validate_output(self) -> tuple[bool, Optional[str]]:
        """Validate that embeddings were computed."""
        frame_emb_path = NamingConvention.frame_embeddings_local()

        if not frame_emb_path.exists():
            return False, f"Frame embeddings file not created: {frame_emb_path}"

        # Verify we have embeddings for this video
        with open(frame_emb_path, "rb") as f:
            embeddings = pickle.load(f)

        # Check if any embeddings exist for this video
        video_embeddings = {
            k: v for k, v in embeddings.items() if k.startswith(f"{self.video_name}/")
        }
        if len(video_embeddings) == 0:
            return False, f"No embeddings computed for video {self.video_name}"

        return True, None
