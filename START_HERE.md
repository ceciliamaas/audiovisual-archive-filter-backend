# 🚀 Development Startup Guide

## Quick Start (Every Time You Open the Project)

### Option 1: Using Scripts (Easiest)

Open **3 terminals**:

**Terminal 1 - Backend:**

```bash
cd archive-filter_backend
chmod +x dev-start.sh  # Only needed first time
./dev-start.sh
```

**Terminal 2 - Frontend:**

```bash
cd archive-filter_frontend
chmod +x dev-start.sh  # Only needed first time
./dev-start.sh
```

That's it! ✨

---

### Option 2: Manual Startup

**Terminal 1 - Start Qdrant (if using local):**

```bash
cd archive-filter_backend
docker start archive_qdrant
# OR if container doesn't exist:
docker compose up -d qdrant
```

**Terminal 2 - Start Backend:**

```bash
cd archive-filter_backend
export $(cat .env | grep -v '^#' | xargs)
PYTHONPATH=$(pwd) .venv/bin/python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 - Start Frontend:**

```bash
cd archive-filter_frontend
npm run dev
```

---

## What Runs Where

| Service      | URL                        | Purpose                    |
| ------------ | -------------------------- | -------------------------- |
| **Frontend** | http://localhost:5173      | React UI                   |
| **Backend**  | http://localhost:8000      | FastAPI server             |
| **API Docs** | http://localhost:8000/docs | Interactive API docs       |
| **Qdrant**   | http://localhost:6333      | Vector database (if local) |

---

## Troubleshooting

### ❌ Port Already in Use

**Backend (port 8000):**

```bash
lsof -ti:8000 | xargs kill -9
```

**Frontend (port 5173):**

```bash
lsof -ti:5173 | xargs kill -9
```

### ❌ Qdrant Not Running

```bash
docker start archive_qdrant
# Check status:
docker ps | grep qdrant
```

### ❌ Backend Can't Find Modules

```bash
cd archive-filter_backend
export PYTHONPATH=$(pwd)
```

### ❌ Frontend Won't Start

```bash
cd archive-filter_frontend
rm -rf node_modules package-lock.json
npm install
```

---

## Stopping Everything

**Stop Backend/Frontend:**

- Press `Ctrl+C` in each terminal

**Stop Qdrant:**

```bash
docker stop archive_qdrant
```

**Stop Everything with Docker:**

```bash
cd archive-filter_backend
docker compose down
```

---

## Environment Modes

Your `.env` file controls whether you use **local** or **cloud** services:

### Development (Local)

```bash
QDRANT_MODE=local
STORAGE_MODE=local-only  # or hybrid
```

### Production (Cloud)

```bash
QDRANT_MODE=cloud
STORAGE_MODE=s3-only
```

---

## Need Help?

- Backend logs: Check Terminal 2
- Frontend logs: Check Terminal 3
- Qdrant logs: `docker logs archive_qdrant`
- API documentation: http://localhost:8000/docs

---

## First Time Setup

If this is your first time, you need to:

1. **Install Python dependencies:**

```bash
cd archive-filter_backend
python3 -m venv .venv
source .venv/bin/activate  # or `.venv/bin/activate` on Windows
pip install -e .
```

2. **Install Node dependencies:**

```bash
cd archive-filter_frontend
npm install
```

3. **Copy environment file:**

```bash
cd archive-filter_backend
cp .env.example .env
# Edit .env with your API keys
```

4. **Start Docker:**

- Open Docker Desktop
- Make sure it's running
