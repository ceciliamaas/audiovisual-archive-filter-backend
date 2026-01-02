"""
Results display component for the Streamlit app.
Handles rendering of search results with images from storage.
"""

import streamlit as st
from typing import List, Optional
import logging
from pathlib import Path

from ...core.search import SearchResult
from ...storage import get_storage_manager

logger = logging.getLogger(__name__)


def render_results(results: List[SearchResult], query_config: dict) -> None:
    """
    Render search results in an organized grid layout.

    Args:
        results: List of SearchResult objects
        query_config: Configuration used for the search
    """
    if not results:
        st.warning(
            "No se encontraron resultados para tu búsqueda. Intenta con términos diferentes."
        )
        return

    # Results header
    st.markdown("---")

    # Display different headers based on query type
    query_type = query_config.get("type", "text")
    if query_type == "text":
        query_text = query_config.get("query", "")
        st.markdown(f"### 📋 Resultados para '{query_text}'")
    else:  # image search
        st.markdown(f"### 📋 Resultados de búsqueda por imagen")
        st.caption(f"{len(results)} resultados encontrados")

    # Group results by type for better organization
    frame_results = [r for r in results if r.result_type == "frame"]
    object_results = [r for r in results if r.result_type == "object"]

    # Display frames
    if frame_results:
        st.markdown(f"#### 🎬 Fotogramas ({len(frame_results)})")
        _render_result_grid(frame_results, "frame")

    # Display objects
    if object_results:
        st.markdown(f"#### 🎯 Objetos detectados ({len(object_results)})")
        _render_result_grid(object_results, "object")


