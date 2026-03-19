# Intent Engine - Project Overview

**Version:** v2.3.1 - Professional Organization Update
**Last Updated:** March 18, 2026
**Repository:** [intent-engine](https://github.com/itxLikhith/intent-engine)
**Docker Image:** `anony45/intent-engine-api:latest`
**License:** [IECL v1.0](../../LICENSE)

---

## Executive Summary

The Intent Engine is a **privacy-first, intent-driven system** for search, service recommendation, and ad matching. It processes user queries to extract structured intent while respecting privacy and ethical considerations, without discriminatory targeting or user tracking.

### Core Principles

1. **Intent-First**: All decisions derive from structured intent, not user identity
2. **Privacy Native**: No persistent tracking; intent signals decay on session boundary (8-hour TTL)
3. **Open Architecture**: Intent schema is composable and extensible
4. **Non-Discriminatory**: Matching algorithms never use sensitive attributes
5. **Transparent**: Intent extraction rules are inspectable and rule-based
6. **Self-Improving**: Every search makes the system smarter via automatic URL seeding
7. **Type-Safe Configuration**: Centralized Pydantic settings with validation
8. **Comprehensive Monitoring**: Authoritative health checks for all services

### Key Features (v2.3.1 Reorganization)

#### Application Structure
- ✅ **Modular Package Architecture** - Core logic isolated in `app/` package
- ✅ **Enterprise Entry Point** - Unified `run.py` for API, CLI, and Workers
- ✅ **Clean Root Directory** - Clutter-free root with dedicated `infrastructure/` and `docs/`

#### Health Monitoring
- ✅ **Comprehensive Health Checks** - 9 services monitored (Database, Redis, SearXNG, Go services, Qdrant, Models)
- ✅ **Kubernetes-Style Probes** - Readiness (`/health/ready`) and liveness (`/health/live`) endpoints
- ✅ **Detailed Diagnostics** - Full service health at `/health/detailed`

---

## Quick Reference

### Start the System

```bash
# Using Docker (Recommended)
docker-compose -f infrastructure/compose/docker-compose.yml up -d

# Wait for initialization (~60 seconds)
sleep 60

# Verify installation
curl http://localhost:8000/health/live
```

### First API Call

```bash
# Extract intent from a query
curl -X POST http://localhost:8000/extract-intent \
  -H "Content-Type: application/json" \
  -d '{
    "product": "search",
    "input": {"text": "best laptop for programming under 50000 rupees"},
    "context": {"sessionId": "test-123", "userLocale": "en-US"}
  }' | jq
```

### Run Demos

```bash
# Run all demos via the entry point
python run.py cli demo

# Or directly
python -m app.main demo
```

---

## Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM for database operations
- **Pydantic v2** - Data validation and settings management
- **PostgreSQL** - Primary database
- **Redis/Valkey** - Caching and session management

---

## Project Structure

```
intent-engine/
├── app/                    # Python Application Package
│   ├── api/                # API v1 routes (Planned)
│   ├── extraction/         # Intent extraction
│   ├── ranking/            # Ranking module
│   ├── searxng/            # SearXNG integration
│   ├── core/               # Shared schema and utilities
│   ├── tests/              # Unit + integration tests
│   └── ...                 # Other domain modules
├── go-crawler/             # Go-based web crawler
├── infrastructure/         # DevOps & Ops configuration
│   ├── compose/            # Docker Compose variants
│   ├── docker/             # Dockerfiles
│   ├── database/           # Migrations
│   └── monitoring/         # Prometheus/Grafana
├── docs/                   # Documentation Hub
├── scripts/                # Utility scripts
├── run.py                  # Unified entry point
└── pyproject.toml          # Project metadata
```

---

## Documentation

### Getting Started
| Document | Description |
|----------|-------------|
| **[README.md](../../README.md)** | Main README with quick start guide |
| **[Quick Start](../getting-started/QUICKSTART.md)** | Get started in 5 minutes |
| **[Production Setup](../getting-started/README_PRODUCTION.md)** | Production deployment guide |

### Architecture & Design
| Document | Description |
|----------|-------------|
| **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** | This file - Quick reference and overview |
| **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** | Detailed directory layout |
| **[ARCHITECTURE_BLUEPRINT.md](../ARCHITECTURE_BLUEPRINT.md)** | Unified architecture blueprint |

---

## Testing

```bash
# Run all tests
make test

# Or directly
python -m pytest app/tests/ -v

# Run load tests
cd app/load_testing
locust -f locustfile.py
```

---

## License

This project is licensed under the **Intent Engine Community License (IECL) v1.0** - see the [LICENSE](../../LICENSE) file for details.
