# Project Name

**Secure Enterprise RAG Platform with Guardrails**

---

# Objective

Build a production-ready, enterprise-grade, SaaS-style Retrieval-Augmented Generation (RAG) platform demonstrating modern AI engineering, security, scalability, maintainability, and software engineering best practices.

The project should resemble an internal enterprise knowledge assistant rather than a simple chatbot.

---

# Core Technologies

## IDE

* Antigravity

## Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* shadcn/ui
* React Query
* Axios

## Backend

* Python 3.11+
* FastAPI
* SQLAlchemy
* Alembic
* Pydantic v2
* JWT Authentication
* Redis
* Celery (preferred) or FastAPI BackgroundTasks
* PostgreSQL
* Docker

## AI Stack

* LangChain
* OpenRouter API (OpenAI-compatible endpoint)
* Sentence Transformers
* ChromaDB

---

# LLM Configuration

Use OpenRouter as the LLM provider.

Never hardcode the model.

The active model must always come from environment variables.

Configure the project with a default free OpenRouter model for development while allowing any compatible OpenRouter model to be used without code changes.

---

# Embedding Configuration

Use Sentence Transformers.

Default embedding model:

BAAI/bge-m3

The embedding model should also be configurable through environment variables.

---

# Retrieval Pipeline

Implement:

* Dense Retrieval
* BM25 Retrieval
* Hybrid Retrieval
* Cross-Encoder Re-ranking using `BAAI/bge-reranker-v2-m3`
* Metadata filtering
* Source citation generation
* Configurable retrieval parameters
* Retrieval metrics collection (dense time, BM25 time, fusion time, rerank time, total latency)

---

# Supported Documents

* PDF
* DOCX
* TXT
* Markdown

Each uploaded document should preserve metadata.

---

# Chunking

Implement:

* Recursive Character Splitter
* Token-aware chunking
* Configurable chunk size
* Configurable overlap
* Metadata preservation

---

# SaaS Architecture

The application must support multiple users.

Each user must have:

* Their own account
* Their own uploaded documents
* Their own vector namespace
* Their own chat history
* Their own settings
* Their own audit logs
* Their own usage statistics

No user should be able to access another user's resources.

---

# Authentication

Implement:

* Registration
* Login
* JWT Access Tokens
* Refresh Token architecture
* Password hashing using bcrypt
* Role-Based Access Control (Admin/User)
* Protected API routes

---

# Database

Use PostgreSQL.

Design tables for at least:

* Users
* Roles
* Sessions
* Documents
* Chunks
* Chats
* Messages
* Feedback
* Audit Logs
* API Usage

Use Alembic for migrations.

---

# Vector Database

Use ChromaDB.

Store:

* Document chunks
* Embeddings
* Metadata
* Source information

---

# Background Processing

Use Celery if practical; otherwise FastAPI BackgroundTasks.

Background jobs should include:

* PDF parsing
* DOCX parsing
* Chunk generation
* Embedding generation
* Vector insertion
* Document indexing

---

# Redis

Use Redis for:

* Response caching
* Retrieval caching
* Session storage
* Rate limiting
* Frequently accessed metadata

---

# Security

Implement:

* Prompt injection detection
* Jailbreak detection
* Context filtering
* PII detection
* Input moderation
* Output moderation
* Hallucination detection
* Source citations
* Secure file validation
* File size limits
* MIME type validation
* Audit logging
* CORS configuration
* Environment-based secrets
* Secure password hashing

---

# Logging

Implement structured JSON logging.

Log:

* Authentication events
* Upload events
* Retrieval events
* AI requests
* Security warnings
* Prompt injection attempts
* Errors
* Performance metrics
* Latency
* Audit events

---

# API Design

Follow REST principles.

Use:

* Versioned API routes
* Dependency injection
* Consistent response models
* Proper HTTP status codes
* Pagination where appropriate

---

# Code Quality

The project must follow:

* Clean Architecture
* SOLID Principles
* DRY Principle
* Modular design
* Repository pattern where appropriate
* Service layer separation
* Strict typing
* Docstrings
* Centralized configuration
* Consistent naming conventions

---

# Testing

Implement:

* Unit tests
* Integration tests
* Authentication tests
* RAG pipeline tests
* API tests
* Security tests

Aim for high test coverage.

---

# Docker

Provide Docker support for:

* Frontend
* Backend
* PostgreSQL
* Redis
* ChromaDB

Use Docker Compose for local development.

---

# Documentation

Maintain and update:

* README.md
* Installation Guide
* API Documentation
* Architecture Documentation
* Deployment Guide
* Database Schema
* Sequence Diagrams

Documentation must be updated whenever functionality changes.

---

# Development Workflow

For every implementation phase, always execute the following sequence:

1. Plan the architecture.
2. Explain design decisions.
3. Create or modify files.
4. Verify imports and dependencies.
5. Check typing and formatting.
6. Detect and fix bugs.
7. Generate tests.
8. Review the completed implementation.
9. Update documentation.
10. Generate a meaningful Git commit message.

Do not skip any step.

Do not move to the next phase until the current phase is fully complete, verified, tested, documented, and internally reviewed.

Maintain architecture consistency throughout the entire project.
