import streamlit as st
from pathlib import Path
from search import search  # archivo que contiene toda la lógica
import base64
import pickle

st.set_page_config(
    page_title="Buscador de Archivo Audiovisual",
    page_icon="🎥",
    layout="wide",
)

# -------------------------------------------------------
# UI
# -------------------------------------------------------

st.title("🎥 Buscador de Archivo Audiovisual")
st.write(
    "Introduce una descripción en texto para encontrar los fotogramas más similares."
)

query = st.text_input(
    "Consulta de búsqueda:",
    placeholder="Ejemplo: policías en línea, mujer sosteniendo un cartel",
)

# Sidebar for debugging
st.sidebar.title("Debugging Sidebar")

# Resolve the path relative to the script's location
input_videos_dir = Path(__file__).parent / "input_videos"

# Dropdown to select input video
input_videos = [video.name for video in input_videos_dir.glob("*.mp4")]
selected_video = st.sidebar.selectbox("Select Input Video", input_videos)

# Add a video player for the selected video
if selected_video:
    video_path = input_videos_dir / selected_video
    if video_path.exists():
        st.sidebar.video(str(video_path))
    else:
        st.sidebar.write("Selected video file not found.")


# Open and count embeddings for search

PROJECT_ROOT = Path(__file__).resolve().parents[1]

frame_embeddings_file = PROJECT_ROOT / "app/embeddings/frame_embeddings.pkl"
object_embeddings_file = PROJECT_ROOT / "app/embeddings/object_embeddings.pkl"

# Debug: Log the total number of embeddings and any issues
if frame_embeddings_file.exists():
    with open(frame_embeddings_file, "rb") as f:
        frame_embeddings = pickle.load(f)
    total_frame_embeddings = len(frame_embeddings)
    st.sidebar.write(f"Total Frame Embeddings: {total_frame_embeddings}")
    used_frame_embeddings = sum(
        1 for emb in frame_embeddings.values() if emb is not None
    )
    st.sidebar.write(f"Frame Embeddings Used for Search: {used_frame_embeddings}")
else:
    st.sidebar.write("Frame Embeddings File Not Found")

if object_embeddings_file.exists():
    with open(object_embeddings_file, "rb") as f:
        object_embeddings = pickle.load(f)
    total_object_embeddings = len(object_embeddings)
    st.sidebar.write(f"Total Object Embeddings: {total_object_embeddings}")
    used_object_embeddings = sum(
        1 for emb in object_embeddings.values() if emb is not None
    )
    st.sidebar.write(f"Object Embeddings Used for Search: {used_object_embeddings}")
else:
    st.sidebar.write("Object Embeddings File Not Found")

# Ensure the correct paths are used for loading frame and object paths
FRAME_PATHS_PATH = Path(__file__).parent / "embeddings/frame_paths.pkl"
OBJECT_PATHS_PATH = Path(__file__).parent / "embeddings/object_paths.pkl"

# Load the paths using the correct paths
with open(FRAME_PATHS_PATH, "rb") as f:
    frame_paths = pickle.load(f)

with open(OBJECT_PATHS_PATH, "rb") as f:
    object_paths = pickle.load(f)

# Trigger search when the user presses Enter
if query.strip():
    st.session_state.search_triggered = True

if "search_triggered" in st.session_state and st.session_state.search_triggered:
    st.write("🔍 Buscando… esto puede tardar unos segundos.")

    try:
        results = search(query, top_k=12)

        st.subheader("Resultados")

        for result in results:
            col1, col2 = st.columns(2)

            with col1:
                if result["type"] == "frame":
                    full_path = Path("output_frames") / result["path"]
                    if full_path.exists():
                        st.image(str(full_path), use_container_width=True)
                    else:
                        st.error(f"No se encontró la imagen: {full_path}")
                elif result["type"] == "object":
                    object_path = Path("cropped_objects") / result["path"]
                    if object_path.exists():
                        with open(object_path, "rb") as img_file:
                            encoded_image = base64.b64encode(img_file.read()).decode(
                                "utf-8"
                            )

                        st.markdown(
                            f"""
                            <div style="max-height: 300px; overflow: hidden;">
                                <img src="data:image/jpeg;base64,{encoded_image}" alt="Objeto" style="max-height: 300px; width: auto;">
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error(f"No se encontró la imagen del objeto: {object_path}")

            with col2:
                if result["type"] == "object":
                    frame_path = Path("output_frames") / result["frame_path"]
                    if frame_path.exists():
                        st.image(
                            str(frame_path),
                            use_container_width=True,
                            caption="Fotograma completo",
                        )
                    else:
                        st.error(f"No se encontró el fotograma: {frame_path}")

                st.write(f"**Ruta:** `{result['path']}`")
                st.write(f"**Similitud:** `{result['similarity']:.4f}`")

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")

    st.session_state.search_triggered = False
