# Integrated Pipeline - Quick Start Guide

## 🎯 What You Can Do Now

Process any video through the complete pipeline with a single command!

## 📋 Prerequisites

1. **Environment variables** in `.env`:
   ```
   REPLICATE_API_TOKEN=your_token_here
   STORAGE_MODE=s3-only  # or local-only, hybrid, auto
   ```

2. **S3 credentials** (if using S3 storage):
   - Configure in `.env` or AWS credentials file

## 🚀 Quick Start

### Process a YouTube Video

```bash
python -m scripts.pipeline process "my_video" \
    --source youtube \
    --url "https://youtube.com/watch?v=..."
```

### Process a Google Drive Video

```bash
python -m scripts.pipeline process "my_video" \
    --source drive \
    --url "https://drive.google.com/file/d/FILE_ID/view"
```

### Process a Local Video

```bash
python -m scripts.pipeline process "my_video" \
    --source local \
    --url "path/to/video.mp4"
```

## 🔧 Advanced Options

### Custom Frame Rate

```bash
python -m scripts.pipeline process "my_video" \
    --source youtube \
    --url "https://..." \
    --fps 2  # Extract 2 frames per second
```

### Custom YOLO Classes

```bash
python -m scripts.pipeline process "my_video" \
    --source youtube \
    --url "https://..." \
    --yolo-classes "person,gun,car,building"
```

### Run Specific Steps Only

```bash
# Only download and extract frames
python -m scripts.pipeline process "my_video" \
    --source youtube \
    --url "https://..." \
    --steps "download,extract_frames"
```

### Force Reprocessing

```bash
# Reprocess even if already completed
python -m scripts.pipeline process "my_video" \
    --source youtube \
    --url "https://..." \
    --force
```

## 📊 Check Status

### List All Videos

```bash
python -m scripts.pipeline list
```

Output:
```
Found 3 video(s):

Video Name                     Status               Frames   Objects
----------------------------------------------------------------------
✅ my_video                    completed            240      1500
⏳ another_video               extracting_frames    120      0
✗ failed_video                 failed               0        0
```

### Check Specific Video

```bash
python -m scripts.pipeline status "my_video"
```

Output:
```
Video: my_video
Status: completed
Source: youtube - https://youtube.com/watch?v=...
Created: 2025-12-26T18:00:00
Updated: 2025-12-26T18:45:00
Frames: 240
Objects: 1500
Steps completed: download, extract_frames, detect_objects, compute_embeddings, upload
```

### Filter by Status

```bash
python -m scripts.pipeline list --status completed
python -m scripts.pipeline list --status failed
python -m scripts.pipeline list --status pending
```

## 🔄 Resume Processing

If processing was interrupted, resume from where it left off:

```bash
python -m scripts.pipeline resume "my_video"
```

The pipeline automatically:
- ✅ Skips completed steps
- ✅ Continues from last successful step
- ✅ Preserves all progress

## ✅ Validate Artifacts

Check if all artifacts are properly generated:

```bash
python -m scripts.pipeline validate "my_video"
```

Output:
```
Validating: my_video
Status: completed
  ✓ download: valid
  ✓ extract_frames: valid
  ✓ detect_objects: valid
  ✓ compute_embeddings: valid
  ✓ upload: valid

✅ All artifacts valid for my_video
```

## 🏃 Complete Workflow Example

Here's a complete example of processing a new video:

```bash
# 1. Process the video
python -m scripts.pipeline process "protest_video_2024" \
    --source youtube \
    --url "https://youtube.com/watch?v=abc123" \
    --fps 1 \
    --yolo-classes "person,gun,backpack,hat,building"

# 2. Check status
python -m scripts.pipeline status "protest_video_2024"

# 3. Validate results
python -m scripts.pipeline validate "protest_video_2024"

# 4. List all videos
python -m scripts.pipeline list
```

## 📂 What Gets Created

For a video named `my_video`, the pipeline creates:

### Local Files
```
data/
├── videos/
│   └── my_video.mp4                          # Original video
├── frames/
│   └── my_video/
│       ├── frame_00000.jpg                   # Extracted frames
│       ├── frame_00001.jpg
│       └── ...
├── objects/
│   └── my_video/
│       ├── frame_00000_obj_000.jpg           # Detected objects
│       ├── frame_00000_obj_001.jpg
│       └── ...
├── embeddings/
│   ├── frame_embeddings.pkl                  # CLIP embeddings
│   ├── frame_paths.pkl                       # Frame paths
│   ├── object_embeddings.pkl                 # Object embeddings
│   └── object_paths.pkl                      # Object paths
└── pipeline_state/
    └── my_video.json                         # Processing state
```

### S3 Files (if STORAGE_MODE includes S3)
```
s3://your-bucket/
├── videos/
│   └── my_video.mp4
├── frames/
│   └── my_video/
│       ├── frame_00000.jpg
│       └── ...
├── objects/
│   └── my_video/
│       ├── frame_00000_obj_000.jpg
│       └── ...
└── embeddings/
    ├── frame_embeddings.pkl
    ├── frame_paths.pkl
    ├── object_embeddings.pkl
    └── object_paths.pkl
```

## 🔍 Pipeline Steps Explained

The pipeline runs these steps in order:

1. **Download** - Get video from source (YouTube/Drive/local)
2. **Extract Frames** - Split video into frames at specified FPS
3. **Detect Objects** - Use YOLO to find and crop objects
4. **Compute Embeddings** - Generate CLIP embeddings for search
5. **Upload** - Store everything to S3 (if configured)

Each step:
- ✅ Validates input before running
- ✅ Validates output after completing
- ✅ Can be skipped if already completed
- ✅ Can be run independently
- ✅ Saves progress to state file

## ⚠️ Troubleshooting

### "REPLICATE_API_TOKEN not set"
Add to `.env`:
```
REPLICATE_API_TOKEN=your_token_here
```

### "Video file not created"
Check:
- YouTube URL is valid
- Google Drive file is shared publicly
- Local path exists

### Processing is slow
- YOLO detection: ~1-2 seconds per frame (API call)
- CLIP embeddings: ~0.5 seconds per image (API call)
- For 240 frames + 1500 objects: expect 30-45 minutes total

### Resume after failure
```bash
python -m scripts.pipeline resume "my_video"
```

### Force complete reprocessing
```bash
python -m scripts.pipeline process "my_video" \
    --source youtube \
    --url "https://..." \
    --force
```

## 💡 Tips

1. **Test with short videos first** - YOLO/CLIP processing can take time
2. **Use meaningful video names** - Easier to manage multiple videos
3. **Check status regularly** - Monitor progress for long videos
4. **Validate after completion** - Ensure all artifacts are correct
5. **Use --steps for debugging** - Test individual steps independently

## 📚 Next Steps

- Check [scripts/README.md](README.md) for detailed documentation
- See [PHASE1_COMPLETE.md](../PHASE1_COMPLETE.md) for architecture details
- Review [SCRIPTS_ANALYSIS.md](../SCRIPTS_ANALYSIS.md) for design decisions
