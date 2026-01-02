# Scripts Directory Structure

## 📁 Directory Organization

### `pipeline/` - Integrated Video Processing Pipeline

**Purpose**: Complete end-to-end video processing system

#### Core Infrastructure

- **`state.py`** - Track video processing status through pipeline stages
- **`naming.py`** - Centralized naming conventions for all files/paths
- **`orchestrator.py`** - Pipeline coordinator that manages workflow
- **`cli.py`** - Command-line interface for easy usage
- **`__main__.py`** - Module entry point (enables `python -m scripts.pipeline`)

#### Pipeline Steps (`steps/`)

- **`base.py`** - Base class for all pipeline steps
- **`download.py`** - Download from YouTube/Drive/local
- **`extract_frames.py`** - Extract frames with OpenCV
- **`detect_objects.py`** - Detect objects with YOLO-World-XL
- **`compute_embeddings.py`** - Compute CLIP embeddings
- **`upload.py`** - Upload all artifacts to S3

**Usage Example**:

```python
from scripts.pipeline import PipelineState, VideoStatus, NamingConvention, Pipeline

# Create and run pipeline
pipeline = Pipeline()
pipeline.process_video(
    video_name="my_video",
    source_type="youtube",
    source_url="https://..."
)

# Use consistent naming
frame_path = NamingConvention.frame_local_path("my_video", 42)
# -> data/frames/my_video/frame_00042.jpg
```

## Quick Start

### Process a Video

```bash
# YouTube
python -m scripts.pipeline process "my_video" --source youtube --url "https://youtube.com/watch?v=..."

# Google Drive
python -m scripts.pipeline process "my_video" --source drive --url "https://drive.google.com/file/d/..."

# Local file
python -m scripts.pipeline process "my_video" --source local --url "path/to/video.mp4"
```

This single command:

1. Downloads the video
2. Extracts frames (configurable FPS)
3. Detects objects with YOLO
4. Computes CLIP embeddings
5. Uploads everything to S3

### Check Status

```bash
# List all videos
python -m scripts.pipeline list

# Check specific video
python -m scripts.pipeline status "my_video"

# Resume processing
python -m scripts.pipeline resume "my_video"

# Validate artifacts
python -m scripts.pipeline validate "my_video"
```

## Naming Conventions

All files follow standardized naming:

**Videos**: `{video_name}.mp4`

- Example: `my_video.mp4`

**Frames**: `frame_{index:05d}.jpg`

- Example: `frame_00042.jpg`
- Location: `data/frames/{video_name}/`

**Objects**: `frame_{frame_index:05d}_obj_{object_index:03d}.jpg`

- Example: `frame_00042_obj_003.jpg`
- Location: `data/objects/{video_name}/`

**Embeddings**:

- `frame_embeddings.pkl` / `frame_paths.pkl`
- `object_embeddings.pkl` / `object_paths.pkl`
- Location: `data/embeddings/`

## State Management

Each video's processing state is tracked in `data/pipeline_state/{video_name}.json`:

```json
{
  "video_name": "my_video",
  "status": "completed",
  "source_type": "youtube",
  "source_url": "https://...",
  "created_at": "2025-12-26T17:30:00",
  "updated_at": "2025-12-26T18:45:00",
  "completed_at": "2025-12-26T18:45:00",
  "frame_count": 240,
  "object_count": 1523,
  "steps_completed": [
    "download",
    "extract_frames",
    "detect_objects",
    "compute_embeddings",
    "upload"
  ]
}
```

This enables:

- Resume interrupted processing
- Track what's been processed
- Query video status
- Identify failed videos
