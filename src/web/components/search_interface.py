"""
Search interface component for the Streamlit app.
Handles user input for search queries and options.
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile


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
        example_images_dir = Path("input_image_for_search")
        if example_images_dir.exists():
            example_images = (
                list(example_images_dir.glob("*.jpg"))
                + list(example_images_dir.glob("*.jpeg"))
                + list(example_images_dir.glob("*.png"))
            )

            if example_images:
                selected_example = st.selectbox(
                    "Selecciona una imagen de ejemplo:",
                    options=[None] + example_images,
                    format_func=lambda x: "Ninguna" if x is None else x.name,
                )

                if selected_example:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.image(
                            str(selected_example),
                            caption=f"Ejemplo: {selected_example.name}",
                            use_container_width=True,
                        )

                    if st.button("Usar esta imagen"):
                        st.session_state.selected_image_path = str(selected_example)
                        st.rerun()
            else:
                st.info("No hay imágenes de ejemplo disponibles")
        else:
            st.info("Directorio de imágenes de ejemplo no encontrado")

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
