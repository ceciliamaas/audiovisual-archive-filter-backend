"""
Embeddings module for CLIP-based embedding operations.

This module provides centralized embedding computation and management using
the CLIP model via Replicate API.
"""

from .client import get_replicate_client
from .service import EmbeddingService
from .manager import EmbeddingsManager

__all__ = [
    "get_replicate_client",
    "EmbeddingService",
    "EmbeddingsManager",
]
