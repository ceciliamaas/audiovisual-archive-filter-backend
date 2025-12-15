"""
Main Streamlit application for the audiovisual archive search.
Refactored from the original app.py with improved structure.
"""

import streamlit as st
import logging
import sys
from pathlib import Path

# Load environment variables early
from dotenv import load_dotenv

load_dotenv()

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from src.config.settings import app_config, dev_config
from src.config.storage import validate_storage_config
from src.core.search import get_search_engine
from src.storage import get_storage_manager
from src.web.components.search_interface import render_search_interface
from src.web.components.results_display import render_results, render_search_stats

# Configure logging
logging.basicConfig(
    level=logging.INFO if not dev_config.debug_mode else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title=app_config.app_title,
        page_icon=app_config.app_icon,
        layout=app_config.layout,
        initial_sidebar_state="auto",
    )


def render_sidebar():
    """Render sidebar with app information and status"""
    with st.sidebar:
        st.markdown("### ℹ️ Información del sistema")

        # Storage status
        with st.expander("💾 Estado del almacenamiento"):
            storage_status = validate_storage_config()

            if storage_status["s3_available"]:
                st.success("✅ S3/Storj disponible")
            else:
                st.warning("⚠️ S3/Storj no disponible")

            if storage_status["local_available"]:
                st.success("✅ Almacenamiento local disponible")
            else:
                st.error("❌ Almacenamiento local no disponible")

            st.write(f"**Recomendado:** {storage_status['recommended_backend']}")

            # Show storage mode information
            try:
                from src.config.settings import get_preferred_storage_mode

                storage_manager = get_storage_manager()
                manager_status = storage_manager.get_status()
                st.write(
                    f"**Modo actual:** {manager_status.get('preferred_mode', 'unknown')}"
                )
                st.write(
                    f"**Fallback habilitado:** {'Sí' if manager_status.get('fallback_enabled', False) else 'No'}"
                )
            except Exception as e:
                st.write(f"**Error obteniendo modo:** {e}")

            if storage_status["issues"]:
                st.write("**Problemas:**")
                for issue in storage_status["issues"]:
                    st.write(f"• {issue}")

        # Search engine status
        with st.expander("🔍 Estado del motor de búsqueda"):
            try:
                search_engine = get_search_engine()
                search_status = search_engine.get_status()

                if search_status["replicate_available"]:
                    st.success("✅ Replicate API disponible")
                else:
                    st.error("❌ Replicate API no disponible")

                st.write(f"**Modelo:** {search_status['model']}")

                embeddings_status = search_status["embeddings_status"]
                if embeddings_status["loaded"]:
                    st.success("✅ Embeddings cargados")
                    st.write(f"• Fotogramas: {embeddings_status['frame_count']}")
                    st.write(f"• Objetos: {embeddings_status['object_count']}")
                else:
                    st.warning("⚠️ Embeddings no cargados")

            except Exception as e:
                st.error(f"❌ Error: {e}")

        # Debug information
        if dev_config.debug_mode:
            with st.expander("🐛 Debug"):
                st.write("**Modo debug activo**")
                st.write(f"Log level: {dev_config.log_level}")
                st.json(
                    {
                        "app_config": {
                            "max_results": app_config.max_search_results,
                            "similarity_threshold": app_config.similarity_threshold,
                            "model": app_config.embedding_model,
                        }
                    }
                )


def handle_search_error(e: Exception):
    """Handle search errors gracefully"""
    logger.error(f"Search error: {e}")

    if "embeddings" in str(e).lower():
        st.error("❌ Error cargando embeddings. Verifica el almacenamiento.")
    elif "replicate" in str(e).lower():
        st.error("❌ Error con la API de Replicate. Verifica la configuración.")
    elif "storage" in str(e).lower():
        st.error("❌ Error de almacenamiento. Verifica la conexión.")
    else:
        st.error(f"❌ Error inesperado: {e}")

    st.info("💡 Intenta revisar la configuración en la barra lateral.")


def main():
    """Main application function"""
    configure_page()
    render_sidebar()

    # Initialize session state for results
    if "all_results" not in st.session_state:
        st.session_state.all_results = None
    if "last_query_config" not in st.session_state:
        st.session_state.last_query_config = None

    # Main content
    try:
        # Render search interface
        query_config = render_search_interface()

        if query_config:
            # Perform search only if it's a new query
            with st.spinner("🔍 Buscando..."):
                search_engine = get_search_engine()

                # Fetch more results than max to allow slider adjustment
                fetch_limit = 200  # Fetch up to 200 results for filtering

                if query_config["type"] == "text":
                    all_results = search_engine.search_by_text(
                        query=query_config["query"],
                        search_frames=query_config["search_frames"],
                        search_objects=query_config["search_objects"],
                        max_results=fetch_limit,
                    )
                else:  # image search
                    all_results = search_engine.search_by_image(
                        image_path=query_config["image_path"],
                        search_frames=query_config["search_frames"],
                        search_objects=query_config["search_objects"],
                        max_results=fetch_limit,
                    )

                # Store results in session state
                st.session_state.all_results = all_results
                st.session_state.last_query_config = query_config

        # Display results if available (from current search or session state)
        if st.session_state.all_results:
            # Get current max_results from session state (updated by slider)
            max_results = st.session_state.get("max_results", 50)

            # Filter results based on slider value
            filtered_results = st.session_state.all_results[:max_results]

            # Display results
            query_config_display = st.session_state.last_query_config or query_config
            if query_config_display:
                query_config_display["max_results"] = max_results
                render_results(filtered_results, query_config_display)

    except Exception as e:
        handle_search_error(e)


if __name__ == "__main__":
    main()
