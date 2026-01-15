"""
Search endpoints for the API.
Handles text and image-based searches.
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from ..models import (
    TextSearchRequest,
    SearchResponse,
    SearchResultItem,
    ErrorResponse,
)
from ...core.search import get_search_engine, SearchResult
from ...storage import get_storage_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_search_results(
    results: List[SearchResult], query: str, query_type: str, request_params: dict
) -> SearchResponse:
    """
    Convert SearchResult objects to API response format.

    Args:
        results: List of SearchResult objects
        query: Original search query
        query_type: Type of query ('text' or 'image')
        request_params: Original request parameters

    Returns:
        SearchResponse object
    """
    storage_manager = get_storage_manager()

    # Convert results and optionally add presigned URLs
    items = []
    for result in results:
        item_dict = {
            "path": result.path,
            "similarity": result.similarity,
            "result_type": result.result_type,
            "metadata": result.metadata,
        }

        # Try to get presigned URL for the image
        try:
            url = storage_manager.get_presigned_url(result.path)
            item_dict["url"] = url
        except Exception as e:
            logger.debug(f"Could not get presigned URL for {result.path}: {e}")
            item_dict["url"] = None

        # For objects, also get the frame URL to show full frame with bbox
        if result.result_type == "object" and result.metadata.get("frame_path"):
            try:
                frame_url = storage_manager.get_presigned_url(
                    result.metadata["frame_path"]
                )
                item_dict["frame_url"] = frame_url
            except Exception as e:
                logger.debug(f"Could not get presigned URL for frame: {e}")
                item_dict["frame_url"] = None

        items.append(SearchResultItem(**item_dict))

    return SearchResponse(
        query=query,
        query_type=query_type,
        results=items,
        total_results=len(items),
        search_frames=request_params.get("search_frames", True),
        search_objects=request_params.get("search_objects", True),
        max_results=request_params.get("max_results", 50),
    )


@router.post("/text", response_model=SearchResponse)
async def search_by_text(request: TextSearchRequest):
    """
    Search for similar frames/objects using text query.

    Args:
        request: TextSearchRequest with query and search parameters

    Returns:
        SearchResponse with matching results

    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(
            f"Text search request: '{request.query}' (max_results={request.max_results})"
        )

        search_engine = get_search_engine()

        # Perform search
        results = search_engine.search_by_text(
            query=request.query,
            search_frames=request.search_frames,
            search_objects=request.search_objects,
            max_results=request.max_results,
            video_names=request.video_names,
        )

        # Convert to API response format
        response = _convert_search_results(
            results=results,
            query=request.query,
            query_type="text",
            request_params={
                "search_frames": request.search_frames,
                "search_objects": request.search_objects,
                "max_results": request.max_results,
            },
        )

        logger.info(f"Text search returned {len(results)} results")
        return response

    except Exception as e:
        logger.error(f"Text search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/image", response_model=SearchResponse)
async def search_by_image(
    image: UploadFile = File(..., description="Image file to search with"),
    search_frames: bool = Form(True, description="Search in video frames"),
    search_objects: bool = Form(True, description="Search in detected objects"),
    max_results: int = Form(50, ge=1, le=200, description="Maximum number of results"),
    video_names: Optional[str] = Form(
        None, description="Comma-separated list of video names to filter by"
    ),
):
    """
    Search for similar frames/objects using an uploaded image.

    Args:
        image: Uploaded image file
        search_frames: Whether to search in frames
        search_objects: Whether to search in objects
        max_results: Maximum number of results to return
        video_names: Comma-separated list of video names to filter by

    Returns:
        SearchResponse with matching results

    Raises:
        HTTPException: If search fails or image is invalid
    """
    temp_path = None
    try:
        # Validate image file
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="File must be an image (JPEG, PNG, etc.)"
            )

        logger.info(
            f"Image search request: {image.filename} (max_results={max_results})"
        )

        # Parse video_names from comma-separated string
        video_names_list = None
        if video_names:
            video_names_list = [v.strip() for v in video_names.split(",") if v.strip()]

        # Save uploaded file to temporary location
        suffix = Path(image.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await image.read()
            temp_file.write(content)
            temp_path = temp_file.name

        search_engine = get_search_engine()

        # Perform search
        results = search_engine.search_by_image(
            image_path=temp_path,
            search_frames=search_frames,
            search_objects=search_objects,
            max_results=max_results,
            video_names=video_names_list,
        )

        # Convert to API response format
        response = _convert_search_results(
            results=results,
            query=image.filename,
            query_type="image",
            request_params={
                "search_frames": search_frames,
                "search_objects": search_objects,
                "max_results": max_results,
            },
        )

        logger.info(f"Image search returned {len(results)} results")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Image search failed: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_path and Path(temp_path).exists():
            try:
                Path(temp_path).unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_path}: {e}")


@router.get("/examples")
async def get_example_images():
    """
    Get list of example images that can be used for search.

    Returns:
        List of example images with their paths and URLs
    """
    try:
        storage_manager = get_storage_manager()
        storage = storage_manager.get_storage()

        examples = []

        # List all files in example_images/ prefix
        try:
            example_files = storage.list_files("example_images/")

            for s3_path in example_files:
                # Only include image files
                if s3_path.lower().endswith((".jpg", ".jpeg", ".png")):
                    filename = Path(s3_path).name
                    display_name = (
                        Path(filename).stem.replace("_", " ").replace("-", " ").title()
                    )

                    # Get presigned URL
                    try:
                        url = storage_manager.get_presigned_url(s3_path)
                    except:
                        url = None

                    examples.append(
                        {
                            "name": display_name,
                            "path": s3_path,
                            "url": url,
                        }
                    )
        except Exception as e:
            logger.warning(f"Could not list example images: {e}")

        return {"examples": examples}

    except Exception as e:
        logger.error(f"Error getting example images: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get example images: {str(e)}"
        )
