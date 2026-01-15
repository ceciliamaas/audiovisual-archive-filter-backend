# Deployment Guide

## Overview

This application consists of two main components:

- **Backend**: FastAPI server deployed on Hetzner VPS
- **Frontend**: React application deployed on Cloudflare Pages

---

## Backend Deployment (Hetzner VPS)

### Prerequisites

- Hetzner VPS/Cloud Server (Ubuntu 22.04 recommended)
- Docker and Docker Compose installed on server
- Domain name pointed to your server IP
- `.env` file with all required environment variables

### Initial Server Setup

1. **Connect to your Hetzner server**

```bash
ssh root@your-server-ip
```

2. **Update system**

```bash
apt update && apt upgrade -y
```

3. **Install Docker**

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Verify installation
docker --version
docker-compose --version
```

4. **Install Git**

```bash
apt install git -y
```

### Deploy Backend

1. **Clone repository**

```bash
cd /opt
git clone <your-backend-repo-url> archive-filter_backend
cd archive-filter_backend
```

2. **Set up environment variables**

```bash
cp .env.example .env
nano .env
# Edit with your production values:
# - REPLICATE_API_TOKEN
# - STORJ credentials (or AWS S3)
# - QDRANT_CLOUD and QDRANT_API_KEY
# - Set STORAGE_MODE=s3-only
# - Set QDRANT_MODE=cloud
```

3. **Build and run with Docker**

```bash
# Build the Docker image
docker build -t archive-backend .

# Run the container
docker run -d \
  --name archive-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  -v /opt/archive-filter_backend/data:/app/data \
  archive-backend
```

4. **Verify it's running**

```bash
docker ps
docker logs archive-backend
curl http://localhost:8000/health
```

### Set Up Nginx Reverse Proxy (Optional but Recommended)

1. **Install Nginx**

```bash
apt install nginx -y
```

2. **Create Nginx configuration**

```bash
nano /etc/nginx/sites-available/archive-backend
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;  # Replace with your domain

    client_max_body_size 500M;  # Allow large video uploads

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

3. **Enable the site**

```bash
ln -s /etc/nginx/sites-available/archive-backend /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

4. **Set up SSL with Let's Encrypt**

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d api.yourdomain.com
```

### Updating the Backend

```bash
cd /opt/archive-filter_backend
git pull
docker stop archive-backend
docker rm archive-backend
docker build -t archive-backend .
docker run -d \
  --name archive-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  -v /opt/archive-filter_backend/data:/app/data \
  archive-backend
```

---

## Frontend Deployment (Cloudflare Pages)

### Prerequisites

- Cloudflare account
- GitHub repository with frontend code
- Backend API URL (from Hetzner deployment)

### Deploy to Cloudflare Pages

1. **Log in to Cloudflare Dashboard**

Go to https://dash.cloudflare.com/

2. **Navigate to Pages**

- Click on "Workers & Pages" in the sidebar
- Click "Create application"
- Choose "Pages" tab
- Click "Connect to Git"

3. **Connect GitHub Repository**

- Authorize Cloudflare to access your GitHub
- Select your `archive-filter_frontend` repository

4. **Configure Build Settings**

- **Project name**: `archive-filter-frontend` (or your choice)
- **Production branch**: `main`
- **Build command**: `npm run build`
- **Build output directory**: `dist`
- **Root directory**: `/` (leave empty if frontend is at root)

5. **Add Environment Variables**

Click "Environment variables" and add:

```
VITE_API_URL = https://api.yourdomain.com
```

Replace with your actual backend URL from Hetzner.

6. **Deploy**

Click "Save and Deploy"

Cloudflare will:

- Build your application
- Deploy to their global CDN
- Provide you with a URL like `archive-filter-frontend.pages.dev`

### Custom Domain (Optional)

1. In Cloudflare Pages dashboard, go to your project
2. Click "Custom domains"
3. Add your domain (e.g., `app.yourdomain.com`)
4. Cloudflare will automatically set up DNS and SSL

### Updating the Frontend

Simply push changes to your GitHub repository:

