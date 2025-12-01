import io
import numpy as np
from PIL import Image
from dotenv import load_dotenv
import replicate
import os
import os
import replicate

# Try loading .env locally (ignored on Streamlit Cloud)
try:
    from dotenv import load_dotenv

    load_dotenv()  # loads REPLICATE_API_TOKEN locally
except:
    pass

# Always load from environment (this is where Streamlit Secrets go)
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

if not REPLICATE_API_TOKEN:
    raise RuntimeError(
        "Missing Replicate API token. \n"
        "Locally: add to .env as REPLICATE_API_TOKEN=xxx \n"
        "Streamlit: add in Secrets as REPLICATE_API_TOKEN='xxx'"
    )

# Create Replicate client
client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# -----------------------------
# OPTIONAL YOLO SUPPORT (LOCAL)
# -----------------------------
# YOLO + OpenCV cannot be imported on Streamlit Cloud.
# We try to import them, but fail gracefully.
try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
except Exception:
    YOLO = None
    YOLO_AVAILABLE = False


# -----------------------------
# CLIP EMBEDDINGS (WORKS ON STREAMLIT)
# -----------------------------
def embed_text_clip(text: str):
    """Embed text using CLIP via Replicate (works on Streamlit)."""
    client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))
    output = client.run(
        "openai/clip",
        input={"text": text, "task": "embed"},
    )
    return np.array(output["embedding"])


def embed_clip(image: Image.Image):
    """Embed image using CLIP via Replicate (works on Streamlit)."""
    client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)

    output = client.run(
        "openai/clip",
        input={"image": buf, "task": "embed"},
    )
    return np.array(output["embedding"])


def embed_text_image_clip(text: str, image: Image.Image):
    text_embedding = embed_text_clip(text)
    image_embedding = embed_clip(image)
    return text_embedding, image_embedding


# -----------------------------
# OPTIONAL YOLO (LOCAL ONLY)
# -----------------------------
def run_yolo_locally(image_path: str):
    """Local-only YOLO inference. Will raise error on Streamlit."""
    if not YOLO_AVAILABLE:
        raise RuntimeError(
            "YOLO is not available in this environment. "
            "Use this function only on your local machine."
        )

    model = YOLO("yolov8n.pt")  # local file
    results = model(image_path)
    return results


# -----------------------------
# UTILITIES
# -----------------------------
def cosine_similarity(a, b):
    import streamlit as st

    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
