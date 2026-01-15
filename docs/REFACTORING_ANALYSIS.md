# Code Cleanup & Refactoring Analysis

## 🗑️ Files to DELETE (One-Time Scripts)

### Backend Root Directory Scripts

1. **`app.py`** ❌ DELETE

   - Old Streamlit entry point (no longer used)
   - We now use FastAPI (`src/api/main.py`)

2. **`migrate_to_cloud.py`** ❌ DELETE

   - One-time script to migrate local Qdrant to cloud
   - Migration is complete

3. **`clear_qdrant_duplicates.py`** ❌ DELETE

   - One-time cleanup script for duplicates
   - No longer needed

4. **`create_bbox_metadata.py`** ❌ DELETE

   - One-time script to retroactively add bbox metadata
   - All new videos now include this automatically

5. **`reindex_with_bbox.py`** ❌ DELETE

   - One-time reindexing script
   - No longer needed

6. **`update_object_timestamps.py`** ❌ DELETE

   - One-time script to add timestamps to existing objects
   - All new objects now include timestamps

7. **`recompute_embeddings.py`** ❌ DELETE

   - One-time recomputation script
   - Use the pipeline CLI instead: `python -m scripts.pipeline process`

8. **`start_server.sh`** ❌ DELETE
   - Replaced by `dev-start.sh`

### Log Files

9. **`bbox_creation.log`** ❌ DELETE
10. **`bbox_creation2.log`** ❌ DELETE
11. **`reindex.log`** ❌ DELETE
12. **`reindex2.log`** ❌ DELETE

---

## 📁 Directory Structure Issues

### Current Issues:

- Too many scripts at root level (should be in `scripts/`)
- Log files committed to git (should be in `.gitignore`)
- Multiple entry points confusing

### Recommended Structure:

```
archive-filter_backend/
├── src/                    # Core application code
│   ├── api/               # FastAPI routes
│   ├── core/              # Business logic
│   ├── storage/           # Storage backends
│   └── config/            # Configuration
├── scripts/               # Pipeline & utilities
│   ├── pipeline/          # Video processing pipeline
│   └── maintenance/       # NEW: One-time maintenance scripts (archived)
├── tests/                 # Unit tests
├── docs/                  # Documentation
├── data/                  # Local data (gitignored)
├── notebooks/             # Jupyter notebooks
├── dev-start.sh           # Development startup
└── pyproject.toml         # Dependencies
```

---

## 🔄 Code Duplication Issues

### 1. **Replicate Client Initialization** (HIGH PRIORITY)

**Duplicated in:**

- `src/core/search.py` (lines 23-40)
- `scripts/pipeline/steps/compute_embeddings.py` (lines 66-72)

**Problem:**

- Same Replicate client setup logic in two places
- Error handling inconsistent

**Solution:**
Move to a shared utility:

```python
# src/core/embeddings/client.py
def get_replicate_client():
    """Centralized Replicate client creation"""
    # Single source of truth
```

### 2. **Embedding Computation Logic** (HIGH PRIORITY)

**Duplicated between:**

- `ComputeEmbeddingsStep` (pipeline step) - For batch processing
- `SearchEngine.compute_text_embedding()` - For query embeddings
- `SearchEngine.compute_image_embedding()` - For image queries

**Problem:**

- 3 different implementations of embedding computation
- Retry logic only in pipeline, not in search
- Inconsistent error handling

**Solution:**
Create unified embedding service:

```python
# src/core/embeddings/service.py
class EmbeddingService:
    def compute_text_embedding(self, text: str) -> np.ndarray
    def compute_image_embedding(self, image_path: Path) -> np.ndarray
    def compute_batch_embeddings(self, items: List) -> List[np.ndarray]
```

### 3. **Path/Naming Logic**

**Good!** ✅ Already centralized in `NamingConvention` class

- No duplication found

### 4. **Qdrant Operations**

**Partially duplicated:**

- `QdrantStorage` class (good abstraction)
- Some direct Qdrant client calls in scripts

**Solution:**

- Always use `QdrantStorage` class
- Remove direct client usage

### 5. **State Management**

**Good!** ✅ `PipelineState` class handles all state

- Well encapsulated

### 6. **FPS Calculation** (MINOR)

