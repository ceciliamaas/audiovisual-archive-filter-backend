# Audiovisual Archive Filter

AI-powered search for audiovisual archives using CLIP embeddings and YOLO object detection.

## Features

- **Text-based semantic search** using CLIP embeddings
- **Image-based similarity search** - find content by uploading reference images
- **Object detection** with YOLO
- **Frame-based video analysis**
- **S3/Storj cloud storage** integration with local fallback
- **Interactive Streamlit web interface**

## Setup

1. Install dependencies:

```bash
pip install -e .
```

2. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your AWS credentials and settings
```

3. Run the application:

```bash
python main.py
```

## Usage

### Search by Text

1. Select "🔤 Búsqueda por texto" in the interface
2. Enter a text description (e.g., "person walking", "yellow building")
3. Press Enter or click "🔍 Buscar"
4. View results organized by frames and detected objects

### Search by Image

1. Select "🖼️ Búsqueda por imagen" in the interface
2. Upload an image or select from examples
3. Click "🔍 Buscar por imagen"
4. View similar frames and objects from the archive

For detailed information about image search, see [docs/IMAGE_SEARCH.md](docs/IMAGE_SEARCH.md)

## Project Structure

- `src/` - Core application code
- `scripts/` - Data processing and migration scripts
- `notebooks/` - Jupyter notebooks for experimentation
- `data/` - Local data storage
- `deployment/` - Deployment configurations
