# Environment Variables Reference

## Application

| Variable | Default | Description |
|----------|---------|-------------|
| APP_NAME | SecureRAG | Application name |
| APP_VERSION | 1.0.0 | Application version |
| APP_ENV | development | Environment (development/production/testing) |
| DEBUG | true | Enable debug mode |
| LOG_LEVEL | INFO | Logging level |

## Backend

| Variable | Default | Description |
|----------|---------|-------------|
| BACKEND_HOST | 0.0.0.0 | Backend bind host |
| BACKEND_PORT | 8000 | Backend bind port |
| BACKEND_WORKERS | 4 | Uvicorn worker count |
| ALLOWED_ORIGINS | http://localhost:5173 | CORS allowed origins |

## Database

| Variable | Default | Description |
|----------|---------|-------------|
| POSTGRES_HOST | localhost | PostgreSQL host |
| POSTGRES_PORT | 5432 | PostgreSQL port |
| POSTGRES_USER | secure_rag_user | Database user |
| POSTGRES_PASSWORD | - | Database password (required) |
| POSTGRES_DB | secure_rag_db | Database name |

## Redis

| Variable | Default | Description |
|----------|---------|-------------|
| REDIS_HOST | localhost | Redis host |
| REDIS_PORT | 6379 | Redis port |
| REDIS_PASSWORD | - | Redis password (optional) |
| REDIS_DB | 0 | Redis database number |

## ChromaDB

| Variable | Default | Description |
|----------|---------|-------------|
| CHROMA_HOST | localhost | ChromaDB host |
| CHROMA_PORT | 8000 | ChromaDB port |
| CHROMA_COLLECTION | secure_rag_vectors | Default collection name |

## Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| JWT_SECRET_KEY | - | JWT signing key (required) |
| JWT_ALGORITHM | HS256 | JWT algorithm |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | 30 | Access token TTL |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | 7 | Refresh token TTL |

## LLM

| Variable | Default | Description |
|----------|---------|-------------|
| OPENROUTER_API_KEY | - | OpenRouter API key |
| OPENROUTER_MODEL | meta-llama/llama-3.1-8b-instruct:free | LLM model |
| LLM_TEMPERATURE | 0.7 | Generation temperature |
| LLM_MAX_TOKENS | 2048 | Max output tokens |
| LLM_TIMEOUT | 60 | Request timeout (seconds) |

## Embeddings

| Variable | Default | Description |
|----------|---------|-------------|
| EMBEDDING_MODEL | BAAI/bge-m3 | Embedding model |
| EMBEDDING_DEVICE | cpu | Compute device |
| EMBEDDING_BATCH_SIZE | 32 | Batch size |

## Reranking

| Variable | Default | Description |
|----------|---------|-------------|
| RERANKER_MODEL | BAAI/bge-reranker-v2-m3 | Reranker model |
| ENABLE_RERANKING | true | Enable reranking |

## RAG Pipeline

| Variable | Default | Description |
|----------|---------|-------------|
| CHUNK_SIZE | 512 | Text chunk size |
| CHUNK_OVERLAP | 50 | Chunk overlap |
| TOP_K_RETRIEVAL | 10 | Retrieval count |
| TOP_K_RERANK | 5 | Reranked count |
| RETRIEVAL_MODE | hybrid | dense/bm25/hybrid |

## Celery

| Variable | Default | Description |
|----------|---------|-------------|
| CELERY_BROKER_URL | redis://localhost:6379/1 | Broker URL |
| CELERY_RESULT_BACKEND | redis://localhost:6379/2 | Result backend |

## Security

| Variable | Default | Description |
|----------|---------|-------------|
| CORS_ORIGINS | http://localhost:5173 | CORS origins |
| ENCRYPTION_KEY | - | Data encryption key |
| RATE_LIMIT_REQUESTS | 100 | Requests per window |
| RATE_LIMIT_WINDOW | 60 | Rate limit window (seconds) |

## Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| VITE_API_URL | http://localhost:8000 | Backend API URL |
