"""
Pydantic models for API requests and responses.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# Request models
class TextSearchRequest(BaseModel):
    """Request model for text-based search"""

    query: str = Field(..., description="Text query for semantic search")
    search_frames: bool = Field(True, description="Search in video frames")
    search_objects: bool = Field(True, description="Search in detected objects")
    max_results: int = Field(50, ge=1, le=200, description="Maximum number of results")
    similarity_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Minimum similarity score (0-1)"
    )
    video_names: Optional[List[str]] = Field(
        None, description="Filter results to specific videos (empty = search all)"
    )


class ImageSearchRequest(BaseModel):
    """Request model for image-based search"""

    search_frames: bool = Field(True, description="Search in video frames")
    search_objects: bool = Field(True, description="Search in detected objects")
    max_results: int = Field(50, ge=1, le=200, description="Maximum number of results")
    similarity_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Minimum similarity score (0-1)"
    )
    video_names: Optional[List[str]] = Field(
        None, description="Filter results to specific videos (empty = search all)"
    )


# Response models
class SearchResultItem(BaseModel):
    """Single search result item"""

    path: str = Field(..., description="Path to the image/frame")
    similarity: float = Field(..., description="Similarity score (0-1)")
    result_type: Literal["frame", "object"] = Field(
        ..., description="Type of result: frame or object"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata about the result"
    )
    url: Optional[str] = Field(
        None, description="Presigned URL for accessing the image (if available)"
    )
    frame_url: Optional[str] = Field(
        None,
        description="For objects: presigned URL for the full frame to display with bbox",
    )


class SearchResponse(BaseModel):
    """Response model for search results"""

    query: str = Field(..., description="Original query")
    query_type: Literal["text", "image"] = Field(
        ..., description="Type of search performed"
    )
    results: List[SearchResultItem] = Field(..., description="List of search results")
    total_results: int = Field(..., description="Total number of results returned")
    search_frames: bool = Field(..., description="Whether frames were searched")
    search_objects: bool = Field(..., description="Whether objects were searched")
    max_results: int = Field(..., description="Maximum results requested")


class StatusResponse(BaseModel):
    """Response model for system status"""

    replicate_available: bool = Field(..., description="Replicate API availability")
    model: str = Field(..., description="CLIP model being used")
    embeddings_status: Dict[str, Any] = Field(
        ..., description="Status of embeddings (loaded, counts, etc.)"
    )


class StorageStatusResponse(BaseModel):
    """Response model for storage status"""

    s3_available: bool = Field(..., description="S3/Storj availability")
    local_available: bool = Field(..., description="Local storage availability")
    recommended_backend: str = Field(..., description="Recommended storage backend")
    current_mode: Optional[str] = Field(None, description="Current storage mode")
    fallback_enabled: bool = Field(..., description="Whether fallback is enabled")
    issues: List[str] = Field(default_factory=list, description="Storage issues")


class EmbeddingsStatusResponse(BaseModel):
    """Response model for embeddings status"""

    loaded: bool = Field(..., description="Whether embeddings are loaded")
    frame_count: int = Field(..., description="Number of frame embeddings")
    object_count: int = Field(..., description="Number of object embeddings")
    source: str = Field(..., description="Source of embeddings (e.g., 'qdrant')")


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error type or category")
    detail: str = Field(..., description="Detailed error message")
    status_code: int = Field(..., description="HTTP status code")


# Video upload and processing models
class VideoUploadResponse(BaseModel):
    """Response model for video upload"""

    video_name: str = Field(..., description="Name of the uploaded video")
    status: str = Field(..., description="Initial processing status")
    message: str = Field(..., description="Status message")


class VideoProcessingStatus(BaseModel):
    """Response model for video processing status"""

    video_name: str = Field(..., description="Name of the video")
    status: str = Field(..., description="Current processing status")
    progress: float = Field(..., description="Processing progress percentage (0-100)")
    frame_count: Optional[int] = Field(None, description="Number of frames extracted")
    object_count: Optional[int] = Field(None, description="Number of objects detected")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    steps_completed: List[str] = Field(
        default_factory=list, description="Completed steps"
    )


class VideoItem(BaseModel):
    """Video item in list"""

    video_name: str = Field(..., description="Name of the video")
    status: str = Field(..., description="Current processing status")
    progress: float = Field(..., description="Processing progress percentage (0-100)")
    frame_count: Optional[int] = Field(None, description="Number of frames")
    object_count: Optional[int] = Field(None, description="Number of objects")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    steps_completed: List[str] = Field(
        default_factory=list, description="Completed steps"
    )


class VideoListResponse(BaseModel):
    """Response model for video list"""

    videos: List[VideoItem] = Field(..., description="List of videos")
    total: int = Field(..., description="Total number of videos")


class VideoNamesResponse(BaseModel):
    """Response model for video names only (lightweight)"""

    video_names: List[str] = Field(..., description="List of video names")
    total: int = Field(..., description="Total number of videos")


class VideoProcessRequest(BaseModel):
    """Request model for processing a video from URL or upload"""

    video_name: str = Field(..., description="Name for the video")
    source_type: Literal["youtube", "drive", "local"] = Field(
        ..., description="Type of source: youtube, drive, or local"
    )
    source_url: str = Field(..., description="URL or path to video")
    fps: int = Field(1, ge=1, le=30, description="Frames per second to extract")
    force: bool = Field(
        False, description="Force reprocessing even if already completed"
    )
