# Archived One-Time Scripts

These scripts were archived on 2026-01-15 as they were one-time maintenance/migration tasks that are no longer needed in the active codebase.

## Scripts Archived:

### 1. `app.py`

- **Purpose**: Old Streamlit entry point
- **Status**: Obsolete - now using FastAPI (`src/api/main.py`)
- **Last Used**: Pre-FastAPI migration

### 2. `migrate_to_cloud.py`

- **Purpose**: One-time migration of embeddings from local Qdrant to cloud Qdrant
- **Status**: Migration completed
- **Last Used**: Initial cloud setup

### 3. `clear_qdrant_duplicates.py`

- **Purpose**: One-time cleanup of duplicate embeddings in Qdrant
- **Status**: Cleanup completed
- **Last Used**: After fixing embedding pipeline bug

### 4. `create_bbox_metadata.py`

- **Purpose**: Retroactively create bounding box metadata JSON files for existing objects
- **Status**: Completed - all new videos include this automatically
- **Last Used**: When adding bbox feature

### 5. `reindex_with_bbox.py`

- **Purpose**: One-time reindexing of videos to add bounding box data
- **Status**: Completed
- **Last Used**: When adding bbox feature

### 6. `update_object_timestamps.py`

- **Purpose**: One-time script to add timestamps to existing object embeddings
- **Status**: Completed - all new objects include timestamps
- **Last Used**: When adding timestamp feature

### 7. `recompute_embeddings.py`

- **Purpose**: Bypass pipeline to recompute embeddings
- **Status**: Replaced by pipeline CLI
- **Alternative**: Use `python -m scripts.pipeline process --force`

### 8. `start_server.sh`

- **Purpose**: Old server startup script
- **Status**: Replaced by `dev-start.sh`
- **Alternative**: Use `./dev-start.sh`

## If You Need These Scripts:

They are safely archived here. To use them:

1. Copy back to project root if needed
2. Or run directly from this folder: `python scripts/maintenance/archived_2026_01_15/script_name.py`

## Notes:

- These scripts are kept for reference only
- They may require updates to work with current codebase
- For new maintenance tasks, create scripts in `scripts/maintenance/` with dated filenames
- Consider if the task should be added to the pipeline CLI instead
