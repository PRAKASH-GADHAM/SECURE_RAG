# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] - 2026-07-17

### Added

#### Core Platform
- FastAPI async backend with Clean Architecture
- React 18 TypeScript frontend with Vite 6
- PostgreSQL database with SQLAlchemy async and Alembic migrations
- Redis caching and Celery background task processing
- ChromaDB vector database for multi-tenant embedding storage

#### RAG Engine
- Hybrid retrieval (Dense + BM25) with Reciprocal Rank Fusion
- Cross-encoder reranking with BAAI/bge-reranker-v2-m3
- BAAI/bge-m3 embedding model support
- Streaming SSE responses with source citations
- Multi-format document upload (PDF, DOCX, TXT, MD)
- Configurable chunk size and overlap

#### AI Security Layer (5-Layer Pipeline)
- PII detection and redaction (SSN, email, phone, credit cards, medical records)
- Prompt injection detection (6 attack pattern categories)
- Toxicity filtering
- Content policy enforcement
- Output sanitization
- Risk scoring with configurable thresholds

#### Output Guardrails
- Content moderation and filtering
- Citation validation
- Response groundness checking
- Token budget management (per-user/per-model daily limits)

#### Enterprise Features
- JWT authentication with refresh tokens
- Role-based access control (Admin, User)
- API key management
- Rate limiting per user/endpoint (Redis-backed)
- Circuit breaker pattern for LLM/embedding failover
- Conversation rename and deletion
- Notification system with mark-all-read

#### Monitoring & Evaluation
- Real-time metrics dashboard with Recharts
- LLM performance tracking
- Retrieval quality evaluation (Precision@K, Recall@K, MRR, nDCG)
- Hallucination detection
- Security event logging with audit trail
- Structured JSON logging with RotatingFileHandler
- Health endpoints (/health/detailed, /health/system)

#### Frontend (35+ files)
- 11 page components with full CRUD
- 10-tab enterprise admin portal (Overview, Metrics, Latency, Security, Users, Audit Logs, Evaluation, Infrastructure, Guardrails, Configuration)
- Streaming chat with Markdown rendering and syntax highlighting
- Document management with drag-and-drop upload and batch operations
- Notification dropdown with mark-all-read and unread badge
- React.lazy + Suspense code splitting
- Responsive design with mobile support
- Dark/light theme toggle
- Accessibility: ARIA landmarks, skip-to-content, keyboard navigation
- React.memo optimization on Sidebar and Topbar
- Vite manual chunks (vendor/ui/charts/query/markdown/motion/forms)
- 78+ unit tests (Vitest) + 4 Playwright E2E specs

#### DevOps & Infrastructure
- Multi-stage Docker builds (backend + frontend)
- Docker Compose production (8 services) and development configs
- Nginx reverse proxy with rate limiting, WebSocket, streaming, security headers
- GitHub Actions CI/CD pipeline (6 parallel jobs)
- Automated backup and restore scripts
- Health check scripts
- Comprehensive deployment documentation

#### Documentation & Portfolio
- README with badges, architecture diagram, and quick start
- ARCHITECTURE.md with 5 Mermaid diagrams
- SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md
- docs/deployment.md, docs/docker.md, docs/environment.md, docs/production.md
- PORTFOLIO.md (resume bullets, LinkedIn, GitHub description, interview talking points)
- DEMO.md (5-min script, 10-slide deck, system design guide, FAQ)
- GitHub issue and PR templates

### Security
- HSTS, Content-Security-Policy, Permissions-Policy headers
- Non-root Docker containers with tini init
- CORS restriction
- Encrypted secrets management
- Cookie security (Secure, HttpOnly, SameSite=Strict)
- Request ID propagation for distributed tracing
