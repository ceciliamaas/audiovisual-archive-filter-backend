# Quick Start: Image Search

This guide will help you start using the image similarity search feature.

## Prerequisites

1. Ensure you have the required API token:
   ```bash
   # In your .env file
   REPLICATE_API_TOKEN=your_token_here
   ```

2. Embeddings must be pre-computed and available in storage
   - Frame embeddings: `embeddings/frame_embeddings.pkl`
   - Object embeddings: `embeddings/object_embeddings.pkl`
   - Paths: `embeddings/frame_paths.pkl`, `embeddings/object_paths.pkl`

## Using Image Search

### Via Web Interface

1. **Start the application:**
   ```bash
   python main.py
   ```

2. **Select image search mode:**
   - Click on "🖼️ Búsqueda por imagen" radio button

3. **Choose your image:**
   
   **Option A: Upload your own image**
   - Click "Browse files" 
   - Select a JPG, JPEG, or PNG image
   - Preview appears automatically
   
   **Option B: Use example images**
   - Expand "📷 Usar imágenes de ejemplo"
   - Select an image from the dropdown
   - Click "Usar esta imagen"

4. **Execute search:**
   - Click "🔍 Buscar por imagen"
   - Wait for results (typically 2-5 seconds)

5. **View results:**
   - Results are organized in two sections:
     - **🎬 Fotogramas**: Complete video frames
     - **🎯 Objetos detectados**: Detected objects with their source frames
   - Each result shows similarity score (0.0 to 1.0, higher is better)

### Via Python API

```python
from src.core.search import get_search_engine

# Initialize search engine
engine = get_search_engine()

# Search with an image
results = engine.search_by_image(
    image_path="path/to/your/image.jpg",
    search_frames=True,      # Search in video frames
    search_objects=True,     # Search in detected objects
    max_results=50          # Maximum results to return
)

# Process results
for result in results:
    print(f"Path: {result.path}")
    print(f"Type: {result.result_type}")  # 'frame' or 'object'
    print(f"Similarity: {result.similarity:.4f}")
    print("---")
```

## Tips for Best Results

1. **Image Quality**: Use clear, well-lit images for better matching
2. **Similar Content**: Upload images similar in content/style to what you're searching for
3. **Adjust Results**: Use the "Máximo resultados" slider to see more/fewer matches
4. **Similarity Threshold**: Results with similarity > 0.3 are typically good matches
5. **Try Different Images**: If results aren't satisfactory, try a different reference image

## Example Use Cases

- **Find similar scenes**: Upload a frame from one video to find similar scenes in others
- **Object matching**: Upload an image of an object to find where it appears in videos
- **Style matching**: Find frames with similar visual style or composition
- **Color matching**: Find frames with similar color palettes

## Troubleshooting

### No results found
- Try lowering the similarity threshold in configuration
- Ensure embeddings are properly loaded
- Check that reference image is clear and relevant

### Slow performance
- First search may be slow while embeddings load
- Subsequent searches are much faster
- Consider reducing max_results

### Error messages
- Check that REPLICATE_API_TOKEN is set correctly
- Verify embeddings exist in storage
- Ensure image file is valid (not corrupted)

## Configuration

Edit settings in `.env` or `src/config/settings.py`:

```python
# Minimum similarity score for results
similarity_threshold = 0.15

# Maximum results to return
max_search_results = 50

# CLIP model to use
embedding_model = "openai/clip:ViT-B/32"
```

## Next Steps

- Read the full documentation: [docs/IMAGE_SEARCH.md](IMAGE_SEARCH.md)
- Run tests: `python tests/test_image_search.py`
- Explore the Python API for custom integrations
