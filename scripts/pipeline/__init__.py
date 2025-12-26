"""
Pipeline module for standardized video processing workflow.

This module provides:
- State management for tracking video processing status
- Naming conventions for consistent file/path handling
- Pipeline steps for download, extraction, detection, embeddings
"""

from .state import PipelineState, VideoStatus
from .naming import NamingConvention

__all__ = ["PipelineState", "VideoStatus", "NamingConvention"]