def _render_result_grid(results: List[SearchResult], result_type: str) -> None:
    """Render a grid of results"""

    # Sort by similarity (highest first)
    sorted_results = sorted(results, key=lambda x: x.similarity, reverse=True)

    if result_type == "frame":
        # For frames, display in 3 columns
        cols_per_row = 3
        for i in range(0, len(sorted_results), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                result_idx = i + j
                if result_idx < len(sorted_results):
                    result = sorted_results[result_idx]
                    _render_frame_result(col, result)
    else:
        # For objects, display with frame context - one per row
        for result in sorted_results:
            _render_object_with_frame(result)


def _render_frame_result(col, result: SearchResult) -> None:
    """Render a single frame result"""
    try:
        logger.info(f"Attempting to load frame from path: {result.path}")
        image_data = _get_image_from_storage(result.path)

        if image_data is not None:
            filename = Path(result.path).name

            with col:
                st.image(image_data, caption=f"Frame: {filename}", width="stretch")
                st.caption(f"Similaridad: {result.similarity:.3f}")
        else:
            with col:
                st.error(f"❌ No se pudo cargar: {Path(result.path).name}")
                st.write(f"Similaridad: {result.similarity:.3f}")
                logger.error(f"Failed to load frame: {result.path}")

    except Exception as e:
        logger.error(f"Error rendering frame {result.path}: {e}", exc_info=True)
        with col:
            st.error(f"❌ Error: {Path(result.path).name}")


def _render_object_with_frame(result: SearchResult) -> None:
    """Render an object result with its corresponding frame"""
    try:
        # Extract frame information from object path
        # Path format: objects/video_X/frame_XXXXX_obj_Y.jpg
        object_path = result.path

        # Get frame path from object path
        # objects/reconstruccion_jonathan/frame_00367_obj_2.jpg -> frames/reconstruccion_jonathan/frame_00367.jpg
        path_parts = Path(object_path).parts
        if len(path_parts) >= 3 and path_parts[0] == "objects":
            video_dir = path_parts[1]  # reconstruccion_jonathan, etc.
            filename = path_parts[2]  # frame_00367_obj_2.jpg

            # Extract frame number from filename
            if "_obj_" in filename:
                frame_base = filename.split("_obj_")[0]  # frame_00367
                # Frames are named simply: frame_00367.jpg (no video prefix)
                frame_name = f"{frame_base}.jpg"
                frame_path = f"frames/{video_dir}/{frame_name}"
            else:
                frame_path = None
        else:
            frame_path = None

        logger.info(f"Object path: {object_path}, Extracted frame path: {frame_path}")

        # Create two columns
        col1, col2 = st.columns([1, 2])

        # Load object image
        object_image = _get_image_from_storage(object_path)

        # Load frame image if path exists
        frame_image = None
        if frame_path:
            frame_image = _get_image_from_storage(frame_path)

        # Display object (with max height 150px)
        with col1:
            if object_image is not None:
                # Use HTML/CSS to set max height
                st.markdown("**Objeto detectado:**")
                st.image(
                    object_image,
                    use_container_width=True,
                )
                st.caption(f"Similaridad: {result.similarity:.3f}")
                # Add CSS to limit height
                st.markdown(
                    """
                <style>
                img {
                    max-height: 150px;
                    object-fit: contain;
                }
                </style>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.error(f"❌ Objeto no disponible")
                logger.error(f"Failed to load object: {object_path}")

        # Display frame
        with col2:
            if frame_image is not None:
                st.markdown("**Fotograma completo:**")
                st.image(
                    frame_image,
                    use_container_width=True,
                )
            elif frame_path:
                st.warning(f"⚠️ Fotograma no disponible: {frame_path}")
                logger.warning(f"Failed to load frame: {frame_path}")
            else:
                st.info("ℹ️ Fotograma no identificado")

        st.markdown("---")

    except Exception as e:
        logger.error(
            f"Error rendering object with frame {result.path}: {e}", exc_info=True
        )
        st.error(f"❌ Error al cargar objeto: {Path(result.path).name}")
        st.write(f"Error: {str(e)}")


def _get_image_from_storage(image_path: str):
    """Get image data from storage backend"""
    try:
        storage_manager = get_storage_manager()
        storage = storage_manager.get_storage()

        # Try to get direct URL first (for S3)
        image_url = storage.get_file_url(image_path)
        if image_url:
            logger.info(
                f"Generated presigned URL for {image_path}: {image_url[:100]}..."
            )

            # Fetch the image from the URL
            import requests
            from PIL import Image
            from io import BytesIO

            try:
                logger.info(f"Fetching image from URL...")
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()

                logger.info(
                    f"Response status: {response.status_code}, content-length: {len(response.content)}"
                )

                # Load image from response content
                image_bytes = BytesIO(response.content)
                img = Image.open(image_bytes)

                logger.info(
                    f"Successfully loaded image from URL for {image_path}, size: {img.size}"
                )
                return img
            except requests.exceptions.RequestException as req_error:
                logger.error(f"Request failed for URL: {req_error}")
                # Fall through to download method
            except Exception as url_error:
                logger.error(f"Failed to load image from URL response: {url_error}")
                # Fall through to download method
        else:
            logger.warning(
                f"No presigned URL available for {image_path}, will try downloading"
            )

        # Fallback: download to temp file and return the file path
        import tempfile
        from PIL import Image

        # Create temp file with proper extension
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp_path = tmp_file.name
        tmp_file.close()

        # Try to download the file
        if storage.download_file(image_path, tmp_path):
            logger.info(f"Downloaded {image_path} to {tmp_path}")
            # Load and return the image
            try:
                img = Image.open(tmp_path)
                return img
            except Exception as img_error:
                logger.error(f"Downloaded file is not a valid image: {img_error}")
                return None
        else:
            # Try fallback storage
            if storage_manager.fallback_enabled:
                fallback_storage = storage_manager.get_storage(prefer_fallback=True)
                if fallback_storage != storage and fallback_storage.download_file(
                    image_path, tmp_path
                ):
                    logger.info(f"Downloaded {image_path} from fallback to {tmp_path}")
                    try:
                        img = Image.open(tmp_path)
                        return img
                    except Exception as img_error:
                        logger.error(
                            f"Downloaded file from fallback is not a valid image: {img_error}"
                        )
                        return None

            logger.error(f"Failed to download image: {image_path}")
            return None

    except Exception as e:
        logger.error(f"Error getting image from storage {image_path}: {e}")
        return None


def _handle_download(result: SearchResult) -> None:
    """Handle file download request"""
    try:
        storage_manager = get_storage_manager()
        storage = storage_manager.get_storage()

        # Get file data
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            if storage.download_file(result.path, tmp_file.name):
                with open(tmp_file.name, "rb") as f:
                    file_data = f.read()

                filename = Path(result.path).name
                st.download_button(
                    label=f"💾 Descargar {filename}",
                    data=file_data,
                    file_name=filename,
                    mime="image/jpeg",
                    key=f"download_button_{result.path}",
                )
            else:
                st.error("No se pudo descargar el archivo")

    except Exception as e:
        logger.error(f"Error handling download for {result.path}: {e}")
        st.error(f"Error en descarga: {e}")


def render_search_stats(results: List[SearchResult]) -> None:
    """Render search statistics"""
    if not results:
        return

    # Calculate statistics
    total_results = len(results)
    frame_count = len([r for r in results if r.result_type == "frame"])
    object_count = len([r for r in results if r.result_type == "object"])
    avg_similarity = sum(r.similarity for r in results) / total_results
    max_similarity = max(r.similarity for r in results)
    min_similarity = min(r.similarity for r in results)

    # Display stats
    st.markdown("#### 📊 Estadísticas de búsqueda")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total resultados", total_results)

    with col2:
        st.metric("Fotogramas", frame_count)

    with col3:
        st.metric("Objetos", object_count)

    with col4:
        st.metric("Similaridad promedio", f"{avg_similarity:.3f}")

    # Similarity distribution
    with st.expander("📈 Distribución de similaridades"):
        similarities = [r.similarity for r in results]
        st.bar_chart({"Similaridad": similarities})

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Máxima:** {max_similarity:.4f}")
            st.write(f"**Promedio:** {avg_similarity:.4f}")

        with col2:
            st.write(f"**Mínima:** {min_similarity:.4f}")
            st.write(f"**Rango:** {max_similarity - min_similarity:.4f}")
