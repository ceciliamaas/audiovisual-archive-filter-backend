"""
embeddings.py

Provides two modes for generating embeddings from images:

1) CLIP_ONLY:     A single global CLIP embedding for the full frame.
2) YOLO_ENRICHED: First detects persons using YOLO, crops them,
                   generates CLIP embeddings for each crop, and returns
                   a combined enriched embedding.

Requirements:
    pip install ultralytics pillow numpy replicate python-dotenv
    Add REPLICATE_API_TOKEN=xxxx to .env
"""

import os
import io
import numpy as np
from PIL import Image

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None
from dotenv import load_dotenv
import replicate

# Load environment variables
load_dotenv()


# -------------------------
# CONFIG
# -------------------------

# Load YOLO COCO model (detects 80 common objects including "person")
YOLO_MODEL = YOLO("yolov8n.pt")
PERSON_CLASS_ID = 0  # COCO class index for "person"

# Replicate CLIP model
CLIP_MODEL = "openai/clip"

# Replicate client
client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))


# ===========================================================
#  CLIP EMBEDDING IMPLEMENTATION
# ===========================================================


def embed_clip(image: Image.Image) -> np.ndarray:
    """
    Embeds an image using Replicate's openai/clip model.
    Works for https://replicate.com/openai/clip
    """
    import replicate
    from io import BytesIO
    import numpy as np
    import os

    client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

    # Convert PIL to bytes
    buf = BytesIO()
    image.save(buf, format="JPEG")
    buf.seek(0)

    # Correct call for openai/clip:
    # It requires task='embed' to get embeddings.
    output = client.run("openai/clip", input={"image": buf, "task": "embed"})

    # output is a dict: {"embedding": [...]}
    embedding = output.get("embedding")
    return np.array(embedding, dtype=float)


def embed_text_clip(text: str) -> np.ndarray:
    """
    Embeds a text string into the same CLIP embedding space as images.
    Works with Replicate's openai/clip model.
    """
    import os
    import numpy as np
    import replicate

    client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

    # Replicate call for text embedding (must use task="embed")
    output = client.run(
        CLIP_MODEL,
        input={
            "text": text,
            "task": "embed",  # ensures we get a vector
        },
    )

    # output = {"embedding": [...]}
    emb = output.get("embedding")
    return np.array(emb, dtype=float)


# -------------------------
# Preprocessing Helpers
# -------------------------


def load_image(path_or_img):
    """Load image from path or use existing PIL image."""
    if isinstance(path_or_img, Image.Image):
        return path_or_img.convert("RGB")
    return Image.open(path_or_img).convert("RGB")


def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ===========================================================
# 1)  CLIP-ONLY (GLOBAL IMAGE EMBEDDING)
# ===========================================================


def embed_image_clip_only(image_input) -> dict:
    """
    Generates a single CLIP embedding for the full frame.

    Returns:
        {
            "frame_embedding": np.ndarray,
            "person_embeddings": [],
            "metadata": { … }
        }
    """
    img = load_image(image_input)
    emb = embed_clip(img)

    return {
        "frame_embedding": emb,
        "person_embeddings": [],
        "metadata": {"num_people": 0},
    }


# ===========================================================
# 2)  YOLO + CLIP ENRICHED EMBEDDING
# ===========================================================


def embed_image_yolo_clip(image_input) -> dict:
    """
    Uses YOLO to detect people, crops them, embeds crops with CLIP,
    and returns separate embeddings for the whole frame and each detected person.

    Returns:
        {
            "frame_embedding": np.ndarray,
            "person_embeddings": [np.ndarray, ...],
            "metadata": {
                "num_people": int,
                "persons_detected": int,
            }
        }
    """
    if YOLO is None:
        raise RuntimeError("YOLO is not available in this environment")
    img = load_image(image_input)
    w, h = img.size

    # Run YOLO model to detect objects
    results = YOLO_MODEL(img)[0]

    # Extract bounding boxes for detected persons
    person_boxes = [box for box in results.boxes if int(box.cls[0]) == PERSON_CLASS_ID]

    person_embeddings = []

    # ---- Crop persons and embed with CLIP ----
    for box in person_boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        crop = img.crop((x1, y1, x2, y2))
        person_embeddings.append(embed_clip(crop))

    # ---- Embed whole frame ----
    frame_embedding = embed_clip(img)

    # Return separate embeddings for the frame and persons
    return {
        "frame_embedding": frame_embedding,
        "person_embeddings": person_embeddings,
        "metadata": {
            "num_people": len(person_boxes),
            "persons_detected": len(person_boxes),
        },
    }


# -------------------------
# Standalone Test
# -------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python embeddings.py [clip|yolo] path/to/image.jpg")
        exit()

    mode = sys.argv[1]
    path = sys.argv[2]

    if mode == "clip":
        out = embed_image_clip_only(path)
        print("CLIP embedding computed.")
        print("Shape:", out["frame_embedding"].shape)

    elif mode == "yolo":
        out = embed_image_yolo_clip(path)
        print("YOLO+CLIP embedding computed.")
        print("Detected persons:", out["metadata"]["num_people"])
        print("Vector shape:", out["embedding"].shape)

    else:
        print("Unknown mode. Use 'clip' or 'yolo'.")
