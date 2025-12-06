"""
Compute embeddings with CLIP for:
1. Full frames
2. Objects detected by YOLO-World-XL

Stores results incrementally in:
- frame_embeddings.pkl       (CLIP for full frames)
- object_embeddings.pkl      (CLIP for YOLO crops)

Resumes automatically if files exist.
Only reprocesses what is missing unless FORCE_REPROCESS is True.
"""

import io
import os
import time
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image
from dotenv import load_dotenv
import replicate
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# Setup
# =============================================================================

load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

if not REPLICATE_API_TOKEN:
    raise RuntimeError("Missing REPLICATE_API_TOKEN in .env")

client = replicate.Client(api_token=REPLICATE_API_TOKEN)

FRAMES_DIR = Path(__file__).parent.parent / "app/output_frames"
CROPPED_DIR = Path(__file__).parent.parent / "app/cropped_objects"


OUTPUT_FRAME_EMBEDDINGS_FILE = (
    Path(__file__).parent.parent / "app/embeddings/frame_embeddings.pkl"
)
OUTPUT_OBJECT_EMBEDDINGS_FILE = (
    Path(__file__).parent.parent / "app/embeddings/object_embeddings.pkl"
)
OUTPUT_FRAME_PATHS_FILE = (
    Path(__file__).parent.parent / "app/embeddings/frame_paths.pkl"
)
OUTPUT_OBJECT_PATHS_FILE = (
    Path(__file__).parent.parent / "app/embeddings/object_paths.pkl"
)

# Classes to detect with YOLO
YOLO_CLASSES = ["person", "building", "car"]  # optional

# If True: recompute CLIP + YOLO for all frames
FORCE_REPROCESS = False


# =============================================================================
# Utility functions
# =============================================================================


def load_pickle(path: Path, default):
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return default


# =============================================================================
# CLIP Embedding
# =============================================================================


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
# YOLO-World-XL Detection
# =============================================================================


def parse_yolo_output(raw):
    """Parses YOLO-World-XL output from Replicate, which may appear in multiple shapes."""

    # CASE 1 — raw is already a JSON string:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raise RuntimeError("String output was not valid JSON")

    # CASE 2 — raw is a list
    if isinstance(raw, list):
        return raw

    # CASE 3 — raw is a dict
    if isinstance(raw, dict):

        # Subcase: dict contains json_str
        if "json_str" in raw:
            try:
                parsed = json.loads(raw["json_str"])
            except json.JSONDecodeError:
                raise RuntimeError("json_str value was not valid JSON")

            # Parsed is the YOLO detections object
            return _parse_det_dict(parsed)

        # Subcase: dict IS the YOLO detections object already
        # i.e. {"Det-0": {...}}
        if all(k.startswith("Det-") for k in raw.keys()):
            return _parse_det_dict(raw)

        # Subcase: dict contains standard array keys
        for key in ["predictions", "detections", "boxes", "results"]:
            if isinstance(raw.get(key), list):
                return raw[key]

    raise RuntimeError("Could not parse YOLO output structure")


def _parse_det_dict(det_dict):
    """Helper to normalize YOLO dict: {'Det-0': {...}, ...}"""
    detections = []
    for det in det_dict.values():

        # Some models double-encode detection JSON
        if isinstance(det, str):
            try:
                det = json.loads(det)
            except Exception:
                continue

        if not isinstance(det, dict):
            continue

        x0 = det.get("x0")
        y0 = det.get("y0")
        x1 = det.get("x1")
        y1 = det.get("y1")
        if None in (x0, y0, x1, y1):
            continue

        detections.append(
            {
                "bbox": [
                    int(round(x0)),
                    int(round(y0)),
                    int(round(x1)),
                    int(round(y1)),
                ],
                "score": det.get("score"),
                "cls": det.get("cls"),
            }
        )

    return detections


def extract_bbox(det) -> Tuple[int, int, int, int]:
    """Extract bbox from a YOLO detection dict."""
    if "bbox" in det:
        x1, y1, x2, y2 = det["bbox"]
    elif "xyxy" in det:
        x1, y1, x2, y2 = det["xyxy"]
    elif "box" in det and len(det["box"]) == 4:
        x1, y1, x2, y2 = det["box"]
    else:
        return None

    return int(x1), int(y1), int(x2), int(y2)


