"""
Compute embeddings for pre-cropped objects in the `CROPPED_DIR` directory
that do not already have embeddings.

Stores results incrementally in:
- object_embeddings.pkl
"""

import os
import pickle
from pathlib import Path
from typing import Dict
import io

import numpy as np
from PIL import Image
from dotenv import load_dotenv
import replicate

# =============================================================================
# Setup
# =============================================================================

load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

if not REPLICATE_API_TOKEN:
    raise RuntimeError("Missing REPLICATE_API_TOKEN in .env")

client = replicate.Client(api_token=REPLICATE_API_TOKEN)

CROPPED_DIR = Path("app/cropped_objects")
OUTPUT_YOLO_EMBEDDINGS_FILE = Path("object_embeddings.pkl")

# =============================================================================
# Utility functions
# =============================================================================


def load_pickle(path: Path, default):
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return default


def embed_clip(image_path: Path) -> np.ndarray:
    """Embed an image using CLIP via replicate."""
    try:
        with Image.open(image_path) as img:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

        out = client.run(
            "openai/clip",
            input={"image": buf, "task": "embed"},
        )
        return np.array(out["embedding"], dtype=np.float32)

    except Exception as e:
        raise RuntimeError(f"CLIP embedding failed for {image_path}: {e}") from e


# =============================================================================
# Main
# =============================================================================


def main():
    # Load existing embeddings
    yolo_embeddings = load_pickle(OUTPUT_YOLO_EMBEDDINGS_FILE, {})

    # Gather cropped object images
    cropped_paths = sorted(CROPPED_DIR.rglob("*.jpg"))
    cropped_paths = [
        p
        for p in cropped_paths
        if str(p.relative_to(CROPPED_DIR)) not in yolo_embeddings
    ]

    print(f"Found {len(cropped_paths)} cropped objects to process.")

    if not cropped_paths:
        print("Nothing to do.")
        return

    for i, path in enumerate(cropped_paths, start=1):
        try:
            embedding = embed_clip(path)
            yolo_embeddings[str(path.relative_to(CROPPED_DIR))] = embedding
            print(f"Processed {i}/{len(cropped_paths)}: {path}")
        except Exception as e:
            print(f"[ERROR] Failed to process {path}: {e}")

        # Save periodically
        if i % 10 == 0 or i == len(cropped_paths):
            with open(OUTPUT_YOLO_EMBEDDINGS_FILE, "wb") as f:
                pickle.dump(yolo_embeddings, f)
            print("Progress saved.")

    print("\nAll embeddings completed.")


if __name__ == "__main__":
    main()
