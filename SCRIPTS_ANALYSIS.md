# Scripts Analysis & Refactoring Plan

## 📊 Current State Analysis

### Directory Structure

```
scripts/
├── preprocessing/          # Video processing pipeline
├── data_migration/         # S3 upload utilities
├── utils/                  # Testing utilities
└── root level/            # Validation & one-off scripts
```

---

## 📁 1. Preprocessing Scripts (`scripts/preprocessing/`)

### Purpose
Process videos through the complete pipeline: download → frames → objects → embeddings

### Current Scripts

#### ✅ **process_new_video.py** (291 lines)
- **Purpose**: Complete pipeline for ONE new video
- **Features**: 
  - Downloads from Drive/YouTube/local
  - Extracts frames
  - Detects objects with YOLO
  - Computes embeddings
  - Uploads to S3
- **Issues**:
  - ❌ Hardcoded paths and subprocess calls
  - ❌ No resume capability if interrupted
  - ❌ No validation of intermediate steps
  - ❌ Mixed concerns (orchestration + implementation)

#### ⚠️ **process_workflow.py** (134 lines)
- **Purpose**: Batch process multiple videos
- **Issues**:
  - ❌ Incomplete implementation (imports commented out)
  - ❌ Doesn't handle individual video tracking
  - ❌ No way to process specific videos
  - ❌ No status reporting

#### ✅ **download_videos.py** (90 lines)
- **Purpose**: Download from YouTube using yt-dlp
- **Good**: Works well for YouTube
- **Issues**:
  - ❌ Only handles YouTube (despite name)
  - ❌ No progress tracking
  - ❌ No error recovery

#### ⚠️ **download_from_drive.py** (113 lines)
- **Purpose**: Download from Google Drive
- **Issues**:
  - ❌ Not integrated with pipeline
  - ❌ Requires manual file ID extraction
  - ❌ No batch download support

#### ✅ **extract_frames.py** (126 lines)
- **Purpose**: Extract frames from videos using OpenCV
- **Good**: Simple, works well
- **Issues**:
  - ⚠️ Inconsistent naming: saves as `frame_00000.jpg` but expects `video_X_frame_00000.jpg` elsewhere
  - ❌ No video metadata preservation
  - ❌ Processes all or one, no selective processing

#### ⚠️ **process_objects_yolo.py** (355 lines)
- **Purpose**: Detect objects with YOLO-World-XL
- **Issues**:
  - ❌ Hardcoded `TARGET_VIDEOS` (currently only "video_reconstrucción_jonathan")
  - ❌ Very slow (API call per frame)
  - ❌ No batch processing optimization
  - ❌ Mixed storage logic (local + S3)
  - ❌ Poor error handling for API failures

#### ⚠️ **compute_clip_embeddings.py** (389 lines)
- **Purpose**: Compute CLIP embeddings for frames and objects
- **Good**: Incremental processing, can resume
- **Issues**:
  - ❌ Complex dict vs array logic
  - ❌ Inconsistent path handling
  - ❌ No batch optimization for API calls
  - ❌ Mixed local/S3 storage logic

#### ❌ **test_yolo_single_frame.py**
- **Purpose**: Test YOLO on single frame
- **Status**: Debugging script, should not be in preprocessing/

#### ⚠️ **organize_objects.py** & **rename_objects.py**
- **Purpose**: Fix naming/organization issues
- **Issue**: Band-aid solutions for naming inconsistencies

---

## 📁 2. Data Migration Scripts (`scripts/data_migration/`)

### Purpose
Upload data to S3 storage

### Current Scripts

#### ⚠️ **upload_frames_to_s3.py** (100 lines)
- **Issues**:
  - ❌ Uses old path structure (`app/output_frames`)
  - ❌ Custom S3 client instead of storage manager
  - ❌ No resume capability

#### ⚠️ **upload_objects_to_s3.py**
- Same issues as upload_frames_to_s3.py

#### ⚠️ **migrate_to_s3.py**, **migrate_smart.py**, **migrate_objects.py**, **migrate_embeddings.py**
- **Purpose**: Various S3 migration utilities
- **Issues**:
  - ❌ Duplicate functionality
  - ❌ Inconsistent approaches
  - ❌ Should be consolidated