```bash
git add .
git commit -m "Update frontend"
git push origin main
```

Cloudflare Pages will automatically rebuild and deploy.

---

## Environment Variables

### Backend (.env)

```bash
# Required
REPLICATE_API_TOKEN=your_token_here

# Storage (S3/Storj)
STORJ_ENDPOINT_URL=https://gateway.storjshare.io
STORJ_ACCESS_KEY=your_access_key
STORJ_SECRET_KEY=your_secret_key
STORJ_BUCKET_NAME=your_bucket_name
STORAGE_MODE=s3-only
USE_LOCAL_FALLBACK=false

# Qdrant
QDRANT_CLOUD=https://your-qdrant-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_api_key
QDRANT_MODE=cloud

# API
API_PORT=8000
API_HOST=0.0.0.0
```

### Frontend (.env)

```bash
VITE_API_URL=https://your-backend-url.com
```

---

## Production Checklist

### Backend

- [ ] Set `STORAGE_MODE=s3-only` (not local)
- [ ] Use `QDRANT_MODE=cloud` (not local)
- [ ] Add all API keys and secrets
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring (healthcheck endpoints available)
- [ ] Configure CORS for your frontend domain
- [ ] Set up backup for pipeline state files

### Frontend

- [ ] Set correct `VITE_API_URL` pointing to backend
- [ ] Build optimized production bundle
- [ ] Enable CDN/caching
- [ ] Configure proper error tracking
- [ ] Test on multiple browsers/devices

---

## CORS Configuration

If deploying separately, update CORS in [backend/src/api/main.py](../backend/src/api/main.py):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Development
        "https://your-frontend-domain.com",  # Production
        "https://www.your-frontend-domain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Monitoring & Health Checks

### Backend Health Endpoints

- `/health` - Basic health check
- `/api/status` - Detailed service status
- `/docs` - API documentation

### Frontend Health Endpoint

- `/health` - Nginx health check

---

## Troubleshooting

### Backend Issues

**Qdrant Connection Error**

- Check `QDRANT_MODE` and `QDRANT_CLOUD` URL
- Verify `QDRANT_API_KEY` is correct
- Test connection: `curl https://your-qdrant-cluster.cloud.qdrant.io`

**S3/Storj Connection Error**

- Verify credentials in environment variables
- Check bucket exists and has proper permissions
- Test with AWS CLI: `aws s3 ls --endpoint-url=https://gateway.storjshare.io`

**Replicate API Error**

- Check `REPLICATE_API_TOKEN` is valid
- Verify API quota/limits

### Frontend Issues

**API Connection Failed**

- Verify `VITE_API_URL` is correct
- Check CORS configuration in backend
- Open browser console for detailed errors

**Build Fails**

- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version: `node --version` (should be 18+)

---

## Scaling Considerations

### Backend

- Use cloud Qdrant for vector search (already configured)
- Store all files in S3/Storj (already configured)
- Increase uvicorn workers: `--workers 4`
- Use gunicorn for production: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api.main:app`

### Frontend

- Static files on CDN (automatic with Vercel/Netlify)
- Enable aggressive caching for assets
- Use compression (gzip/brotli)

---

## Cost Estimates

### Cloud Services

- **Qdrant Cloud**: Free tier (1GB), Paid from $25/month
- **Storj S3**: Free tier (25GB), then ~$4/TB
- **Replicate API**: Pay per use, ~$0.001 per request

### Hosting Options (Backend)

- **Render**: Free tier, Paid from $7/month
- **Railway**: Free trial, then ~$5-10/month
- **Fly.io**: Free tier, then ~$5-10/month
- **DigitalOcean**: From $5/month (droplet) or $12/month (app platform)

### Hosting Options (Frontend)

- **Vercel**: Free for hobby projects
- **Netlify**: Free for hobby projects
- **Cloudflare Pages**: Free for unlimited sites

**Recommended Budget**: $15-30/month for small production deployment

---

## Support

For issues or questions:

1. Check logs: `docker compose logs -f backend`
2. Test health endpoints
3. Review environment variables
4. Check API documentation at `/docs`
