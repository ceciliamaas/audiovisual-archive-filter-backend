# Backend API Documentation

## Overview

This FastAPI backend provides AI-powered search capabilities for audiovisual archives using CLIP embeddings and Qdrant vector database. The backend is designed to work seamlessly with a React frontend.

## Base URL

Development: `http://localhost:8000`

## Core Features

1. **Video Upload & Processing** - Upload videos for automatic frame extraction, object detection, and embedding generation
2. **Text Search** - Search for frames and objects using natural language queries
3. **Image Search** - Search for similar frames and objects using image uploads
4. **Video Streaming** - Stream videos with timestamp support

## API Endpoints

### 1. Video Management

#### Upload Video

```
POST /api/videos/upload
```

Upload a new video for processing.

**Request:**

- Content-Type: `multipart/form-data`
- Body:
  - `file`: Video file (mp4, avi, mov, mkv, etc.)

**Response:**

```json
{
  "video_name": "my_video",
  "status": "pending",
  "message": "Video 'my_video' uploaded successfully. Processing started."
}
```

**Processing Pipeline:**

1. Extract frames at 1 FPS
2. Detect objects using YOLO
3. Compute CLIP embeddings
4. Upload to storage (S3/local)
5. Index in Qdrant vector database

#### Get Video Status

```
GET /api/videos/status/{video_name}
```

Get processing status for a specific video.

**Response:**

```json
{
  "video_name": "my_video",
  "status": "completed",
  "progress": 100.0,
  "frame_count": 245,
  "object_count": 1203,
  "created_at": "2026-01-03T10:30:00",
  "updated_at": "2026-01-03T10:45:00",
  "completed_at": "2026-01-03T10:45:00",
  "error_message": null,
  "steps_completed": [
    "download",
    "extract_frames",
    "detect_objects",
    "compute_embeddings",
    "upload"
  ]
}
```

**Status Values:**

- `pending` - Queued for processing
- `downloading` - Downloading/copying video
- `extracting_frames` - Extracting frames
- `detecting_objects` - Running YOLO detection
- `computing_embeddings` - Computing CLIP embeddings
- `uploading` - Uploading to storage
- `completed` - Processing complete
- `failed` - Processing failed

#### List Videos

```
GET /api/videos/list?status={status}&limit={limit}
```

List all videos and their processing status.

**Query Parameters:**

- `status` (optional): Filter by status (pending, processing, completed, failed)
- `limit` (optional): Maximum number of results (default: 100, max: 500)

**Response:**

```json
{
  "videos": [
    {
      "video_name": "my_video",
      "status": "completed",
      "progress": 100.0,
      "frame_count": 245,
      "object_count": 1203,
      "created_at": "2026-01-03T10:30:00",
      "updated_at": "2026-01-03T10:45:00",
      "completed_at": "2026-01-03T10:45:00",
      "error_message": null,
      "steps_completed": [
        "download",
        "extract_frames",
        "detect_objects",
        "compute_embeddings",
        "upload"
      ]
    }
  ],
  "total": 1
}
```

#### Stream Video

```
GET /api/videos/stream/{video_name}
```

Stream a video file. Returns presigned URL for S3 storage or direct file stream for local storage.

#### Delete Video

```
DELETE /api/videos/{video_name}
```

Delete a video and all associated data (frames, objects, embeddings).

**Response:**

```json
{
  "message": "Video 'my_video' deleted successfully",
  "video_name": "my_video"
}
```

---

### 2. Search

#### Text Search

```
POST /api/search/text
```

Search for similar frames/objects using natural language.

**Request:**

```json
{
  "query": "person walking on the beach",
  "search_frames": true,
  "search_objects": true,
  "max_results": 50,
  "similarity_threshold": 0.75
}
```

**Response:**

```json
{
  "query": "person walking on the beach",
  "query_type": "text",
  "results": [
    {
      "path": "frames/beach_video/frame_00123.jpg",
      "similarity": 0.89,
      "result_type": "frame",
      "metadata": {
        "video_name": "beach_video",
        "frame_index": 123,
        "timestamp": 123.0
      },
      "url": "https://storage.example.com/presigned-url"
    }
  ],
  "total_results": 1,
  "search_frames": true,
  "search_objects": true,
  "max_results": 50
}
```

#### Image Search

```
POST /api/search/image
```

Search for similar frames/objects using an uploaded image.

**Request:**

- Content-Type: `multipart/form-data`
- Body:
  - `image`: Image file (jpg, png, etc.)
  - `search_frames`: boolean (default: true)
  - `search_objects`: boolean (default: true)
  - `max_results`: integer (default: 50, max: 200)

**Response:** Same format as text search

---

### 3. System Status

#### Get System Status

```
GET /api/status
```

Get overall system status including embeddings information.

**Response:**

