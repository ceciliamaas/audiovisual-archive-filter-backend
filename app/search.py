import os
import pickle
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# -----------------------------------------------------------
# 1) Load Replicate API token (Streamlit first, fallback to .env)
# -----------------------------------------------------------
try:
    import streamlit as st

    REPLICATE_API_TOKEN = st.secrets.get("REPLICATE_API_TOKEN")
except Exception:
    REPLICATE_API_TOKEN = None

if not REPLICATE_API_TOKEN:
    load_dotenv()
    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

if not REPLICATE_API_TOKEN:
    raise RuntimeError("Missing Replicate API token. Add to .env or Streamlit secrets.")

import replicate

client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# -----------------------------------------------------------
# 2) PATHS TO EMBEDDINGS
# -----------------------------------------------------------
FRAME_EMB_PATH = Path(__file__).parent / "./embeddings/frame_embeddings.pkl"
FRAME_PATHS_PATH = Path(__file__).parent / "embeddings/frame_paths.pkl"

OBJECT_EMB_PATH = Path(__file__).parent / "./embeddings/object_embeddings.pkl"
OBJECT_PATHS_PATH = Path(__file__).parent / "embeddings/object_paths.pkl"

# Load precomputed frame embeddings
with open(FRAME_EMB_PATH, "rb") as f:
    FRAME_EMBEDDINGS = pickle.load(f)

with open(FRAME_PATHS_PATH, "rb") as f:
    frame_paths = pickle.load(f)

# Load precomputed object embeddings
with open(OBJECT_EMB_PATH, "rb") as f:
    OBJECT_EMBEDDINGS = pickle.load(f)

with open(OBJECT_PATHS_PATH, "rb") as f:
    object_paths = pickle.load(f)

# Convert dict values to NumPy arrays
for k, v in FRAME_EMBEDDINGS.items():
    FRAME_EMBEDDINGS[k] = np.array(v, dtype=float)

for k, v in OBJECT_EMBEDDINGS.items():
    OBJECT_EMBEDDINGS[k] = np.array(v, dtype=float)

# Debug: Log loaded object paths
print(
    "Loaded object paths:", object_paths[:10]
)  # Log first 10 object paths for verification

# Debug: Log loaded frame paths
print(
    "Loaded frame paths:", frame_paths[:10]
)  # Log first 10 frame paths for verification


# -----------------------------------------------------------
# 3) Compute CLIP text embedding using Replicate
# -----------------------------------------------------------
def embed_text_clip(text: str) -> np.ndarray:
    output = client.run("openai/clip", input={"text": text, "task": "embed"})
    emb = output["embedding"]
    return np.array(emb, dtype=float)


# -----------------------------------------------------------
# 4) Cosine similarity
# -----------------------------------------------------------
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)

    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# -----------------------------------------------------------
# 5) SEARCH FUNCTION (main entry point)
# -----------------------------------------------------------
def search(query: str, top_k: int = 10):
    """
    Returns top_k most similar frames and objects for the given text query.
    Includes metadata to distinguish between frames and objects.
    """

    text_vec = embed_text_clip(query)

    results = []

    # Search in frame embeddings
    for rel_path in frame_paths:
        key = str(rel_path)

        if key not in FRAME_EMBEDDINGS:
            continue

        frame_vec = FRAME_EMBEDDINGS[key]
        sim = cosine_similarity(text_vec, frame_vec)
        results.append({"type": "frame", "path": key, "similarity": sim})

    # Search in object embeddings
    object_results_count = 0

    # Debug: Log the total number of object embeddings and paths
    print(f"Total object embeddings: {len(OBJECT_EMBEDDINGS)}")
    print(f"Total object paths: {len(object_paths)}")

    for rel_path in object_paths:
        key = str(rel_path).replace("cropped_objects/", "")

        if key not in OBJECT_EMBEDDINGS:
            # Skip missing embeddings silently instead of printing errors
            continue

        object_vec = OBJECT_EMBEDDINGS[key]
        sim = cosine_similarity(text_vec, object_vec)

        # Extract video number (video_1)
        video_number = key.split("_")[0] + "_" + key.split("_")[1]

        # Extract the frame identifier (video_1_frame_00001)
        frame_id = key.split("_obj_")[0]

        # Build final frame path
        frame_path = f"{video_number}/{frame_id}.jpg"
        results.append(
            {"type": "object", "path": key, "frame_path": frame_path, "similarity": sim}
        )
        object_results_count += 1

    print(f"Found {object_results_count} results in object embeddings.")

    return sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k]


if __name__ == "__main__":
    query = "policeman"  # Replace with your test query
    top_k = 20
    print(f"Running search for query: '{query}'")
    results = search(query, top_k=top_k)
    print("Search results:")
    for result in results:
        print(result)
