"""
Search interface component for the Streamlit app.
Handles user input for search queries and options.
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile


def _get_example_images() -> Dict[str, str]:
    """
    Get example images from storage (S3 or local fallback).

    Returns:
        Dict mapping display name to storage path
    """
    from ...storage import get_storage_manager

    example_images = {}

    # Try S3 first
    try:
        storage = get_storage_manager().get_storage()

        # List all files in example_images/ prefix
        example_files = storage.list_files("example_images/")
        
        for s3_path in example_files:
            # Only include image files
            if s3_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Extract filename from path
                filename = Path(s3_path).name
                # Use filename without extension as display name
                display_name = Path(filename).stem.replace("_", " ").replace("-", " ").title()
                example_images[display_name] = s3_path

    except Exception as e:
        st.warning(f"No se pudieron cargar imágenes de ejemplo desde S3: {e}")

    # Fallback to local directory if no S3 images found
    if not example_images:
        local_dir = Path("data/example_images")
        if local_dir.exists():
            for img_file in local_dir.glob("*.[jp][pn][g]*"):
                display_name = img_file.stem.replace("_", " ").replace("-", " ").title()
                example_images[display_name] = str(img_file)

    return example_images


def render_search_interface() -> Optional[Dict[str, Any]]:
    """
    Render the search input interface and return query configuration.

    Returns:
        Dict with search parameters or None if no search should be performed
    """
    st.title("🎥 Buscador de Archivo Audiovisual")
    st.markdown(
        "Busca contenido en videos usando descripción de texto o imágenes similares"
    )

    # Initialize max_results in session state if not exists
    if "max_results" not in st.session_state:
        st.session_state.max_results = 10

    # Search type selection
    search_type = st.radio(
        "Tipo de búsqueda:",
        ["🔤 Búsqueda por texto", "🖼️ Búsqueda por imagen"],
        horizontal=True,
        disabled=False,
    )

    query_config = None

    if search_type == "🔤 Búsqueda por texto":
        query_config = _render_text_search()
    else:
        # Image search enabled
        query_config = _render_image_search()

    # Show max results slider below search interface
    max_results = st.slider(
        "Máximo resultados",
        min_value=10,
        max_value=100,
        value=st.session_state.max_results,
        key="max_results_slider",
    )

    # Update session state
    st.session_state.max_results = max_results

    # Add search options to config if search is triggered
    if query_config:
        query_config.update(
            {
                "search_frames": True,  # Always search frames
                "search_objects": True,  # Always search objects
                "max_results": max_results,
            }
        )

    return query_config


def _render_text_search() -> Optional[Dict[str, Any]]:
    """Render text search interface"""

    # Initialize session state for query text if not exists
    if "current_query" not in st.session_state:
        st.session_state.current_query = ""

    # Check if we need to trigger search from example
    should_trigger_search = False
    if "trigger_search_with_query" in st.session_state:
        query_to_search = st.session_state.trigger_search_with_query
        del st.session_state.trigger_search_with_query
        st.session_state.current_query = query_to_search
        should_trigger_search = True

    # Use form to enable Enter key submission
    with st.form(key="text_search_form", clear_on_submit=False):
        query_text = st.text_input(
            "Describe lo que buscas:",
            value=st.session_state.current_query,
            placeholder="Ej: personas caminando en la calle, edificios históricos, manifestación...",
            help="Describe el contenido que quieres encontrar en los videos. Presiona Enter para buscar.",
        )

        # Search button inside form (not disabled to allow form submission)
        search_clicked = st.form_submit_button("🔍 Buscar", type="primary")

        # Only return search if button clicked AND query has text
        if search_clicked:
            if query_text.strip():
                st.session_state.current_query = query_text.strip()
                return {"type": "text", "query": query_text.strip()}
            else:
                st.warning("Por favor ingresa un texto para buscar")
                return None

    # If triggered by example, return search config after rendering form
    if should_trigger_search:
        return {"type": "text", "query": st.session_state.current_query}

    # Example queries (outside form)
    with st.expander("💡 Ejemplos de búsqueda"):
        example_queries = [
            "policía",
            "bandera",
            "hombre con casco amarillo",
            "edificio",
        ]

        cols = st.columns(2)
        for i, example in enumerate(example_queries):
            col = cols[i % 2]
            if col.button(f"'{example}'", key=f"example_{i}"):
                # Set the query and trigger search on next rerun
                st.session_state.trigger_search_with_query = example
                st.rerun()

    return None


def _render_image_search() -> Optional[Dict[str, Any]]:
    """Render image search interface"""

    # Initialize session state for image path
    if "selected_image_path" not in st.session_state:
        st.session_state.selected_image_path = None

    # Image upload
    uploaded_file = st.file_uploader(
        "Sube una imagen de referencia:",
        type=["png", "jpg", "jpeg"],
        help="Sube una imagen para encontrar contenido similar en los videos",
    )

    image_path = None

    if uploaded_file is not None:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{uploaded_file.type.split('/')[-1]}"
        ) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            image_path = tmp_file.name
            st.session_state.selected_image_path = image_path

        # Show preview
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(
                uploaded_file, caption="Imagen de referencia", use_container_width=True
            )

    # Alternative: Use example images
    with st.expander("📷 Usar imágenes de ejemplo"):
        example_images = _get_example_images()

        if example_images:
            selected_example = st.selectbox(
                "Selecciona una imagen de ejemplo:",
                options=[None] + list(example_images.keys()),
                format_func=lambda x: "Ninguna" if x is None else x,
            )

            if selected_example:
                example_path = example_images[selected_example]

                # Check if it's a local path or S3 path
                is_local = Path(example_path).exists()
                
                if is_local:
                    # Local file - use directly
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.image(
                            example_path,
                            caption=f"Ejemplo: {selected_example}",
                            use_container_width=True,
                        )

                    if st.button("Usar esta imagen"):
                        st.session_state.selected_image_path = example_path
                        st.rerun()
                else:
                    # S3/remote file - download it
                    try:
                        from ...storage import get_storage_manager

                        # Download to temp file for display and use
                        tmp_file = tempfile.NamedTemporaryFile(
                            delete=False, suffix=Path(example_path).suffix
                        )
                        tmp_path = tmp_file.name
                        tmp_file.close()
                        
                        storage = get_storage_manager().get_storage()
                        if storage.download_file(example_path, tmp_path):
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                st.image(
                                    tmp_path,
                                    caption=f"Ejemplo: {selected_example}",
                                    use_container_width=True,
                                )

                            if st.button("Usar esta imagen"):
                                st.session_state.selected_image_path = tmp_path
                                st.rerun()
                        else:
                            st.error("No se pudo cargar la imagen de ejemplo desde el almacenamiento")
                            st.caption(f"Ruta: {example_path}")
                    except Exception as e:
                        st.error(f"Error cargando imagen: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        else:
            st.info("No hay imágenes de ejemplo disponibles")

    # Use session state image path if no upload
    if image_path is None and st.session_state.selected_image_path:
        image_path = st.session_state.selected_image_path

    # Search button
    search_clicked = st.button(
        "🔍 Buscar por imagen", type="primary", disabled=image_path is None
    )

    if search_clicked and image_path:
        return {"type": "image", "image_path": image_path}

    return None