```json
{
  "replicate_available": true,
  "model": "andreasjansson/clip-features",
  "embeddings_status": {
    "loaded": true,
    "frame_count": 12450,
    "object_count": 45230,
    "source": "qdrant"
  }
}
```

#### Get Storage Status

```
GET /api/storage/status
```

Get storage system configuration and status.

**Response:**

```json
{
  "s3_available": true,
  "local_available": true,
  "recommended_backend": "s3",
  "current_mode": "s3",
  "fallback_enabled": true,
  "issues": []
}
```

---

## Result Metadata

All search results include metadata with video timestamp information:

### Frame Results

```json
{
  "path": "frames/video_name/frame_00123.jpg",
  "similarity": 0.89,
  "result_type": "frame",
  "metadata": {
    "video_name": "video_name",
    "frame_index": 123,
    "timestamp": 123.0 // Seconds from video start
  },
  "url": "https://..."
}
```

### Object Results

```json
{
  "path": "objects/video_name/frame_00123_obj_002.jpg",
  "similarity": 0.87,
  "result_type": "object",
  "metadata": {
    "video_name": "video_name",
    "frame_index": 123,
    "object_index": 2,
    "timestamp": 123.0 // Seconds from video start
  },
  "url": "https://..."
}
```

## Video Player Integration

To display search results with video playback:

1. **Get the timestamp** from `metadata.timestamp`
2. **Get the video name** from `metadata.video_name`
3. **Stream the video** using `/api/videos/stream/{video_name}`
4. **Seek to timestamp** in your video player

Example React component:

```javascript
function SearchResult({ result }) {
  const { metadata } = result;
  const videoUrl = `/api/videos/stream/${metadata.video_name}`;

  return (
    <div>
      <img src={result.url} alt="Search result" />
      <video src={`${videoUrl}#t=${metadata.timestamp}`} controls />
    </div>
  );
}
```

## CORS Configuration

The backend is configured to accept requests from:

- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

To add your production frontend URL, edit `src/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-production-frontend.com",  # Add here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Running the Backend

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export REPLICATE_API_TOKEN=your_token_here
export QDRANT_MODE=local  # or cloud
export QDRANT_LOCAL=http://localhost:6333

# Run with auto-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker-compose up
```

## Environment Variables

Required:

- `REPLICATE_API_TOKEN` - Replicate API token for CLIP embeddings

Optional:

- `QDRANT_MODE` - `local` or `cloud` (default: local)
- `QDRANT_LOCAL` - Local Qdrant URL (default: http://localhost:6333)
- `QDRANT_CLOUD` - Cloud Qdrant URL
- `QDRANT_API_KEY` - Qdrant API key (for cloud)
- `S3_ACCESS_KEY` - AWS S3 access key
- `S3_SECRET_KEY` - AWS S3 secret key
- `S3_BUCKET` - S3 bucket name
- `S3_ENDPOINT` - S3 endpoint URL

## API Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Error Handling

All endpoints return standardized error responses:

```json
{
  "error": "Error category",
  "detail": "Detailed error message",
  "status_code": 400
}
```

Common status codes:

- `400` - Bad request (invalid input)
- `404` - Resource not found
- `500` - Internal server error

## Rate Limiting

The CLIP embedding API (Replicate) has rate limits. The backend includes:

- Concurrent processing (10 workers)
- Automatic retry with exponential backoff
- Progress tracking during processing

## Performance Tips

1. **Batch video uploads** - The pipeline processes videos sequentially
2. **Use appropriate search parameters** - Set `max_results` based on your needs
3. **Filter by video** - Use `video_name` filter in searches for faster results
4. **Monitor processing status** - Poll `/api/videos/status/{video_name}` during upload

## Example React Integration

```javascript
// Upload video
async function uploadVideo(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("http://localhost:8000/api/videos/upload", {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  return data.video_name;
}

// Poll for status
async function pollVideoStatus(videoName) {
  const response = await fetch(
    `http://localhost:8000/api/videos/status/${videoName}`
  );
  return await response.json();
}

// Search by text
async function searchByText(query) {
  const response = await fetch("http://localhost:8000/api/search/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      search_frames: true,
      search_objects: true,
      max_results: 50,
    }),
  });

  return await response.json();
}

// Search by image
async function searchByImage(imageFile) {
  const formData = new FormData();
  formData.append("image", imageFile);
  formData.append("search_frames", "true");
  formData.append("search_objects", "true");
  formData.append("max_results", "50");

  const response = await fetch("http://localhost:8000/api/search/image", {
    method: "POST",
    body: formData,
  });

  return await response.json();
}
```

## Support

For issues or questions:

1. Check the API docs at `/docs`
2. Review the logs for error details
3. Ensure all environment variables are set correctly
4. Verify Qdrant and storage connectivity
