<div align="center">

# SecureRAG

### Secure Enterprise RAG Platform with AI Guardrails

[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/yourusername/secure-rag/releases)
[![CI/CD](https://github.com/yourusername/secure-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/secure-rag/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-200%2B-brightgreen.svg)](#testing)

A production-grade Retrieval-Augmented Generation platform with enterprise security, AI output guardrails, comprehensive monitoring, and a polished React frontend.

[Features](#features) · [Architecture](#architecture) · [Quick Start](#quick-start) · [Deployment](#deployment) · [API](#api-overview) · [Security](#security) · [Testing](#testing) · [Portfolio](PORTFOLIO.md) · [Demo](DEMO.md)

</div>

---

## Features

### RAG Engine
- **Hybrid Retrieval** — Dense (embeddings) + BM25 with Reciprocal Rank Fusion
- **Cross-Encoder Reranking** — BAAI/bge-reranker-v2-m3 for precision
- **Streaming Responses** — Real-time SSE streaming with source citations
- **Multi-Format Support** — PDF, DOCX, TXT, Markdown document processing
- **Smart Chunking** — Configurable chunk size with overlap for optimal retrieval

### AI Security Layer
- **Prompt Injection Detection** — Classifies and blocks malicious inputs
- **Jailbreak Detection** — Identifies bypass attempts in real-time
- **Input Validation** — Max length, format, and content checks
- **Risk Scoring** — Configurable thresholds with admin bypass option

### Output Guardrails
- **PII Detection** — Scans for sensitive data in LLM outputs
- **Content Moderation** — Blocks harmful, toxic, or inappropriate content
- **Citation Validation** — Ensures responses cite source documents
- **Response Validation** — Checks length, coherence, and groundness

### Enterprise Features
- **Role-Based Access Control** — Admin and user roles with permissions
- **API Key Management** — Generate, revoke, and track API keys
- **Rate Limiting** — Per-user and per-endpoint rate limiting
- **Circuit Breaker** — Automatic LLM provider failover
- **Token Budget Management** — Prevents runaway API costs

### Monitoring & Evaluation
- **Real-Time Metrics** — Request counts, latency, error rates
- **LLM Performance** — Token usage, latency percentiles, success rates
- **Retrieval Quality** — Precision@K, Recall@K, MRR, nDCG
- **Hallucination Detection** — Groundedness scoring and context overlap
- **Dashboard** — Interactive charts with Recharts

### Platform
- **React 18 Frontend** — TypeScript, TailwindCSS, shadcn/ui, React Query
- **FastAPI Backend** — Async Python, SQLAlchemy, Alembic, Celery
- **Docker Deployment** — Multi-stage builds, Docker Compose
- **CI/CD Pipeline** — GitHub Actions with lint, test, security scan
- **Structured Logging** — JSON logs with rotation and separate streams

---

## Architecture

```
                          ┌─────────────────────┐
                          │       Nginx         │
                          │   Reverse Proxy     │
                          │   Rate Limiting     │
                          │   SSL Termination   │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
              ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
              │  Frontend  │   │  Backend  │   │  Static   │
              │  React SPA │   │  FastAPI  │   │  Assets   │
              │  Vite Build│   │  REST API │   │           │
              └───────────┘   └─────┬─────┘   └───────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     │              │              │
               ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
               │ PostgreSQL │ │   Redis   │ │ ChromaDB  │
               │  Primary   │ │  Cache +  │ │  Vector   │
               │  Database  │ │  Broker   │ │  Store    │
               └───────────┘ └───────────┘ └───────────┘
                     │
               ┌─────▼─────┐ ┌───────────┐
               │   Celery  │ │  Celery   │
               │  Worker   │ │   Beat    │
               │  (Async)  │ │ (Cron)    │
               └───────────┘ └───────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose

### Development (Docker)

```bash
# Clone the repository
git clone https://github.com/yourusername/secure-rag.git
cd secure-rag

# Configure environment
cp .env.example .env.development

# Start development environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Development (Manual)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Production

```bash
# Configure production environment
cp .env.example .env.production
# Edit .env.production with secure values

# Generate secrets
openssl rand -hex 32  # For JWT_SECRET_KEY
openssl rand -hex 32  # For ENCRYPTION_KEY

# Start production environment
docker compose up -d --build

# Run database migrations
docker compose exec backend alembic upgrade head
```

---

## Project Structure

```
secure-rag/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/            # API endpoint handlers
│   │   ├── core/              # Middleware, security, exceptions
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── repositories/      # Data access layer
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic layer
│   │   │   ├── security/      # AI security pipeline
│   │   │   ├── guardrails/    # Output protection
│   │   │   ├── monitoring/    # Metrics and evaluation
│   │   │   ├── cache/         # Redis caching
│   │   │   ├── llm/           # LLM provider abstraction
│   │   │   └── background/    # Celery tasks
│   │   └── utils/             # Logging, validators
│   ├── tests/                 # pytest test suite
│   ├── alembic/               # Database migrations
│   └── Dockerfile             # Multi-stage build
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Route page components
│   │   ├── services/          # API client services
│   │   ├── hooks/             # Custom React hooks
│   │   ├── stores/            # Zustand state management
│   │   ├── types/             # TypeScript interfaces
│   │   └── test/              # Vitest unit tests
│   ├── e2e/                   # Playwright E2E tests
│   └── Dockerfile             # Multi-stage build
├── scripts/                    # Backup, restore, health scripts
├── docs/                       # Documentation
├── .github/workflows/          # CI/CD pipeline
├── docker-compose.yml          # Production compose
├── docker-compose.dev.yml      # Development overrides
└── .env.example                # Environment template
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite 6, TailwindCSS 3, shadcn/ui |
| **State** | Zustand, React Query v5, React Hook Form + Zod |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy async, Alembic |
| **Task Queue** | Celery + Redis |
| **Database** | PostgreSQL 16, Redis 7, ChromaDB |
| **LLM** | OpenRouter API (provider-agnostic) |
| **Embeddings** | BAAI/bge-m3 (Sentence Transformers) |
| **Reranking** | BAAI/bge-reranker-v2-m3 (Cross-Encoder) |
| **Testing** | pytest, Vitest, Playwright |
| **DevOps** | Docker, GitHub Actions, Nginx |

---

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/login` | POST | User authentication |
| `/api/v1/documents/upload` | POST | Upload document |
| `/api/v1/chat/query` | POST | RAG query |
| `/api/v1/chat/query/stream` | POST | Streaming RAG query |
| `/api/v1/chat/sessions` | GET/POST | List/create sessions |
| `/api/v1/admin/stats` | GET | Admin statistics |
| `/api/v1/monitoring/metrics` | GET | System metrics |
| `/api/v1/security/statistics` | GET | Security statistics |
| `/api/v1/guardrails/check` | POST | Content moderation |
| `/api/v1/health/detailed` | GET | Detailed health check |

Full API documentation available at `/docs` when `DEBUG=true`.

---

## Security

### AI Security Pipeline
1. **Input Validation** — Length, format, content checks
2. **Prompt Injection Detection** — ML-based classifier with risk scoring
3. **Jailbreak Detection** — Pattern matching + semantic analysis
4. **Query Processing** — Sanitized and validated before LLM

### Output Guardrails
1. **PII Detection** — Scans for SSN, email, phone, credit cards
2. **Content Moderation** — Blocks harmful/inappropriate content
3. **Citation Validation** — Ensures source attribution
4. **Response Validation** — Length, coherence, and groundness checks

### Infrastructure Security
- JWT authentication with short-lived tokens
- CORS restricted to configured origins
- Rate limiting per user and endpoint
- Security headers (HSTS, CSP, X-Frame-Options)
- Non-root Docker containers
- Encrypted secrets in environment variables

---

## Monitoring

The platform includes comprehensive monitoring:

- **Metrics Dashboard** — Real-time charts for requests, latency, errors
- **LLM Metrics** — Token usage, success rates, latency percentiles
- **Retrieval Metrics** — Precision@K, Recall@K, MRR, nDCG@5
- **Hallucination Detection** — Groundedness scoring, context overlap
- **Security Events** — Injection attempts, jailbreaks, PII leaks
- **Health Checks** — Database, Redis, ChromaDB, Celery, LLM

---

## Testing

### Unit Tests
```bash
# Backend
cd backend && pytest -v --cov=app

# Frontend
cd frontend && npx vitest run --coverage
```

### E2E Tests
```bash
cd frontend
npx playwright install
npx playwright test
```

### Health Checks
```bash
./scripts/health_check.sh
```

---

## Deployment

See [Deployment Guide](docs/deployment.md) for detailed instructions.

### Docker
```bash
docker compose up -d --build
```

### Environment Variables
See [Environment Reference](docs/environment.md) for all variables.

---

## Roadmap

- [ ] WebSocket real-time notifications
- [ ] Multi-modal document support (images, tables)
- [ ] Advanced RAG strategies (self-RAG, corrective RAG)
- [ ] Federated search across multiple vector stores
- [ ] A/B testing for retrieval strategies
- [ ] Kubernetes deployment manifests
- [ ] Terraform infrastructure-as-code
- [ ] OpenTelemetry distributed tracing

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [Contributing Guide](CONTRIBUTING.md) for details.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**v1.0.0 — Built with care for production deployment**

</div>
