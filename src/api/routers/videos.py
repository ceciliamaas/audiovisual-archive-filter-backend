"""
Video management endpoints for the API.
Handles video upload, processing status, and video streaming.
"""

import logging
import tempfile
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from ..models import (
    VideoUploadResponse,
    VideoListResponse,
    VideoNamesResponse,
    VideoItem,
    VideoProcessingStatus,
    VideoProcessRequest,
    ErrorResponse,
)
from ...config.settings import app_config
from ...storage import get_storage_manager
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.naming import NamingConvention
from scripts.pipeline.state import PipelineState, VideoStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Track video processing status in memory (in production, use a database)
_processing_status: dict = {}


def _is_state_stale(state: PipelineState, max_hours: int = 2) -> bool:
    """Check if a processing state is stale (stuck for too long).
    
    Args:
        state: Pipeline state to check
        max_hours: Maximum hours before considering state stale
    
    Returns:
        True if state is in processing status but hasn't been updated recently
    """
    if not state.status.is_processing():
        return False
    
    try:
        updated_at = datetime.fromisoformat(state.updated_at)
        time_since_update = datetime.now() - updated_at
        return time_since_update > timedelta(hours=max_hours)
    except (ValueError, TypeError):
        # If we can't parse the timestamp, consider it stale to be safe
        return True


def _get_video_status(video_name: str) -> Optional[dict]:
    """Get video processing status"""
    state_path = Path("data/pipeline_state") / f"{video_name}.json"
    if state_path.exists():
        try:
            state = PipelineState.load(video_name)
            return {
                "video_name": state.video_name,
                "status": state.status.value,
                "progress": _calculate_progress(state),
                "frame_count": state.frame_count,
                "object_count": state.object_count,
                "created_at": state.created_at,
                "updated_at": state.updated_at,
                "completed_at": state.completed_at,
                "error_message": state.error_message,
                "steps_completed": state.steps_completed,
                "is_stale": _is_state_stale(state),
            }
        except Exception as e:
            logger.error(f"Error loading state for {video_name}: {e}")
    return None


def _calculate_progress(state: PipelineState) -> float:
    """Calculate progress percentage based on completed steps"""
    total_steps = (
        5  # download, extract_frames, detect_objects, compute_embeddings, upload
    )
    completed = len(state.steps_completed)
    return (completed / total_steps) * 100