def detect_and_crop(image_path: Path) -> List[Path]:
    """Detect objects with YOLO-World-XL and save cropped regions."""
    try:
        with open(image_path, "rb") as f:
            input_data = {"input_media": f, "return_json": True}
            if YOLO_CLASSES:
                input_data["class_names"] = ",".join(YOLO_CLASSES)

            raw_output = client.run(
                "franz-biz/yolo-world-xl:fd1305d3fc19e81540542f51c2530cf8f393e28cc6ff4976337c3e2b75c7c292",
                input=input_data,
            )

        # Depending on model, raw_output may already be dict or contain json_str
        if isinstance(raw_output, dict) and "json_str" in raw_output:
            detections = parse_yolo_output(raw_output["json_str"])
        else:
            detections = parse_yolo_output(raw_output)

        cropped_paths = []
        with Image.open(image_path) as img:
            for i, det in enumerate(detections):
                bbox = extract_bbox(det)
                if bbox is None:
                    continue

                x1, y1, x2, y2 = bbox
                if x2 <= x1 or y2 <= y1:
                    continue

                crop = img.crop((x1, y1, x2, y2))
                out_path = CROPPED_DIR / f"{image_path.stem}_obj_{i}.jpg"
                crop.save(out_path)
                cropped_paths.append(out_path)

        # Update object_paths.pkl
        object_paths_file = Path(OUTPUT_OBJECT_PATHS_FILE)
        existing_paths = load_pickle(object_paths_file, [])

        # Ensure existing_paths is a list
        if not isinstance(existing_paths, list):
            existing_paths = []

        # Convert absolute paths to relative paths starting with `cropped_objects/`
        updated_paths = existing_paths + [
            str(path.relative_to(CROPPED_DIR.parent)) for path in cropped_paths
        ]

        with open(object_paths_file, "wb") as f:
            pickle.dump(updated_paths, f)

        return cropped_paths

    except Exception as e:
        raise RuntimeError(f"YOLO-World-XL failed for {image_path}: {e}") from e


# =============================================================================
# Decision logic: what needs processing?
# =============================================================================


def analyze_needs(
    frame_path: Path,
    clip_embeddings: Dict[str, np.ndarray],
    yolo_embeddings: Dict[str, np.ndarray],
) -> Tuple[bool, bool]:
    """
    Decide whether this frame needs:
    - CLIP embedding (do_clip)
    - YOLO + object embeddings (do_yolo)
    """
    rel = str(frame_path.relative_to(FRAMES_DIR))

    if FORCE_REPROCESS:
        return True, True

    # --- CLIP needs to run if missing ---
    needs_clip = rel not in clip_embeddings

    # --- YOLO needs to run if crops missing or embeddings missing ---
    prefix = frame_path.stem + "_obj_"
    crop_paths = list(CROPPED_DIR.glob(f"{prefix}*.jpg"))

    # If no crops → need YOLO
    if len(crop_paths) == 0:
        return needs_clip, True

    # If ANY crop has no embedding → need YOLO
    for crop_path in crop_paths:
        obj_key = str(crop_path.relative_to(CROPPED_DIR))
        if obj_key not in yolo_embeddings:
            return needs_clip, True

    # If YOLO embeddings exist for this frame but count mismatch → need YOLO
    yolo_keys_for_frame = [
        k for k in yolo_embeddings.keys() if k.startswith(frame_path.stem + "_obj_")
    ]
    if len(yolo_keys_for_frame) != len(crop_paths):
        return needs_clip, True

    # Otherwise: YOLO is complete
    return needs_clip, False


# =============================================================================
# Worker for multithreading
# =============================================================================


def process_frame(
    path: Path,
    do_clip: bool,
    do_yolo: bool,
    clip_embeddings: Dict[str, np.ndarray],
    yolo_embeddings: Dict[str, np.ndarray],
):
    """Process one frame: CLIP for whole image and YOLO crops, but only as needed."""
    rel = str(path.relative_to(FRAMES_DIR))

    try:
        frame_emb = None
        obj_embs: Dict[str, np.ndarray] = {}

        # CLIP for full frame (only if requested)
        if do_clip:
            frame_emb = embed_clip(path)
        else:
            # Reuse existing frame embedding
            frame_emb = clip_embeddings.get(rel, None)

        # YOLO detection + crop embeddings (only if requested)
        if do_yolo:
            cropped_paths = detect_and_crop(path)

            for cpath in cropped_paths:
                obj_key = str(cpath.relative_to(CROPPED_DIR))

                # Reuse existing embedding if present and not forcing a rebuild
                if not FORCE_REPROCESS and obj_key in yolo_embeddings:
                    emb = yolo_embeddings[obj_key]
                else:
                    emb = embed_clip(cpath)

                obj_embs[obj_key] = emb

        return {
            "frame": rel,
            "frame_emb": frame_emb,
            "obj_embs": obj_embs,
            "error": None,
        }

    except Exception as e:
        return {"frame": rel, "frame_emb": None, "obj_embs": {}, "error": str(e)}


# =============================================================================
# Main
# =============================================================================


