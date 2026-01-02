# Qdrant Vector Database Setup

This project now uses Qdrant for storing and searching video frame and object embeddings, replacing pickle files with a proper vector database.

## Benefits of Qdrant

- **Faster search**: Optimized vector similarity search
- **Scalability**: Handle millions of embeddings efficiently
- **Filtering**: Search by video name or other metadata
- **Production-ready**: Persistent storage with ACID guarantees
- **Cloud or Local**: Run locally for development or use Qdrant Cloud

## Installation

### Option 1: Local Qdrant with Docker (Recommended for Development)

```bash
# Run Qdrant locally
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

Or use docker-compose:

```yaml
# docker-compose.yml
version: "3.8"
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
```

Then run: `docker-compose up -d`

### Option 2: Qdrant Cloud (Recommended for Production)

1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a cluster
3. Get your cluster URL and API key
4. Update `.env`:

```bash
QDRANT_CLOUD=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_api_key_here
QDRANT_MODE=cloud
```

## Configuration

Add to your `.env` file:

```bash
# For local development
QDRANT_LOCAL=http://localhost:6333
QDRANT_MODE=local

# For production with Qdrant Cloud
QDRANT_CLOUD=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_api_key_here
QDRANT_MODE=cloud
```

## Usage

### Automatic Migration

When you run the pipeline, embeddings will automatically be stored in both:

- **Qdrant** (for fast vector search)
- **Pickle files** (for backward compatibility)

```bash
# Process a video - embeddings automatically go to Qdrant
python -m scripts.pipeline process my_video --source drive --url "..."
```

### Search Using Qdrant

The search engine automatically uses Qdrant when available:

```python
from src.core.search import SearchEngine

engine = SearchEngine()

# Search by text - uses Qdrant automatically
results = engine.search_by_text("person with backpack")

# Search by image
results = engine.search_by_image("query_image.jpg")
```

### Manual Qdrant Operations

```python
from src.storage.qdrant import QdrantStorage

qdrant = QdrantStorage()

# Get collection info
frames_info = qdrant.get_collection_info("frames")
print(f"Frames in Qdrant: {frames_info['points_count']}")

objects_info = qdrant.get_collection_info("objects")
print(f"Objects in Qdrant: {objects_info['points_count']}")

# Search directly
results = qdrant.search_frames(query_vector, limit=10)
results = qdrant.search_objects(query_vector, limit=10, video_name="my_video")
```

### Migrating Existing Pickle Files to Qdrant

If you have existing pickle embeddings, run the pipeline with `--force` to recompute and store in Qdrant:

```bash
python -m scripts.pipeline process existing_video --source local --force
```

Or create a migration script:

```python
import pickle
from src.storage.qdrant import QdrantStorage

# Load existing pickles
with open("data/embeddings/frame_embeddings.pkl", "rb") as f:
    frame_emb = pickle.load(f)
with open("data/embeddings/frame_paths.pkl", "rb") as f:
    frame_paths = pickle.load(f)

# Convert to Qdrant format
qdrant = QdrantStorage()
paths_dict = {key: frame_paths[i] for i, key in enumerate(frame_emb.keys())}
qdrant.store_frame_embeddings(frame_emb, paths_dict)
```

## Collections Structure

### Frames Collection

- **Name**: `frames`
- **Vector dimension**: 512 (CLIP embeddings)
- **Distance metric**: Cosine similarity
- **Payload**:
  - `key`: Frame identifier (e.g., "video_name/frame_00001.jpg")
  - `path`: S3 storage path
  - `video_name`: Video name for filtering
  - `type`: "frame"

### Objects Collection

- **Name**: `objects`
- **Vector dimension**: 512 (CLIP embeddings)
- **Distance metric**: Cosine similarity
- **Payload**:
  - `key`: Object identifier
  - `path`: S3 storage path
  - `video_name`: Video name for filtering
  - `type`: "object"

## Fallback Behavior

The system gracefully falls back to pickle files if:

- Qdrant is not available
- Collections are empty
- Connection fails

This ensures backward compatibility and development flexibility.

## Monitoring

Check Qdrant Web UI:

- Local: http://localhost:6333/dashboard
- Cloud: Your cluster URL

Or use the API:

```bash
curl http://localhost:6333/collections
```

## Troubleshooting

### "Failed to initialize Qdrant"

- Ensure Docker is running
- Check `QDRANT_URL` in `.env`
- Verify port 6333 is available

### "Qdrant collections are empty"

- Run the pipeline to compute embeddings
- Check logs for storage errors
- Verify Qdrant has write permissions

### Search returns no results

- Verify embeddings were stored: check collection info
- Ensure query embedding computation succeeds
- Check video_name filter if using it
