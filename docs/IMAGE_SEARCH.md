# Search by Image Feature

## Overview

The search by image feature allows users to find similar content in the video archive by uploading a reference image. The system uses CLIP (Contrastive Language-Image Pre-Training) embeddings to compute visual similarity between the uploaded image and frames/objects in the archive.

## How It Works

1. **Image Upload**: Users can upload an image (PNG, JPG, JPEG) through the web interface
2. **Embedding Computation**: The system computes a CLIP embedding vector for the uploaded image using the OpenAI CLIP model via Replicate API
3. **Similarity Search**: The embedding is compared against pre-computed embeddings of all frames and objects in the archive using cosine similarity
4. **Results Display**: The most similar frames and objects are displayed, ranked by similarity score

## Technical Implementation

### Backend Components

#### `src/core/search.py`

- **`SearchEngine.compute_image_embedding()`**: Computes CLIP embedding for an image file

  - Opens the image file and sends it to the Replicate API
  - Uses the `openai/clip` model with ViT-B/32 architecture
  - Normalizes the resulting embedding vector

- **`SearchEngine.search_by_image()`**: Performs similarity search using an image query
  - Loads embeddings from storage if not already loaded
  - Computes embedding for the query image
  - Searches both frame and object embeddings
  - Returns ranked results by similarity score

### Frontend Components

#### `src/web/components/search_interface.py`

- **`_render_image_search()`**: Renders the image search UI
  - File uploader for custom images
  - Example images selector (from `input_image_for_search/` directory)
  - Image preview
  - Search button

#### `src/web/components/results_display.py`

- **`render_results()`**: Updated to handle both text and image query types
  - Shows appropriate header based on query type
  - Displays results in organized grids

## Usage

### Via Web Interface

1. Launch the application: `python main.py`
2. Select "🖼️ Búsqueda por imagen" in the search type radio buttons
3. Either:
   - Upload an image using the file uploader
   - Select an example image from the expander
4. Click "🔍 Buscar por imagen"
5. View results organized by frames and detected objects

### Via Python API

```python
from src.core.search import get_search_engine

# Get search engine instance
search_engine = get_search_engine()

# Search by image
results = search_engine.search_by_image(
    image_path="/path/to/image.jpg",
    search_frames=True,
    search_objects=True,
    max_results=50
)

# Process results
for result in results:
    print(f"{result.path}: {result.similarity:.3f} ({result.result_type})")
```

## Configuration

The image search uses the same configuration as text search:

- **`REPLICATE_API_TOKEN`**: Required for CLIP model access
- **`similarity_threshold`**: Minimum similarity score (default: 0.15)
- **`max_search_results`**: Maximum results to return (default: 50)
- **`embedding_model`**: CLIP model to use (default: "openai/clip:ViT-B/32")

## Example Images

To use example images:

1. Create directory: `input_image_for_search/`
2. Add sample images (JPG, JPEG, PNG)
3. Images will appear in the example images dropdown

## Performance Considerations

- **Embedding Computation**: Takes ~1-2 seconds per image via Replicate API
- **Search Speed**: Very fast once embedding is computed (~10-50ms for 10K embeddings)
- **Storage**: Uses pre-computed embeddings for all frames and objects
- **Caching**: Embeddings are loaded once and cached in memory

## Limitations

- Requires active internet connection for Replicate API
- Query image must be in a supported format (PNG, JPG, JPEG)
- Results depend on the quality of pre-computed embeddings
- Similarity threshold may need adjustment based on use case

## Testing

Run the test suite:

```bash
python tests/test_image_search.py
```

This tests:

- Image embedding computation
- Full search workflow
- Search engine status and configuration

## Future Enhancements

Possible improvements:

- Local CLIP model deployment (no API dependency)
- Support for more image formats
- Batch image upload and comparison
- Advanced filters (by video, by object type, by timeframe)
- Image preprocessing options
- Similarity score visualization
- Export results functionality
