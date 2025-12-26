"""
Pipeline state management for tracking video processing status.

This module provides:
- State tracking for each video through the pipeline
- Persistence to JSON files
- Status queries and updates
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List


class VideoStatus(str, Enum):
    """Status of a video in the processing pipeline."""
    
    PENDING = "pending"               # Not started
    DOWNLOADING = "downloading"       # Downloading from source
    DOWNLOADED = "downloaded"         # Video file saved locally
    EXTRACTING_FRAMES = "extracting_frames"  # Extracting frames
    FRAMES_EXTRACTED = "frames_extracted"    # Frames extracted
    DETECTING_OBJECTS = "detecting_objects"  # YOLO detection
    OBJECTS_DETECTED = "objects_detected"    # Objects detected
    COMPUTING_EMBEDDINGS = "computing_embeddings"  # CLIP embeddings
    EMBEDDINGS_COMPUTED = "embeddings_computed"    # Embeddings computed
    UPLOADING = "uploading"           # Uploading to S3
    COMPLETED = "completed"           # All steps complete
    FAILED = "failed"                 # Processing failed
    
    def is_terminal(self) -> bool:
        """Check if this is a terminal status (no more processing)."""
        return self in {VideoStatus.COMPLETED, VideoStatus.FAILED}
    
    def is_processing(self) -> bool:
        """Check if this status indicates active processing."""
        return self in {
            VideoStatus.DOWNLOADING,
            VideoStatus.EXTRACTING_FRAMES,
            VideoStatus.DETECTING_OBJECTS,
            VideoStatus.COMPUTING_EMBEDDINGS,
            VideoStatus.UPLOADING
        }


class PipelineState:
    """Track processing state for a single video."""
    
    def __init__(
        self,
        video_name: str,
        status: VideoStatus = VideoStatus.PENDING,
        source_type: Optional[str] = None,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize pipeline state for a video.
        
        Args:
            video_name: Name of the video
            status: Current processing status
            source_type: Type of source (youtube, drive, local)
            source_url: URL or path to source
            metadata: Additional metadata
        """
        self.video_name = video_name
        self.status = status
        self.source_type = source_type
        self.source_url = source_url
        self.metadata = metadata or {}
        
        # Timestamps
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.completed_at: Optional[str] = None
        
        # Processing metrics
        self.frame_count: Optional[int] = None
        self.object_count: Optional[int] = None
        self.error_message: Optional[str] = None
        
        # Step completion tracking
        self.steps_completed: List[str] = []
    
    def update_status(self, status: VideoStatus, error_message: Optional[str] = None):
        """Update the status of the video.
        
        Args:
            status: New status
            error_message: Error message if status is FAILED
        """
        self.status = status
        self.updated_at = datetime.now().isoformat()
        self.error_message = error_message
        
        if status == VideoStatus.COMPLETED:
            self.completed_at = self.updated_at
    
    def mark_step_completed(self, step_name: str):
        """Mark a processing step as completed.
        
        Args:
            step_name: Name of the step (e.g., "download", "extract_frames")
        """
        if step_name not in self.steps_completed:
            self.steps_completed.append(step_name)
        self.updated_at = datetime.now().isoformat()
    
    def is_step_completed(self, step_name: str) -> bool:
        """Check if a step has been completed.
        
        Args:
            step_name: Name of the step
            
        Returns:
            True if step is completed
        """
        return step_name in self.steps_completed
    
    def set_metadata(self, key: str, value: Any):
        """Set a metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.updated_at = datetime.now().isoformat()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "video_name": self.video_name,
            "status": self.status.value,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "frame_count": self.frame_count,
            "object_count": self.object_count,
            "error_message": self.error_message,
            "steps_completed": self.steps_completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineState":
        """Create state from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            PipelineState instance
        """
        state = cls(
            video_name=data["video_name"],
            status=VideoStatus(data["status"]),
            source_type=data.get("source_type"),
            source_url=data.get("source_url"),
            metadata=data.get("metadata", {})
        )
        state.created_at = data["created_at"]
        state.updated_at = data["updated_at"]
        state.completed_at = data.get("completed_at")
        state.frame_count = data.get("frame_count")
        state.object_count = data.get("object_count")
        state.error_message = data.get("error_message")
        state.steps_completed = data.get("steps_completed", [])
        return state
    
    def save(self, state_dir: str = "data/pipeline_state"):
        """Save state to JSON file.
        
        Args:
            state_dir: Directory to save state files
        """
        state_path = Path(state_dir)
        state_path.mkdir(parents=True, exist_ok=True)
        
        state_file = state_path / f"{self.video_name}.json"
        with open(state_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, video_name: str, state_dir: str = "data/pipeline_state") -> Optional["PipelineState"]:
        """Load state from JSON file.
        
        Args:
            video_name: Name of the video
            state_dir: Directory containing state files
            
        Returns:
            PipelineState instance or None if not found
        """
        state_file = Path(state_dir) / f"{video_name}.json"
        if not state_file.exists():
            return None
        
        with open(state_file, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def list_all(cls, state_dir: str = "data/pipeline_state") -> List["PipelineState"]:
        """List all saved video states.
        
        Args:
            state_dir: Directory containing state files
            
        Returns:
            List of PipelineState instances
        """
        state_path = Path(state_dir)
        if not state_path.exists():
            return []
        
        states = []
        for state_file in state_path.glob("*.json"):
            with open(state_file, "r") as f:
                data = json.load(f)
            states.append(cls.from_dict(data))
        return states
    
    @classmethod
    def list_by_status(cls, status: VideoStatus, state_dir: str = "data/pipeline_state") -> List["PipelineState"]:
        """List all videos with a specific status.
        
        Args:
            status: Status to filter by
            state_dir: Directory containing state files
            
        Returns:
            List of PipelineState instances with matching status
        """
        all_states = cls.list_all(state_dir)
        return [s for s in all_states if s.status == status]
    
    @classmethod
    def delete(cls, video_name: str, state_dir: str = "data/pipeline_state") -> bool:
        """Delete state file for a video.
        
        Args:
            video_name: Name of the video
            state_dir: Directory containing state files
            
        Returns:
            True if deleted, False if not found
        """
        state_file = Path(state_dir) / f"{video_name}.json"
        if state_file.exists():
            state_file.unlink()
            return True
        return False
    
    def __repr__(self) -> str:
        """String representation of state."""
        return (
            f"PipelineState(video_name='{self.video_name}', "
            f"status={self.status.value}, "
            f"frames={self.frame_count}, "
            f"objects={self.object_count})"
        )
