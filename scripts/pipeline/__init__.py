"""
Pipeline module for standardized video processing workflow.

This module provides:
- State management for tracking video processing status
- Naming conventions for consistent file/path handling
- Pipeline steps for download, extraction, detection, embeddings
- Orchestrator for running the complete pipeline
- CLI interface for easy usage
"""

from .state import PipelineState, VideoStatus
from .naming import NamingConvention
from .orchestrator import Pipeline

__all__ = ["PipelineState", "VideoStatus", "NamingConvention", "Pipeline"]
