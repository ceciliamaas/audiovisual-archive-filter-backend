# Docker Setup for Audiovisual Archive

This project uses Docker for local development and deployment.

## Quick Start

### Start Qdrant Only (Minimal Setup)

```bash
# Start Qdrant vector database
docker compose up qdrant -d

# Check status
docker compose ps

# View logs
docker compose logs -f qdrant

# Stop
docker compose down
```

Your app will connect to Qdrant at `http://localhost:6333`.

### Start Full Stack (App + Qdrant)

Uncomment the `app` service in `docker-compose.yml`, then:

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

Access:

- **Streamlit App**: http://localhost:8501
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Services

### Qdrant (Vector Database)

- **Port**: 6333 (REST API), 6334 (gRPC)
- **Storage**: `./qdrant_storage/` (persisted on host)
- **Dashboard**: http://localhost:6333/dashboard

### Streamlit App (Optional)

- **Port**: 8501
- **Volumes**:
  - Code: `.:/app` (live reload)
  - Data: `./data:/app/data`
- **Environment**: Uses `.env` file

## Development Workflow

### Option 1: Qdrant in Docker, App on Host (Recommended)

Best for active development with fast iteration:

```bash
# Start only Qdrant
docker compose up qdrant -d

# Run app locally (in virtual environment)
streamlit run app.py

# Or run pipeline
python -m scripts.pipeline process video_name --source drive --url "..."
```

### Option 2: Full Stack in Docker

Best for production-like testing:

```bash
# Uncomment app service in docker-compose.yml

# Start everything
docker compose up -d

# Execute pipeline inside container
docker compose exec app python -m scripts.pipeline process video_name --source drive --url "..."
```

## Environment Variables

Create `.env` file (see `.env.example`):

```bash
# For Docker app service
QDRANT_LOCAL=http://qdrant:6333

# For local development
QDRANT_LOCAL=http://localhost:6333

# For Qdrant Cloud
QDRANT_CLOUD=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_api_key
QDRANT_MODE=cloud

# Other vars
REPLICATE_API_TOKEN=your_token
STORJ_ACCESS_KEY=your_key
```

## Data Persistence

### Qdrant Data

Stored in `./qdrant_storage/` directory:

- Persists across container restarts
- Backed up with your project
- Can be deleted to reset database

### Application Data

- Local: `./data/` directory
- Docker: Mounted as volume

## Useful Commands

```bash
# View container status
docker compose ps

# View logs
docker compose logs -f [service_name]

# Restart service
docker compose restart [service_name]

# Rebuild after code changes
docker compose up --build -d

# Stop and remove containers
docker compose down

# Stop and remove with volumes (caution: deletes data)
docker compose down -v

# Execute command in running container
docker compose exec app bash

# View Qdrant collections
curl http://localhost:6333/collections
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 6333
lsof -i :6333

# Change ports in docker-compose.yml
ports:
  - "6334:6333"  # Use 6334 on host instead
```

### Qdrant Container Won't Start

```bash
# View detailed logs
docker compose logs qdrant

# Reset Qdrant data
rm -rf qdrant_storage/
docker compose up qdrant -d
```

### App Can't Connect to Qdrant

- From Docker app: Use `QDRANT_LOCAL=http://qdrant:6333` and `QDRANT_MODE=local`
- From host: Use `QDRANT_LOCAL=http://localhost:6333` and `QDRANT_MODE=local`
- Check network: `docker compose exec app ping qdrant`

## Production Deployment

For production, consider:

1. **Qdrant Cloud**: Use hosted Qdrant instead

   ```bash
   QDRANT_URL=https://your-cluster.cloud.qdrant.io
   QDRANT_API_KEY=your_api_key
   ```

2. **Container Registry**: Push to Docker Hub/ECR

   ```bash
   docker build -t your-registry/archive-filter:latest .
   docker push your-registry/archive-filter:latest
   ```

3. **Orchestration**: Use Kubernetes/Docker Swarm for multi-instance deployment

## Monitoring

### Qdrant Health

```bash
curl http://localhost:6333/health
```

### App Health

```bash
curl http://localhost:8501/_stcore/health
```

## Backup & Restore

### Backup Qdrant

```bash
# Stop Qdrant
docker compose stop qdrant

# Backup storage
tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz qdrant_storage/

# Start Qdrant
docker compose start qdrant
```

### Restore Qdrant

```bash
# Stop Qdrant
docker compose stop qdrant

# Restore storage
rm -rf qdrant_storage/
tar -xzf qdrant_backup_YYYYMMDD.tar.gz

# Start Qdrant
docker compose start qdrant
```
