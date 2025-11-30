"""
computes embeddings with CLIP for the whole frame and stores them to .pkl iteratively
"""

import pickle
from pathlib import Path
from embeddings import embed_image_clip_only
import numpy as np

# -----------------------------
# Configuration
# -----------------------------
FRAMES_DIR = Path("output_frames")
OUTPUT_EMBEDDINGS_FILE = "clip_only_embeddings.pkl"
OUTPUT_PATHS_FILE = "clip_only_paths.pkl"

# -----------------------------
# Load frame paths
# -----------------------------
# Recursively find all .jpg files in subdirectories
image_paths = sorted(FRAMES_DIR.rglob("*.jpg"))

if not image_paths:
    raise FileNotFoundError("No frames found in output_frames or its subdirectories.")

# Filter to start from frame_00164.jpg
start_frame = "video_2_frame_00317.jpg"
image_paths = [path for path in image_paths if path.name >= start_frame]

if not image_paths:
    raise FileNotFoundError(f"No frames found starting from {start_frame}.")

print(f"Found {len(image_paths)} frames to process, starting from {start_frame}.")

# -----------------------------
# Compute embeddings iteratively
# -----------------------------
# Check if files already exist to resume progress
if Path(OUTPUT_EMBEDDINGS_FILE).exists():
    with open(OUTPUT_EMBEDDINGS_FILE, "rb") as f:
        clip_embeddings = pickle.load(f)
else:
    clip_embeddings = {}

if Path(OUTPUT_PATHS_FILE).exists():
    with open(OUTPUT_PATHS_FILE, "rb") as f:
        saved_paths = pickle.load(f)
else:
    saved_paths = []

# Filter out already processed frames
image_paths = [
    path for path in image_paths if path.relative_to(FRAMES_DIR) not in saved_paths
]

print(f"Processing {len(image_paths)} new frames...")

for path in image_paths:
    print(f"Embedding: {path.name}")
    out = embed_image_clip_only(path)
    emb = out["frame_embedding"]

    # Ensure NumPy array
    emb = np.array(emb, dtype=float)

    # Use relative paths to preserve folder structure
    relative_path = path.relative_to(FRAMES_DIR)  # e.g., video1/frame_00164.jpg
    clip_embeddings[str(relative_path)] = emb  # Store as a string for compatibility

    # Save progress iteratively
    with open(OUTPUT_EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(clip_embeddings, f)

    saved_paths.append(relative_path)
    with open(OUTPUT_PATHS_FILE, "wb") as f:
        pickle.dump(saved_paths, f)

print("\nAll embeddings computed and saved iteratively.")
