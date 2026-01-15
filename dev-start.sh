#!/bin/bash
# Development startup script for backend

echo "🚀 Starting Backend Development Server..."

# Change to script directory
cd "$(dirname "$0")"

# Start Qdrant if not running
if ! docker ps | grep -q archive_qdrant; then
    echo "📦 Starting Qdrant..."
    docker start archive_qdrant 2>/dev/null || docker compose up -d qdrant
    sleep 2
fi

# Load environment variables and start backend
echo "⚡ Starting FastAPI server..."
export $(cat .env | grep -v '^#' | xargs)
PYTHONPATH=$(pwd) .venv/bin/python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
