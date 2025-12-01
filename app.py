import streamlit as st
from PIL import Image
import numpy as np
import pickle
from embeddings import embed_text_clip, cosine_similarity
from pathlib import Path
import os

st.write("TOKEN FOUND:", bool(os.environ.get("REPLICATE_API_TOKEN")))

# -----------------------------
# Load your embeddings (stored earlier)
# -----------------------------
# Example: assume saved as .pkl
with open("clip_only_embeddings.pkl", "rb") as f:
    clip_embeddings = pickle.load(f)

# Ensure paths are valid and organized by subdirectories
frames_dir = Path("output_frames")  # Base directory for frames
updated_clip_embeddings = {}

# Dynamically update paths to match the current structure
for path, embedding in clip_embeddings.items():
    # Extract the filename
    filename = Path(path).name

    # Search for the file in all subdirectories of `output_frames`
    matching_files = list(frames_dir.rglob(filename))  # Recursively search for the file
    if matching_files:
        updated_clip_embeddings[matching_files[0]] = embedding  # Use the first match
    else:
        # Log the error to the console instead of the UI
        print(f"Archivo no encontrado: {filename}")

clip_embeddings = updated_clip_embeddings  # Replace with updated paths
image_paths = list(clip_embeddings.keys())  # Updated list of paths


# -----------------------------
# Search function
# -----------------------------
def search(query, top_k=12):
    # Embed the text query using CLIP
    text_vec = embed_text_clip(query)

    scored = []

    # Compare query to CLIP-only frame embeddings
    for path, frame_vec in clip_embeddings.items():
        sim = cosine_similarity(text_vec, frame_vec)
        scored.append((path, sim))

    st.write("TEXT VEC TYPE:", type(text_vec))
    st.write("FRAME VEC TYPE:", type(frame_vec))

    # Sort by similarity (descending)
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored[:top_k]


# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🔍 Prueba de búsqueda semántica en videos")

# Section: Display uploaded videos
st.sidebar.title("📂 Videos Subidos")
video_dir = Path("input_videos")
video_files = sorted(video_dir.glob("*.mp4"))  # Adjust extension if needed

if video_files:
    st.sidebar.write("Seleccioná un video para reproducir:")
    selected_video = st.sidebar.selectbox(
        "Videos disponibles:", [video.name for video in video_files]
    )

    if selected_video:
        video_path = video_dir / selected_video
        st.sidebar.video(str(video_path))
else:
    st.sidebar.write("No se encontraron videos en la carpeta `input_videos`.")

# Section: Semantic search
query = st.text_input(
    "Ingresá la búsqueda (por ejemplo: policías formados en línea, hombre con gorra negra, mujer sosteniendo un cartel)",
    "",
)

if query:
    st.write(f"### Resultados para: `{query}`")
    results = search(query)

    # Display results in a grid
    num_columns = 3  # Number of columns in the grid
    cols = st.columns(num_columns)

    for i, (path, score) in enumerate(results):
        col = cols[i % num_columns]  # Select the column based on the index
        with col:
            try:
                st.image(
                    Image.open(path),
                    caption=f"{path.parent.name}/{path.name}\nScore: {score:.3f}",
                    use_container_width=True,  # Updated to use the new parameter
                )
            except FileNotFoundError:
                st.write(f"Archivo no encontrado: {path.name}")

# Debugging: Inspect the loaded embeddings
if st.sidebar.checkbox("🔍 Debug: Show loaded embeddings"):
    st.write("Number of embeddings loaded:", len(clip_embeddings))
    st.write("Sample paths and embeddings:")
    for path, embedding in list(clip_embeddings.items())[
        :5
    ]:  # Show the first 5 entries
        st.write(f"Path: {path}, Embedding shape: {np.array(embedding).shape}")
