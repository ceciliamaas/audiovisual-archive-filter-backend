# Audiovisual Archive Filter

AI-powered search for audiovisual archives using CLIP embeddings and YOLO object detection.

## Features

- Semantic search using CLIP embeddings
- Object detection with YOLO
- Frame-based video analysis
- S3 storage integration
- Interactive Streamlit web interface

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
streamlit run app.py
```

## Project Structure

- `src/` - Core application code
- `scripts/` - Data processing and migration scripts
- `notebooks/` - Jupyter notebooks for experimentation
- `data/` - Local data storage
- `deployment/` - Deployment configurations
