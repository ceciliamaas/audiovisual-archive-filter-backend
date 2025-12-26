"""
Pipeline steps for video processing.

Each step is a self-contained module that performs one part of the pipeline:
- download: Get video from YouTube/Drive/local
- extract_frames: Extract frames from video
- detect_objects: Detect objects with YOLO
- compute_embeddings: Compute CLIP embeddings
- upload: Upload to S3
"""

from .base import PipelineStep
from .download import DownloadStep
from .extract_frames import ExtractFramesStep
from .detect_objects import DetectObjectsStep
from .compute_embeddings import ComputeEmbeddingsStep
from .upload import UploadStep

__all__ = [
    "PipelineStep",
    "DownloadStep",
    "ExtractFramesStep",
    "DetectObjectsStep",
    "ComputeEmbeddingsStep",
    "UploadStep",
]
