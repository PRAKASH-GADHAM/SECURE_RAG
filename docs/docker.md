# Docker Guide

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- 4GB+ RAM recommended

## Images

### Backend (Multi-stage)

- **Builder stage**: Installs Python dependencies with compiled extensions
- **Production stage**: Slim Python image with only runtime dependencies
- Uses `tini` for proper signal handling
- Non-root user (`appuser`)
- Health check via `/health` endpoint

### Frontend (Multi-stage)

- **Build stage**: Node 20 Alpine, builds React app with Vite
- **Production stage**: Nginx 1.27 Alpine, serves static files
- Gzip compression enabled
- Security headers configured

## Commands

```bash
# Build all services
docker compose build

# Build specific service
docker compose build backend

# Rebuild without cache
docker compose build --no-cache

# Start all services
docker compose up -d

# Start with logs
docker compose up -d --build

# View logs
docker compose logs -f backend
docker compose logs -f celery_worker

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Execute command in container
docker compose exec backend python -c "from app.config import get_settings; print(get_settings().APP_ENV)"

# Run database migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"
```

## Volumes

| Volume | Purpose |
|--------|---------|
| postgres_data | PostgreSQL data |
| redis_data | Redis persistence |
| chroma_data | ChromaDB vectors |
| upload_data | User uploaded files |
| backend_logs | Application logs |
| worker_logs | Celery worker logs |
| nginx_logs | Nginx access/error logs |

## Networking

- `secure_rag_internal`: Internal service communication (bridge, no external access)
- `secure_rag_proxy`: External-facing services (Nginx, Backend)

## Development Mode

```bash
# Use development overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# This enables:
# - Hot reload for backend
# - Source code mounting
# - Debug logging
# - All ports exposed
```

## Troubleshooting

### Container won't start
```bash
docker compose logs <service>
docker compose ps
```

### Database connection refused
```bash
docker compose exec postgres pg_isready
docker compose restart postgres
```

### Redis connection refused
```bash
docker compose exec redis redis-cli ping
docker compose restart redis
```

### Out of memory
Check resource usage:
```bash
docker stats
```
Adjust limits in docker-compose.yml.