def main():
    print("=== Starting compute_embeddings.py ===")

    # Load existing progress
    clip_embeddings: Dict[str, np.ndarray] = load_pickle(
        OUTPUT_FRAME_EMBEDDINGS_FILE, {}
    )
    yolo_embeddings: Dict[str, np.ndarray] = load_pickle(
        OUTPUT_OBJECT_EMBEDDINGS_FILE, {}
    )

    # Load or initialize the output paths - these are now lists, not dictionaries
    existing_frame_paths: List[str] = load_pickle(OUTPUT_FRAME_PATHS_FILE, [])
    existing_object_paths: List[str] = load_pickle(OUTPUT_OBJECT_PATHS_FILE, [])

    # Gather all frame images
    image_paths = sorted(FRAMES_DIR.rglob("*.jpg"))

    # Decide what each frame actually needs
    tasks = []
    for p in image_paths:
        do_clip, do_yolo = analyze_needs(p, clip_embeddings, yolo_embeddings)
        if do_clip or do_yolo:
            tasks.append((p, do_clip, do_yolo))

    print(f"Found {len(tasks)} frames to process.")
    if not tasks:
        print("Nothing to do.")
        return

    if FORCE_REPROCESS:
        print("FORCE_REPROCESS is enabled. Rebuilding all embeddings.")

    start = time.time()
    total = len(tasks)

    print(f"Starting processing with {total} tasks...")
    print("Submitting tasks to ThreadPoolExecutor...")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                process_frame, p, do_clip, do_yolo, clip_embeddings, yolo_embeddings
            )
            for (p, do_clip, do_yolo) in tasks
        ]

        print(f"Submitted {len(futures)} futures to executor")
        print("Waiting for results...")

        for i, f in enumerate(as_completed(futures), start=1):
            result = f.result()

            if result["error"]:
                print(f"[ERROR] {result['frame']}: {result['error']}")
            else:
                rel = result["frame"]

                # Update CLIP frame embeddings
                if result["frame_emb"] is not None:
                    clip_embeddings[rel] = result["frame_emb"]

                # Update YOLO object embeddings
                for obj_rel, emb in result["obj_embs"].items():
                    yolo_embeddings[obj_rel] = emb

                # Note: Object and frame paths are now updated directly in detect_and_crop function

            # ==== LIVE PROGRESS METRICS ====
            num_clip = len(clip_embeddings)
            num_obj_embs = len(yolo_embeddings)
            print(
                f"  → CLIP embeddings so far: {num_clip} "
                f"| Object crops detected this frame: {len(result['obj_embs'])} "
                f"| Total object embeddings so far: {num_obj_embs}"
            )
            # ================================

            # ==== ETA CALCULATION ====
            elapsed = time.time() - start
            avg = elapsed / i
            remaining = avg * (total - i)
            print(f"Processed {i}/{total} frames. ETA: {remaining/60:.2f} min")
            # ==========================

            # ==== PERIODIC SAVE ====
            if i % 10 == 0 or i == total:
                with open(OUTPUT_FRAME_EMBEDDINGS_FILE, "wb") as f_out:
                    pickle.dump(clip_embeddings, f_out)

                with open(OUTPUT_OBJECT_EMBEDDINGS_FILE, "wb") as f_out:
                    pickle.dump(yolo_embeddings, f_out)

                # Note: Frame and object paths are now saved directly in detect_and_crop function

                # Debug: Log when saving progress
                print(
                    f"Saving progress to {OUTPUT_OBJECT_EMBEDDINGS_FILE} with {len(yolo_embeddings)} paths."
                )

                print("Progress saved.")
            # ========================

    print("\nAll embeddings completed.")

    # Separate paths for frames and objects
    frame_paths = []
    object_paths = []

    # Iterate through the embeddings and categorize paths
    for path in clip_embeddings.keys():
        if "cropped_objects" in path:
            object_paths.append(path)
        else:
            # This is a frame path - add output_frames/ prefix
            frame_path = f"output_frames/{path}"
            frame_paths.append(frame_path)

    # Save the paths separately
    with open(OUTPUT_FRAME_PATHS_FILE, "wb") as f:
        pickle.dump(frame_paths, f)

    with open(OUTPUT_OBJECT_PATHS_FILE, "wb") as f:
        pickle.dump(object_paths, f)

    # Debug: Log object paths being saved
    print(
        "Object paths being saved:", object_paths[:10]
    )  # Log first 10 object paths for verification

    # Debug: Log frame paths being saved
    print(
        "Frame paths being saved:", frame_paths[:10]
    )  # Log first 10 frame paths for verification


# def main():
#     # Load existing progress
#     clip_embeddings: Dict[str, np.ndarray] = load_pickle(OUTPUT_EMBEDDINGS_FILE, {})
#     yolo_embeddings: Dict[str, np.ndarray] = load_pickle(
#         OUTPUT_YOLO_EMBEDDINGS_FILE, {}
#     )

# # ===========================
# # DEBUG PRINTS — ADD HERE
# # ===========================
# print("=== DEBUG INFO ===")
# print("Total saved CLIP frame embeddings:", len(clip_embeddings))
# print("Total saved YOLO object embeddings:", len(yolo_embeddings))

# sample_clip = list(clip_embeddings.keys())[:5]
# print("Sample CLIP keys:", sample_clip)

# crop_files = list(CROPPED_DIR.glob("*.jpg"))
# print("Total crop images found:", len(crop_files))
# if crop_files:
#     print("Sample crop file:", crop_files[0].name)

# frame_files = list(FRAMES_DIR.rglob("*.jpg"))
# print("Total frame images found:", len(frame_files))
# if frame_files:
#     print("Sample frame file:", frame_files[0].name)

# print("===================")
# # ===========================


if __name__ == "__main__":
    main()
