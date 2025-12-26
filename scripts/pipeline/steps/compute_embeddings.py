"""
Compute embeddings step for the pipeline.

Computes CLIP embeddings for frames and objects using Replicate API.
"""

import os
import pickle
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv

from .base import PipelineStep
from ..state import VideoStatus
from ..naming import NamingConvention

load_dotenv()


class ComputeEmbeddingsStep(PipelineStep):
    """Compute CLIP embeddings for frames and objects."""
    
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
        """Compute embeddings for frames."""
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
        
        new_count = 0
        for i, frame_path in enumerate(frame_files):
            frame_key = f"{self.video_name}/{frame_path.name}"
            
            # Skip if already computed
            if frame_key in embeddings:
                continue
            
            print(f"    Frame {i+1}/{len(frame_files)}...", end="\r")
            
            try:
                with open(frame_path, "rb") as f:
                    output = client.run(
                        "andreasjansson/clip-features:75b33f253f7714a281ad3e9b28f63e3232d583716ef6718f2e46641077ea040a",
                        input={"inputs": f}
                    )
                
                if output and len(output) > 0:
                    embedding = np.array(output[0])
                    embeddings[frame_key] = embedding
                    
                    # Add path if not exists
                    s3_key = NamingConvention.frame_s3_key(self.video_name, NamingConvention.parse_frame_index(frame_path.name))
                    if s3_key not in paths:
                        paths.append(s3_key)
                    
                    new_count += 1
            except Exception as e:
                print(f"    Error computing embedding for {frame_path.name}: {e}")
                continue
        
        # Save updated embeddings
        frame_emb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(frame_emb_path, "wb") as f:
            pickle.dump(embeddings, f)
        with open(frame_paths_path, "wb") as f:
            pickle.dump(paths, f)
        
        print(f"    Computed {new_count} new frame embeddings (total: {len(embeddings)})")
        return True
    
    def _compute_object_embeddings(self, client) -> bool:
        """Compute embeddings for objects."""
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
        
        new_count = 0
        for i, obj_path in enumerate(object_files):
            obj_key = f"{self.video_name}/{obj_path.name}"
            
            # Skip if already computed
            if obj_key in embeddings:
                continue
            
            print(f"    Object {i+1}/{len(object_files)}...", end="\r")
            
            try:
                with open(obj_path, "rb") as f:
                    output = client.run(
                        "andreasjansson/clip-features:75b33f253f7714a281ad3e9b28f63e3232d583716ef6718f2e46641077ea040a",
                        input={"inputs": f}
                    )
                
                if output and len(output) > 0:
                    embedding = np.array(output[0])
                    embeddings[obj_key] = embedding
                    
                    # Add path if not exists
                    indices = NamingConvention.parse_object_indices(obj_path.name)
                    if indices:
                        frame_idx, obj_idx = indices
                        s3_key = NamingConvention.object_s3_key(self.video_name, frame_idx, obj_idx)
                        if s3_key not in paths:
                            paths.append(s3_key)
                    
                    new_count += 1
            except Exception as e:
                print(f"    Error computing embedding for {obj_path.name}: {e}")
                continue
        
        # Save updated embeddings
        obj_emb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(obj_emb_path, "wb") as f:
            pickle.dump(embeddings, f)
        with open(obj_paths_path, "wb") as f:
            pickle.dump(paths, f)
        
        print(f"    Computed {new_count} new object embeddings (total: {len(embeddings)})")
        return True
    
    def validate_output(self) -> tuple[bool, Optional[str]]:
        """Validate that embeddings were computed."""
        frame_emb_path = NamingConvention.frame_embeddings_local()
        
        if not frame_emb_path.exists():
            return False, f"Frame embeddings file not created: {frame_emb_path}"
        
        # Verify we have embeddings for this video
        with open(frame_emb_path, "rb") as f:
            embeddings = pickle.load(f)
        
        # Check if any embeddings exist for this video
        video_embeddings = {k: v for k, v in embeddings.items() if k.startswith(f"{self.video_name}/")}
        if len(video_embeddings) == 0:
            return False, f"No embeddings computed for video {self.video_name}"
        
        return True, None