async def _process_video_background(
    video_name: str,
    source_type: str,
    source_url: str,
    fps: int = 1,
    force: bool = False,
):
    """Process video in background"""
    try:
        logger.info(f"Starting background processing for {video_name}")

        # Create pipeline with config
        pipeline = Pipeline(
            config={
                "fps": fps,
            }
        )

        # Process video
        success = pipeline.process_video(
            video_name=video_name,
            source_type=source_type,
            source_url=source_url,
            steps=None,  # Run all steps
            force=force,
        )

        if success:
            logger.info(f"Successfully processed video: {video_name}")
        else:
            logger.error(f"Failed to process video: {video_name}")

    except Exception as e:
        logger.error(f"Error processing video {video_name}: {e}", exc_info=True)
        # Update state with error
        try:
            state = PipelineState.load(video_name)
            state.status = VideoStatus.FAILED
            state.error_message = str(e)
            state.save()
        except:
            pass


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file to upload"),
):
    """
    Upload a new video for processing.

    The video will be saved and automatically processed through the pipeline:
    1. Extract frames at 1 FPS
    2. Detect objects using YOLO
    3. Compute CLIP embeddings
    4. Upload to storage

    Args:
        file: Video file (mp4, avi, mov, etc.)

    Returns:
        VideoUploadResponse with processing status

    Raises:
        HTTPException: If upload or processing fails
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("video/"):
            # Also accept common video file extensions
            valid_extensions = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
            if not any(file.filename.lower().endswith(ext) for ext in valid_extensions):
                raise HTTPException(
                    status_code=400,
                    detail="File must be a video (mp4, avi, mov, mkv, etc.)",
                )

        logger.info(f"Video upload request: {file.filename}")

        # Sanitize filename to create video_name
        from scripts.pipeline.naming import NamingConvention

        file_stem = Path(file.filename).stem
        video_name = NamingConvention.sanitize_video_name(file_stem)

        # Check if video already exists and is being processed
        existing_status = _get_video_status(video_name)
        if existing_status and existing_status["status"] not in ["completed", "failed"]:
            return VideoUploadResponse(
                video_name=video_name,
                status=existing_status["status"],
                message=f"Video '{video_name}' is already being processed",
            )

        # Save video to local storage
        video_path = NamingConvention.video_local_path(video_name)
        video_path.parent.mkdir(parents=True, exist_ok=True)

        # Write uploaded file
        content = await file.read()
        with open(video_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved video to {video_path} ({len(content)} bytes)")

        # Create initial pipeline state
        state = PipelineState(
            video_name=video_name,
            status=VideoStatus.PENDING,
            source_type="upload",
            source_url=str(video_path),
        )
        state.save()

        # Start background processing with source info
        background_tasks.add_task(
            _process_video_background, video_name, "upload", str(video_path)
        )

        return VideoUploadResponse(
            video_name=video_name,
            status="pending",
            message=f"Video '{video_name}' uploaded successfully. Processing started.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Video upload failed: {str(e)}")


@router.post("/process", response_model=VideoUploadResponse)
async def process_video_from_url(
    background_tasks: BackgroundTasks,
    request: VideoProcessRequest,
):
    """
    Process a video from a URL (YouTube, Google Drive) or local path.

    The video will be downloaded (if URL) and processed through the pipeline:
    1. Download video (if YouTube/Drive URL)
    2. Extract frames at specified FPS
    3. Detect objects using YOLO
    4. Compute CLIP embeddings with timestamps
    5. Upload to cloud storage

    Args:
        request: VideoProcessRequest with source details

    Returns:
        VideoUploadResponse with processing status

    Raises:
        HTTPException: If processing cannot be started

    Examples:
        YouTube: {"video_name": "demo", "source_type": "youtube", "source_url": "https://youtube.com/watch?v=xxx", "fps": 1}
        Drive: {"video_name": "demo", "source_type": "drive", "source_url": "https://drive.google.com/file/d/xxx", "fps": 1}
    """
    try:
        logger.info(
            f"Video process request: {request.video_name} from {request.source_type}"
        )

        # Sanitize video name
        from scripts.pipeline.naming import NamingConvention

        video_name = NamingConvention.sanitize_video_name(request.video_name)

        # Check if video already exists and is being processed
        existing_status = _get_video_status(video_name)
        if existing_status and existing_status["status"] not in ["completed", "failed"]:
            # Check if state is stale (stuck for too long)
            if existing_status.get("is_stale", False):
                logger.warning(f"Video {video_name} has stale state ({existing_status['status']}), allowing reprocessing")
            elif not request.force:
                return VideoUploadResponse(
                    video_name=video_name,
                    status=existing_status["status"],
                    message=f"Video '{video_name}' is already being processed. Use force=true to reprocess.",
                )

        # Validate source type
        if request.source_type not in ["youtube", "drive", "local"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source_type: {request.source_type}. Must be 'youtube', 'drive', or 'local'.",
            )

        # For local files, validate that path exists
        if request.source_type == "local":
            local_path = Path(request.source_url)
            if not local_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Local file not found: {request.source_url}",
                )

        # Don't create state here - let the Pipeline handle it to avoid race conditions
        # The Pipeline.process_video will load existing state or create new one as needed
        
        # Start background processing
        background_tasks.add_task(
            _process_video_background,
            video_name,
            request.source_type,
            request.source_url,
            request.fps,
            request.force,
        )

        return VideoUploadResponse(
            video_name=video_name,
            status="pending",
            message=f"Video '{video_name}' processing started from {request.source_type}.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video process error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to start video processing: {str(e)}"
        )


@router.get("/status/{video_name}", response_model=VideoProcessingStatus)
async def get_video_status(video_name: str):
    """
    Get processing status for a specific video.

    Args:
        video_name: Name of the video

    Returns:
        VideoProcessingStatus with current processing state

    Raises:
        HTTPException: If video not found
    """
    try:
        status = _get_video_status(video_name)

        if not status:
            raise HTTPException(
                status_code=404, detail=f"Video '{video_name}' not found"
            )

        return VideoProcessingStatus(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get video status: {str(e)}"
        )


@router.get("/list", response_model=VideoListResponse)
async def list_videos(
    status: Optional[str] = Query(
        None, description="Filter by status (pending, processing, completed, failed)"
    ),
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of videos to return"
    ),
):
    """
    List all videos and their processing status.

    Args:
        status: Optional status filter
        limit: Maximum number of results

    Returns:
        VideoListResponse with list of videos
    """
    try:
        state_dir = Path("data/pipeline_state")
        if not state_dir.exists():
            return VideoListResponse(videos=[], total=0)

        videos = []
        for state_file in state_dir.glob("*.json"):
            try:
                video_name = state_file.stem
                video_status = _get_video_status(video_name)

                if video_status:
                    # Apply status filter
                    if status and video_status["status"] != status:
                        continue

                    videos.append(VideoItem(**video_status))

            except Exception as e:
                logger.warning(f"Error loading {state_file}: {e}")
                continue

        # Sort by updated_at descending (most recent first)
        videos.sort(key=lambda v: v.updated_at or "", reverse=True)

        # Apply limit
        videos = videos[:limit]

        return VideoListResponse(
            videos=videos,
            total=len(videos),
        )

    except Exception as e:
        logger.error(f"Error listing videos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")


@router.get("/names", response_model=VideoNamesResponse)
async def get_video_names(
    status: Optional[str] = Query(
        None, description="Filter by status (pending, processing, completed, failed)"
    ),
):
    """
    Get list of video names only (lightweight endpoint for filters).

    Args:
        status: Optional status filter

    Returns:
        VideoNamesResponse with list of video names
    """
    try:
        state_dir = Path("data/pipeline_state")
        if not state_dir.exists():
            return VideoNamesResponse(video_names=[], total=0)

        video_names = []
        for state_file in state_dir.glob("*.json"):
            try:
                # Only read the status field, not the entire state
                import json

                with open(state_file, "r") as f:
                    data = json.load(f)
                    video_status = data.get("status")

                    # Apply status filter
                    if status and video_status != status:
                        continue

                    video_names.append(state_file.stem)

            except Exception as e:
                logger.warning(f"Error reading {state_file}: {e}")
                continue

        # Sort alphabetically
        video_names.sort()

        return VideoNamesResponse(
            video_names=video_names,
            total=len(video_names),
        )

    except Exception as e:
        logger.error(f"Error getting video names: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get video names: {str(e)}"
        )


@router.get("/stream/{video_name}")
async def stream_video(video_name: str):
    """
    Stream a video file.

    Args:
        video_name: Name of the video

    Returns:
        StreamingResponse with video content

    Raises:
        HTTPException: If video not found
    """
    try:
        storage_manager = get_storage_manager()

        # Try to get from storage
        video_s3_key = NamingConvention.video_s3_key(video_name)

        try:
            # Check if video exists in storage
            url = storage_manager.get_presigned_url(video_s3_key, expiration=3600)

            # For now, redirect to presigned URL
            # In production, you might want to implement proper streaming
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url=url)

        except:
            # Fallback to local file
            video_path = NamingConvention.video_local_path(video_name)

            if not video_path.exists():
                raise HTTPException(
                    status_code=404, detail=f"Video '{video_name}' not found"
                )

            # Stream from local file
            return FileResponse(
                path=video_path,
                media_type="video/mp4",
                filename=f"{video_name}.mp4",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stream video: {str(e)}")


@router.delete("/{video_name}")
async def delete_video(video_name: str):
    """
    Delete a video and all its associated data.

    Args:
        video_name: Name of the video to delete

    Returns:
        Success message

    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Delete state file
        state_path = Path("data/pipeline_state") / f"{video_name}.json"
        if state_path.exists():
            state_path.unlink()
            logger.info(f"Deleted state file: {state_path}")

        # Delete local files
        video_path = NamingConvention.video_local_path(video_name)
        if video_path.exists():
            video_path.unlink()

        frames_dir = NamingConvention.frames_dir_local(video_name)
        if frames_dir.exists():
            import shutil

            shutil.rmtree(frames_dir)

        objects_dir = NamingConvention.objects_dir_local(video_name)
        if objects_dir.exists():
            import shutil

            shutil.rmtree(objects_dir)

        # TODO: Delete from Qdrant collections
        # TODO: Delete from S3/storage

        logger.info(f"Deleted video: {video_name}")

        return {
            "message": f"Video '{video_name}' deleted successfully",
            "video_name": video_name,
        }

    except Exception as e:
        logger.error(f"Error deleting video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")
