# Preprocessing Scripts

This directory contains scripts for processing videos into searchable embeddings using the new data structure.

## 📁 Data Structure

All data is stored in the `data/` directory with the following structure:

```
data/
├── videos/          # Original video files
├── frames/          # Extracted frames organized by video
│   ├── video_1/
│   ├── video_2/
│   └── ...
├── objects/         # Cropped objects detected by YOLO
└── embeddings/      # Local cache (main storage is S3)
```

## 🔄 Processing Workflow

### Option 1: Complete Workflow (Recommended)

```bash
# Run the complete processing pipeline
python process_workflow.py
```

### Option 2: Step-by-Step Processing

#### 1. Download Videos

```bash
# Download from URLs
python download_videos.py https://youtube.com/watch?v=...

# Or edit the script to add default URLs
python download_videos.py
```

#### 2. Extract Frames

```bash
# Extract frames from all videos in data/videos/
python extract_frames.py

# Extract from specific video
python extract_frames.py --video "my_video.mp4"

# Extract at different frame rate
python extract_frames.py --fps 2
```

#### 3. Detect and Crop Objects

```bash
# Process all frames to detect and crop objects
python process_objects_yolo.py
```

#### 4. Compute CLIP Embeddings

```bash
# Compute embeddings for all frames and objects
python compute_clip_embeddings.py

# Compute only frame embeddings
python compute_clip_embeddings.py --frames-only

# Compute only object embeddings
python compute_clip_embeddings.py --objects-only

# Force recompute all embeddings
python compute_clip_embeddings.py --force
```

## 📋 Script Descriptions

### Core Processing Scripts

#### `process_objects_yolo.py` ⭐

- **Purpose**: Detects objects in frames using YOLO-World-XL and crops them
- **Input**: Frame images from `data/frames/`
- **Output**: Cropped object images in `data/objects/`
- **Features**:
  - Detects configurable object classes (person, car, building, etc.)
  - Saves cropped objects with descriptive filenames
  - Uploads results to S3 storage

#### `compute_clip_embeddings.py` ⭐

- **Purpose**: Computes CLIP embeddings for any JPG images
- **Input**: Images from `data/frames/` and `data/objects/`
- **Output**: Embeddings stored in S3 (`embeddings/*.pkl`)
- **Features**:
  - Processes both frames and objects
  - Incremental processing (resumes from where it left off)
  - Flexible command-line options
  - Automatic S3 upload

### Utility Scripts

#### `download_videos.py`

- **Purpose**: Downloads videos from YouTube/web URLs
- **Output**: Video files in `data/videos/`
- **Usage**: Supports both command-line URLs and default URLs

#### `extract_frames.py`

- **Purpose**: Extracts frames from videos
- **Input**: Videos from `data/videos/`
- **Output**: Frame images in `data/frames/video_*/`
- **Features**: Configurable frame extraction rate (FPS)

#### `process_workflow.py`

- **Purpose**: Orchestrates the complete processing pipeline
- **Features**: Runs all steps in sequence with error handling

### Legacy Scripts (Updated)

#### `compute_embeddings.py`

- **Status**: Updated to use `data/` structure (legacy combined script)
- **Note**: Use the new separate scripts instead

#### `compute_embeddings_s3.py`

- **Status**: Outdated S3 integration
- **Note**: Use the new scripts with integrated S3 support

#### `inspect_embeddings.py`

- **Purpose**: Debug/analyze existing embeddings
- **Usage**: Useful for troubleshooting embedding files

## 🔧 Configuration

### Environment Variables

Ensure your `.env` file contains:

```
REPLICATE_API_TOKEN=your_token_here
STORJ_BUCKET_NAME=videos
STORJ_ACCESS_KEY=your_key
STORJ_SECRET_KEY=your_secret
STORJ_ENDPOINT_URL=https://gateway.storjshare.io
```

### YOLO Classes

Edit `process_objects_yolo.py` to customize detected object classes:

```python
YOLO_CLASSES = ["person", "car", "building", "bicycle", "motorcycle"]
```

## 📊 Expected Results

After running the complete workflow, you should have:

- ✅ Videos stored in `data/videos/`
- ✅ Extracted frames in `data/frames/video_*/`
- ✅ Cropped objects in `data/objects/`
- ✅ Embeddings uploaded to S3 storage
- ✅ Ready-to-use search application

## 🚀 Next Steps

After processing is complete:

1. Start the Streamlit application: `python main.py`
2. The search interface will load embeddings from S3
3. Search functionality will work with your processed data

## 🔍 Troubleshooting

- **No objects detected**: Check YOLO classes configuration
- **Embeddings not loading**: Verify S3 credentials and bucket name
- **Out of memory**: Process in smaller batches or reduce concurrent operations
- **API errors**: Check Replicate API token and rate limits
