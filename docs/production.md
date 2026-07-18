# Production Checklist

## Pre-Deployment

- [ ] All environment variables configured in `.env.production`
- [ ] Strong passwords generated (`openssl rand -hex 32`)
- [ ] JWT secret key generated
- [ ] Encryption key generated
- [ ] OpenRouter API key obtained
- [ ] Domain name configured
- [ ] SSL certificates obtained (if using HTTPS)
- [ ] CORS origins updated for production domain

## Security

- [ ] `DEBUG=false` in production
- [ ] `APP_ENV=production`
- [ ] Strong database password
- [ ] Strong JWT secret (32+ bytes)
- [ ] Redis password set
- [ ] CORS restricted to production domain
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Prompt injection detection enabled
- [ ] Jailbreak detection enabled
- [ ] Output moderation enabled
- [ ] PII detection enabled

## Infrastructure

- [ ] Docker Compose production config
- [ ] Resource limits set
- [ ] Health checks configured
- [ ] Log rotation enabled
- [ ] Backup scripts scheduled
- [ ] Monitoring configured

## Database

- [ ] PostgreSQL running with persistent storage
- [ ] Alembic migrations applied
- [ ] Default roles seeded
- [ ] Connection pooling configured

## Services

- [ ] Backend API accessible
- [ ] Celery worker processing tasks
- [ ] Celery beat scheduling tasks
- [ ] Redis caching operational
- [ ] ChromaDB storing vectors
- [ ] Nginx serving frontend and proxying API

## Monitoring

- [ ] Health endpoints responding
- [ ] Logs being collected
- [ ] Error tracking configured
- [ ] Performance metrics available

## Backup

- [ ] Automated backups scheduled
- [ ] Backup restoration tested
- [ ] Off-site backup storage
- [ ] Recovery procedures documented

## Post-Deployment

- [ ] All health checks passing
- [ ] Authentication working
- [ ] Document upload/processing working
- [ ] Chat with RAG working
- [ ] Streaming responses working
- [ ] Admin panel accessible
- [ ] API keys functional

## Emergency Procedures

### Service Down
```bash
# Check service status
docker compose ps

# View logs
docker compose logs -f <service>

# Restart specific service
docker compose restart <service>

# Full restart
docker compose down && docker compose up -d
```

### Database Recovery
```bash
# Restore from backup
./scripts/restore.sh ./backups/<timestamp>
```

### Complete Reset
```bash
# WARNING: Destroys all data
docker compose down -v
docker compose up -d --build
docker compose exec backend alembic upgrade head
```