#### ⚠️ **upload_video.py**
- **Purpose**: Upload original video files
- **Issue**: Not integrated with pipeline

---

## 📁 3. Root Level Scripts

### Validation Scripts (Recently Added) ✅
- `validate_video_embeddings.py`
- `check_s3_embeddings.py`
- `final_validation.py`
- `check_jonathan_media.py`

**Good**: These work well for debugging

### Upload Scripts
- `upload_all_data.py` - Most comprehensive
- `upload_embeddings_simple.py`
- `upload_embeddings_to_s3.py`
- `upload_jonathan_embeddings.py`

**Issues**: Too many similar scripts, redundant

### Path Fixing Scripts
- `fix_object_paths.py`
- `verify_paths.py`
- `check_frame_paths.py`

**Issue**: Symptoms of inconsistent path handling

---

## 🔴 Major Problems Identified

### 1. **Naming Inconsistencies**
- Frame naming: `frame_00000.jpg` vs `video_X_frame_00000.jpg`
- Object naming: Multiple formats throughout codebase
- Path formats: `frames/video_X/` vs `video_X/` inconsistencies

### 2. **Fragmented Pipeline**
- No single entry point for complete workflow
- Manual intervention needed between steps
- No state tracking (can't resume easily)
- Process one video OR all videos, no selective processing

### 3. **Duplicate Functionality**
- Multiple upload scripts doing similar things
- Multiple migration scripts
- Multiple path-fixing utilities

### 4. **Poor Error Handling**
- API failures crash entire pipeline
- No retry logic
- No validation between steps
- No rollback capability

### 5. **Hard to Use**
- Must edit code to change target videos
- No clear "process this video" command
- Confusing array of script options
- No progress visibility for long operations

### 6. **Performance Issues**
- No batch API calls (YOLO and CLIP)
- Sequential processing (could parallelize)
- Redundant S3 uploads (no skip-if-exists logic in some scripts)

### 7. **Storage Confusion**
- Mixed local/S3 logic throughout
- Inconsistent use of storage manager
- Some scripts bypass storage abstraction

---

## ✅ Proposed Refactoring Plan

### Phase 1: Core Infrastructure (Week 1)

#### 1.1 Create Pipeline State Manager
```python
class PipelineState:
    """Track processing state for each video"""
    - video_name
    - status (downloaded, frames_extracted, objects_detected, embeddings_computed, uploaded)
    - metadata (frame_count, object_count, errors)
    - timestamps
    - save/load from JSON
```

#### 1.2 Standardize Naming Convention
```python
class NamingConvention:
    """Consistent naming across all components"""
    - Videos: {video_name}.mp4
    - Frames: frames/{video_name}/frame_{index:05d}.jpg
    - Objects: objects/{video_name}/frame_{frame_index:05d}_obj_{obj_index}.jpg
    - Embeddings: embeddings/{type}_embeddings.pkl
```

#### 1.3 Create Base Pipeline Step
```python
class PipelineStep:
    """Base class for all pipeline steps"""
    def validate_input() -> bool
    def execute() -> bool
    def validate_output() -> bool
    def rollback() -> bool
    def get_progress() -> dict
```

### Phase 2: Refactored Pipeline (Week 2)

#### 2.1 New Structure
```
scripts/
├── pipeline/
│   ├── __init__.py
│   ├── cli.py                    # Main entry point
│   ├── orchestrator.py           # Pipeline coordinator
│   ├── state.py                  # State management
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── download.py           # Download from YouTube/Drive/Local
│   │   ├── extract_frames.py    # Frame extraction
│   │   ├── detect_objects.py    # YOLO detection
│   │   ├── compute_embeddings.py # CLIP embeddings
│   │   └── upload.py             # Upload to S3
│   └── utils/
│       ├── naming.py             # Naming conventions
│       ├── progress.py           # Progress tracking
│       └── validation.py         # Validation utilities
├── tools/                        # Stand-alone utilities
│   ├── validate_video.py
│   ├── check_s3.py
│   ├── inspect_embeddings.py
│   └── repair_paths.py
└── legacy/                       # Old scripts (for reference)
```

#### 2.2 CLI Interface
```bash
# Process new video (complete pipeline)
python -m scripts.pipeline process VIDEO_NAME --source youtube URL
python -m scripts.pipeline process VIDEO_NAME --source drive URL
python -m scripts.pipeline process VIDEO_NAME --source local PATH

# Process specific steps
python -m scripts.pipeline extract-frames VIDEO_NAME
python -m scripts.pipeline detect-objects VIDEO_NAME
python -m scripts.pipeline compute-embeddings VIDEO_NAME

# Batch operations
python -m scripts.pipeline process --all              # Process all videos
python -m scripts.pipeline process --pending          # Process incomplete videos
python -m scripts.pipeline process VIDEO1 VIDEO2 VIDEO3

# Status and validation
python -m scripts.pipeline status VIDEO_NAME
python -m scripts.pipeline validate VIDEO_NAME
python -m scripts.pipeline list

# Resume interrupted processing
python -m scripts.pipeline resume VIDEO_NAME
```

### Phase 3: Optimizations (Week 3)

#### 3.1 Batch Processing
- Batch CLIP embeddings (compute multiple at once)
- Parallel frame extraction
- Concurrent S3 uploads

#### 3.2 Smart Caching
- Skip already-processed frames
- Resume from interruption points
- Incremental uploads

#### 3.3 Better Error Handling
- Retry logic with exponential backoff
- Partial success handling
- Detailed error logging

### Phase 4: Testing & Documentation (Week 4)

#### 4.1 Tests
- Unit tests for each step
- Integration tests for full pipeline
- Mock API calls for testing

#### 4.2 Documentation
- API documentation
- User guide with examples
- Troubleshooting guide

---

## 🎯 Immediate Quick Wins

### 1. Create Unified CLI (1 day)
Single entry point: `python -m scripts.pipeline`

### 2. Fix Naming Consistency (1 day)
Standardize all path/file naming

### 3. Add State Tracking (2 days)
JSON file tracking video processing status

### 4. Consolidate Upload Scripts (1 day)
One script to rule them all

### 5. Add Progress Bars (1 day)
tqdm for all long operations

---

## 📋 Migration Strategy

### Step 1: Create New Structure (Don't break existing)
- Build new pipeline/ directory
- Keep old scripts working

### Step 2: Test New Pipeline
- Process one test video end-to-end
- Compare outputs with old scripts
- Fix any issues

### Step 3: Migrate Existing Videos
- Process any pending videos with new pipeline
- Validate results

### Step 4: Deprecate Old Scripts
- Move to legacy/
- Update documentation

---

## 💡 Key Design Principles

1. **Single Responsibility**: Each script does ONE thing well
2. **Fail Fast**: Validate early, fail with clear errors
3. **Resume-able**: Always able to continue from interruption
4. **Observable**: Clear progress and status reporting
5. **Testable**: Mock external dependencies
6. **Configurable**: Easy to adjust parameters
7. **Documented**: Clear usage examples

---

## 🚀 Implementation Priority

**P0 (Must Have - Week 1)**
- [ ] Pipeline state management
- [ ] Naming convention standardization
- [ ] Basic CLI interface
- [ ] Unified upload script

**P1 (Should Have - Week 2)**
- [ ] Complete pipeline orchestrator
- [ ] All pipeline steps as classes
- [ ] Error handling & retry logic
- [ ] Progress tracking

**P2 (Nice to Have - Week 3)**
- [ ] Batch processing optimizations
- [ ] Parallel processing
- [ ] Smart resume
- [ ] Performance monitoring

**P3 (Future)**
- [ ] Web UI for pipeline management
- [ ] Automated video discovery
- [ ] Quality metrics tracking
- [ ] Cost optimization

---

## 📝 Next Steps

1. **Review this analysis** with team
2. **Prioritize** features based on pain points
3. **Create** detailed technical specs for P0 items
4. **Implement** in phases with testing
5. **Document** as we go
6. **Deprecate** old scripts gradually

Would you like me to start implementing any of these improvements?
