# Scripts Directory Structure

Reorganized for clarity and maintainability. All scripts follow standardized naming conventions and state management.

## 📁 Directory Organization

### `pipeline/` - Core Pipeline Infrastructure
**Purpose**: Standardized video processing pipeline with state management

- **`state.py`** - Track video processing status through pipeline stages
- **`naming.py`** - Centralized naming conventions for all files/paths
- **`__init__.py`** - Module exports

**Usage Example**:
```python
from scripts.pipeline import PipelineState, VideoStatus, NamingConvention

# Create state for new video
state = PipelineState("my_video", source_type="youtube", source_url="https://...")
state.save()

# Update status as processing progresses
state.update_status(VideoStatus.DOWNLOADING)
state.mark_step_completed("download")
state.save()

# Use consistent naming
frame_path = NamingConvention.frame_local_path("my_video", 42)
# -> data/frames/my_video/frame_00042.jpg
```

### `preprocessing/` - Video Processing Steps
**Purpose**: Individual processing steps (download, extract, detect, embed)

**Active Scripts**:
- `download_videos.py` - Download from YouTube (yt-dlp)
- `download_from_drive.py` - Download from Google Drive (gdown)
- `extract_frames.py` - Extract frames from video (OpenCV)
- `process_objects_yolo.py` - Detect objects with YOLO-World-XL
- `compute_clip_embeddings.py` - Compute CLIP embeddings
- `process_new_video.py` - Complete pipeline for one video (to be refactored)
- `process_workflow.py` - Batch processor (incomplete, to be refactored)

**To Be Refactored**: These scripts will be updated to use the new state management and naming conventions.

### `tools/` - Validation & Debugging Tools
**Purpose**: One-off scripts for validation, debugging, and maintenance

- `validate_video_embeddings.py` - Validate embeddings for a specific video
- `check_s3_embeddings.py` - Check what videos exist in S3
- `final_validation.py` - Final validation after upload
- `check_jonathan_media.py` - Check media files for jonathan video
- `upload_jonathan_embeddings.py` - One-off upload for jonathan video

**Usage**: Run directly when needed for debugging/validation.

### `tests/` - Testing Scripts
**Purpose**: Scripts for testing individual components

- `test_yolo_single_frame.py` - Test YOLO on a single frame
- `test_aws_cli.py` - Test AWS CLI configuration
- `test_s3.py` - Test S3 connectivity with boto3
- `test_simple_s3.py` - Simple S3 test

### `legacy/` - Deprecated Scripts
**Purpose**: Old scripts kept for reference, no longer actively used

Contains old migration scripts, duplicate upload utilities, and path-fixing band-aids that are replaced by the new standardized approach.

### Root Level Scripts
- `generate_embeddings.py` - Generate embeddings (to be refactored)
- `upload_all_data.py` - Unified upload script (to be refactored)

## 🎯 Migration Plan

### Phase 1: Infrastructure ✅ COMPLETE
- [x] Create state management (`state.py`)
- [x] Create naming conventions (`naming.py`)
- [x] Organize scripts into directories

### Phase 2: Refactor Preprocessing Scripts (IN PROGRESS)
- [ ] Update all preprocessing scripts to use `NamingConvention`
- [ ] Update all preprocessing scripts to use `PipelineState`
- [ ] Create CLI interface for easy pipeline execution
- [ ] Consolidate `process_new_video.py` into modular steps

### Phase 3: Create Unified CLI (TODO)
```bash
# Future interface
python -m scripts.pipeline process VIDEO_NAME --source youtube URL
python -m scripts.pipeline process VIDEO_NAME --source drive URL
python -m scripts.pipeline process VIDEO_NAME --source local PATH
```

## 📝 Naming Conventions

All files now follow standardized naming:

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

## 🔧 State Management

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
  "steps_completed": ["download", "extract_frames", "detect_objects", "compute_embeddings", "upload"]
}
```

This enables:
- Resume interrupted processing
- Track what's been processed
- Query video status
- Identify failed videos

## 🚀 Quick Start

To start using the new infrastructure in your scripts:

```python
from scripts.pipeline import PipelineState, VideoStatus, NamingConvention

# 1. Sanitize video name
video_name = NamingConvention.sanitize_video_name("My Cool Video!")
# -> "my_cool_video"

# 2. Create/load state
state = PipelineState.load(video_name) or PipelineState(video_name)

# 3. Use consistent paths
video_path = NamingConvention.video_local_path(video_name)
frames_dir = NamingConvention.frames_dir_local(video_name)

# 4. Update state as you process
state.update_status(VideoStatus.EXTRACTING_FRAMES)
state.save()

# 5. Mark steps complete
state.mark_step_completed("extract_frames")
state.frame_count = 240
state.save()
```
