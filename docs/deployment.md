# Deployment Guide

## Quick Start

### Development

```bash
# Clone and configure
cp .env.example .env.development
# Edit .env.development with your settings

# Start development environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Production

```bash
# Clone and configure
cp .env.example .env.production
# Edit .env.production with secure values
# Generate secrets: openssl rand -hex 32

# Start production environment
docker compose up -d --build

# Run database migrations
docker compose exec backend alembic upgrade head

# Access
# Frontend: http://localhost:80
# Backend API: http://localhost:8000
```

## Architecture

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (Reverse   │
                    │   Proxy)    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │  Frontend  │ │Backend│ │  Static   │
        │  (React)   │ │ (API) │ │  Assets   │
        └───────────┘ └───┬───┘ └───────────┘
                          │
           ┌──────────────┼──────────────┐
           │              │              │
     ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
     │ PostgreSQL │ │   Redis   │ │ ChromaDB  │
     │  (Data)    │ │  (Cache)  │ │ (Vectors) │
     └───────────┘ └───────────┘ └───────────┘
           │
     ┌─────▼─────┐ ┌───────────┐
     │   Celery  │ │  Celery   │
     │  Worker   │ │   Beat    │
     └───────────┘ └───────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Nginx | 80, 443 | Reverse proxy, static files |
| Backend | 8000 | FastAPI REST API |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache, message broker |
| ChromaDB | 8001 | Vector database |
| Celery Worker | - | Background tasks |
| Celery Beat | - | Task scheduler |
| Frontend | 3000 (dev) | React SPA |

## Environment Variables

See [Environment Reference](environment.md) for all variables.

Required for production:
- `POSTGRES_PASSWORD` - Database password
- `JWT_SECRET_KEY` - JWT signing key
- `OPENROUTER_API_KEY` - LLM API key
- `ENCRYPTION_KEY` - Data encryption key
- `CORS_ORIGINS` - Allowed origins

## Backup

```bash
# Create backup
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh ./backups/20250115_100000
```

## Health Checks

```bash
# System health check
./scripts/health_check.sh

# API health endpoint
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/api/v1/health/detailed
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
  celery_worker:
    deploy:
      replicas: 2
```

### Resource Limits

Default limits are set in docker-compose.yml:
- Backend: 2GB memory
- Celery Worker: 2GB memory
- PostgreSQL: 512MB memory
- Redis: 256MB memory
- ChromaDB: 512MB memory

## SSL/TLS

1. Place certificates in `nginx/ssl/`:
   - `nginx/ssl/cert.pem`
   - `nginx/ssl/key.pem`

2. Update nginx.conf to listen on 443:
   ```nginx
   listen 443 ssl;
   ssl_certificate /etc/nginx/ssl/cert.pem;
   ssl_certificate_key /etc/nginx/ssl/key.pem;
   ```

3. Enable HSTS in security headers (already configured).

## Monitoring

- Prometheus metrics at `/api/v1/monitoring/metrics`
- Dashboard at `/api/v1/monitoring/dashboard`
- Logs stored in Docker volumes
- Structured JSON logs in production