**Duplicated in:**

- `update_object_timestamps.py` (lines 22-30)
- `scripts/pipeline/steps/extract_frames.py`

**Solution:**
Add to `NamingConvention` or create `VideoUtils` class

---

## 🏗️ Architecture Improvements

### 1. **Separate Concerns** (MEDIUM PRIORITY)

**Current Issue:**
`SearchEngine` does too much:

- Manages embeddings
- Computes embeddings
- Performs searches
- Handles Replicate client

**Recommended Split:**

```
src/core/
├── embeddings/
│   ├── __init__.py
│   ├── client.py          # Replicate client management
│   ├── service.py         # Embedding computation
│   └── manager.py         # Embeddings storage/retrieval
└── search/
    ├── __init__.py
    └── engine.py          # Pure search logic
```

### 2. **Configuration Management** (LOW PRIORITY)

**Current:** Environment variables scattered
**Better:** Centralized config validation at startup

### 3. **Error Handling** (MEDIUM PRIORITY)

**Current:** Inconsistent error handling
**Better:**

- Custom exception hierarchy
- Consistent error responses
- Better logging

---

## 📊 Code Metrics

### Current Stats:

- **Total Python files**: ~40
- **Scripts at root**: 8 (should be 1-2)
- **Duplicated functions**: ~5 significant ones
- **Lines of code**: ~6,000

### After Cleanup:

- **Remove**: ~800 lines (one-time scripts)
- **Consolidate**: ~300 lines (duplicates)
- **Net reduction**: ~15-20% cleaner codebase

---

## 🎯 Priority Refactoring Plan

### Phase 1: Quick Wins (1-2 hours)

1. ✅ Delete one-time scripts
2. ✅ Remove log files
3. ✅ Update `.gitignore`
4. ✅ Create `scripts/maintenance/` archive folder

### Phase 2: Code Consolidation (2-3 hours)

1. Create `src/core/embeddings/` module
2. Consolidate Replicate client
3. Unified embedding computation
4. Remove duplicated FPS logic

### Phase 3: Architecture Improvements (4-6 hours)

1. Split `SearchEngine` into focused modules
2. Centralize configuration
3. Add custom exceptions
4. Improve error handling

---

## 🧪 Testing Recommendations

**Currently missing:**

- Tests for most functionality
- Integration tests
- API tests

**Recommended additions:**

```
tests/
├── unit/
│   ├── test_embeddings.py
│   ├── test_search.py
│   └── test_storage.py
├── integration/
│   ├── test_pipeline.py
│   └── test_api.py
└── conftest.py
```

---

## 📦 Dependencies Review

### Check for unused dependencies:

```bash
pip install pipdeptree
pipdeptree
```

### Potential removals:

- Streamlit (if no longer used)
- Any unused libraries

---

## 🎨 Frontend Cleanup

### Current Issues:

- Minimal - frontend is clean!

### Minor improvements:

1. Extract `formatTimestamp` to utils file
2. Consolidate API error handling
3. Add PropTypes or TypeScript

---

## 💾 `.gitignore` Updates Needed

Add:

```
# Logs
*.log

# Data directories
data/

# Virtual environment
.venv/
venv/

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local

# Build artifacts
dist/
build/
*.egg-info/
```

---

## 📝 Summary

### Immediate Actions (Do Now):

1. **Delete 7 one-time scripts** - Safe to remove
2. **Delete 4 log files** - Not needed in git
3. **Update `.gitignore`** - Prevent future clutter

### High-Impact Refactoring (Next Sprint):

1. **Consolidate embedding logic** - Reduce 300+ duplicate lines
2. **Split SearchEngine** - Better maintainability
3. **Add basic tests** - Prevent regressions

### Total Cleanup Impact:

- **Delete**: ~800 lines of obsolete code
- **Consolidate**: ~300 lines of duplicates
- **Result**: 20% smaller, much more maintainable codebase

---

## ⚠️ Before Deleting

1. ✅ Verify all scripts are truly one-time
2. ✅ Archive scripts in `scripts/maintenance/` (just in case)
3. ✅ Commit current state before changes
4. ✅ Test after each deletion

Would you like me to proceed with Phase 1 (deletions) now?
